# API Reference - OptiBoard ETL

Documentation complete de l'API ETL pour la gestion des agents de synchronisation.

## Authentication

### Headers requis pour les agents

```http
X-API-Key: <cle_api_agent>
X-Agent-ID: <uuid_agent>
Content-Type: application/json
```

## Endpoints Administration

### Agents

#### GET /api/admin/etl/agents

Liste tous les agents ETL.

**Parametres Query:**
| Parametre | Type | Description |
|-----------|------|-------------|
| dwh_code | string | Filtrer par code DWH |
| status | string | Filtrer par statut (active, inactive, syncing, error) |

**Reponse:**
```json
{
  "success": true,
  "data": [
    {
      "agent_id": "uuid",
      "dwh_code": "DWH_CLIENT",
      "name": "Agent Principal",
      "status": "active",
      "health_status": "En ligne",
      "hostname": "server-01",
      "ip_address": "192.168.1.100",
      "last_heartbeat": "2024-01-15T10:00:00",
      "last_sync": "2024-01-15T09:55:00",
      "tables_count": 5,
      "total_syncs": 100,
      "consecutive_failures": 0
    }
  ],
  "count": 1
}
```

#### POST /api/admin/etl/agents

Cree un nouvel agent.

**Body:**
```json
{
  "dwh_code": "DWH_CLIENT",
  "name": "Nouvel Agent",
  "description": "Description optionnelle",
  "sync_interval_seconds": 300,
  "heartbeat_interval_seconds": 30,
  "batch_size": 10000
}
```

**Reponse:**
```json
{
  "success": true,
  "message": "Agent cree avec succes",
  "data": {
    "agent_id": "uuid-genere",
    "api_key": "cle-api-a-sauvegarder",
    "name": "Nouvel Agent",
    "dwh_code": "DWH_CLIENT"
  },
  "warning": "Sauvegardez la cle API immediatement!"
}
```

#### GET /api/admin/etl/agents/{agent_id}

Recupere les details d'un agent.

**Reponse:**
```json
{
  "success": true,
  "data": {
    "agent_id": "uuid",
    "dwh_code": "DWH_CLIENT",
    "name": "Agent Principal",
    "description": "...",
    "status": "active",
    "hostname": "server-01",
    "ip_address": "192.168.1.100",
    "agent_version": "1.0.0",
    "last_heartbeat": "2024-01-15T10:00:00",
    "last_sync": "2024-01-15T09:55:00",
    "sync_interval_seconds": 300,
    "heartbeat_interval_seconds": 30,
    "batch_size": 10000,
    "is_active": true,
    "total_syncs": 100,
    "total_rows_synced": 50000,
    "consecutive_failures": 0,
    "health_status": "En ligne"
  }
}
```

#### PUT /api/admin/etl/agents/{agent_id}

Met a jour un agent.

**Body:**
```json
{
  "name": "Nouveau Nom",
  "description": "Nouvelle description",
  "sync_interval_seconds": 600,
  "is_active": true
}
```

#### DELETE /api/admin/etl/agents/{agent_id}

Supprime un agent.

#### POST /api/admin/etl/agents/{agent_id}/regenerate-key

Regenere la cle API d'un agent.

**Reponse:**
```json
{
  "success": true,
  "message": "Cle API regeneree",
  "data": {
    "api_key": "nouvelle-cle-api"
  }
}
```

### Configuration Tables

#### GET /api/admin/etl/agents/{agent_id}/tables

Liste les tables configurees pour un agent.

**Reponse:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "table_name": "Collaborateurs",
      "source_query": "SELECT ... FROM F_COLLABORATEUR",
      "target_table": "Collaborateurs",
      "societe_code": "BIJOU",
      "primary_key_columns": "[\"Societe\", \"cbMarq\"]",
      "sync_type": "incremental",
      "timestamp_column": "cbModification",
      "is_enabled": true,
      "priority": "normal",
      "last_sync": "2024-01-15T10:00:00",
      "last_sync_status": "success"
    }
  ],
  "count": 1
}
```

#### POST /api/admin/etl/agents/{agent_id}/tables

Ajoute une table a synchroniser.

**Body:**
```json
{
  "table_name": "Articles",
  "source_query": "SELECT AR_Ref, AR_Design FROM F_ARTICLE",
  "target_table": "Articles",
  "societe_code": "BIJOU",
  "primary_key_columns": ["Societe", "cbMarq"],
  "sync_type": "incremental",
  "timestamp_column": "cbModification",
  "priority": "normal",
  "is_enabled": true
}
```

#### PUT /api/admin/etl/agents/{agent_id}/tables/{table_id}

Met a jour une configuration de table.

#### DELETE /api/admin/etl/agents/{agent_id}/tables/{table_id}

Supprime une configuration de table.

#### POST /api/admin/etl/agents/{agent_id}/import-tables

Importe les tables depuis la configuration YAML.

**Parametres Query:**
| Parametre | Type | Description |
|-----------|------|-------------|
| societe_code | string | Code societe pour les tables |

### Commandes

#### GET /api/admin/etl/agents/{agent_id}/commands

Liste les commandes d'un agent.

**Parametres Query:**
| Parametre | Type | Description |
|-----------|------|-------------|
| status | string | Filtrer par statut |
| limit | integer | Nombre max de resultats (defaut: 50) |

#### POST /api/admin/etl/agents/{agent_id}/commands

Cree une commande pour un agent.

**Body:**
```json
{
  "command_type": "sync_now",
  "command_data": null,
  "priority": 1,
  "expires_in_minutes": null
}
```

**Types de commandes:**
| Type | Description |
|------|-------------|
| sync_now | Declencher synchronisation immediate |
| sync_table | Synchroniser une table specifique |
| pause | Mettre l'agent en pause |
| resume | Reprendre l'agent |
| update_config | Recharger la configuration |

### Logs et Monitoring

#### GET /api/admin/etl/agents/{agent_id}/logs

Liste les logs de synchronisation.

**Parametres Query:**
| Parametre | Type | Description |
|-----------|------|-------------|
| table_name | string | Filtrer par table |
| status | string | Filtrer par statut |
| limit | integer | Nombre max (defaut: 100) |

**Reponse:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "agent_id": "uuid",
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
      "error_message": null
    }
  ]
}
```

