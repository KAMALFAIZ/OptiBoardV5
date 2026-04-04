"""
Comptabilité — API Router
==========================
Endpoints pour tous les documents comptables :
  - Balance Générale
  - Journal des Écritures
  - Balance Tiers (clients + fournisseurs)
  - Écritures de Trésorerie
  - Détail des Charges
  - Détail des Produits
  - Échéances Fournisseurs
  - Lettrage et Rapprochement
  - Analyses Comptables (évolution mensuelle)
  - KPIs globaux comptables

Datasource templates : POST /api/comptabilite/seed-datasources
  → Insère/met à jour les datasources comptables dans APP_DataSources_Templates
    afin qu'ils soient disponibles dans PivotBuilder/GridViewBuilder/DashboardBuilder.
"""

import json
import logging
import re
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..database_unified import execute_app as execute_query, execute_central as execute_central_query, write_central
from ..sql.query_templates import (
    BALANCE_GENERALE,
    BALANCE_GENERALE_PAR_CLASSE,
    KPIS_BALANCE_GENERALE,
    JOURNAL_ECRITURES,
    JOURNAL_ECRITURES_PAR_JOURNAL,
    BALANCE_TIERS_CLIENTS,
    BALANCE_TIERS_FOURNISSEURS,
    KPIS_BALANCE_TIERS,
    ECRITURES_TRESORERIE,
    ECRITURES_TRESORERIE_PAR_BANQUE,
    KPIS_TRESORERIE,
    DETAIL_CHARGES,
    DETAIL_CHARGES_PAR_CATEGORIE,
    DETAIL_PRODUITS,
    DETAIL_PRODUITS_PAR_CATEGORIE,
    ECHEANCES_FOURNISSEURS,
    ECHEANCES_FOURNISSEURS_PAR_FOURNISSEUR,
    KPIS_ECHEANCES_FOURNISSEURS,
    LETTRAGE_RAPPROCHEMENT,
    LETTRAGE_NON_LETTRE,
    KPIS_LETTRAGE,
    ANALYSE_CHARGES_PRODUITS_MENSUEL,
    ECHEANCES_A_ECHOIR,
    ECHEANCES_VENTES_NON_REGLEES,
    KPIS_RECOUVREMENT,
)
from ..services.calculs import get_periode_dates, parse_number

logger = logging.getLogger("Comptabilite")

router = APIRouter(prefix="/api/comptabilite", tags=["Comptabilité"])


def _current_year() -> int:
    return datetime.now().year


