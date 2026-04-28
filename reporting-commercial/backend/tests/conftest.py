"""
Configuration pytest pour les tests backend OptiBoard.
Fournit des fixtures communes et des helpers de mock pour toute la suite de tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ─────────────────────────────────────────────
# Constantes de test
# ─────────────────────────────────────────────
TEST_DWH_CODE = "TEST_DWH"
TEST_USER_ID = 999
TEST_SOCIETE = "TEST_SOC"
ANNEE_TEST = 2025


# ─────────────────────────────────────────────
# Fixtures de connexion DB (mock)
# ─────────────────────────────────────────────
@pytest.fixture
def mock_db_connection():
    """Mock de la connexion base de données (legacy)."""
    with patch('app.database.get_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_conn, mock_cursor


@pytest.fixture
def mock_execute_query():
    """Mock de execute_query (legacy routes ETL)."""
    with patch('app.database.execute_query') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_execute_app():
    """Mock de la fonction execute_app (database_unified) — utilisée par dashboard, ventes, etc."""
    with patch('app.database_unified.execute_app') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_execute_central():
    """Mock de execute_central (base centrale OptiBoard_SaaS)."""
    with patch('app.database_unified.execute_central') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_execute_client():
    """Mock de execute_client (base client OptiBoard_XXX)."""
    with patch('app.database_unified.execute_client') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_all_db():
    """Mock de toutes les fonctions DB en une seule fixture."""
    with patch('app.database_unified.execute_app', return_value=[]) as m_app, \
         patch('app.database_unified.execute_central', return_value=[]) as m_central, \
         patch('app.database_unified.execute_client', return_value=[]) as m_client, \
         patch('app.database_unified.write_central', return_value=None) as m_wc, \
         patch('app.database_unified.write_client', return_value=None) as m_wcl:
        yield {
            'execute_app': m_app,
            'execute_central': m_central,
            'execute_client': m_client,
            'write_central': m_wc,
            'write_client': m_wcl,
        }


# ─────────────────────────────────────────────
# Fixtures TestClient
# ─────────────────────────────────────────────
@pytest.fixture
def client(mock_execute_query):
    """Client de test FastAPI (pour les routes ETL legacy)."""
    from run import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_client(mock_all_db):
    """Client de test FastAPI avec tous les mocks DB actifs."""
    from run import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_client_with_headers(mock_all_db):
    """Client de test avec headers DWH et User préconfigurés."""
    from run import app
    with TestClient(app, headers={
        "X-DWH-Code": TEST_DWH_CODE,
        "X-User-Id": str(TEST_USER_ID),
    }) as c:
        yield c


# ─────────────────────────────────────────────
# Factories de données de test
# ─────────────────────────────────────────────
@pytest.fixture
def ca_row_factory():
    """Fabrique des lignes de CA mensuelles simulées."""
    def _make(annee=ANNEE_TEST, mois=1, ca_ht=100_000,
              ca_ttc=120_000, cout=70_000, nb_clients=50, nb_transactions=200):
        return {
            "Annee": annee,
            "Mois": mois,
            "CA_HT": ca_ht,
            "CA_TTC": ca_ttc,
            "Cout_Total": cout,
            "Nb_Clients": nb_clients,
            "Nb_Transactions": nb_transactions,
        }
    return _make


@pytest.fixture
def ca_rows_annuels(ca_row_factory):
    """12 mois de CA simulés pour une année complète."""
    return [
        ca_row_factory(mois=m, ca_ht=100_000 + m * 10_000, ca_ttc=120_000 + m * 12_000)
        for m in range(1, 13)
    ]


@pytest.fixture
def balance_row_factory():
    """Fabrique des lignes de balance âgée simulées."""
    def _make(client="CLI001", solde=50_000, a30=20_000, a60=15_000,
              a90=10_000, a120=3_000, plus120=2_000):
        return {
            "Client": client,
            "Solde_Cloture": solde,
            "0-30": a30,
            "31-60": a60,
            "61-90": a90,
            "91-120": a120,
            "+120": plus120,
        }
    return _make


@pytest.fixture
def balance_rows_multi(balance_row_factory):
    """5 clients avec des balances variées."""
    return [
        balance_row_factory(f"CLI{i:03d}", solde=20_000 + i * 5_000,
                            a30=10_000 + i * 2_000, a60=5_000,
                            plus120=1_000 * i)
        for i in range(1, 6)
    ]


# ─────────────────────────────────────────────
# Données ETL (legacy)
# ─────────────────────────────────────────────
@pytest.fixture
def sample_agent_data():
    """Données d'exemple pour un agent ETL."""
    return {
        "agent_id": "12345678-1234-1234-1234-123456789012",
        "dwh_code": TEST_DWH_CODE,
        "name": "Agent Test",
        "description": "Agent de test",
        "status": "active",
        "hostname": "test-host",
        "ip_address": "192.168.1.100",
        "agent_version": "1.0.0",
        "last_heartbeat": "2024-01-15T10:00:00",
        "last_sync": "2024-01-15T09:55:00",
        "sync_interval_seconds": 300,
        "heartbeat_interval_seconds": 30,
        "is_active": True,
        "total_syncs": 100,
        "total_rows_synced": 50_000,
        "consecutive_failures": 0,
        "tables_count": 5,
    }


@pytest.fixture
def sample_table_config():
    """Configuration de table ETL d'exemple."""
    return {
        "table_name": "Collaborateurs",
        "source_query": "SELECT * FROM F_COLLABORATEUR",
        "target_table": "Collaborateurs",
        "societe_code": "BIJOU",
        "primary_key_columns": ["Societe", "cbMarq"],
        "sync_type": "incremental",
        "timestamp_column": "cbModification",
        "priority": "normal",
        "is_enabled": True,
    }


@pytest.fixture
def sample_sync_log():
    """Log de synchronisation ETL d'exemple."""
    return {
        "id": 1,
        "agent_id": "12345678-1234-1234-1234-123456789012",
        "table_name": "Collaborateurs",
        "societe_code": "BIJOU",
        "started_at": "2024-01-15T10:00:00",
        "completed_at": "2024-01-15T10:00:05",
        "duration_seconds": 5.0,
        "status": "success",
        "rows_extracted": 100,
        "rows_inserted": 50,
        "rows_updated": 50,
        "rows_failed": 0,
        "error_message": None,
    }


# ─────────────────────────────────────────────
# Helpers réutilisables
# ─────────────────────────────────────────────
@pytest.fixture
def assert_base_response():
    """Helper pour vérifier la structure BaseResponse."""
    def _assert(response, expected_status=200):
        assert response.status_code == expected_status, \
            f"Code HTTP inattendu: {response.status_code} (attendu: {expected_status})\n{response.text}"
        data = response.json()
        assert "success" in data, "Champ 'success' absent de la réponse"
        return data
    return _assert


@pytest.fixture
def assert_kpis_structure():
    """Helper pour vérifier la structure des KPIs du dashboard."""
    def _assert(kpis):
        expected_keys = [
            "ca_ht", "marge_brute", "dso",
            "encours_clients", "nb_clients_actifs", "creances_douteuses"
        ]
        for key in expected_keys:
            assert key in kpis, f"KPI manquant: {key}"
            assert "value" in kpis[key], f"KPI {key}: champ 'value' absent"
            assert "label" in kpis[key], f"KPI {key}: champ 'label' absent"
    return _assert
