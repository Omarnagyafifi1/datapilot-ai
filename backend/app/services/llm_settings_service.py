"""
LLM Settings Service for managing LLM provider configuration.

This module provides functions to get and save LLM settings to the database.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, create_engine, select, insert, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_METADATA = MetaData()
_LLM_SETTINGS = Table(
    "llm_settings",
    _METADATA,
    Column("id", String(36), primary_key=True, default="default"),
    Column("provider", String(32), nullable=False, default="groq"),
    Column("model", String(128), nullable=False, default="llama-3.1-8b-instant"),
    Column("temperature", Float, nullable=False, default=0.2),
    Column("max_tokens", Integer, nullable=False, default=2048),
    Column("api_keys", String(2048), nullable=True),  # JSON string containing encrypted API keys
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)

_SETTINGS_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def _get_settings_engine() -> Engine:
    global _SETTINGS_ENGINE

    if _SETTINGS_ENGINE is not None:
        return _SETTINGS_ENGINE

    db_url = settings.data_sources_db_url.strip()
    if not db_url:
        db_url = "sqlite:///./data_sources.db"

    _SETTINGS_ENGINE = create_engine(db_url, pool_pre_ping=True)
    _METADATA.create_all(_SETTINGS_ENGINE, tables=[_LLM_SETTINGS])
    return _SETTINGS_ENGINE


def _get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=_get_settings_engine(), autoflush=False, autocommit=False)
    return _SESSION_FACTORY


def get_llm_settings() -> dict:
    """Get current LLM settings from database."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(
            select(_LLM_SETTINGS).where(_LLM_SETTINGS.c.id == "default")
        ).mappings().first()
        
        if row:
            import json
            api_keys = {}
            if row["api_keys"]:
                try:
                    api_keys = json.loads(row["api_keys"])
                except Exception:
                    api_keys = {}
            
            return {
                "provider": row["provider"],
                "model": row["model"],
                "temperature": float(row["temperature"]),
                "max_tokens": int(row["max_tokens"]),
                "api_keys": api_keys,
            }
        
        # Return defaults if no settings found
        return {
            "provider": settings.DEFAULT_LLM_PROVIDER if hasattr(settings, 'DEFAULT_LLM_PROVIDER') else "groq",
            "model": settings.DEFAULT_LLM_MODEL if hasattr(settings, 'DEFAULT_LLM_MODEL') else "llama-3.1-8b-instant",
            "temperature": 0.2,
            "max_tokens": 2048,
            "api_keys": {},
        }
    finally:
        session.close()


def save_llm_settings(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    api_keys: Optional[dict] = None,
) -> dict:
    """Save LLM settings to database."""
    session_local = _get_session_factory()
    session: Session = session_local()
    
    import json
    settings_data = {
        "provider": provider or "groq",
        "model": model or "llama-3.1-8b-instant",
        "temperature": temperature if temperature is not None else 0.2,
        "max_tokens": max_tokens if max_tokens is not None else 2048,
        "api_keys": api_keys or {},
    }
    
    try:
        # Check if record exists
        existing = session.execute(
            select(_LLM_SETTINGS).where(_LLM_SETTINGS.c.id == "default")
        ).mappings().first()
        
        if existing:
            existing_keys = json.loads(existing["api_keys"]) if existing["api_keys"] else {}
            # Merge keys: if new value starts with "***", keep the existing key
            merged_keys = {}
            for k, v in settings_data["api_keys"].items():
                if v and v.startswith("***"):
                    merged_keys[k] = existing_keys.get(k, "")
                else:
                    merged_keys[k] = v

            session.execute(
                update(_LLM_SETTINGS)
                .where(_LLM_SETTINGS.c.id == "default")
                .values(
                    provider=settings_data["provider"],
                    model=settings_data["model"],
                    temperature=settings_data["temperature"],
                    max_tokens=settings_data["max_tokens"],
                    api_keys=json.dumps(merged_keys),
                    updated_at=datetime.utcnow(),
                )
            )
        else:
            session.execute(
                insert(_LLM_SETTINGS).values(
                    id="default",
                    provider=settings_data["provider"],
                    model=settings_data["model"],
                    temperature=settings_data["temperature"],
                    max_tokens=settings_data["max_tokens"],
                    api_keys=json.dumps(settings_data["api_keys"]),
                    updated_at=datetime.utcnow(),
                )
            )
        session.commit()
        return settings_data
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to save LLM settings")
        raise
    finally:
        session.close()