def _safe_float(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _default_dates():
    d = get_periode_dates("annee_courante")
    return d["date_debut"], d["date_fin"]


# =============================================================================
# KPIs GLOBAUX COMPTABLES
# =============================================================================

@router.get("/kpis")
async def get_kpis_comptables(exercice: Optional[int] = None):
    """KPIs agrégés : résultat net, trésorerie, encours clients, dettes fournisseurs."""
    year = exercice or _current_year()
    date_debut, date_fin = _default_dates()
    try:
        # Balance générale KPIs
        bg_rows = execute_query(KPIS_BALANCE_GENERALE, (str(year),))
        bg = bg_rows[0] if bg_rows else {}

        # Balance tiers KPIs
        bt_rows = execute_query(KPIS_BALANCE_TIERS)
        bt = bt_rows[0] if bt_rows else {}

        # Lettrage KPIs
        lt_rows = execute_query(KPIS_LETTRAGE, (date_debut, date_fin))
        lt = lt_rows[0] if lt_rows else {}

        # Échéances fournisseurs KPIs
        ef_rows = execute_query(KPIS_ECHEANCES_FOURNISSEURS)
        ef = ef_rows[0] if ef_rows else {}

        return {
            "success": True,
            "data": {
                "total_charges": _safe_float(bg.get("Total_Charges")),
                "total_produits": _safe_float(bg.get("Total_Produits")),
                "resultat_net": _safe_float(bg.get("Resultat_Net")),
                "solde_tresorerie": _safe_float(bg.get("Solde_Tresorerie")),
                "nb_comptes_actifs": int(bg.get("Nb_Comptes_Actifs") or 0),
                "encours_clients": _safe_float(bt.get("Encours_Clients")),
                "nb_clients_encours": int(bt.get("Nb_Clients_Encours") or 0),
                "creances_douteuses": _safe_float(bt.get("Creances_Douteuses")),
                "dettes_fournisseurs": _safe_float(bt.get("Dettes_Fournisseurs")),
                "total_a_payer_fournisseurs": _safe_float(ef.get("Total_A_Payer")),
                "nb_pieces_lettrage": int(lt.get("Nb_Total_Pieces") or 0),
                "taux_lettrage": round(
                    _safe_float(lt.get("Total_Lettre")) / max(_safe_float(lt.get("Total_Factures")), 1) * 100, 1
                ),
                "exercice": year,
            }
        }
    except Exception as e:
        logger.error(f"get_kpis_comptables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BALANCE GÉNÉRALE
# =============================================================================

@router.get("/balance-generale")
async def get_balance_generale(exercice: Optional[int] = None):
    """Balance générale complète par compte."""
    year = exercice or _current_year()
    try:
        rows = execute_query(BALANCE_GENERALE)
        par_classe = execute_query(BALANCE_GENERALE_PAR_CLASSE, (str(year),))
        kpis_rows = execute_query(KPIS_BALANCE_GENERALE, (str(year),))
        kpis = kpis_rows[0] if kpis_rows else {}
        return {
            "success": True,
            "kpis": {
                "total_charges": _safe_float(kpis.get("Total_Charges")),
                "total_produits": _safe_float(kpis.get("Total_Produits")),
                "resultat_net": _safe_float(kpis.get("Resultat_Net")),
                "solde_tresorerie": _safe_float(kpis.get("Solde_Tresorerie")),
                "nb_comptes_actifs": int(kpis.get("Nb_Comptes_Actifs") or 0),
            },
            "data": rows,
            "par_classe": par_classe,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_balance_generale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# JOURNAL DES ÉCRITURES
# =============================================================================

@router.get("/journal-ecritures")
async def get_journal_ecritures(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    journal: Optional[str] = None,
):
    """Journal des écritures comptables avec filtre période et journal."""
    d_debut, d_fin = (date_debut, date_fin) if date_debut and date_fin else _default_dates()
    try:
        rows = execute_query(JOURNAL_ECRITURES, (d_debut, d_fin))
        if journal:
            rows = [r for r in rows if (r.get("Code_Journal") or "").upper() == journal.upper()]

        par_journal = execute_query(JOURNAL_ECRITURES_PAR_JOURNAL, (d_debut, d_fin))
        return {
            "success": True,
            "data": rows,
            "par_journal": par_journal,
            "total": len(rows),
            "periode": {"debut": d_debut, "fin": d_fin},
        }
    except Exception as e:
        logger.error(f"get_journal_ecritures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BALANCE TIERS
# =============================================================================

@router.get("/balance-tiers")
async def get_balance_tiers(type_tiers: Optional[str] = Query(None, description="clients | fournisseurs | all")):
    """Balance tiers : clients et/ou fournisseurs."""
    tiers_type = (type_tiers or "all").lower()
    try:
        clients, fournisseurs = [], []

        if tiers_type in ("clients", "all"):
            clients = execute_query(BALANCE_TIERS_CLIENTS)

        if tiers_type in ("fournisseurs", "all"):
            try:
                fournisseurs = execute_query(BALANCE_TIERS_FOURNISSEURS)
            except Exception:
                fournisseurs = []

        kpis_rows = execute_query(KPIS_BALANCE_TIERS)
        kpis = kpis_rows[0] if kpis_rows else {}

        combined = []
        for r in clients:
            combined.append({**r, "Type_Tiers": "Client"})
        for r in fournisseurs:
            combined.append({**r, "Type_Tiers": "Fournisseur"})

        return {
            "success": True,
            "kpis": {
                "encours_clients": _safe_float(kpis.get("Encours_Clients")),
                "nb_clients_encours": int(kpis.get("Nb_Clients_Encours") or 0),
                "creances_douteuses": _safe_float(kpis.get("Creances_Douteuses")),
                "dettes_fournisseurs": _safe_float(kpis.get("Dettes_Fournisseurs")),
            },
            "clients": clients,
            "fournisseurs": fournisseurs,
            "data": combined,
            "total": len(combined),
        }
    except Exception as e:
        logger.error(f"get_balance_tiers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ÉCRITURES DE TRÉSORERIE
# =============================================================================

@router.get("/tresorerie")
async def get_tresorerie(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
):
    """Écritures de trésorerie avec KPIs par banque."""
    d_debut, d_fin = (date_debut, date_fin) if date_debut and date_fin else _default_dates()
    try:
        rows = execute_query(ECRITURES_TRESORERIE, (d_debut, d_fin))
        par_banque = execute_query(ECRITURES_TRESORERIE_PAR_BANQUE, (d_debut, d_fin))
        kpis_rows = execute_query(KPIS_TRESORERIE, (d_debut, d_fin))
        kpis = kpis_rows[0] if kpis_rows else {}
        return {
            "success": True,
            "kpis": {
                "total_encaissements": _safe_float(kpis.get("Total_Encaissements")),
                "total_decaissements": _safe_float(kpis.get("Total_Decaissements")),
                "flux_net": _safe_float(kpis.get("Flux_Net_Periode")),
                "nb_comptes_bancaires": int(kpis.get("Nb_Comptes_Bancaires") or 0),
                "tresorerie_totale": _safe_float(kpis.get("Tresorerie_Totale")),
            },
            "data": rows,
            "par_banque": par_banque,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_tresorerie: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DÉTAIL DES CHARGES
# =============================================================================

@router.get("/charges")
async def get_detail_charges(exercice: Optional[int] = None):
    """Détail des charges par compte avec comparatif N/N-1."""
    year = exercice or _current_year()
    try:
        rows = execute_query(DETAIL_CHARGES, (str(year),))
        par_categorie = execute_query(DETAIL_CHARGES_PAR_CATEGORIE, (str(year),))
        total_charges = sum(_safe_float(r.get("Montant_Charge")) for r in rows)
        return {
            "success": True,
            "kpis": {
                "total_charges": total_charges,
                "nb_comptes": len(rows),
                "exercice": year,
            },
            "data": rows,
            "par_categorie": par_categorie,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_detail_charges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DÉTAIL DES PRODUITS
# =============================================================================

@router.get("/produits")
async def get_detail_produits(exercice: Optional[int] = None):
    """Détail des produits par compte avec comparatif N/N-1."""
    year = exercice or _current_year()
    try:
        rows = execute_query(DETAIL_PRODUITS, (str(year),))
        par_categorie = execute_query(DETAIL_PRODUITS_PAR_CATEGORIE, (str(year),))
        total_produits = sum(_safe_float(r.get("Montant_Produit")) for r in rows)
        return {
            "success": True,
            "kpis": {
                "total_produits": total_produits,
                "nb_comptes": len(rows),
                "exercice": year,
            },
            "data": rows,
            "par_categorie": par_categorie,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_detail_produits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ÉCHÉANCES CLIENTS  (réutilise les templates recouvrement)
# =============================================================================

@router.get("/echeances-clients")
async def get_echeances_clients(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
):
    """Échéances clients non réglées + KPIs recouvrement."""
    d_debut, d_fin = (date_debut, date_fin) if date_debut and date_fin else _default_dates()
    try:
        echeances = execute_query(ECHEANCES_VENTES_NON_REGLEES)
        a_echoir = execute_query(ECHEANCES_A_ECHOIR)
        kpis_rows = execute_query(KPIS_RECOUVREMENT)
        kpis = kpis_rows[0] if kpis_rows else {}
        return {
            "success": True,
            "kpis": {
                "encours_total": _safe_float(kpis.get("Encours_Total")),
                "a_echoir": _safe_float(kpis.get("A_Echoir")),
                "echu": _safe_float(kpis.get("Echu")),
                "nb_echeances_retard": int(kpis.get("Nb_Echeances_Retard") or 0),
                "nb_clients_retard": int(kpis.get("Nb_Clients_Retard") or 0),
                "retard_moyen_jours": _safe_float(kpis.get("Retard_Moyen_Jours")),
            },
            "echeances_non_reglees": echeances,
            "a_echoir": a_echoir,
            "total": len(echeances),
        }
    except Exception as e:
        logger.error(f"get_echeances_clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ÉCHÉANCES FOURNISSEURS
# =============================================================================

@router.get("/echeances-fournisseurs")
async def get_echeances_fournisseurs():
    """Échéances fournisseurs non réglées avec KPIs."""
    try:
        rows = execute_query(ECHEANCES_FOURNISSEURS)
        par_fournisseur = execute_query(ECHEANCES_FOURNISSEURS_PAR_FOURNISSEUR)
        kpis_rows = execute_query(KPIS_ECHEANCES_FOURNISSEURS)
        kpis = kpis_rows[0] if kpis_rows else {}
        return {
            "success": True,
            "kpis": {
                "total_a_payer": _safe_float(kpis.get("Total_A_Payer")),
                "montant_en_retard": _safe_float(kpis.get("Montant_En_Retard")),
                "a_echoir": _safe_float(kpis.get("A_Echoir")),
                "nb_echeances": int(kpis.get("Nb_Echeances_Ouvertes") or 0),
                "nb_fournisseurs": int(kpis.get("Nb_Fournisseurs") or 0),
            },
            "data": rows,
            "par_fournisseur": par_fournisseur,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_echeances_fournisseurs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LETTRAGE ET RAPPROCHEMENT
# =============================================================================

@router.get("/lettrage")
async def get_lettrage(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    statut: Optional[str] = Query(None, description="lettre | non_lettre | partiel | all"),
):
    """Lettrage et rapprochement des factures/règlements."""
    d_debut, d_fin = (date_debut, date_fin) if date_debut and date_fin else _default_dates()
    try:
        rows = execute_query(LETTRAGE_RAPPROCHEMENT, (d_debut, d_fin))
        non_lettres = execute_query(LETTRAGE_NON_LETTRE)
        kpis_rows = execute_query(KPIS_LETTRAGE, (d_debut, d_fin))
        kpis = kpis_rows[0] if kpis_rows else {}

        # Filtre statut côté Python
        if statut and statut != "all":
            map_statut = {
                "lettre": "Lettré complet",
                "partiel": "Lettré partiel",
                "non_lettre": "Non lettré",
            }
            target = map_statut.get(statut)
            if target:
                rows = [r for r in rows if r.get("Statut_Lettrage") == target]

        total_lettrage = max(_safe_float(kpis.get("Total_Factures")), 1)
        return {
            "success": True,
            "kpis": {
                "nb_total_pieces": int(kpis.get("Nb_Total_Pieces") or 0),
                "nb_lettres_complet": int(kpis.get("Nb_Lettres_Complet") or 0),
                "nb_lettres_partiel": int(kpis.get("Nb_Lettres_Partiel") or 0),
                "nb_non_lettres": int(kpis.get("Nb_Non_Lettres") or 0),
                "total_factures": _safe_float(kpis.get("Total_Factures")),
                "total_lettre": _safe_float(kpis.get("Total_Lettre")),
                "total_non_lettre": _safe_float(kpis.get("Total_Non_Lettre")),
                "taux_lettrage": round(
                    _safe_float(kpis.get("Total_Lettre")) / total_lettrage * 100, 1
                ),
            },
            "data": rows,
            "non_lettres": non_lettres,
            "total": len(rows),
        }
    except Exception as e:
        logger.error(f"get_lettrage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ANALYSES COMPTABLES
# =============================================================================

@router.get("/analyses")
async def get_analyses_comptables(exercice: Optional[int] = None):
    """Évolution mensuelle charges/produits/résultat pour l'exercice."""
    year = exercice or _current_year()
    try:
        mensuel = execute_query(ANALYSE_CHARGES_PRODUITS_MENSUEL, (str(year),))
        return {
            "success": True,
            "data": mensuel,
            "exercice": year,
        }
    except Exception as e:
        logger.error(f"get_analyses_comptables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SEED DATASOURCE TEMPLATES
# =============================================================================

PARAMS_DATE_SOCIETE = '[{"name": "dateDebut", "type": "date", "source": "global"}, {"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'
PARAMS_DATEFIN_SOCIETE = '[{"name": "dateFin", "type": "date", "source": "global"}, {"name": "societe", "type": "select", "source": "query", "query": "SELECT code AS value, nom AS label FROM APP_DWH WHERE actif = 1 ORDER BY nom", "required": false, "allow_null": true, "null_label": "(Toutes)"}]'

COMPTABILITE_DATASOURCES = [
    # ── Écritures comptables ──────────────────────────────────────────────────
    {
        "code": "DS_ECRITURES_GLOBAL",
        "nom": "Ecritures Comptables Global",
        "category": "Comptabilite",
        "description": "Synthese globale des ecritures comptables par periode",
        "query_template": """
            SELECT
                [societe] AS [Societe],
                [Exercice],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes],
                COUNT(DISTINCT [Code Journal]) AS [Nb Journaux]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [societe], [Exercice]
            ORDER BY [Exercice] DESC
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_ECRITURES_PAR_JOURNAL",
        "nom": "Ecritures par Journal",
        "category": "Comptabilite",
        "description": "Ecritures comptables agregees par journal",
        "query_template": """
            SELECT
                [Code Journal],
                [Libellé Journal] AS [Journal],
                [Type Code Journal] AS [Type Journal],
                [societe] AS [Societe],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Code Journal], [Libellé Journal], [Type Code Journal], [societe]
            ORDER BY [Total Debit] DESC
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_ECRITURES_PAR_COMPTE",
        "nom": "Ecritures par Compte",
        "category": "Comptabilite",
        "description": "Mouvements par compte general",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [Masse], [Rubrique], [Poste],
                [societe] AS [Societe],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(*) AS [Nb Ecritures]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [Masse], [Rubrique], [Poste], [societe]
            ORDER BY [Compte]
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_ECRITURES_PAR_TIERS",
        "nom": "Ecritures par Tiers",
        "category": "Comptabilite",
        "description": "Mouvements par compte tiers (clients/fournisseurs)",
        "query_template": """
            SELECT
                [Compte Tiers] AS [Code Tiers],
                [Intitulé tiers] AS [Tiers],
                [Type tiers] AS [Type],
                [societe] AS [Societe],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                COUNT(*) AS [Nb Ecritures],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Compte Tiers] IS NOT NULL AND [Compte Tiers] <> ''
              AND [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Compte Tiers], [Intitulé tiers], [Type tiers], [societe]
            ORDER BY ABS(SUM([Débit]) - SUM([Crédit])) DESC
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_ECRITURES_PAR_MOIS",
        "nom": "Ecritures par Mois",
        "category": "Comptabilite",
        "description": "Evolution mensuelle des ecritures comptables",
        "query_template": """
            SELECT
                [Année] AS [Annee],
                [Mois],
                [societe] AS [Societe],
                COUNT(*) AS [Nb Ecritures],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                COUNT(DISTINCT [N° Compte Général]) AS [Nb Comptes],
                COUNT(DISTINCT [N° Pièce]) AS [Nb Pieces]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [Année], [Mois], [societe]
            ORDER BY [Annee] DESC, [Mois] DESC
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_ECRITURES_DETAIL",
        "nom": "Detail Ecritures Comptables",
        "category": "Comptabilite",
        "description": "Liste detaillee des ecritures comptables",
        "query_template": """
            SELECT
                [Date d'écriture] AS [Date],
                [Code Journal],
                [Libellé Journal] AS [Journal],
                [N° Pièce] AS [Num Piece],
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule Compte],
                [Compte Tiers],
                [Intitulé tiers] AS [Tiers],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Sens],
                [Référence],
                [Date d'échéance] AS [Echeance],
                [Mode de réglement] AS [Mode Reglement],
                [Lettrage],
                [societe] AS [Societe]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [Date d'écriture] DESC, [N° Pièce]
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    # ── Grand Livre ───────────────────────────────────────────────────────────
    {
        "code": "DS_GRAND_LIVRE",
        "nom": "Grand Livre",
        "category": "Comptabilite",
        "description": "Grand livre comptable par compte",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule Compte],
                [Date d'écriture] AS [Date],
                [Code Journal] AS [Journal],
                [N° Pièce] AS [Num Piece],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Compte Tiers] AS [Tiers],
                [Intitulé tiers] AS [Nom Tiers],
                [Lettrage],
                [societe] AS [Societe]
            FROM [Ecritures_Comptables]
            WHERE [Date d'écriture] BETWEEN @dateDebut AND @dateFin
              AND (@societe IS NULL OR [societe] = @societe)
            ORDER BY [N° Compte Général], [Date d'écriture]
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    # ── Balance Générale ──────────────────────────────────────────────────────
    {
        "code": "DS_BALANCE_GENERALE",
        "nom": "Balance Generale",
        "category": "Comptabilite",
        "description": "Balance generale des comptes avec soldes",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [Masse], [Rubrique], [Poste],
                [Nature Compte] AS [Nature],
                [societe] AS [Societe],
                SUM(CASE WHEN [Report à Nouveau] = 'Oui' THEN [Débit] - [Crédit] ELSE 0 END) AS [A Nouveau],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Débit] ELSE 0 END) AS [Mvt Debit],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Crédit] ELSE 0 END) AS [Mvt Credit],
                SUM([Débit]) AS [Total Debit],
                SUM([Crédit]) AS [Total Credit],
                SUM([Débit]) - SUM([Crédit]) AS [Solde],
                CASE WHEN SUM([Débit]) > SUM([Crédit]) THEN SUM([Débit]) - SUM([Crédit]) ELSE 0 END AS [Solde Debiteur],
                CASE WHEN SUM([Crédit]) > SUM([Débit]) THEN SUM([Crédit]) - SUM([Débit]) ELSE 0 END AS [Solde Crediteur]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [Masse], [Rubrique], [Poste], [Nature Compte], [societe]
            HAVING SUM([Débit]) <> 0 OR SUM([Crédit]) <> 0
            ORDER BY [Compte]
        """,
        "parameters": PARAMS_DATEFIN_SOCIETE,
    },
    # ── Trésorerie (classe 5) ─────────────────────────────────────────────────
    {
        "code": "DS_TRESORERIE",
        "nom": "Tresorerie",
        "category": "Comptabilite",
        "description": "Situation de la tresorerie (classe 5)",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Societe],
                SUM(CASE WHEN [Report à Nouveau] = 'Oui' THEN [Débit] - [Crédit] ELSE 0 END) AS [Solde Initial],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Débit] ELSE 0 END) AS [Encaissements],
                SUM(CASE WHEN [Report à Nouveau] <> 'Oui' THEN [Crédit] ELSE 0 END) AS [Decaissements],
                SUM([Débit]) - SUM([Crédit]) AS [Solde Final]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [N° Compte Général] LIKE '5%'
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            ORDER BY [Compte]
        """,
        "parameters": PARAMS_DATEFIN_SOCIETE,
    },
    {
        "code": "DS_TRESORERIE_PAR_MOIS",
        "nom": "Tresorerie par Mois",
        "category": "Comptabilite",
        "description": "Evolution mensuelle de la tresorerie",
        "query_template": """
            SELECT
                [Année] AS [Annee],
                [Mois],
                [societe] AS [Societe],
                SUM([Débit]) AS [Encaissements],
                SUM([Crédit]) AS [Decaissements],
                SUM([Débit]) - SUM([Crédit]) AS [Flux Net]
            FROM [Ecritures_Comptables]
            WHERE [N° Compte Général] LIKE '5%'
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date d'écriture] BETWEEN @dateDebut AND @dateFin
            GROUP BY [Année], [Mois], [societe]
            ORDER BY [Annee], [Mois]
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    # ── Échéances & Lettrage ──────────────────────────────────────────────────
    {
        "code": "DS_ECHEANCES_COMPTABLES",
        "nom": "Echeances Comptables",
        "category": "Comptabilite",
        "description": "Ecritures avec echeances non lettrees",
        "query_template": """
            SELECT
                [Date d'échéance] AS [Echeance],
                [N° Compte Général] AS [Compte],
                [Compte Tiers],
                [Intitulé tiers] AS [Tiers],
                [N° Pièce] AS [Num Piece],
                [Libellé] AS [Libelle],
                [Débit],
                [Crédit],
                [Mode de réglement] AS [Mode Reglement],
                [Lettrage],
                [Type tiers],
                [societe] AS [Societe],
                DATEDIFF(DAY, GETDATE(), [Date d'échéance]) AS [Jours Avant Echeance]
            FROM [Ecritures_Comptables]
            WHERE [Date d'échéance] IS NOT NULL
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Date d'échéance] BETWEEN @dateDebut AND @dateFin
              AND [Lettrage] IS NULL
            ORDER BY [Date d'échéance]
        """,
        "parameters": PARAMS_DATE_SOCIETE,
    },
    {
        "code": "DS_LETTRAGE",
        "nom": "Analyse Lettrage",
        "category": "Comptabilite",
        "description": "Analyse des ecritures lettrees et non lettrees",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Societe],
                SUM(CASE WHEN [Lettrage] IS NOT NULL THEN 1 ELSE 0 END) AS [Nb Lettrees],
                SUM(CASE WHEN [Lettrage] IS NULL THEN 1 ELSE 0 END) AS [Nb Non Lettrees],
                SUM(CASE WHEN [Lettrage] IS NULL THEN [Débit] - [Crédit] ELSE 0 END) AS [Solde Non Lettre]
            FROM [Ecritures_Comptables]
            WHERE [Exercice] = YEAR(@dateFin)
              AND (@societe IS NULL OR [societe] = @societe)
              AND [Saisie Echéance] = 'Oui'
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            HAVING SUM(CASE WHEN [Lettrage] IS NULL THEN 1 ELSE 0 END) > 0
            ORDER BY ABS(SUM(CASE WHEN [Lettrage] IS NULL THEN [Débit] - [Crédit] ELSE 0 END)) DESC
        """,
        "parameters": PARAMS_DATEFIN_SOCIETE,
    },
    # ── Détail Charges / Produits (classes 6 et 7) ───────────────────────────
    {
        "code": "DS_DETAIL_CHARGES",
        "nom": "Detail des Charges",
        "category": "Comptabilite",
        "description": "Charges par compte — classe 6 — avec comparatif N/N-1",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Societe],
                SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Débit] - [Crédit] ELSE 0 END) AS [Montant N],
                SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Débit] - [Crédit] ELSE 0 END) AS [Montant N1],
                CASE WHEN SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Débit] - [Crédit] ELSE 0 END) <> 0
                  THEN ROUND((SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Débit] - [Crédit] ELSE 0 END)
                       - SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Débit] - [Crédit] ELSE 0 END))
                       / ABS(SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Débit] - [Crédit] ELSE 0 END)) * 100, 2)
                  ELSE NULL END AS [Evolution %]
            FROM [Ecritures_Comptables]
            WHERE [N° Compte Général] LIKE '6%'
              AND [Exercice] IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            HAVING SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Débit] - [Crédit] ELSE 0 END) <> 0
            ORDER BY [Compte]
        """,
        "parameters": PARAMS_DATEFIN_SOCIETE,
    },
    {
        "code": "DS_DETAIL_PRODUITS",
        "nom": "Detail des Produits",
        "category": "Comptabilite",
        "description": "Produits par compte — classe 7 — avec comparatif N/N-1",
        "query_template": """
            SELECT
                [N° Compte Général] AS [Compte],
                [Intitulé compte général] AS [Intitule],
                [societe] AS [Societe],
                SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Crédit] - [Débit] ELSE 0 END) AS [Montant N],
                SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Crédit] - [Débit] ELSE 0 END) AS [Montant N1],
                CASE WHEN SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Crédit] - [Débit] ELSE 0 END) <> 0
                  THEN ROUND((SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Crédit] - [Débit] ELSE 0 END)
                       - SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Crédit] - [Débit] ELSE 0 END))
                       / ABS(SUM(CASE WHEN [Exercice] = YEAR(@dateFin) - 1 THEN [Crédit] - [Débit] ELSE 0 END)) * 100, 2)
                  ELSE NULL END AS [Evolution %]
            FROM [Ecritures_Comptables]
            WHERE [N° Compte Général] LIKE '7%'
              AND [Exercice] IN (YEAR(@dateFin), YEAR(@dateFin) - 1)
              AND (@societe IS NULL OR [societe] = @societe)
            GROUP BY [N° Compte Général], [Intitulé compte général], [societe]
            HAVING SUM(CASE WHEN [Exercice] = YEAR(@dateFin) THEN [Crédit] - [Débit] ELSE 0 END) <> 0
            ORDER BY [Compte]
        """,
        "parameters": PARAMS_DATEFIN_SOCIETE,
    },
]


@router.post("/seed-datasources")
async def seed_comptabilite_datasources():
    """
    Insère ou met à jour les datasource templates comptables dans APP_DataSources_Templates.
    Ces datasources sont ensuite disponibles dans PivotBuilder, GridViewBuilder et DashboardBuilder.
    """
    inserted, updated, errors = 0, 0, []
    for ds in COMPTABILITE_DATASOURCES:
        try:
            existing = execute_central_query(
                "SELECT id FROM APP_DataSources_Templates WHERE code = ?", (ds["code"],)
            )
            if existing:
                write_central(
                    """UPDATE APP_DataSources_Templates
                       SET nom=?, category=?, description=?, query_template=?, parameters=?, actif=1
                       WHERE code=?""",
                    (ds["nom"], ds["category"], ds["description"],
                     ds["query_template"], ds["parameters"], ds["code"]),
                )
                updated += 1
            else:
                write_central(
                    """INSERT INTO APP_DataSources_Templates
                       (code, nom, type, category, description, query_template, parameters, is_system, actif)
                       VALUES (?, ?, 'query', ?, ?, ?, ?, 0, 1)""",
                    (ds["code"], ds["nom"], ds["category"], ds["description"],
                     ds["query_template"], ds["parameters"]),
                )
                inserted += 1
        except Exception as e:
            errors.append({"code": ds["code"], "error": str(e)})

    return {
        "success": True,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "message": f"{inserted} datasources créées, {updated} mises à jour.",
    }


# =============================================================================
# RAPPORTS COMPTABILITE : GridViews + PivotGrids + Dashboards + Menus
# =============================================================================

_SOC = "(@societe IS NULL OR ec.societe = @societe)"
_PARAMS_DATE_SOC = json.dumps([
    {"name": "dateDebut", "type": "date", "label": "Date début", "required": True, "default": "FIRST_DAY_YEAR"},
    {"name": "dateFin",   "type": "date", "label": "Date fin",   "required": True, "default": "TODAY"},
    {"name": "societe",   "type": "select", "label": "Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"},
])
_PARAMS_SOC_ONLY = json.dumps([
    {"name": "societe", "type": "select", "label": "Société", "required": False,
     "source": "query",
     "query": "SELECT code as value, nom + ' (' + code + ')' as label FROM APP_DWH WHERE actif = 1 ORDER BY nom",
     "allow_null": True, "null_label": "(Toutes)"},
])

_CPT_DS_TEMPLATES = [
    {"code": "DS_CPT_GRAND_LIVRE", "nom": "Grand Livre Général", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Date d'écriture] AS [Date], ec.[N° Compte Général] AS [Compte], "
         "ec.[Intitulé compte général] AS [Intitule Compte], ec.[Compte Tiers], "
         "ec.[Intitulé tiers] AS [Tiers], ec.[N° Pièce] AS [Num Piece], "
         "ec.[Code Journal], ec.[Libellé Journal] AS [Journal], ec.[Libellé] AS [Libelle], "
         "ec.[Débit], ec.[Crédit], ec.[Débit] - ec.[Crédit] AS [Solde], "
         "ec.[Nature Compte], ec.[Exercice], ec.societe AS [Societe] "
         "FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "ORDER BY ec.[N° Compte Général], ec.[Date d'écriture]"
     )},
    {"code": "DS_CPT_BALANCE", "nom": "Balance Générale", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[N° Compte Général] AS [Compte], ec.[Intitulé compte général] AS [Intitule Compte], "
         "ec.[Nature Compte], SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[N° Compte Général], ec.[Intitulé compte général], ec.[Nature Compte], ec.societe "
         "ORDER BY ec.[N° Compte Général]"
     )},
    {"code": "DS_CPT_JOURNAL", "nom": "Journal des Ecritures", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Date d'écriture] AS [Date], ec.[Code Journal], ec.[Libellé Journal] AS [Journal], "
         "ec.[N° Pièce] AS [Num Piece], ec.[N° Compte Général] AS [Compte], "
         "ec.[Intitulé compte général] AS [Intitule Compte], ec.[Compte Tiers], "
         "ec.[Intitulé tiers] AS [Tiers], ec.[Libellé] AS [Libelle], ec.[Débit], ec.[Crédit], "
         "ec.[Type Ecriture], ec.[Exercice], ec.societe AS [Societe] "
         "FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "ORDER BY ec.[Date d'écriture] DESC, ec.[N° Pièce]"
     )},
    {"code": "DS_CPT_BALANCE_TIERS", "nom": "Balance Tiers", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Tiers], ec.[Type tiers], ec.[Nature Compte], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         "WHERE ec.[Compte Tiers] IS NOT NULL AND ec.[Compte Tiers] <> '' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.[Type tiers], ec.[Nature Compte], ec.societe "
         "ORDER BY ABS(SUM(ec.[Débit]) - SUM(ec.[Crédit])) DESC"
     )},
    {"code": "DS_CPT_TRESORERIE", "nom": "Ecritures de Trésorerie", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Date d'écriture] AS [Date], ec.[Code Journal], ec.[Libellé Journal] AS [Journal], "
         "ec.[N° Pièce] AS [Num Piece], ec.[N° Compte Général] AS [Compte], "
         "ec.[Intitulé compte général] AS [Intitule Compte], ec.[Compte Tiers], "
         "ec.[Intitulé tiers] AS [Tiers], ec.[Libellé] AS [Libelle], ec.[Débit], ec.[Crédit], "
         "ec.[Mode de règlement] AS [Mode Reglement], ec.[N° Pièce de tréso] AS [Num Piece Treso], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type Code Journal] = 'Trésorerie' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "ORDER BY ec.[Date d'écriture] DESC"
     )},
    {"code": "DS_CPT_CHARGES", "nom": "Détail des Charges", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[N° Compte Général] AS [Compte], ec.[Intitulé compte général] AS [Intitule Compte], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Montant Charge], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Nature Compte] = 'Charge' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[N° Compte Général], ec.[Intitulé compte général], ec.societe "
         "ORDER BY SUM(ec.[Débit]) - SUM(ec.[Crédit]) DESC"
     )},
    {"code": "DS_CPT_PRODUITS", "nom": "Détail des Produits", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[N° Compte Général] AS [Compte], ec.[Intitulé compte général] AS [Intitule Compte], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Crédit]) - SUM(ec.[Débit]) AS [Montant Produit], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Nature Compte] = 'Produit' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[N° Compte Général], ec.[Intitulé compte général], ec.societe "
         "ORDER BY SUM(ec.[Crédit]) - SUM(ec.[Débit]) DESC"
     )},
    {"code": "DS_CPT_ECHEANCES_CLIENTS", "nom": "Echéances Clients", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Client], "
         "ec.[Date d'échéance] AS [Date Echeance], ec.[Date d'écriture] AS [Date Ecriture], "
         "ec.[N° Pièce] AS [Num Piece], ec.[N° facture] AS [Num Facture], ec.[Libellé] AS [Libelle], "
         "ec.[Débit], ec.[Crédit], ec.[Débit] - ec.[Crédit] AS [Solde], "
         "ec.[Lettrage], ec.[Lettre], ec.[Mode de règlement] AS [Mode Reglement], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Client' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "ORDER BY ec.[Date d'échéance] DESC"
     )},
    {"code": "DS_CPT_ECHEANCES_FOURN", "nom": "Echéances Fournisseurs", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Fournisseur], "
         "ec.[Date d'échéance] AS [Date Echeance], ec.[Date d'écriture] AS [Date Ecriture], "
         "ec.[N° Pièce] AS [Num Piece], ec.[N° facture] AS [Num Facture], ec.[Libellé] AS [Libelle], "
         "ec.[Débit], ec.[Crédit], ec.[Crédit] - ec.[Débit] AS [Solde], "
         "ec.[Lettrage], ec.[Lettre], ec.[Mode de règlement] AS [Mode Reglement], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Fournisseur' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "ORDER BY ec.[Date d'échéance] DESC"
     )},
    {"code": "DS_CPT_LETTRAGE", "nom": "Lettrage et Rapprochement", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Tiers], ec.[Type tiers], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], "
         "SUM(CASE WHEN ec.[Lettrage] = 'OUI' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Lettre], "
         "SUM(CASE WHEN ec.[Lettrage] = 'NON' OR ec.[Lettrage] IS NULL THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Non Lettre], "
         "COUNT(*) AS [Nb Ecritures], ec.societe AS [Societe] "
         "FROM Ecritures_Comptables ec "
         "WHERE ec.[Compte Tiers] IS NOT NULL AND ec.[Compte Tiers] <> '' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.[Type tiers], ec.societe "
         "ORDER BY ABS(SUM(CASE WHEN ec.[Lettrage] = 'NON' OR ec.[Lettrage] IS NULL THEN ec.[Débit] - ec.[Crédit] ELSE 0 END)) DESC"
     )},
    {"code": "DS_CPT_RESULTAT_NATURE", "nom": "Résultat par Nature", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Nature Compte], LEFT(ec.[N° Compte Général], 2) AS [Classe], "
         "ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], ec.societe AS [Societe] "
         "FROM Ecritures_Comptables ec "
         f"WHERE ec.[Nature Compte] IN ('Charge', 'Produit') "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Nature Compte], LEFT(ec.[N° Compte Général], 2), ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_BALANCE_JOURNAL", "nom": "Balance par Journal", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Code Journal], ec.[Libellé Journal] AS [Journal], "
         "ec.[Type Code Journal] AS [Type Journal], ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Code Journal], ec.[Libellé Journal], ec.[Type Code Journal], ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_BALANCE_CLASSE", "nom": "Balance par Classe Comptable", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT LEFT(ec.[N° Compte Général], 1) AS [Classe], "
         "CASE LEFT(ec.[N° Compte Général], 1) "
         "WHEN '1' THEN 'Capitaux' WHEN '2' THEN 'Immobilisations' "
         "WHEN '3' THEN 'Stocks' WHEN '4' THEN 'Tiers' "
         "WHEN '5' THEN 'Tresorerie' WHEN '6' THEN 'Charges' "
         "WHEN '7' THEN 'Produits' ELSE 'Autres' END AS [Libelle Classe], "
         "ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY LEFT(ec.[N° Compte Général], 1), ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_TRESO_BANQUE", "nom": "Trésorerie par Banque", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Code Journal], ec.[Libellé Journal] AS [Banque], ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Encaissements], SUM(ec.[Crédit]) AS [Decaissements], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Operations], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type Code Journal] = 'Trésorerie' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Code Journal], ec.[Libellé Journal], ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_SOLDES_CLIENTS", "nom": "Soldes Clients", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Client], ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Client' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_SOLDES_FOURN", "nom": "Soldes Fournisseurs", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Compte Tiers], ec.[Intitulé tiers] AS [Fournisseur], ec.[Mois], ec.[Année] AS [Annee], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "SUM(ec.[Crédit]) - SUM(ec.[Débit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Fournisseur' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.[Mois], ec.[Année], ec.societe"
     )},
    {"code": "DS_CPT_KPI_GLOBAL", "nom": "KPI Comptabilité Globale", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "COUNT(*) AS [Nb Ecritures], COUNT(DISTINCT ec.[N° Compte Général]) AS [Nb Comptes], "
         "COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Total Charges], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) AS [Total Produits], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) - "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Resultat], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.societe"
     )},
    {"code": "DS_CPT_EVOLUTION_MENSUELLE", "nom": "Evolution Mensuelle Comptable", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Année] AS [Annee], ec.[Mois], "
         "CAST(ec.[Année] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde Net], "
         "COUNT(*) AS [Nb Ecritures], COUNT(DISTINCT ec.[N° Compte Général]) AS [Nb Comptes], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Année], ec.[Mois], ec.societe ORDER BY ec.[Année], ec.[Mois]"
     )},
    {"code": "DS_CPT_CHARGES_PRODUITS_MENS", "nom": "Charges vs Produits Mensuel", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Année] AS [Annee], ec.[Mois], "
         "CAST(ec.[Année] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Charges], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) AS [Produits], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) - "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Resultat], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Nature Compte] IN ('Charge', 'Produit') "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Année], ec.[Mois], ec.societe ORDER BY ec.[Année], ec.[Mois]"
     )},
    {"code": "DS_CPT_REPARTITION_NATURE", "nom": "Répartition par Nature Compte", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Nature Compte], SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "ABS(SUM(ec.[Débit]) - SUM(ec.[Crédit])) AS [Solde Abs], COUNT(*) AS [Nb Ecritures], "
         "COUNT(DISTINCT ec.[N° Compte Général]) AS [Nb Comptes], ec.societe AS [Societe] "
         "FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Nature Compte], ec.societe ORDER BY ABS(SUM(ec.[Débit]) - SUM(ec.[Crédit])) DESC"
     )},
    {"code": "DS_CPT_FLUX_TRESORERIE", "nom": "Flux de Trésorerie", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Année] AS [Annee], ec.[Mois], "
         "CAST(ec.[Année] AS VARCHAR) + '-' + RIGHT('0' + CAST(ec.[Mois] AS VARCHAR), 2) AS [Periode], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[Débit] ELSE 0 END) AS [Encaissements], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[Crédit] ELSE 0 END) AS [Decaissements], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Flux Net], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Caisse' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Flux Caisse], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Nature Compte] IN ('Banque', 'Caisse') "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Année], ec.[Mois], ec.societe ORDER BY ec.[Année], ec.[Mois]"
     )},
    {"code": "DS_CPT_TOP_CLIENTS", "nom": "Top Clients par Solde", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT TOP 20 ec.[Compte Tiers], ec.[Intitulé tiers] AS [Client], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Débit]) - SUM(ec.[Crédit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Client' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.societe "
         "HAVING SUM(ec.[Débit]) - SUM(ec.[Crédit]) > 0 "
         "ORDER BY SUM(ec.[Débit]) - SUM(ec.[Crédit]) DESC"
     )},
    {"code": "DS_CPT_TOP_FOURNISSEURS", "nom": "Top Fournisseurs par Solde", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT TOP 20 ec.[Compte Tiers], ec.[Intitulé tiers] AS [Fournisseur], "
         "SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "SUM(ec.[Crédit]) - SUM(ec.[Débit]) AS [Solde], COUNT(*) AS [Nb Ecritures], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Type tiers] = 'Fournisseur' "
         f"AND ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Compte Tiers], ec.[Intitulé tiers], ec.societe "
         "HAVING SUM(ec.[Crédit]) - SUM(ec.[Débit]) > 0 "
         "ORDER BY SUM(ec.[Crédit]) - SUM(ec.[Débit]) DESC"
     )},
    {"code": "DS_CPT_REPARTITION_JOURNAL", "nom": "Répartition par Type Journal", "params": _PARAMS_DATE_SOC,
     "query": (
         "SELECT ec.[Type Code Journal] AS [Type Journal], "
         "SUM(ec.[Débit]) AS [Debit], SUM(ec.[Crédit]) AS [Credit], "
         "COUNT(*) AS [Nb Ecritures], COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
         "ec.societe AS [Societe] FROM Ecritures_Comptables ec "
         f"WHERE ec.[Date d'écriture] BETWEEN @dateDebut AND @dateFin AND {_SOC} "
         "GROUP BY ec.[Type Code Journal], ec.societe ORDER BY SUM(ec.[Débit]) DESC"
     )},
    {"code": "DS_CPT_SYNTHESE_ANNUELLE", "nom": "Synthèse Annuelle Comptable", "params": _PARAMS_SOC_ONLY,
     "query": (
         "SELECT ec.[Exercice], SUM(ec.[Débit]) AS [Total Debit], SUM(ec.[Crédit]) AS [Total Credit], "
         "COUNT(*) AS [Nb Ecritures], COUNT(DISTINCT ec.[N° Compte Général]) AS [Nb Comptes], "
         "COUNT(DISTINCT ec.[Code Journal]) AS [Nb Journaux], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Total Charges], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) AS [Total Produits], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Produit' THEN ec.[Crédit] - ec.[Débit] ELSE 0 END) - "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Charge' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Resultat], "
         "SUM(CASE WHEN ec.[Nature Compte] = 'Banque' THEN ec.[Débit] - ec.[Crédit] ELSE 0 END) AS [Solde Banques], "
         f"ec.societe AS [Societe] FROM Ecritures_Comptables ec WHERE {_SOC} "
         "GROUP BY ec.[Exercice], ec.societe ORDER BY ec.[Exercice]"
     )},
]

