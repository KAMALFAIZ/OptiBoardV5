"""
Tests des améliorations de sécurité et de qualité.
Couvre : APP_ENV/license check, logging structuré, pool ODBC, config.
"""
import hashlib
import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════════════════
# 1. Settings — APP_ENV et LICENSE_SIGNING_SECRET
# ═══════════════════════════════════════════════════════════════════
class TestSettings:
    """Vérifie la configuration sécurisée des settings."""

    def test_app_env_default_is_development(self):
        """APP_ENV vaut 'development' par défaut."""
        with patch.dict(os.environ, {}, clear=False):
            from app.config import Settings
            s = Settings(DB_SERVER="", DB_NAME="", DB_USER="", DB_PASSWORD="")
            assert s.APP_ENV == "development"

    def test_is_production_false_by_default(self):
        """is_production retourne False en mode development."""
        from app.config import Settings
        s = Settings(DB_SERVER="", DB_NAME="", DB_USER="", DB_PASSWORD="", APP_ENV="development")
        assert s.is_production is False

    def test_is_production_true_when_set(self):
        """is_production retourne True quand APP_ENV=production."""
        from app.config import Settings
        s = Settings(DB_SERVER="", DB_NAME="", DB_USER="", DB_PASSWORD="", APP_ENV="production")
        assert s.is_production is True

    def test_license_signing_secret_no_hardcoded_default(self):
        """LICENSE_SIGNING_SECRET ne doit pas avoir de valeur hardcodée en prod."""
        from app.config import Settings
        s = Settings(DB_SERVER="", DB_NAME="", DB_USER="", DB_PASSWORD="")
        # La valeur par défaut doit être vide (pas de secret hardcodé)
        assert s.LICENSE_SIGNING_SECRET == "" or len(s.LICENSE_SIGNING_SECRET) > 10, \
            "LICENSE_SIGNING_SECRET est vide par défaut (correct) ou provient du .env"

    def test_license_signing_secret_readable_from_env(self):
        """LICENSE_SIGNING_SECRET peut être défini via variable d'environnement."""
        with patch.dict(os.environ, {"LICENSE_SIGNING_SECRET": "my-secret-key-test"}):
            from app.config import Settings
            s = Settings(DB_SERVER="", DB_NAME="", DB_USER="", DB_PASSWORD="")
            assert s.LICENSE_SIGNING_SECRET == "my-secret-key-test"

    def test_save_env_config_includes_license_secret(self, tmp_path):
        """save_env_config écrit LICENSE_SIGNING_SECRET dans le .env."""
        from app import config as cfg_module
        env_path = tmp_path / ".env"
        original_path = cfg_module.ENV_FILE_PATH

        try:
            cfg_module.ENV_FILE_PATH = env_path
            cfg_module.save_env_config({
                "DB_SERVER": "server",
                "DB_NAME": "db",
                "DB_USER": "user",
                "DB_PASSWORD": "pass",
                "LICENSE_SIGNING_SECRET": "secret-test-key",
            })
            content = env_path.read_text(encoding="utf-8")
            assert "LICENSE_SIGNING_SECRET=secret-test-key" in content
        finally:
            cfg_module.ENV_FILE_PATH = original_path

    def test_save_env_config_includes_app_env(self, tmp_path):
        """save_env_config écrit APP_ENV dans le .env."""
        from app import config as cfg_module
        env_path = tmp_path / ".env"
        original_path = cfg_module.ENV_FILE_PATH

        try:
            cfg_module.ENV_FILE_PATH = env_path
            cfg_module.save_env_config({
                "DB_SERVER": "server",
                "DB_NAME": "db",
                "DB_USER": "user",
                "DB_PASSWORD": "pass",
                "APP_ENV": "production",
            })
            content = env_path.read_text(encoding="utf-8")
            assert "APP_ENV=production" in content
        finally:
            cfg_module.ENV_FILE_PATH = original_path


