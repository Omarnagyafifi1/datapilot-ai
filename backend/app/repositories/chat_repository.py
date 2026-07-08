from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import desc, update as sql_update, delete as sql_delete, select
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.models.chat import _CHAT_MESSAGES, _CHAT_SESSIONS, _get_session_factory

logger = get_logger(__name__)


class ChatRepository:
    """Repository for chat session and message persistence."""

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    def _session(self) -> Session:
        return _get_session_factory(self._db_url)()

    # ── Session operations ──────────────────────────────────────────────

    def find_session_by_session_id(self, session_id: str) -> Optional[dict[str, Any]]:
        """Find a chat session by its public session_id."""
        session = self._session()
        try:
            row = session.execute(
                select(_CHAT_SESSIONS).where(_CHAT_SESSIONS.c.session_id == session_id)
            ).mappings().first()
            return dict(row) if row else None
        finally:
            session.close()

    def create_session(self, session_id: str, title: str = "New Chat", user_id: Optional[str] = None) -> dict[str, Any]:
        """Create a new chat session and return its record."""
        now = datetime.utcnow()
        payload = {
            "id": str(uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        session = self._session()
        try:
            session.execute(_CHAT_SESSIONS.insert().values(**payload))
            session.commit()
            return dict(payload)
        except Exception:
            session.rollback()
            logger.exception("Failed to create chat session")
            raise
        finally:
            session.close()

    def update_session_title(self, session_id: str, title: str) -> None:
        """Rename a chat session."""
        session = self._session()
        try:
            session.execute(
                sql_update(_CHAT_SESSIONS)
                .where(_CHAT_SESSIONS.c.session_id == session_id)
                .values(title=title, updated_at=datetime.utcnow())
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to update session title")
            raise
        finally:
            session.close()

    def delete_session(self, session_id: str) -> None:
        """Delete a chat session and all its messages."""
        ses = self._session()
        try:
            # Delete messages first
            ses.execute(
                sql_delete(_CHAT_MESSAGES)
                .where(_CHAT_MESSAGES.c.chat_session_id.in_(
                    select(_CHAT_SESSIONS.c.id).where(_CHAT_SESSIONS.c.session_id == session_id)
                ))
            )
            # Delete session
            ses.execute(
                sql_delete(_CHAT_SESSIONS).where(_CHAT_SESSIONS.c.session_id == session_id)
            )
            ses.commit()
        except Exception:
            ses.rollback()
            logger.exception("Failed to delete chat session")
            raise
        finally:
            ses.close()

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List all chat sessions ordered by updated_at descending."""
        ses = self._session()
        try:
            rows = ses.execute(
                select(_CHAT_SESSIONS)
                .order_by(desc(_CHAT_SESSIONS.c.updated_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
            return [dict(r) for r in rows]
        finally:
            ses.close()

    # ── Message operations ─────────────────────────────────────────────

    def save_message(
        self,
        chat_session_id: str,
        role: str,
        content: str,
        token_count: Optional[int] = None,
    ) -> dict[str, Any]:
        """Save a message and return its record."""
        now = datetime.utcnow()
        payload = {
            "id": str(uuid4()),
            "chat_session_id": chat_session_id,
            "role": role,
            "content": content,
            "token_count": token_count,
            "created_at": now,
        }
        ses = self._session()
        try:
            ses.execute(_CHAT_MESSAGES.insert().values(**payload))

            # Update parent session's updated_at
            ses.execute(
                sql_update(_CHAT_SESSIONS)
                .where(_CHAT_SESSIONS.c.id == chat_session_id)
                .values(updated_at=now)
            )
            ses.commit()
            return dict(payload)
        except Exception:
            ses.rollback()
            logger.exception("Failed to save chat message")
            raise
        finally:
            ses.close()

    def get_messages(self, chat_session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get messages for a session ordered by created_at ascending."""
        ses = self._session()
        try:
            rows = ses.execute(
                select(_CHAT_MESSAGES)
                .where(_CHAT_MESSAGES.c.chat_session_id == chat_session_id)
                .order_by(_CHAT_MESSAGES.c.created_at.asc())
                .limit(limit)
            ).mappings().all()
            return [dict(r) for r in rows]
        finally:
            ses.close()

    def get_recent_messages_by_session_id(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get the most recent N messages for a session (by public session_id)."""
        ses = self._session()
        try:
            row = ses.execute(
                select(_CHAT_SESSIONS).where(_CHAT_SESSIONS.c.session_id == session_id)
            ).mappings().first()
            if not row:
                return []
            chat_id = row["id"]
            return self.get_messages(chat_session_id=chat_id, limit=limit)
        finally:
            ses.close()