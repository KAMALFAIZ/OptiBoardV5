"""Service de logging des requêtes SQL pour l'interface admin"""
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict
import threading


class QueryLogger:
    """Logger pour les requêtes SQL avec statistiques de performance."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.history: List[Dict[str, Any]] = []
        self.stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_executions": 0,
            "total_time": 0,
            "avg_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "total_rows": 0,
            "last_execution": None,
            "errors": 0
        })
        self.max_history = 1000

    def log_query(
        self,
        query_id: str,
        query_name: str,
        query_sql: str,
        execution_time: float,
        rows_returned: int,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Enregistre une exécution de requête."""
        entry = {
            "id": query_id,
            "name": query_name,
            "sql": query_sql[:500],  # Tronquer pour l'historique
            "execution_time": round(execution_time, 4),
            "rows_returned": rows_returned,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

        # Ajouter à l'historique
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Mettre à jour les stats
        stats = self.stats[query_id]
        stats["total_executions"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["total_executions"]
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["total_rows"] += rows_returned
        stats["last_execution"] = entry["timestamp"]
        if not success:
            stats["errors"] += 1

    def get_history(self, limit: int = 100, query_id: Optional[str] = None) -> List[Dict]:
        """Récupère l'historique des requêtes."""
        history = self.history
        if query_id:
            history = [h for h in history if h["id"] == query_id]
        return list(reversed(history[-limit:]))

    def get_stats(self, query_id: Optional[str] = None) -> Dict[str, Any]:
        """Récupère les statistiques des requêtes."""
        if query_id:
            return dict(self.stats.get(query_id, {}))
        return {k: dict(v) for k, v in self.stats.items()}

    def get_slowest_queries(self, limit: int = 10) -> List[Dict]:
        """Récupère les requêtes les plus lentes."""
        sorted_stats = sorted(
            [(k, v) for k, v in self.stats.items()],
            key=lambda x: x[1]["avg_time"],
            reverse=True
        )
        return [
            {"query_id": k, **v}
            for k, v in sorted_stats[:limit]
        ]

    def clear_history(self):
        """Efface l'historique des requêtes."""
        self.history.clear()

    def clear_stats(self):
        """Réinitialise les statistiques."""
        self.stats.clear()


# Instance singleton
query_logger = QueryLogger()


def timed_query(query_id: str, query_name: str):
    """Décorateur pour mesurer le temps d'exécution des requêtes."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                rows = len(result) if isinstance(result, list) else 0
                query_logger.log_query(
                    query_id=query_id,
                    query_name=query_name,
                    query_sql=kwargs.get('query', str(args[0]) if args else ''),
                    execution_time=execution_time,
                    rows_returned=rows,
                    success=True
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                query_logger.log_query(
                    query_id=query_id,
                    query_name=query_name,
                    query_sql=kwargs.get('query', str(args[0]) if args else ''),
                    execution_time=execution_time,
                    rows_returned=0,
                    success=False,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator
