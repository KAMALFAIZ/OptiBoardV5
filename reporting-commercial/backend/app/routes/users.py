"""Routes pour la gestion des utilisateurs, societes et DWH"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..database_unified import execute_central as execute_query, central_cursor as get_db_cursor, execute_client, write_client, client_manager
import hashlib
import secrets
import pyodbc

logger = logging.getLogger("UsersAdmin")

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Pages autorisées par rôle pour les utilisateurs de bases client (OptiBoard_XXX).
# Ces listes sont déterministes : elles ne dépendent JAMAIS d'enregistrements
# APP_UserPages qui peuvent être orphelins ou corrompus.
CLIENT_PAGES_BY_ROLE = {
    "user":         ["dashboard", "ventes", "stocks", "recouvrement"],
    "admin_client": ["dashboard", "ventes", "stocks", "recouvrement", "admin", "etl_admin", "settings", "client_users", "client_dwh"],
    "readonly":     ["dashboard", "ventes", "stocks"],
}


# Schemas Pydantic
class SocieteCreate(BaseModel):
    """Schema pour creer une societe/DWH Client"""
    code: str
    nom: str
    serveur: str
    base_donnees: str
    username: str
    password: str
    description: Optional[str] = None
    actif: bool = True


class SocieteUpdate(BaseModel):
    """Schema pour mettre a jour une societe/DWH Client"""
    nom: Optional[str] = None
    serveur: Optional[str] = None
    base_donnees: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None
    actif: Optional[bool] = None


# Note: Les schemas DWHCreate et DWHUpdate sont remplaces par SocieteCreate et SocieteUpdate
# car Societe = DWH Client dans la nouvelle architecture


class UserCreate(BaseModel):
    """Schema pour creer un utilisateur"""
    username: str
    password: str
    nom: str
    prenom: str
    email: Optional[str] = None
    role: str = "user"  # superadmin, admin, user, readonly
    dwh_autorises: List[str] = []  # Liste des codes DWH accessibles
    societes: List[str] = []  # Liste des codes societes format "DWH_CODE:SOCIETE_CODE"
    pages_autorisees: List[str] = []  # dashboard, ventes, stocks, recouvrement, admin


class UserUpdate(BaseModel):
    """Schema pour mettre a jour un utilisateur"""
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None
    dwh_autorises: Optional[List[str]] = None  # Liste des codes DWH accessibles
    societes: Optional[List[str]] = None  # Liste des codes societes format "DWH_CODE:SOCIETE_CODE"
    pages_autorisees: Optional[List[str]] = None


class UserLogin(BaseModel):
    username: str
    password: str
    dwh_code: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_tables():
    """Initialise les tables si elles n'existent pas et migre l'ancienne structure"""
    queries = [
        # ===================== TABLE APP_Societes (= DWH Clients) =====================
        # Creer la nouvelle structure si la table n'existe pas
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        CREATE TABLE APP_Societes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            nom NVARCHAR(200) NOT NULL,
            serveur VARCHAR(200) NOT NULL,
            base_donnees VARCHAR(100) NOT NULL,
            username VARCHAR(100) NOT NULL,
            password VARCHAR(200) NOT NULL,
            description NVARCHAR(500),
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE()
        )
        """,
        # Migration: Ajouter colonne username si elle n'existe pas
        """
        IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        AND NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='APP_Societes' AND COLUMN_NAME='username')
        ALTER TABLE APP_Societes ADD username VARCHAR(100) NULL
        """,
        # Migration: Ajouter colonne password si elle n'existe pas
        """
        IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        AND NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='APP_Societes' AND COLUMN_NAME='password')
        ALTER TABLE APP_Societes ADD password VARCHAR(200) NULL
        """,
        # Migration: Ajouter colonne description si elle n'existe pas
        """
        IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        AND NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='APP_Societes' AND COLUMN_NAME='description')
        ALTER TABLE APP_Societes ADD description NVARCHAR(500) NULL
        """,
        # Migration: S'assurer que serveur n'est pas NULL
        """
        IF EXISTS (SELECT * FROM sysobjects WHERE name='APP_Societes' AND xtype='U')
        UPDATE APP_Societes SET serveur = '.' WHERE serveur IS NULL OR serveur = ''
        """,
        # ===================== TABLE APP_Users =====================
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_Users' AND xtype='U')
        CREATE TABLE APP_Users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(64) NOT NULL,
            nom NVARCHAR(100) NOT NULL,
            prenom NVARCHAR(100) NOT NULL,
            email VARCHAR(200),
            role VARCHAR(20) DEFAULT 'user',
            actif BIT DEFAULT 1,
            date_creation DATETIME DEFAULT GETDATE(),
            derniere_connexion DATETIME
        )
        """,
        # ===================== TABLE APP_UserSocietes (User <-> DWH liaison) =====================
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserSocietes' AND xtype='U')
        CREATE TABLE APP_UserSocietes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            societe_code VARCHAR(50) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
        """,
        # ===================== TABLE APP_UserPages =====================
        """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APP_UserPages' AND xtype='U')
        CREATE TABLE APP_UserPages (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NOT NULL,
            page_code VARCHAR(50) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES APP_Users(id) ON DELETE CASCADE
        )
        """
        # Note: APP_DWH et APP_UserDWH sont deprecies - utiliser APP_Societes et APP_UserSocietes
    ]

    try:
        with get_db_cursor() as cursor:
            for query in queries:
                cursor.execute(query)
        return True
    except Exception as e:
        print(f"Erreur init tables: {e}")
        return False


