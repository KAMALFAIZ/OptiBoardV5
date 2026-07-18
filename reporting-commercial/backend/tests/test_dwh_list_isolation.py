"""Régression P0 — isolation du sélecteur « Changer de base ».

Bug corrigé : /api/auth/dwh-list dérivait l'identité du header X-User-Id
(falsifiable). L'id d'une base CLIENT (ex. admin AMM = id 1) entrait en collision
avec le superadmin de la base CENTRALE (id 1) → l'admin tenant était promu
superadmin et voyait TOUS les tenants, et pouvait basculer vers n'importe quel DWH.

Après correctif : l'autorisation vient de la SESSION validée. Une session liée à
un tenant ne voit QUE son DWH et ne peut pas basculer vers un autre.

Hermétique : validate_session, execute_central et has_client_db sont mockés.
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


def _patches(session):
    """Patche les deux points d'appel de validate_session + neutralise le check DB."""
    return (
        patch("app.middleware.tenant_context.validate_session", return_value=session),
        patch("app.routes.auth_multitenant.validate_session", return_value=session),
        patch("app.middleware.tenant_context.client_manager.has_client_db", return_value=True),
    )


class TestDwhListIsolation:
    def test_tenant_id_collision_ne_voit_que_son_dwh(self, client):
        """admin AMM (id client 1 == superadmin central 1) → UNIQUEMENT AMM."""
        session = {"user_id": 1, "dwh_code": "AMM"}

        def fake_central(query, params=None, use_cache=True, **kw):
            if "WHERE code = ?" in query:  # la seule requête légitime (branche tenant)
                return [{"code": "AMM", "nom": "ATLAS MULTI MATERIAL",
                         "raison_sociale": None, "logo_url": None, "is_default": 1}]
            # Toute retombée sur le lookup central = régression → superadmin = fuite
            return [{"role_global": "superadmin"}]

        p1, p2, p3 = _patches(session)
        with p1, p2, p3, patch("app.routes.auth_multitenant.execute_central", side_effect=fake_central):
            r = client.get("/api/auth/dwh-list",
                           headers={"X-Session-Token": TOKEN, "X-DWH-Code": "AMM"})
        assert r.status_code == 200, r.text
        codes = [d["code"] for d in r.json()]
        assert codes == ["AMM"], f"fuite cross-tenant : {codes}"

    def test_session_centrale_superadmin_voit_tout(self, client):
        """Session centrale (dwh=None) + superadmin réel → tous les DWH."""
        session = {"user_id": 1, "dwh_code": None}

        def fake_central(query, params=None, use_cache=True, **kw):
            if "role_global" in query:
                return [{"role_global": "superadmin"}]
            if "WHERE actif=1" in query:
                return [{"code": "AMM", "nom": "AMM"},
                        {"code": "KA", "nom": "KA"},
                        {"code": "ALEAFOOD", "nom": "ALEA"}]
            return []

        p1, p2, p3 = _patches(session)
        with p1, p2, p3, patch("app.routes.auth_multitenant.execute_central", side_effect=fake_central):
            r = client.get("/api/auth/dwh-list", headers={"X-Session-Token": TOKEN})
        assert r.status_code == 200, r.text
        assert len(r.json()) == 3

    def test_dwh_list_sans_session_401(self, client):
        """Sans session, le plancher d'auth bloque (plus dans SESSION_OPTIONAL)."""
        r = client.get("/api/auth/dwh-list")
        assert r.status_code == 401

    def test_switch_dwh_tenant_vers_autre_403(self, client):
        """Session tenant AMM tentant de basculer vers KA → 403."""
        session = {"user_id": 1, "dwh_code": "AMM"}
        p1, p2, p3 = _patches(session)
        with p1, p2, p3:
            r = client.post("/api/auth/switch-dwh", json={"dwh_code": "KA"},
                            headers={"X-Session-Token": TOKEN})
        assert r.status_code == 403, r.text

    def test_context_tenant_pas_escalade_superadmin(self, client):
        """P1 : /context d'un user tenant (id 1) ne doit PAS être promu superadmin
        ni exposer d'autres DWH — identité lue en base CLIENT."""
        session = {"user_id": 1, "dwh_code": "AMM"}

        def fake_client(query, params=None, dwh_code=None, use_cache=True, **kw):
            if "role_dwh FROM APP_Users" in query:
                return [{"id": 1, "username": "admin", "nom": "A", "prenom": "B",
                         "email": "a@x", "role_dwh": "user"}]
            if "page_code" in query:
                return [{"page_code": "dashboard"}]
            return []

        def fake_central(query, params=None, use_cache=True, **kw):
            if "FROM APP_DWH WHERE code" in query:
                return [{"nom": "ATLAS MULTI MATERIAL"}]
            return [{"role_global": "superadmin"}]  # piège : ne doit PAS être atteint

        p1, p2, p3 = _patches(session)
        with p1, p2, p3, \
             patch("app.routes.auth_multitenant.execute_client", side_effect=fake_client), \
             patch("app.routes.auth_multitenant.execute_central", side_effect=fake_central):
            r = client.get("/api/auth/context",
                           headers={"X-Session-Token": TOKEN, "X-DWH-Code": "AMM"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["role_global"] == "user", "escalade superadmin !"
        assert d["is_admin"] is False
        assert [x["code"] for x in d["dwh_accessibles"]] == ["AMM"]
        assert d["current_dwh"]["code"] == "AMM"

    def test_context_sans_session_401(self, client):
        r = client.get("/api/auth/context")
        assert r.status_code == 401
