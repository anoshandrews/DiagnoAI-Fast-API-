from collections import defaultdict
from threading import Lock

from backend.app.models.schemas import ChatMessage


class InMemorySessionStore:
    """Simple per-session store for local development and tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = defaultdict(list)
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions[session_id])

    def append(self, session_id: str, *messages: ChatMessage) -> list[ChatMessage]:
        with self._lock:
            self._sessions[session_id].extend(messages)
            return list(self._sessions[session_id])

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


session_store = InMemorySessionStore()
