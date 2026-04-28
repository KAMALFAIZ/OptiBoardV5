"""
Tests Sécurité IA — Validation SQL - OptiBoard
Vérifie que le validateur SQL interdit toutes les requêtes destructives
et qu'il ne laisse passer que des SELECT en lecture seule.
"""
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.services.ai_sql_validator import validate_ai_sql, FORBIDDEN_KEYWORDS


# ═══════════════════════════════════════════════════════════════════
# 1. Requêtes valides — doivent passer
# ═══════════════════════════════════════════════════════════════════
class TestRequetesValides:
    """Ces requêtes légitimes doivent être acceptées."""

    def test_select_simple(self):
        sql = "SELECT * FROM DashBoard_CA"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True
        assert err == ""

    def test_select_avec_where(self):
        sql = "SELECT Client, CA_HT FROM DashBoard_CA WHERE Annee = 2025"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_avec_group_by(self):
        sql = "SELECT Gamme, SUM(CA_HT) as Total FROM DashBoard_CA GROUP BY Gamme"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_avec_join(self):
        sql = ("SELECT c.Client, SUM(b.Solde_Cloture) "
               "FROM DashBoard_CA c JOIN BalanceAgee b ON c.Client = b.Client "
               "GROUP BY c.Client")
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_avec_order_by(self):
        sql = "SELECT TOP 10 Client, CA_HT FROM DashBoard_CA ORDER BY CA_HT DESC"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_cte_simple(self):
        sql = ("WITH top_clients AS ("
               "SELECT Client, SUM(CA_HT) as CA FROM DashBoard_CA GROUP BY Client"
               ") SELECT * FROM top_clients ORDER BY CA DESC")
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_avec_sous_requete(self):
        sql = ("SELECT * FROM DashBoard_CA "
               "WHERE CA_HT > (SELECT AVG(CA_HT) FROM DashBoard_CA)")
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_case_when(self):
        sql = ("SELECT Client, "
               "CASE WHEN CA_HT > 100000 THEN 'Grand' ELSE 'Petit' END as Categorie "
               "FROM DashBoard_CA")
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_minuscules(self):
        """Les SELECT en minuscules doivent aussi passer."""
        sql = "select client, ca_ht from dashboard_ca"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True

    def test_select_avec_commentaire_sql_nettoye(self):
        """Les commentaires SQL doivent être supprimés avant validation."""
        sql = "SELECT * FROM DashBoard_CA -- afficher tout"
        ok, sanitized, err = validate_ai_sql(sql)
        assert ok is True


# ═══════════════════════════════════════════════════════════════════
# 2. Requêtes destructives — doivent être bloquées
# ═══════════════════════════════════════════════════════════════════
class TestRequetesDestructivesBloquees:
    """Toutes ces requêtes doivent être rejetées."""

    @pytest.mark.parametrize("sql,description", [
        ("DELETE FROM DashBoard_CA", "DELETE direct"),
        ("DELETE FROM DashBoard_CA WHERE 1=1", "DELETE avec WHERE"),
        ("DROP TABLE DashBoard_CA", "DROP TABLE"),
        ("DROP DATABASE OptiBoard_SaaS", "DROP DATABASE"),
        ("ALTER TABLE DashBoard_CA ADD col INT", "ALTER TABLE"),
        ("TRUNCATE TABLE DashBoard_CA", "TRUNCATE TABLE"),
        ("INSERT INTO DashBoard_CA VALUES (1,2,3)", "INSERT"),
        ("UPDATE DashBoard_CA SET CA_HT = 0", "UPDATE"),
        ("EXEC xp_cmdshell 'dir'", "EXEC xp_cmdshell"),
        ("EXECUTE sp_executesql N'DROP TABLE foo'", "EXECUTE sp_executesql"),
        ("CREATE TABLE evil (id INT)", "CREATE TABLE"),
        ("GRANT ALL ON DashBoard_CA TO hacker", "GRANT"),
        ("REVOKE SELECT ON DashBoard_CA FROM user1", "REVOKE"),
        ("MERGE INTO DashBoard_CA USING src ON 1=1 WHEN MATCHED THEN DELETE", "MERGE"),
        ("WAITFOR DELAY '0:0:5'", "WAITFOR"),
        ("SHUTDOWN WITH NOWAIT", "SHUTDOWN"),
    ])
    def test_requete_bloquee(self, sql, description):
        ok, _, err = validate_ai_sql(sql)
        assert ok is False, \
            f"SÉCURITÉ: La requête '{description}' aurait dû être bloquée mais a été acceptée!"
        assert err != "", f"'{description}': message d'erreur vide"


# ═══════════════════════════════════════════════════════════════════
# 3. Injection SQL via commentaires
# ═══════════════════════════════════════════════════════════════════
class TestInjectionSQLCommentaires:
    """Tentatives d'injection via commentaires SQL."""

    def test_injection_via_commentaire_double_tiret(self):
        """SELECT légitime suivi d'injection via --."""
        sql = "SELECT * FROM DashBoard_CA -- ; DROP TABLE DashBoard_CA"
        ok, sanitized, err = validate_ai_sql(sql)
        # Le DROP doit être nettoyé par suppression des commentaires
        if ok:
            assert "DROP" not in sanitized.upper()

    def test_injection_via_commentaire_bloc(self):
        """SELECT avec commentaire bloc cachant un DROP."""
        sql = "SELECT * FROM DashBoard_CA /* DROP TABLE evil */"
        ok, sanitized, err = validate_ai_sql(sql)
        if ok:
            assert "DROP" not in sanitized.upper()

    def test_select_avec_delete_dans_commentaire_accepte(self):
        """Un DELETE dans un commentaire ne doit pas bloquer un SELECT valide."""
        sql = "SELECT * FROM DashBoard_CA -- DELETE est interdit"
        # Après nettoyage des commentaires, il ne reste que le SELECT → doit passer
        ok, _, err = validate_ai_sql(sql)
        assert ok is True, f"Un SELECT valide avec DELETE en commentaire a été bloqué: {err}"


