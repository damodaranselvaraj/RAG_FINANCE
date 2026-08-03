from contextlib import contextmanager

from .db import SessionLocal


class BaseRepository:
    """Shared SQLAlchemy session plumbing for the memory repositories.

    ``SessionLocal`` expires ORM instances on commit, so writes and reads get
    two different scopes:

    * ``_write()``  — commits on success, rolls back on error. Anything the
      caller needs afterwards must be read *inside* the block (after a flush),
      because the instances are expired once the commit lands.
    * ``_read()``   — never commits, so the rows it returns stay usable after
      the session is closed (detached but fully loaded).
    """

    def __init__(self, session_factory=SessionLocal):

        self._session_factory = session_factory

    @contextmanager
    def _write(self):

        db = self._session_factory()

        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def _read(self):

        db = self._session_factory()

        try:
            yield db
        finally:
            db.close()
