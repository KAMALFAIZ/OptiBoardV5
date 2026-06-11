"""Isolation tenant — garde anti-rejeu cross-tenant du middleware.

Vérifie que le dwh_code prouvé au login (session.dwh_code) fait autorité :
- une session liée à un tenant est figée sur ce tenant (un autre dwh_code → 403) ;
- une session centrale (dwh_code=None) peut accéder aux DWH autorisés
  (superadmin / APP_UserDWH), refusée sinon.

Hermétique : validate_session et user_can_access_dwh sont mockés, aucune base
réelle n'est requise.
"""
import pytest
from unittest.mock import patch

TOKEN = "t" * 64


@pytest.fixture
def client():
    with patch("app.database_unified.execute_app", return_value=[]):
        from run import app
        from fastapi.testclient import TestClient
        return TestClient(app)


def _headers(dwh=None):
    h = {"X-Session-Token": TOKEN}
    if dwh:
        h["X-DWH-Code"] = dwh
    return h


class TestTenantIsolation:
    def test_user_client_meme_dwh_pas_403(self, client):
        """User client (session=SG) accédant à SG → la garde ne bloque pas."""
        with patch("app.middleware.tenant_context.validate_session",
                   return_value={"user_id": 5, "dwh_code": "SG"}):
            r = client.get("/api/dashboard", headers=_headers("SG"))
            assert r.status_code != 403

    def test_user_client_autre_dwh_403(self, client):
        """User client (session=SG) tentant MA → 403 (rejeu cross-tenant)."""
        with patch("app.middleware.tenant_context.validate_session",
                   return_value={"user_id": 5, "dwh_code": "SG"}):
            r = client.get("/api/dashboard", headers=_headers("MA"))
            assert r.status_code == 403

    def test_session_centrale_acces_autorise_pas_403(self, client):
        """Session centrale (dwh=None) + accès autorisé → la garde ne bloque pas."""
        with patch("app.middleware.tenant_context.validate_session",
                   return_value={"user_id": 1, "dwh_code": None}):
            with patch("app.security.user_can_access_dwh", return_value=True):
                r = client.get("/api/dashboard", headers=_headers("MA"))
                assert r.status_code != 403

    def test_session_centrale_acces_refuse_403(self, client):
        """Session centrale (dwh=None) + accès refusé → 403."""
        with patch("app.middleware.tenant_context.validate_session",
                   return_value={"user_id": 9, "dwh_code": None}):
            with patch("app.security.user_can_access_dwh", return_value=False):
                r = client.get("/api/dashboard", headers=_headers("MA"))
                assert r.status_code == 403

    def test_sans_session_pas_de_garde_mais_floor_401(self, client):
        """Sans session, le plancher d'auth renvoie 401 (la garde tenant ne s'applique pas)."""
        r = client.get("/api/dashboard", headers={"X-DWH-Code": "MA"})
        assert r.status_code == 401
