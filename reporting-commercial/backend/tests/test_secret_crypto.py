"""Tests unitaires du chiffrement au repos des secrets (APP_ETL_Agents.sage_password)."""
import importlib

import pytest

from app.services import secret_crypto


def test_roundtrip():
    enc = secret_crypto.enc_secret("SQL@2019")
    assert enc.startswith("$sec1$")
    assert secret_crypto.dec_secret(enc) == "SQL@2019"


def test_encryption_is_randomized():
    # Nonce aleatoire : deux chiffrements du meme secret different, sinon un dump
    # revele quels agents partagent le meme mot de passe.
    assert secret_crypto.enc_secret("x") != secret_crypto.enc_secret("x")


def test_enc_is_idempotent():
    once = secret_crypto.enc_secret("hunter2")
    assert secret_crypto.enc_secret(once) == once


def test_plaintext_legacy_passes_through():
    # Migration progressive : une valeur non prefixee est rendue telle quelle.
    assert secret_crypto.dec_secret("motdepasse-en-clair") == "motdepasse-en-clair"


@pytest.mark.parametrize("empty", ["", None])
def test_empty_values_untouched(empty):
    assert secret_crypto.enc_secret(empty) == empty
    assert secret_crypto.dec_secret(empty) == empty


def test_wrong_key_returns_empty_not_blob(monkeypatch):
    """Cle rotee sans migration : ne jamais renvoyer le blob comme mot de passe.

    Rendre le blob provoquerait un echec de connexion Sage avec un message
    trompeur ; une chaine vide rend la cause evidente.
    """
    enc = secret_crypto.enc_secret("secret")
    monkeypatch.setenv("OPTIBOARD_SECRETS_AES_KEY", "0" * 32)
    reloaded = importlib.reload(secret_crypto)
    try:
        assert reloaded.dec_secret(enc) == ""
    finally:
        monkeypatch.delenv("OPTIBOARD_SECRETS_AES_KEY", raising=False)
        importlib.reload(secret_crypto)


def test_env_key_must_be_32_bytes(monkeypatch):
    """Cle de mauvaise longueur : repli documente, pas de crash au demarrage."""
    monkeypatch.setenv("OPTIBOARD_SECRETS_AES_KEY", "trop-courte")
    reloaded = importlib.reload(secret_crypto)
    try:
        assert reloaded.dec_secret(reloaded.enc_secret("abc")) == "abc"
    finally:
        monkeypatch.delenv("OPTIBOARD_SECRETS_AES_KEY", raising=False)
        importlib.reload(secret_crypto)


def test_dec_rows_decrypts_field_in_place():
    rows = [{"agent_id": "a", "sage_password": secret_crypto.enc_secret("p1")},
            {"agent_id": "b", "sage_password": "legacy"},
            {"agent_id": "c"}]
    secret_crypto.dec_rows(rows)
    assert [r.get("sage_password") for r in rows] == ["p1", "legacy", None]
