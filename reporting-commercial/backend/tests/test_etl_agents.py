"""
Tests pour les routes ETL Agents
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestAgentRoutes:
    """Tests pour les routes de gestion des agents"""

    def test_list_agents_empty(self, client, mock_execute_query):
        """Test liste agents vide"""
        mock_execute_query.return_value = []

        response = client.get("/api/admin/etl/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["count"] == 0

    def test_list_agents_with_data(self, client, mock_execute_query, sample_agent_data):
        """Test liste agents avec donnees"""
        mock_execute_query.return_value = [sample_agent_data]

        response = client.get("/api/admin/etl/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Agent Test"

    def test_list_agents_filter_by_dwh(self, client, mock_execute_query, sample_agent_data):
        """Test filtre par DWH"""
        mock_execute_query.return_value = [sample_agent_data]

        response = client.get("/api/admin/etl/agents?dwh_code=TEST_DWH")

        assert response.status_code == 200
        # Verifier que le filtre est passe a la requete
        mock_execute_query.assert_called_once()

    def test_list_agents_filter_by_status(self, client, mock_execute_query, sample_agent_data):
        """Test filtre par status"""
        mock_execute_query.return_value = [sample_agent_data]

        response = client.get("/api/admin/etl/agents?status=active")

        assert response.status_code == 200
        mock_execute_query.assert_called_once()

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_create_agent_success(self, mock_cursor, client):
        """Test creation agent reussie"""
        mock_ctx = MagicMock()
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.post("/api/admin/etl/agents", json={
            "dwh_code": "TEST_DWH",
            "name": "New Agent",
            "description": "Test agent",
            "sync_interval_seconds": 300
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "agent_id" in data["data"]
        assert "api_key" in data["data"]
        assert len(data["data"]["api_key"]) > 20  # Cle API assez longue

    def test_create_agent_missing_fields(self, client):
        """Test creation agent sans champs requis"""
        response = client.post("/api/admin/etl/agents", json={
            "name": "New Agent"  # dwh_code manquant
        })

        assert response.status_code == 422  # Validation error

    def test_get_agent_not_found(self, client, mock_execute_query):
        """Test agent non trouve"""
        mock_execute_query.return_value = []

        response = client.get("/api/admin/etl/agents/nonexistent-id")

        assert response.status_code == 404

    def test_get_agent_success(self, client, mock_execute_query, sample_agent_data):
        """Test recuperation agent reussie"""
        mock_execute_query.return_value = [sample_agent_data]

        response = client.get(f"/api/admin/etl/agents/{sample_agent_data['agent_id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Agent Test"

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_update_agent(self, mock_cursor, client, mock_execute_query, sample_agent_data):
        """Test mise a jour agent"""
        mock_ctx = MagicMock()
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.put(
            f"/api/admin/etl/agents/{sample_agent_data['agent_id']}",
            json={"name": "Updated Agent", "sync_interval_seconds": 600}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_delete_agent_success(self, mock_cursor, client):
        """Test suppression agent"""
        mock_ctx = MagicMock()
        mock_ctx.rowcount = 1
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.delete("/api/admin/etl/agents/test-agent-id")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_delete_agent_not_found(self, mock_cursor, client):
        """Test suppression agent inexistant"""
        mock_ctx = MagicMock()
        mock_ctx.rowcount = 0
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.delete("/api/admin/etl/agents/nonexistent-id")

        assert response.status_code == 404


class TestTableConfigRoutes:
    """Tests pour les routes de configuration des tables"""

    def test_list_tables(self, client, mock_execute_query, sample_table_config):
        """Test liste des tables"""
        mock_execute_query.return_value = [sample_table_config]

        response = client.get("/api/admin/etl/agents/test-agent-id/tables")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_add_table(self, mock_cursor, client, sample_table_config):
        """Test ajout table"""
        mock_ctx = MagicMock()
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.post(
            "/api/admin/etl/agents/test-agent-id/tables",
            json=sample_table_config
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestHeartbeatRoutes:
    """Tests pour les routes heartbeat"""

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_heartbeat(self, mock_cursor, client, mock_execute_query):
        """Test heartbeat agent"""
        mock_ctx = MagicMock()
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_execute_query.return_value = []  # Pas de commandes en attente

        response = client.post(
            "/api/agents/test-agent-id/heartbeat",
            json={
                "status": "idle",
                "cpu_usage": 25.0,
                "memory_usage": 50.0,
                "disk_usage": 30.0,
                "queue_size": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "commands" in data


class TestCommandRoutes:
    """Tests pour les routes de commandes"""

    def test_list_commands(self, client, mock_execute_query):
        """Test liste des commandes"""
        mock_execute_query.return_value = [
            {
                "id": 1,
                "command_type": "sync_now",
                "status": "pending",
                "priority": 1
            }
        ]

        response = client.get("/api/admin/etl/agents/test-agent-id/commands")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch('app.routes.etl_agents.get_db_cursor')
    def test_create_command(self, mock_cursor, client):
        """Test creation commande"""
        mock_ctx = MagicMock()
        mock_cursor.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_cursor.return_value.__exit__ = MagicMock(return_value=False)

        response = client.post(
            "/api/admin/etl/agents/test-agent-id/commands",
            json={
                "command_type": "sync_now",
                "priority": 1
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSyncLogRoutes:
    """Tests pour les routes de logs"""

    def test_list_logs(self, client, mock_execute_query, sample_sync_log):
        """Test liste des logs"""
        mock_execute_query.return_value = [sample_sync_log]

        response = client.get("/api/admin/etl/agents/test-agent-id/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_list_logs_filter_by_table(self, client, mock_execute_query, sample_sync_log):
        """Test liste logs filtree par table"""
        mock_execute_query.return_value = [sample_sync_log]

        response = client.get("/api/admin/etl/agents/test-agent-id/logs?table_name=Collaborateurs")

        assert response.status_code == 200

    def test_list_logs_filter_by_status(self, client, mock_execute_query, sample_sync_log):
        """Test liste logs filtree par status"""
        mock_execute_query.return_value = [sample_sync_log]

        response = client.get("/api/admin/etl/agents/test-agent-id/logs?status=success")

        assert response.status_code == 200


class TestStatsRoutes:
    """Tests pour les routes statistiques"""

    def test_get_etl_stats(self, client, mock_execute_query):
        """Test statistiques ETL"""
        mock_execute_query.side_effect = [
            # Stats agents
            [{
                "total_agents": 5,
                "active_agents": 3,
                "syncing_agents": 1,
                "error_agents": 1,
                "online_agents": 4
            }],
            # Stats syncs
            [{
                "total_syncs": 100,
                "success_syncs": 95,
                "error_syncs": 5,
                "total_rows_extracted": 50000,
                "total_rows_synced": 49000,
                "avg_duration": 5.5
            }]
        ]

        response = client.get("/api/admin/etl/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "agents" in data["data"]
        assert "syncs_today" in data["data"]


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires"""

    def test_hash_api_key(self):
        """Test hachage cle API"""
        from app.routes.etl_agents import hash_api_key

        api_key = "test_api_key_12345"
        hashed = hash_api_key(api_key)

        assert len(hashed) == 64  # SHA256 produit 64 caracteres hex
        assert hashed == hash_api_key(api_key)  # Deterministe

    def test_generate_api_key(self):
        """Test generation cle API"""
        from app.routes.etl_agents import generate_api_key

        key1 = generate_api_key()
        key2 = generate_api_key()

        assert len(key1) > 20
        assert key1 != key2  # Aleatoire

    @patch('app.routes.etl_agents.execute_query')
    def test_verify_agent_valid(self, mock_query):
        """Test verification agent valide"""
        from app.routes.etl_agents import verify_agent, hash_api_key

        mock_query.return_value = [{"1": 1}]

        result = verify_agent("test-id", "test-key")

        assert result is True

    @patch('app.routes.etl_agents.execute_query')
    def test_verify_agent_invalid(self, mock_query):
        """Test verification agent invalide"""
        from app.routes.etl_agents import verify_agent

        mock_query.return_value = []

        result = verify_agent("test-id", "wrong-key")

        assert result is False
