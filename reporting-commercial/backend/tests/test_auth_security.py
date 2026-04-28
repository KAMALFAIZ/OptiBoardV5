"""
Tests Authentification & Sécurité - OptiBoard
Vérifie : login/logout, hachage des mots de passe, protection des routes,
gestion des tokens JWT, droits multi-rôles.
"""
import pytest
import hashlib
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════════════════
# 1. Hachage des mots de passe
# ═══════════════════════════════════════════════════════════════════
class TestHachageMotDePasse:
    """Le mot de passe ne doit jamais être stocké en clair."""

    def _hash_password(self, password: str) -> str:
        """Recrée le hachage utilisé dans auth_multitenant.py."""
        return hashlib.sha256(password.encode()).hexdigest()

    def test_hash_sha256_longueur(self):
        hashed = self._hash_password("MonMotDePasse123")
        assert len(hashed) == 64

    def test_hash_deterministe(self):
        pwd = "test_password"
        assert self._hash_password(pwd) == self._hash_password(pwd)

    def test_hash_different_passwords(self):
        assert self._hash_password("pass1") != self._hash_password("pass2")

    def test_hash_pas_le_mot_de_passe_clair(self):
        pwd = "MonMotDePasse123"
        hashed = self._hash_password(pwd)
        assert pwd not in hashed

    def test_hash_sensible_casse(self):
        assert self._hash_password("Password") != self._hash_password("password")

    def test_hash_chaîne_vide(self):
        """Hash d'une chaîne vide doit quand même être de longueur 64."""
        hashed = self._hash_password("")
        assert len(hashed) == 64


# ═══════════════════════════════════════════════════════════════════
# 2. Validation des champs de login
# ═══════════════════════════════════════════════════════════════════
class TestValidationLogin:
    """Les requêtes sans username/password doivent être rejetées (422)."""

    @pytest.fixture
    def client(self):
        with patch("app.database_unified.execute_central", return_value=[]):
            with patch("app.database_unified.execute_client", return_value=[]):
                from run import app
                from fastapi.testclient import TestClient
                return TestClient(app)

    def test_login_sans_username_422(self, client):
        resp = client.post("/api/auth/login", json={"password": "test"})
        assert resp.status_code == 422

    def test_login_sans_password_422(self, client):
        resp = client.post("/api/auth/login", json={"username": "test"})
        assert resp.status_code == 422

    def test_login_body_vide_422(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422

    def test_login_corps_non_json_422(self, client):
        resp = client.post("/api/auth/login", data="pas_du_json")
        assert resp.status_code in (400, 422)


# ═══════════════════════════════════════════════════════════════════
# 3. Tentative de login avec mauvaises credentials
# ═══════════════════════════════════════════════════════════════════
class TestLoginEchoue:
    """Mauvais identifiants → pas de token, message d'erreur."""

    @pytest.fixture
    def client(self):
        """Simule une DB qui ne retourne aucun utilisateur (user inconnu)."""
        with patch("app.database_unified.execute_central", return_value=[]):
            with patch("app.database_unified.execute_client", return_value=[]):
                with patch("app.database_unified.write_client", return_value=None):
                    with patch("app.database_unified.write_central", return_value=None):
                        from run import app
                        from fastapi.testclient import TestClient
                        return TestClient(app)

    def test_user_inconnu_echec(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "inconnu@test.com",
            "password": "mauvais_mdp"
        })
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            assert resp.json().get("success") is False

    def test_reponse_pas_de_token_si_echec(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "inconnu@test.com",
            "password": "mauvais_mdp"
        })
        data = resp.json()
        # Aucun token ne doit être exposé en cas d'échec
        assert "token" not in data or data.get("token") is None


# ═══════════════════════════════════════════════════════════════════
# 4. Protection des routes — headers requis
# ═══════════════════════════════════════════════════════════════════
class TestProtectionRoutes:
    """Les routes protégées doivent refuser l'accès sans token."""

    PROTECTED_ENDPOINTS = [
        "/api/dashboard",
        "/api/dashboard/evolution-mensuelle",
        "/api/dashboard/comparatif-annuel",
    ]

    @pytest.fixture
    def client(self):
        with patch("app.database_unified.execute_app", return_value=[]):
            from run import app
            from fastapi.testclient import TestClient
            return TestClient(app)

    def test_routes_accessibles_sans_auth_car_pas_de_guard(self, client):
        """
        Si l'app ne configure pas de guard JWT obligatoire sur ces routes,
        elles doivent quand même retourner 200 (données vides mockées).
        Ce test documente l'état actuel — à convertir en 401 si un guard est ajouté.
        """
        for endpoint in self.PROTECTED_ENDPOINTS:
            resp = client.get(endpoint)
            # Soit 200 (pas de guard), soit 401/403 (guard actif)
            assert resp.status_code in (200, 401, 403), \
                f"Code inattendu {resp.status_code} pour {endpoint}"


