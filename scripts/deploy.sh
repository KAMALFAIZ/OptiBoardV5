#!/bin/bash
# ============================================================
# OptiBoard v5 — Script de déploiement manuel
# Usage : bash deploy.sh [tag]
# Exemple : bash deploy.sh latest
# ============================================================

set -e

TAG=${1:-latest}
COMPOSE_FILE="docker-compose.prod.yml"
APP_DIR="/opt/optiboard"

echo "🚀 Déploiement OptiBoard — tag: $TAG"
cd "$APP_DIR"

# Pull derniers fichiers de config depuis git
git pull origin main

# Mettre à jour le tag dans .env si fourni
if [ "$TAG" != "latest" ]; then
    sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$TAG/" .env
fi

# Pull les nouvelles images
docker compose -f "$COMPOSE_FILE" pull

# Redémarrer sans interruption
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Health check rapide
echo "⏳ Attente du démarrage..."
sleep 10
if curl -sf http://localhost:8080/api/docs > /dev/null; then
    echo "✅ Backend OK"
else
    echo "❌ Backend ne répond pas — vérifier les logs"
    docker compose -f "$COMPOSE_FILE" logs --tail=50 backend
    exit 1
fi

# Nettoyage images inutilisées
docker image prune -f

echo "✅ Déploiement terminé — $(date)"
