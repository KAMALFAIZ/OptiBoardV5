# Architecture ETL - Administration

## Vue d'ensemble

Le systeme ETL d'OptiBoard permet la synchronisation des donnees entre des bases **Sage 100** locales et un **Data Warehouse (DWH)** centralise. L'architecture utilise un modele **Agent-Centralise** avec des agents Python deployes sur les sites distants.

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   SITE LOCAL 1      │     │   SITE LOCAL 2      │     │   SITE LOCAL N      │
│  ┌───────────────┐  │     │  ┌───────────────┐  │     │  ┌───────────────┐  │
│  │   Sage 100    │  │     │  │   Sage 100    │  │     │  │   Sage 100    │  │
│  │  (SQL Server) │  │     │  │  (SQL Server) │  │     │  │  (SQL Server) │  │
│  └───────┬───────┘  │     │  └───────┬───────┘  │     │  └───────┬───────┘  │
│          │          │     │          │          │     │          │          │
│  ┌───────▼───────┐  │     │  ┌───────▼───────┐  │     │  ┌───────▼───────┐  │
│  │  ETL Agent    │  │     │  │  ETL Agent    │  │     │  │  ETL Agent    │  │
│  │   (Python)    │  │     │  │   (Python)    │  │     │  │   (Python)    │  │
│  └───────┬───────┘  │     │  └───────┬───────┘  │     │  └───────┬───────┘  │
└──────────┼──────────┘     └──────────┼──────────┘     └──────────┼──────────┘
           │                           │                           │
           │ HTTPS/REST                │ HTTPS/REST                │ HTTPS/REST
           └───────────────────────────┼───────────────────────────┘
                                       │
                                       ▼
            ┌──────────────────────────────────────────────────────┐
            │                  SERVEUR CENTRAL                      │
            │  ┌────────────────────────────────────────────────┐  │
            │  │              Backend FastAPI                    │  │
            │  │  • Gestion Agents (/api/admin/etl/agents)      │  │
            │  │  • Reception Donnees (/api/agents/*/push-data) │  │
            │  │  • Commandes (/api/agents/*/commands)          │  │
            │  └────────────────────────────────────────────────┘  │
            │                         │                             │
            │  ┌────────────────────────────────────────────────┐  │
            │  │              OptiBoard_SaaS (SQL Server)         │  │
            │  │  • APP_ETL_Agents (Registre)                   │  │
            │  │  • APP_ETL_Agent_Tables (Config)               │  │
            │  │  • APP_ETL_Agent_Sync_Log (Journaux)           │  │
            │  │  • APP_ETL_Agent_Commands (Commandes)          │  │
            │  └────────────────────────────────────────────────┘  │
            │                         │                             │
            │  ┌────────────────────────────────────────────────┐  │
            │  │                 DWH Clients                     │  │
            │  │  • Collaborateurs, Articles, Clients...        │  │
            │  │  • Colonne Societe pour multi-tenant           │  │
            │  └────────────────────────────────────────────────┘  │
            └──────────────────────────────────────────────────────┘
```

## Composants

### 1. ETL Agent (etl-agent/)

Agent Python deploye sur chaque site distant pour extraire les donnees Sage 100.

**Structure:**
```
etl-agent/
├── config/
│   ├── __init__.py          # Configuration classes
│   └── config.yaml.example  # Template configuration
├── core/
│   ├── database.py          # Connexion Sage 100
│   ├── extractor.py         # Extraction donnees
│   └── api_client.py        # Communication serveur
├── services/
│   ├── sync_service.py      # Orchestration sync
│   └── scheduler.py         # Planification
├── main.py                   # Point d'entree
└── requirements.txt
```

**Commandes:**
```bash
# Executer l'agent
python main.py run

# Synchronisation unique
python main.py sync

# Tester les connexions
python main.py test

# Afficher le statut
python main.py status
```

### 2. Backend API (backend/app/routes/etl_agents.py)

Routes FastAPI pour l'administration des agents.

**Endpoints Administration:**
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/admin/etl/agents` | Liste agents |
| POST | `/api/admin/etl/agents` | Creer agent |
| GET | `/api/admin/etl/agents/{id}` | Detail agent |
| PUT | `/api/admin/etl/agents/{id}` | Modifier agent |
| DELETE | `/api/admin/etl/agents/{id}` | Supprimer agent |
| POST | `/api/admin/etl/agents/{id}/regenerate-key` | Regenerer cle API |
| GET | `/api/admin/etl/agents/{id}/tables` | Tables agent |
| POST | `/api/admin/etl/agents/{id}/tables` | Ajouter table |
| GET | `/api/admin/etl/agents/{id}/logs` | Logs sync |
| POST | `/api/admin/etl/agents/{id}/commands` | Envoyer commande |