#### GET /api/admin/etl/agents/{agent_id}/heartbeats

Liste les heartbeats d'un agent.

**Parametres Query:**
| Parametre | Type | Description |
|-----------|------|-------------|
| limit | integer | Nombre max (defaut: 50) |

#### GET /api/admin/etl/stats

Statistiques globales ETL.

**Reponse:**
```json
{
  "success": true,
  "data": {
    "agents": {
      "total_agents": 5,
      "active_agents": 3,
      "syncing_agents": 1,
      "error_agents": 1,
      "online_agents": 4
    },
    "syncs_today": {
      "total_syncs": 100,
      "success_syncs": 95,
      "error_syncs": 5,
      "total_rows_extracted": 50000,
      "total_rows_synced": 49000,
      "avg_duration": 5.5
    }
  }
}
```

## Endpoints Agent

Ces endpoints sont appeles par l'agent ETL lui-meme.

### POST /api/agents/{agent_id}/register

Enregistre l'agent au demarrage.

**Body:**
```json
{
  "hostname": "server-01",
  "ip_address": "192.168.1.100",
  "os_info": "Windows 10",
  "agent_version": "1.0.0"
}
```

### POST /api/agents/{agent_id}/heartbeat

Envoie un signal de vie.

**Body:**
```json
{
  "status": "idle",
  "current_task": null,
  "cpu_usage": 25.5,
  "memory_usage": 50.0,
  "disk_usage": 30.0,
  "queue_size": 0
}
```

**Reponse:**
```json
{
  "success": true,
  "commands": [
    {
      "id": 1,
      "command_type": "sync_now",
      "command_data": null,
      "priority": 1
    }
  ]
}
```

### GET /api/agents/{agent_id}/tables

Recupere la configuration des tables.

### POST /api/agents/{agent_id}/push-data

Envoie les donnees synchronisees.

**Body:**
```json
{
  "table_name": "Collaborateurs",
  "target_table": "Collaborateurs",
  "societe_code": "BIJOU",
  "sync_type": "incremental",
  "primary_key": ["Societe", "cbMarq"],
  "columns": ["Societe", "cbMarq", "CO_Nom", "CO_Prenom"],
  "rows_count": 100,
  "data": [
    {"Societe": "BIJOU", "cbMarq": 1, "CO_Nom": "Dupont", "CO_Prenom": "Jean"},
    {"Societe": "BIJOU", "cbMarq": 2, "CO_Nom": "Martin", "CO_Prenom": "Marie"}
  ],
  "batch_id": "abc123",
  "sync_timestamp_start": "2024-01-15T09:00:00",
  "sync_timestamp_end": "2024-01-15T10:00:00"
}
```

**Reponse:**
```json
{
  "success": true,
  "rows_inserted": 50,
  "rows_updated": 50,
  "duration_seconds": 2.5
}
```

### POST /api/agents/{agent_id}/commands/{command_id}/ack

Acquitte une commande.

### POST /api/agents/{agent_id}/commands/{command_id}/complete

Marque une commande comme terminee.

**Body:**
```json
{
  "success": true,
  "result": {"rows_synced": 100},
  "error": null
}
```

### POST /api/agents/{agent_id}/sync-result

Rapporte le resultat d'une synchronisation.

**Body:**
```json
{
  "table_name": "Collaborateurs",
  "societe_code": "BIJOU",
  "success": true,
  "rows_extracted": 100,
  "rows_inserted": 50,
  "rows_updated": 50,
  "rows_failed": 0,
  "duration_seconds": 5.0,
  "error_message": null
}
```

## Codes d'erreur

| Code | Description |
|------|-------------|
| 200 | Succes |
| 400 | Requete invalide |
| 401 | Non autorise (cle API invalide) |
| 404 | Ressource non trouvee |
| 422 | Erreur de validation |
| 500 | Erreur serveur |
| 503 | Base de donnees non configuree |

## Exemples cURL

```bash
# Lister les agents
curl -X GET "http://localhost:8080/api/admin/etl/agents"

# Creer un agent
curl -X POST "http://localhost:8080/api/admin/etl/agents" \
  -H "Content-Type: application/json" \
  -d '{"dwh_code": "TEST_DWH", "name": "Agent Test"}'

# Heartbeat (depuis l'agent)
curl -X POST "http://localhost:8080/api/agents/{agent_id}/heartbeat" \
  -H "X-API-Key: ma-cle-api" \
  -H "X-Agent-ID: {agent_id}" \
  -H "Content-Type: application/json" \
  -d '{"status": "idle", "cpu_usage": 25.5}'
```
