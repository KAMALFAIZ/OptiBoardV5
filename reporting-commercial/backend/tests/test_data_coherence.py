"""
Tests de Cohérence des Données - OptiBoard
Vérifie que les données sont cohérentes entre elles :
- Les totaux du dashboard correspondent aux détails des endpoints ventes/stocks/recouvrement
- Les agrégations sont mathématiquement correctes
- Les filtres de date et société produisent des sous-ensembles cohérents
"""
import pytest
from unittest.mock import patch
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATCH = "app.database_unified.execute_app"


# ─────────────────────────────────────────────
# Fixtures de données réalistes
# ─────────────────────────────────────────────
def make_ca_rows(n_mois=12, base_ca=100_000, base_cout=70_000):
    """Génère n_mois lignes de CA mensuelles cohérentes."""
    return [
        {
            "Annee": 2025, "Mois": m,
            "CA_HT": base_ca + m * 5_000,
            "CA_TTC": (base_ca + m * 5_000) * 1.2,
            "Cout_Total": base_cout + m * 3_000,
            "Nb_Clients": 50 + m,
            "Nb_Transactions": (50 + m) * 4,
        }
        for m in range(1, n_mois + 1)
    ]


def make_balance_rows(n_clients=5, base_solde=20_000):
    """Génère des lignes de balance âgée pour n_clients."""
    rows = []
    for i in range(n_clients):
        solde = base_solde + i * 5_000
        rows.append({
            "Client": f"CLI{i:03d}",
            "Solde_Cloture": solde,
            "0-30": solde * 0.5,
            "31-60": solde * 0.2,
            "61-90": solde * 0.1,
            "91-120": solde * 0.1,
            "+120": solde * 0.1,
        })
    return rows


# ═══════════════════════════════════════════════════════════════════
# 1. Cohérence Dashboard ↔ Evolution mensuelle
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceDashboardEvolution:
    """Le CA total du dashboard doit être la somme des CA mensuels."""

    def test_ca_dashboard_egal_somme_evolution(self):
        ca_rows = make_ca_rows(n_mois=6, base_ca=200_000)
        balance_rows = make_balance_rows()

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            # Dashboard — utilise les mêmes données
            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp_dash = client.get("/api/dashboard")
            ca_dashboard = resp_dash.json()["kpis"]["ca_ht"]["value"]

            # Evolution mensuelle — mêmes données
            mock_db.reset_mock()
            mock_db.return_value = ca_rows
            resp_evol = client.get("/api/dashboard/evolution-mensuelle")
            ca_sum_evol = sum(item["ca_ht"] for item in resp_evol.json()["data"])

        assert ca_dashboard == pytest.approx(ca_sum_evol, rel=1e-4), \
            f"Dashboard CA ({ca_dashboard}) ≠ Somme évolution ({ca_sum_evol})"

    def test_marge_dashboard_egal_somme_evolution(self):
        ca_rows = make_ca_rows(n_mois=3, base_ca=300_000)
        balance_rows = make_balance_rows(n_clients=3)

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp_dash = client.get("/api/dashboard")
            marge_dashboard = resp_dash.json()["kpis"]["marge_brute"]["value"]

            mock_db.reset_mock()
            mock_db.return_value = ca_rows
            resp_evol = client.get("/api/dashboard/evolution-mensuelle")
            marge_sum_evol = sum(item["marge_brute"] for item in resp_evol.json()["data"])

        assert marge_dashboard == pytest.approx(marge_sum_evol, rel=1e-4), \
            f"Dashboard Marge ({marge_dashboard}) ≠ Somme évolution ({marge_sum_evol})"

    def test_nb_clients_dashboard_somme_mensuelle(self):
        ca_rows = make_ca_rows(n_mois=4)
        balance_rows = make_balance_rows(n_clients=2)

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp_dash = client.get("/api/dashboard")
            nb_dashboard = resp_dash.json()["kpis"]["nb_clients_actifs"]["value"]

            mock_db.reset_mock()
            mock_db.return_value = ca_rows
            resp_evol = client.get("/api/dashboard/evolution-mensuelle")
            nb_sum_evol = sum(item["nb_clients"] for item in resp_evol.json()["data"])

        assert nb_dashboard == pytest.approx(nb_sum_evol, rel=1e-4)


# ═══════════════════════════════════════════════════════════════════
# 2. Cohérence Balance Âgée ↔ KPI Encours
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceBalanceEncours:
    """L'encours dashboard = somme(Solde_Cloture) de la balance âgée."""

    def test_encours_coherent(self):
        balance_rows = make_balance_rows(n_clients=4, base_solde=30_000)
        encours_attendu = sum(r["Solde_Cloture"] for r in balance_rows)

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            mock_db.side_effect = [make_ca_rows(1), [], balance_rows]
            resp = client.get("/api/dashboard")

        encours_kpi = resp.json()["kpis"]["encours_clients"]["value"]
        assert encours_kpi == pytest.approx(encours_attendu, rel=1e-4)

    def test_creances_douteuses_coherentes(self):
        """creances_douteuses = sum(+120) de la balance."""
        balance_rows = make_balance_rows(n_clients=3, base_solde=50_000)
        creances_attendues = sum(r["+120"] for r in balance_rows)

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            mock_db.side_effect = [make_ca_rows(1), [], balance_rows]
            resp = client.get("/api/dashboard")

        creances_kpi = resp.json()["kpis"]["creances_douteuses"]["value"]
        assert creances_kpi == pytest.approx(creances_attendues, rel=1e-4)


