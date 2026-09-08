"""Régression — l'en-tête X-User-Role ne fait plus autorité.

`X-User-Role` est fourni par l'appelant : il est falsifiable (un simple curl le
pose). Trois familles de routes s'en servaient comme unique garde de rôle :

  - /api/demo/admin/sessions[...]   : le préfixe /api/demo est SESSION_OPTIONAL
    (inscription publique + agent démo), donc ces routes admin étaient
    atteignables SANS session — lister les sessions démo (jetons, emails),
    les révoquer ou les prolonger ne demandait que `X-User-Role: superadmin`.
  - /api/datasources/templates      : protection des templates `is_system`
    (création / modification / suppression).
  - /api/admin/etl/agents           : cf. test_etl_agents_central_view.py.

Après correctif, le rôle vient d'une session validée (`require_superadmin` /
`is_superadmin_session`), fail-closed. Hermétique : aucune base touchée.
"""
import pytest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

TOKEN = "t" * 64
FORGE = {"X-User-Role": "superadmin"}


def _session_patches(session, role_global):
    """Session validée + rôle central résolu en base (cf. security._resolve_role)."""
    return (
        patch("app.security.validate_session", return_value=session),
        patch("app.security.client_manager.has_client_db", return_value=False),
        patch("app.security.execute_central", return_value=[{"role_global": role_global}]),
    )


# ============================================================
# Portail démo — routes admin
# ============================================================

@pytest.fixture
def demo_client():
    from app.routes.demo_portal import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestDemoAdminRoutes:
    ROUTES = [
        ("get", "/api/demo/admin/sessions"),
        ("delete", "/api/demo/admin/sessions/abc"),
        ("post", "/api/demo/admin/sessions/abc/extend"),
    ]

    @pytest.mark.parametrize("method,url", ROUTES)
    def test_sans_session_refuse(self, demo_client, method, url):
        r = getattr(demo_client, method)(url)
        assert r.status_code == 401, r.text

    @pytest.mark.parametrize("method,url", ROUTES)
    def test_role_forge_sans_session_refuse(self, demo_client, method, url):
        """LA faille : un simple en-tête suffisait à passer."""
        r = getattr(demo_client, method)(url, headers=FORGE)
        assert r.status_code == 401, r.text

    @pytest.mark.parametrize("method,url", ROUTES)
    def test_session_non_superadmin_refuse(self, demo_client, method, url):
        session = {"user_id": 1, "dwh_code": None}
        p1, p2, p3 = _session_patches(session, "admin")
        with p1, p2, p3:
            r = getattr(demo_client, method)(url, headers={"X-Session-Token": TOKEN, **FORGE})
        assert r.status_code == 403, r.text

    def test_superadmin_central_autorise(self, demo_client):
        session = {"user_id": 1, "dwh_code": None}
        p1, p2, p3 = _session_patches(session, "superadmin")
        with p1, p2, p3, patch("app.routes.demo_portal.execute_query", return_value=[]):
            r = demo_client.get("/api/demo/admin/sessions",
                                headers={"X-Session-Token": TOKEN})
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True


# ============================================================
# Templates de datasources — garde `is_system`
# ============================================================

@pytest.fixture
def ds_client():
    from app.routes.datasource_templates import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestTemplatesSysteme:
    PAYLOAD = {"code": "DS_TEST", "nom": "Test", "query_template": "SELECT 1",
               "is_system": True}

    def test_creation_systeme_avec_role_forge_refusee(self, ds_client):
        r = ds_client.post("/api/datasources/templates", json=self.PAYLOAD, headers=FORGE)
        assert r.status_code == 403, r.text
        assert "superadmin" in r.json()["detail"]

    def test_modification_systeme_avec_role_forge_refusee(self, ds_client):
        with patch("app.routes.datasource_templates.execute_query",
                   return_value=[{"id": 1, "is_system": True}]):
            r = ds_client.put("/api/datasources/templates/1", json={"nom": "X"}, headers=FORGE)
        assert r.status_code == 403, r.text

    def test_suppression_systeme_avec_role_forge_refusee(self, ds_client):
        with patch("app.routes.datasource_templates.execute_query",
                   return_value=[{"id": 1, "is_system": True, "code": "DS_SYS"}]):
            r = ds_client.delete("/api/datasources/templates/id/1", headers=FORGE)
        assert r.status_code == 403, r.text

    def test_superadmin_reel_peut_supprimer_un_template_systeme(self, ds_client):
        session = {"user_id": 1, "dwh_code": None}
        p1, p2, p3 = _session_patches(session, "superadmin")

        class FakeCursor:
            def execute(self, *a, **kw):
                pass

        class FakeCtx:
            def __enter__(self):
                return FakeCursor()

            def __exit__(self, *a):
                return False

        with p1, p2, p3, \
                patch("app.routes.datasource_templates.execute_query",
                      return_value=[{"id": 1, "is_system": True, "code": "DS_SYS"}]), \
                patch("app.routes.datasource_templates.get_db_cursor", return_value=FakeCtx()):
            r = ds_client.delete("/api/datasources/templates/id/1",
                                 headers={"X-Session-Token": TOKEN})
        assert r.status_code == 200, r.text

    def test_template_non_systeme_reste_modifiable_sans_superadmin(self, ds_client):
        """Non-régression : la garde ne concerne que les templates is_system."""
        class FakeCursor:
            def execute(self, *a, **kw):
                pass

        class FakeCtx:
            def __enter__(self):
                return FakeCursor()

            def __exit__(self, *a):
                return False

        with patch("app.routes.datasource_templates.execute_query",
                   return_value=[{"id": 2, "is_system": False}]), \
                patch("app.routes.datasource_templates.get_db_cursor", return_value=FakeCtx()):
            r = ds_client.put("/api/datasources/templates/2", json={"nom": "Nouveau nom"})
        assert r.status_code == 200, r.text
