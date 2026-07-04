"""Tests unitaires du métrage IA (logique pure, sans base de données)."""
import re

from app.services.ai_usage import estimate_tokens, current_year_month


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