# ═══════════════════════════════════════════════════════════════════
# 3. Cohérence Calculs KPI — pas de divergence entre services
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceCalculsKPI:
    """Les KPIs calculés manuellement doivent correspondre à ceux du dashboard."""

    def test_dso_calcule_manuellement(self):
        ca_ht = 1_200_000
        ca_ttc = ca_ht * 1.2
        encours = 200_000
        ca_rows = [{
            "Annee": 2025, "Mois": 1,
            "CA_HT": ca_ht, "CA_TTC": ca_ttc,
            "Cout_Total": 840_000, "Nb_Clients": 100, "Nb_Transactions": 400,
        }]
        balance_rows = [{"Client": "CLI001", "Solde_Cloture": encours,
                         "0-30": encours * 0.7, "31-60": encours * 0.2,
                         "61-90": 0, "91-120": 0, "+120": encours * 0.1}]

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp = client.get("/api/dashboard")

        dso_api = resp.json()["kpis"]["dso"]["value"]

        from app.services.calculs import calculer_dso
        dso_attendu = calculer_dso(encours, ca_ttc)
        assert dso_api == pytest.approx(dso_attendu, rel=1e-3)

    def test_marge_taux_coherent_avec_ca(self):
        """taux_marge = marge / ca_ht × 100 doit être cohérent."""
        ca_ht = 500_000
        cout = 350_000
        marge = ca_ht - cout

        from app.services.calculs import calculer_marge_brute
        result = calculer_marge_brute(ca_ht, cout)

        taux_attendu = marge / ca_ht * 100
        assert result["taux_marge"] == pytest.approx(taux_attendu, rel=1e-3)

    def test_evolution_ca_n_vs_n1(self):
        """L'évolution entre N et N-1 doit être calculée correctement."""
        ca_n1 = 1_000_000
        ca_n = 1_250_000
        evolution_attendue = (ca_n - ca_n1) / ca_n1 * 100  # 25%

        from app.services.calculs import calculer_evolution
        result = calculer_evolution(ca_n, ca_n1)

        assert result["evolution_pct"] == pytest.approx(evolution_attendue, rel=1e-3)
        assert result["tendance"] == "hausse"


# ═══════════════════════════════════════════════════════════════════
# 4. Cohérence des filtres de période
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceFiltrePeriode:
    """Vérifie que les plages de dates sont cohérentes pour tous les presets."""

    @pytest.mark.parametrize("periode", [
        "annee_courante",
        "annee_precedente",
        "mois_courant",
        "trimestre_courant",
        "12_derniers_mois",
    ])
    def test_debut_avant_fin(self, periode):
        from app.services.calculs import get_periode_dates
        debut, fin = get_periode_dates(periode)
        assert debut <= fin, f"{periode}: début ({debut}) > fin ({fin})"

    @pytest.mark.parametrize("periode", [
        "annee_courante",
        "annee_precedente",
        "mois_courant",
        "trimestre_courant",
        "12_derniers_mois",
    ])
    def test_format_date_correct(self, periode):
        from app.services.calculs import get_periode_dates
        import re
        debut, fin = get_periode_dates(periode)
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        assert re.match(pattern, debut), f"{periode}: format début incorrect: {debut}"
        assert re.match(pattern, fin), f"{periode}: format fin incorrect: {fin}"

    def test_annee_precedente_une_annee_avant(self):
        from datetime import datetime
        from app.services.calculs import get_periode_dates

        debut_prec, fin_prec = get_periode_dates("annee_precedente")
        annee_prec = int(debut_prec[:4])
        annee_courante = datetime.now().year
        assert annee_prec == annee_courante - 1

    def test_n1_calculee_correctement(self):
        """La date N-1 doit être exactement 1 an avant."""
        debut = "2025-01-01"
        fin = "2025-04-15"
        annee_courante = int(debut[:4])

        debut_n1 = debut.replace(str(annee_courante), str(annee_courante - 1))
        fin_n1 = fin.replace(str(annee_courante), str(annee_courante - 1))

        assert debut_n1 == "2024-01-01"
        assert fin_n1 == "2024-04-15"


