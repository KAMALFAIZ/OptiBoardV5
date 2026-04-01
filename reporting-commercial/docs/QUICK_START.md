# Guide de Demarrage Rapide

## Prerequisites

- Python 3.9+
- Node.js 18+
- SQL Server avec ODBC Driver 17
- Acces aux bases Sage 100

## 1. Installation Backend

```bash
cd backend

# Creer environnement virtuel
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Activer (Linux/Mac)
source venv/bin/activate

# Installer dependances
pip install -r requirements.txt

# Configurer
cp .env.example .env
# Editer .env avec vos parametres
```

## 2. Configuration Base de Donnees

Editer `.env`:

```ini
DB_SERVER=localhost
DB_NAME=OptiBoard_SaaS
DB_USER=sa
DB_PASSWORD=votre_mot_de_passe
```

Initialiser les tables:

```bash
# Executer les scripts SQL
sqlcmd -S localhost -d OptiBoard_SaaS -i sql/001_optiboard_web_central.sql
sqlcmd -S localhost -d OptiBoard_SaaS -i sql/003_create_etl_agents_tables.sql
```

## 3. Demarrer le Backend

```bash
python run.py
# API disponible sur http://localhost:8080
# Documentation: http://localhost:8080/api/docs
```

## 4. Installation Frontend

```bash
cd frontend

# Installer dependances
npm install

# Demarrer en mode dev
npm run dev
# Interface disponible sur http://localhost:5173
```

## 5. Configuration ETL Agent

```bash
cd etl-agent

# Installer dependances
pip install -r requirements.txt

# Configurer
cp config/config.yaml.example config/config.yaml
# Editer config.yaml
```

## 6. Creer un Agent

1. Ouvrir l'interface web: http://localhost:5173
2. Aller dans Administration > ETL
3. Cliquer "Nouvel Agent"
4. Remplir le formulaire
5. **Sauvegarder la cle API affichee**

## 7. Configurer l'Agent

Editer `etl-agent/config/config.yaml`:

```yaml
agent:
  id: "votre-agent-id"
  api_key: "votre-cle-api"
  name: "Agent Site 1"

central_server:
  url: "http://localhost:8080/api"

sage_database:
  server: "localhost"
  database: "BIJOU"
  username: "sa"
  password: "mot_de_passe"
  societe_code: "BIJOU"
```

## 8. Tester et Demarrer

```bash
# Tester les connexions
python main.py test

# Demarrer l'agent
python main.py run
```

## Verification

1. L'agent doit apparaitre "En ligne" dans l'interface
2. Les heartbeats doivent arriver toutes les 30 secondes
3. La premiere synchronisation doit demarrer automatiquement

## Depannage

### Agent "Hors ligne"
- Verifier que l'agent est demarre
- Verifier la configuration reseau
- Verifier les credentials

### Erreur de synchronisation
- Consulter les logs dans l'interface
- Verifier la connexion Sage 100
- Verifier les requetes SQL

### Base non configuree
- Executer les scripts SQL d'initialisation
- Verifier le fichier .env

## Commandes Utiles

```bash
# Backend
python run.py              # Demarrer API
pytest tests/              # Executer tests

# Frontend
npm run dev                # Mode dev
npm run build              # Build production

# Agent
python main.py run         # Executer agent
python main.py sync        # Sync unique
python main.py test        # Tester connexions
python main.py status      # Afficher statut
```
