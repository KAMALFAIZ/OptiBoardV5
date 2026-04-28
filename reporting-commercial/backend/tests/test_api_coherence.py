"""
Tests de cohérence API - OptiBoard
Vérifie la structure des réponses, les schémas, et la cohérence des données
retournées par les endpoints REST (sans connexion DB réelle — tout mocké).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─────────────────────────────────────────────
# Fixtures communes
# ─────────────────────────────────────────────
@pytest.fixture(scope="module")
def ca_row_factory():
    """Fabrique une ligne de CA simulée."""
    def _make(annee=2025, mois=1, ca_ht=100_000, ca_ttc=120_000,
              cout=70_000, nb_clients=50, nb_transactions=200):
        return {
            "Annee": annee, "Mois": mois,
            "CA_HT": ca_ht, "CA_TTC": ca_ttc,
            "Cout_Total": cout, "Nb_Clients": nb_clients,
            "Nb_Transactions": nb_transactions,
        }
    return _make


@pytest.fixture(scope="module")
def balance_row_factory():
    """Fabrique une ligne de balance âgée simulée."""
    def _make(client="CLI001", solde=50_000, a30=20_000, a60=15_000,
              a90=10_000, a120=3_000, plus120=2_000):
        return {
            "Client": client,
            "Solde_Cloture": solde,
            "0-30": a30, "31-60": a60,
            "61-90": a90, "91-120": a120, "+120": plus120,
        }
    return _make


# ─────────────────────────────────────────────
# Helper — patch execute_app (database_unified)
# ─────────────────────────────────────────────
DB_PATCH = "app.database_unified.execute_app"


# ═══════════════════════════════════════════════════════════════════
# 1. Structure des réponses Dashboard
# ═══════════════════════════════════════════════════════════════════
class TestDashboardResponseStructure:
    """Vérifie que /api/dashboard retourne la structure attendue."""

    def _make_client(self, ca_rows, balance_rows):
        """Crée un TestClient avec les données mockées."""
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]  # ca, ca_n1, balance
            from run import app
            return TestClient(app), mock_db

    def test_champs_kpis_presents(self, ca_row_factory, balance_row_factory):
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        kpis = data["kpis"]
        for champ in ["ca_ht", "marge_brute", "dso", "encours_clients",
                      "nb_clients_actifs", "creances_douteuses"]:
            assert champ in kpis, f"Champ KPI manquant: {champ}"

    def test_chaque_kpi_a_value_et_label(self, ca_row_factory, balance_row_factory):
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        kpis = resp.json()["kpis"]
        for nom, kpi in kpis.items():
            assert "value" in kpi, f"KPI {nom}: 'value' absent"
            assert "label" in kpi, f"KPI {nom}: 'label' absent"

    def test_alertes_est_liste(self, ca_row_factory, balance_row_factory):
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        assert isinstance(resp.json()["alertes"], list)

    def test_date_mise_a_jour_presente(self, ca_row_factory, balance_row_factory):
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        assert "date_mise_a_jour" in resp.json()

    def test_ca_ht_coherent_avec_donnees(self, ca_row_factory, balance_row_factory):
        """ca_ht.value doit être la somme des CA_HT de la DB."""
        rows = [
            ca_row_factory(mois=1, ca_ht=100_000),
            ca_row_factory(mois=2, ca_ht=200_000),
        ]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        kpi_ca = resp.json()["kpis"]["ca_ht"]
        assert kpi_ca["value"] == pytest.approx(300_000)

    def test_marge_brute_coherente(self, ca_row_factory, balance_row_factory):
        """marge_brute = sum(CA_HT) - sum(Cout_Total)."""
        rows = [ca_row_factory(ca_ht=500_000, cout=350_000)]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        kpi_marge = resp.json()["kpis"]["marge_brute"]
        assert kpi_marge["value"] == pytest.approx(150_000)

    def test_encours_coherent_avec_balance(self, ca_row_factory, balance_row_factory):
        """encours_clients.value = sum(Solde_Cloture) de la balance âgée."""
        ca_rows = [ca_row_factory()]
        balance_rows = [
            balance_row_factory(solde=80_000),
            balance_row_factory(client="CLI002", solde=50_000),
        ]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        encours = resp.json()["kpis"]["encours_clients"]["value"]
        assert encours == pytest.approx(130_000)

    def test_dashboard_vide_retourne_zeros(self):
        """Aucune donnée DB → KPIs à 0, pas d'erreur."""
        with patch(DB_PATCH) as mock_db:
            mock_db.return_value = []
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["ca_ht"]["value"] == 0
        assert kpis["marge_brute"]["value"] == 0


