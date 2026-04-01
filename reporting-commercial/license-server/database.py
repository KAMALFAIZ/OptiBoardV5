"""Database layer pour le serveur de licences"""
import pyodbc
import logging
from config import get_settings

logger = logging.getLogger(__name__)


def get_connection():
    settings = get_settings()
    conn_str = (
        f"DRIVER={settings.DB_DRIVER};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE={settings.DB_NAME};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
        f"TrustServerCertificate=yes"
    )
    return pyodbc.connect(conn_str)


def init_database():
    """Cree les tables du serveur de licences si elles n'existent pas"""
    settings = get_settings()

    # D'abord se connecter au master pour creer la DB si necessaire
    try:
        conn_str = (
            f"DRIVER={settings.DB_DRIVER};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE=master;"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            f"TrustServerCertificate=yes"
        )
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(f"""
            IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{settings.DB_NAME}')
            CREATE DATABASE [{settings.DB_NAME}]
        """)
        conn.close()
        logger.info(f"[DB] Database {settings.DB_NAME} ready")
    except Exception as e:
        logger.error(f"[DB] Error creating database: {e}")

    # Creer les tables
    conn = get_connection()
    conn.autocommit = True
    cursor = conn.cursor()

    # Table des clients
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LIC_Clients' AND xtype='U')
        CREATE TABLE LIC_Clients (
            id INT IDENTITY(1,1) PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name NVARCHAR(200) NOT NULL,
            email NVARCHAR(200),
            phone NVARCHAR(50),
            address NVARCHAR(500),
            contact_name NVARCHAR(200),
            notes NVARCHAR(MAX),
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE()
        )
    """)

    # Table des licences
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LIC_Licenses' AND xtype='U')
        CREATE TABLE LIC_Licenses (
            id INT IDENTITY(1,1) PRIMARY KEY,
            license_key VARCHAR(2000) UNIQUE NOT NULL,
            client_id INT NOT NULL,
            [plan] VARCHAR(30) DEFAULT 'standard',
            max_users INT DEFAULT 5,
            max_dwh INT DEFAULT 1,
            features NVARCHAR(MAX),
            machine_id VARCHAR(64) NULL,
            expiry_date DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT 'valid',
            activated_at DATETIME NULL,
            last_check DATETIME NULL,
            check_count INT DEFAULT 0,
            hostname NVARCHAR(200) NULL,
            ip_address VARCHAR(50) NULL,
            app_version VARCHAR(20) NULL,
            deployment_mode VARCHAR(20) DEFAULT 'on-premise',
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE(),
            date_modification DATETIME DEFAULT GETDATE(),
            CONSTRAINT FK_LIC_Client FOREIGN KEY (client_id) REFERENCES LIC_Clients(id)
        )
    """)

    # Table des logs de validation
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LIC_Validation_Log' AND xtype='U')
        CREATE TABLE LIC_Validation_Log (
            id BIGINT IDENTITY(1,1) PRIMARY KEY,
            license_id INT NULL,
            action VARCHAR(30) NOT NULL,
            machine_id VARCHAR(64),
            ip_address VARCHAR(50),
            hostname NVARCHAR(200),
            app_version VARCHAR(20),
            status VARCHAR(20),
            message NVARCHAR(MAX),
            date_action DATETIME DEFAULT GETDATE()
        )
    """)

    # Ajouter deployment_mode si la table existe deja sans cette colonne
    try:
        cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM sys.columns
                WHERE object_id = OBJECT_ID('LIC_Licenses') AND name = 'deployment_mode'
            )
            ALTER TABLE LIC_Licenses ADD deployment_mode VARCHAR(20) DEFAULT 'on-premise'
        """)
    except Exception as e:
        logger.warning(f"[DB] Note: {e}")

    # Index
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_LIC_Licenses_key')
            CREATE INDEX IX_LIC_Licenses_key ON LIC_Licenses(license_key);
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_LIC_Licenses_client')
            CREATE INDEX IX_LIC_Licenses_client ON LIC_Licenses(client_id);
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_LIC_Licenses_status')
            CREATE INDEX IX_LIC_Licenses_status ON LIC_Licenses(status);
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_LIC_Log_date')
            CREATE INDEX IX_LIC_Log_date ON LIC_Validation_Log(date_action);
    """)

    conn.close()
    logger.info("[DB] License tables initialized")
