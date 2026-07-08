from __future__ import annotations

import json
from typing import Any, Optional

from app.core.config import settings
from app.core.logger import get_logger
from app.repositories.chat_repository import ChatRepository
from app.agents.graph import AgentGraph

logger = get_logger(__name__)


def _extract_content_text(content: str) -> str:
    """Extract display text from a stored message, handling JSON agent responses."""
    if not content:
        return ""
    if content.startswith("{"):
        try:
            data = json.loads(content)
            if isinstance(data, dict) and data.get("__type") == "agent_message":
                return data.get("answer") or "Query executed."
        except (json.JSONDecodeError, TypeError):
            pass
    return content


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

        # Convert to LLM-friendly format (extract plain text from JSON agent messages)
        chat_history: list[dict[str, str]] = [
            {"role": msg["role"], "content": _extract_content_text(msg["content"])}
            for msg in recent_messages
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

        # ── 5. Save full assistant response as structured JSON ──────────
        assistant_content = json.dumps({
            "__type": "agent_message",
            "answer": result.get("answer") or result.get("message") or "",
            "sql": result.get("sql", ""),
            "results": result.get("results", []),
            "results_count": result.get("results_count", len(result.get("results", []))),
            "insights": result.get("insights", []),
            "suggestions": result.get("suggestions", []),
            "visualization": result.get("visualization"),
            "thread_id": result.get("thread_id"),
            "status": result.get("status", "completed"),
        }, ensure_ascii=False)

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
        """Get all messages for a session, parsing JSON agent messages."""
        session_record = self._repo.find_session_by_session_id(session_id)
        if session_record is None:
            return []
        messages = self._repo.get_messages(
            chat_session_id=session_record["id"],
            limit=limit or self._history_limit,
        )
        result = []
        for msg in messages:
            content = msg.get("content", "")
            enriched = dict(msg)
            enriched["extra"] = {}
            if content.startswith("{") and msg.get("role") == "assistant":
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get("__type") == "agent_message":
                        enriched["content"] = data.get("answer") or "Query executed."
                        enriched["extra"] = {k: v for k, v in data.items() if k != "__type" and k != "answer"}
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(enriched)
        return result

    # ── Session listing ─────────────────────────────────────────────────

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all chat sessions."""
        sessions = self._repo.list_sessions()
        enriched = []
        for ses in sessions:
            messages = self._repo.get_messages(
                chat_session_id=ses["id"],
                limit=self._history_limit,
            )
            preview = _extract_content_text(messages[-1]["content"])[:100] if messages else ""
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