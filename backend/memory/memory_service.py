from .conversation_repository import ConversationRepository
from .session_repository import SessionRepository

VALID_ROLES = ("user", "assistant", "system")


class MemoryService:
    """Chat-memory API used by the rest of the app.

    Holds no SQL of its own — every read/write goes through
    ``SessionRepository`` / ``ConversationRepository``.
    """

    def __init__(
        self,
        session_repository: SessionRepository = None,
        conversation_repository: ConversationRepository = None
    ):

        self.sessions = session_repository or SessionRepository()
        self.conversations = conversation_repository or ConversationRepository()

    def create_session(
        self,
        title: str = "New Chat",
    ) -> str:
        """Create a new session row in the repository and return the generated session id."""

        return self.sessions.create(title=title)

    def save_message(
        self,
        session_id: str,
        role: str,
        message: str,
        user_id: str | None = None,
    ):
        """Append a turn and mark the session as recently active."""

        if role not in VALID_ROLES:
            raise ValueError(
                f"role must be one of {VALID_ROLES}, got {role!r}"
            )

        if not self.sessions.exists(session_id):
            raise KeyError(f"unknown session: {session_id}")

        saved = self.conversations.add(session_id, role, message, user_id=user_id)

        self.sessions.touch(session_id)

        return saved

    def get_history(
        self,
        session_id: str
    ):

        return self.conversations.list_by_session(session_id)

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 4
    ):

        return self.conversations.get_recent(session_id, limit)

    def delete_session(
        self,
        session_id: str
    ):
        """Drop a session and its messages. Returns ``True`` if it existed."""

        self.conversations.delete_by_session(session_id)

        return self.sessions.delete(session_id)

    def list_sessions(self):

        return self.sessions.list_all()

    def rename_session(
        self,
        session_id: str,
        title: str
    ):

        return self.sessions.rename(session_id, title)
