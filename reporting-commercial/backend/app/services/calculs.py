"""Service de calculs des indicateurs commerciaux"""
from typing import Dict, Any, List, Union
from datetime import datetime, timedelta
import pandas as pd
import re


def parse_number(value: Union[str, int, float, None]) -> float:
    """
    Convertit une valeur numérique formatée en float.
    Gère les formats: " 2 047 733,00 ", "1234.56", 1234, None, etc.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    if isinstance(value, str):
        # Nettoyer la chaîne
        cleaned = value.strip()
        if not cleaned or cleaned == '-':
            return 0.0
        # Supprimer les espaces (séparateurs de milliers français)
        cleaned = cleaned.replace(' ', '').replace('\xa0', '')
        # Remplacer la virgule par un point (format français)
        cleaned = cleaned.replace(',', '.')
        # Supprimer les caractères non numériques sauf le point et le signe moins
        cleaned = re.sub(r'[^\d.\-]', '', cleaned)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def safe_sum(values: List[Any], key: str = None) -> float:
    """
    Somme sécurisée qui gère les valeurs formatées et None.
    """
    total = 0.0
    for item in values:
        if key is not None:
            value = item.get(key, 0) if isinstance(item, dict) else 0
        else:
            value = item
        total += parse_number(value)
    return total


def calculer_marge_brute(ca: float, cout: float) -> Dict[str, float]:
    """Calcule la marge brute et le taux de marge."""
    marge = ca - cout if ca and cout else 0
    taux_marge = (marge / ca * 100) if ca and ca > 0 else 0
    return {
        "marge_brute": round(marge, 2),
        "taux_marge": round(taux_marge, 2)
    }


def calculer_dso(encours_clients: float, ca_ttc: float, nb_jours: int = 365) -> float:
    """
    Calcule le DSO (Days Sales Outstanding).
    DSO = (Encours Clients / CA TTC) × Nombre de jours
    """
    if ca_ttc and ca_ttc > 0:
        return round((encours_clients / ca_ttc) * nb_jours, 1)
    return 0


def calculer_rotation_stock(ca_annuel: float, stock_moyen: float) -> float:
    """
    Calcule la rotation des stocks.
    Rotation = CA / Stock Moyen
    """
    if stock_moyen and stock_moyen > 0:
        return round(ca_annuel / stock_moyen, 2)
    return 0


def calculer_couverture_stock(stock_actuel: float, ca_annuel: float) -> float:
    """
    Calcule la couverture de stock en jours.
    Couverture (jours) = (Stock / CA annuel) × 365
    """
    if ca_annuel and ca_annuel > 0:
        return round((stock_actuel / ca_annuel) * 365, 1)
    return 0


def calculer_taux_recouvrement(montant_recouvre: float, montant_a_recouvrer: float) -> float:
    """
    Calcule le taux de recouvrement.
    Taux = Montant recouvert / Montant à recouvrer × 100
    """
    if montant_a_recouvrer and montant_a_recouvrer > 0:
        return round((montant_recouvre / montant_a_recouvrer) * 100, 2)
    return 0


def calculer_evolution(valeur_actuelle: float, valeur_precedente: float) -> Dict[str, Any]:
    """Calcule l'évolution entre deux périodes."""
    if valeur_precedente and valeur_precedente > 0:
        evolution = ((valeur_actuelle - valeur_precedente) / valeur_precedente) * 100
        tendance = "hausse" if evolution > 0 else "baisse" if evolution < 0 else "stable"
    else:
        evolution = 0
        tendance = "stable"

    return {
        "valeur_actuelle": round(valeur_actuelle, 2),
        "valeur_precedente": round(valeur_precedente, 2) if valeur_precedente else 0,
        "evolution_pct": round(evolution, 2),
        "tendance": tendance
    }


