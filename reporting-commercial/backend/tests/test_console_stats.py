"""Tests unitaires des helpers de console_stats (logique pure, sans base ni licence)."""
from app.routes.console_stats import _iso_date_from_exp, _modules


def test_modules_none():
    assert _modules(None) == ([], [])


def test_modules_visible_and_engines_merged():
    visible, active = _modules({"modules": ["ventes", "stocks"], "engines": ["ai", "stocks"]})
    assert visible == ["ventes", "stocks"]
    # engines fusionnés dans active, sans doublon (stocks déjà visible)
    assert active == ["ventes", "stocks", "ai"]


def test_modules_empty_claims():
    assert _modules({}) == ([], [])


def test_iso_date_from_exp_epoch():
    assert _iso_date_from_exp(0) == "1970-01-01"


def test_iso_date_from_exp_invalid():
    assert _iso_date_from_exp(None) is None
    assert _iso_date_from_exp("pas-un-nombre") is None