# ===================== SOCIETES (= DWH Clients) =====================

def get_societe_connection_string(societe: dict) -> str:
    """Construit la chaine de connexion pour une societe/DWH"""
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={societe['serveur']};"
        f"DATABASE={societe['base_donnees']};"
        f"UID={societe['username']};"
        f"PWD={societe['password']};"
        f"TrustServerCertificate=yes"
    )


@router.get("/societes")
async def get_societes():
    """Liste toutes les societes/DWH (sans les mots de passe)"""
    try:
        init_tables()
        results = execute_query(
            """SELECT id, code, nom, serveur, base_donnees, username,
                      description, actif, date_creation
               FROM APP_Societes ORDER BY nom""",
            use_cache=False
        )
        return {"success": True, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.get("/societes/{code}")
async def get_societe(code: str):
    """Recupere une societe par son code (sans mot de passe)"""
    try:
        results = execute_query(
            """SELECT id, code, nom, serveur, base_donnees, username,
                      description, actif, date_creation
               FROM APP_Societes WHERE code = ?""",
            (code,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail=f"Societe '{code}' non trouvee")
        return {"success": True, "data": results[0]}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": None}


@router.post("/societes")
async def create_societe(societe: SocieteCreate):
    """Cree une nouvelle societe/DWH Client"""
    try:
        init_tables()
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO APP_Societes
                   (code, nom, serveur, base_donnees, username, password, description, actif)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (societe.code, societe.nom, societe.serveur, societe.base_donnees,
                 societe.username, societe.password, societe.description, societe.actif)
            )
        return {"success": True, "message": "Societe creee avec succes"}
    except Exception as e:
        import traceback
        print(f"Erreur creation societe: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/societes/schema")
async def get_societes_schema():
    """Retourne la structure de la table APP_Societes (pour debug)"""
    try:
        init_tables()
        results = execute_query(
            """SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
               FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_NAME = 'APP_Societes'
               ORDER BY ORDINAL_POSITION""",
            use_cache=False
        )
        return {"success": True, "columns": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/societes/migrate")
async def migrate_societes_table():
    """Migration: Recree la table APP_Societes avec la nouvelle structure"""
    try:
        with get_db_cursor() as cursor:
            # Etape 1: Verifier si la table existe
            cursor.execute("SELECT COUNT(*) FROM sysobjects WHERE name='APP_Societes' AND xtype='U'")
            table_exists = cursor.fetchone()[0] > 0

            if table_exists:
                # Etape 2: Sauvegarder dans table temporaire
                cursor.execute("SELECT * INTO APP_Societes_Backup FROM APP_Societes")

                # Etape 3: Supprimer l'ancienne table
                cursor.execute("DROP TABLE APP_Societes")

            # Etape 4: Creer la nouvelle table
            cursor.execute("""
                CREATE TABLE APP_Societes (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    nom NVARCHAR(200) NOT NULL,
                    serveur VARCHAR(200) NOT NULL DEFAULT '.',
                    base_donnees VARCHAR(100) NOT NULL,
                    username VARCHAR(100) NOT NULL DEFAULT 'sa',
                    password VARCHAR(200) NOT NULL DEFAULT '',
                    description NVARCHAR(500),
                    actif BIT DEFAULT 1,
                    date_creation DATETIME DEFAULT GETDATE()
                )
            """)

            if table_exists:
                # Etape 5: Restaurer les donnees
                # Verifier si l'ancienne table avait username
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME='APP_Societes_Backup' AND COLUMN_NAME='username'
                """)
                has_username = cursor.fetchone()[0] > 0

                if has_username:
                    cursor.execute("""
                        INSERT INTO APP_Societes (code, nom, serveur, base_donnees, username, password, description, actif)
                        SELECT code, nom, ISNULL(serveur, '.'), base_donnees,
                               ISNULL(username, 'sa'), ISNULL(password, ''),
                               CASE WHEN COL_LENGTH('APP_Societes_Backup', 'description') IS NOT NULL
                                    THEN description ELSE NULL END,
                               ISNULL(actif, 1)
                        FROM APP_Societes_Backup
                    """)
                else:
                    cursor.execute("""
                        INSERT INTO APP_Societes (code, nom, serveur, base_donnees, username, password, actif)
                        SELECT code, nom, ISNULL(serveur, '.'), base_donnees, 'sa', '', ISNULL(actif, 1)
                        FROM APP_Societes_Backup
                    """)

                # Etape 6: Supprimer la backup
                cursor.execute("DROP TABLE APP_Societes_Backup")

        return {"success": True, "message": "Table APP_Societes migree avec succes"}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}


@router.put("/societes/{code}")
async def update_societe(code: str, societe: SocieteUpdate):
    """Met a jour une societe/DWH"""
    try:
        updates = []
        params = []

        if societe.nom is not None:
            updates.append("nom = ?")
            params.append(societe.nom)
        if societe.serveur is not None:
            updates.append("serveur = ?")
            params.append(societe.serveur)
        if societe.base_donnees is not None:
            updates.append("base_donnees = ?")
            params.append(societe.base_donnees)
        if societe.username is not None:
            updates.append("username = ?")
            params.append(societe.username)
        if societe.password is not None:
            updates.append("password = ?")
            params.append(societe.password)
        if societe.description is not None:
            updates.append("description = ?")
            params.append(societe.description)
        if societe.actif is not None:
            updates.append("actif = ?")
            params.append(societe.actif)

        if not updates:
            return {"success": False, "message": "Aucune modification"}

        params.append(code)

        with get_db_cursor() as cursor:
            cursor.execute(
                f"UPDATE APP_Societes SET {', '.join(updates)} WHERE code = ?",
                tuple(params)
            )
        return {"success": True, "message": "Societe mise a jour"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/societes/{code}")
async def delete_societe(code: str):
    """Supprime une societe/DWH"""
    try:
        with get_db_cursor() as cursor:
            # Supprimer d'abord les liaisons utilisateurs
            cursor.execute("DELETE FROM APP_UserSocietes WHERE societe_code = ?", (code,))
            cursor.execute("DELETE FROM APP_Societes WHERE code = ?", (code,))
        return {"success": True, "message": "Societe supprimee"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/societes/{code}/test")
async def test_societe_connection(code: str):
    """Teste la connexion a une societe/DWH"""
    try:
        # Recuperer les infos de la societe avec le mot de passe
        results = execute_query(
            "SELECT * FROM APP_Societes WHERE code = ?",
            (code,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail=f"Societe '{code}' non trouvee")

        societe = results[0]
        conn_string = get_societe_connection_string(societe)

        # Tester la connexion
        conn = pyodbc.connect(conn_string, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": f"Connexion reussie a {societe['base_donnees']} sur {societe['serveur']}"
        }
    except pyodbc.Error as e:
        return {"success": False, "error": f"Erreur de connexion: {str(e)}"}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/societes/{code}/tables")
async def get_societe_tables(code: str):
    """Liste les tables disponibles dans une societe/DWH"""
    try:
        results = execute_query(
            "SELECT * FROM APP_Societes WHERE code = ?",
            (code,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail=f"Societe '{code}' non trouvee")

        societe = results[0]
        conn_string = get_societe_connection_string(societe)

        conn = pyodbc.connect(conn_string, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [{"TABLE_NAME": row[0], "TABLE_TYPE": row[1]} for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return {"success": True, "societe": code, "data": tables}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/societes/{code}/query")
async def execute_societe_query(code: str, request: dict):
    """Execute une requete SQL sur une societe/DWH specifique"""
    try:
        query = request.get("query", "")
        params = request.get("params", [])

        if not query:
            raise HTTPException(status_code=400, detail="Query requise")

        # Recuperer les infos de la societe
        results = execute_query(
            "SELECT * FROM APP_Societes WHERE code = ?",
            (code,),
            use_cache=False
        )
        if not results:
            raise HTTPException(status_code=404, detail=f"Societe '{code}' non trouvee")

        societe = results[0]
        conn_string = get_societe_connection_string(societe)

        conn = pyodbc.connect(conn_string, timeout=30)
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        columns = [column[0] for column in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "societe": code,
            "row_count": len(data),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


# ===================== DWH (Data Warehouse) =====================

# ===================== ROUTES DWH (ALIAS VERS SOCIETES) =====================
# Ces routes sont maintenues pour la retrocompatibilite
# Societe = DWH Client dans la nouvelle architecture

@router.get("/dwh")
async def get_dwh_list():
    """Liste tous les DWH disponibles depuis APP_DWH"""
    print("[DEBUG] get_dwh_list CALLED")
    try:
        dwh_list = execute_query(
            """
            SELECT code, nom, serveur_dwh, base_dwh, actif, ISNULL(is_demo,0) AS is_demo
            FROM APP_DWH
            WHERE actif = 1
            ORDER BY nom
            """,
            use_cache=False
        )
        return {"success": True, "data": dwh_list}
    except Exception as e:
        print(f"[ERROR] get_dwh_list: {e}")
        # Fallback sans is_demo
        try:
            dwh_list = execute_query("SELECT code, nom, serveur_dwh, base_dwh, actif FROM APP_DWH WHERE actif = 1 ORDER BY nom", use_cache=False)
            for r in dwh_list:
                r['is_demo'] = r.get('code', '') == 'KA'
            return {"success": True, "data": dwh_list}
        except Exception:
            return {"success": True, "data": []}


@router.get("/dwh/{code}")
async def get_dwh(code: str):
    """Recupere un DWH par son code (alias vers societes)"""
    return await get_societe(code)


@router.post("/dwh")
async def create_dwh(dwh: SocieteCreate):
    """Cree un nouveau DWH (alias vers societes)"""
    return await create_societe(dwh)


@router.put("/dwh/{code}")
async def update_dwh(code: str, dwh: SocieteUpdate):
    """Met a jour un DWH (alias vers societes)"""
    return await update_societe(code, dwh)


@router.delete("/dwh/{code}")
async def delete_dwh(code: str):
    """Supprime un DWH (alias vers societes)"""
    return await delete_societe(code)


@router.post("/dwh/{code}/test")
async def test_dwh_connection(code: str):
    """Teste la connexion a un DWH (alias vers societes)"""
    return await test_societe_connection(code)


# ===================== USERS =====================

@router.get("/users")
async def get_users():
    """Liste tous les utilisateurs avec leurs societes, pages et DWH"""
    try:
        init_tables()
        users = execute_query(
            """SELECT id, username, nom, prenom, email, role_global as role, actif,
                      date_creation, derniere_connexion
               FROM APP_Users ORDER BY nom, prenom""",
            use_cache=False
        )

        # Ajouter dwh_autorises, societes et pages pour chaque user
        for user in users:
            # DWH autorises
            dwh = execute_query(
                "SELECT dwh_code FROM APP_User_DWH WHERE user_id = ?",
                (user['id'],),
                use_cache=False
            )
            user['dwh_autorises'] = [d['dwh_code'] for d in dwh]

            # Societes (format DWH:SOCIETE)
            societes = execute_query(
                "SELECT dwh_code, societe_code FROM APP_User_Societes WHERE user_id = ?",
                (user['id'],),
                use_cache=False
            )
            user['societes'] = [f"{s['dwh_code']}:{s['societe_code']}" for s in societes]

            # Pages autorisees
            pages = execute_query(
                "SELECT page_code FROM APP_UserPages WHERE user_id = ?",
                (user['id'],),
                use_cache=False
            )
            user['pages_autorisees'] = [p['page_code'] for p in pages]

        return {"success": True, "data": users}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@router.post("/users")
async def create_user(user: UserCreate):
    """Cree un nouvel utilisateur"""
    try:
        init_tables()
        password_hash = hash_password(user.password)

        with get_db_cursor() as cursor:
            # Creer l'utilisateur
            cursor.execute(
                """INSERT INTO APP_Users (username, password_hash, nom, prenom, email, role_global)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user.username, password_hash, user.nom, user.prenom, user.email, user.role)
            )

            # Recuperer l'ID
            cursor.execute("SELECT @@IDENTITY AS id")
            user_id = cursor.fetchone()[0]

            # Ajouter les DWH autorises
            for dwh_code in user.dwh_autorises:
                cursor.execute(
                    "INSERT INTO APP_User_DWH (user_id, dwh_code) VALUES (?, ?)",
                    (user_id, dwh_code)
                )

            # Ajouter les societes (format "DWH_CODE:SOCIETE_CODE")
            for societe in user.societes:
                parts = societe.split(':')
                if len(parts) == 2:
                    cursor.execute(
                        "INSERT INTO APP_User_Societes (user_id, dwh_code, societe_code) VALUES (?, ?, ?)",
                        (user_id, parts[0], parts[1])
                    )

            # Ajouter les pages autorisees
            for page_code in user.pages_autorisees:
                cursor.execute(
                    "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                    (user_id, page_code)
                )

        return {"success": True, "message": "Utilisateur cree", "id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{user_id}")