# ═══════════════════════════════════════════════════════════════════
# 2. Cohérence Evolution mensuelle
# ═══════════════════════════════════════════════════════════════════
class TestEvolutionMensuelle:
    def test_structure_liste(self, ca_row_factory):
        rows = [ca_row_factory(mois=1), ca_row_factory(mois=2)]
        with patch(DB_PATCH, return_value=rows):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/evolution-mensuelle")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 2

    def test_champs_par_mois(self, ca_row_factory):
        with patch(DB_PATCH, return_value=[ca_row_factory()]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/evolution-mensuelle")

        item = resp.json()["data"][0]
        for champ in ["periode", "mois", "annee", "ca_ht", "ca_ttc",
                      "marge_brute", "nb_clients", "nb_transactions"]:
            assert champ in item, f"Champ manquant: {champ}"

    def test_periode_format_correct(self, ca_row_factory):
        """La période doit être au format YYYY-MM."""
        with patch(DB_PATCH, return_value=[ca_row_factory(annee=2025, mois=3)]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/evolution-mensuelle")

        item = resp.json()["data"][0]
        assert item["periode"] == "2025-03"

    def test_marge_calculee_correctement(self, ca_row_factory):
        """marge_brute = CA_HT - Cout_Total par ligne."""
        row = ca_row_factory(ca_ht=200_000, cout=130_000)
        with patch(DB_PATCH, return_value=[row]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/evolution-mensuelle")

        item = resp.json()["data"][0]
        assert item["marge_brute"] == pytest.approx(70_000)


# ═══════════════════════════════════════════════════════════════════
# 3. Cohérence Comparatif Annuel
# ═══════════════════════════════════════════════════════════════════
class TestComparatifAnnuel:
    def _make_annuel_row(self, annee, ca_ht=500_000, ca_ttc=600_000,
                         marge=150_000, nb_clients=100):
        return {"Annee": annee, "CA_HT": ca_ht, "CA_TTC": ca_ttc,
                "Marge_Brute": marge, "Nb_Clients": nb_clients}

    def test_evolution_calculee_correctement(self):
        rows = [
            self._make_annuel_row(2024, ca_ht=1_000_000),
            self._make_annuel_row(2025, ca_ht=1_200_000),
        ]
        with patch(DB_PATCH, return_value=rows):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel?annee=2025")

        assert resp.status_code == 200
        data = resp.json()
        assert data["evolution_pct"] == pytest.approx(20.0)

    def test_une_seule_annee_pas_evolution(self):
        rows = [self._make_annuel_row(2025)]
        with patch(DB_PATCH, return_value=rows):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel?annee=2025")

        # Pas de 2ème période → evolution None
        assert resp.json()["evolution_pct"] is None

    def test_structure_data(self):
        rows = [self._make_annuel_row(2024), self._make_annuel_row(2025)]
        with patch(DB_PATCH, return_value=rows):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel")

        data = resp.json()["data"]
        assert isinstance(data, list)
        for item in data:
            for champ in ["annee", "ca_ht", "ca_ttc", "marge_brute", "nb_clients"]:
                assert champ in item


# ═══════════════════════════════════════════════════════════════════
# 4. Cohérence filtres — Société
# ═══════════════════════════════════════════════════════════════════
class TestFiltresSociete:
    """Vérifie que le filtre société est bien transmis à la DB."""

    def test_filtre_societe_transmis(self, ca_row_factory, balance_row_factory):
        """Quand societe=TEST, le paramètre doit apparaître dans l'appel DB."""
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            client.get("/api/dashboard?societe=TEST")

        # Vérifier que "TEST" est bien passé comme paramètre
        calls = mock_db.call_args_list
        # Au moins un appel doit contenir "TEST" dans ses paramètres
        params_passed = [str(c) for c in calls]
        assert any("TEST" in p for p in params_passed), \
            "Le filtre société n'a pas été transmis à la DB"

    def test_sans_filtre_pas_de_societe(self, ca_row_factory, balance_row_factory):
        ca_rows = [ca_row_factory()]
        balance_rows = [balance_row_factory()]
        with patch(DB_PATCH) as mock_db:
            mock_db.side_effect = [ca_rows, [], balance_rows]
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")

        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 5. Format des réponses — BaseResponse wrapper
# ═══════════════════════════════════════════════════════════════════
class TestBaseResponseWrapper:
    """Tous les endpoints doivent retourner {success: bool, ...}."""

    ENDPOINTS = [
        "/api/dashboard/evolution-mensuelle",
        "/api/dashboard/comparatif-annuel",
    ]

    def test_tous_ont_champ_success(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            for endpoint in self.ENDPOINTS:
                resp = client.get(endpoint)
                assert resp.status_code == 200, f"Endpoint {endpoint} en erreur"
                assert "success" in resp.json(), f"Endpoint {endpoint}: 'success' absent"

    def test_success_true_quand_ok(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            for endpoint in self.ENDPOINTS:
                resp = client.get(endpoint)
                assert resp.json()["success"] is True, \
                    f"Endpoint {endpoint}: success=False sans erreur"


# ═══════════════════════════════════════════════════════════════════
# 6. Tests des codes HTTP
# ═══════════════════════════════════════════════════════════════════
class TestCodesHTTP:
    def test_dashboard_retourne_200(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard")
        assert resp.status_code == 200

    def test_evolution_mensuelle_retourne_200(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/evolution-mensuelle")
        assert resp.status_code == 200

    def test_comparatif_annuel_retourne_200(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel")
        assert resp.status_code == 200

    def test_route_inexistante_retourne_404(self):
        with patch(DB_PATCH, return_value=[]):
            from run import app
            client = TestClient(app)
            resp = client.get("/api/dashboard/inexistant")
        assert resp.status_code == 404