# 10 GridViews
_CPT_GRIDVIEWS = [
    "DS_CPT_GRAND_LIVRE", "DS_CPT_BALANCE", "DS_CPT_JOURNAL", "DS_CPT_BALANCE_TIERS",
    "DS_CPT_TRESORERIE", "DS_CPT_CHARGES", "DS_CPT_PRODUITS",
    "DS_CPT_ECHEANCES_CLIENTS", "DS_CPT_ECHEANCES_FOURN", "DS_CPT_LETTRAGE",
]

# 6 PivotGrids: (ds_code, rows, values, filters)
_CPT_PIVOTS = [
    ("DS_CPT_RESULTAT_NATURE",
     [{"field": "Nature Compte"}, {"field": "Classe"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Annee"}]),
    ("DS_CPT_BALANCE_JOURNAL",
     [{"field": "Code Journal"}, {"field": "Journal"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Type Journal"}]),
    ("DS_CPT_BALANCE_CLASSE",
     [{"field": "Classe"}, {"field": "Libelle Classe"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}, {"field": "Nb Ecritures", "aggregation": "sum"}],
     [{"field": "Societe"}, {"field": "Annee"}]),
    ("DS_CPT_TRESO_BANQUE",
     [{"field": "Code Journal"}, {"field": "Banque"}],
     [{"field": "Encaissements", "aggregation": "sum"}, {"field": "Decaissements", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_CPT_SOLDES_CLIENTS",
     [{"field": "Compte Tiers"}, {"field": "Client"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),
    ("DS_CPT_SOLDES_FOURN",
     [{"field": "Compte Tiers"}, {"field": "Fournisseur"}],
     [{"field": "Debit", "aggregation": "sum"}, {"field": "Credit", "aggregation": "sum"}, {"field": "Solde", "aggregation": "sum"}],
     [{"field": "Societe"}]),
]

# 9 Dashboards: (ds_code, nom, widgets)
_CPT_DASHBOARDS = [
    ("DS_CPT_KPI_GLOBAL", "TB Comptabilité Globale", [
        {"id": "w1", "type": "kpi", "title": "Total Débit", "x": 0, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Debit", "format": "currency", "suffix": " DH"}},
        {"id": "w2", "type": "kpi", "title": "Total Crédit", "x": 3, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Credit", "format": "currency", "suffix": " DH"}},
        {"id": "w3", "type": "kpi", "title": "Résultat", "x": 6, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Resultat", "format": "currency", "suffix": " DH",
                    "conditional_color": [{"operator": ">=", "value": 0, "color": "#10b981"}, {"operator": "<", "value": 0, "color": "#ef4444"}]}},
        {"id": "w4", "type": "kpi", "title": "Nb Ecritures", "x": 9, "y": 0, "w": 3, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Ecritures", "format": "number"}},
        {"id": "w5", "type": "kpi", "title": "Total Charges", "x": 0, "y": 3, "w": 4, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Charges", "format": "currency", "suffix": " DH"}},
        {"id": "w6", "type": "kpi", "title": "Total Produits", "x": 4, "y": 3, "w": 4, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Total Produits", "format": "currency", "suffix": " DH"}},
        {"id": "w7", "type": "kpi", "title": "Nb Comptes", "x": 8, "y": 3, "w": 2, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Comptes", "format": "number"}},
        {"id": "w8", "type": "kpi", "title": "Nb Journaux", "x": 10, "y": 3, "w": 2, "h": 3,
         "config": {"dataSourceCode": "DS_CPT_KPI_GLOBAL", "dataSourceOrigin": "template",
                    "value_field": "Nb Journaux", "format": "number"}},
    ]),
    ("DS_CPT_EVOLUTION_MENSUELLE", "Evolution Mensuelle Comptable", [
        {"id": "w1", "type": "bar", "title": "Débit / Crédit par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Total Debit", "Total Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Solde Net Mensuel", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_EVOLUTION_MENSUELLE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Solde Net"],
                    "colors": ["#10b981"]}},
    ]),
    ("DS_CPT_CHARGES_PRODUITS_MENS", "Charges vs Produits", [
        {"id": "w1", "type": "bar", "title": "Charges vs Produits par Mois", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_CHARGES_PRODUITS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Charges", "Produits"],
                    "colors": ["#ef4444", "#10b981"]}},
        {"id": "w2", "type": "line", "title": "Résultat Mensuel", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_CHARGES_PRODUITS_MENS", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Resultat"],
                    "colors": ["#8b5cf6"]}},
    ]),
    ("DS_CPT_REPARTITION_NATURE", "Répartition par Nature Compte", [
        {"id": "w1", "type": "pie", "title": "Répartition par Nature (Volume)", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "category_field": "Nature Compte", "value_field": "Nb Ecritures"}},
        {"id": "w2", "type": "pie", "title": "Répartition par Nature (Montant)", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "category_field": "Nature Compte", "value_field": "Solde Abs"}},
        {"id": "w3", "type": "table", "title": "Détail par Nature", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_NATURE", "dataSourceOrigin": "template",
                    "columns": ["Nature Compte", "Debit", "Credit", "Solde Abs", "Nb Ecritures", "Nb Comptes"]}},
    ]),
    ("DS_CPT_FLUX_TRESORERIE", "Flux de Trésorerie", [
        {"id": "w1", "type": "bar", "title": "Encaissements vs Décaissements", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Encaissements", "Decaissements"],
                    "colors": ["#10b981", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Flux Net Bancaire", "x": 0, "y": 8, "w": 8, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Flux Net"],
                    "colors": ["#3b82f6"]}},
        {"id": "w3", "type": "line", "title": "Flux Caisse", "x": 8, "y": 8, "w": 4, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_FLUX_TRESORERIE", "dataSourceOrigin": "template",
                    "category_field": "Periode", "value_fields": ["Flux Caisse"],
                    "colors": ["#f59e0b"]}},
    ]),
    ("DS_CPT_TOP_CLIENTS", "Top 20 Clients Comptable", [
        {"id": "w1", "type": "bar", "title": "Top 20 Clients par Solde", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_TOP_CLIENTS", "dataSourceOrigin": "template",
                    "category_field": "Client", "value_fields": ["Solde"],
                    "colors": ["#3b82f6"]}},
        {"id": "w2", "type": "table", "title": "Détail Top Clients", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_TOP_CLIENTS", "dataSourceOrigin": "template",
                    "columns": ["Compte Tiers", "Client", "Total Debit", "Total Credit", "Solde", "Nb Ecritures"]}},
    ]),
    ("DS_CPT_TOP_FOURNISSEURS", "Top 20 Fournisseurs Comptable", [
        {"id": "w1", "type": "bar", "title": "Top 20 Fournisseurs par Solde", "x": 0, "y": 0, "w": 12, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_TOP_FOURNISSEURS", "dataSourceOrigin": "template",
                    "category_field": "Fournisseur", "value_fields": ["Solde"],
                    "colors": ["#ef4444"]}},
        {"id": "w2", "type": "table", "title": "Détail Top Fournisseurs", "x": 0, "y": 8, "w": 12, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_TOP_FOURNISSEURS", "dataSourceOrigin": "template",
                    "columns": ["Compte Tiers", "Fournisseur", "Total Debit", "Total Credit", "Solde", "Nb Ecritures"]}},
    ]),
    ("DS_CPT_REPARTITION_JOURNAL", "Répartition par Type Journal", [
        {"id": "w1", "type": "pie", "title": "Volume par Type Journal", "x": 0, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_JOURNAL", "dataSourceOrigin": "template",
                    "category_field": "Type Journal", "value_field": "Nb Ecritures"}},
        {"id": "w2", "type": "bar", "title": "Montants par Type Journal", "x": 6, "y": 0, "w": 6, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_REPARTITION_JOURNAL", "dataSourceOrigin": "template",
                    "category_field": "Type Journal", "value_fields": ["Debit", "Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
    ]),
    ("DS_CPT_SYNTHESE_ANNUELLE", "Synthèse Annuelle Comptable", [
        {"id": "w1", "type": "bar", "title": "Débit / Crédit par Exercice", "x": 0, "y": 0, "w": 8, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Total Debit", "Total Credit"],
                    "colors": ["#3b82f6", "#ef4444"]}},
        {"id": "w2", "type": "line", "title": "Résultat par Exercice", "x": 8, "y": 0, "w": 4, "h": 8,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Resultat"],
                    "colors": ["#10b981"]}},
        {"id": "w3", "type": "bar", "title": "Charges vs Produits par Exercice", "x": 0, "y": 8, "w": 8, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "category_field": "Exercice", "value_fields": ["Total Charges", "Total Produits"],
                    "colors": ["#ef4444", "#10b981"]}},
        {"id": "w4", "type": "kpi", "title": "Solde Banques", "x": 8, "y": 8, "w": 4, "h": 6,
         "config": {"dataSourceCode": "DS_CPT_SYNTHESE_ANNUELLE", "dataSourceOrigin": "template",
                    "value_field": "Solde Banques", "format": "currency", "suffix": " DH"}},
    ]),
]

