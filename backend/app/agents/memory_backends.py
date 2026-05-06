from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class GraphMemoryBackends:
    def __init__(self) -> None:
        self.backend_type = "in-memory"
        self.checkpointer: Any = InMemorySaver()
        self.store: Any = InMemoryStore()
        self._checkpointer_cm: Any | None = None
        self._store_cm: Any | None = None
        self._initialize()

    def _initialize(self) -> None:
        db_uri = settings.langgraph_memory_db_uri.strip()
        if not db_uri:
            logger.info("LangGraph memory backend: in-memory (no LANGGRAPH_MEMORY_DB_URI set)")
            return

        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            from langgraph.store.postgres import PostgresStore

            self._checkpointer_cm = PostgresSaver.from_conn_string(db_uri)
            self._store_cm = PostgresStore.from_conn_string(db_uri)
            self.checkpointer = self._checkpointer_cm.__enter__()
            self.store = self._store_cm.__enter__()

            if settings.langgraph_run_migrations_on_start:
                self.store.setup()
                self.checkpointer.setup()

            self.backend_type = "postgres"
            logger.info("LangGraph memory backend: postgres")
        except Exception:
            logger.exception("Failed to initialize PostgreSQL LangGraph memory; falling back to in-memory")
            self._cleanup_contexts()
            self.backend_type = "in-memory"
            self.checkpointer = InMemorySaver()
            self.store = InMemoryStore()

    def _cleanup_contexts(self) -> None:
        if self._store_cm is not None:
            try:
                self._store_cm.__exit__(None, None, None)
            except Exception:
                logger.exception("Failed to close PostgresStore context")
            finally:
                self._store_cm = None

        if self._checkpointer_cm is not None:
            try:
                self._checkpointer_cm.__exit__(None, None, None)
            except Exception:
                logger.exception("Failed to close PostgresSaver context")
            finally:
                self._checkpointer_cm = None

    def close(self) -> None:
        self._cleanup_contexts()
