"""
Genere le fichier agent_config_<CODE>.json pour chaque DWH.
Le fichier est chiffre AES-256-GCM avec la cle partagee de l'agent C#.
"""
import base64, os, json, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pyodbc

SERVER_URL = sys.argv[1] if len(sys.argv) > 1 else "http://kasoft.selfip.net:8084"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else r"D:\kasoft-platform\OptiBoard\agent_configs"
KEY = b"kasoft_optiboard_etl_key_2026!!!"  # 32 bytes — meme cle que l'agent C#

os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = pyodbc.connect('DRIVER={SQL Server};SERVER=kasoft.selfip.net;DATABASE=OptiBoard_SaaS;UID=sa;PWD=SQL@2019')
cur = conn.cursor()
cur.execute("SELECT code, nom FROM APP_DWH WHERE code IN (SELECT dwh_code FROM APP_ETL_Agents_Monitoring)")
dwhs = cur.fetchall()
conn.close()

aesgcm = AESGCM(KEY)
for code, nom in dwhs:
    payload = {"dwh_code": code, "server_url": SERVER_URL, "client_nom": nom or code}
    plaintext = json.dumps(payload, ensure_ascii=False).encode()
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    encrypted_b64 = base64.b64encode(nonce + ciphertext).decode()
    envelope = {"v": 1, "data": encrypted_b64}
    path = os.path.join(OUTPUT_DIR, f"agent_config_{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)
    print(f"[OK] {path}  (server={SERVER_URL}, dwh={code}, nom={nom})")

print(f"\nFichiers dans : {OUTPUT_DIR}")