def analyser_balance_agee(data: List[Dict]) -> Dict[str, Any]:
    """Analyse la balance âgée et retourne des statistiques."""
    if not data:
        return {
            "total_encours": 0,
            "repartition": {},
            "creances_douteuses": 0,
            "nb_clients": 0
        }

    df = pd.DataFrame(data)

    total_encours = df['Solde_Cloture'].sum() if 'Solde_Cloture' in df.columns else 0

    repartition = {
        "0_30": df['0-30'].sum() if '0-30' in df.columns else 0,
        "31_60": df['31-60'].sum() if '31-60' in df.columns else 0,
        "61_90": df['61-90'].sum() if '61-90' in df.columns else 0,
        "91_120": df['91-120'].sum() if '91-120' in df.columns else 0,
        "plus_120": df['+120'].sum() if '+120' in df.columns else 0,
    }

    creances_douteuses = repartition.get("plus_120", 0)

    return {
        "total_encours": round(total_encours, 2),
        "repartition": {k: round(v, 2) for k, v in repartition.items()},
        "creances_douteuses": round(creances_douteuses, 2),
        "taux_creances_douteuses": round((creances_douteuses / total_encours * 100) if total_encours > 0 else 0, 2),
        "nb_clients": len(df)
    }


def identifier_alertes(kpis: Dict[str, Any], seuils: Dict[str, float] = None) -> List[Dict[str, Any]]:
    """Identifie les alertes basées sur les KPIs et les seuils."""
    if seuils is None:
        seuils = {
            "dso_max": 60,
            "taux_creances_douteuses_max": 10,
            "rotation_stock_min": 2,
        }

    alertes = []

    # Alerte DSO
    if kpis.get("dso", 0) > seuils.get("dso_max", 60):
        alertes.append({
            "type": "DSO",
            "niveau": "warning" if kpis["dso"] < 90 else "critical",
            "message": f"DSO élevé: {kpis['dso']} jours (seuil: {seuils['dso_max']} jours)",
            "valeur": kpis["dso"]
        })

    # Alerte créances douteuses
    taux_creances = kpis.get("taux_creances_douteuses", 0)
    if taux_creances > seuils.get("taux_creances_douteuses_max", 10):
        alertes.append({
            "type": "Créances",
            "niveau": "warning" if taux_creances < 15 else "critical",
            "message": f"Taux de créances douteuses: {taux_creances}%",
            "valeur": taux_creances
        })

    # Alerte rotation stock
    rotation = kpis.get("rotation_stock", 0)
    if rotation > 0 and rotation < seuils.get("rotation_stock_min", 2):
        alertes.append({
            "type": "Stock",
            "niveau": "warning",
            "message": f"Rotation stock faible: {rotation} (minimum recommandé: {seuils['rotation_stock_min']})",
            "valeur": rotation
        })

    return alertes


def formater_montant(montant: float, devise: str = "MAD") -> str:
    """Formate un montant avec séparateurs et devise."""
    if montant is None:
        return f"0.00 {devise}"
    return f"{montant:,.2f} {devise}".replace(",", " ")


def get_periode_dates(periode: str) -> tuple:
    """Retourne les dates de début et fin pour une période donnée."""
    today = datetime.now()
    current_year = today.year

    if periode == "annee_courante":
        debut = datetime(current_year, 1, 1)
        fin = today
    elif periode == "annee_precedente":
        debut = datetime(current_year - 1, 1, 1)
        fin = datetime(current_year - 1, 12, 31)
    elif periode == "trimestre_courant":
        trimestre = (today.month - 1) // 3
        debut = datetime(current_year, trimestre * 3 + 1, 1)
        fin = today
    elif periode == "mois_courant":
        debut = datetime(current_year, today.month, 1)
        fin = today
    elif periode == "12_derniers_mois":
        debut = today - timedelta(days=365)
        fin = today
    else:
        # Par défaut: année courante
        debut = datetime(current_year, 1, 1)
        fin = today

    return debut.strftime("%Y-%m-%d"), fin.strftime("%Y-%m-%d")