async def update_user(user_id: int, user: UserUpdate):
    """Met a jour un utilisateur"""
    try:
        updates = []
        params = []

        if user.nom is not None:
            updates.append("nom = ?")
            params.append(user.nom)
        if user.prenom is not None:
            updates.append("prenom = ?")
            params.append(user.prenom)
        if user.email is not None:
            updates.append("email = ?")
            params.append(user.email)
        if user.role is not None:
            updates.append("role_global = ?")
            params.append(user.role)
        if user.actif is not None:
            updates.append("actif = ?")
            params.append(user.actif)

        with get_db_cursor() as cursor:
            # Update user info
            if updates:
                params.append(user_id)
                cursor.execute(
                    f"UPDATE APP_Users SET {', '.join(updates)} WHERE id = ?",
                    tuple(params)
                )

            # Update DWH autorises
            if user.dwh_autorises is not None:
                cursor.execute("DELETE FROM APP_User_DWH WHERE user_id = ?", (user_id,))
                for dwh_code in user.dwh_autorises:
                    cursor.execute(
                        "INSERT INTO APP_User_DWH (user_id, dwh_code) VALUES (?, ?)",
                        (user_id, dwh_code)
                    )

            # Update societes (format "DWH_CODE:SOCIETE_CODE")
            if user.societes is not None:
                cursor.execute("DELETE FROM APP_User_Societes WHERE user_id = ?", (user_id,))
                for societe in user.societes:
                    parts = societe.split(':')
                    if len(parts) == 2:
                        cursor.execute(
                            "INSERT INTO APP_User_Societes (user_id, dwh_code, societe_code) VALUES (?, ?, ?)",
                            (user_id, parts[0], parts[1])
                        )

            # Update pages autorisees
            if user.pages_autorisees is not None:
                cursor.execute("DELETE FROM APP_UserPages WHERE user_id = ?", (user_id,))
                for page_code in user.pages_autorisees:
                    cursor.execute(
                        "INSERT INTO APP_UserPages (user_id, page_code) VALUES (?, ?)",
                        (user_id, page_code)
                    )

        return {"success": True, "message": "Utilisateur mis a jour"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Supprime un utilisateur"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM APP_Users WHERE id = ?", (user_id,))
        return {"success": True, "message": "Utilisateur supprime"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/password")
async def change_password(user_id: int, data: PasswordChange):
    """Change le mot de passe d'un utilisateur"""
    try:
        old_hash = hash_password(data.old_password)
        new_hash = hash_password(data.new_password)

        # Verifier l'ancien mot de passe
        result = execute_query(
            "SELECT id FROM APP_Users WHERE id = ? AND password_hash = ?",
            (user_id, old_hash),
            use_cache=False
        )

        if not result:
            raise HTTPException(status_code=401, detail="Mot de passe incorrect")

        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE APP_Users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )

        return {"success": True, "message": "Mot de passe modifie"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: int):
    """Reset le mot de passe (admin only) - nouveau mdp = username"""
    try:
        # Recuperer le username
        user = execute_query(
            "SELECT username FROM APP_Users WHERE id = ?",
            (user_id,),
            use_cache=False
        )

        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouve")

        new_hash = hash_password(user[0]['username'])

        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE APP_Users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )

        return {"success": True, "message": f"Mot de passe reinitialise (nouveau: {user[0]['username']})"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== AUTH =====================

@router.post("/login")
async def login(credentials: UserLogin):
    """Authentification utilisateur (central + client DB si dwh_code fourni)"""
    try:
        password_hash = hash_password(credentials.password)
        user = None
        from_client_db = False

        # ── Étape 1 : chercher dans la base client si dwh_code fourni ──────
        if credentials.dwh_code and client_manager.has_client_db(credentials.dwh_code):
            try:
                # Vérifier d'abord si l'utilisateur existe avec password_hash NULL (1er login)
                client_rows_any = execute_client(
                    "SELECT id, username, password_hash, actif FROM APP_Users WHERE username = ? AND actif = 1",
                    (credentials.username,),
                    dwh_code=credentials.dwh_code,
                    use_cache=False,
                )
                if client_rows_any:
                    first_user = dict(client_rows_any[0])
                    if first_user.get("password_hash") is None:
                        return {
                            "success": True,
                            "message": "Premier login — création du mot de passe requise",
                            "must_change_password": True,
                            "first_login_user_id": first_user["id"],
                            "user": None,
                            "token": None,
                        }
                client_rows = execute_client(
                    "SELECT id, username, nom, prenom, email, role_dwh as role, actif FROM APP_Users WHERE username = ? AND password_hash = ? AND actif = 1",
                    (credentials.username, password_hash),
                    dwh_code=credentials.dwh_code,
                    use_cache=False,
                )
                if client_rows:
                    user = dict(client_rows[0])
                    from_client_db = True
                    # Mise à jour derniere connexion dans base client
                    try:
                        write_client(
                            "UPDATE APP_Users SET derniere_connexion = GETDATE() WHERE id = ?",
                            (user['id'],),
                            dwh_code=credentials.dwh_code,
                        )
                    except Exception:
                        pass
            except Exception as client_db_err:
                # La base client est inaccessible (ex: typo dans base_optiboard, serveur down)
                # → on logue l'erreur technique et on retourne un message lisible
                logger.error(
                    f"[LOGIN] Connexion impossible à la base client '{credentials.dwh_code}': {client_db_err}"
                )
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"La base de données du client '{credentials.dwh_code}' est inaccessible. "
                        f"Contactez l'administrateur système. "
                        f"[{type(client_db_err).__name__}]"
                    )
                )

        # ── Étape 2 : base centrale (superadmin uniquement, sans dwh_code) ────
        if user is None:
            if credentials.dwh_code:
                # dwh_code fourni mais user absent/invalide dans la base client
                # → accès refusé, pas de repli sur OptiBoard_SaaS (isolation tenant)
                raise HTTPException(status_code=401, detail="Identifiants incorrects")
            central_rows = execute_query(
                "SELECT id, username, nom, prenom, email, role_global as role, actif FROM APP_Users WHERE username = ? AND password_hash = ? AND actif = 1",
                (credentials.username, password_hash),
                use_cache=False
            )
            if not central_rows:
                raise HTTPException(status_code=401, detail="Identifiants incorrects")
            user = dict(central_rows[0])
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE APP_Users SET derniere_connexion = GETDATE() WHERE id = ?",
                    (user['id'],)
                )

        # ── Étape 3 : pages & societes ──────────────────────────────────────
        if from_client_db:
            # Pages déterminées par role_dwh — jamais lues depuis APP_UserPages
            # (évite les enregistrements orphelins qui accordent des droits non voulus)
            role = user.get('role', 'user')
            user['pages_autorisees'] = CLIENT_PAGES_BY_ROLE.get(role, CLIENT_PAGES_BY_ROLE['user'])
            user['societes'] = []
            user['societes_list'] = []
            user['dwh_code'] = credentials.dwh_code
        else:
            societes = execute_query(
                "SELECT societe_code FROM APP_UserSocietes WHERE user_id = ?",
                (user['id'],),
                use_cache=False
            )
            user['societes'] = [s['societe_code'] for s in societes]

            pages = execute_query(
                "SELECT page_code FROM APP_UserPages WHERE user_id = ?",
                (user['id'],),
                use_cache=False
            )
            user['pages_autorisees'] = [p['page_code'] for p in pages]

            if user['societes']:
                placeholders = ','.join(['?' for _ in user['societes']])
                societe_details = execute_query(
                    f"""SELECT code, nom, serveur, base_donnees, description
                        FROM APP_Societes WHERE code IN ({placeholders}) AND actif = 1""",
                    tuple(user['societes']),
                    use_cache=False
                )
                user['societes_list'] = societe_details
            else:
                user['societes_list'] = []

        token = secrets.token_hex(32)
        has_client_db = bool(
            credentials.dwh_code and client_manager.has_client_db(credentials.dwh_code)
        )
        user['from_client_db'] = from_client_db
        return {"success": True, "user": user, "token": token, "has_client_db": has_client_db}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pages")
async def get_available_pages():
    """Liste les pages disponibles"""
    return {
        "success": True,
        "data": [
            {"code": "dashboard", "nom": "Dashboard", "description": "Tableau de bord principal"},
            {"code": "ventes", "nom": "Ventes", "description": "Analyse des ventes"},
            {"code": "stocks", "nom": "Stocks", "description": "Gestion des stocks"},
            {"code": "recouvrement", "nom": "Recouvrement", "description": "Suivi recouvrement et DSO"},
            {"code": "admin", "nom": "Admin SQL", "description": "Administration SQL"},
            {"code": "users", "nom": "Gestion Utilisateurs", "description": "Administration des utilisateurs"}
        ]
    }


# ===================== DWH QUERY EXECUTION (ALIAS VERS SOCIETES) =====================

@router.get("/dwh/{code}/tables")
async def get_dwh_tables(code: str):
    """Liste les tables d'un DWH (alias vers societes)"""
    return await get_societe_tables(code)


@router.post("/dwh/{code}/query")
async def execute_dwh_query_alias(code: str, request: dict):
    """Execute une requete sur un DWH (alias vers societes)"""
    return await execute_societe_query(code, request)
