"""
Configuration pytest pour les tests backend
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Ajouter le repertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_db_connection():
    """Mock de la connexion base de donnees"""
    with patch('app.database.get_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_conn, mock_cursor


@pytest.fixture
def mock_execute_query():
    """Mock de execute_query"""
    with patch('app.database.execute_query') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def client(mock_execute_query):
    """Client de test FastAPI"""
    from run import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_agent_data():
    """Donnees d'exemple pour un agent"""
    return {
        "agent_id": "12345678-1234-1234-1234-123456789012",
        "dwh_code": "TEST_DWH",
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
        "total_rows_synced": 50000,
        "consecutive_failures": 0,
        "tables_count": 5
    }


@pytest.fixture
def sample_table_config():
    """Configuration de table d'exemple"""
    return {
        "table_name": "Collaborateurs",
        "source_query": "SELECT * FROM F_COLLABORATEUR",
        "target_table": "Collaborateurs",
        "societe_code": "BIJOU",
        "primary_key_columns": ["Societe", "cbMarq"],
        "sync_type": "incremental",
        "timestamp_column": "cbModification",
        "priority": "normal",
        "is_enabled": True
    }


@pytest.fixture
def sample_sync_log():
    """Log de synchronisation d'exemple"""
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
        "error_message": None
    }
