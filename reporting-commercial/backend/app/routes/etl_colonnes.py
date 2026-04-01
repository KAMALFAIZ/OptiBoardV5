"""
ETL Colonnes — Gestion des colonnes du catalogue et choix client
================================================================
Architecture :
  CENTRAL  : APP_ETL_Tables_Colonnes  — colonnes officielles par table Sage
             Le superadmin definit quelles colonnes existent, lesquelles
             sont obligatoires, et leur type.

  CLIENT   : APP_ETL_Published_Colonnes — colonnes choisies par le client
             Le client decide quelles colonnes optionnelles il inclut
             et peut definir un alias d'affichage.

Logique metier :
  - Colonnes obligatoires  (obligatoire=1) : toujours incluses, le client ne peut PAS exclure
  - Colonnes optionnelles  (obligatoire=0) : le client choisit inclus=1 ou inclus=0
  - Publication            : quand le central publie une table ETL, il publie
                             aussi ses colonnes vers APP_ETL_Published_Colonnes du client
  - MAJ colonne            : nouvelle colonne ajoutee au central → proposee au client
                             colonne obligatoire → automatiquement ajoutee chez le client
"""
import logging
import pyodbc
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel

from ..database_unified import (
    execute_central, write_central, central_cursor,
    execute_client, write_client, client_cursor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/etl-colonnes", tags=["ETL Colonnes"])


# ============================================================
# Schemas Pydantic
# ============================================================

class ColonneCreate(BaseModel):
    nom_colonne: str
    type_donnee: str                       # VARCHAR, INT, DECIMAL, DATE, BIT...
    longueur: Optional[int] = None
    description: Optional[str] = None
    obligatoire: bool = False              # True = client ne peut pas exclure
    visible_client: bool = True            # False = colonne interne, non affichee
    valeur_defaut: Optional[str] = None

class ColonneUpdate(BaseModel):
    type_donnee: Optional[str] = None
    longueur: Optional[int] = None
    description: Optional[str] = None
    obligatoire: Optional[bool] = None
    visible_client: Optional[bool] = None
    valeur_defaut: Optional[str] = None
    actif: Optional[bool] = None

class ColonneClientToggle(BaseModel):
    inclus: bool
    alias: Optional[str] = None           # Nom d'affichage personnalise


# ============================================================
# HELPERS
# ============================================================

def _build_client_conn_str(client_info: Dict) -> str:
    from ..config_multitenant import get_central_settings
    central = get_central_settings()
    server   = client_info.get('db_server')   or central._effective_server
    db_name  = client_info.get('db_name')     or ''
    user     = client_info.get('db_user')     or central._effective_user
    password = client_info.get('db_password') or central._effective_password
    return (
        f"DRIVER={central._effective_driver};"
        f"SERVER={server};DATABASE={db_name};UID={user};PWD={password};"
        "TrustServerCertificate=yes;"
    )


def _get_client_info(dwh_code: str) -> Optional[Dict]:
    """Recupere les infos de connexion d'un client depuis la base centrale."""
    rows = execute_central(
        """SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
           FROM APP_DWH d
           LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
           WHERE d.code = ? AND d.actif = 1""",
        (dwh_code,), use_cache=False
    )
    return rows[0] if rows else None


def _publish_colonnes_to_client(table_code: str, colonnes: List[Dict], client: Dict) -> Dict:
    """
    Publie les colonnes d'une table ETL vers un client.
    Logique :
      - Colonnes obligatoires → INSERT ou UPDATE (ne peut pas etre exclu)
      - Colonnes optionnelles deja chez le client → mise a jour des metadonnees SANS changer inclus
      - Nouvelles colonnes optionnelles → INSERT avec inclus=1 (par defaut inclus)
    """
    try:
        conn_str = _build_client_conn_str(client)
        conn = pyodbc.connect(conn_str, timeout=15)
        conn.autocommit = False
        cursor = conn.cursor()

        inserted = 0
        updated = 0

        for col in colonnes:
            cursor.execute(
                "SELECT id, inclus FROM APP_ETL_Published_Colonnes WHERE table_code = ? AND nom_colonne = ?",
                (table_code, col['nom_colonne'])
            )
            existing = cursor.fetchone()

            if existing:
                # UPDATE — ne pas changer inclus sauf si colonne obligatoire
                if col.get('obligatoire'):
                    cursor.execute(
                        """UPDATE APP_ETL_Published_Colonnes SET
                             type_donnee = ?, longueur = ?, obligatoire = 1,
                             inclus = 1, version_ajout = ?
                           WHERE table_code = ? AND nom_colonne = ?""",
                        (col['type_donnee'], col.get('longueur'), col.get('version_ajout', 1),
                         table_code, col['nom_colonne'])
                    )
                else:
                    # Mettre a jour metadonnees seulement, pas inclus
                    cursor.execute(
                        """UPDATE APP_ETL_Published_Colonnes SET
                             type_donnee = ?, longueur = ?,
                             obligatoire = ?, version_ajout = ?
                           WHERE table_code = ? AND nom_colonne = ?""",
                        (col['type_donnee'], col.get('longueur'),
                         1 if col.get('obligatoire') else 0,
                         col.get('version_ajout', 1),
                         table_code, col['nom_colonne'])
                    )
                updated += 1
            else:
                # INSERT — nouvelle colonne
                cursor.execute(
                    """INSERT INTO APP_ETL_Published_Colonnes
                         (table_code, nom_colonne, type_donnee, longueur,
                          inclus, obligatoire, version_ajout)
                       VALUES (?, ?, ?, ?, 1, ?, ?)""",
                    (table_code, col['nom_colonne'], col['type_donnee'],
                     col.get('longueur'),
                     1 if col.get('obligatoire') else 0,
                     col.get('version_ajout', 1))
                )
                inserted += 1

        conn.commit()
        conn.close()
        return {"success": True, "inserted": inserted, "updated": updated}

    except Exception as e:
        logger.error(f"Erreur publication colonnes {table_code} -> {client.get('code')}: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# ROUTES CENTRAL — Gestion colonnes catalogue
# ============================================================

@router.get("/central/{table_code}")
async def list_central_colonnes(
    table_code: str,
    actif: Optional[bool] = Query(None)
):
    """[CENTRAL] Liste les colonnes officielles d'une table du catalogue ETL."""
    try:
        query = "SELECT * FROM APP_ETL_Tables_Colonnes WHERE etl_table_code = ?"
        params = [table_code]
        if actif is not None:
            query += " AND actif = ?"
            params.append(1 if actif else 0)
        query += " ORDER BY obligatoire DESC, nom_colonne"
        colonnes = execute_central(query, tuple(params), use_cache=False)
        return {"success": True, "data": colonnes, "count": len(colonnes)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0,
                    "warning": "APP_ETL_Tables_Colonnes non initialisee. Executez 001_central_schema.sql"}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/central/{table_code}")
async def add_central_colonne(table_code: str, col: ColonneCreate):
    """[CENTRAL] Ajoute une colonne au catalogue d'une table ETL."""
    try:
        # Recuperer la version actuelle de la table
        tables = execute_central(
            "SELECT version FROM APP_ETL_Tables_Config WHERE code = ?",
            (table_code,), use_cache=False
        )
        if not tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_code}' introuvable dans le catalogue")
        version = tables[0]['version']

        with central_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_ETL_Tables_Colonnes
                     (etl_table_code, nom_colonne, type_donnee, longueur, description,
                      obligatoire, visible_client, valeur_defaut, version_ajout, actif)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (table_code, col.nom_colonne, col.type_donnee, col.longueur,
                 col.description, 1 if col.obligatoire else 0,
                 1 if col.visible_client else 0,
                 col.valeur_defaut, version)
            )
            cursor.commit()
        return {"success": True, "message": f"Colonne '{col.nom_colonne}' ajoutee a '{table_code}'"}
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower() or "violation" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Colonne '{col.nom_colonne}' existe deja")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/central/{table_code}/{nom_colonne}")
async def update_central_colonne(table_code: str, nom_colonne: str, update: ColonneUpdate):
    """[CENTRAL] Met a jour une colonne du catalogue."""
    try:
        fields, params = [], []
        if update.type_donnee is not None:
            fields.append("type_donnee = ?"); params.append(update.type_donnee)
        if update.longueur is not None:
            fields.append("longueur = ?"); params.append(update.longueur)
        if update.description is not None:
            fields.append("description = ?"); params.append(update.description)
        if update.obligatoire is not None:
            fields.append("obligatoire = ?"); params.append(1 if update.obligatoire else 0)
        if update.visible_client is not None:
            fields.append("visible_client = ?"); params.append(1 if update.visible_client else 0)
        if update.valeur_defaut is not None:
            fields.append("valeur_defaut = ?"); params.append(update.valeur_defaut)
        if update.actif is not None:
            fields.append("actif = ?"); params.append(1 if update.actif else 0)

        if not fields:
            raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour")

        params.extend([table_code, nom_colonne])
        write_central(
            f"UPDATE APP_ETL_Tables_Colonnes SET {', '.join(fields)} WHERE etl_table_code = ? AND nom_colonne = ?",
            tuple(params)
        )
        return {"success": True, "message": f"Colonne '{nom_colonne}' mise a jour"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/central/{table_code}/{nom_colonne}")
async def delete_central_colonne(table_code: str, nom_colonne: str):
    """
    [CENTRAL] Supprime (desactive) une colonne du catalogue.
    Logique metier : on ne supprime pas physiquement, on desactive (actif=0)
    pour garder la trace et eviter de casser les bases clients existantes.
    """
    try:
        write_central(
            "UPDATE APP_ETL_Tables_Colonnes SET actif = 0 WHERE etl_table_code = ? AND nom_colonne = ?",
            (table_code, nom_colonne)
        )
        return {"success": True, "message": f"Colonne '{nom_colonne}' desactivee (pas supprimee physiquement)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/central/{table_code}/publish")
async def publish_colonnes_to_clients(
    table_code: str,
    dwh_codes: Optional[List[str]] = Query(None)
):
    """
    [CENTRAL] Publie les colonnes d'une table ETL vers les bases clients.
    - Si dwh_codes=None → tous les clients actifs qui ont cette table publiee.
    - Colonnes obligatoires → forcees inclus=1 chez tous les clients.
    - Nouvelles colonnes optionnelles → inclus=1 par defaut.
    """
    try:
        colonnes = execute_central(
            "SELECT * FROM APP_ETL_Tables_Colonnes WHERE etl_table_code = ? AND actif = 1",
            (table_code,), use_cache=False
        )
        if not colonnes:
            return {"success": False, "message": "Aucune colonne active pour cette table"}

        # Clients qui ont cette table publiee
        if dwh_codes:
            placeholders = ','.join(['?' for _ in dwh_codes])
            clients_query = f"""
                SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
                FROM APP_DWH d
                LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
                WHERE d.code IN ({placeholders}) AND d.actif = 1"""
            clients = execute_central(clients_query, tuple(dwh_codes), use_cache=False)
        else:
            clients = execute_central(
                """SELECT d.code, d.nom, c.db_name, c.db_server, c.db_user, c.db_password
                   FROM APP_DWH d
                   LEFT JOIN APP_ClientDB c ON d.code = c.dwh_code
                   WHERE d.actif = 1 AND c.actif = 1""",
                use_cache=False
            )

        results = {"published": 0, "failed": 0, "details": []}
        for client in clients:
            if not client.get('db_name'):
                continue
            res = _publish_colonnes_to_client(table_code, colonnes, client)
            if res['success']:
                results['published'] += 1
            else:
                results['failed'] += 1
                results['details'].append({"client": client['code'], "error": res.get('error')})

        return {"success": True, "results": results,
                "colonnes": len(colonnes), "clients": len(clients)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ROUTES CLIENT — Colonnes publiees (choix du client)
# ============================================================

@router.get("/client/{table_code}")
async def list_client_colonnes(
    table_code: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Liste les colonnes disponibles pour une table ETL publiee.
    Retourne toutes les colonnes avec leur statut inclus/exclu.
    Les colonnes obligatoires ont toujours inclus=1.
    """
    try:
        colonnes = execute_client(
            """SELECT id, table_code, nom_colonne, type_donnee, longueur,
                      inclus, alias, obligatoire, version_ajout
               FROM APP_ETL_Published_Colonnes
               WHERE table_code = ?
               ORDER BY obligatoire DESC, nom_colonne""",
            (table_code,), use_cache=False
        )
        return {"success": True, "data": colonnes, "count": len(colonnes)}
    except Exception as e:
        if "invalid object name" in str(e).lower():
            return {"success": True, "data": [], "count": 0,
                    "warning": "Colonnes non encore publiees pour cette table"}
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/client/{table_code}/{nom_colonne}")
async def toggle_client_colonne(
    table_code: str,
    nom_colonne: str,
    toggle: ColonneClientToggle,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Active/desactive une colonne ou change son alias.
    Logique metier :
      - Si la colonne est obligatoire → inclus ne peut pas etre mis a 0
      - Le client peut toujours modifier l'alias (nom d'affichage)
    """
    try:
        # Verifier si la colonne est obligatoire
        colonnes = execute_client(
            "SELECT obligatoire FROM APP_ETL_Published_Colonnes WHERE table_code = ? AND nom_colonne = ?",
            (table_code, nom_colonne), use_cache=False
        )
        if not colonnes:
            raise HTTPException(status_code=404, detail="Colonne non trouvee")

        if colonnes[0]['obligatoire'] and not toggle.inclus:
            raise HTTPException(
                status_code=400,
                detail=f"La colonne '{nom_colonne}' est obligatoire et ne peut pas etre exclue"
            )

        with client_cursor(x_dwh_code) as cursor:
            cursor.execute(
                """UPDATE APP_ETL_Published_Colonnes
                   SET inclus = ?, alias = ?
                   WHERE table_code = ? AND nom_colonne = ?""",
                (1 if toggle.inclus else 0, toggle.alias, table_code, nom_colonne)
            )
            cursor.commit()

        statut = "incluse" if toggle.inclus else "exclue"
        return {"success": True, "message": f"Colonne '{nom_colonne}' {statut}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{table_code}/selected")
async def get_selected_colonnes(
    table_code: str,
    x_dwh_code: str = Header(..., alias="X-DWH-Code")
):
    """
    [CLIENT] Retourne uniquement les colonnes incluses pour une table.
    Utilise par l'agent ETL pour construire la requete SQL source.
    """
    try:
        colonnes = execute_client(
            """SELECT nom_colonne,
                      COALESCE(alias, nom_colonne) AS nom_affichage,
                      type_donnee, longueur, obligatoire
               FROM APP_ETL_Published_Colonnes
               WHERE table_code = ? AND inclus = 1
               ORDER BY obligatoire DESC, nom_colonne""",
            (table_code,), use_cache=False
        )
        return {"success": True, "data": colonnes, "count": len(colonnes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
