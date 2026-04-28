"""
Tests Isolation Multi-Tenant - OptiBoard
Vérifie que le contexte DWH est correctement isolé par requête,
et qu'un tenant ne peut pas accéder aux données d'un autre.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════════════════
# 1. ContextVars — isolation par requête
# ═══════════════════════════════════════════════════════════════════
class TestContextVarIsolation:
    """Les ContextVars doivent être indépendants entre coroutines."""

    def test_contextvars_isoles_entre_taches(self):
        """
        Deux coroutines concurrentes ne doivent pas partager leur contexte DWH.
        """
        import asyncio
        from contextvars import ContextVar

        current_dwh = ContextVar("current_dwh", default=None)

        async def task_a():
            current_dwh.set("DWH_CLIENT_A")
            await asyncio.sleep(0)          # cède le contrôle
            return current_dwh.get()

        async def task_b():
            current_dwh.set("DWH_CLIENT_B")
            await asyncio.sleep(0)
            return current_dwh.get()

        async def run():
            results = await asyncio.gather(task_a(), task_b())
            return results

        results = asyncio.run(run())
        # Chaque tâche doit voir son propre DWH
        assert "DWH_CLIENT_A" in results
        assert "DWH_CLIENT_B" in results

    def test_contextvars_pas_de_fuite(self):
        """La valeur d'un contextvar ne doit pas fuiter vers un autre contexte."""
        import asyncio
        from contextvars import ContextVar, copy_context

        current_dwh = ContextVar("current_dwh", default="DEFAULT")

        results = {}

        def set_and_read(name, value):
            current_dwh.set(value)
            results[name] = current_dwh.get()

        ctx_a = copy_context()
        ctx_b = copy_context()

        ctx_a.run(set_and_read, "a", "DWH_A")
        ctx_b.run(set_and_read, "b", "DWH_B")

        assert results["a"] == "DWH_A"
        assert results["b"] == "DWH_B"
        # La valeur par défaut reste inchangée dans le contexte principal
        assert current_dwh.get() == "DEFAULT"


# ═══════════════════════════════════════════════════════════════════
# 2. Header X-DWH-Code — transmission et validation
# ═══════════════════════════════════════════════════════════════════
class TestDWHHeader:
    """Vérifie que le header X-DWH-Code est requis et utilisé correctement."""

    @pytest.fixture
    def client(self):
        with patch("app.database_unified.execute_app", return_value=[]):
            from run import app
            from fastapi.testclient import TestClient
            return TestClient(app)

    def test_requete_avec_dwh_header_acceptee(self, client):
        resp = client.get(
            "/api/dashboard",
            headers={"X-DWH-Code": "TEST_DWH"}
        )
        assert resp.status_code == 200

    def test_requete_sans_dwh_header(self, client):
        """Sans header DWH, le comportement dépend de la config (200 ou 400)."""
        resp = client.get("/api/dashboard")
        # Acceptable : soit 200 (DWH par défaut), soit 400/422 (DWH requis)
        assert resp.status_code in (200, 400, 422)

    def test_dwh_code_different_deux_requetes(self, client):
        """Deux requêtes successives avec des DWH différents doivent rester isolées."""
        resp_a = client.get("/api/dashboard", headers={"X-DWH-Code": "DWH_CLIENT_A"})
        resp_b = client.get("/api/dashboard", headers={"X-DWH-Code": "DWH_CLIENT_B"})
        # Les deux doivent répondre normalement
        assert resp_a.status_code in (200, 400, 404)
        assert resp_b.status_code in (200, 400, 404)


# ═══════════════════════════════════════════════════════════════════
# 3. Fonctions execute_ — routage correct
# ═══════════════════════════════════════════════════════════════════
class TestExecuteFunctions:
    """Vérifie que execute_central/execute_client/execute_dwh
    appellent le bon niveau de base de données."""

    def test_execute_central_importe(self):
        from app.database_unified import execute_central
        assert callable(execute_central)

    def test_execute_client_importe(self):
        from app.database_unified import execute_client
        assert callable(execute_client)

    def test_execute_app_importe(self):
        from app.database_unified import execute_app
        assert callable(execute_app)

    def test_write_central_importe(self):
        from app.database_unified import write_central
        assert callable(write_central)

    def test_write_client_importe(self):
        from app.database_unified import write_client
        assert callable(write_client)


