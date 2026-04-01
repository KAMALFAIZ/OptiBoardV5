"""
Service de détection d'anomalies statistiques pour OptiBoard.
Utilise Z-score et IQR (interquartile range) — 100% Python stdlib, sans IA.
Détecte les valeurs aberrantes dans les colonnes numériques d'un rapport.
"""
import math
import decimal
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Seuils de détection — valeurs par défaut (mode Normal)
ZSCORE_CRITICAL = 3.0     # > 3σ → critique
ZSCORE_WARNING  = 2.5     # > 2.5σ → attention
IQR_MULTIPLIER  = 2.0     # valeurs hors [Q1 - 2*IQR, Q3 + 2*IQR] → suspectes
MIN_ROWS_FOR_STATS = 5    # min de lignes pour calculer des stats fiables


def _to_float(val) -> Optional[float]:
    """Convertit une valeur en float, retourne None si impossible."""
    if val is None:
        return None
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        clean = val.replace(' ', '').replace('\xa0', '').replace(',', '.')
        try:
            return float(clean)
        except ValueError:
            return None
    return None


def _stats(values: List[float]) -> Dict:
    """Calcule mean, std, Q1, Q3, IQR sur une liste de floats."""
    n = len(values)
    if n < MIN_ROWS_FOR_STATS:
        return None

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance) if variance > 0 else 0.0

    sorted_vals = sorted(values)
    q1_idx = int(n * 0.25)
    q3_idx = int(n * 0.75)
    q1 = sorted_vals[q1_idx]
    q3 = sorted_vals[min(q3_idx, n - 1)]
    iqr = q3 - q1

    return {
        "mean": mean, "std": std,
        "q1": q1, "q3": q3, "iqr": iqr,
        "min": sorted_vals[0], "max": sorted_vals[-1], "n": n
    }


def _zscore_severity(zscore: float, critical: float, warning: float) -> Optional[str]:
    abs_z = abs(zscore)
    if abs_z >= critical:
        return "critical"
    if abs_z >= warning:
        return "warning"
    return None


def detect_anomalies(
    data: List[Dict[str, Any]],
    columns_info: List[Dict] = None,
    max_anomalies: int = 50,
    zscore_critical: float = ZSCORE_CRITICAL,
    zscore_warning: float = ZSCORE_WARNING,
    iqr_multiplier: float = IQR_MULTIPLIER,
    min_rows: int = MIN_ROWS_FOR_STATS,
) -> Dict:
    """
    Détecte les anomalies statistiques dans les données d'un rapport.

    Retourne:
    {
      "success": True,
      "anomalies": [
        {
          "row_index": int,
          "row_data": dict,        # données complètes de la ligne
          "fields": [              # champs anormaux
            {"field": str, "header": str, "value": float,
             "zscore": float, "severity": "critical"|"warning",
             "mean": float, "std": float}
          ]
        }
      ],
      "summary": {
        "total": int,
        "critical": int,
        "warning": int,
        "anomalous_fields": [str]  # champs les plus souvent anormaux
      },
      "field_stats": {field: {mean, std, min, max, n}}
    }
    """
    if not data:
        return {"success": True, "anomalies": [], "summary": {"total": 0, "critical": 0, "warning": 0, "anomalous_fields": []}, "field_stats": {}}

    # Construire un header mapping field → header label
    header_map = {}
    if columns_info:
        for c in columns_info:
            field = c.get("field") or c.get("key", "")
            header = c.get("header") or c.get("label") or field
            if field:
                header_map[field] = header

    # Identifier les colonnes numériques
    numeric_fields = {}   # field → list of (row_index, float_value)

    for row_idx, row in enumerate(data):
        if isinstance(row, dict) and row.get("__isGroupRow"):
            continue
        for field, raw_val in row.items():
            if field.startswith("__"):
                continue
            fval = _to_float(raw_val)
            if fval is not None:
                if field not in numeric_fields:
                    numeric_fields[field] = []
                numeric_fields[field].append((row_idx, fval))

    # Filtrer les champs avec assez de valeurs non-nulles
    # et dont la std est significative (pas que des zéros)
    field_stats = {}
    for field, pairs in numeric_fields.items():
        if len(pairs) < min_rows:
            continue
        values = [v for _, v in pairs]
        s = _stats(values)
        if s and s["std"] > 0:
            field_stats[field] = s

    if not field_stats:
        return {
            "success": True,
            "anomalies": [],
            "summary": {"total": 0, "critical": 0, "warning": 0, "anomalous_fields": []},
            "field_stats": {}
        }

    # Détecter les anomalies ligne par ligne
    anomaly_map: Dict[int, Dict] = {}   # row_index → anomaly entry
    field_anomaly_count: Dict[str, int] = {}

    for field, pairs in numeric_fields.items():
        s = field_stats.get(field)
        if not s:
            continue

        mean, std = s["mean"], s["std"]
        q1, q3, iqr = s["q1"], s["q3"], s["iqr"]
        iqr_lo = q1 - iqr_multiplier * iqr
        iqr_hi = q3 + iqr_multiplier * iqr

        for row_idx, fval in pairs:
            # Z-score
            zscore = (fval - mean) / std if std > 0 else 0.0
            severity = _zscore_severity(zscore, zscore_critical, zscore_warning)

            # IQR check en complément
            if severity is None and iqr > 0:
                if fval < iqr_lo or fval > iqr_hi:
                    severity = "warning"

            if severity is None:
                continue

            if row_idx not in anomaly_map:
                anomaly_map[row_idx] = {
                    "row_index": row_idx,
                    "row_data": data[row_idx],
                    "fields": []
                }

            anomaly_map[row_idx]["fields"].append({
                "field": field,
                "header": header_map.get(field, field),
                "value": fval,
                "zscore": round(zscore, 2),
                "severity": severity,
                "mean": round(mean, 2),
                "std": round(std, 2),
                "expected_range": [round(mean - 2 * std, 2), round(mean + 2 * std, 2)]
            })

            field_anomaly_count[field] = field_anomaly_count.get(field, 0) + 1

    # Trier les anomalies par gravité (critical d'abord) et limiter
    anomalies = list(anomaly_map.values())
    anomalies.sort(key=lambda a: (
        -max(1 if f["severity"] == "critical" else 0 for f in a["fields"]),
        -max(abs(f["zscore"]) for f in a["fields"])
    ))
    anomalies = anomalies[:max_anomalies]

    n_critical = sum(1 for a in anomalies if any(f["severity"] == "critical" for f in a["fields"]))
    n_warning = len(anomalies) - n_critical

    top_fields = sorted(field_anomaly_count.items(), key=lambda x: -x[1])[:5]
    anomalous_fields = [f for f, _ in top_fields]

    # Sérialiser field_stats (garder seulement les champs utiles)
    serializable_stats = {
        f: {
            "mean": round(s["mean"], 2),
            "std": round(s["std"], 2),
            "min": round(s["min"], 2),
            "max": round(s["max"], 2),
            "n": s["n"]
        }
        for f, s in field_stats.items()
    }

    return {
        "success": True,
        "anomalies": anomalies,
        "summary": {
            "total": len(anomalies),
            "critical": n_critical,
            "warning": n_warning,
            "anomalous_fields": anomalous_fields
        },
        "field_stats": serializable_stats
    }
