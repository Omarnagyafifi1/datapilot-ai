import json
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.agents.nodes.sql_node import run_sql_node
from app.agents.prompts import INSIGHT_PROMPT, SUGGESTION_PROMPT
from app.agents.state.agent_state import AgentState
from app.agents.tools.schema_tools import fetch_schema_context
from app.agents.tools.sql_tools import execute_sql
from app.core.logger import get_logger
from app.llm.base_llm import BaseLLM
from app.models.schemas import QueryDocument
from app.services.db_service import DBService
from app.services.schema_service import SchemaService


logger = get_logger(__name__)


def _fallback_insights() -> list[dict[str, str]]:
    return [{"ar": "لا توجد بيانات كافية للتحليل", "en": "No data to analyze"}]


def _extract_json_payload(raw_response: str) -> str:
    cleaned = raw_response.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return cleaned


def _normalize_insights(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("insights")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")
        if not isinstance(ar_value, str) or not isinstance(en_value, str):
            continue

        ar_value = ar_value.strip()
        en_value = en_value.strip()
        if ar_value and en_value:
            normalized.append({"ar": ar_value, "en": en_value})

    if not normalized:
        return None

    trimmed = normalized[:5]
    if len(trimmed) < 3:
        return None

    return trimmed


def _parse_insights(raw_response: str) -> list[dict[str, str]] | None:
    cleaned = _extract_json_payload(raw_response)
    candidates = [cleaned]

    list_start = cleaned.find("[")
    list_end = cleaned.rfind("]")
    if list_start != -1 and list_end > list_start:
        candidates.append(cleaned[list_start : list_end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        normalized = _normalize_insights(payload)
        if normalized is not None:
            return normalized

    return None


def _normalize_suggestions(payload: Any) -> list[dict[str, str]] | None:
    if isinstance(payload, dict):
        payload = payload.get("suggestions")

    if not isinstance(payload, list):
        return None

    normalized: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        ar_value = item.get("ar")
        en_value = item.get("en")
        if not isinstance(ar_value, str) or not isinstance(en_value, str):
            continue

        ar_value = ar_value.strip()
        en_value = en_value.strip()
        if ar_value and en_value:
            normalized.append({"ar": ar_value, "en": en_value})

    if len(normalized) != 3:
        return None

    return normalized


def _parse_suggestions(raw_response: str) -> list[dict[str, str]] | None:
    cleaned = _extract_json_payload(raw_response)
    candidates = [cleaned]

    list_start = cleaned.find("[")
    list_end = cleaned.rfind("]")
    if list_start != -1 and list_end > list_start:
        candidates.append(cleaned[list_start : list_end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        normalized = _normalize_suggestions(payload)
        if normalized is not None:
            return normalized

    return None


def insight_node(state: AgentState, llm: BaseLLM) -> AgentState:
    if not state.query_results:
        state.insights = _fallback_insights()
        return state

    truncated_results = state.query_results[:50]
    prompt = (
        f"{INSIGHT_PROMPT}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Query results (first {len(truncated_results)} rows):\n"
        f"{json.dumps(truncated_results, ensure_ascii=False)}"
    )

    raw_response = llm.generate(prompt)
    parsed_insights = _parse_insights(raw_response)
    state.insights = parsed_insights if parsed_insights is not None else _fallback_insights()
    return state


def suggestion_node(state: AgentState, llm: BaseLLM) -> AgentState:
    prompt = (
        f"{SUGGESTION_PROMPT}\n\n"
        f"Question:\n{state.question}\n\n"
        f"Generated SQL:\n{state.sql}\n\n"
        f"Insights:\n{json.dumps(state.insights, ensure_ascii=False)}"
    )

    raw_response = llm.generate(prompt)
    parsed_suggestions = _parse_suggestions(raw_response)
    state.suggestions = parsed_suggestions if parsed_suggestions is not None else []
    return state


def documentation_node(state: AgentState) -> AgentState:
    state.executed_at = datetime.now(timezone.utc)
    document = QueryDocument(
        question=state.question,
        sql=state.sql,
        results_count=len(state.query_results),
        insights=state.insights,
        suggestions=state.suggestions,
        executed_at=state.executed_at.isoformat(),
    )
    serialized_document = document.model_dump()
    logger.info("%s", json.dumps(serialized_document, ensure_ascii=False))
    state.documentation = serialized_document
    return state


class AgentGraph(BaseAgent):
    def __init__(
        self,
        llm: BaseLLM,
        db_service: DBService,
        schema_service: SchemaService,
    ) -> None:
        self.llm = llm
        self.db_service = db_service
        self.schema_service = schema_service

    def run(self, question: str, source_id: str) -> dict[str, Any]:
        state = AgentState(question=question, source_id=source_id)

        # Simple orchestration flow: schema -> SQL generation -> SQL execution -> insights -> suggestions -> documentation -> answer.
        _schema = fetch_schema_context(self.schema_service)
        state = run_sql_node(state, self.llm)
        state.query_results = execute_sql(self.db_service, state.sql, state.source_id) or []
        state = insight_node(state, self.llm)
        state = suggestion_node(state, self.llm)
        state = documentation_node(state)

        state.answer = f"Stub answer. Schema: {_schema}. Result: {state.query_results}"
        return {"answer": state.answer, "documentation": state.documentation}
