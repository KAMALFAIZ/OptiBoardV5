"""Tests unitaires du métrage IA + quota (logique pure, sans base de données)."""
import re

from app.services.ai_usage import estimate_tokens, current_year_month, _quota_decision


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0
    assert estimate_tokens(None) == 0


def test_estimate_tokens_ratio():
    assert estimate_tokens("abcd") == 1        # 4 caractères → 1 token
    assert estimate_tokens("a" * 40) == 10     # 40 caractères → 10 tokens
    assert estimate_tokens("x") == 1           # jamais 0 si non vide


def test_current_year_month_format():
    ym = current_year_month()
    assert re.fullmatch(r"\d{4}-\d{2}", ym), ym


# ── Quota IA mensuel (décision pure) ──
def test_quota_unlimited_or_off():
    assert _quota_decision("block", 10**9, None) == "ok"   # pas de plafond
    assert _quota_decision("block", 10**9, 0) == "ok"      # 0 = illimité
    assert _quota_decision("off", 10**9, 100) == "ok"      # report seul


def test_quota_under_limit():
    assert _quota_decision("warn", 50, 100) == "ok"
    assert _quota_decision("block", 99, 100) == "ok"


def test_quota_over_limit():
    assert _quota_decision("warn", 100, 100) == "warn"     # atteint = dépassé
    assert _quota_decision("warn", 150, 100) == "warn"
    assert _quota_decision("block", 100, 100) == "block"
    assert _quota_decision("block", 200, 100) == "block"
