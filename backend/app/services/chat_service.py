from __future__ import annotations

from typing import Any, Optional

from app.core.config import settings
from app.core.logger import get_logger
from app.repositories.chat_repository import ChatRepository
from app.agents.graph import AgentGraph

logger = get_logger(__name__)


class ChatService:
    """Service layer for chat memory and conversation management."""

    def __init__(self, graph: AgentGraph) -> None:
        self._repo = ChatRepository(
            db_url=settings.CHAT_DB_URL or "sqlite:///./data/chat.db"
        )
        self._graph = graph
        self._history_limit: int = settings.CHAT_HISTORY_LIMIT or 20

    # ── Auto-title generation from first user message ────────────────────

    @staticmethod
    def _generate_title(first_message: str) -> str:
        """Generate a short title from the first user message."""
        cleaned = first_message.strip().strip('?"؟').strip()
        if len(cleaned) <= 40:
            return cleaned
        # Try to find a meaningful break
        break_chars = [".", "?", "!", "،", ".", "؟"]
        for bc in break_chars:
            idx = cleaned.find(bc)
            if 10 < idx < 40:
                return cleaned[:idx + 1]
        return cleaned[:40].rsplit(" ", 1)[0] + "..."

    # ── Core send-message flow ──────────────────────────────────────────

    def send_message(
        self,
        session_id: str,
        question: str,
        source_id: str,
        preview_only: bool = False,
        sql: Optional[str] = None,
        thread_id: Optional[str] = None,
        llm_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Main flow:
        1. Find or create session by session_id.
        2. Save user message.
        3. Load recent conversation history.
        4. Inject history into the LLM call.
        5. Save assistant response.
        6. Return final response.
        """
        # ── 1. Find or create session ───────────────────────────────────
        session_record = self._repo.find_session_by_session_id(session_id)
        is_new = False
        if session_record is None:
            is_new = True
            session_record = self._repo.create_session(
                session_id=session_id,
                title="New Chat",
            )

        chat_session_id = session_record["id"]

        # ── 2. Save user message ────────────────────────────────────────
        self._repo.save_message(
            chat_session_id=chat_session_id,
            role="user",
            content=question,
        )

        # ── 3. Load recent history ──────────────────────────────────────
        recent_messages = self._repo.get_messages(
            chat_session_id=chat_session_id,
            limit=self._history_limit,
        )

        # Convert to LLM-friendly format
        chat_history: list[dict[str, str]] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recent_messages
            # Exclude the just-saved user message if we only want prior context
            # But including it is fine; the LLM can use full context
        ]

        # ── 4. Call the existing LLM flow with history injected ─────────
        try:
            result = self._graph.run(
                question=question,
                source_id=source_id,
                thread_id=thread_id,
                preview_only=preview_only,
                sql=sql,
                chat_history=chat_history,  # New optional parameter
            )
        except Exception:
            logger.exception("Chat LLM call failed")
            raise

        # Extract assistant response content
        assistant_content = (
            result.get("answer")
            or result.get("message")
            or result.get("documentation", {}).get("sql", "")
        )
        if not assistant_content:
            assistant_content = "Query executed successfully."

        # ── 5. Save assistant response ──────────────────────────────────
        self._repo.save_message(
            chat_session_id=chat_session_id,
            role="assistant",
            content=assistant_content,
        )

        # ── Auto-title the session if it's new ──────────────────────────
        if is_new:
            title = self._generate_title(question)
            self._repo.update_session_title(session_id, title)

        # ── 6. Return result ────────────────────────────────────────────
        return {
            **result,
            "session_id": session_id,
        }

    # ── History retrieval ───────────────────────────────────────────────

    def get_history(self, session_id: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Get all messages for a session."""
        session_record = self._repo.find_session_by_session_id(session_id)
        if session_record is None:
            return []
        return self._repo.get_messages(
            chat_session_id=session_record["id"],
            limit=limit or self._history_limit,
        )

    # ── Session listing ─────────────────────────────────────────────────

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all chat sessions."""
        sessions = self._repo.list_sessions()
        # Add a preview of the last message for each session
        enriched = []
        for ses in sessions:
            messages = self._repo.get_messages(
                chat_session_id=ses["id"],
                limit=1,
            )
            preview = messages[-1]["content"][:100] if messages else ""
            enriched.append({**ses, "preview": preview})
        return enriched

    # ── New session ─────────────────────────────────────────────────────

    def new_session(self, session_id: str) -> dict[str, Any]:
        """Create a new empty session."""
        return self._repo.create_session(session_id=session_id, title="New Chat")

    # ── Delete session ──────────────────────────────────────────────────

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        self._repo.delete_session(session_id)

    # ── Rename session ──────────────────────────────────────────────────

    def rename_session(self, session_id: str, title: str) -> None:
        """Rename a session."""
        self._repo.update_session_title(session_id, title)