# ═══════════════════════════════════════════════════════════════════
# 5. Cohérence des aggregations — safe_sum vs sum natif
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceAggregation:
    """safe_sum doit produire les mêmes résultats que sum() pour des entiers."""

    def test_safe_sum_egal_sum_natif(self):
        from app.services.calculs import safe_sum

        data = [{"ca": 100_000}, {"ca": 200_000}, {"ca": 300_000}]
        resultat_safe = safe_sum(data, "ca")
        resultat_natif = sum(row["ca"] for row in data)

        assert resultat_safe == pytest.approx(resultat_natif)

    def test_aggregation_ca_avec_none(self):
        """Les None doivent être traités comme 0."""
        from app.services.calculs import safe_sum

        data = [{"ca": 100_000}, {"ca": None}, {"ca": 200_000}]
        resultat_safe = safe_sum(data, "ca")
        assert resultat_safe == pytest.approx(300_000)

    def test_aggregation_zero_dans_liste(self):
        from app.services.calculs import safe_sum

        data = [{"ca": 0}, {"ca": 0}]
        assert safe_sum(data, "ca") == 0.0

    def test_aggregation_grands_nombres(self):
        """Test avec des montants réalistes grands (milliards)."""
        from app.services.calculs import safe_sum

        data = [{"ca": 500_000_000}, {"ca": 750_000_000}]
        assert safe_sum(data, "ca") == pytest.approx(1_250_000_000)


# ═══════════════════════════════════════════════════════════════════
# 6. Cohérence Comparatif Annuel
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceComparatifAnnuel:
    """Vérifie que le calcul d'évolution N/N-1 est correct."""

    def _row(self, annee, ca_ht):
        return {"Annee": annee, "CA_HT": ca_ht, "CA_TTC": ca_ht * 1.2,
                "Marge_Brute": ca_ht * 0.3, "Nb_Clients": 100}

    @pytest.mark.parametrize("ca_n1,ca_n,expected_evol", [
        (1_000_000, 1_200_000, 20.0),
        (1_000_000, 800_000, -20.0),
        (1_000_000, 1_000_000, 0.0),
        (500_000, 750_000, 50.0),
    ])
    def test_evolution_parametrique(self, ca_n1, ca_n, expected_evol):
        rows = [self._row(2024, ca_n1), self._row(2025, ca_n)]

        with patch(DB_PATCH, return_value=rows):
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel?annee=2025")

        evol = resp.json()["evolution_pct"]
        assert evol == pytest.approx(expected_evol, rel=1e-2), \
            f"CA N-1={ca_n1}, CA N={ca_n}: évolution attendue={expected_evol}%, obtenue={evol}%"

    def test_evolution_nulle_stable(self):
        rows = [self._row(2024, 1_000_000), self._row(2025, 1_000_000)]

        with patch(DB_PATCH, return_value=rows):
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            resp = client.get("/api/dashboard/comparatif-annuel?annee=2025")

        assert resp.json()["evolution_pct"] == pytest.approx(0.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════════
# 7. Cohérence des alertes avec les KPIs
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceAlertes:
    """Les alertes déclenchées doivent correspondre aux KPIs calculés."""

    def test_alerte_dso_declenchee_quand_dso_eleve(self):
        """Si DSO calculé > 60j, le dashboard doit retourner une alerte DSO."""
        # DSO = (encours / CA_TTC) * 365
        # Pour DSO = 80j : encours = CA_TTC * 80/365
        ca_ttc = 1_200_000
        encours = ca_ttc * 80 / 365  # ~263 000

        ca_rows = [{"Annee": 2025, "Mois": 1, "CA_HT": 1_000_000,
                    "CA_TTC": ca_ttc, "Cout_Total": 700_000,
                    "Nb_Clients": 100, "Nb_Transactions": 400}]
        balance_rows = [{"Client": "CLI001", "Solde_Cloture": encours,
                         "0-30": encours * 0.4, "31-60": encours * 0.3,
                         "61-90": encours * 0.2, "91-120": encours * 0.07,
                         "+120": encours * 0.03}]

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp = client.get("/api/dashboard")

        data = resp.json()
        dso_kpi = data["kpis"]["dso"]["value"]
        alertes = data["alertes"]
        types_alertes = [a["type"] for a in alertes]

        assert dso_kpi > 60, f"DSO attendu > 60, obtenu: {dso_kpi}"
        assert "DSO" in types_alertes, \
            f"Alerte DSO attendue mais absente. Alertes: {types_alertes}"

    def test_pas_alerte_quand_kpis_normaux(self):
        """KPIs dans les normes → aucune alerte."""
        ca_ttc = 1_200_000
        encours = ca_ttc * 30 / 365  # DSO = 30j → pas d'alerte

        ca_rows = [{"Annee": 2025, "Mois": 1, "CA_HT": 1_000_000,
                    "CA_TTC": ca_ttc, "Cout_Total": 700_000,
                    "Nb_Clients": 100, "Nb_Transactions": 400}]
        balance_rows = [{"Client": "CLI001", "Solde_Cloture": encours,
                         "0-30": encours * 0.9, "31-60": encours * 0.05,
                         "61-90": encours * 0.05, "91-120": 0, "+120": 0}]

        with patch(DB_PATCH) as mock_db:
            from run import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            mock_db.side_effect = [ca_rows, [], balance_rows]
            resp = client.get("/api/dashboard")

        alertes = resp.json()["alertes"]
        assert alertes == [], f"Alertes inattendues: {alertes}"
