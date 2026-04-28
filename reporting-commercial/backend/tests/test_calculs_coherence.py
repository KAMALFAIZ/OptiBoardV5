"""
Tests de cohérence des calculs KPI - OptiBoard
Vérifie la correction mathématique de tous les indicateurs commerciaux.
"""
import pytest
from decimal import Decimal


# ─────────────────────────────────────────────
# Import du module à tester
# ─────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.services.calculs import (
    parse_number,
    safe_sum,
    calculer_marge_brute,
    calculer_dso,
    calculer_rotation_stock,
    calculer_couverture_stock,
    calculer_taux_recouvrement,
    calculer_evolution,
    analyser_balance_agee,
    identifier_alertes,
    formater_montant,
    get_periode_dates,
)


# ═══════════════════════════════════════════════════════════════════
# 1. parse_number — conversion robuste des valeurs
# ═══════════════════════════════════════════════════════════════════
class TestParseNumber:
    """Vérifie que parse_number gère tous les formats de valeur."""

    def test_none_retourne_zero(self):
        assert parse_number(None) == 0.0

    def test_entier(self):
        assert parse_number(42) == 42.0

    def test_float(self):
        assert parse_number(3.14) == 3.14

    def test_decimal(self):
        assert parse_number(Decimal("1234.56")) == pytest.approx(1234.56)

    def test_chaine_simple(self):
        assert parse_number("1234.56") == pytest.approx(1234.56)

    def test_format_francais_virgule(self):
        """Format MAD/EUR : virgule comme séparateur décimal."""
        assert parse_number("1 234,56") == pytest.approx(1234.56)

    def test_espaces_milliers(self):
        assert parse_number("2 047 733,00") == pytest.approx(2047733.0)

    def test_chaine_vide(self):
        assert parse_number("") == 0.0

    def test_tiret(self):
        assert parse_number("-") == 0.0

    def test_valeur_negative(self):
        assert parse_number("-500.75") == pytest.approx(-500.75)

    def test_valeur_zero_string(self):
        assert parse_number("0") == 0.0

    def test_chaine_invalide(self):
        assert parse_number("abc") == 0.0

    def test_nbsp(self):
        """Espace insécable (souvent dans copier-coller depuis Excel)."""
        assert parse_number("1\xa0000") == pytest.approx(1000.0)


# ═══════════════════════════════════════════════════════════════════
# 2. safe_sum — somme robuste sur listes de dicts
# ═══════════════════════════════════════════════════════════════════
class TestSafeSum:
    def test_liste_vide(self):
        assert safe_sum([], "ca") == 0.0

    def test_somme_simple(self):
        data = [{"ca": 100}, {"ca": 200}, {"ca": 300}]
        assert safe_sum(data, "ca") == pytest.approx(600.0)

    def test_avec_none(self):
        data = [{"ca": 100}, {"ca": None}, {"ca": 200}]
        assert safe_sum(data, "ca") == pytest.approx(300.0)

    def test_avec_valeurs_formatees(self):
        data = [{"ca": "1 000,50"}, {"ca": "2 000,50"}]
        assert safe_sum(data, "ca") == pytest.approx(3001.0)

    def test_cle_absente(self):
        data = [{"autre": 100}, {"autre": 200}]
        assert safe_sum(data, "ca") == 0.0

    def test_sans_cle_liste_scalaire(self):
        values = [10.0, 20.0, 30.0]
        assert safe_sum(values) == pytest.approx(60.0)


# ═══════════════════════════════════════════════════════════════════
# 3. calculer_marge_brute
# ═══════════════════════════════════════════════════════════════════
class TestCalculerMargeBrute:
    """Marge = CA - Coût ; Taux = Marge / CA × 100"""

    def test_cas_normal(self):
        result = calculer_marge_brute(ca=1_000_000, cout=700_000)
        assert result["marge_brute"] == pytest.approx(300_000)
        assert result["taux_marge"] == pytest.approx(30.0)

    def test_ca_zero_retourne_zero(self):
        result = calculer_marge_brute(ca=0, cout=0)
        assert result["marge_brute"] == 0
        assert result["taux_marge"] == 0

    def test_marge_negative(self):
        result = calculer_marge_brute(ca=500_000, cout=600_000)
        assert result["marge_brute"] == pytest.approx(-100_000)
        assert result["taux_marge"] < 0

    def test_marge_totale(self):
        """CA = coût → marge nulle."""
        result = calculer_marge_brute(ca=500_000, cout=500_000)
        assert result["marge_brute"] == pytest.approx(0)
        assert result["taux_marge"] == pytest.approx(0)

    def test_arrondi_deux_decimales(self):
        result = calculer_marge_brute(ca=3, cout=1)
        assert result["taux_marge"] == pytest.approx(66.67, abs=0.01)

    def test_coherence_taux(self):
        """taux_marge doit être cohérent avec marge_brute et CA."""
        ca = 850_000
        cout = 612_000
        result = calculer_marge_brute(ca, cout)
        expected_taux = (result["marge_brute"] / ca) * 100
        assert result["taux_marge"] == pytest.approx(expected_taux, rel=1e-4)


