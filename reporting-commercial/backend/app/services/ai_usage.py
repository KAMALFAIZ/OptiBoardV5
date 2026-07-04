"""
Métrage de l'usage IA — tokens & appels par tenant et par mois.
================================================================
Point de collecte UNIQUE, alimenté par ai_provider.py (le seul passage IA de
l'application). Agrège dans la base centrale OptiBoard_SaaS.APP_AI_Usage,
indexé par (dwh_code, year_month, provider, model).

Sert de source à :
  - GET /api/console/instance-stats  (bloc `ai` : tokensMonth / callsMonth)  [Phase 2]
  - le contrôle de quota mensuel `aiMonthlyTokens` de la licence signée       [Phase 2]

Le `dwh_code` provient du contexte tenant (routage par sous-domaine
xxxx.optiboard.kasoft.ma → DWH). Un usage hors tenant (tâche centrale) est
rattaché au pseudo-code « _central ».

Contrat de robustesse : le métrage ne DOIT JAMAIS interrompre un appel IA.
Toute erreur est avalée et journalisée en debug (fail-safe, non bloquant).

Note : sur le flux (streaming), certains fournisseurs n'exposent pas l'usage
exact ; on stocke alors une ESTIMATION (≈ 4 caractères/token). Le chemin
non-streaming enregistre l'usage EXACT renvoyé par le fournisseur.
"""
import logging
from datetime import datetime
from typing import Optional

from ..database_unified import current_dwh_code, execute_central, write_central

logger = logging.getLogger(__name__)

_CENTRAL_CODE = "_central"      # usage IA hors tenant (tâches centrales)
_TABLE_READY = False            # table créée à la volée une seule fois

_CREATE_SQL = """
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_AI_Usage' AND xtype='U')
CREATE TABLE APP_AI_Usage (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    dwh_code      VARCHAR(50)   NOT NULL,
    year_month    CHAR(7)       NOT NULL,     -- 'YYYY-MM'
    provider      VARCHAR(50)   NOT NULL,     -- 'anthropic' | 'openai' | 'ollama' | ...
    model         VARCHAR(120)  NOT NULL,
    calls         INT           NOT NULL DEFAULT 0,
    tokens_in     BIGINT        NOT NULL DEFAULT 0,
    tokens_out    BIGINT        NOT NULL DEFAULT 0,
    tokens_total  BIGINT        NOT NULL DEFAULT 0,
    updated_at    DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_AI_Usage UNIQUE (dwh_code, year_month, provider, model)
);
"""

# Upsert atomique (SQL Server) : incrémente si la ligne du mois existe, sinon insère.
# HOLDLOCK évite la course insert/insert concurrente sur la contrainte UNIQUE.
_MERGE_SQL = """
MERGE APP_AI_Usage WITH (HOLDLOCK) AS t
USING (SELECT ? AS dwh_code, ? AS year_month, ? AS provider, ? AS model) AS s
   ON t.dwh_code = s.dwh_code AND t.year_month = s.year_month
  AND t.provider = s.provider AND t.model = s.model
WHEN MATCHED THEN UPDATE SET
    calls        = t.calls + 1,
    tokens_in    = t.tokens_in + ?,
    tokens_out   = t.tokens_out + ?,
    tokens_total = t.tokens_total + ?,
    updated_at   = GETDATE()
WHEN NOT MATCHED THEN INSERT
    (dwh_code, year_month, provider, model, calls, tokens_in, tokens_out, tokens_total)
    VALUES (s.dwh_code, s.year_month, s.provider, s.model, 1, ?, ?, ?);
"""


def _ensure_table() -> None:
    """Crée APP_AI_Usage si absente (idempotent, une seule fois par process)."""
    global _TABLE_READY
    if _TABLE_READY:
        return
    try:
        write_central(_CREATE_SQL)
        _TABLE_READY = True
    except Exception as e:  # pragma: no cover - dépend de la base
        logger.debug(f"[AI-USAGE] init table: {e}")


def current_year_month() -> str:
    """Mois courant au format 'YYYY-MM'."""
    return datetime.now().strftime("%Y-%m")


def estimate_tokens(text: str) -> int:
    """Estimation grossière du nombre de tokens (≈ 4 caractères/token).

    Utilisée uniquement en streaming, où l'usage exact n'est pas toujours
    exposé par le fournisseur.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _current_dwh() -> str:
    try:
        code = (current_dwh_code.get() or "").strip()
    except Exception:
        code = ""
    return code or _CENTRAL_CODE


def record_usage(provider: str, model: str, tokens_in, tokens_out) -> None:
    """Agrège un appel IA dans APP_AI_Usage pour le tenant & le mois courants.

    Fail-safe : n'émet jamais d'exception vers l'appelant (le passage IA).
    """
    try:
        _ensure_table()
        dwh = _current_dwh()
        ym = current_year_month()
        ti = int(tokens_in or 0)
        to = int(tokens_out or 0)
        tt = ti + to
        write_central(_MERGE_SQL, (
            dwh, ym, (provider or "?")[:50], (model or "?")[:120],
            ti, to, tt,   # WHEN MATCHED  → incréments
            ti, to, tt,   # WHEN NOT MATCHED → valeurs d'insertion
        ))
    except Exception as e:  # pragma: no cover - dépend de la base
        logger.debug(f"[AI-USAGE] record: {e}")


def monthly_usage(year_month: Optional[str] = None) -> dict:
    """Somme des tokens/appels IA du mois pour TOUTE l'installation (tous DWH).

    Alimente le bloc `ai` de /api/console/instance-stats (Phase 2). Ne lève
    jamais : renvoie des zéros si la table est absente ou la base injoignable.
    """
    ym = year_month or current_year_month()
    try:
        _ensure_table()
        rows = execute_central(
            "SELECT SUM(calls) AS calls, SUM(tokens_in) AS tin, "
            "       SUM(tokens_out) AS tout, SUM(tokens_total) AS ttot "
            "FROM APP_AI_Usage WHERE year_month = ?",
            (ym,), use_cache=False,
        )
        if rows and rows[0]:
            r = rows[0]
            return {
                "month": ym,
                "calls": int(r.get("calls") or 0),
                "tokensIn": int(r.get("tin") or 0),
                "tokensOut": int(r.get("tout") or 0),
                "tokensMonth": int(r.get("ttot") or 0),
            }
    except Exception as e:  # pragma: no cover - dépend de la base
        logger.debug(f"[AI-USAGE] monthly_usage: {e}")
    return {"month": ym, "calls": 0, "tokensIn": 0, "tokensOut": 0, "tokensMonth": 0}
