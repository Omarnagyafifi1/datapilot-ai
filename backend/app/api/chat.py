from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_data_source_service, get_graph_orchestrator
from app.agents.graph import AgentGraph
from app.core.logger import get_logger
from app.services.chat_service import ChatService
from app.services.data_source_service import DataSourceService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_chat_service(graph: AgentGraph = Depends(get_graph_orchestrator)) -> ChatService:
    return ChatService(graph=graph)


@router.post("/message")
def send_message(
    body: dict[str, Any],
    data_source_service: DataSourceService = Depends(get_data_source_service),
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """
    Send a message in a chat session.

    Body:
    - session_id (str): The frontend-generated session UUID.
    - question (str): The user's question.
    - source_id (str): The connected data source ID.
    - preview_only (bool, optional): If True, only preview the SQL.
    - sql (str, optional): Pre-written SQL to execute.
    - thread_id (str, optional): LangGraph thread ID.
    - llm_config (dict, optional): LLM config overrides.
    """
    session_id = body.get("session_id")
    question = body.get("question")
    source_id = body.get("source_id")

    if not session_id or not question or not source_id:
        raise HTTPException(status_code=400, detail="session_id, question, and source_id are required")

    data_source_service.get_conn_string(source_id)

    try:
        result = chat_service.send_message(
            session_id=session_id,
            question=question,
            source_id=source_id,
            preview_only=body.get("preview_only", False),
            sql=body.get("sql"),
            thread_id=body.get("thread_id"),
            llm_config=body.get("llm_config"),
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("Chat message failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_chat_history(
    session_id: str,
    limit: Optional[int] = None,
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """
    Get the message history for a chat session.

    Query params:
    - session_id (str): The frontend-generated session UUID.
    - limit (int, optional): Max number of messages to return.
    """
    try:
        messages = chat_service.get_history(session_id=session_id, limit=limit)
        return {"success": True, "data": messages}
    except Exception as e:
        logger.exception("Failed to get chat history")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_chat_sessions(
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """List all chat sessions."""
    try:
        sessions = chat_service.list_sessions()
        return {"success": True, "data": sessions}
    except Exception as e:
        logger.exception("Failed to list chat sessions")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/new")
def new_chat_session(
    body: dict[str, Any],
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """
    Create a new empty chat session.

    Body:
    - session_id (str): The new frontend-generated session UUID.
    """
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        session = chat_service.new_session(session_id=session_id)
        return {"success": True, "data": session}
    except Exception as e:
        logger.exception("Failed to create new chat session")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
def delete_chat_session(
    session_id: str,
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """Delete a chat session and all its messages."""
    try:
        chat_service.delete_session(session_id=session_id)
        return {"success": True, "message": "Chat session deleted"}
    except Exception as e:
        logger.exception("Failed to delete chat session")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{session_id}/rename")
def rename_chat_session(
    session_id: str,
    body: dict[str, Any],
    chat_service: ChatService = Depends(_get_chat_service),
) -> dict[str, Any]:
    """
    Rename a chat session.

    Body:
    - title (str): The new title.
    """
    title = body.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    try:
        chat_service.rename_session(session_id=session_id, title=title)
        return {"success": True, "message": "Chat session renamed"}
    except Exception as e:
        logger.exception("Failed to rename chat session")
        raise HTTPException(status_code=500, detail=str(e))