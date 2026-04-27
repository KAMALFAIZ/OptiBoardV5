# OptiBoard — Guide Technique Claude

## Architecture générale

```
C:\OptiBoard\                       <- Dossier d'installation
  python\                           <- Python 3.11 embedded (avec toutes les dépendances)
  backend\                          <- Code Cython compilé (.pyd) + .pyc
  frontend\                         <- React build (Vite dist/)
  nssm.exe                          <- Service manager Windows
  .env                              <- Template vide (créé par Inno Setup si absent)
  backend\.env                      <- VRAIE config SQL (écrite par le wizard de setup)
  logs\                             <- backend.log + backend.error.log
  OptiBoard-Launcher.bat            <- Lanceur intelligent (double-clic)
  install_service.bat               <- Installe le service Windows NSSM
  uninstall_service.bat             <- Désinstalle le service Windows NSSM
```

**IMPORTANT** : Le `.env` racine (`C:\OptiBoard\.env`) est un template vide créé par Inno Setup.
La vraie configuration est écrite par le wizard de setup à `C:\OptiBoard\backend\.env`.
`config.py` cherche : `Path(__file__).parent.parent / ".env"` → `backend/.env`.

---

## Pipeline de build complet

### Prérequis
- Python 3.11 + MSVC (Visual Studio Build Tools) — pour Cython
- Node.js 18+ — pour le build React
- Inno Setup 6 — `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

### Étapes dans l'ordre

```
1. Compiler le backend (Cython)
   cd reporting-commercial\backend
   build_protected.bat
   -> Produit: dist_client\  (53 .pyd + 43 .pyc)

2. Builder le frontend (React/Vite)
   cd reporting-commercial\frontend
   npm run build
   -> Produit: dist\

3. Lancer le build installeur
   cd installer
   build_installer.bat
   -> Ce script fait:
      [1/7] Télécharge Python 3.11 embedded (cache)
      [2/7] Télécharge NSSM (cache)
      [3/7] Extrait + patche python311._pth (active import site + ajoute ..\backend)
      [4/7] Installe pip + requirements.txt dans le Python embedded
      [5/7] Extrait nssm.exe
      [6/7] Copie backend (dist_client -> payload\backend) + frontend (dist -> payload\frontend)
      [7/7] ISCC.exe -> output\OptiBoard-Setup-1.0.0.exe (~109 MB)
```

**Piège critique** : Si on modifie `setup.py` ou `SetupPage.jsx` APRÈS le build Cython/React,
il faut OBLIGATOIREMENT relancer les étapes 1 et/ou 2 avant l'étape 3.
Le script `build_installer.bat` vérifie que `dist_client\` et `dist\` existent mais ne vérifie pas les dates.

---

## Bug NSSM AppDirectory (trailing quote) — CORRIGÉ

### Symptôme
Service `OptiBoard-Backend` crashe au démarrage. Dans les logs NSSM :
`Le chemin d'accès spécifié est introuvable : C:\OptiBoard"`

### Cause
Dans `install_service.bat`, la variable `APP_DIR` se termine par `\` :
```bat
set "APP_DIR=C:\OptiBoard\"
"%NSSM%" set %SVC% AppDirectory "%APP_DIR%"
```
Le `\"` final est interprété par cmd.exe comme un guillemet échappé.
NSSM enregistre alors `C:\OptiBoard"` dans le registre → chemin invalide → crash.

### Fix appliqué (`installer/payload/scripts/install_service.bat`)
```bat
set "APP_DIR_NS=%APP_DIR%"
if "%APP_DIR_NS:~-1%"=="\" set "APP_DIR_NS=%APP_DIR_NS:~0,-1%"
...
"%NSSM%" set %SVC% AppDirectory "%APP_DIR_NS%"
```

### Fix pour installations existantes (`FIX_SERVICE.bat` à la racine)
Script auto-élevé (admin) qui :
1. Arrête le service
2. Corrige AppDirectory via `nssm.exe set OptiBoard-Backend AppDirectory "C:\OptiBoard"`
3. Redémarre le service

