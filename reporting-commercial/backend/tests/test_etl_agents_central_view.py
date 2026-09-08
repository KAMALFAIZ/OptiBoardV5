"""Régression — vue centrale de /api/admin/etl/agents réservée au superadmin.

Bug corrigé : `list_agents` basculait sur la vue centrale (APP_ETL_Agents_Monitoring,
TOUS les tenants) dès que l'appelant envoyait `X-User-Role: superadmin`. Cet en-tête
est fourni par le client, donc falsifiable, et le routeur etl_agents n'est pas protégé
par `require_superadmin` (il doit rester joignable par l'agent ETL). N'importe quel
utilisateur authentifié d'un tenant pouvait ainsi énumérer les agents de tous les
clients (code DWH, nom, hostname, IP, heartbeats).

Après correctif : la vue centrale exige un superadmin CENTRAL prouvé par une session
validée (`security.is_superadmin_session`), fail-closed. La vue client (X-DWH-Code =
un tenant) est inchangée et ne lit que la base de ce tenant.

Hermétique : aucune base de données n'est touchée (accès SQL et session mockés).
"""
import pytest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

TOKEN = "t" * 64


@pytest.fixture
def client():
    from app.routes.etl_agents import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _session_patches(session, role_global):
    """Session validée + rôle central résolu en base (comme security._resolve_role)."""
    return (
        patch("app.security.validate_session", return_value=session),
        patch("app.security.client_manager.has_client_db", return_value=False),
        patch("app.security.execute_central", return_value=[{"role_global": role_global}]),
    )


class TestVueCentraleAgents:
    @pytest.mark.parametrize("headers", [
        {},                                                   # ni tenant ni session
        {"X-DWH-Code": "CENTRAL"},                            # vue centrale sans session
        {"X-User-Role": "superadmin"},                        # LA faille : rôle forgé
        {"X-DWH-Code": "CENTRAL", "X-User-Role": "superadmin"},
    ])
    def test_sans_session_superadmin_la_vue_centrale_est_refusee(self, client, headers):
        r = client.get("/api/admin/etl/agents", headers=headers)
        assert r.status_code == 403, r.text

    def test_session_tenant_meme_avec_role_forge_ne_voit_pas_le_parc(self, client):
        """Session liée à un tenant + X-User-Role forgé → 403 (pas de vue centrale)."""
        session = {"user_id": 1, "dwh_code": "AMM"}
        p1, p2, p3 = _session_patches(session, "admin_client")
        with p1, p2, p3:
            r = client.get("/api/admin/etl/agents", headers={
                "X-Session-Token": TOKEN,
                "X-DWH-Code": "CENTRAL",
                "X-User-Role": "superadmin",
            })
        assert r.status_code == 403, r.text

    def test_session_invalide_est_refusee(self, client):
        """Fail-closed : validate_session ne renvoie rien → 403."""
        with patch("app.security.validate_session", return_value=None):
            r = client.get("/api/admin/etl/agents", headers={
                "X-Session-Token": TOKEN, "X-DWH-Code": "CENTRAL",
            })
        assert r.status_code == 403, r.text

    def test_superadmin_central_voit_le_parc(self, client):
        """Session centrale + role_global=superadmin → vue monitoring (tous tenants)."""
        session = {"user_id": 1, "dwh_code": None}

        def fake_central(query, params=None, use_cache=True, **kw):
            if "APP_ETL_Agents_Monitoring" in query:
                return [
                    {"agent_id": "a1", "nom": "ALEA_FOOD", "dwh_code": "ALEAFOOD"},
                    {"agent_id": "a2", "nom": "ATLASMULTIMATERIAL", "dwh_code": "AMM"},
                ]
            if "APP_DWH" in query:
                return []
            return []

        p1, p2, p3 = _session_patches(session, "superadmin")
        with p1, p2, p3, \
                patch("app.routes.etl_agents.execute_central", side_effect=fake_central), \
                patch("app.routes.etl_agents.execute_client", return_value=[]):
            r = client.get("/api/admin/etl/agents", headers={
                "X-Session-Token": TOKEN, "X-DWH-Code": "CENTRAL",
            })
        assert r.status_code == 200, r.text
        codes = sorted(a["dwh_code"] for a in r.json()["data"])
        assert codes == ["ALEAFOOD", "AMM"]


class TestVueClientInchangee:
    def test_vue_client_ne_lit_que_la_base_du_tenant(self, client):
        """X-DWH-Code = tenant → APP_ETL_Agents de CE tenant, dwh_code forcé au tenant."""
        captured = {}

        class FakeCursor:
            description = [("agent_id",), ("nom",)]

            def execute(self, query, params=()):
                captured["query"] = query

            def fetchall(self):
                return [("a2", "ATLASMULTIMATERIAL")]

        class FakeCtx:
            def __enter__(self):
                return FakeCursor()

            def __exit__(self, *a):
                return False

        def fake_client_cursor(dwh_code):
            captured["dwh_code"] = dwh_code
            return FakeCtx()

        with patch("app.routes.etl_agents._get_demo_session", return_value=None), \
                patch("app.routes.etl_agents.client_cursor", side_effect=fake_client_cursor), \
                patch("app.routes.etl_agents.dec_secret_rows"), \
                patch("app.routes.etl_agents.execute_central", return_value=[]):
            r = client.get("/api/admin/etl/agents", headers={"X-DWH-Code": "AMM"})

        assert r.status_code == 200, r.text
        assert captured["dwh_code"] == "AMM"
        assert "APP_ETL_Agents_Monitoring" not in captured["query"]
        assert [a["dwh_code"] for a in r.json()["data"]] == ["AMM"]
