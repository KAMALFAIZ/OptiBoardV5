#!/bin/bash
# ============================================================
# OptiBoard v5 — Premier setup du serveur de production
# Exécuter UNE SEULE FOIS sur le nouveau serveur (Ubuntu/Debian)
# Usage : sudo bash server-setup.sh
# ============================================================

set -e

echo "======================================"
echo " OptiBoard — Setup Serveur Production "
echo "======================================"

# 1. Mise à jour système
apt-get update && apt-get upgrade -y

# 2. Dépendances de base
apt-get install -y \
    curl git unzip ufw \
    ca-certificates gnupg

# 3. Installer Docker
if ! command -v docker &> /dev/null; then
    echo "→ Installation Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installé"
else
    echo "✅ Docker déjà installé"
fi

# 4. Créer répertoire projet
mkdir -p /opt/optiboard/{nginx/ssl,logs}
chown -R $SUDO_USER:$SUDO_USER /opt/optiboard 2>/dev/null || true

# 5. Cloner le repo GitHub (adapter l'URL)
GITHUB_REPO="https://github.com/KAMALFAIZ/OptiBoardV5.git"
if [ ! -d "/opt/optiboard/.git" ]; then
    echo "→ Clonage du repo..."
    git clone "$GITHUB_REPO" /opt/optiboard
    echo "✅ Repo cloné"
else
    echo "✅ Repo déjà présent"
fi

# 6. Créer le fichier .env depuis l'exemple
if [ ! -f "/opt/optiboard/.env" ]; then
    cp /opt/optiboard/.env.production.example /opt/optiboard/.env
    echo ""
    echo "⚠️  IMPORTANT : Editer /opt/optiboard/.env avec tes vraies valeurs !"
    echo "   nano /opt/optiboard/.env"
fi

# 7. Firewall — ouvrir ports nécessaires
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "✅ Firewall configuré"

echo ""
echo "======================================"
echo " Setup terminé !"
echo " Prochaines étapes :"
echo "   1. Editer /opt/optiboard/.env"
echo "   2. Copier tes certificats SSL dans /opt/optiboard/nginx/ssl/"
echo "   3. Configurer les GitHub Secrets (voir DEPLOYMENT.md)"
echo "   4. Pusher sur main → déploiement automatique"
echo "======================================"