# ═══════════════════════════════════════════════════════════════════
# 4. calculer_dso
# ═══════════════════════════════════════════════════════════════════
class TestCalculerDSO:
    """DSO = (Encours / CA_TTC) × nb_jours"""

    def test_cas_normal_annuel(self):
        # Encours = 150 000, CA TTC = 1 200 000, 365 jours → ~45,6 j
        dso = calculer_dso(encours_clients=150_000, ca_ttc=1_200_000, nb_jours=365)
        expected = (150_000 / 1_200_000) * 365
        assert dso == pytest.approx(expected, rel=1e-3)

    def test_ca_zero_retourne_zero(self):
        assert calculer_dso(50_000, 0) == 0

    def test_encours_zero(self):
        assert calculer_dso(0, 500_000) == 0.0

    def test_dso_30_jours_coherent(self):
        """Si encours = CA mensuel → DSO ≈ 30 j."""
        ca_annuel = 1_200_000
        ca_mensuel = ca_annuel / 12
        dso = calculer_dso(ca_mensuel, ca_annuel)
        assert dso == pytest.approx(30.0, abs=1.0)

    def test_parametre_nb_jours_30(self):
        dso = calculer_dso(50_000, 600_000, nb_jours=30)
        expected = (50_000 / 600_000) * 30
        assert dso == pytest.approx(expected, rel=1e-3)


# ═══════════════════════════════════════════════════════════════════
# 5. calculer_rotation_stock
# ═══════════════════════════════════════════════════════════════════
class TestCalculerRotationStock:
    """Rotation = CA / Stock Moyen"""

    def test_cas_normal(self):
        rotation = calculer_rotation_stock(ca_annuel=1_200_000, stock_moyen=400_000)
        assert rotation == pytest.approx(3.0)

    def test_stock_zero(self):
        assert calculer_rotation_stock(1_200_000, 0) == 0

    def test_stock_superieur_ca(self):
        """Rotation < 1 → stock élevé par rapport au CA."""
        rotation = calculer_rotation_stock(ca_annuel=100_000, stock_moyen=200_000)
        assert rotation == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════════════
# 6. calculer_couverture_stock
# ═══════════════════════════════════════════════════════════════════
class TestCalculerCouvertureStock:
    """Couverture (jours) = (Stock / CA annuel) × 365"""

    def test_cas_normal(self):
        cov = calculer_couverture_stock(stock_actuel=200_000, ca_annuel=1_200_000)
        expected = (200_000 / 1_200_000) * 365
        assert cov == pytest.approx(expected, rel=1e-3)

    def test_ca_zero(self):
        assert calculer_couverture_stock(100_000, 0) == 0

    def test_coherence_avec_rotation(self):
        """Couverture × Rotation ≈ 365."""
        ca = 1_000_000
        stock = 300_000
        rotation = calculer_rotation_stock(ca, stock)
        couverture = calculer_couverture_stock(stock, ca)
        assert rotation * couverture == pytest.approx(365, abs=1.0)


# ═══════════════════════════════════════════════════════════════════
# 7. calculer_taux_recouvrement
# ═══════════════════════════════════════════════════════════════════
class TestCalculerTauxRecouvrement:
    def test_cas_normal(self):
        taux = calculer_taux_recouvrement(80_000, 100_000)
        assert taux == pytest.approx(80.0)

    def test_recouvrement_total(self):
        assert calculer_taux_recouvrement(100_000, 100_000) == pytest.approx(100.0)

    def test_montant_zero(self):
        assert calculer_taux_recouvrement(0, 100_000) == 0.0

    def test_denominateur_zero(self):
        assert calculer_taux_recouvrement(50_000, 0) == 0


