from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Text, Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.logger import get_logger

logger = get_logger(__name__)

_METADATA = MetaData()

_CHAT_SESSIONS = Table(
    "chat_sessions",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column("session_id", String(255), nullable=False, index=True),
    Column("user_id", String(255), nullable=True),  # nullable for future auth
    Column("title", String(512), nullable=False, default="New Chat"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)

_CHAT_MESSAGES = Table(
    "chat_messages",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column("chat_session_id", String(36), ForeignKey("chat_sessions.id"), nullable=False, index=True),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("token_count", Integer, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)


_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def _get_engine(db_url: str) -> Engine:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    from sqlalchemy import create_engine
    _ENGINE = create_engine(db_url, pool_pre_ping=True)
    _METADATA.create_all(_ENGINE, tables=[_CHAT_SESSIONS, _CHAT_MESSAGES])
    return _ENGINE


def _get_session_factory(db_url: str) -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=_get_engine(db_url), autoflush=False, autocommit=False)
    return _SESSION_FACTORY


def reset_engine() -> None:
    """Reset the engine and session factory (useful for testing or reconfiguration)."""
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_FACTORY = None
