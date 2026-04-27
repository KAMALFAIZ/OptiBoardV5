"""
Routes pour la gestion des DataSources Templates
================================================
CRUD pour les templates de datasources (centraux et overrides par DWH)
"""

from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
from pydantic import BaseModel
from ..database_unified import execute_central as execute_query, central_cursor as get_db_cursor, DWHConnectionManager

router = APIRouter(prefix="/api/datasources", tags=["DataSource Templates"])


# =============================================================================
# SCHEMAS
# =============================================================================

class DataSourceTemplateCreate(BaseModel):
    code: str
    nom: str
    type: str = "query"
    category: str = "Ventes"
    description: Optional[str] = None
    query_template: str
    parameters: Optional[str] = "[]"
    is_system: bool = False
    actif: bool = True


class DataSourceTemplateUpdate(BaseModel):
    nom: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    query_template: Optional[str] = None
    parameters: Optional[str] = None
    is_system: Optional[bool] = None
    actif: Optional[bool] = None


# =============================================================================
# TEMPLATES (Base centrale)
# =============================================================================

@router.get("/templates")
async def get_templates(
    category: Optional[str] = Query(None, description="Filtrer par categorie"),
    search: Optional[str] = Query(None, description="Recherche par code ou nom")
):
    """Liste tous les templates de datasources depuis la base centrale"""
    try:
        query = """
            SELECT
                id, code, nom, type, category, description,
                query_template, parameters, is_system, actif, date_creation
            FROM APP_DataSources_Templates
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(category)

        if search:
            query += " AND (code LIKE ? OR nom LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY category, code"

        templates = execute_query(query, tuple(params) if params else None, use_cache=False)

        # Compter par categorie
        categories_count = {}
        for t in templates:
            cat = t.get('category', 'Autre')
            categories_count[cat] = categories_count.get(cat, 0) + 1

        return {
            "success": True,
            "data": templates,
            "total": len(templates),
            "categories": categories_count
        }
    except Exception as e:
        print(f"[ERROR] get_templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: int):
    """Recupere un template specifique par ID"""
    try:
        templates = execute_query(
            """
            SELECT
                id, code, nom, type, category, description,
                query_template, parameters, is_system, actif, date_creation
            FROM APP_DataSources_Templates
            WHERE id = ?
            """,
            (template_id,),
            use_cache=False
        )

        if not templates:
            raise HTTPException(status_code=404, detail="Template non trouve")

        return {
            "success": True,
            "data": templates[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/code/{code}")
async def get_template_by_code(code: str):
    """Recupere un template specifique par code"""
    try:
        templates = execute_query(
            """
            SELECT
                id, code, nom, type, category, description,
                query_template, parameters, is_system, actif, date_creation
            FROM APP_DataSources_Templates
            WHERE code = ?
            """,
            (code,),
            use_cache=False
        )

        if not templates:
            raise HTTPException(status_code=404, detail="Template non trouve")

        return {
            "success": True,
            "data": templates[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_template_by_code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(
    template: DataSourceTemplateCreate,
    x_user_role: str = Header(None, alias="X-User-Role"),
    x_user_id: str = Header(None, alias="X-User-Id")
):
    """Cree un nouveau template de datasource"""
    try:
        # Verification role pour templates systeme
        if template.is_system and x_user_role != "superadmin":
            raise HTTPException(status_code=403, detail="Seul un superadmin peut creer des templates systeme")

        # Verifier si le code existe deja
        existing = execute_query(
            "SELECT id FROM APP_DataSources_Templates WHERE code = ?",
            (template.code,),
            use_cache=False
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"Le code '{template.code}' existe deja")

        # Inserer le template
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO APP_DataSources_Templates
                (code, nom, type, category, description, query_template, parameters, is_system, actif)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template.code,
                    template.nom,
                    template.type,
                    template.category,
                    template.description,
                    template.query_template,
                    template.parameters,
                    1 if template.is_system else 0,
                    1 if template.actif else 0
                )
            )

            # Recuperer l'ID cree
            cursor.execute("SELECT SCOPE_IDENTITY() as id")
            result = cursor.fetchone()
            new_id = result[0] if result else None

        return {
            "success": True,
            "message": "Template cree avec succes",
            "id": new_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] create_template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    template: DataSourceTemplateUpdate,
    x_user_role: str = Header(None, alias="X-User-Role"),
    x_user_id: str = Header(None, alias="X-User-Id")
):
    """Met a jour un template existant"""
    try:
        # Verifier que le template existe
        existing = execute_query(
            "SELECT id, is_system FROM APP_DataSources_Templates WHERE id = ?",
            (template_id,),
            use_cache=False
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Template non trouve")

        # Verification role pour templates systeme
        if existing[0].get('is_system') and x_user_role != "superadmin":
            raise HTTPException(status_code=403, detail="Seul un superadmin peut modifier les templates systeme")

        # Construire la requete de mise a jour
        updates = []
        params = []

        if template.nom is not None:
            updates.append("nom = ?")
            params.append(template.nom)
        if template.type is not None:
            updates.append("type = ?")
            params.append(template.type)
        if template.category is not None:
            updates.append("category = ?")
            params.append(template.category)
        if template.description is not None:
            updates.append("description = ?")
            params.append(template.description)
        if template.query_template is not None:
            updates.append("query_template = ?")
            params.append(template.query_template)
        if template.parameters is not None:
            updates.append("parameters = ?")
            params.append(template.parameters)
        if template.is_system is not None and x_user_role == "superadmin":
            updates.append("is_system = ?")
            params.append(1 if template.is_system else 0)
        if template.actif is not None:
            updates.append("actif = ?")
            params.append(1 if template.actif else 0)

        if not updates:
            return {"success": True, "message": "Aucune modification"}

        params.append(template_id)

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE APP_DataSources_Templates SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

        return {
            "success": True,
            "message": "Template mis a jour avec succes"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] update_template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/id/{template_id}")
async def delete_template(
    template_id: int,
    x_user_role: str = Header(None, alias="X-User-Role")
):
    """Supprime un template"""
    try:
        # Verifier que le template existe
        existing = execute_query(
            "SELECT id, is_system, code FROM APP_DataSources_Templates WHERE id = ?",
            (template_id,),
            use_cache=False
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Template non trouve")

        # Verification role pour templates systeme
        if existing[0].get('is_system') and x_user_role != "superadmin":
            raise HTTPException(status_code=403, detail="Seul un superadmin peut supprimer les templates systeme")

        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_DataSources_Templates WHERE id = ?", (template_id,))

        return {
            "success": True,
            "message": f"Template '{existing[0].get('code')}' supprime avec succes"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] delete_template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OVERRIDES (Base DWH client - pour future implementation)
# =============================================================================

@router.get("/overrides")
async def get_overrides(
    x_dwh_code: str = Header(None, alias="X-DWH-Code")
):
    """Liste les overrides de datasources pour un DWH specifique"""
    # Pour l'instant, retourne une liste vide car les overrides sont par DWH
    # Cette fonctionnalite sera implementee quand on aura le contexte DWH
    return {
        "success": True,
        "data": [],
        "message": "Les overrides sont specifiques par DWH client"
    }


# =============================================================================
# TEST DE REQUETE
# =============================================================================

# =============================================================================
# ROUTE UNIFIEE POUR LES BUILDERS (Templates + Sources locales)
# =============================================================================

@router.get("/unified")
async def get_unified_datasources(
    category: Optional[str] = Query(None, description="Filtrer par categorie"),
    search: Optional[str] = Query(None, description="Recherche par code ou nom"),
    include_local: bool = Query(True, description="Inclure les sources locales APP_DataSources")
):
    """
    Liste unifiee des DataSources pour les Builders (Dashboard, Pivot, GridView).

    Combine:
    1. APP_DataSources_Templates (templates centraux) - prioritaires
    2. APP_DataSources (sources locales) - si include_local=True

    Retourne une liste avec un champ 'origin' pour distinguer la source.
    """
    try:
        result = []
        seen_codes = set()

        # 1. D'abord les templates (prioritaires)
        template_query = """
            SELECT
                id, code, nom, type, category, description,
                query_template, parameters, is_system, actif,
                'template' as origin
            FROM APP_DataSources_Templates
            WHERE actif = 1
        """
        template_params = []

        if category:
            template_query += " AND LOWER(category) = LOWER(?)"
            template_params.append(category)

        if search:
            template_query += " AND (code LIKE ? OR nom LIKE ?)"
            template_params.extend([f"%{search}%", f"%{search}%"])

        template_query += " ORDER BY category, nom"

        templates = execute_query(template_query, tuple(template_params) if template_params else None, use_cache=False)

        for t in templates:
            t['origin'] = 'template'
            t['origin_label'] = 'Template'
            t['can_edit'] = False  # Les templates ne sont pas editables directement
            result.append(t)
            if t.get('code'):
                seen_codes.add(t['code'])

        # 2. Ensuite les sources locales (si pas deja un template avec le meme code)
        if include_local:
            local_query = """
                SELECT
                    id, nom, type, description,
                    query_template, parameters,
                    'local' as origin
                FROM APP_DataSources
            """
            local_params = []

            if search:
                local_query += " WHERE (nom LIKE ?)"
                local_params.append(f"%{search}%")

            local_query += " ORDER BY nom"

            local_sources = execute_query(local_query, tuple(local_params) if local_params else None, use_cache=False)

            for s in local_sources:
                # Generer un code si absent
                s['code'] = s.get('code') or f"LOCAL_{s['id']}"
                s['category'] = s.get('category') or 'custom'
                s['origin'] = 'local'
                s['origin_label'] = 'Source Locale'
                s['can_edit'] = True
                s['is_system'] = False
                s['actif'] = True

                # Ne pas ajouter si un template avec le meme code existe
                if s['code'] not in seen_codes:
                    result.append(s)

        # Grouper par categorie pour le frontend
        categories = {}
        for ds in result:
            cat = ds.get('category') or 'Autre'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ds)

        return {
            "success": True,
            "data": result,
            "total": len(result),
            "categories": {k: len(v) for k, v in categories.items()},
            "grouped": categories
        }
    except Exception as e:
        print(f"[ERROR] get_unified_datasources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/{identifier}")
async def get_unified_datasource(
    identifier: str,
    x_dwh_code: str = Header(None, alias="X-DWH-Code")
):
    """
    Recupere une DataSource par ID ou code.

    - Si identifier est numerique: cherche par ID (d'abord local, puis template)
    - Si identifier est une chaine: cherche par code (d'abord template, puis local)
    """
    from ..services.parameter_resolver import extract_parameters_from_query

    try:
        datasource = None
        origin = None

        # Determiner si c'est un ID ou un code
        is_numeric = identifier.isdigit()

        if is_numeric:
            ds_id = int(identifier)

            # Chercher d'abord dans les sources locales
            local = execute_query(
                "SELECT * FROM APP_DataSources WHERE id = ?",
                (ds_id,),
                use_cache=False
            )
            if local:
                datasource = local[0]
                datasource['origin'] = 'local'
                datasource['code'] = datasource.get('code') or f"LOCAL_{ds_id}"
                datasource['category'] = datasource.get('category') or 'custom'
            else:
                # Chercher dans les templates
                template = execute_query(
                    "SELECT * FROM APP_DataSources_Templates WHERE id = ?",
                    (ds_id,),
                    use_cache=False
                )
                if template:
                    datasource = template[0]
                    datasource['origin'] = 'template'
        else:
            # Chercher par code - d'abord templates (prioritaires)
            template = execute_query(
                "SELECT * FROM APP_DataSources_Templates WHERE code = ? AND actif = 1",
                (identifier,),
                use_cache=False
            )
            if template:
                datasource = template[0]
                datasource['origin'] = 'template'
            else:
                # Chercher dans les sources locales par nom
                local = execute_query(
                    "SELECT * FROM APP_DataSources WHERE nom = ?",
                    (identifier,),
                    use_cache=False
                )
                if local:
                    datasource = local[0]
                    datasource['origin'] = 'local'
                    datasource['code'] = datasource.get('code') or f"LOCAL_{datasource['id']}"

        if not datasource:
            raise HTTPException(status_code=404, detail=f"DataSource '{identifier}' non trouvee")

        # Parser les parametres si c'est une chaine JSON
        if datasource.get('parameters'):
            try:
                import json
                if isinstance(datasource['parameters'], str):
                    datasource['parameters'] = json.loads(datasource['parameters'])
            except:
                datasource['parameters'] = []
        else:
            datasource['parameters'] = []

        # Extraire les parametres de la requete si non definis
        if not datasource['parameters'] and datasource.get('query_template'):
            datasource['extracted_params'] = extract_parameters_from_query(datasource['query_template'])

        return {
            "success": True,
            "data": datasource
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] get_unified_datasource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unified/{identifier}/preview")
async def preview_unified_datasource(
    identifier: str,
    body: dict = {},
    x_dwh_code: str = Header(None, alias="X-DWH-Code")
):
    """
    Execute une DataSource (template ou locale) avec les parametres fournis.
    - limit=0 => pas de limite (viewer mode, toutes les donnees)
    - limit=100 (defaut) => mode builder/preview
    """
    from ..services.parameter_resolver import inject_params
    from ..database_unified import current_dwh_code as _ctx_dwh

    # Fallback: utiliser le ContextVar injecté par TenantContextMiddleware (DWH_CODE .env)
    effective_header_dwh = x_dwh_code or _ctx_dwh.get()

    try:
        context = body.get('context', {})
        limit = body.get('limit', 100)

        # Recuperer la datasource
        ds_response = await get_unified_datasource(identifier, effective_header_dwh)
        datasource = ds_response['data']

        query = datasource.get('query_template', '')
        if not query:
            raise HTTPException(status_code=400, detail="Aucune requete definie")

        # Injecter les parametres
        final_query = inject_params(query, context)

        # Ajouter TOP si absent (sauf si limit=0 => pas de limite = viewer mode)
        if limit and limit > 0 and "SELECT" in final_query.upper() and "TOP" not in final_query.upper():
            final_query = final_query.replace("SELECT", f"SELECT TOP {limit}", 1)

        # Executer sur le bon DWH (avec cache pour eviter les requetes redondantes)
        effective_dwh = effective_header_dwh
        if not effective_dwh and datasource.get('origin') == 'template':
            try:
                dwh_list = execute_query(
                    "SELECT TOP 1 code FROM APP_DWH WHERE actif = 1 ORDER BY id",
                    use_cache=True
                )
                if dwh_list:
                    effective_dwh = dwh_list[0]['code']
            except Exception:
                pass

        if effective_dwh:
            results = DWHConnectionManager.execute_dwh_query(effective_dwh, final_query, use_cache=False)
        else:
            results = execute_query(final_query, use_cache=False)

        # Extraire les colonnes
        columns = []
        if results:
            for key, value in results[0].items():
                col_type = "text"
                if isinstance(value, (int, float)):
                    col_type = "number"
                columns.append({"name": key, "type": col_type})

        return {
            "success": True,
            "data": results if (not limit or limit <= 0) else results[:limit],
            "columns": columns,
            "total": len(results),
            "origin": datasource.get('origin'),
            "executed_query": final_query
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] preview_unified_datasource: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "columns": []
        }


@router.get("/unified/{identifier}/fields")
async def get_unified_datasource_fields(
    identifier: str,
    x_dwh_code: str = Header(None, alias="X-DWH-Code")
):
    """
    Recupere les champs (colonnes) d'une DataSource en executant la requete avec LIMIT 1.
    """
    from ..services.parameter_resolver import inject_params

    try:
        # Recuperer la datasource
        ds_response = await get_unified_datasource(identifier, x_dwh_code)
        datasource = ds_response['data']

        query = datasource.get('query_template', '')
        if not query:
            return {"success": True, "fields": []}

        # Injecter les parametres avec valeurs par defaut
        from ..services.parameter_resolver import get_default_context
        default_ctx = get_default_context()
        query = inject_params(query, default_ctx)

        # Envelopper dans SELECT TOP 1 pour forcer la limite
        import re
        query = re.sub(r'\s+ORDER\s+BY\s+[\s\S]+$', '', query, flags=re.IGNORECASE)
        query = f"SELECT TOP 1 * FROM ({query}) AS __fields__"

        # Executer sur le bon DWH (meme pattern que preview_unified_datasource)
        if x_dwh_code:
            results = DWHConnectionManager.execute_dwh_query(x_dwh_code, query, use_cache=False)
        else:
            results = execute_query(query, use_cache=False)

        if results:
            from decimal import Decimal
            from datetime import datetime, date
            fields = []
            for key, value in results[0].items():
                field_type = "text"
                if isinstance(value, bool):
                    field_type = "boolean"
                elif isinstance(value, (int, float, Decimal)):
                    field_type = "number"
                elif isinstance(value, (datetime, date)):
                    field_type = "date"
                fields.append({"name": key, "type": field_type})
            return {"success": True, "fields": fields}

        return {"success": True, "fields": []}
    except Exception as e:
        print(f"[ERROR] get_unified_datasource_fields: {e}")
        return {"success": False, "error": str(e), "fields": []}


@router.get("/dwh-filter-options")
async def get_dwh_filter_options(
    field: str = Query(..., description="Champ à lister: societe, commercial, gamme, zone"),
    x_dwh_code: Optional[str] = Header(None, alias="X-DWH-Code")
):
    """
    Retourne les valeurs distinctes d'un champ depuis les données DWH.
    Utilisé pour alimenter les filtres globaux (GlobalFilterBar).
    """
    from ..database_unified import current_dwh_code as _ctx_dwh

    effective_dwh = x_dwh_code or _ctx_dwh.get()
    if not effective_dwh:
        return {"success": False, "error": "DWH code manquant", "data": []}

    # Mapping champ → colonne dans Lignes_des_ventes
    field_map = {
        "societe":    "[societe]",
        "commercial": "[Représentant]",
        "gamme":      "[Catalogue 1]",
        "zone":       "[Souche]",
    }
    column = field_map.get(field)
    if not column:
        raise HTTPException(status_code=400, detail=f"Champ non supporté: {field}. Valeurs: {list(field_map.keys())}")

    query = f"SELECT DISTINCT {column} AS value, {column} AS label FROM Lignes_des_ventes WHERE {column} IS NOT NULL ORDER BY {column}"

    try:
        results = DWHConnectionManager.execute_dwh_query(effective_dwh, query, use_cache=False)
        return {"success": True, "data": results}
    except Exception as e:
        print(f"[ERROR] get_dwh_filter_options ({field}, {effective_dwh}): {e}")
        return {"success": False, "error": str(e), "data": []}


@router.post("/execute/test")
async def test_query(
    body: dict,
    x_user_role: str = Header(None, alias="X-User-Role")
):
    """Teste une requete SQL avec des parametres"""
    try:
        query = body.get("query", "")
        params = body.get("parameters", {})
        limit = body.get("limit", 10)

        if not query:
            raise HTTPException(status_code=400, detail="Requete vide")

        # Securite: verification basique
        query_lower = query.lower().strip()
        if any(kw in query_lower for kw in ['drop ', 'delete ', 'truncate ', 'insert ', 'update ', 'alter ', 'create ']):
            raise HTTPException(status_code=403, detail="Operations de modification non autorisees en mode test")

        # Remplacer les parametres @param par des valeurs de test (format dates sécurisé)
        from ..services.parameter_resolver import inject_params
        test_query = inject_params(query, params)

        # Ajouter TOP pour limiter les resultats
        if "SELECT" in test_query.upper() and "TOP" not in test_query.upper():
            test_query = test_query.replace("SELECT", f"SELECT TOP {limit}", 1)

        # Executer la requete
        results = execute_query(test_query, use_cache=False)

        # Extraire les colonnes
        columns = list(results[0].keys()) if results else []

        return {
            "success": True,
            "data": results[:limit],
            "rowCount": len(results),
            "columns": columns,
            "query_executed": test_query[:500] + "..." if len(test_query) > 500 else test_query
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] test_query: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "rowCount": 0,
            "columns": []
        }
