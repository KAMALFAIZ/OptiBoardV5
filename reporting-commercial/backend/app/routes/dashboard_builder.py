"""Routes pour le Dashboard Builder - Creation de dashboards par drag & drop"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..database_unified import execute_central as execute_query, central_cursor as get_db_cursor, DWHConnectionManager, execute_central as execute_master_query, central_cursor as get_master_cursor, execute_dwh
from ..services.datasource_resolver import datasource_resolver, DataSourceOrigin
import json
import logging
import re
import hashlib
import time
from datetime import datetime


def _generate_entity_code(entity_type: str, nom: str) -> str:
    """Genere un code unique pour une entite (ex: DB_accueil_a3f2)"""
    slug = re.sub(r'[^a-z0-9]+', '_', nom.lower().strip())[:40].strip('_')
    suffix = hashlib.md5(f"{nom}{time.time()}".encode()).hexdigest()[:4]
    return f"{entity_type}_{slug}_{suffix}"

logger = logging.getLogger("DashboardBuilder")

router = APIRouter(prefix="/api/builder", tags=["dashboard-builder"])


# Schemas Pydantic
class WidgetConfig(BaseModel):
    id: str
    type: str  # kpi, kpi_compare, gauge, progress, sparkline, chart_bar, chart_stacked_bar, chart_combo, chart_line, chart_pie, chart_area, chart_funnel, chart_treemap, table, text, image
    title: str
    x: float = 0  # Position X dans la grille (float pour react-grid-layout)
    y: float = 0  # Position Y dans la grille
    w: float = 4  # Largeur (colonnes)
    h: float = 4  # Hauteur (lignes)
    config: Dict[str, Any] = {}  # Configuration specifique au widget

    class Config:
        extra = "allow"  # Accepter les champs supplementaires


class DashboardCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    widgets: List[Dict[str, Any]] = []  # Accept raw dicts for flexibility
    is_public: bool = False


class DashboardUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    widgets: Optional[List[Dict[str, Any]]] = None  # Accept raw dicts for flexibility
    is_public: Optional[bool] = None
    application: Optional[str] = None


def init_builder_tables():
    """Cree les tables pour le dashboard builder"""
    queries = [
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Dashboards' AND xtype='U')
        CREATE TABLE APP_Dashboards (
            id INT IDENTITY(1,1) PRIMARY KEY,
            nom NVARCHAR(200) NOT NULL,
            description NVARCHAR(500),
            config NVARCHAR(MAX),
            widgets NVARCHAR(MAX),
            is_public BIT DEFAULT 0,
            created_by INT,
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE(),
            date_modification DATETIME DEFAULT GETDATE()
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_WidgetTemplates' AND xtype='U')
        CREATE TABLE APP_WidgetTemplates (
            id INT IDENTITY(1,1) PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            nom NVARCHAR(200) NOT NULL,
            description NVARCHAR(500),
            default_config NVARCHAR(MAX),
            icon VARCHAR(50)
        )
        """,
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_DataSources' AND xtype='U')
        CREATE TABLE APP_DataSources (
            id INT IDENTITY(1,1) PRIMARY KEY,
            nom NVARCHAR(200) NOT NULL,
            type VARCHAR(50) NOT NULL,
            query_template NVARCHAR(MAX),
            parameters NVARCHAR(MAX),
            description NVARCHAR(500)
        )
        """
    ]

    # Colonnes a ajouter aux tables existantes
    migration_columns = {
        'APP_Dashboards': [
            ("code", "VARCHAR(100)"),
            ("application", "NVARCHAR(100)"),
        ],
        'APP_DataSources': [
            ("code", "VARCHAR(100)"),
        ]
    }

    try:
        with get_db_cursor() as cursor:
            for query in queries:
                cursor.execute(query)
            # Migration: ajouter colonnes manquantes
            for table_name, columns in migration_columns.items():
                for col_name, col_type in columns:
                    try:
                        cursor.execute(f"""
                            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id=OBJECT_ID('{table_name}') AND name='{col_name}')
                            ALTER TABLE {table_name} ADD {col_name} {col_type}
                        """)
                    except Exception:
                        pass
        return True
    except Exception as e:
        print(f"Erreur init builder tables: {e}")
        return False


def init_default_data():
    """Initialise les donnees par defaut (templates uniquement) - Sources gerees par reset_datasources.py"""
    try:
        # Verifier seulement les templates - NE JAMAIS TOUCHER AUX SOURCES
        existing = execute_query("SELECT COUNT(*) as cnt FROM APP_WidgetTemplates", use_cache=False)
        need_templates = not existing or existing[0]['cnt'] == 0

        if need_templates:
            templates = [
                ("kpi", "KPI Simple", "Affiche une valeur avec tendance", '{"value_field": "", "format": "number", "color": "blue", "icon": "TrendingUp"}', "Activity"),
                ("kpi_compare", "KPI Comparatif", "KPI avec comparaison periode precedente", '{"value_field": "", "compare_field": "", "format": "currency"}', "TrendingUp"),
                ("chart_bar", "Graphique Barres", "Diagramme en barres", '{"x_field": "", "y_field": "", "color": "#3b82f6"}', "BarChart2"),
                ("chart_line", "Graphique Lignes", "Courbe d evolution", '{"x_field": "", "y_field": "", "color": "#10b981"}', "LineChart"),
                ("chart_pie", "Graphique Camembert", "Repartition en secteurs", '{"label_field": "", "value_field": ""}', "PieChart"),
                ("chart_area", "Graphique Aires", "Courbe avec aire remplie", '{"x_field": "", "y_field": "", "color": "#8b5cf6"}', "AreaChart"),
                ("table", "Tableau", "Tableau de donnees avec tri et pagination", '{"columns": [], "pageSize": 10}', "Table"),
                ("text", "Texte", "Zone de texte libre", '{"content": "", "fontSize": "base"}', "Type"),
            ]
            with get_db_cursor() as cursor:
                for t in templates:
                    cursor.execute(
                        """INSERT INTO APP_WidgetTemplates (type, nom, description, default_config, icon)
                           VALUES (?, ?, ?, ?, ?)""",
                        t
                    )
        return True
    except Exception as e:
        print(f"Erreur init default data: {e}")
        return False


# ===================== DASHBOARDS =====================

@router.get("/dashboards")
async def get_dashboards(user_id: Optional[int] = None):
    """Liste tous les dashboards"""
    try:
        init_builder_tables()
        init_default_data()

        if user_id:
            results = execute_query(
                """SELECT id, nom, code, description, is_public, created_by, date_creation, date_modification, application
                   FROM APP_Dashboards
                   WHERE created_by = ? OR is_public = 1
                   ORDER BY date_modification DESC""",
                (user_id,),
                use_cache=False
            )
        else:
            results = execute_query(
                """SELECT id, nom, code, description, is_public, created_by, date_creation, date_modification, application
                   FROM APP_Dashboards
                   ORDER BY date_modification DESC""",
                use_cache=False
            )
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: int):
    """Recupere un dashboard avec ses widgets"""
    try:
        results = execute_query(
            "SELECT * FROM APP_Dashboards WHERE id = ?",
            (dashboard_id,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail="Dashboard non trouve")

        dashboard = results[0]
        # Parser les widgets JSON
        if dashboard.get('widgets'):
            dashboard['widgets'] = json.loads(dashboard['widgets'])
        else:
            dashboard['widgets'] = []

        return {"success": True, "data": dashboard}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboards")
async def create_dashboard(dashboard: DashboardCreate, user_id: int = 1):
    """Cree un nouveau dashboard"""
    try:
        init_builder_tables()

        widgets_json = json.dumps(dashboard.widgets)

        # Auto-generer un code unique si absent
        code = getattr(dashboard, 'code', None) or _generate_entity_code('DB', dashboard.nom)

        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_Dashboards (nom, code, description, widgets, is_public, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (dashboard.nom, code, dashboard.description, widgets_json, dashboard.is_public, user_id)
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]

        return {"success": True, "message": "Dashboard cree", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: int, dashboard: DashboardUpdate):
    """Met a jour un dashboard"""
    try:
        updates = []
        params = []

        if dashboard.nom is not None:
            updates.append("nom = ?")
            params.append(dashboard.nom)
        if dashboard.description is not None:
            updates.append("description = ?")
            params.append(dashboard.description)
        if dashboard.widgets is not None:
            updates.append("widgets = ?")
            params.append(json.dumps(dashboard.widgets))
        if dashboard.is_public is not None:
            updates.append("is_public = ?")
            params.append(dashboard.is_public)
        if dashboard.application is not None:
            updates.append("application = ?")
            params.append(dashboard.application)

        updates.append("date_modification = GETDATE()")

        if not updates:
            return {"success": False, "message": "Aucune modification"}

        params.append(dashboard_id)

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE APP_Dashboards SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

        return {"success": True, "message": "Dashboard mis a jour"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: int):
    """Supprime un dashboard (interdit pour les dashboards publics/accueil)"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT is_public FROM APP_Dashboards WHERE id = ?", (dashboard_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dashboard non trouvé")
            if row[0]:
                raise HTTPException(status_code=403, detail="Impossible de supprimer le dashboard d'accueil")
            cursor.execute("DELETE FROM APP_Dashboards WHERE id = ?", (dashboard_id,))
        return {"success": True, "message": "Dashboard supprime"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== TEMPLATES =====================

@router.get("/templates")
async def get_widget_templates():
    """Liste les templates de widgets disponibles"""
    try:
        init_builder_tables()
        init_default_data()

        results = execute_master_query(
            "SELECT * FROM APP_WidgetTemplates ORDER BY type, nom",
            use_cache=False
        )

        # Parser les configs JSON
        for r in results:
            if r.get('default_config'):
                r['default_config'] = json.loads(r['default_config'])

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ===================== DATA SOURCES =====================

@router.get("/datasources")
async def get_data_sources():
    """Liste les sources de donnees disponibles"""
    try:
        init_builder_tables()
        init_default_data()

        results = execute_query(
            "SELECT * FROM APP_DataSources ORDER BY nom",
            use_cache=False
        )

        # Parser les parameters JSON
        for r in results:
            if r.get('parameters'):
                r['parameters'] = json.loads(r['parameters'])

        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


class ParameterDefinition(BaseModel):
    """Définition d'un paramètre de datasource"""
    name: str
    type: str = "string"  # string, number, float, date, boolean
    label: str = ""
    required: bool = False
    source: str = "user"  # global, user, fixed
    global_key: Optional[str] = None
    default: Optional[Any] = None
    options: Optional[List[Any]] = None


class DataSourceCreate(BaseModel):
    nom: str
    type: str = "query"
    description: Optional[str] = None
    query_template: str
    parameters: List[Dict[str, Any]] = []  # Liste de ParameterDefinition


class DataSourceUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    query_template: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None


@router.post("/datasources")
async def create_data_source(source: DataSourceCreate):
    """Cree une nouvelle source de donnees"""
    try:
        init_builder_tables()

        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_DataSources (nom, type, description, query_template, parameters)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    source.nom,
                    source.type,
                    source.description,
                    source.query_template,
                    json.dumps(source.parameters)
                )
            )
            cursor.execute("SELECT @@IDENTITY AS id")
            new_id = cursor.fetchone()[0]

        return {"success": True, "message": "Source creee", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/datasources/{source_id}")
async def update_data_source(source_id: int, source: DataSourceUpdate):
    """Met à jour une source de données"""
    try:
        updates = []
        params = []

        if source.nom is not None:
            updates.append("nom = ?")
            params.append(source.nom)
        if source.description is not None:
            updates.append("description = ?")
            params.append(source.description)
        if source.query_template is not None:
            updates.append("query_template = ?")
            params.append(source.query_template)
        if source.parameters is not None:
            updates.append("parameters = ?")
            params.append(json.dumps(source.parameters))

        if not updates:
            return {"success": False, "message": "Aucune modification"}

        params.append(source_id)

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE APP_DataSources SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

        return {"success": True, "message": "Source mise à jour"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/datasources/{source_id}")
async def delete_data_source(source_id: int):
    """Supprime une source de données"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_DataSources WHERE id = ?", (source_id,))
        return {"success": True, "message": "Source supprimée"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datasources/{source_id}")
async def get_data_source(
    source_id: int,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Récupère une source de données avec ses paramètres

    Utilise le resolver avec fallback Template -> Override
    """
    try:
        # Essayer avec le resolver (fallback template -> override)
        try:
            datasource = datasource_resolver.resolve_by_id(source_id, dwh_code)
            source = datasource.to_dict()
            if source.get('parameters'):
                source['parameters'] = json.loads(source['parameters'])
            else:
                source['parameters'] = []
            source['_origin'] = datasource.origin.value
            return {"success": True, "data": source}
        except ValueError:
            pass

        # Fallback: ancien comportement
        sources = execute_query(
            "SELECT * FROM APP_DataSources WHERE id = ?",
            (source_id,),
            use_cache=False
        )

        if not sources:
            raise HTTPException(status_code=404, detail="Source non trouvée")

        source = sources[0]
        if source.get('parameters'):
            source['parameters'] = json.loads(source['parameters'])
        else:
            source['parameters'] = []

        return {"success": True, "data": source}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/datasources/{source_id}/extract-params")
async def extract_datasource_params(
    source_id: int,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Extrait automatiquement les paramètres d'une requête SQL

    Utilise le resolver avec fallback Template -> Override
    """
    from ..services.parameter_resolver import extract_parameters_from_query

    try:
        query = None

        # Essayer avec le resolver
        try:
            datasource = datasource_resolver.resolve_by_id(source_id, dwh_code)
            query = datasource.query_template
        except ValueError:
            # Fallback: ancien comportement
            sources = execute_query(
                "SELECT query_template FROM APP_DataSources WHERE id = ?",
                (source_id,),
                use_cache=False
            )
            if not sources:
                raise HTTPException(status_code=404, detail="Source non trouvée")
            query = sources[0]['query_template']

        suggestions = extract_parameters_from_query(query)

        return {"success": True, "parameters": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "parameters": []}


@router.post("/datasources/{source_id}/preview")
async def preview_data_source(
    source_id: int,
    context: Dict[str, Any] = {},
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Execute une source de données avec les filtres globaux

    Utilise le resolver avec fallback Template -> Override
    - context.__limit=0 => pas de limite (viewer mode, toutes les donnees)
    - context.__limit absent => defaut TOP 100 (builder/preview)
    """
    from ..services.parameter_resolver import inject_params

    try:
        query = None
        origin = "local"
        limit = context.pop('__limit', 100) if isinstance(context, dict) else 100

        # Essayer avec le resolver
        try:
            datasource = datasource_resolver.resolve_by_id(source_id, dwh_code)
            query = datasource.query_template
            origin = datasource.origin.value
        except ValueError:
            # Fallback: ancien comportement
            sources = execute_query(
                "SELECT * FROM APP_DataSources WHERE id = ?",
                (source_id,),
                use_cache=False
            )
            if not sources:
                raise HTTPException(status_code=404, detail="Source non trouvée")
            query = sources[0]['query_template']

        # Gérer @societe_filter AVANT inject_params (sinon inject_params le remplace par NULL)
        if '@societe_filter' in query:
            societe_val = context.get('societe') or context.get('societe_filter')
            if societe_val:
                query = query.replace('@societe_filter', f"societe_code = '{societe_val}'")
            else:
                query = query.replace('@societe_filter', '1=1')

        # Gérer @societe IS NULL OR pattern
        if '@societe' in query and 'societe_filter' not in query:
            societe_val = context.get('societe')
            if not societe_val:
                # Remplacer le pattern (@societe IS NULL OR ...) par 1=1
                import re
                query = re.sub(
                    r'\(\s*@societe\s+IS\s+NULL\s+OR\s+[^)]+\)',
                    '1=1',
                    query,
                    flags=re.IGNORECASE
                )

        # Injecter les paramètres directement
        final_query = inject_params(query, context)

        # Ajouter TOP si absent (sauf si limit=0 => viewer mode, pas de limite)
        if limit and limit > 0 and "SELECT" in final_query.upper() and "TOP" not in final_query.upper():
            final_query = final_query.replace("SELECT", f"SELECT TOP {limit}", 1)

        # Router vers le DWH pour les datasources template
        effective_dwh = dwh_code
        if not effective_dwh and origin == "template":
            # Auto-détection: prendre le premier DWH actif
            try:
                dwh_list = execute_master_query(
                    "SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id",
                    use_cache=True
                )
                if dwh_list:
                    effective_dwh = dwh_list[0]['code']
            except Exception:
                pass

        if effective_dwh:
            # Exécuter sur le DWH client (templates ET sources locales)
            logger.info(f"Executing on DWH '{effective_dwh}' (origin={origin})")
            results = DWHConnectionManager.execute_dwh_query(
                effective_dwh, final_query, use_cache=False
            )
        else:
            results = execute_query(final_query, use_cache=False)

        return {
            "success": True,
            "data": results if (not limit or limit <= 0) else results[:limit],
            "columns": list(results[0].keys()) if results else [],
            "total": len(results),
            "executed_query": final_query[:200] + "..." if len(final_query) > 200 else final_query,
            "_origin": origin,
            "_dwh": effective_dwh
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/execute-query")
async def execute_custom_query(query: str, params: Dict[str, Any] = {}):
    """Execute une requete personnalisee (SELECT uniquement)"""
    try:
        # Securite: uniquement SELECT
        if not query.strip().upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Seules les requetes SELECT sont autorisees")

        # Remplacer les parametres (utiliser inject_params pour le format de dates sécurisé)
        from ..services.parameter_resolver import inject_params
        query = inject_params(query, params)

        # Limiter les resultats
        if "TOP" not in query.upper():
            query = query.replace("SELECT", "SELECT TOP 1000", 1)

        results = execute_query(query, use_cache=False)

        return {
            "success": True,
            "data": results,
            "columns": list(results[0].keys()) if results else [],
            "total": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ===================== DWH QUERY =====================

@router.get("/dwh-tables")
async def get_dwh_tables(dwh_code: Optional[str] = None):
    """Liste les tables d'un DWH (auto-detect si pas de code fourni)"""
    try:
        effective_dwh = dwh_code
        if not effective_dwh:
            dwh_list = execute_query(
                "SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id",
                use_cache=True
            )
            if dwh_list:
                effective_dwh = dwh_list[0]['code']

        if not effective_dwh:
            return {"success": False, "error": "Aucun DWH configuré", "tables": []}

        results = DWHConnectionManager.execute_dwh_query(
            effective_dwh,
            """SELECT TABLE_NAME as name, TABLE_TYPE as type
               FROM INFORMATION_SCHEMA.TABLES
               WHERE TABLE_TYPE = 'BASE TABLE'
               ORDER BY TABLE_NAME""",
            use_cache=False
        )
        return {"success": True, "tables": results, "dwh": effective_dwh}
    except Exception as e:
        return {"success": False, "error": str(e), "tables": []}


# ===================== QUERY BUILDER =====================

@router.get("/query-builder/tables")
async def get_database_tables(
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Recupere la liste des tables et vues de la base de donnees DWH"""
    try:
        results = execute_dwh(
            """SELECT TABLE_NAME as name, TABLE_TYPE as type
               FROM INFORMATION_SCHEMA.TABLES
               WHERE (TABLE_TYPE = 'BASE TABLE' OR TABLE_TYPE = 'VIEW')
               AND TABLE_NAME NOT LIKE 'APP_%'
               AND TABLE_NAME NOT LIKE 'Temp_%'
               AND TABLE_NAME NOT LIKE 'sys%'
               ORDER BY TABLE_TYPE, TABLE_NAME""",
            dwh_code=dwh_code,
            use_cache=False
        )
        return {"success": True, "tables": results}
    except Exception as e:
        return {"success": False, "error": str(e), "tables": []}


@router.get("/query-builder/tables/{table_name}/columns")
async def get_table_columns(
    table_name: str,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Recupere les colonnes d'une table du DWH"""
    try:
        results = execute_dwh(
            """SELECT
                COLUMN_NAME as name,
                DATA_TYPE as type,
                IS_NULLABLE as nullable,
                CHARACTER_MAXIMUM_LENGTH as max_length,
                NUMERIC_PRECISION as precision
               FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_NAME = ?
               ORDER BY ORDINAL_POSITION""",
            (table_name,),
            dwh_code=dwh_code,
            use_cache=False
        )
        return {"success": True, "columns": results}
    except Exception as e:
        return {"success": False, "error": str(e), "columns": []}


@router.get("/query-builder/tables/{table_name}/relations")
async def get_table_relations(
    table_name: str,
    dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """Recupere les relations (foreign keys) d'une table du DWH"""
    try:
        results = execute_dwh(
            """SELECT
                fk.name AS constraint_name,
                tp.name AS parent_table,
                cp.name AS parent_column,
                tr.name AS referenced_table,
                cr.name AS referenced_column
               FROM sys.foreign_keys fk
               INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
               INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
               INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
               INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
               INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
               WHERE tp.name = ? OR tr.name = ?""",
            (table_name, table_name),
            dwh_code=dwh_code,
            use_cache=False
        )
        return {"success": True, "relations": results}
    except Exception as e:
        return {"success": False, "error": str(e), "relations": []}


class QueryBuilderRequest(BaseModel):
    tables: List[Dict[str, Any]]  # [{name, alias, columns: [{name, alias, aggregate, groupBy}]}]
    joins: List[Dict[str, Any]] = []  # [{type, table1, column1, table2, column2}]
    where: List[Dict[str, Any]] = []  # [{column, operator, value, connector}]
    groupBy: List[str] = []
    orderBy: List[Dict[str, str]] = []  # [{column, direction}]
    limit: int = 1000


@router.post("/query-builder/build")
async def build_query(request: QueryBuilderRequest):
    """Construit une requete SQL a partir de la configuration"""
    try:
        # SELECT
        select_parts = []
        for table in request.tables:
            table_alias = table.get('alias', table['name'])
            for col in table.get('columns', []):
                col_name = col['name']
                col_alias = col.get('alias', '')
                aggregate = col.get('aggregate', '')

                if col_name == '*':
                    select_parts.append(f"[{table_alias}].*")
                elif aggregate:
                    if col_alias:
                        select_parts.append(f"{aggregate}([{table_alias}].[{col_name}]) AS [{col_alias}]")
                    else:
                        select_parts.append(f"{aggregate}([{table_alias}].[{col_name}]) AS [{aggregate}_{col_name}]")
                else:
                    if col_alias:
                        select_parts.append(f"[{table_alias}].[{col_name}] AS [{col_alias}]")
                    else:
                        select_parts.append(f"[{table_alias}].[{col_name}]")

        if not select_parts:
            select_parts = ["*"]

        # FROM
        from_table = request.tables[0]
        from_alias = from_table.get('alias', from_table['name'])
        from_part = f"[{from_table['name']}] AS [{from_alias}]"

        # JOINS
        join_parts = []
        for join in request.joins:
            join_type = join.get('type', 'INNER JOIN')
            t2 = join['table2']
            t2_alias = join.get('alias2', t2)
            join_parts.append(
                f"{join_type} [{t2}] AS [{t2_alias}] ON [{join['table1']}].[{join['column1']}] = [{t2_alias}].[{join['column2']}]"
            )

        # WHERE
        where_parts = []
        for i, cond in enumerate(request.where):
            col = cond['column']
            op = cond['operator']
            val = cond['value']
            connector = cond.get('connector', 'AND') if i > 0 else ''

            if op.upper() in ('IS NULL', 'IS NOT NULL'):
                clause = f"[{col}] {op}"
            elif op.upper() in ('IN', 'NOT IN'):
                clause = f"[{col}] {op} ({val})"
            elif op.upper() == 'LIKE':
                clause = f"[{col}] LIKE '%{val}%'"
            else:
                if isinstance(val, str):
                    clause = f"[{col}] {op} '{val}'"
                else:
                    clause = f"[{col}] {op} {val}"

            if connector:
                where_parts.append(f"{connector} {clause}")
            else:
                where_parts.append(clause)

        # GROUP BY
        group_by_part = ""
        if request.groupBy:
            group_by_part = "GROUP BY " + ", ".join([f"[{g}]" for g in request.groupBy])

        # ORDER BY
        order_by_part = ""
        if request.orderBy:
            order_parts = [f"[{o['column']}] {o.get('direction', 'ASC')}" for o in request.orderBy]
            order_by_part = "ORDER BY " + ", ".join(order_parts)

        # Build final query
        query = f"SELECT TOP {request.limit} {', '.join(select_parts)}\nFROM {from_part}"
        if join_parts:
            query += "\n" + "\n".join(join_parts)
        if where_parts:
            query += "\nWHERE " + " ".join(where_parts)
        if group_by_part:
            query += "\n" + group_by_part
        if order_by_part:
            query += "\n" + order_by_part

        return {"success": True, "query": query}
    except Exception as e:
        return {"success": False, "error": str(e), "query": ""}


@router.post("/query-builder/preview")
async def preview_query(data: Dict[str, Any]):
    """Execute une requete et retourne un apercu"""
    try:
        query = data.get('query', '')

        # Securite: uniquement SELECT
        if not query.strip().upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Seules les requetes SELECT sont autorisees")

        # Ajouter TOP si absent
        if "TOP" not in query.upper():
            query = query.replace("SELECT", "SELECT TOP 100", 1)

        results = execute_query(query, use_cache=False)

        return {
            "success": True,
            "data": results[:100],
            "columns": list(results[0].keys()) if results else [],
            "total": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ===================== PARAMETER RESOLVER CONFIG =====================

@router.get("/parameters/config")
async def get_parameter_config():
    """Retourne la configuration des paramètres (macros, types, sources disponibles)"""
    from ..services.parameter_resolver import (
        AVAILABLE_MACROS, AVAILABLE_GLOBAL_KEYS, PARAMETER_TYPES, PARAMETER_SOURCES
    )

    return {
        "success": True,
        "macros": AVAILABLE_MACROS,
        "global_keys": AVAILABLE_GLOBAL_KEYS,
        "types": PARAMETER_TYPES,
        "sources": PARAMETER_SOURCES
    }


@router.post("/parameters/extract")
async def extract_params_from_query(data: Dict[str, str]):
    """Extrait les paramètres d'une requête SQL brute"""
    from ..services.parameter_resolver import extract_parameters_from_query

    try:
        query = data.get('query', '')
        if not query:
            return {"success": False, "error": "Requête vide", "parameters": []}

        suggestions = extract_parameters_from_query(query)
        return {"success": True, "parameters": suggestions}
    except Exception as e:
        return {"success": False, "error": str(e), "parameters": []}


# ===================== AI TEMPLATE GENERATOR =====================

class AIGenerateRequest(BaseModel):
    description: str
    dwh_code: Optional[str] = None
    user_id: Optional[int] = None


@router.post("/ai/generate")
async def ai_generate_dashboard(
    request: AIGenerateRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Genere un dashboard complet (widgets + SQL) a partir d'une description textuelle via l'IA.
    Retourne la structure JSON du dashboard prete a etre importee dans le builder.
    """
    from ..services.ai_provider import get_ai_provider, AIMessage, AIProviderError
    from ..services.ai_schema import get_schema_for_ai
    from ..services.ai_sql_validator import validate_ai_sql
    import json as _json

    dwh_code = request.dwh_code or x_dwh_code
    user_id = request.user_id or (int(x_user_id) if x_user_id and x_user_id.isdigit() else 0)

    # Résoudre le DWH automatiquement si absent
    if not dwh_code:
        try:
            dwh_rows = execute_query(
                "SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id",
                use_cache=True
            )
            if dwh_rows:
                dwh_code = dwh_rows[0]['code']
        except Exception:
            pass

    # Récupérer le provider IA
    try:
        provider = get_ai_provider()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not provider:
        raise HTTPException(
            status_code=503,
            detail="Module IA non configuré. Activez un fournisseur dans Paramètres > Intelligence Artificielle."
        )

    # Récupérer le schéma DWH
    schema_text = "(Schéma non disponible)"
    if dwh_code:
        try:
            schema_text = get_schema_for_ai(dwh_code)
        except Exception:
            pass

    # Types de widgets disponibles
    widget_types_desc = """
Types de widgets disponibles:
- kpi          : KPI simple (1 valeur). config: {sql, value_field, format:"number|currency|percent", color:"blue|green|red|orange|purple"}
- kpi_compare  : KPI avec comparaison N vs N-1. config: {sql, value_field, compare_sql, compare_field, format}
- chart_bar    : Barres verticales. config: {sql, x_field, y_fields:["col1","col2"], color}
- chart_line   : Courbe. config: {sql, x_field, y_fields:["col1"], color}
- chart_pie    : Camembert. config: {sql, label_field, value_field}
- chart_area   : Aire. config: {sql, x_field, y_fields:["col1"], color}
- chart_stacked_bar : Barres empilées. config: {sql, x_field, y_fields:["col1","col2"]}
- table        : Tableau de données. config: {sql, columns:[{key,label}], pageSize:10}
- text         : Texte libre. config: {content:"<texte>", fontSize:"base|lg|xl"}
Grille: 12 colonnes. Largeurs conseillées: kpi=3, graphique=6, tableau=12
""".strip()

    system_prompt = f"""Tu es un expert en création de dashboards pour OptiBoard, une plateforme de reporting commercial.
Ta tâche: générer un dashboard complet au format JSON à partir de la description de l'utilisateur.

{schema_text}

{widget_types_desc}

RÈGLES SQL OBLIGATOIRES:
- T-SQL (SQL Server): TOP, GETDATE(), DATEADD, FORMAT, ISNULL
- Pour CA/ventes: TOUJOURS WHERE [Valorise CA] = 'Oui'
- Noms de colonnes entre crochets: [Montant HT Net]
- Tables SANS préfixe: FROM Lignes_des_ventes
- Pas de point-virgule, pas de DROP/INSERT/UPDATE

FORMAT DE SORTIE — Retourne UNIQUEMENT du JSON valide, sans markdown ni commentaires:
{{
  "nom": "Nom du dashboard",
  "description": "Description courte",
  "widgets": [
    {{
      "id": "w_1",
      "type": "kpi",
      "title": "Titre du widget",
      "x": 0, "y": 0, "w": 3, "h": 3,
      "config": {{
        "sql": "SELECT SUM([Montant HT Net]) AS valeur FROM Lignes_des_ventes WHERE [Valorise CA] = 'Oui'",
        "value_field": "valeur",
        "format": "currency",
        "color": "blue"
      }}
    }}
  ]
}}
Positionne les widgets intelligemment dans la grille 12 colonnes (y croissant).
"""

    messages = [
        AIMessage("system", system_prompt),
        AIMessage("user", f"Crée un dashboard pour: {request.description}")
    ]

    try:
        raw_response = await provider.chat(messages)
    except AIProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur IA: {str(e)}")

    # Extraire le JSON de la réponse (peut être entouré de ```json...```)
    json_text = raw_response.strip()
    if "```" in json_text:
        import re as _re
        match = _re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
        if match:
            json_text = match.group(1).strip()

    try:
        dashboard_data = _json.loads(json_text)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=f"L'IA n'a pas retourné un JSON valide. Réessayez avec une description plus précise."
        )

    # Valider et sécuriser chaque SQL dans les widgets
    widgets = dashboard_data.get("widgets", [])
    validation_warnings = []

    for i, widget in enumerate(widgets):
        cfg = widget.get("config", {})
        for sql_key in ("sql", "compare_sql"):
            sql = cfg.get(sql_key)
            if sql:
                is_valid, safe_sql, err = validate_ai_sql(sql, max_rows=500)
                if is_valid:
                    cfg[sql_key] = safe_sql
                else:
                    validation_warnings.append(f"Widget '{widget.get('title', i)}' SQL invalide: {err}")
                    cfg[sql_key] = sql  # garder l'original mais signaler

        # Assurer un ID unique
        if not widget.get("id"):
            widget["id"] = f"w_{i+1}_{int(time.time()) % 10000}"

        widget["config"] = cfg

    dashboard_data["widgets"] = widgets

    return {
        "success": True,
        "dashboard": dashboard_data,
        "warnings": validation_warnings,
        "provider": provider.get_provider_name(),
        "dwh_code": dwh_code
    }


# ===================== AI PIVOT GENERATOR =====================

@router.post("/ai/generate/pivot")
async def ai_generate_pivot(
    request: AIGenerateRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Genere une configuration de Pivot Table complete a partir d'une description via l'IA.
    Retourne: sql (requete source), nom, rows_config, columns_config, values_config.
    """
    from ..services.ai_provider import get_ai_provider, AIMessage, AIProviderError
    from ..services.ai_schema import get_schema_for_ai
    from ..services.ai_sql_validator import validate_ai_sql
    import json as _json

    dwh_code = request.dwh_code or x_dwh_code
    if not dwh_code:
        try:
            rows = execute_query("SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id", use_cache=True)
            if rows:
                dwh_code = rows[0]['code']
        except Exception:
            pass

    try:
        provider = get_ai_provider()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not provider:
        raise HTTPException(status_code=503, detail="Module IA non configuré.")

    schema_text = "(Schéma non disponible)"
    if dwh_code:
        try:
            schema_text = get_schema_for_ai(dwh_code)
        except Exception:
            pass

    system_prompt = f"""Tu es un expert en analyse de données pour OptiBoard.
Ta tâche: générer une configuration complète de Pivot Table au format JSON.

{schema_text}

RÈGLES SQL (T-SQL SQL Server):
- Pour CA/ventes: TOUJOURS WHERE [Valorise CA] = 'Oui'
- Noms de colonnes entre crochets: [Montant HT Net]
- Tables SANS préfixe: FROM Lignes_des_ventes
- Utilise des alias SQL clairs (sans espaces, ex: ca_ht, nb_clients)
- Pas de point-virgule

STRUCTURE DE LA CONFIGURATION:
- rows_config: axes de lignes (dimensions: clients, articles, périodes...)
- columns_config: axes de colonnes (ex: mois, catalogue) — souvent vide []
- values_config: mesures (montants, quantités, comptes) avec aggregate SUM/AVG/COUNT
- filters_config: filtres prédéfinis (souvent vide [])

Aggregates disponibles: SUM, AVG, COUNT, MIN, MAX
Formats disponibles: currency, number, percent, date

Retourne UNIQUEMENT du JSON valide sans markdown:
{{
  "nom": "Nom du pivot",
  "description": "Description courte",
  "sql": "SELECT ... FROM ... WHERE ...",
  "rows_config": [
    {{"field": "nom_colonne_sql", "label": "Libellé affiché"}}
  ],
  "columns_config": [],
  "values_config": [
    {{"field": "nom_alias_sql", "label": "Libellé", "aggregate": "SUM", "format": "currency"}}
  ],
  "filters_config": [],
  "show_grand_totals": true,
  "show_subtotals": true,
  "comparison_mode": ""
}}

IMPORTANT: Les "field" dans rows/values/filters doivent correspondre EXACTEMENT aux alias ou noms de colonnes du SELECT.
"""

    messages = [
        AIMessage("system", system_prompt),
        AIMessage("user", f"Crée un pivot pour: {request.description}")
    ]

    try:
        raw = await provider.chat(messages)
    except AIProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    json_text = raw.strip()
    if "```" in json_text:
        import re as _re
        m = _re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
        if m:
            json_text = m.group(1).strip()

    try:
        pivot_data = _json.loads(json_text)
    except Exception:
        raise HTTPException(status_code=422, detail="L'IA n'a pas retourné un JSON valide. Réessayez.")

    # Valider le SQL
    sql = pivot_data.get("sql", "")
    warnings = []
    if sql:
        is_valid, safe_sql, err = validate_ai_sql(sql, max_rows=5000)
        if is_valid:
            pivot_data["sql"] = safe_sql
        else:
            warnings.append(f"SQL invalide: {err}")

    return {
        "success": True,
        "pivot": pivot_data,
        "warnings": warnings,
        "provider": provider.get_provider_name(),
        "dwh_code": dwh_code
    }


# ===================== AI GRIDVIEW GENERATOR =====================

@router.post("/ai/generate/gridview")
async def ai_generate_gridview(
    request: AIGenerateRequest,
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """
    Genere une configuration de GridView (tableau AG Grid) complete via l'IA.
    Retourne: sql, nom, columns (field, header, format, width...).
    """
    from ..services.ai_provider import get_ai_provider, AIMessage, AIProviderError
    from ..services.ai_schema import get_schema_for_ai
    from ..services.ai_sql_validator import validate_ai_sql
    import json as _json

    dwh_code = request.dwh_code or x_dwh_code
    if not dwh_code:
        try:
            rows = execute_query("SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id", use_cache=True)
            if rows:
                dwh_code = rows[0]['code']
        except Exception:
            pass

    try:
        provider = get_ai_provider()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not provider:
        raise HTTPException(status_code=503, detail="Module IA non configuré.")

    schema_text = "(Schéma non disponible)"
    if dwh_code:
        try:
            schema_text = get_schema_for_ai(dwh_code)
        except Exception:
            pass

    system_prompt = f"""Tu es un expert en reporting pour OptiBoard.
Ta tâche: générer une configuration complète de GridView (tableau de données) au format JSON.

{schema_text}

RÈGLES SQL (T-SQL SQL Server):
- Pour CA/ventes: TOUJOURS WHERE [Valorise CA] = 'Oui'
- Noms de colonnes entre crochets: [Montant HT Net]
- Tables SANS préfixe: FROM Lignes_des_ventes
- Utilise des alias SQL propres (sans espaces, ex: ca_ht, nb_clients)
- Pas de point-virgule
- Ajoute ORDER BY pertinent

Formats de colonnes disponibles: currency, number, percent, date (ou null si texte)
Largeurs conseillées: date=110, texte court=130, texte long=200, montant=130

Retourne UNIQUEMENT du JSON valide sans markdown:
{{
  "nom": "Nom de la grille",
  "description": "Description courte",
  "sql": "SELECT TOP 500 ... FROM ... WHERE ... ORDER BY ...",
  "columns": [
    {{"field": "alias_sql", "header": "Libellé colonne", "format": "currency", "width": 130, "align": "right", "sortable": true, "filterable": true, "visible": true}},
    {{"field": "alias_texte", "header": "Client", "format": null, "width": 200, "align": "left", "sortable": true, "filterable": true, "visible": true}}
  ],
  "page_size": 25,
  "show_totals": false,
  "total_columns": []
}}

IMPORTANT: Les "field" dans columns doivent correspondre EXACTEMENT aux alias du SELECT SQL.
Pour les montants (format currency/number), mettre align: "right".
"""

    messages = [
        AIMessage("system", system_prompt),
        AIMessage("user", f"Crée une grille pour: {request.description}")
    ]

    try:
        raw = await provider.chat(messages)
    except AIProviderError as e:
        raise HTTPException(status_code=503, detail=str(e))

    json_text = raw.strip()
    if "```" in json_text:
        import re as _re
        m = _re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
        if m:
            json_text = m.group(1).strip()

    try:
        grid_data = _json.loads(json_text)
    except Exception:
        raise HTTPException(status_code=422, detail="L'IA n'a pas retourné un JSON valide. Réessayez.")

    sql = grid_data.get("sql", "")
    warnings = []
    if sql:
        is_valid, safe_sql, err = validate_ai_sql(sql, max_rows=1000)
        if is_valid:
            grid_data["sql"] = safe_sql
        else:
            warnings.append(f"SQL invalide: {err}")

    return {
        "success": True,
        "gridview": grid_data,
        "warnings": warnings,
        "provider": provider.get_provider_name(),
        "dwh_code": dwh_code
    }
