# OptiBoard v5 — Guide de Déploiement

## Architecture

```
PC Local (dev)
     │
     │  git push origin main
     ▼
GitHub Repository
     │
     │  GitHub Actions CI/CD
     ▼
GitHub Container Registry (GHCR)
   optiboard-backend:latest
   optiboard-frontend:latest
     │
     │  SSH + docker compose pull
     ▼
Serveur de Production (Linux)
   ├── optiboard-backend  (FastAPI :8080)
   ├── optiboard-frontend (Nginx :80/:443)
   └── watchtower         (auto-update)
```

---

## 1. Initialisation du repo GitHub

```bash
# Sur ton PC local, dans D:\OptiBoard v5
cd "D:\OptiBoard v5"

git init
git add .
git commit -m "Initial commit"

# Créer le repo sur github.com, puis :
git remote add origin https://github.com/KAMALFAIZ/optiboard-v5.git
git branch -M main
git push -u origin main
```

---

## 2. Configuration des GitHub Secrets

Dans ton repo GitHub → **Settings → Secrets and variables → Actions**

| Secret | Description |
|--------|-------------|
| `PROD_HOST` | IP ou hostname du serveur (ex: `192.168.1.100`) |
| `PROD_USER` | Utilisateur SSH (ex: `ubuntu` ou `root`) |
| `PROD_SSH_KEY` | Clé SSH privée (contenu complet de `~/.ssh/id_rsa`) |
| `PROD_SSH_PORT` | Port SSH (défaut: `22`) |
| `PROD_API_URL` | URL publique de l'API (ex: `https://api.optiboard.com`) |

### Générer une clé SSH dédiée au déploiement

```bash
# Sur ton PC local
ssh-keygen -t ed25519 -C "optiboard-deploy" -f ~/.ssh/optiboard_deploy

# Copier la clé publique sur le serveur
ssh-copy-id -i ~/.ssh/optiboard_deploy.pub user@SERVEUR_IP

# Dans GitHub Secrets → PROD_SSH_KEY :
# coller le contenu de ~/.ssh/optiboard_deploy (clé PRIVÉE)
cat ~/.ssh/optiboard_deploy
```

---

## 3. Premier setup du serveur

```bash
# Se connecter au serveur
ssh user@SERVEUR_IP

# Télécharger et exécuter le script de setup
curl -o setup.sh https://raw.githubusercontent.com/KAMALFAIZ/optiboard-v5/main/scripts/server-setup.sh
sudo bash setup.sh
```

### Configurer les variables d'environnement

```bash
nano /opt/optiboard/.env
# Remplir avec les vraies valeurs (voir .env.production.example)
```

### Copier les certificats SSL (HTTPS)

```bash
# Option A : Let's Encrypt (recommandé, gratuit)
apt-get install -y certbot
certbot certonly --standalone -d votre-domaine.com
cp /etc/letsencrypt/live/votre-domaine.com/fullchain.pem /opt/optiboard/nginx/ssl/
cp /etc/letsencrypt/live/votre-domaine.com/privkey.pem   /opt/optiboard/nginx/ssl/

# Option B : Sans SSL (dev/test uniquement, HTTP seulement)
# Retirer le bloc HTTPS du nginx.prod.conf et garder uniquement port 80
```

---

## 4. Déploiement automatique

Après configuration :

```bash
# Sur ton PC local — n'importe quelle modification
git add .
git commit -m "feat: nouvelle fonctionnalité"
git push origin main

# → GitHub Actions se déclenche automatiquement :
#   1. Build Docker images
#   2. Push vers GHCR
#   3. SSH sur le serveur
#   4. docker compose pull + up -d
```

Suivre l'avancement : **GitHub → Actions tab**

---

## 5. Déploiement manuel (si besoin)

```bash
ssh user@SERVEUR_IP
cd /opt/optiboard
bash scripts/deploy.sh
```

---

## 6. Commandes utiles sur le serveur

```bash
# Voir l'état des services
docker compose -f docker-compose.prod.yml ps

# Voir les logs en temps réel
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Redémarrer un service
docker compose -f docker-compose.prod.yml restart backend

# Mettre à jour manuellement
docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d

# Rollback vers une version précédente
docker compose -f docker-compose.prod.yml stop backend
docker run -d --name optiboard-backend ghcr.io/KAMALFAIZ/optiboard-backend:SHA_DU_COMMIT
```

---

## 7. Structure des branches Git

| Branche | Rôle | Déploiement |
|---------|------|-------------|
| `main` | Code production stable | → Serveur prod automatique |
| `develop` | Intégration features | → Serveur staging (optionnel) |
| `feature/xxx` | Développement | Aucun |

```bash
# Workflow quotidien
git checkout -b feature/ma-fonctionnalite
# ... développer ...
git commit -m "feat: description"
git push origin feature/ma-fonctionnalite

# Merger dans develop pour tests
git checkout develop && git merge feature/ma-fonctionnalite

# Quand prêt pour prod
git checkout main && git merge develop
git push origin main   # → déploiement automatique !
```

---

## 8. Troubleshooting

**Les images ne se mettent pas à jour ?**
```bash
docker compose -f docker-compose.prod.yml pull --no-cache
```

**Le backend ne démarre pas ?**
```bash
docker compose -f docker-compose.prod.yml logs backend
# Vérifier les variables .env (DB_SERVER, DB_PASSWORD, etc.)
```

**Erreur de connexion SQL Server ?**
```bash
# Tester la connexion depuis le container
docker exec -it optiboard-backend python -c "import pyodbc; print(pyodbc.connect('...'))"
```