---

## Wizard de setup — 4 étapes

### Flux général
```
App.jsx  --(GET /api/setup/status)--> configured: false
         --> affiche SetupPage.jsx
         configured: true
         --> affiche l'app normale
```

### Routes exemptées d'auth (setup.py)
- `GET  /api/setup/status`
- `POST /api/setup/test-connection`
- `POST /api/setup/configure`

### Étapes du wizard (`SetupPage.jsx`)

**Étape 1 — Serveur SQL**
- Serveur (`DB_SERVER`), port, utilisateur, mot de passe
- Base centrale (`DB_NAME`, défaut : `OptiBoard_SaaS`)
- Nom de l'application (`APP_NAME`)

**Étape 2 — Premier client DWH**
- Case à cocher "Créer un premier client local" (`create_first_dwh`)
- Code client (`first_dwh_code`, ex: `LOCAL`) → prévisualisation `OptiBoard_LOCAL`
- Nom de l'entreprise (`first_dwh_name`)
- `canStep2 = !create_first_dwh || (first_dwh_code && first_dwh_name)`

**Étape 3 — Test de connexion + installation**
- Bouton "Tester la connexion" → `POST /api/setup/test-connection`
- Bouton "Installer" désactivé jusqu'au succès du test
- Payload envoyé : `{ server, port, user, password, database, app_name, create_first_dwh, first_dwh_code, first_dwh_name }`

**Étape 4 — Succès**
- Affiche les credentials admin (boutons "copier")
- Carte d'info DWH créé
- Redirection automatique après 5 secondes

### Logique backend (`/configure`)
```python
1. Écrire C:\OptiBoard\backend\.env
2. init_all_tables()           <- crée toutes les tables SQL
3. _create_admin_users()       <- superadmin + admin_client
4. if create_first_dwh:
       _create_first_local_dwh(code, nom, ...)
```

