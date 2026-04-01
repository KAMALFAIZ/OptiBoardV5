"""
Service de Resolution des DataSources Multi-Tenant
===================================================
Implemente le pattern Template -> Override pour la resolution des sources de donnees:
1. Chercher d'abord dans APP_DataSources du DWH client (override custom)
2. Si non trouve, chercher dans APP_DataSources_Templates de la base centrale
3. Appliquer la resolution des parametres avec le contexte utilisateur
"""

from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Import unifie multi-tenant
from ..database_unified import (
    execute_app as _execute_standard_query,
    app_cursor as get_db_cursor,
    execute_central as _execute_central_mt,
    execute_dwh_query,
    write_dwh as _write_dwh_func,
    UserContext,
    build_societe_filter
)
MULTITENANT_ENABLED = True

def execute_dwh_write(dwh_code, query, params=None):
    """Wrapper pour write_dwh avec ancienne signature"""
    return _write_dwh_func(query, params, dwh_code=dwh_code)


def execute_central_query(query, params=None, use_cache=True):
    """Execute sur la base centrale avec fallback automatique sur la base standard"""
    if MULTITENANT_ENABLED:
        try:
            return _execute_central_mt(query, params, use_cache=use_cache)
        except Exception as e:
            # Fallback si base centrale non configuree
            logger_init = logging.getLogger("DataSourceResolver")
            logger_init.debug(f"Fallback sur base standard: {e}")
            return _execute_standard_query(query, params, use_cache=use_cache)
    return _execute_standard_query(query, params, use_cache=use_cache)

from .parameter_resolver import inject_params, extract_parameters_from_query

logger = logging.getLogger("DataSourceResolver")


class DataSourceOrigin(Enum):
    """Origine de la DataSource resolue"""
    TEMPLATE = "template"      # Depuis APP_DataSources_Templates (centrale)
    OVERRIDE = "override"      # Depuis APP_DataSources (DWH client)
    NOT_FOUND = "not_found"


@dataclass
class ResolvedDataSource:
    """DataSource resolue avec toutes ses informations"""
    id: Optional[int]
    code: str
    nom: str
    description: Optional[str]
    query_template: str
    parameters: Optional[str]  # JSON
    category: Optional[str]
    origin: DataSourceOrigin
    is_system: bool = False
    is_custom: bool = False
    dwh_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "nom": self.nom,
            "description": self.description,
            "query_template": self.query_template,
            "parameters": self.parameters,
            "category": self.category,
            "origin": self.origin.value,
            "is_system": self.is_system,
            "is_custom": self.is_custom,
            "dwh_code": self.dwh_code
        }


