"""
Générateur de clé SSH ED25519 pour tunnel OptiBoard → Sage
Usage : python generate_ssh_key.py
"""
import sys
import os

try:
    import paramiko
except ImportError:
    print("Installation de paramiko...")
    os.system(f"{sys.executable} -m pip install paramiko")
    import paramiko

import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption
)

# En mode exe PyInstaller → utiliser le répertoire courant (pas le dossier temp)
import sys
OUTPUT_DIR = os.getcwd() if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
KEY_FILE    = os.path.join(OUTPUT_DIR, "sage_tunnel_key")
PUBKEY_FILE = KEY_FILE + ".pub"
COMMENT     = "optiboard-sage-tunnel"


def generate():
    print("=" * 55)
    print("  Generateur de cle SSH ED25519 - OptiBoard Tunnel")
    print("=" * 55)

    # ── Générer ───────────────────────────────────────────────
    private_key = Ed25519PrivateKey.generate()
    public_key  = private_key.public_key()
    print("\n[OK] Cle ED25519 generee")

    # ── Sauvegarder clé privée (format OpenSSH PEM) ───────────
    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()
    ).decode()

    with open(KEY_FILE, "w", newline="\n") as f:
        f.write(private_pem)

    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass

    print(f"[->] Cle privee  : {KEY_FILE}")

    # ── Sauvegarder clé publique (format authorized_keys) ─────
    pub_raw  = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    # Format wire SSH : length-prefixed "ssh-ed25519" + raw key
    key_type = b"ssh-ed25519"
    def _pack(b): return len(b).to_bytes(4, "big") + b
    wire     = _pack(key_type) + _pack(pub_raw)
    pub_b64  = base64.b64encode(wire).decode()
    pub_line = f"ssh-ed25519 {pub_b64} {COMMENT}\n"

    with open(PUBKEY_FILE, "w", newline="\n") as f:
        f.write(pub_line)

    print(f"[->] Cle publique: {PUBKEY_FILE}")

    # ── Afficher les deux clés ────────────────────────────────
    print("\n" + "-" * 55)
    print("CLE PRIVEE - A coller dans OptiBoard (champ SSH) :")
    print("-" * 55)
    print(private_pem)

    print("-" * 55)
    print("CLE PUBLIQUE - A ajouter sur le serveur Sage :")
    print("-" * 55)
    print(pub_line)

    # ── Instructions de déploiement ───────────────────────────
    pub_line_stripped = pub_line.strip()
    print("-" * 55)
    print("DEPLOIEMENT SUR LE SERVEUR SAGE (Linux) :")
    print("-" * 55)
    print(f"""
  # 1. Créer l'utilisateur restreint (sans shell)
  useradd -r -s /bin/false sageTunnelUser
  mkdir -p /home/sageTunnelUser/.ssh
  chmod 700 /home/sageTunnelUser/.ssh

  # 2. Ajouter la clé publique avec restriction port-forwarding
  echo "restrict,port-forwarding {pub_line_stripped}" \\
       >> /home/sageTunnelUser/.ssh/authorized_keys
  chmod 600 /home/sageTunnelUser/.ssh/authorized_keys
  chown -R sageTunnelUser:sageTunnelUser /home/sageTunnelUser/.ssh

  # 3. Tester depuis le serveur OptiBoard
  ssh -i sage_tunnel_key -N -L 1434:localhost:1433 sageTunnelUser@<IP_SAGE>
""")

    print("-" * 55)
    print("Dans OptiBoard :")
    print("  * Hote SSH         : <IP ou hostname du serveur Sage>")
    print("  * Port SSH         : 22")
    print("  * Utilisateur SSH  : sageTunnelUser")
    print("  * Cle privee SSH   : coller le contenu de sage_tunnel_key")
    print("  * Serveur SQL DWH  : laisser  .  (tunnel redirige vers localhost:1433)")
    print("-" * 55)
    print("\n[OK] Termine.")


if __name__ == "__main__":
    generate()
