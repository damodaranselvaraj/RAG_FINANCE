from uuid import uuid4

from datetime import datetime

from .base_repository import BaseRepository
from .models import Session


class SessionRepository(BaseRepository):
    """All SQLite reads/writes for the ``session`` table."""

    def create(self, title: str = "New Chat", session_id: str | None = None) -> str:
        """Insert a new chat session and return its id.

        If *session_id* is provided (e.g. client-generated UUID) it is used
        as-is; otherwise a new UUID is generated server-side.
        """

        session_id = session_id or uuid4().hex

        with self._write() as db:

            db.add(
                Session(
                    id=session_id,
                    title=title
                )
            )

        return session_id

    def get(self, session_id: str):
        """Return the session row, or ``None`` if it does not exist."""

        with self._read() as db:

            return db.query(Session).filter(
                Session.id == session_id
            ).first()

    def exists(self, session_id: str) -> bool:

        with self._read() as db:

            return db.query(Session.id).filter(
                Session.id == session_id
            ).first() is not None

    def list_all(self):
        """Return every session, most recently updated first."""

        with self._read() as db:

            return db.query(Session).order_by(
                Session.updated_at.desc()
            ).all()

    def rename(self, session_id: str, title: str) -> bool:
        """Set a new title. Returns ``False`` if the session is unknown."""

        with self._write() as db:

            row = db.query(Session).filter(
                Session.id == session_id
            ).first()

            if row is None:
                return False

            row.title = title

            return True

    def touch(self, session_id: str) -> bool:
        """Bump ``updated_at`` so the session floats to the top of the list."""

        with self._write() as db:

            row = db.query(Session).filter(
                Session.id == session_id
            ).first()

            if row is None:
                return False

            row.updated_at = datetime.utcnow()

            return True

    def delete(self, session_id: str) -> bool:
        """Delete the session row. Returns ``False`` if it was not there.

        Messages are removed separately by ``ConversationRepository`` — SQLite
        only honours ``ON DELETE CASCADE`` when the ``foreign_keys`` pragma is
        enabled on the connection.
        """

        with self._write() as db:

            deleted = db.query(Session).filter(
                Session.id == session_id
            ).delete()

            return deleted > 0