class DataSourceResolver:
    """
    Resolveur de DataSources avec pattern Template -> Override

    Flux de resolution:
    1. Si dwh_code fourni: chercher dans APP_DataSources du DWH (override)
    2. Si non trouve ou pas de dwh_code: chercher dans APP_DataSources_Templates (centrale)
    3. Retourner la DataSource avec son origine
    """

    def __init__(self):
        self._cache = {}  # Cache simple en memoire
        self._cache_ttl = 300  # 5 minutes

    def resolve_by_code(
        self,
        datasource_code: str,
        dwh_code: Optional[str] = None
    ) -> ResolvedDataSource:
        """
        Resout une DataSource par son code avec fallback Template -> Override

        Args:
            datasource_code: Code unique de la DataSource (ex: DS_VENTES_PAR_CLIENT)
            dwh_code: Code du DWH client (optionnel, pour chercher les overrides)

        Returns:
            ResolvedDataSource avec l'origine (OVERRIDE ou TEMPLATE)

        Raises:
            ValueError si la DataSource n'est pas trouvee
        """
        # Etape 1: Chercher dans le DWH client (override)
        if dwh_code:
            override = self._find_in_dwh(datasource_code, dwh_code)
            if override:
                logger.debug(f"DataSource '{datasource_code}' trouvee en override pour DWH '{dwh_code}'")
                return override

        # Etape 2: Chercher dans les templates centraux
        template = self._find_in_templates(datasource_code)
        if template:
            logger.debug(f"DataSource '{datasource_code}' trouvee dans les templates centraux")
            return template

        # Non trouve
        logger.warning(f"DataSource '{datasource_code}' non trouvee (dwh_code={dwh_code})")
        raise ValueError(f"DataSource '{datasource_code}' non trouvee")

    def resolve_by_id(
        self,
        datasource_id: int,
        dwh_code: Optional[str] = None
    ) -> ResolvedDataSource:
        """
        Resout une DataSource par son ID

        Args:
            datasource_id: ID de la DataSource
            dwh_code: Code du DWH (pour savoir ou chercher)

        Returns:
            ResolvedDataSource
        """
        # Chercher d'abord dans le DWH si fourni
        if dwh_code:
            override = self._find_by_id_in_dwh(datasource_id, dwh_code)
            if override:
                return override

        # Chercher dans les templates
        template = self._find_by_id_in_templates(datasource_id)
        if template:
            return template

        raise ValueError(f"DataSource ID={datasource_id} non trouvee")

    def resolve_with_context(
        self,
        datasource_code: str,
        user_context: UserContext,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[ResolvedDataSource, str]:
        """
        Resout une DataSource et prepare la requete avec le contexte utilisateur

        Args:
            datasource_code: Code de la DataSource
            user_context: Contexte utilisateur (contient dwh_code, societes, etc.)
            extra_params: Parametres supplementaires a injecter

        Returns:
            Tuple (ResolvedDataSource, requete_preparee)
        """
        # Resoudre la DataSource
        datasource = self.resolve_by_code(datasource_code, user_context.current_dwh_code)

        # Construire le contexte de parametres
        params = self._build_params_context(user_context, extra_params)

        # Injecter les parametres dans la requete
        prepared_query = inject_params(datasource.query_template, params)

        # Ajouter le filtre societe si necessaire
        prepared_query = self._inject_societe_filter(prepared_query, user_context)

        return datasource, prepared_query

    def list_available(
        self,
        dwh_code: Optional[str] = None,
        category: Optional[str] = None,
        include_templates: bool = True
    ) -> List[ResolvedDataSource]:
        """
        Liste toutes les DataSources disponibles (templates + overrides)

        Args:
            dwh_code: Code DWH pour inclure les overrides
            category: Filtrer par categorie
            include_templates: Inclure les templates centraux

        Returns:
            Liste de DataSources resolues
        """
        result = []
        seen_codes = set()

        # 1. D'abord les overrides du DWH (prioritaires)
        if dwh_code:
            overrides = self._list_dwh_datasources(dwh_code, category)
            for ds in overrides:
                result.append(ds)
                seen_codes.add(ds.code)

        # 2. Ensuite les templates (si pas deja override)
        if include_templates:
            templates = self._list_template_datasources(category)
            for ds in templates:
                if ds.code not in seen_codes:
                    result.append(ds)

        return result

    def create_override(
        self,
        template_code: str,
        dwh_code: str,
        custom_query: Optional[str] = None,
        custom_params: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> int:
        """
        Cree un override d'un template pour un DWH specifique

        Args:
            template_code: Code du template a overrider
            dwh_code: Code du DWH cible
            custom_query: Requete personnalisee (optionnel)
            custom_params: Parametres personnalises JSON (optionnel)
            created_by: ID de l'utilisateur createur

        Returns:
            ID de l'override cree
        """
        # Recuperer le template
        template = self._find_in_templates(template_code)
        if not template:
            raise ValueError(f"Template '{template_code}' non trouve")

        # Verifier si un override existe deja
        existing = self._find_in_dwh(template_code, dwh_code)
        if existing:
            raise ValueError(f"Un override existe deja pour '{template_code}' dans le DWH '{dwh_code}'")

        # Creer l'override
        query = """
            INSERT INTO APP_DataSources
            (template_code, nom, code, type, category, description, query_template, parameters, is_custom, created_by, actif)
            VALUES (?, ?, ?, 'query', ?, ?, ?, ?, 1, ?, 1)
        """
        params = (
            template_code,
            template.nom,
            template.code,
            template.category,
            template.description,
            custom_query or template.query_template,
            custom_params or template.parameters,
            created_by
        )

        execute_dwh_write(dwh_code, query, params)

        # Recuperer l'ID cree
        result = execute_dwh_query(
            dwh_code,
            "SELECT MAX(id) as id FROM APP_DataSources WHERE code = ?",
            (template_code,),
            use_cache=False
        )

        return result[0]["id"] if result else 0

    # =========================================================================
    # METHODES PRIVEES
    # =========================================================================

    def _find_in_dwh(self, code: str, dwh_code: str) -> Optional[ResolvedDataSource]:
        """Cherche une DataSource dans le DWH client"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, template_code, is_custom, created_by
                FROM APP_DataSources
                WHERE code = ? AND actif = 1
            """
            results = execute_dwh_query(dwh_code, query, (code,), use_cache=True)

            if results:
                row = results[0]
                return ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.OVERRIDE,
                    is_system=False,
                    is_custom=bool(row.get("is_custom")),
                    dwh_code=dwh_code
                )
        except Exception as e:
            logger.warning(f"Erreur recherche DataSource dans DWH {dwh_code}: {e}")

        return None

    def _find_in_templates(self, code: str) -> Optional[ResolvedDataSource]:
        """Cherche une DataSource dans les templates centraux"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, is_system
                FROM APP_DataSources_Templates
                WHERE code = ? AND actif = 1
            """
            results = execute_central_query(query, (code,), use_cache=True)

            if results:
                row = results[0]
                return ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.TEMPLATE,
                    is_system=bool(row.get("is_system")),
                    is_custom=False,
                    dwh_code=None
                )
        except Exception as e:
            logger.warning(f"Erreur recherche DataSource dans templates: {e}")

        return None

    def _find_by_id_in_dwh(self, ds_id: int, dwh_code: str) -> Optional[ResolvedDataSource]:
        """Cherche une DataSource par ID dans le DWH"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, template_code, is_custom
                FROM APP_DataSources
                WHERE id = ? AND actif = 1
            """
            results = execute_dwh_query(dwh_code, query, (ds_id,), use_cache=True)

            if results:
                row = results[0]
                return ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.OVERRIDE,
                    is_system=False,
                    is_custom=bool(row.get("is_custom")),
                    dwh_code=dwh_code
                )
        except Exception as e:
            logger.warning(f"Erreur recherche DataSource ID={ds_id} dans DWH: {e}")

        return None

    def _find_by_id_in_templates(self, ds_id: int) -> Optional[ResolvedDataSource]:
        """Cherche une DataSource par ID dans les templates"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, is_system
                FROM APP_DataSources_Templates
                WHERE id = ? AND actif = 1
            """
            results = execute_central_query(query, (ds_id,), use_cache=True)

            if results:
                row = results[0]
                return ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.TEMPLATE,
                    is_system=bool(row.get("is_system")),
                    is_custom=False,
                    dwh_code=None
                )
        except Exception as e:
            logger.warning(f"Erreur recherche DataSource ID={ds_id} dans templates: {e}")

        return None

    def _list_dwh_datasources(
        self,
        dwh_code: str,
        category: Optional[str] = None
    ) -> List[ResolvedDataSource]:
        """Liste les DataSources d'un DWH"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, template_code, is_custom
                FROM APP_DataSources
                WHERE actif = 1
            """
            params = ()

            if category:
                query += " AND category = ?"
                params = (category,)

            query += " ORDER BY category, nom"

            results = execute_dwh_query(dwh_code, query, params if params else None, use_cache=True)

            return [
                ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.OVERRIDE,
                    is_system=False,
                    is_custom=bool(row.get("is_custom")),
                    dwh_code=dwh_code
                )
                for row in results
            ]
        except Exception as e:
            logger.warning(f"Erreur liste DataSources DWH {dwh_code}: {e}")
            return []

    def _list_template_datasources(
        self,
        category: Optional[str] = None
    ) -> List[ResolvedDataSource]:
        """Liste les templates de DataSources"""
        try:
            query = """
                SELECT id, code, nom, description, query_template, parameters,
                       category, is_system
                FROM APP_DataSources_Templates
                WHERE actif = 1
            """
            params = ()

            if category:
                query += " AND category = ?"
                params = (category,)

            query += " ORDER BY category, nom"

            results = execute_central_query(query, params if params else None, use_cache=True)

            return [
                ResolvedDataSource(
                    id=row.get("id"),
                    code=row.get("code"),
                    nom=row.get("nom"),
                    description=row.get("description"),
                    query_template=row.get("query_template"),
                    parameters=row.get("parameters"),
                    category=row.get("category"),
                    origin=DataSourceOrigin.TEMPLATE,
                    is_system=bool(row.get("is_system")),
                    is_custom=False,
                    dwh_code=None
                )
                for row in results
            ]
        except Exception as e:
            logger.warning(f"Erreur liste templates DataSources: {e}")
            return []

    def _build_params_context(
        self,
        user_context: UserContext,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Construit le contexte de parametres depuis le contexte utilisateur"""
        params = {
            "dwh_code": user_context.current_dwh_code,
            "user_id": user_context.user_id,
            "username": user_context.username,
        }

        # Ajouter les societes accessibles
        societes = user_context.get_societe_filter()
        if societes:
            params["societe"] = societes[0] if len(societes) == 1 else ",".join(societes)
            params["societes"] = societes

        # Fusionner avec les params supplementaires
        if extra_params:
            params.update(extra_params)

        return params

    def _inject_societe_filter(self, query: str, user_context: UserContext) -> str:
        """
        Injecte le filtre societe dans la requete si necessaire

        Cherche @societe_filter ou @societes et les remplace par la clause appropriee
        """
        societes = user_context.get_societe_filter()

        if not societes:
            # Pas de filtre - remplacer par 1=1
            query = query.replace("@societe_filter", "1=1")
            query = query.replace("AND societe_code IN (@societes)", "")
            query = query.replace("WHERE societe_code IN (@societes)", "WHERE 1=1")
            return query

        # Construire la clause IN
        if len(societes) == 1:
            filter_clause = f"societe_code = '{societes[0]}'"
            in_clause = f"'{societes[0]}'"
        else:
            escaped = [s.replace("'", "''") for s in societes]
            quoted = ["'" + s + "'" for s in escaped]
            filter_clause = "societe_code IN (" + ",".join(quoted) + ")"
            in_clause = ",".join(quoted)

        query = query.replace("@societe_filter", filter_clause)
        query = query.replace("@societes", in_clause)

        return query


# Instance globale du resolver
datasource_resolver = DataSourceResolver()


# =========================================================================
# FONCTIONS UTILITAIRES EXPORTEES
# =========================================================================

def resolve_datasource(
    code_or_id: Union[str, int],
    dwh_code: Optional[str] = None
) -> ResolvedDataSource:
    """
    Fonction utilitaire pour resoudre une DataSource

    Args:
        code_or_id: Code ou ID de la DataSource
        dwh_code: Code du DWH (optionnel)

    Returns:
        ResolvedDataSource
    """
    if isinstance(code_or_id, int):
        return datasource_resolver.resolve_by_id(code_or_id, dwh_code)
    return datasource_resolver.resolve_by_code(code_or_id, dwh_code)


def get_datasource_query(
    code_or_id: Union[str, int],
    user_context: UserContext,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Recupere la requete preparee d'une DataSource avec le contexte

    Args:
        code_or_id: Code ou ID de la DataSource
        user_context: Contexte utilisateur
        params: Parametres supplementaires

    Returns:
        Requete SQL preparee
    """
    if isinstance(code_or_id, int):
        ds = datasource_resolver.resolve_by_id(code_or_id, user_context.current_dwh_code)
    else:
        ds = datasource_resolver.resolve_by_code(code_or_id, user_context.current_dwh_code)

    # Construire les params complets
    full_params = datasource_resolver._build_params_context(user_context, params)

    # Injecter les parametres
    query = inject_params(ds.query_template, full_params)

    # Injecter le filtre societe
    query = datasource_resolver._inject_societe_filter(query, user_context)

    return query


def list_datasources(
    dwh_code: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Liste les DataSources disponibles

    Args:
        dwh_code: Code du DWH pour les overrides
        category: Filtrer par categorie

    Returns:
        Liste de dictionnaires
    """
    sources = datasource_resolver.list_available(dwh_code, category)
    return [ds.to_dict() for ds in sources]
