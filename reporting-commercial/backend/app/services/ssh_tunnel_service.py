"""
Service de gestion des tunnels SSH par DWH.

Un tunnel SSH redirige le port SQL Server distant (1433) vers un port local,
permettant une connexion sécurisée sans exposer SQL Server à internet.

Architecture :
    OptiBoard (backend) ──SSH──▶ Serveur Sage ──localhost──▶ SQL Server
    localhost:{local_port}                                    :1433
"""
import logging
import threading
import io
from typing import Dict, Optional

logger = logging.getLogger("SSHTunnelService")

# Base port pour les tunnels (DWH 1 → 14431, DWH 2 → 14432, etc.)
BASE_LOCAL_PORT = 14430

_lock = threading.Lock()
_tunnels: Dict[str, object] = {}   # dwh_code → SSHTunnelForwarder
_ports:   Dict[str, int]    = {}   # dwh_code → local_port


def _next_port() -> int:
    used = set(_ports.values())
    port = BASE_LOCAL_PORT + 1
    while port in used:
        port += 1
    return port


def start_tunnel(dwh_code: str, ssh_config: dict) -> int:
    """
    Démarre (ou retourne) le tunnel SSH pour un DWH.

    ssh_config doit contenir :
        ssh_host       : str   – IP/hostname du serveur Sage
        ssh_port       : int   – port SSH (défaut 22)
        ssh_user       : str   – utilisateur SSH restreint
        ssh_private_key: str   – contenu de la clé privée PEM

    Retourne le port local sur lequel SQL Server est accessible.
    """
    from sshtunnel import SSHTunnelForwarder
    import paramiko

    with _lock:
        # Tunnel déjà actif ?
        if dwh_code in _tunnels:
            t = _tunnels[dwh_code]
            if t.is_active:
                return _ports[dwh_code]
            else:
                # Tunnel mort → nettoyer
                try:
                    t.stop()
                except Exception:
                    pass
                del _tunnels[dwh_code]
                del _ports[dwh_code]

        local_port = _next_port()

        # Charger la clé privée depuis le contenu PEM
        key_content = ssh_config["ssh_private_key"].strip()
        pkey = None
        for key_class in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
            try:
                pkey = key_class.from_private_key(io.StringIO(key_content))
                break
            except Exception:
                continue

        if pkey is None:
            raise ValueError("Clé SSH invalide ou format non supporté (ED25519/RSA/ECDSA)")

        tunnel = SSHTunnelForwarder(
            (ssh_config["ssh_host"], int(ssh_config.get("ssh_port", 22))),
            ssh_username=ssh_config["ssh_user"],
            ssh_pkey=pkey,
            remote_bind_address=("localhost", 1433),
            local_bind_address=("127.0.0.1", local_port),
            set_keepalive=30,
        )
        tunnel.start()

        _tunnels[dwh_code] = tunnel
        _ports[dwh_code]   = local_port
        logger.info(f"[SSH] Tunnel {dwh_code} démarré : 127.0.0.1:{local_port} → {ssh_config['ssh_host']}:1433")
        return local_port


def stop_tunnel(dwh_code: str) -> None:
    with _lock:
        if dwh_code in _tunnels:
            try:
                _tunnels[dwh_code].stop()
            except Exception:
                pass
            del _tunnels[dwh_code]
            del _ports[dwh_code]
            logger.info(f"[SSH] Tunnel {dwh_code} arrêté")


def stop_all() -> None:
    with _lock:
        for code, t in list(_tunnels.items()):
            try:
                t.stop()
            except Exception:
                pass
        _tunnels.clear()
        _ports.clear()
    logger.info("[SSH] Tous les tunnels arrêtés")


def get_status(dwh_code: str) -> dict:
    with _lock:
        if dwh_code not in _tunnels:
            return {"active": False}
        t = _tunnels[dwh_code]
        return {
            "active": t.is_active,
            "local_port": _ports.get(dwh_code),
        }


def get_tunnel_conn_str(dwh_code: str, ssh_config: dict, base: str, user: str, password: str) -> str:
    """
    Lance le tunnel si nécessaire et retourne une connection string
    pointant vers localhost:{local_port}.
    """
    local_port = start_tunnel(dwh_code, ssh_config)
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER=127.0.0.1,{local_port};"
        f"DATABASE={base};"
        f"UID={user};PWD={password};"
        "TrustServerCertificate=yes;"
    )