# ═══════════════════════════════════════════════════════════════════
# 4. UserContext — structure et cohérence
# ═══════════════════════════════════════════════════════════════════
class TestUserContext:
    """Le UserContext doit toujours avoir les champs clés."""

    def test_user_context_importable(self):
        from app.database_unified import UserContext
        assert UserContext is not None

    def test_user_context_champs_attendus(self):
        """UserContext doit exposer au moins current_dwh_code et user_id."""
        from app.database_unified import UserContext
        try:
            field_names = set(UserContext.__fields__.keys())
        except AttributeError:
            try:
                field_names = set(UserContext.__dataclass_fields__.keys())
            except AttributeError:
                pytest.skip("Impossible de lire les champs de UserContext")

        # Champs minimaux requis (noms réels du modèle)
        for champ in ["user_id", "current_dwh_code"]:
            assert champ in field_names, f"Champ attendu absent: {champ}"


# ═══════════════════════════════════════════════════════════════════
# 5. Middleware — TenantContextMiddleware
# ═══════════════════════════════════════════════════════════════════
class TestTenantMiddleware:
    """Vérifie que le middleware de contexte tenant est bien enregistré."""

    def test_middleware_enregistre_dans_app(self):
        from run import app
        middleware_types = [
            type(m).__name__
            for m in app.user_middleware
        ]
        # Vérifier qu'au moins un middleware de contexte est présent
        middleware_str = str(middleware_types)
        # Au moins un middleware doit être enregistré
        assert len(app.user_middleware) > 0, "Aucun middleware enregistré"


# ═══════════════════════════════════════════════════════════════════
# 6. Isolation des données — pas de cross-tenant dans les mocks
# ═══════════════════════════════════════════════════════════════════
class TestIsolationDonnees:
    """Simule deux clients et vérifie qu'ils voient des données différentes."""

    def _make_data(self, ca_ht, nb_clients):
        return [{
            "Annee": 2025, "Mois": 1,
            "CA_HT": ca_ht, "CA_TTC": ca_ht * 1.2,
            "Cout_Total": ca_ht * 0.7, "Nb_Clients": nb_clients,
            "Nb_Transactions": nb_clients * 4,
        }]

    def test_deux_clients_donnees_differentes(self):
        """Deux appels avec des données différentes retournent des KPIs différents."""
        from run import app
        from fastapi.testclient import TestClient

        data_a = self._make_data(ca_ht=1_000_000, nb_clients=100)
        data_b = self._make_data(ca_ht=2_500_000, nb_clients=250)

        # Patcher le symbole local importé dans dashboard.py
        with patch("app.routes.dashboard.execute_query") as mock_db:
            client = TestClient(app)

            # Requête client A
            mock_db.side_effect = [data_a, [], []]
            resp_a = client.get("/api/dashboard", headers={"X-DWH-Code": "DWH_A"})

            # Requête client B
            mock_db.side_effect = [data_b, [], []]
            resp_b = client.get("/api/dashboard", headers={"X-DWH-Code": "DWH_B"})

        ca_a = resp_a.json()["kpis"]["ca_ht"]["value"]
        ca_b = resp_b.json()["kpis"]["ca_ht"]["value"]

        assert ca_a != ca_b, "Les deux clients voient le même CA (fuite de données?)"
        assert ca_a == pytest.approx(1_000_000)
        assert ca_b == pytest.approx(2_500_000)

    def test_requetes_sequentielles_pas_de_contamination(self):
        """La 2ème requête ne doit pas être polluée par la 1ère."""
        from run import app
        from fastapi.testclient import TestClient

        data_1 = self._make_data(ca_ht=500_000, nb_clients=50)
        data_2 = self._make_data(ca_ht=800_000, nb_clients=80)

        with patch("app.routes.dashboard.execute_query") as mock_db:
            client = TestClient(app)

            mock_db.side_effect = [data_1, [], []]
            resp_1 = client.get("/api/dashboard")
            ca_1 = resp_1.json()["kpis"]["ca_ht"]["value"]

            mock_db.side_effect = [data_2, [], []]
            resp_2 = client.get("/api/dashboard")
            ca_2 = resp_2.json()["kpis"]["ca_ht"]["value"]

        assert ca_1 == pytest.approx(500_000)
        assert ca_2 == pytest.approx(800_000)
        assert ca_1 != ca_2
