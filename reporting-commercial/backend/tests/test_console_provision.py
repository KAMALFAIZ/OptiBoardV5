"""Tests unitaires de console_provision — validation du code (logique pure, sans base)."""
import pytest
from fastapi import HTTPException

from app.routes.console_provision import _normalize_code


def test_normalize_code_uppercases_and_trims():
    assert _normalize_code("  sg ") == "SG"


def test_normalize_code_spaces_to_underscore():
    assert _normalize_code("mon client") == "MON_CLIENT"


def test_normalize_code_accepts_digits_and_underscore():
    assert _normalize_code("cli_01") == "CLI_01"


def test_normalize_code_accepts_hyphen_console_style():
    # Les codes console (^[a-z0-9][a-z0-9-]{1,28}$) contiennent des tirets.
    assert _normalize_code("client-az") == "CLIENT-AZ"


@pytest.mark.parametrize("bad", [
    "",                       # vide
    "x]; DROP DATABASE [y",   # injection identifiant SQL
    "a.b",                    # point interdit
    "a;b",                    # point-virgule interdit
    "société",               # accents/caractères non ASCII
    "x" * 41,                 # trop long (>40)
])
def test_normalize_code_rejects_unsafe(bad):
    with pytest.raises(HTTPException) as exc:
        _normalize_code(bad)
    assert exc.value.status_code == 400