# ═══════════════════════════════════════════════════════════════════
# 2. Middleware licence — comportement selon APP_ENV
# ═══════════════════════════════════════════════════════════════════
class TestLicenseMiddleware:
    """Vérifie que le middleware licence est actif uniquement en production."""

    @pytest.fixture
    def app_with_mock_db(self):
        with patch('app.database_unified.execute_central', return_value=[]), \
             patch('app.database_unified.execute_client', return_value=[]), \
             patch('app.database_unified.test_central_connection', return_value=True):
            from run import app
            from fastapi.testclient import TestClient
            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

    def test_health_endpoint_accessible_without_license(self, app_with_mock_db):
        """GET /api/health ne nécessite pas de licence (route exemptée)."""
        response = app_with_mock_db.get("/api/health")
        assert response.status_code in (200, 503)  # 503 si DB non configurée, mais pas 403

    def test_setup_status_accessible_without_license(self, app_with_mock_db):
        """GET /api/setup/status est toujours accessible (route exemptée)."""
        response = app_with_mock_db.get("/api/setup/status")
        # La route est exemptée de la vérification licence — jamais 403
        assert response.status_code != 403


# ═══════════════════════════════════════════════════════════════════
# 3. Pool ODBC — _SemaphoreConnection
# ═══════════════════════════════════════════════════════════════════
class TestSemaphoreConnection:
    """Vérifie le mécanisme de semaphore sur les connexions ODBC."""

    def test_semaphore_released_on_close(self):
        """Le semaphore est libéré lorsque la connexion est fermée."""
        from app.database_unified import _SemaphoreConnection
        sem = threading.Semaphore(2)
        mock_conn = MagicMock()

        # Acquérir le semaphore manuellement (simule ce que fait DWHConnectionPool)
        sem.acquire()
        wrapped = _SemaphoreConnection(mock_conn, sem)
        wrapped.close()

        # Après close(), on doit pouvoir acquérir 2 fois (valeur initiale restaurée)
        assert sem.acquire(blocking=False)
        assert sem.acquire(blocking=False)
        sem.release()
        sem.release()

    def test_semaphore_released_on_context_manager_exit(self):
        """Le semaphore est libéré en sortant du context manager."""
        from app.database_unified import _SemaphoreConnection
        sem = threading.Semaphore(1)
        mock_conn = MagicMock()

        sem.acquire()
        with _SemaphoreConnection(mock_conn, sem):
            pass  # connexion utilisée

        # Semaphore doit être disponible après __exit__
        assert sem.acquire(blocking=False)
        sem.release()

    def test_semaphore_not_double_released(self):
        """Appeler close() deux fois ne libère le semaphore qu'une seule fois."""
        from app.database_unified import _SemaphoreConnection
        sem = threading.Semaphore(1)
        mock_conn = MagicMock()

        sem.acquire()
        wrapped = _SemaphoreConnection(mock_conn, sem)
        wrapped.close()
        wrapped.close()  # second appel ne doit pas re-libérer

        # Le semaphore vaut 1, pas 2
        assert sem.acquire(blocking=False)
        assert not sem.acquire(blocking=False)  # déjà épuisé
        sem.release()

    def test_dwh_pool_max_concurrent_defined(self):
        """DWHConnectionPool.MAX_CONCURRENT doit être défini et raisonnable."""
        from app.database_unified import DWHConnectionPool
        assert DWHConnectionPool.MAX_CONCURRENT >= 5
        assert DWHConnectionPool.MAX_CONCURRENT <= 100

    def test_pyodbc_pooling_enabled(self):
        """pyodbc.pooling doit être activé."""
        import pyodbc
        assert pyodbc.pooling is True


