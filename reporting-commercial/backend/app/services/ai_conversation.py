"""
Gestionnaire d'historique de conversation pour le module IA.
Stockage en memoire par session utilisateur.
"""
from typing import List, Dict, Optional
from datetime import datetime
import threading
import uuid


class ConversationSession:
    """Session de conversation d'un utilisateur."""

    def __init__(self, session_id: str, user_id: int, dwh_code: str):
        self.session_id = session_id
        self.user_id = user_id
        self.dwh_code = dwh_code
        self.messages: List[Dict] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

    def add_message(self, role: str, content: str, metadata: dict = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.last_activity = datetime.now()

    def get_recent_messages(self, max_messages: int = 20) -> List[Dict]:
        """Retourne les N derniers messages pour le contexte LLM."""
        return self.messages[-max_messages:]

    def clear(self):
        self.messages = []


class ConversationManager:
    """Gestionnaire global des sessions de conversation (singleton thread-safe)."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sessions: Dict[str, ConversationSession] = {}
                    cls._instance._session_ttl = 3600  # 1 heure
        return cls._instance

    def create_session(self, user_id: int, dwh_code: str) -> str:
        """Cree une nouvelle session et retourne son ID."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ConversationSession(
            session_id, user_id, dwh_code
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        session = self._sessions.get(session_id)
        if session and self._is_expired(session):
            del self._sessions[session_id]
            return None
        return session

    def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: int,
        dwh_code: str
    ) -> ConversationSession:
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        new_id = self.create_session(user_id, dwh_code)
        return self._sessions[new_id]

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Supprime les sessions expirees. Retourne le nombre supprime."""
        expired = [
            sid for sid, s in self._sessions.items()
            if self._is_expired(s)
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def _is_expired(self, session: ConversationSession) -> bool:
        return (
            (datetime.now() - session.last_activity).total_seconds()
            > self._session_ttl
        )


# Singleton global
conversation_manager = ConversationManager()
