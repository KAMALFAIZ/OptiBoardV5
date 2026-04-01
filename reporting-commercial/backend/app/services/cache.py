"""Service de cache pour optimiser les requêtes lentes"""
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
import hashlib
import json


class QueryCache:
    """Cache simple avec expiration pour les résultats de requêtes SQL."""

    def __init__(self, default_ttl: int = 300):
        """
        Initialise le cache.

        Args:
            default_ttl: Durée de vie par défaut en secondes (5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0}

    def _make_key(self, query: str, params: Optional[Tuple] = None) -> str:
        """Crée une clé unique pour la requête."""
        key_data = f"{query}:{params}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        Récupère un résultat du cache s'il existe et n'est pas expiré.

        Returns:
            Les données en cache ou None si non trouvé/expiré
        """
        key = self._make_key(query, params)

        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry["expires_at"]:
                self.stats["hits"] += 1
                return entry["data"]
            else:
                # Expiré, on le supprime
                del self._cache[key]

        self.stats["misses"] += 1
        return None

    def set(self, query: str, params: Optional[Tuple], data: Any, ttl: Optional[int] = None) -> None:
        """
        Stocke un résultat dans le cache.

        Args:
            query: La requête SQL
            params: Les paramètres de la requête
            data: Les données à mettre en cache
            ttl: Durée de vie en secondes (utilise default_ttl si non spécifié)
        """
        key = self._make_key(query, params)
        ttl = ttl or self.default_ttl

        self._cache[key] = {
            "data": data,
            "expires_at": datetime.now() + timedelta(seconds=ttl),
            "created_at": datetime.now()
        }

    def invalidate(self, query: str = None, params: Optional[Tuple] = None) -> int:
        """
        Invalide le cache.

        Args:
            query: Si spécifié, invalide seulement cette requête
            params: Paramètres de la requête

        Returns:
            Nombre d'entrées supprimées
        """
        if query:
            key = self._make_key(query, params)
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0
        else:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """Supprime les entrées expirées."""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now >= entry["expires_at"]
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "entries": len(self._cache),
            "total_requests": total
        }


# Instance globale du cache
query_cache = QueryCache(default_ttl=300)  # 5 minutes par défaut


# TTL spécifiques par type de requête (en secondes)
CACHE_TTL = {
    "dashboard": 300,      # 5 minutes - données agrégées
    "evolution": 300,      # 5 minutes
    "comparatif": 600,     # 10 minutes - change peu
    "ventes": 180,         # 3 minutes
    "stocks": 300,         # 5 minutes
    "recouvrement": 300,   # 5 minutes
    "balance_agee": 600,   # 10 minutes - change peu
}