_CPT_MENU_ICONS = {
    "Grand Livre Général": "BookOpen",
    "Balance Générale": "Scale",
    "Journal des Ecritures": "FileText",
    "Balance Tiers": "Users",
    "Ecritures de Trésorerie": "Landmark",
    "Détail des Charges": "TrendingDown",
    "Détail des Produits": "TrendingUp",
    "Echéances Clients": "Clock",
    "Echéances Fournisseurs": "Timer",
    "Lettrage et Rapprochement": "Link",
    "Résultat par Nature": "PieChart",
    "Balance par Journal": "BookOpen",
    "Balance par Classe": "Layers",
    "Trésorerie par Banque": "Landmark",
    "Soldes Clients": "UserCheck",
    "Soldes Fournisseurs": "Truck",
    "TB Comptabilité Globale": "LayoutGrid",
    "Evolution Mensuelle Comptable": "TrendingUp",
    "Charges vs Produits": "GitCompare",
    "Répartition par Nature Compte": "PieChart",
    "Flux de Trésorerie": "Waves",
    "Top 20 Clients Comptable": "Award",
    "Top 20 Fournisseurs Comptable": "Award",
    "Répartition par Type Journal": "PieChart",
    "Synthèse Annuelle Comptable": "CalendarDays",
}


def _gv_columns_from_query(query: str):
    """Extrait les colonnes d'alias SQL [AS [ColName]] et génère la config GridView."""
    aliases = re.findall(r'AS\s+\[([^\]]+)\]', query, re.IGNORECASE)
    columns = []
    for alias in aliases:
        if alias.lower() == "societe":
            continue
        low = alias.lower()
        fmt = "text"
        if any(k in low for k in ("debit", "credit", "solde", "montant", "valeur", "charge", "produit",
                                   "total", "lettre", "non lettre", "flux", "encaissement", "decaissement",
                                   "resultat", "net")):
            fmt = "currency"
        elif any(k in low for k in ("nb ", "nombre", "nb_")):
            fmt = "number"
        elif "date" in low or "periode" in low or "annee" in low or "mois" in low or "exercice" in low:
            fmt = "date" if "date" in low else "text"
        columns.append({
            "field": alias, "header": alias, "format": fmt,
            "sortable": True, "filterable": True, "width": 150,
        })
    return columns