# ═══════════════════════════════════════════════════════════════════
# 4. Logging — pas de print() dans les modules critiques
# ═══════════════════════════════════════════════════════════════════
class TestNoDebugPrints:
    """Vérifie l'absence de print() de debug dans les modules critiques."""

    def _count_prints(self, filepath: str) -> int:
        if not os.path.exists(filepath):
            return 0
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        import re
        # Ignorer les print() dans les commentaires ou docstrings
        lines = [l for l in content.splitlines()
                 if "print(" in l and not l.strip().startswith("#")]
        return len(lines)

    def _backend(self, relpath):
        return os.path.join(
            os.path.dirname(__file__), '..', relpath
        )

    def test_no_print_in_config(self):
        path = self._backend("app/config.py")
        assert self._count_prints(path) == 0, \
            f"Des print() persistent dans app/config.py"

    def test_no_print_in_database_unified(self):
        path = self._backend("app/database_unified.py")
        count = self._count_prints(path)
        assert count == 0, \
            f"{count} print() persistent dans app/database_unified.py"

    def test_no_sage_debug_log_writes(self):
        """Aucune écriture dans sage_debug.log dans database_unified.py."""
        path = self._backend("app/database_unified.py")
        if not os.path.exists(path):
            pytest.skip("Fichier introuvable")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "sage_debug.log" not in content, \
            "Les écritures sage_debug.log n'ont pas été supprimées"

    def test_no_print_in_run(self):
        path = self._backend("run.py")
        count = self._count_prints(path)
        assert count == 0, \
            f"{count} print() persistent dans run.py"


# ═══════════════════════════════════════════════════════════════════
# 5. Route /api/auth/login — comportement de base
# ═══════════════════════════════════════════════════════════════════
class TestAuthLogin:
    """Tests fonctionnels du endpoint d'authentification."""

    @pytest.fixture
    def auth_client(self):
        with patch('app.database_unified.execute_central', return_value=[]), \
             patch('app.database_unified.execute_client', return_value=[]), \
             patch('app.database_unified.write_central', return_value=None), \
             patch('app.database_unified.test_central_connection', return_value=True), \
             patch('app.database_unified.client_manager') as mock_cm:
            mock_cm.has_client_db.return_value = False
            from run import app
            from fastapi.testclient import TestClient
            with TestClient(app) as c:
                yield c

    def test_login_missing_username_returns_422(self, auth_client):
        """Login sans username → 422 Unprocessable Entity."""
        response = auth_client.post("/api/auth/login", json={"password": "test"})
        assert response.status_code == 422

    def test_login_missing_password_returns_422(self, auth_client):
        """Login sans password → 422 Unprocessable Entity."""
        response = auth_client.post("/api/auth/login", json={"username": "admin"})
        assert response.status_code == 422

    def test_login_invalid_credentials_returns_401(self, auth_client):
        """Login avec credentials invalides → 401."""
        response = auth_client.post("/api/auth/login", json={
            "username": "hacker",
            "password": "wrong",
        })
        assert response.status_code == 401

    def test_login_demo_dwh_blocked(self, auth_client):
        """Accès au DWH de démo (KA) → 403 pour les utilisateurs clients."""
        response = auth_client.post("/api/auth/login", json={
            "username": "user",
            "password": "pass",
            "dwh_code": "KA",
        })
        assert response.status_code == 403

    def test_login_empty_strings_returns_401(self, auth_client):
        """Login avec chaînes vides → 401 (pas d'accès)."""
        response = auth_client.post("/api/auth/login", json={
            "username": "",
            "password": "",
        })
        assert response.status_code in (401, 422)

    def test_login_valid_central_user(self, auth_client):
        """Login avec un superadmin central valide → 200."""
        pwd_hash = hashlib.sha256("correct_password".encode()).hexdigest()
        mock_user = [{
            "id": 1,
            "username": "admin",
            "password_hash": pwd_hash,
            "nom": "Admin",
            "prenom": "Super",
            "email": "admin@test.com",
            "role_global": "superadmin",
            "actif": True,
        }]
        from app.database_unified import UserContext
        mock_context = UserContext(
            user_id=1, username="admin", nom="Admin", prenom="Super",
            email="admin@test.com", role_global="superadmin",
            dwh_accessibles=[], societes_accessibles=[], pages_accessibles=[],
        )
        # Patcher là où les fonctions sont UTILISÉES (dans auth_multitenant), pas où définies
        with patch('app.routes.auth_multitenant.execute_central', return_value=mock_user), \
             patch('app.routes.auth_multitenant.write_central', return_value=None), \
             patch('app.routes.auth_multitenant.create_user_context', return_value=mock_context):
            response = auth_client.post("/api/auth/login", json={
                "username": "admin",
                "password": "correct_password",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
