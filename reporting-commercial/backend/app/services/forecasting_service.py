"""
Service de prévision (forecasting) pour OptiBoard.
Implémente 3 méthodes purement Python stdlib, sans numpy/pandas/sklearn.

Méthodes disponibles :
  - linear    : Régression linéaire OLS (tendance + extrapolation)
  - moving_avg: Moyenne mobile pondérée (demi-vie décroissante)
  - holt      : Lissage exponentiel double de Holt (niveau + tendance)
  - auto      : Sélectionne automatiquement la meilleure méthode (MAE)
"""
import math
import logging
import decimal
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Utilitaires mathématiques (stdlib uniquement)
# --------------------------------------------------------------------------- #

def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: List[float]) -> float:
    m = _mean(vals)
    return math.sqrt(_mean([(v - m) ** 2 for v in vals])) if len(vals) > 1 else 0.0


def _linear_regression(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    """Retourne (slope, intercept) par OLS."""
    n = len(xs)
    sx = sum(xs);  sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sx2 = sum(x * x for x in xs)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _mae(actuals: List[float], predicted: List[float]) -> float:
    if not actuals:
        return float('inf')
    return _mean([abs(a - p) for a, p in zip(actuals, predicted)])


# --------------------------------------------------------------------------- #
#  Méthodes de prévision
# --------------------------------------------------------------------------- #

def _forecast_linear(values: List[float], periods: int) -> Dict:
    """Régression linéaire sur l'ensemble des données + extrapolation."""
    n = len(values)
    xs = list(range(n))
    slope, intercept = _linear_regression(xs, values)

    fitted = [slope * x + intercept for x in xs]
    residuals = [v - f for v, f in zip(values, fitted)]
    rmse = math.sqrt(_mean([r * r for r in residuals])) if residuals else 0.0

    # IC : ±1.96 * RMSE (approx 95 %)
    forecast_vals = []
    ci_half = 1.96 * rmse
    for i in range(1, periods + 1):
        x = n - 1 + i
        pred = slope * x + intercept
        forecast_vals.append({
            "value": round(pred, 2),
            "ci_low": round(pred - ci_half * math.sqrt(1 + i / n), 2),
            "ci_high": round(pred + ci_half * math.sqrt(1 + i / n), 2),
        })

    mae = _mae(values, fitted)
    return {"forecast": forecast_vals, "mae": mae, "slope": slope, "intercept": intercept, "fitted": fitted}


def _forecast_moving_avg(values: List[float], periods: int, window: int = None) -> Dict:
    """
    Prévision par moyenne mobile pondérée.
    Fenêtre automatique = max(3, min(6, n//3)).
    Les poids décroissent exponentiellement (plus récent = plus lourd).
    """
    n = len(values)
    if window is None:
        window = max(3, min(6, n // 3))
    window = min(window, n)

    # Poids exponentiels dans la fenêtre
    raw_weights = [math.exp(0.5 * i) for i in range(window)]
    total = sum(raw_weights)
    weights = [w / total for w in raw_weights]

    def _wma(arr: List[float]) -> float:
        tail = arr[-window:]
        if len(tail) < window:
            return _mean(tail)
        return sum(w * v for w, v in zip(weights, tail))

    # Valeurs fitted (pour MAE)
    fitted = []
    for i in range(n):
        if i < window:
            fitted.append(_mean(values[:i + 1]))
        else:
            fitted.append(_wma(values[i - window:i]))

    mae = _mae(values, fitted)

    # Extrapolation : utiliser les derniers `window` points réels + points prévus
    extended = list(values)
    forecast_vals = []
    # Estimer une tendance sur la fenêtre courante pour IC
    if n >= 2:
        tail_slope, _ = _linear_regression(list(range(window)), values[-window:])
    else:
        tail_slope = 0.0

    rmse_approx = math.sqrt(_mean([(v - f) ** 2 for v, f in zip(values, fitted)])) if fitted else 0.0

    for i in range(1, periods + 1):
        pred = _wma(extended[-window:])
        ci_half = 1.96 * rmse_approx * math.sqrt(i)
        forecast_vals.append({
            "value": round(pred, 2),
            "ci_low": round(pred - ci_half, 2),
            "ci_high": round(pred + ci_half, 2),
        })
        extended.append(pred)

    return {"forecast": forecast_vals, "mae": mae, "fitted": fitted}


def _forecast_holt(values: List[float], periods: int,
                   alpha: float = None, beta: float = None) -> Dict:
    """
    Lissage exponentiel double de Holt (niveau L + tendance T).
    Alpha et Beta optimisés par grille si non fournis.
    """
    n = len(values)

    def _holt_fit(a: float, b: float) -> Tuple[List[float], float, float]:
        """Fit Holt avec alpha=a, beta=b. Retourne (fitted, L_final, T_final)."""
        L = values[0]
        T = values[1] - values[0] if n > 1 else 0.0
        fitted = [L + T]
        for t in range(1, n):
            L_prev, T_prev = L, T
            L = a * values[t] + (1 - a) * (L_prev + T_prev)
            T = b * (L - L_prev) + (1 - b) * T_prev
            fitted.append(L + T)
        return fitted, L, T

    if alpha is None or beta is None:
        # Optimisation par grille (3×3 points)
        best_mae = float('inf')
        best_a, best_b = 0.3, 0.1
        for a in [0.2, 0.4, 0.6]:
            for bv in [0.05, 0.1, 0.2]:
                try:
                    ft, _, _ = _holt_fit(a, bv)
                    m = _mae(values, ft)
                    if m < best_mae:
                        best_mae = m;  best_a = a;  best_b = bv
                except Exception:
                    pass
        alpha, beta = best_a, best_b

    fitted, L_final, T_final = _holt_fit(alpha, beta)
    mae = _mae(values, fitted)

    rmse = math.sqrt(_mean([(v - f) ** 2 for v, f in zip(values, fitted)])) if fitted else 0.0

    forecast_vals = []
    for i in range(1, periods + 1):
        pred = L_final + i * T_final
        ci_half = 1.96 * rmse * math.sqrt(i)
        forecast_vals.append({
            "value": round(pred, 2),
            "ci_low": round(pred - ci_half, 2),
            "ci_high": round(pred + ci_half, 2),
        })

    return {"forecast": forecast_vals, "mae": mae, "alpha": alpha, "beta": beta, "fitted": fitted}


# --------------------------------------------------------------------------- #
#  Entrée principale
# --------------------------------------------------------------------------- #

def _to_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(',', '.').replace(' ', '').replace('\xa0', ''))
        except ValueError:
            return None
    return None


def _generate_future_labels(last_label: str, periods: int) -> List[str]:
    """Génère des labels futurs à partir du dernier label connu."""
    import re
    # Format Mois YYYY (ex: "Jan 2025")
    months_fr = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                 "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    m = re.match(r'^(\w+)\s+(\d{4})$', str(last_label).strip())
    if m:
        mon_str, yr_str = m.group(1), int(m.group(2))
        for lst in [months_fr, months_en]:
            try:
                idx = [x.lower() for x in lst].index(mon_str.lower()[:3])
                labels = []
                cur_m, cur_y = idx + 1, yr_str
                for _ in range(periods):
                    cur_m += 1
                    if cur_m > 12:
                        cur_m = 1;  cur_y += 1
                    labels.append(f"{lst[cur_m - 1]} {cur_y}")
                return labels
            except ValueError:
                pass

    # Format YYYY (année)
    m2 = re.match(r'^(\d{4})$', str(last_label).strip())
    if m2:
        base = int(m2.group(1))
        return [str(base + i) for i in range(1, periods + 1)]

    # Fallback : T+1, T+2 ...
    return [f"T+{i}" for i in range(1, periods + 1)]


def run_forecast(
    values: List[Any],
    labels: List[str] = None,
    periods: int = 6,
    method: str = "auto",
) -> Dict:
    """
    Point d'entrée principal.

    Paramètres:
      values  — série chronologique (valeurs numériques, ordre chronologique)
      labels  — étiquettes correspondantes (optionnel)
      periods — nombre de périodes futures à projeter
      method  — "linear" | "moving_avg" | "holt" | "auto"

    Retourne:
    {
      success: bool,
      method_used: str,
      historical: [{label, value}],
      forecast: [{label, value, ci_low, ci_high}],
      trend: "up"|"down"|"stable",
      growth_rate_pct: float,
      mae: float,
      error: str (si échec)
    }
    """
    # Nettoyage
    float_vals = [_to_float(v) for v in values]
    # Supprimer les None en début/fin mais pas au milieu (interpolation simple)
    clean_pairs = [(i, v) for i, v in enumerate(float_vals) if v is not None]
    if len(clean_pairs) < 3:
        return {"success": False, "error": "Pas assez de données (minimum 3 points non nuls requis)"}

    clean_vals = [v for _, v in clean_pairs]
    clean_labels = None
    if labels:
        clean_labels = [labels[i] for i, _ in clean_pairs]
    n = len(clean_vals)

    periods = max(1, min(periods, max(6, n)))

    # Sélection méthode
    methods_to_try = ["linear", "moving_avg", "holt"] if method == "auto" else [method]
    results_by_method: Dict[str, Dict] = {}

    for m in methods_to_try:
        try:
            if m == "linear":
                r = _forecast_linear(clean_vals, periods)
            elif m == "moving_avg":
                r = _forecast_moving_avg(clean_vals, periods)
            elif m == "holt":
                r = _forecast_holt(clean_vals, periods)
            else:
                r = _forecast_linear(clean_vals, periods)
            results_by_method[m] = r
        except Exception as e:
            logger.warning(f"Forecasting method {m} failed: {e}")

    if not results_by_method:
        return {"success": False, "error": "Toutes les méthodes de prévision ont échoué"}

    # Choisir la meilleure (plus faible MAE) en mode auto
    if method == "auto":
        best_method = min(results_by_method, key=lambda k: results_by_method[k].get("mae", float('inf')))
    else:
        best_method = list(results_by_method.keys())[0]

    best = results_by_method[best_method]
    forecast_raw = best["forecast"]

    # Construire labels futurs
    last_label = clean_labels[-1] if clean_labels else str(n)
    future_labels = _generate_future_labels(last_label, periods)

    # Assembler historical
    historical = []
    for i, (val, lbl) in enumerate(zip(clean_vals, clean_labels or [str(i + 1) for i in range(n)])):
        historical.append({
            "label": lbl,
            "value": round(val, 2),
            "fitted": round(best.get("fitted", [val] * n)[i], 2) if "fitted" in best else None
        })

    # Assembler forecast
    forecast_out = []
    for i, (f_item, lbl) in enumerate(zip(forecast_raw, future_labels)):
        forecast_out.append({
            "label": lbl,
            "value": f_item["value"],
            "ci_low": f_item["ci_low"],
            "ci_high": f_item["ci_high"],
        })

    # Tendance globale
    first_half_mean = _mean(clean_vals[:max(1, n // 2)])
    last_half_mean = _mean(clean_vals[n // 2:])
    if last_half_mean > first_half_mean * 1.03:
        trend = "up"
    elif last_half_mean < first_half_mean * 0.97:
        trend = "down"
    else:
        trend = "stable"

    # Taux de croissance : premier vs dernier point réel
    if clean_vals[0] != 0:
        growth_rate = (clean_vals[-1] - clean_vals[0]) / abs(clean_vals[0]) * 100
    else:
        growth_rate = 0.0

    # Taux de croissance prévu (dernier réel → dernière prévision)
    if clean_vals[-1] != 0 and forecast_out:
        forecast_growth = (forecast_out[-1]["value"] - clean_vals[-1]) / abs(clean_vals[-1]) * 100
    else:
        forecast_growth = 0.0

    return {
        "success": True,
        "method_used": best_method,
        "historical": historical,
        "forecast": forecast_out,
        "trend": trend,
        "growth_rate_pct": round(growth_rate, 1),
        "forecast_growth_pct": round(forecast_growth, 1),
        "mae": round(best.get("mae", 0.0), 2),
        "n_points": n,
        "periods": periods,
    }
