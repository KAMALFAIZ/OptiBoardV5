"""Fiche Fournisseur - Vue 360° d'un fournisseur (KPIs, échéances, documents achats, paiements)"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date

from ..database_unified import execute_dwh as execute_query
from ..sql.query_templates import (
    LISTE_FOURNISSEURS,
    LISTE_FOURNISSEURS_SAGE,
    INFO_FOURNISSEUR,
    DOCUMENTS_ACHATS_FOURNISSEUR,
    ECHEANCES_NON_REGLEES_FOURNISSEUR,
    HISTORIQUE_PAIEMENTS_FOURNISSEUR,
    ACHATS_EVOLUTION_FOURNISSEUR,
    ACHATS_TOTAL_FOURNISSEUR,
)
from ..services.calculs import get_periode_dates, parse_number

router = APIRouter(prefix="/api/fiche-fournisseur", tags=["Fiche Fournisseur"])


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
async def get_liste_fournisseurs():
    """Retourne la liste agrégée des fournisseurs.
    Fallback sur le CTE Fournisseurs (F_COMPTET CT_Type=1) si Situation_Fournisseurs vide."""
    import logging
    _log = logging.getLogger(__name__)
    try:
        # 1. Essayer Situation_Fournisseurs (DWH)
        rows = []
        try:
            rows = execute_query(LISTE_FOURNISSEURS)
        except Exception as e:
            _log.warning(f"Situation_Fournisseurs non disponible: {e}")

        if rows:
            aggregated: dict = {}
            for row in rows:
                nom = (row.get("Nom_Fournisseur") or "").strip()
                if not nom:
                    continue
                solde = _safe_float(row.get("Solde"))
                total_achats = _safe_float(row.get("Total_Achats"))
                total_regle = _safe_float(row.get("Total_Regle"))
                societe = row.get("Societe") or ""
                if nom not in aggregated:
                    aggregated[nom] = {
                        "nom_fournisseur": nom,
                        "code_fournisseur": row.get("Code fournisseur") or "",
                        "acheteur": row.get("Acheteur") or "",
                        "total_achats": total_achats,
                        "total_regle": total_regle,
                        "solde": solde,
                        "societes": [societe] if societe else [],
                    }
                else:
                    aggregated[nom]["total_achats"] += total_achats
                    aggregated[nom]["total_regle"] += total_regle
                    aggregated[nom]["solde"] += solde
                    if societe and societe not in aggregated[nom]["societes"]:
                        aggregated[nom]["societes"].append(societe)
            sorted_list = sorted(aggregated.values(), key=lambda x: x["solde"], reverse=True)
            return {"success": True, "data": sorted_list, "total": len(sorted_list)}

        # 2. Fallback : CTE Fournisseurs (F_COMPTET CT_Type=1)
        _log.info("Situation_Fournisseurs vide — fallback sur CTE Fournisseurs (F_COMPTET)")
        try:
            sage_rows = execute_query(LISTE_FOURNISSEURS_SAGE)
        except Exception as e:
            _log.warning(f"CTE Fournisseurs non disponible: {e}")
            sage_rows = []

        fournisseurs_fallback = []
        for r in sage_rows:
            nom = _safe_str(r.get("nom_fournisseur") or r.get("code_fournisseur") or "").strip()
            if not nom:
                continue
            fournisseurs_fallback.append({
                "nom_fournisseur": nom,
                "code_fournisseur": _safe_str(r.get("code_fournisseur") or nom).strip(),
                "acheteur": _safe_str(r.get("acheteur") or ""),
                "total_achats": 0.0,
                "total_regle": 0.0,
                "solde": 0.0,
                "societes": [],
            })

        fournisseurs_fallback.sort(key=lambda x: x["nom_fournisseur"])
        return {"success": True, "data": fournisseurs_fallback, "total": len(fournisseurs_fallback)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{nom_fournisseur}")
async def get_fiche_fournisseur(
    nom_fournisseur: str,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    periode: Optional[str] = Query("annee_courante"),
):
    """Retourne la fiche complète d'un fournisseur."""
    try:
        if not date_debut or not date_fin:
            date_debut_str, date_fin_str = get_periode_dates(periode)
        else:
            date_debut_str = date_debut.strftime("%Y-%m-%d")
            date_fin_str = date_fin.strftime("%Y-%m-%d")

        fournisseur_name = nom_fournisseur.strip()

        # ── 1. Situation agrégée ───────────────────────────────────────────────
        try:
            all_situation = execute_query(LISTE_FOURNISSEURS)
            situation = None
            for row in all_situation:
                nom = (row.get("Nom_Fournisseur") or "").strip()
                if nom != fournisseur_name:
                    continue
                if situation is None:
                    situation = {
                        "nom_fournisseur": nom,
                        "code_fournisseur": row.get("Code fournisseur") or "",
                        "acheteur": row.get("Acheteur") or "",
                        "total_achats": _safe_float(row.get("Total_Achats")),
                        "total_regle": _safe_float(row.get("Total_Regle")),
                        "solde": _safe_float(row.get("Solde")),
                    }
                else:
                    situation["total_achats"] += _safe_float(row.get("Total_Achats"))
                    situation["total_regle"] += _safe_float(row.get("Total_Regle"))
                    situation["solde"] += _safe_float(row.get("Solde"))
            if situation is None:
                situation = {
                    "nom_fournisseur": fournisseur_name,
                    "code_fournisseur": "",
                    "acheteur": "",
                    "total_achats": 0,
                    "total_regle": 0,
                    "solde": 0,
                }
        except Exception:
            situation = {"nom_fournisseur": fournisseur_name, "code_fournisseur": "", "acheteur": "", "total_achats": 0, "total_regle": 0, "solde": 0}

        # ── 2. Infos fournisseur Sage ─────────────────────────────────────────
        try:
            info_rows = execute_query(INFO_FOURNISSEUR, (fournisseur_name,))
            info_sage = info_rows[0] if info_rows else {}
        except Exception:
            info_sage = {}

        # ── 3. Total achats + évolution ────────────────────────────────────────
        try:
            achats_total_rows = execute_query(ACHATS_TOTAL_FOURNISSEUR, (fournisseur_name, date_debut_str, date_fin_str))
            achats_info = achats_total_rows[0] if achats_total_rows else {}
        except Exception:
            achats_info = {}

        try:
            achats_evolution = execute_query(ACHATS_EVOLUTION_FOURNISSEUR, (fournisseur_name, date_debut_str, date_fin_str))
        except Exception:
            achats_evolution = []

        # ── 4. Documents achats ────────────────────────────────────────────────
        try:
            documents = execute_query(DOCUMENTS_ACHATS_FOURNISSEUR, (fournisseur_name, date_debut_str, date_fin_str))
        except Exception:
            documents = []

        # ── 5. Échéances non réglées ──────────────────────────────────────────
        try:
            echeances = execute_query(ECHEANCES_NON_REGLEES_FOURNISSEUR, (fournisseur_name,))
        except Exception:
            echeances = []

        # ── 6. Historique paiements ────────────────────────────────────────────
        try:
            paiements = execute_query(HISTORIQUE_PAIEMENTS_FOURNISSEUR, (fournisseur_name,))
        except Exception:
            paiements = []

        # ── 7. KPIs ───────────────────────────────────────────────────────────
        solde = situation["solde"]
        total_achats_ht = _safe_float(achats_info.get("Total_HT"))
        total_achats_ttc = _safe_float(achats_info.get("Total_TTC"))
        total_echeances = sum(_safe_float(e.get("Reste_A_Regler")) for e in echeances)
        total_paiements = sum(_safe_float(p.get("Montant_Paiement")) for p in paiements)

        dernier_paiement = None
        if paiements:
            dates = [p.get("Date_Paiement") for p in paiements if p.get("Date_Paiement")]
            if dates:
                dernier_paiement = _safe_str(max(dates))

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
            "fournisseur": {
                "nom": fournisseur_name,
                "code": situation["code_fournisseur"],
                "acheteur": situation["acheteur"] or _safe_str(info_sage.get("Acheteur")),
            },
            "info_sage": {
                "code_fournisseur": _safe_str(info_sage.get("Code fournisseur")),
                "risque_fournisseur": _safe_str(info_sage.get("Risque_Fournisseur")) or "—",
                "plafond_autorisation": _safe_float(info_sage.get("Plafond_Autorisation")),
                "assurance": _safe_float(info_sage.get("Assurance")),
                "telephone": _safe_str(info_sage.get("Téléphone")),
                "fax": _safe_str(info_sage.get("Fax")),
                "email": _safe_str(info_sage.get("Email")),
                "adresse": _safe_str(info_sage.get("Adresse")),
                "ville": _safe_str(info_sage.get("Ville")),
                "ice": _safe_str(info_sage.get("ICE")),
                "rc": _safe_str(info_sage.get("RC")),
                "capital": _safe_float(info_sage.get("Capital")),
                "forme_juridique": _safe_str(info_sage.get("Forme_Juridique")),
            },
            "kpis": {
                "solde": round(solde, 2),
                "total_achats": round(situation["total_achats"], 2),
                "total_regle_global": round(situation["total_regle"], 2),
                "achats_ht": round(total_achats_ht, 2),
                "achats_ttc": round(total_achats_ttc, 2),
                "nb_documents": int(achats_info.get("Nb_Documents") or 0),
                "nb_echeances": len(echeances),
                "total_echeances_dues": round(total_echeances, 2),
                "total_paiements": round(total_paiements, 2),
                "dernier_paiement": dernier_paiement,
            },
            "achats_evolution": [
                {
                    "mois": f"{int(r.get('Annee', 0))}-{int(r.get('Mois', 0)):02d}",
                    "montant_ht": round(_safe_float(r.get("Montant_HT")), 2),
                    "montant_ttc": round(_safe_float(r.get("Montant_TTC")), 2),
                    "nb_documents": int(r.get("Nb_Documents") or 0),
                }
                for r in achats_evolution
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
                    "acheteur": _safe_str(r.get("Acheteur")),
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
                    "date_echeance": _safe_str(r.get("Date_Echeance")),
                    "montant_echeance": round(_safe_float(r.get("Montant_Echeance")), 2),
                    "montant_regle": round(_safe_float(r.get("Montant_Regle")), 2),
                    "reste_a_regler": round(_safe_float(r.get("Reste_A_Regler")), 2),
                    "jours_retard": int(r.get("Jours_Retard") or 0),
                    "tranche_age": _safe_str(r.get("Tranche_Age")),
                    "mode_reglement": _safe_str(r.get("Mode_Reglement")),
                }
                for r in echeances
            ],
            "paiements": [
                {
                    "date_paiement": _safe_str(r.get("Date_Paiement")),
                    "num_piece": _safe_str(r.get("Num_Piece")),
                    "mode_reglement": _safe_str(r.get("Mode_Reglement")),
                    "montant": round(_safe_float(r.get("Montant_Paiement")), 2),
                    "date_echeance": _safe_str(r.get("Date_Echeance")),
                }
                for r in paiements
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