### `_create_first_local_dwh()`
1. `CREATE DATABASE [OptiBoard_<CODE>]` (si n'existe pas)
2. `INSERT INTO APP_DWH` (code, nom, serveur_dwh, base_dwh, user_dwh, password_dwh)
3. `INSERT INTO APP_UserDWH` pour superadmin et admin_client (`role_dwh='admin', is_default=1`)

---

## Schéma APP_DWH — colonnes manquantes (migration)

### Problème initial
Après un setup, `APP_DWH` était créée avec seulement les colonnes de base.
10 colonnes manquantes provoquaient des erreurs SQL :
```
Nom de colonne non valide: 'serveur_optiboard', 'base_optiboard',
'user_optiboard', 'password_optiboard', 'is_demo',
'ssh_enabled', 'ssh_host', 'ssh_port', 'ssh_user', 'ssh_password'
```

### Fix permanent (section migration dans `setup.py`)
```sql
ALTER TABLE APP_DWH ADD serveur_optiboard NVARCHAR(255) NULL;
ALTER TABLE APP_DWH ADD base_optiboard NVARCHAR(255) NULL;
ALTER TABLE APP_DWH ADD user_optiboard NVARCHAR(255) NULL;
ALTER TABLE APP_DWH ADD password_optiboard NVARCHAR(500) NULL;
ALTER TABLE APP_DWH ADD is_demo BIT NOT NULL DEFAULT 0;
ALTER TABLE APP_DWH ADD ssh_enabled BIT NOT NULL DEFAULT 0;
ALTER TABLE APP_DWH ADD ssh_host NVARCHAR(255) NULL;
ALTER TABLE APP_DWH ADD ssh_port INT NULL;
ALTER TABLE APP_DWH ADD ssh_user NVARCHAR(255) NULL;
ALTER TABLE APP_DWH ADD ssh_password NVARCHAR(500) NULL;
```
Chaque `ALTER` est protégé par `IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE ...)`.

### Fix pour installs existantes
Exécuter le script PowerShell via `System.Data.SqlClient` avec les mêmes `ALTER TABLE`.

---

## Lancement automatique du navigateur (Launcher)

### Problème
Si `.env` n'est pas configuré, le backend démarre en "mode setup" (répond immédiatement sur 8084).
Le launcher attendait 90 tentatives (≈5 min) avant d'ouvrir le navigateur.

### Solution (`OptiBoard-Launcher.bat`)
```bat
set "SETUP_TRIES=3"
...
if !TRIES!==!SETUP_TRIES! (
    sc query %SVC% 2>nul | findstr /C:"STOPPED" >nul 2>&1
    if errorlevel 1 (
        REM Service toujours en cours -> mode setup probable -> ouvrir maintenant
        goto :open_browser
    )
)
```
Après 3 polls HTTP échoués (≈9 sec), si le service n'est pas STOPPED, le navigateur s'ouvre.
Le wizard de setup s'affiche car `/api/setup/status` répond `configured: false`.

---

## Protection du code (Cython)

### Script : `reporting-commercial/backend/build_protected.py`

| Répertoire / Fichier | Traitement |
|---|---|
| `services/`, `routes/`, `middleware/`, `sage_direct/` | Compilé `.pyd` (natif Cython) |
| `config*.py`, `database*.py` | Compilé `.pyd` |
| `models/schemas.py` | Laissé en `.py` (incompatible Pydantic) |
| `__init__.py`, `main.py` | Laissés en `.py` |
| `run_service.py`, `run_client.py` | Copiés tels quels (points d'entrée) |

**Output** : `dist_client/` — jamais modifier les sources, toujours rebuilder.

### `python311._pth` (patch critique)
Python embedded ignore `PYTHONPATH`. Seul le `._pth` est chargé.
Le script `build_installer.bat` y injecte :
```
..\backend
import site
```
Sans `import site`, pip et les packages ne sont pas trouvés.
Sans `..\backend`, `from app.config import ...` échoue au runtime.

---

## Multi-tenant : Base centrale vs DWH

| Base | Contenu |
|---|---|
| `OptiBoard_SaaS` | Tables système : `APP_Client`, `APP_User`, `APP_DWH`, `APP_UserDWH`, etc. |
| `OptiBoard_<CODE>` | Données client : ventes, stocks, indicateurs Sage/BI |

`APP_DWH` stocke les coordonnées de connexion à chaque base DWH client.
`APP_UserDWH` associe les utilisateurs aux DWH auxquels ils ont accès (`is_default=1` → DWH par défaut).

---

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `installer/build_installer.bat` | Pipeline complet : Python embedded + dépendances + ISCC |
| `installer/OptiBoard.iss` | Script Inno Setup (structure install, service, icônes) |
| `installer/payload/scripts/install_service.bat` | Installe le service NSSM (corrigé trailing quote) |
| `installer/payload/scripts/OptiBoard-Launcher.bat` | Lance/attend le backend, ouvre le navigateur |
| `reporting-commercial/backend/build_protected.py` | Compile app/ → dist_client/ via Cython |
| `reporting-commercial/backend/app/routes/setup.py` | Wizard API : status, test-connection, configure |
| `reporting-commercial/frontend/src/pages/SetupPage.jsx` | Wizard UI React (4 étapes) |
| `reporting-commercial/frontend/src/App.jsx` | Routage : vérifie setup/status au démarrage |
| `FIX_SERVICE.bat` | One-shot admin : corrige AppDirectory NSSM sur install existante |

---

## Commandes utiles

```powershell
# Vérifier le service
sc query OptiBoard-Backend

# Voir les logs
notepad C:\OptiBoard\logs\backend.log

# Redémarrer le service
nssm restart OptiBoard-Backend

# Voir AppDirectory dans le registre
reg query "HKLM\SYSTEM\CurrentControlSet\Services\OptiBoard-Backend\Parameters" /v AppDirectory

# Corriger AppDirectory manuellement (admin requis)
C:\OptiBoard\nssm.exe set OptiBoard-Backend AppDirectory "C:\OptiBoard"

# Tester l'API setup
curl http://127.0.0.1:8084/api/setup/status
```

---

## Master Catalog HTTP — Sync depuis serveur central distant

### Architecture

```
┌─────────────────────────────────┐         ┌──────────────────────────────┐
│  Serveur central KASOFT (cloud) │         │  Client (LAN)                │
│  ┌───────────────────────────┐  │  HTTPS  │  ┌────────────────────────┐  │
│  │ OptiBoard_SaaS (master)   │◄─┼─────────┤  │ Récupérer base maître  │  │
│  │   APP_Menus, _Dashboards, │  │         │  └──────────┬─────────────┘  │
│  │   _GridViews, _Pivots_V2  │  │         │             │                │
│  └─────────┬─────────────────┘  │         │  ┌──────────▼─────────────┐  │
│            │                     │         │  │ update_manager.py      │  │
│  GET /api/master/menus           │         │  │ (urllib HTTP client)   │  │
│  GET /api/master/dashboards      │         │  └──────────┬─────────────┘  │
│  GET /api/master/gridviews       │         │             │                │
│  GET /api/master/pivots          │         │  ┌──────────▼─────────────┐  │
│  GET /api/master/datasources     │         │  │ OptiBoard_<CODE>       │  │
│  GET /api/master/all             │         │  │ (is_customized=1       │  │
│  GET /api/master/info            │         │  │  protège du sync)      │  │
│  Auth: X-Master-Api-Key          │         │  └────────────────────────┘  │
│  MASTER_API_KEY=xxx (.env)       │         │  MASTER_API_URL=https://...  │
└─────────────────────────────────┘         │  MASTER_API_KEY=xxx (.env)   │
                                             └──────────────────────────────┘
```

### Côté serveur central (publishing)
- Routeur `app/routes/master_export.py` exposé via `/api/master/*`
- Auth obligatoire via header `X-Master-Api-Key`
- Si `MASTER_API_KEY` vide → routes renvoient `503` (module désactivé)
- Source : base centrale locale `OptiBoard_SaaS`

### Côté client (consuming)
- Vars `.env` :
  - `MASTER_API_URL=https://central.kasoft.ma` (sans `/api`)
  - `MASTER_API_KEY=<même clé que serveur>`
  - `MASTER_TIMEOUT=30`
- Si `MASTER_API_URL` configuré → `pull_builder_updates()` fait HTTP fetch
- Si vide → fallback comportement historique (lecture `OptiBoard_SaaS` locale)
- Réponse `/pull/builder` inclut `"source": "remote_http" | "local_central_db"`

### Endpoints client de gestion (`/api/updates/master/*`)

| Endpoint | Action |
|---|---|
| `GET  /api/updates/master/config` | Lire config courante (clé masquée) |
| `POST /api/updates/master/config` | Écrire URL/KEY/TIMEOUT dans `.env` |
| `POST /api/updates/master/test`   | Test ping sans sauvegarder (`GET /api/master/info`) |

### UI Frontend
- Page `MasterConfigPage.jsx` route `/admin/master-config` (admin uniquement)
- Bouton "Tester" → affiche nb d'éléments exposés par catégorie
- Bouton "Sauvegarder" → écrit `.env` + recharge settings
- Badge live "● Activé / ○ Désactivé (mode local)"

### Test manuel rapide
```powershell
# Côté serveur central
curl -H "X-Master-Api-Key: test123" https://central.kasoft.ma/api/master/info

# Côté client
curl -X POST -H "X-DWH-Code: SG" http://127.0.0.1:8084/api/updates/pull/builder
```

---

## Checklist avant release

- [ ] `build_protected.bat` terminé sans erreur
- [ ] `npm run build` terminé sans erreur
- [ ] `dist_client/` et `dist/` à jour (vérifier les dates)
- [ ] `build_installer.bat` : étape [6/7] copie bien les deux dossiers
- [ ] Taille finale `output\OptiBoard-Setup-1.0.0.exe` ≈ 109 MB
- [ ] Test install sur VM propre : service démarre, wizard s'affiche
- [ ] Wizard 4 étapes : test connexion OK, DWH créé, admin créé
- [ ] Vérifier `APP_DWH` : 10 colonnes présentes après setup