# ═══════════════════════════════════════════════════════════════════
# 4. Requêtes multiples (;)
# ═══════════════════════════════════════════════════════════════════
class TestRequetesMultiples:
    """Le point-virgule permettant d'enchaîner des requêtes doit être bloqué."""

    def test_deux_selects_bloques(self):
        sql = "SELECT * FROM DashBoard_CA; SELECT * FROM BalanceAgee"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False
        assert ";" in err or "multiples" in err.lower() or "interdit" in err.lower()

    def test_select_puis_delete_bloques(self):
        sql = "SELECT * FROM DashBoard_CA; DELETE FROM DashBoard_CA"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False


# ═══════════════════════════════════════════════════════════════════
# 5. Ajout automatique de TOP N
# ═══════════════════════════════════════════════════════════════════
class TestAjoutTopN:
    """Le validateur doit ajouter TOP N si absent pour limiter les résultats."""

    def test_top_ajoute_si_absent(self):
        sql = "SELECT * FROM DashBoard_CA"
        ok, sanitized, _ = validate_ai_sql(sql, max_rows=500)
        assert ok is True
        assert "TOP" in sanitized.upper()

    def test_top_500_par_defaut(self):
        sql = "SELECT Client, CA_HT FROM DashBoard_CA"
        _, sanitized, _ = validate_ai_sql(sql)
        assert "500" in sanitized

    def test_top_n_personnalise(self):
        sql = "SELECT * FROM DashBoard_CA"
        _, sanitized, _ = validate_ai_sql(sql, max_rows=100)
        assert "100" in sanitized

    def test_top_non_double_si_deja_present(self):
        sql = "SELECT TOP 10 Client FROM DashBoard_CA"
        ok, sanitized, _ = validate_ai_sql(sql)
        assert ok is True
        # Ne doit pas insérer un 2ème TOP
        assert sanitized.upper().count("TOP") == 1

    def test_cte_top_ajoute_dans_select_final(self):
        """Pour un CTE, TOP doit être ajouté dans le SELECT final, pas dans le CTE."""
        sql = ("WITH cte AS (SELECT Client, SUM(CA_HT) as CA FROM DashBoard_CA GROUP BY Client) "
               "SELECT Client, CA FROM cte ORDER BY CA DESC")
        ok, sanitized, _ = validate_ai_sql(sql)
        assert ok is True
        assert "TOP" in sanitized.upper()


# ═══════════════════════════════════════════════════════════════════
# 6. Requête vide ou invalide
# ═══════════════════════════════════════════════════════════════════
class TestRequetesVidesinvalides:
    def test_vide_bloquee(self):
        ok, _, err = validate_ai_sql("")
        assert ok is False
        assert err != ""

    def test_espaces_seuls_bloques(self):
        ok, _, err = validate_ai_sql("   ")
        assert ok is False

    def test_none_bloquee(self):
        ok, _, err = validate_ai_sql(None)
        assert ok is False

    def test_requete_trop_longue_bloquee(self):
        # "SELECT " (7) + "alias_col_," * 900 (>10000) + " 1 FROM t"
        sql = "SELECT " + "alias_col_," * 1000 + " 1 FROM t"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False
        assert "long" in err.lower() or "10000" in err


# ═══════════════════════════════════════════════════════════════════
# 7. Procédures système
# ═══════════════════════════════════════════════════════════════════
class TestProceduresSysteme:
    @pytest.mark.parametrize("proc", [
        "xp_cmdshell", "xp_logininfo", "xp_enumgroups",
        "sp_executesql", "sp_configure",
    ])
    def test_procedure_systeme_bloquee(self, proc):
        sql = f"SELECT * FROM sys.tables; EXEC {proc} 'test'"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False, f"Procédure système {proc} aurait dû être bloquée"

    def test_openrowset_bloquee(self):
        sql = "SELECT * FROM OPENROWSET('SQLNCLI', 'server=evil;', 'SELECT 1')"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False

    def test_opendatasource_bloquee(self):
        sql = "SELECT * FROM OPENDATASOURCE('SQLNCLI', 'Data Source=evil')..table"
        ok, _, err = validate_ai_sql(sql)
        assert ok is False


# ═══════════════════════════════════════════════════════════════════
# 8. Liste des mots-clés interdits — couverture complète
# ═══════════════════════════════════════════════════════════════════
class TestCouvertureMosClesInterdits:
    """Vérifie que FORBIDDEN_KEYWORDS contient tous les mots-clés critiques."""

    MOTS_CLES_CRITIQUES = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "EXEC", "EXECUTE", "MERGE", "GRANT", "REVOKE",
    ]

    def test_tous_mots_cles_critiques_presents(self):
        for mot in self.MOTS_CLES_CRITIQUES:
            assert mot in FORBIDDEN_KEYWORDS, \
                f"Mot-clé critique manquant dans FORBIDDEN_KEYWORDS: {mot}"

    def test_waitfor_present(self):
        """WAITFOR permet des attentes (DoS) → doit être interdit."""
        assert "WAITFOR" in FORBIDDEN_KEYWORDS

    def test_bulk_present(self):
        """BULK INSERT → injection de données en masse."""
        assert "BULK" in FORBIDDEN_KEYWORDS