@router.post("/seed-reports")
async def seed_comptabilite_reports():
    """
    Crée ou met à jour tous les rapports comptabilité :
      - 25 DataSource Templates (DS_CPT_*)
      - 10 GridViews
      - 6 PivotGrids (APP_Pivots_V2)
      - 9 Dashboards
      - Menus (3 sous-dossiers + 25 items)
    """
    result = {
        "datasources": {"inserted": 0, "updated": 0},
        "gridviews": {"inserted": 0, "skipped": 0},
        "pivots": {"inserted": 0, "skipped": 0},
        "dashboards": {"inserted": 0, "skipped": 0},
        "menus": {"inserted": 0, "updated": 0},
        "errors": [],
    }

    # ------------------------------------------------------------------
    # 1. DataSource Templates
    # ------------------------------------------------------------------
    ds_ids: dict = {}
    for ds in _CPT_DS_TEMPLATES:
        try:
            existing = execute_central_query(
                "SELECT id FROM APP_DataSources_Templates WHERE code = ?", (ds["code"],)
            )
            if existing:
                write_central(
                    "UPDATE APP_DataSources_Templates SET nom=?, query_template=?, parameters=?, category=?, actif=1 WHERE code=?",
                    (ds["nom"], ds["query"], ds["params"], "comptabilite", ds["code"]),
                )
                ds_ids[ds["code"]] = existing[0]["id"]
                result["datasources"]["updated"] += 1
            else:
                write_central(
                    "INSERT INTO APP_DataSources_Templates (code, nom, description, query_template, parameters, category, actif) VALUES (?, ?, ?, ?, ?, 'comptabilite', 1)",
                    (ds["code"], ds["nom"], ds["nom"], ds["query"], ds["params"]),
                )
                row = execute_central_query("SELECT id FROM APP_DataSources_Templates WHERE code = ?", (ds["code"],))
                ds_ids[ds["code"]] = row[0]["id"] if row else None
                result["datasources"]["inserted"] += 1
        except Exception as e:
            result["errors"].append({"step": "datasource", "code": ds["code"], "error": str(e)})

    # ------------------------------------------------------------------
    # 2. GridViews
    # ------------------------------------------------------------------
    gv_ids: dict = {}
    for ds_code in _CPT_GRIDVIEWS:
        try:
            existing = execute_central_query(
                "SELECT id FROM APP_GridViews WHERE data_source_code = ?", (ds_code,)
            )
            if existing:
                gv_ids[ds_code] = existing[0]["id"]
                result["gridviews"]["skipped"] += 1
                continue

            ds_row = execute_central_query(
                "SELECT nom, query_template FROM APP_DataSources_Templates WHERE code = ?", (ds_code,)
            )
            if not ds_row:
                result["errors"].append({"step": "gridview", "code": ds_code, "error": "datasource not found"})
                continue

            nom = ds_row[0]["nom"]
            query = ds_row[0]["query_template"]
            columns = _gv_columns_from_query(query)
            total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number")][:5]
            features = {"show_search": True, "show_column_filters": True, "show_grouping": True,
                        "show_column_toggle": True, "show_export": True, "show_pagination": True,
                        "allow_sorting": True}

            write_central(
                "INSERT INTO APP_GridViews (nom, description, data_source_code, columns_config, page_size, show_totals, total_columns, features, actif) VALUES (?, ?, ?, ?, 25, 1, ?, ?, 1)",
                (nom, f"Rapport Comptabilité - {nom}", ds_code,
                 json.dumps(columns, ensure_ascii=False),
                 json.dumps(total_cols, ensure_ascii=False),
                 json.dumps(features, ensure_ascii=False)),
            )
            row = execute_central_query("SELECT id FROM APP_GridViews WHERE data_source_code = ?", (ds_code,))
            gv_ids[ds_code] = row[0]["id"] if row else None
            result["gridviews"]["inserted"] += 1
        except Exception as e:
            result["errors"].append({"step": "gridview", "code": ds_code, "error": str(e)})

    # ------------------------------------------------------------------
    # 3. PivotGrids (APP_Pivots_V2)
    # ------------------------------------------------------------------
    pv_ids: dict = {}
    for ds_code, rows_cfg, vals_cfg, filters_cfg in _CPT_PIVOTS:
        try:
            existing = execute_central_query(
                "SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ?", (ds_code,)
            )
            if existing:
                pv_ids[ds_code] = existing[0]["id"]
                result["pivots"]["skipped"] += 1
                continue

            ds_row = execute_central_query(
                "SELECT nom FROM APP_DataSources_Templates WHERE code = ?", (ds_code,)
            )
            nom = ds_row[0]["nom"] if ds_row else ds_code

            write_central(
                "INSERT INTO APP_Pivots_V2 (nom, description, data_source_code, rows_config, columns_config, values_config, filters_config, show_grand_totals, show_subtotals) VALUES (?, ?, ?, ?, '[]', ?, ?, 1, 1)",
                (nom, f"Pivot Comptabilité - {nom}", ds_code,
                 json.dumps(rows_cfg, ensure_ascii=False),
                 json.dumps(vals_cfg, ensure_ascii=False),
                 json.dumps(filters_cfg, ensure_ascii=False)),
            )
            row = execute_central_query("SELECT id FROM APP_Pivots_V2 WHERE data_source_code = ?", (ds_code,))
            pv_ids[ds_code] = row[0]["id"] if row else None
            result["pivots"]["inserted"] += 1
        except Exception as e:
            result["errors"].append({"step": "pivot", "code": ds_code, "error": str(e)})

    # ------------------------------------------------------------------
    # 4. Dashboards
    # ------------------------------------------------------------------
    db_ids: dict = {}
    for ds_code, nom, widgets in _CPT_DASHBOARDS:
        try:
            existing = execute_central_query(
                "SELECT id FROM APP_Dashboards WHERE nom = ?", (nom,)
            )
            if existing:
                db_ids[ds_code] = existing[0]["id"]
                result["dashboards"]["skipped"] += 1
                continue

            write_central(
                "INSERT INTO APP_Dashboards (nom, description, widgets, actif) VALUES (?, ?, ?, 1)",
                (nom, f"Dashboard Comptabilité - {nom}", json.dumps(widgets, ensure_ascii=False)),
            )
            row = execute_central_query("SELECT id FROM APP_Dashboards WHERE nom = ?", (nom,))
            db_ids[ds_code] = row[0]["id"] if row else None
            result["dashboards"]["inserted"] += 1
        except Exception as e:
            result["errors"].append({"step": "dashboard", "code": ds_code, "error": str(e)})

    # ------------------------------------------------------------------
    # 5. Menus
    # ------------------------------------------------------------------
    try:
        root = execute_central_query(
            "SELECT id FROM APP_Menus WHERE (nom = 'Comptabilité' OR nom = 'Comptabilite') AND parent_id IS NULL"
        )
        if root:
            root_id = root[0]["id"]
        else:
            write_central(
                "INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES ('Comptabilité', 'Calculator', 'folder', NULL, 30, 1)"
            )
            root_id = execute_central_query(
                "SELECT id FROM APP_Menus WHERE nom = 'Comptabilité' AND parent_id IS NULL"
            )[0]["id"]
            result["menus"]["inserted"] += 1

        subfolders = [
            ("Documents Comptables", "FileText", 1),
            ("Analyses Comptables", "BarChart3", 2),
            ("Tableaux de Bord", "LayoutGrid", 3),
        ]
        sf_ids: dict = {}
        for sf_label, sf_icon, sf_ordre in subfolders:
            sf = execute_central_query(
                "SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", (sf_label, root_id)
            )
            if sf:
                sf_ids[sf_label] = sf[0]["id"]
            else:
                write_central(
                    "INSERT INTO APP_Menus (nom, icon, type, parent_id, ordre, actif) VALUES (?, ?, 'folder', ?, ?, 1)",
                    (sf_label, sf_icon, root_id, sf_ordre),
                )
                sf_ids[sf_label] = execute_central_query(
                    "SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", (sf_label, root_id)
                )[0]["id"]
                result["menus"]["inserted"] += 1

        menu_items = [
            ("Documents Comptables", "Grand Livre Général",       "gridview",  gv_ids.get("DS_CPT_GRAND_LIVRE"), 1),
            ("Documents Comptables", "Balance Générale",          "gridview",  gv_ids.get("DS_CPT_BALANCE"), 2),
            ("Documents Comptables", "Journal des Ecritures",     "gridview",  gv_ids.get("DS_CPT_JOURNAL"), 3),
            ("Documents Comptables", "Balance Tiers",             "gridview",  gv_ids.get("DS_CPT_BALANCE_TIERS"), 4),
            ("Documents Comptables", "Ecritures de Trésorerie",   "gridview",  gv_ids.get("DS_CPT_TRESORERIE"), 5),
            ("Documents Comptables", "Détail des Charges",        "gridview",  gv_ids.get("DS_CPT_CHARGES"), 6),
            ("Documents Comptables", "Détail des Produits",       "gridview",  gv_ids.get("DS_CPT_PRODUITS"), 7),
            ("Documents Comptables", "Echéances Clients",         "gridview",  gv_ids.get("DS_CPT_ECHEANCES_CLIENTS"), 8),
            ("Documents Comptables", "Echéances Fournisseurs",    "gridview",  gv_ids.get("DS_CPT_ECHEANCES_FOURN"), 9),
            ("Documents Comptables", "Lettrage et Rapprochement", "gridview",  gv_ids.get("DS_CPT_LETTRAGE"), 10),
            ("Analyses Comptables",  "Résultat par Nature",       "pivot-v2",  pv_ids.get("DS_CPT_RESULTAT_NATURE"), 1),
            ("Analyses Comptables",  "Balance par Journal",       "pivot-v2",  pv_ids.get("DS_CPT_BALANCE_JOURNAL"), 2),
            ("Analyses Comptables",  "Balance par Classe",        "pivot-v2",  pv_ids.get("DS_CPT_BALANCE_CLASSE"), 3),
            ("Analyses Comptables",  "Trésorerie par Banque",     "pivot-v2",  pv_ids.get("DS_CPT_TRESO_BANQUE"), 4),
            ("Analyses Comptables",  "Soldes Clients",            "pivot-v2",  pv_ids.get("DS_CPT_SOLDES_CLIENTS"), 5),
            ("Analyses Comptables",  "Soldes Fournisseurs",       "pivot-v2",  pv_ids.get("DS_CPT_SOLDES_FOURN"), 6),
            ("Tableaux de Bord",     "TB Comptabilité Globale",   "dashboard", db_ids.get("DS_CPT_KPI_GLOBAL"), 1),
            ("Tableaux de Bord",     "Evolution Mensuelle Comptable", "dashboard", db_ids.get("DS_CPT_EVOLUTION_MENSUELLE"), 2),
            ("Tableaux de Bord",     "Charges vs Produits",       "dashboard", db_ids.get("DS_CPT_CHARGES_PRODUITS_MENS"), 3),
            ("Tableaux de Bord",     "Répartition par Nature Compte", "dashboard", db_ids.get("DS_CPT_REPARTITION_NATURE"), 4),
            ("Tableaux de Bord",     "Flux de Trésorerie",        "dashboard", db_ids.get("DS_CPT_FLUX_TRESORERIE"), 5),
            ("Tableaux de Bord",     "Top 20 Clients Comptable",  "dashboard", db_ids.get("DS_CPT_TOP_CLIENTS"), 6),
            ("Tableaux de Bord",     "Top 20 Fournisseurs Comptable", "dashboard", db_ids.get("DS_CPT_TOP_FOURNISSEURS"), 7),
            ("Tableaux de Bord",     "Répartition par Type Journal", "dashboard", db_ids.get("DS_CPT_REPARTITION_JOURNAL"), 8),
            ("Tableaux de Bord",     "Synthèse Annuelle Comptable", "dashboard", db_ids.get("DS_CPT_SYNTHESE_ANNUELLE"), 9),
        ]

        for sf_label, label, menu_type, target_id, ordre in menu_items:
            if target_id is None:
                continue
            parent_id = sf_ids.get(sf_label)
            if parent_id is None:
                continue
            icon = _CPT_MENU_ICONS.get(label, "FileText")
            existing = execute_central_query(
                "SELECT id FROM APP_Menus WHERE nom = ? AND parent_id = ?", (label, parent_id)
            )
            if existing:
                write_central(
                    "UPDATE APP_Menus SET icon=?, type=?, target_id=?, ordre=?, actif=1 WHERE id=?",
                    (icon, menu_type, target_id, ordre, existing[0]["id"]),
                )
                result["menus"]["updated"] += 1
            else:
                write_central(
                    "INSERT INTO APP_Menus (nom, icon, type, target_id, parent_id, ordre, actif) VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (label, icon, menu_type, target_id, parent_id, ordre),
                )
                result["menus"]["inserted"] += 1
    except Exception as e:
        result["errors"].append({"step": "menus", "error": str(e)})

    total = (result["datasources"]["inserted"] + result["datasources"]["updated"]
             + result["gridviews"]["inserted"] + result["pivots"]["inserted"]
             + result["dashboards"]["inserted"] + result["menus"]["inserted"])
    return {
        "success": len(result["errors"]) == 0,
        "summary": result,
        "message": (
            f"Comptabilité : {result['datasources']['inserted']} DS créées, "
            f"{result['datasources']['updated']} DS mises à jour, "
            f"{result['gridviews']['inserted']} GridViews, "
            f"{result['pivots']['inserted']} Pivots, "
            f"{result['dashboards']['inserted']} Dashboards, "
            f"{result['menus']['inserted']} menus créés."
        ),
    }