**Endpoints Agent:**
| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/agents/{id}/register` | Enregistrement |
| POST | `/api/agents/{id}/heartbeat` | Signal vie |
| POST | `/api/agents/{id}/push-data` | Envoi donnees |
| GET | `/api/agents/{id}/commands` | Recuperer commandes |

### 3. Frontend (frontend/src/pages/ETLAdmin.jsx)

Interface React pour l'administration.

**Composants:**
- `AgentList.jsx` - Liste des agents avec statut
- `CreateAgentModal.jsx` - Creation nouvel agent
- `AgentDetailModal.jsx` - Details et configuration
- `SyncLogViewer.jsx` - Visualisation logs

## Flux de Synchronisation

```
1. HEARTBEAT (toutes les 30s)
   Agent → Serveur: Statut, metriques systeme
   Serveur → Agent: Commandes en attente

2. SYNCHRONISATION (toutes les 5min par defaut)
   ┌─────────────────────────────────────────────────────────┐
   │ EXTRACT                                                  │
   │ • Connexion Sage 100                                    │
   │ • Execution requete SQL                                  │
   │ • Filtre incremental (cbModification > last_sync)       │
   └─────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ TRANSFORM                                                │
   │ • Ajout colonne Societe                                 │
   │ • Conversion types (datetime, decimal)                  │
   │ • Serialisation JSON                                    │
   └─────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ LOAD                                                     │
   │ • POST /api/agents/{id}/push-data                       │
   │ • MERGE INTO (upsert) dans DWH                          │
   │ • Log resultats                                         │
   └─────────────────────────────────────────────────────────┘
```

## Configuration Agent

Fichier `config/config.yaml`:

```yaml
agent:
  id: "uuid-fourni-par-le-serveur"
  api_key: "cle-api-32-caracteres"
  name: "Agent Site Principal"

central_server:
  url: "https://optiboard.example.com/api"
  timeout: 60
  retry_count: 3

sage_database:
  server: "localhost"
  database: "BIJOU"
  username: "sa"
  password: "mot_de_passe"
  societe_code: "BIJOU"

sync:
  interval_seconds: 300
  heartbeat_interval: 30
  batch_size: 10000
```

## Tables Synchronisees

Configuration YAML (`backend/etl/config/sync_tables.yaml`):

```yaml
tables:
  - name: Collaborateurs
    source:
      query: |
        SELECT CO_No, CO_Nom, CO_Prenom, ...
        FROM F_COLLABORATEUR
    target:
      table: Collaborateurs
      primary_key: [Societe, cbMarq]
    sync_type: full

  - name: Articles
    source:
      query: |
        SELECT AR_Ref, AR_Design, ...
        FROM F_ARTICLE
    target:
      table: Articles
      primary_key: [Societe, cbMarq]
    sync_type: incremental
    timestamp_column: cbModification
```

## Securite

### Authentification Agent

1. **Creation agent** via UI → Generation `agent_id` + `api_key`
2. **Stockage** : `api_key_hash` (SHA256) en base
3. **Verification** : Header `X-API-Key` + `X-Agent-ID` sur chaque requete

### Bonnes Pratiques

- Cle API generee une seule fois, stockee securisee
- Communication HTTPS obligatoire en production
- Isolation multi-tenant via colonne `Societe`
- Logs d'audit pour tracabilite

## Deploiement Agent

```bash
# 1. Installer Python 3.9+
# 2. Cloner/copier etl-agent/

# 3. Installer dependances
pip install -r requirements.txt

# 4. Configurer
cp config/config.yaml.example config/config.yaml
# Editer config.yaml avec les vraies valeurs

# 5. Tester
python main.py test

# 6. Executer
python main.py run
```

### Service Windows

```batch
@echo off
cd C:\ETL-Agent
python main.py run
```

### Service Linux (systemd)

```ini
[Unit]
Description=OptiBoard ETL Agent
After=network.target

[Service]
User=etl-agent
WorkingDirectory=/opt/etl-agent
ExecStart=/usr/bin/python3 main.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Indicateurs

| Indicateur | Seuil Warning | Seuil Critical |
|------------|---------------|----------------|
| Agent offline | > 2 min | > 5 min |
| Echecs consecutifs | >= 3 | >= 5 |
| CPU agent | > 80% | > 95% |
| Duree sync | > 5 min | > 15 min |

### Alertes

Les alertes sont automatiquement generees dans `APP_ETL_Alerts` apres 3 echecs consecutifs.
