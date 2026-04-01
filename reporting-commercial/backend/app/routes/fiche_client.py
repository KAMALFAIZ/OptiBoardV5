"""Fiche Client - Vue 360° d'un client (KPIs, balance âgée, factures, règlements, CA, documents)"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date

from ..database_unified import execute_app as execute_query
from ..sql.query_templates import (
    BALANCE_AGEE,
    CA_EVOLUTION_CLIENT,
    CA_TOTAL_CLIENT,
    TOP_PRODUITS_CLIENT,
    ECHEANCES_NON_REGLEES_CLIENT,
    HISTORIQUE_REGLEMENTS_CLIENT,
    INFO_CLIENT,
    DOCUMENTS_VENTES_CLIENT,
)
from ..services.calculs import get_periode_dates, parse_number

router = APIRouter(prefix="/api/fiche-client", tags=["Fiche Client"])


def _parse_balance_row(row: dict) -> dict:
    return {
        "code_client": (row.get("CLIENTS") or row.get("CLIENTS ") or "").strip(),
        "nom_client": (row.get("CLIENTS") or row.get("CLIENTS ") or "").strip(),
        "commercial": row.get("Representant") or row.get("Représenant") or "",
        "societe": row.get("SOCIETE") or "",
        "encours": parse_number(row.get("Solde_Cloture") or row.get("Solde Clôture") or 0),
        "impayes": parse_number(row.get("Impayes") or row.get("Impayés") or 0),
        "tranche_0_30": parse_number(row.get("0-30") or 0),
        "tranche_31_60": parse_number(row.get("31-60") or 0),
        "tranche_61_90": parse_number(row.get("61-90") or 0),
        "tranche_91_120": parse_number(row.get("91-120") or 0),
        "tranche_plus_120": parse_number(row.get("+120") or 0),
    }


def _safe_float(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_str(v) -> str:
    if v is None or str(v) in ("None", "null"):
        return ""
    return str(v)


@router.get("/liste")
async def get_liste_clients():
    """Retourne la liste de tous les clients agrégés (balance âgée, toutes sociétés confondues)."""
    try:
        rows = execute_query(BALANCE_AGEE)
        aggregated: dict = {}
        for row in rows:
            parsed = _parse_balance_row(row)
            nom = parsed["code_client"]
            if not nom:
                continue
            if nom not in aggregated:
                aggregated[nom] = {**parsed, "societes": [parsed["societe"]] if parsed["societe"] else []}
            else:
                aggregated[nom]["encours"] += parsed["encours"]
                aggregated[nom]["impayes"] += parsed["impayes"]
                aggregated[nom]["tranche_0_30"] += parsed["tranche_0_30"]
                aggregated[nom]["tranche_31_60"] += parsed["tranche_31_60"]
                aggregated[nom]["tranche_61_90"] += parsed["tranche_61_90"]
                aggregated[nom]["tranche_91_120"] += parsed["tranche_91_120"]
                aggregated[nom]["tranche_plus_120"] += parsed["tranche_plus_120"]
                if parsed["societe"] and parsed["societe"] not in aggregated[nom]["societes"]:
                    aggregated[nom]["societes"].append(parsed["societe"])

        clients_sorted = sorted(aggregated.values(), key=lambda x: x["encours"], reverse=True)
        return {"success": True, "data": list(clients_sorted), "total": len(clients_sorted)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{code_client}")
async def get_fiche_client(
    code_client: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
):
    """Retourne la fiche complète d'un client : KPIs, infos, balance âgée, documents,
    factures non réglées, historique règlements, évolution CA, top produits."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        client_name = code_client.strip()

        # ── 1. Balance âgée (agrégée sur toutes sociétés) ─────────────────────
        all_balance = execute_query(BALANCE_AGEE)
        client_balance = None
        for row in all_balance:
            nom = (row.get("CLIENTS") or row.get("CLIENTS ") or "").strip()
            if nom != client_name:
                continue
            parsed = _parse_balance_row(row)
            if client_balance is None:
                client_balance = parsed
            else:
                for key in ("encours", "impayes", "tranche_0_30", "tranche_31_60",
                            "tranche_61_90", "tranche_91_120", "tranche_plus_120"):
                    client_balance[key] += parsed[key]

        if client_balance is None:
            client_balance = {
                "code_client": client_name, "nom_client": client_name,
                "commercial": "", "societe": "",
                "encours": 0, "impayes": 0,
                "tranche_0_30": 0, "tranche_31_60": 0, "tranche_61_90": 0,
                "tranche_91_120": 0, "tranche_plus_120": 0,
            }

        # ── 2. Infos client Sage (plafond, risque, contacts) ──────────────────
        try:
            info_rows = execute_query(INFO_CLIENT, (client_name,))
            info_sage = info_rows[0] if info_rows else {}
        except Exception:
            info_sage = {}

        # ── 3. CA total + évolution mensuelle ─────────────────────────────────
        try:
            ca_total_rows = execute_query(CA_TOTAL_CLIENT, (client_name, date_debut_str, date_fin_str))
            ca_info = ca_total_rows[0] if ca_total_rows else {}
        except Exception:
            ca_info = {}

        try:
            ca_evolution = execute_query(CA_EVOLUTION_CLIENT, (client_name, date_debut_str, date_fin_str))
        except Exception:
            ca_evolution = []

        # ── 4. Top produits ───────────────────────────────────────────────────
        try:
            top_produits = execute_query(TOP_PRODUITS_CLIENT, (client_name, date_debut_str, date_fin_str))
        except Exception:
            top_produits = []

        # ── 5. Documents ventes (BL, Factures, Commandes, Devis…) ────────────
        try:
            documents = execute_query(DOCUMENTS_VENTES_CLIENT, (client_name, date_debut_str, date_fin_str))
        except Exception:
            documents = []

        # ── 6. Échéances non réglées ──────────────────────────────────────────
        try:
            echeances = execute_query(ECHEANCES_NON_REGLEES_CLIENT, (client_name,))
        except Exception:
            echeances = []

        # ── 7. Historique règlements ──────────────────────────────────────────
        try:
            reglements = execute_query(HISTORIQUE_REGLEMENTS_CLIENT, (client_name,))
        except Exception:
            reglements = []

        # ── 8. KPIs calculés ──────────────────────────────────────────────────
        encours = client_balance["encours"]
        ca_ht = _safe_float(ca_info.get("CA_HT"))
        ca_ttc = _safe_float(ca_info.get("CA_TTC"))

        total_regle_reglements = sum(_safe_float(r.get("Montant réglement") or r.get("Montant_reglement")) for r in reglements)
        total_echeances = sum(_safe_float(e.get("Montant_Echeance") or e.get("Montant échéance")) for e in echeances)

        taux_reglement = round(total_regle_reglements / (total_regle_reglements + encours) * 100, 1) if (total_regle_reglements + encours) > 0 else 0
        dso_client = round((encours / ca_ttc) * 365, 0) if ca_ttc > 0 else 0

        dernier_reglement = None
        if reglements:
            dates = [r.get("Date réglement") for r in reglements if r.get("Date réglement")]
            if dates:
                dernier_reglement = _safe_str(max(dates))

        # Résumé documents par type
        docs_summary: dict = {}
        for doc in documents:
            t = doc.get("Type Document") or "Autre"
            if t not in docs_summary:
                docs_summary[t] = {"count": 0, "montant_ttc": 0.0}
            docs_summary[t]["count"] += 1
            docs_summary[t]["montant_ttc"] += _safe_float(doc.get("Montant TTC"))

        return {
            "success": True,
            "client": {
                "code": code_client,
                "nom": _safe_str(ca_info.get("Nom_Client")) or client_name,
                "commercial": client_balance["commercial"] or _safe_str(ca_info.get("Commercial")) or _safe_str(info_sage.get("Représentant")),
                "societe": client_balance["societe"] or "",
            },
            "info_sage": {
                "code_sage": _safe_str(info_sage.get("Code client")),
                "risque_client": _safe_str(info_sage.get("Risque client")) or "—",
                "plafond_autorisation": _safe_float(info_sage.get("Plafond_Autorisation")),
                "assurance": _safe_float(info_sage.get("Assurance")),
                "telephone": _safe_str(info_sage.get("Téléphone")),
                "email": _safe_str(info_sage.get("Email")),
                "adresse": _safe_str(info_sage.get("Adresse")),
                "ville": _safe_str(info_sage.get("Ville")),
                "ice": _safe_str(info_sage.get("ICE")),
                "rc": _safe_str(info_sage.get("RC")),
                "capital": _safe_float(info_sage.get("Capital")),
                "forme_juridique": _safe_str(info_sage.get("Forme_Juridique")),
            },
            "kpis": {
                "encours": round(encours, 2),
                "impayes": round(client_balance["impayes"], 2),
                "ca_ht": round(ca_ht, 2),
                "ca_ttc": round(ca_ttc, 2),
                "nb_transactions": int(ca_info.get("Nb_Transactions") or 0),
                "nb_produits": int(ca_info.get("Nb_Produits_Distincts") or 0),
                "taux_reglement": taux_reglement,
                "dso_client": int(dso_client),
                "nb_factures_impayees": len(echeances),
                "total_factures_impayees": round(total_echeances, 2),
                "nb_documents": len(documents),
                "dernier_reglement": dernier_reglement,
                "tranche_plus_120": round(client_balance["tranche_plus_120"], 2),
                "plafond": _safe_float(info_sage.get("Plafond_Autorisation")),
                "risque": _safe_str(info_sage.get("Risque client")) or "—",
            },
            "balance_agee": {
                "a_echoir": 0,
                "tranche_0_30": round(client_balance["tranche_0_30"], 2),
                "tranche_31_60": round(client_balance["tranche_31_60"], 2),
                "tranche_61_90": round(client_balance["tranche_61_90"], 2),
                "tranche_91_120": round(client_balance["tranche_91_120"], 2),
                "tranche_plus_120": round(client_balance["tranche_plus_120"], 2),
            },
            "ca_evolution": [
                {
                    "mois": f"{int(r.get('Annee', 0))}-{int(r.get('Mois', 0)):02d}",
                    "ca_ht": round(_safe_float(r.get("CA_HT")), 2),
                    "ca_ttc": round(_safe_float(r.get("CA_TTC")), 2),
                    "nb_transactions": int(r.get("Nb_Transactions") or 0),
                }
                for r in ca_evolution
            ],
            "top_produits": [
                {
                    "code_article": _safe_str(r.get("Code_Article")),
                    "designation": _safe_str(r.get("Designation")),
                    "gamme": _safe_str(r.get("Gamme")),
                    "quantite": _safe_float(r.get("Quantite_Vendue")),
                    "ca_ht": round(_safe_float(r.get("CA_HT")), 2),
                }
                for r in top_produits
            ],
            "documents": [
                {
                    "societe": _safe_str(r.get("Societe")),
                    "type_doc": _safe_str(r.get("Type Document")),
                    "souche": _safe_str(r.get("Souche")),
                    "num_piece": _safe_str(r.get("Num_Piece")),
                    "date": _safe_str(r.get("Date")),
                    "montant_ht": round(_safe_float(r.get("Montant_HT")), 2),
                    "montant_ttc": round(_safe_float(r.get("Montant TTC")), 2),
                    "montant_regle": round(_safe_float(r.get("Montant_Regle")), 2),
                    "reste_a_regler": round(_safe_float(r.get("Reste_A_Regler")), 2),
                    "statut": _safe_str(r.get("Statut")),
                    "commercial": _safe_str(r.get("Commercial")),
                }
                for r in documents
            ],
            "docs_summary": [
                {"type_doc": t, "count": v["count"], "montant_ttc": round(v["montant_ttc"], 2)}
                for t, v in sorted(docs_summary.items(), key=lambda x: x[1]["montant_ttc"], reverse=True)
            ],
            "echeances": [
                {
                    "societe": _safe_str(r.get("Societe")),
                    "type_doc": _safe_str(r.get("Type Document")),
                    "num_piece": _safe_str(r.get("Num_Piece")),
                    "date_document": _safe_str(r.get("Date document")),
                    "date_echeance": _safe_str(r.get("Date_Echeance") or r.get("Date d'échéance")),
                    "montant_echeance": round(_safe_float(r.get("Montant_Echeance") or r.get("Montant échéance")), 2),
                    "montant_regle": round(_safe_float(r.get("Montant_Regle") or r.get("Régler")), 2),
                    "reste_a_regler": round(_safe_float(r.get("Reste_A_Regler")), 2),
                    "jours_retard": int(r.get("Jours_Retard") or 0),
                    "tranche_age": _safe_str(r.get("Tranche_Age")),
                    "mode_reglement": _safe_str(r.get("Mode_Reglement") or r.get("Mode de réglement")),
                }
                for r in echeances
            ],
            "reglements": [
                {
                    "date_reglement": _safe_str(r.get("Date réglement")),
                    "num_piece": _safe_str(r.get("Num_Piece")),
                    "type_doc": _safe_str(r.get("Type Document")),
                    "date_document": _safe_str(r.get("Date document")),
                    "montant_facture": round(_safe_float(r.get("Montant facture TTC") or r.get("Montant TTC")), 2),
                    "montant_reglement": round(_safe_float(r.get("Montant réglement")), 2),
                    "mode_reglement": _safe_str(r.get("Mode_Reglement") or r.get("Mode de réglement")),
                    "delai_jours": int(r.get("Delai_Reglement_Jours") or 0),
                }
                for r in reglements
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
