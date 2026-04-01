FROM mcr.microsoft.com/mssql/server:2022-developer

USER root

# Installer sqlcmd (mssql-tools18) + curl pour healthcheck
RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev curl && \
    ln -sf /opt/mssql-tools18/bin/sqlcmd /usr/local/bin/sqlcmd && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copier les scripts d'initialisation
COPY sqlserver/init/ /docker-init/

# Copier et autoriser l'entrypoint
COPY sqlserver/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER mssql

ENTRYPOINT ["/entrypoint.sh"]