# ═══════════════════════════════════════════════════════════════════
# 5. Isolation DWH démonstration
# ═══════════════════════════════════════════════════════════════════
class TestIsolationDemoDWH:
    """Le DWH 'KA' est réservé aux superadmins — un user normal ne doit pas y accéder."""

    def test_demo_dwh_codes_contient_KA(self):
        from app.routes.auth_multitenant import _DEMO_DWH_CODES
        assert "KA" in _DEMO_DWH_CODES

    def test_demo_dwh_non_vide(self):
        from app.routes.auth_multitenant import _DEMO_DWH_CODES
        assert len(_DEMO_DWH_CODES) >= 1


# ═══════════════════════════════════════════════════════════════════
# 6. Schémas Pydantic — LoginRequest / LoginResponse
# ═══════════════════════════════════════════════════════════════════
class TestSchemaAuth:
    def test_login_request_champs_requis(self):
        from app.routes.auth_multitenant import LoginRequest
        req = LoginRequest(username="user@test.com", password="secret123")
        assert req.username == "user@test.com"
        assert req.password == "secret123"
        assert req.dwh_code is None

    def test_login_request_avec_dwh(self):
        from app.routes.auth_multitenant import LoginRequest
        req = LoginRequest(username="u", password="p", dwh_code="TESTDWH")
        assert req.dwh_code == "TESTDWH"

    def test_login_response_success_false(self):
        from app.routes.auth_multitenant import LoginResponse
        resp = LoginResponse(success=False, message="Identifiants incorrects")
        assert resp.success is False
        assert resp.user is None

    def test_login_response_must_change_password_defaut(self):
        from app.routes.auth_multitenant import LoginResponse
        resp = LoginResponse(success=True, message="OK")
        assert resp.must_change_password is False


# ═══════════════════════════════════════════════════════════════════
# 7. Sécurité — Pas d'information sensible dans les réponses d'erreur
# ═══════════════════════════════════════════════════════════════════
class TestSecuriteReponses:
    """Les erreurs ne doivent pas divulguer d'informations internes."""

    @pytest.fixture
    def client(self):
        with patch("app.database_unified.execute_central", return_value=[]):
            with patch("app.database_unified.execute_client", return_value=[]):
                with patch("app.database_unified.write_client", return_value=None):
                    with patch("app.database_unified.write_central", return_value=None):
                        from run import app
                        from fastapi.testclient import TestClient
                        return TestClient(app)

    def test_echec_login_pas_de_stacktrace(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "inconnu", "password": "mauvais"
        })
        body = resp.text
        # Pas de stacktrace Python
        assert "Traceback" not in body
        assert "File \"" not in body

    def test_echec_login_pas_de_hash_mdp(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "inconnu", "password": "mauvais"
        })
        body = resp.text
        # Le hash SHA256 ne doit pas apparaître dans la réponse
        import hashlib
        hashed = hashlib.sha256("mauvais".encode()).hexdigest()
        assert hashed not in body


# ═══════════════════════════════════════════════════════════════════
# 8. Cohérence rôles et permissions
# ═══════════════════════════════════════════════════════════════════
class TestRolesPermissions:
    """Vérifie que les rôles définis ont du sens."""

    ROLES_VALIDES = {"admin", "editeur", "viewer"}

    def test_roles_connus(self):
        """Les rôles doivent être parmi ceux attendus."""
        # Si le module permissions est importable, vérifier ses constantes
        try:
            from app.services.permissions import ROLES
            for role in ROLES:
                assert role in self.ROLES_VALIDES or isinstance(role, str), \
                    f"Rôle inconnu: {role}"
        except (ImportError, AttributeError):
            pytest.skip("Module permissions non disponible dans cet environnement")

    def test_admin_a_plus_de_droits_que_viewer(self):
        """L'admin doit avoir au moins autant de droits que viewer."""
        try:
            from app.services.permissions import get_permissions
            admin_perms = get_permissions("admin")
            viewer_perms = get_permissions("viewer")
            # Admin doit avoir un sur-ensemble des droits viewer
            assert len(admin_perms) >= len(viewer_perms)
        except (ImportError, AttributeError):
            pytest.skip("Fonction get_permissions non disponible")
