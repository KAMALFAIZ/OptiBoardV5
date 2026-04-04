"""
Service de calcul du Score de Santé Client — OptiBoard.

Produit un score 0–100 basé sur les KPIs financiers d'un client :
  - DSO (Days Sales Outstanding) : délai moyen de paiement
  - Ratio encours / plafond de crédit autorisé
  - Montant en retard > 120 jours
  - Nombre de factures impayées
  - Taux de règlement historique

Niveaux :
  Vert   ≥ 70 — Bon payeur
  Orange 40–69 — À surveiller
  Rouge  < 40  — Risque élevé

Usage :
    from .client_health_service import compute_health_score
    score = compute_health_score(kpis_dict)
"""

from typing import Dict, Any, List


def compute_health_score(kpis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule le score de santé d'un client à partir de ses KPIs financiers.

    Args:
        kpis: dict issu de fiche_client.py contenant :
            - dso_client         : jours de délai moyen de paiement
            - encours            : encours total (€)
            - plafond            : plafond d'autorisation Sage (€), 0 si inconnu
            - tranche_plus_120   : montant en retard > 120j (€)
            - nb_factures_impayees : nombre de factures non réglées
            - taux_reglement     : % de règlement historique (0–100)
            - impayes            : total impayés (€)

    Returns:
        {
            "score": int (0–100),
            "niveau": "Vert" | "Orange" | "Rouge",
            "couleur": "#10b981" | "#f59e0b" | "#ef4444",
            "flags": [{"message": str, "poids": int, "severite": "critique"|"attention"|"info"}],
            "detail": {criterion: {"valeur": ..., "impact": int, "ok": bool}}
        }
    """
    score = 100
    flags: List[Dict] = []
    detail: Dict[str, Any] = {}

    dso              = float(kpis.get("dso_client") or 0)
    encours          = float(kpis.get("encours") or 0)
    plafond          = float(kpis.get("plafond") or 0)
    tranche_120      = float(kpis.get("tranche_plus_120") or 0)
    nb_impayes       = int(kpis.get("nb_factures_impayees") or 0)
    taux_reglement   = float(kpis.get("taux_reglement") or 100)
    impayes          = float(kpis.get("impayes") or 0)

    # ── Critère 1 : DSO ───────────────────────────────────────────────────────
    if dso > 90:
        impact = 35
        score -= impact
        flags.append({"message": f"DSO critique : {int(dso)} jours (>90j)", "poids": impact, "severite": "critique"})
        detail["dso"] = {"valeur": int(dso), "impact": -impact, "ok": False}
    elif dso > 60:
        impact = 25
        score -= impact
        flags.append({"message": f"DSO élevé : {int(dso)} jours (>60j)", "poids": impact, "severite": "critique"})
        detail["dso"] = {"valeur": int(dso), "impact": -impact, "ok": False}
    elif dso > 30:
        impact = 12
        score -= impact
        flags.append({"message": f"DSO modéré : {int(dso)} jours (>30j)", "poids": impact, "severite": "attention"})
        detail["dso"] = {"valeur": int(dso), "impact": -impact, "ok": False}
    else:
        detail["dso"] = {"valeur": int(dso), "impact": 0, "ok": True}

    # ── Critère 2 : Ratio encours / plafond ───────────────────────────────────
    if plafond > 0:
        ratio = encours / plafond
        if ratio > 1.0:
            impact = 25
            score -= impact
            flags.append({"message": f"Encours dépasse le plafond ({ratio:.0%})", "poids": impact, "severite": "critique"})
            detail["ratio_credit"] = {"valeur": f"{ratio:.0%}", "impact": -impact, "ok": False}
        elif ratio > 0.85:
            impact = 15
            score -= impact
            flags.append({"message": f"Encours à {ratio:.0%} du plafond autorisé", "poids": impact, "severite": "attention"})
            detail["ratio_credit"] = {"valeur": f"{ratio:.0%}", "impact": -impact, "ok": False}
        else:
            detail["ratio_credit"] = {"valeur": f"{ratio:.0%}", "impact": 0, "ok": True}
    else:
        # Pas de plafond Sage configuré : pas de pénalité
        detail["ratio_credit"] = {"valeur": "N/A", "impact": 0, "ok": True}

    # ── Critère 3 : Montant en retard > 120 jours ────────────────────────────
    if tranche_120 > 0:
        if tranche_120 > 10000:
            impact = 20
            score -= impact
            flags.append({"message": f"Retard >120j : {tranche_120:,.0f} € (risque provision)", "poids": impact, "severite": "critique"})
        else:
            impact = 10
            score -= impact
            flags.append({"message": f"Retard >120j : {tranche_120:,.0f} €", "poids": impact, "severite": "attention"})
        detail["retard_120j"] = {"valeur": tranche_120, "impact": -impact, "ok": False}
    else:
        detail["retard_120j"] = {"valeur": 0, "impact": 0, "ok": True}

    # ── Critère 4 : Nombre de factures impayées ───────────────────────────────
    if nb_impayes > 10:
        impact = min(nb_impayes * 2, 15)
        score -= impact
        flags.append({"message": f"{nb_impayes} factures impayées", "poids": impact, "severite": "attention"})
        detail["factures_impayees"] = {"valeur": nb_impayes, "impact": -impact, "ok": False}
    elif nb_impayes > 3:
        impact = 5
        score -= impact
        flags.append({"message": f"{nb_impayes} factures impayées", "poids": impact, "severite": "info"})
        detail["factures_impayees"] = {"valeur": nb_impayes, "impact": -impact, "ok": False}
    else:
        detail["factures_impayees"] = {"valeur": nb_impayes, "impact": 0, "ok": True}

    # ── Critère 5 : Taux de règlement ─────────────────────────────────────────
    if taux_reglement < 50:
        impact = 15
        score -= impact
        flags.append({"message": f"Taux règlement faible : {taux_reglement:.0f}%", "poids": impact, "severite": "critique"})
        detail["taux_reglement"] = {"valeur": f"{taux_reglement:.0f}%", "impact": -impact, "ok": False}
    elif taux_reglement < 75:
        impact = 7
        score -= impact
        flags.append({"message": f"Taux règlement : {taux_reglement:.0f}%", "poids": impact, "severite": "attention"})
        detail["taux_reglement"] = {"valeur": f"{taux_reglement:.0f}%", "impact": -impact, "ok": False}
    else:
        detail["taux_reglement"] = {"valeur": f"{taux_reglement:.0f}%", "impact": 0, "ok": True}

    # ── Score final ───────────────────────────────────────────────────────────
    score = max(0, min(100, score))

    if score >= 70:
        niveau  = "Vert"
        couleur = "#10b981"
        libelle = "Bon payeur"
    elif score >= 40:
        niveau  = "Orange"
        couleur = "#f59e0b"
        libelle = "À surveiller"
    else:
        niveau  = "Rouge"
        couleur = "#ef4444"
        libelle = "Risque élevé"

    return {
        "score":   score,
        "niveau":  niveau,
        "couleur": couleur,
        "libelle": libelle,
        "flags":   flags,
        "detail":  detail,
    }