# ═══════════════════════════════════════════════════════════════════
# 8. calculer_evolution
# ═══════════════════════════════════════════════════════════════════
class TestCalculerEvolution:
    """Évolution % = (actuelle - précédente) / précédente × 100"""

    def test_hausse(self):
        result = calculer_evolution(120_000, 100_000)
        assert result["evolution_pct"] == pytest.approx(20.0)
        assert result["tendance"] == "hausse"

    def test_baisse(self):
        result = calculer_evolution(80_000, 100_000)
        assert result["evolution_pct"] == pytest.approx(-20.0)
        assert result["tendance"] == "baisse"

    def test_stable(self):
        result = calculer_evolution(100_000, 100_000)
        assert result["evolution_pct"] == pytest.approx(0.0)
        assert result["tendance"] == "stable"

    def test_precedent_zero(self):
        result = calculer_evolution(100_000, 0)
        assert result["evolution_pct"] == 0
        assert result["tendance"] == "stable"

    def test_valeurs_rondes(self):
        """(1 500 000 - 1 200 000) / 1 200 000 = 25%"""
        result = calculer_evolution(1_500_000, 1_200_000)
        assert result["evolution_pct"] == pytest.approx(25.0)

    def test_arrondi(self):
        result = calculer_evolution(1, 3)
        expected = (1 - 3) / 3 * 100
        assert result["evolution_pct"] == pytest.approx(round(expected, 2), abs=0.01)


# ═══════════════════════════════════════════════════════════════════
# 9. analyser_balance_agee
# ═══════════════════════════════════════════════════════════════════
class TestAnalyserBalanceAgee:
    """Teste la décomposition de la balance âgée."""

    def _balance_row(self, solde, a30=0, a60=0, a90=0, a120=0, plus120=0):
        return {
            "Solde_Cloture": solde,
            "0-30": a30,
            "31-60": a60,
            "61-90": a90,
            "91-120": a120,
            "+120": plus120,
        }

    def test_liste_vide(self):
        result = analyser_balance_agee([])
        assert result["total_encours"] == 0
        assert result["nb_clients"] == 0

    def test_total_encours(self):
        data = [
            self._balance_row(10_000, a30=5000, a60=3000, a90=2000),
            self._balance_row(20_000, a30=10000, a60=10000),
        ]
        result = analyser_balance_agee(data)
        assert result["total_encours"] == pytest.approx(30_000)

    def test_creances_douteuses_plus_120(self):
        data = [self._balance_row(50_000, plus120=15_000)]
        result = analyser_balance_agee(data)
        assert result["creances_douteuses"] == pytest.approx(15_000)

    def test_taux_creances_douteuses(self):
        data = [self._balance_row(100_000, plus120=10_000)]
        result = analyser_balance_agee(data)
        assert result["taux_creances_douteuses"] == pytest.approx(10.0)

    def test_nb_clients(self):
        data = [
            self._balance_row(10_000),
            self._balance_row(20_000),
            self._balance_row(5_000),
        ]
        result = analyser_balance_agee(data)
        assert result["nb_clients"] == 3

    def test_coherence_repartition(self):
        """La somme des tranches doit être proche de Solde_Cloture (données bien saisies)."""
        data = [self._balance_row(30_000, a30=10_000, a60=10_000, a90=10_000)]
        result = analyser_balance_agee(data)
        somme_tranches = sum(result["repartition"].values())
        assert somme_tranches == pytest.approx(30_000)


# ═══════════════════════════════════════════════════════════════════
# 10. identifier_alertes
# ═══════════════════════════════════════════════════════════════════
class TestIdentifierAlertes:
    def test_aucune_alerte(self):
        kpis = {"dso": 30, "taux_creances_douteuses": 5, "rotation_stock": 4}
        alertes = identifier_alertes(kpis)
        assert alertes == []

    def test_alerte_dso_warning(self):
        kpis = {"dso": 75, "taux_creances_douteuses": 5}
        alertes = identifier_alertes(kpis)
        types = [a["type"] for a in alertes]
        assert "DSO" in types
        dso_alerte = next(a for a in alertes if a["type"] == "DSO")
        assert dso_alerte["niveau"] == "warning"

    def test_alerte_dso_critical(self):
        kpis = {"dso": 95, "taux_creances_douteuses": 5}
        alertes = identifier_alertes(kpis)
        dso_alerte = next(a for a in alertes if a["type"] == "DSO")
        assert dso_alerte["niveau"] == "critical"

    def test_alerte_creances(self):
        kpis = {"dso": 30, "taux_creances_douteuses": 12}
        alertes = identifier_alertes(kpis)
        types = [a["type"] for a in alertes]
        assert "Créances" in types

    def test_alerte_rotation_stock_faible(self):
        kpis = {"dso": 30, "taux_creances_douteuses": 5, "rotation_stock": 1}
        alertes = identifier_alertes(kpis)
        types = [a["type"] for a in alertes]
        assert "Stock" in types

    def test_seuils_personnalises(self):
        kpis = {"dso": 50, "taux_creances_douteuses": 5}
        seuils = {"dso_max": 40, "taux_creances_douteuses_max": 10}
        alertes = identifier_alertes(kpis, seuils)
        types = [a["type"] for a in alertes]
        assert "DSO" in types

    def test_alerte_contient_valeur(self):
        """L'alerte doit exposer la valeur incriminée pour affichage."""
        kpis = {"dso": 80}
        alertes = identifier_alertes(kpis)
        assert any(a.get("valeur") == 80 for a in alertes)