# =============================================================================
# FIX : Rattacher les datasources aux GridViews existants (data_source_code vide)
# =============================================================================

_GV_NAME_TO_DS = {
    "Grand Livre Général":        "DS_CPT_GRAND_LIVRE",
    "Grand Livre":                "DS_CPT_GRAND_LIVRE",
    "Balance Générale":           "DS_CPT_BALANCE",
    "Balance Generale":           "DS_CPT_BALANCE",
    "Journal des Écritures":      "DS_CPT_JOURNAL",
    "Journal des Ecritures":      "DS_CPT_JOURNAL",
    "Balance Tiers":              "DS_CPT_BALANCE_TIERS",
    "Ecritures de Trésorerie":    "DS_CPT_TRESORERIE",
    "Détail des Charges":         "DS_CPT_CHARGES",
    "Detail des Charges":         "DS_CPT_CHARGES",
    "Détail des Produits":        "DS_CPT_PRODUITS",
    "Detail des Produits":        "DS_CPT_PRODUITS",
    "Echéances Clients":          "DS_CPT_ECHEANCES_CLIENTS",
    "Échéances Clients":          "DS_CPT_ECHEANCES_CLIENTS",
    "Echéances Fournisseurs":     "DS_CPT_ECHEANCES_FOURN",
    "Échéances Fournisseurs":     "DS_CPT_ECHEANCES_FOURN",
    "Lettrage et Rapprochement":  "DS_CPT_LETTRAGE",
    "Résultat par Nature":        "DS_CPT_RESULTAT_NATURE",
    "Balance par Journal":        "DS_CPT_BALANCE_JOURNAL",
    "Balance par Classe":         "DS_CPT_BALANCE_CLASSE",
    "Trésorerie par Banque":      "DS_CPT_TRESO_BANQUE",
    "Soldes Clients":             "DS_CPT_SOLDES_CLIENTS",
    "Soldes Fournisseurs":        "DS_CPT_SOLDES_FOURN",
}


