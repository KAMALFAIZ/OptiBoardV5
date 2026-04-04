# Reporting Commercial - KAsoft

Application web de Reporting Commercial de Fin d'Année pour la société KAsoft, spécialisée dans la fabrication et distribution d'appareils sanitaires.

## Architecture

```
reporting-commercial/
├── backend/                 # API FastAPI (Python)
│   ├── app/
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # Connexion SQL Server
│   │   ├── models/         # Schémas Pydantic
│   │   ├── routes/         # Routes API
│   │   ├── services/       # Services métier
│   │   └── sql/            # Templates SQL
│   ├── requirements.txt
│   └── run.py
└── frontend/               # Interface React
    ├── src/
    │   ├── components/     # Composants réutilisables
    │   ├── pages/          # Pages de l'application
    │   ├── services/       # Appels API
    │   └── utils/
    └── package.json
```

## Prérequis

- **Python 3.10+**
- **Node.js 18+**
- **SQL Server** avec ODBC Driver 17
- Base de données `GROUPE_ALBOUGHAZE` avec les tables:
  - `Chiffre_Affaires_Groupe_Bis`
  - `Mouvement_stock`
  - `BalanceAgee`

## Installation

### Backend

```bash
cd backend

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données
cp .env.example .env
# Modifier .env avec vos paramètres

# Lancer le serveur
python run.py
```

Le backend sera accessible sur http://localhost:8000

### Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer en développement
npm run dev
```

Le frontend sera accessible sur http://localhost:3000

## Modules

### 1. Dashboard Principal
- KPIs en temps réel (CA, Marge, DSO, Rotation Stock)
- Graphiques d'évolution mensuelle
- Comparatif N/N-1
- Alertes (ruptures, impayés critiques)

### 2. Analyse des Ventes
- CA global et évolution mensuelle
- Répartition par gamme de produits
- Performance par canal de distribution
- Analyse géographique
- Top 10 produits / clients

### 3. Performance Commerciale
- Résultats par commercial
- Atteinte des objectifs
- Classement des commerciaux

### 4. Gestion des Stocks
- État global des stocks
- Rotation des stocks
- Couverture de stock
- Stock dormant (>180 jours)
- Alertes surstocks et sous-stocks

### 5. Recouvrement et DSO
- Calcul DSO
- Balance âgée visuelle
- Top 10 encours clients
- Créances douteuses (+120 jours)

### 6. Admin SQL
- Visualisation des requêtes SQL
- Console SQL interactive (lecture seule)
- Statistiques de performance

## API Endpoints

### Dashboard
- `GET /api/dashboard` - KPIs principaux
- `GET /api/dashboard/evolution-mensuelle` - Évolution du CA
- `GET /api/dashboard/comparatif-annuel` - Comparatif N/N-1

### Ventes
- `GET /api/ventes` - Données de ventes avec filtres
- `GET /api/ventes/par-gamme` - Ventes par gamme
- `GET /api/ventes/par-commercial` - Ventes par commercial
- `GET /api/ventes/top-clients` - Top clients
- `GET /api/ventes/top-produits` - Top produits

### Drill-Down Ventes
- `GET /api/ventes/detail/gamme/{gamme}` - Détail par gamme
- `GET /api/ventes/detail/client/{code_client}` - Historique client
- `GET /api/ventes/detail/produit/{code_article}` - Historique produit
- `GET /api/ventes/detail/commercial/{commercial}` - Performance commercial

### Stocks
- `GET /api/stocks` - État global des stocks
- `GET /api/stocks/dormant` - Articles dormants
- `GET /api/stocks/rotation` - Rotation des stocks
- `GET /api/stocks/article/{code_article}` - Mouvements d'un article

### Recouvrement
- `GET /api/recouvrement` - Données recouvrement et DSO
- `GET /api/recouvrement/dso` - Calcul DSO
- `GET /api/recouvrement/balance-agee` - Balance âgée
- `GET /api/recouvrement/client/{client_id}` - Détail encours client
- `GET /api/recouvrement/tranche/{tranche}` - Clients par tranche

### Admin SQL
- `GET /api/admin/queries` - Liste des requêtes
- `GET /api/admin/queries/{id}` - Détail d'une requête
- `POST /api/admin/queries/execute` - Exécuter une requête
- `GET /api/admin/queries/stats` - Statistiques

### Export
- `GET /api/export/excel/ventes` - Export Excel des ventes
- `GET /api/export/excel/stocks` - Export Excel des stocks
- `GET /api/export/excel/recouvrement` - Export Excel recouvrement
- `GET /api/export/excel/complet` - Rapport Excel complet
- `GET /api/export/pdf/dashboard` - Export PDF dashboard

## Fonctionnalité Drill-Down

Chaque élément de l'application permet de consulter les détails en cliquant dessus:

- **KPIs** → Clic pour voir le détail des données
- **Graphiques** → Clic sur une barre/point pour voir les lignes concernées
- **Tableaux** → Clic sur une ligne pour voir le détail complet
- **Totaux** → Clic pour décomposer par dimension

## Technologies

### Backend
- **FastAPI** - Framework Python async
- **pyodbc** - Connexion SQL Server
- **pandas** - Traitement des données
- **openpyxl** - Export Excel
- **reportlab** - Génération PDF

### Frontend
- **React 18** - Framework UI
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Recharts** - Graphiques
- **React Router** - Navigation
- **Axios** - Appels API
- **Lucide React** - Icônes

## Documentation API

Une fois le backend lancé, accédez à:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## Licence

Propriétaire - KAsoft
