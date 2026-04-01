#!/bin/bash
# ============================================================
# OptiBoard - SQL Server Entrypoint
# Lance SQL Server puis initialise les bases au 1er démarrage
# ============================================================

set -e

SQLCMD="/usr/local/bin/sqlcmd"
INIT_DIR="/docker-init"
INIT_FLAG="/var/opt/mssql/.optiboard_initialized"

# Démarrer SQL Server en arrière-plan
echo "[OptiBoard] Démarrage SQL Server Developer 2022..."
/opt/mssql/bin/sqlservr &
SQLPID=$!

# Attendre que SQL Server soit prêt (max 120 secondes)
echo "[OptiBoard] Attente disponibilité SQL Server..."
for i in $(seq 1 60); do
    if $SQLCMD -S localhost -U sa -P "$SA_PASSWORD" -Q "SELECT 1" > /dev/null 2>&1; then
        echo "[OptiBoard] SQL Server prêt (${i}x2s)."
        break
    fi
    if [ $i -eq 60 ]; then
        echo "[ERREUR] SQL Server non disponible après 120s. Abandon."
        kill $SQLPID
        exit 1
    fi
    sleep 2
done

# Initialisation une seule fois (flag fichier)
if [ ! -f "$INIT_FLAG" ]; then
    echo "[OptiBoard] Première initialisation des bases de données..."

    # Exécuter les scripts SQL dans l'ordre alphabétique
    for SCRIPT in $(ls $INIT_DIR/*.sql | sort); do
        echo "[OptiBoard] Exécution : $(basename $SCRIPT)"
        $SQLCMD -S localhost -U sa -P "$SA_PASSWORD" \
            -v DWH_CODE="$DWH_CODE" \
            -v DWH_DB_NAME="$DWH_DB_NAME" \
            -v APP_DB_NAME="$DB_NAME" \
            -i "$SCRIPT"
        if [ $? -ne 0 ]; then
            echo "[ERREUR] Échec de $(basename $SCRIPT). Abandon."
            kill $SQLPID
            exit 1
        fi
    done

    touch "$INIT_FLAG"
    echo "[OptiBoard] Initialisation terminée avec succès."
else
    echo "[OptiBoard] Bases déjà initialisées, démarrage normal."
fi

# Garder SQL Server en foreground
echo "[OptiBoard] SQL Server opérationnel. PID=$SQLPID"
wait $SQLPID