@router.post("/fix-gridviews")
async def fix_comptabilite_gridviews():
    """
    Rattache les datasources DS_CPT_* aux GridViews comptabilité
    dont le champ data_source_code est vide ou NULL.
    Aussi met à jour columns_config depuis la requête du datasource.
    """
    fixed, skipped, errors = 0, 0, []

    # Récupérer tous les GridViews sans datasource
    all_gv = execute_central_query(
        "SELECT id, nom, data_source_code FROM APP_GridViews WHERE data_source_code IS NULL OR data_source_code = ''",
        use_cache=False,
    )

    for gv in all_gv:
        nom = gv["nom"]
        gv_id = gv["id"]
        ds_code = _GV_NAME_TO_DS.get(nom)
        if not ds_code:
            skipped += 1
            continue

        try:
            # Vérifier que le datasource existe
            ds_row = execute_central_query(
                "SELECT nom, query_template FROM APP_DataSources_Templates WHERE code = ?",
                (ds_code,),
                use_cache=False,
            )
            if not ds_row:
                errors.append({"gv_id": gv_id, "nom": nom, "error": f"{ds_code} not found in templates"})
                continue

            query = ds_row[0]["query_template"]

            # Re-générer les colonnes depuis la requête
            columns = _gv_columns_from_query(query)
            total_cols = [c["field"] for c in columns if c["format"] in ("currency", "number")][:5]
            features = {
                "show_search": True, "show_column_filters": True, "show_grouping": True,
                "show_column_toggle": True, "show_export": True, "show_pagination": True,
                "allow_sorting": True,
            }

            write_central(
                """UPDATE APP_GridViews
                   SET data_source_code = ?,
                       columns_config   = ?,
                       total_columns    = ?,
                       features         = ?,
                       show_totals      = 1,
                       page_size        = 25
                   WHERE id = ?""",
                (ds_code,
                 json.dumps(columns, ensure_ascii=False),
                 json.dumps(total_cols, ensure_ascii=False),
                 json.dumps(features, ensure_ascii=False),
                 gv_id),
            )
            fixed += 1
            logger.info(f"[FIX-GV] id={gv_id} '{nom}' → {ds_code}")
        except Exception as e:
            errors.append({"gv_id": gv_id, "nom": nom, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "fixed": fixed,
        "skipped": skipped,
        "errors": errors,
        "message": f"{fixed} GridViews mis à jour avec leur datasource DS_CPT_*.",
    }