# ═══════════════════════════════════════════════════════════════════
# 11. formater_montant
# ═══════════════════════════════════════════════════════════════════
class TestFormaterMontant:
    def test_zero(self):
        assert formater_montant(0) == "0.00 MAD"

    def test_none(self):
        assert formater_montant(None) == "0.00 MAD"

    def test_devise_personnalisee(self):
        result = formater_montant(1000, "EUR")
        assert "EUR" in result

    def test_format_montant_positif(self):
        result = formater_montant(1_234_567.89)
        # Doit contenir la valeur numérique et la devise
        assert "MAD" in result
        assert "1" in result  # au moins un chiffre significatif


# ═══════════════════════════════════════════════════════════════════
# 12. get_periode_dates
# ═══════════════════════════════════════════════════════════════════
class TestGetPeriodeDates:
    """Vérifie la cohérence des plages de dates retournées."""

    def test_annee_courante_debut_janvier(self):
        from datetime import datetime
        debut, fin = get_periode_dates("annee_courante")
        annee = datetime.now().year
        assert debut.startswith(str(annee))
        assert debut.endswith("-01-01")

    def test_annee_courante_fin_avant_ou_egale_auj(self):
        from datetime import date
        _, fin = get_periode_dates("annee_courante")
        assert fin <= date.today().strftime("%Y-%m-%d")

    def test_annee_precedente_coherente(self):
        from datetime import datetime
        debut, fin = get_periode_dates("annee_precedente")
        annee_prec = datetime.now().year - 1
        assert debut.startswith(str(annee_prec))
        assert fin.startswith(str(annee_prec))

    def test_mois_courant_debut_premier_du_mois(self):
        debut, _ = get_periode_dates("mois_courant")
        assert debut.endswith("-01")

    def test_periode_inconnue_fallback(self):
        """Une période inconnue doit retourner l'année courante (fallback)."""
        from datetime import datetime
        debut, _ = get_periode_dates("periode_inconnue_xyz")
        assert debut.startswith(str(datetime.now().year))

    def test_debut_avant_fin(self):
        for periode in ["annee_courante", "annee_precedente", "mois_courant",
                        "trimestre_courant", "12_derniers_mois"]:
            debut, fin = get_periode_dates(periode)
            assert debut <= fin, f"Période {periode}: début > fin"


# ═══════════════════════════════════════════════════════════════════
# 13. Tests de cohérence croisée entre indicateurs
# ═══════════════════════════════════════════════════════════════════
class TestCoherenceCroisee:
    """Vérifie la cohérence mathématique entre plusieurs KPIs calculés ensemble."""

    def test_marge_plus_cout_egal_ca(self):
        ca, cout = 1_500_000, 900_000
        result = calculer_marge_brute(ca, cout)
        assert result["marge_brute"] + cout == pytest.approx(ca)

    def test_dso_encours_coherent_avec_ca(self):
        """Si DSO = 60 j → encours ≈ CA_TTC × 60/365."""
        ca_ttc = 1_200_000
        encours = ca_ttc * 60 / 365
        dso = calculer_dso(encours, ca_ttc)
        assert dso == pytest.approx(60.0, abs=1.0)

    def test_evolution_symetrie(self):
        """Hausse de 25% puis baisse de 20% ≈ valeur initiale."""
        initial = 1_000_000
        apres_hausse = initial * 1.25
        result = calculer_evolution(initial, apres_hausse)
        # -20%
        assert result["evolution_pct"] == pytest.approx(-20.0, abs=0.1)

    def test_alertes_coherentes_avec_kpis_calcules(self):
        """Les alertes détectées doivent correspondre aux calculs KPI."""
        encours = 200_000
        ca_ttc = 1_000_000
        creances = 30_000

        dso = calculer_dso(encours, ca_ttc)
        taux_creances = (creances / encours * 100) if encours > 0 else 0

        kpis = {"dso": dso, "taux_creances_douteuses": taux_creances}
        alertes = identifier_alertes(kpis)

        # DSO = 73 j → alerte warning
        assert dso > 60
        assert any(a["type"] == "DSO" for a in alertes)

    def test_balance_agee_coherence_taux(self):
        """taux_creances_douteuses = créances_douteuses / total_encours × 100."""
        data = [{"Solde_Cloture": 100_000, "0-30": 70_000, "31-60": 15_000,
                 "61-90": 5_000, "91-120": 5_000, "+120": 5_000}]
        result = analyser_balance_agee(data)
        expected_taux = result["creances_douteuses"] / result["total_encours"] * 100
        assert result["taux_creances_douteuses"] == pytest.approx(expected_taux, rel=1e-4)
