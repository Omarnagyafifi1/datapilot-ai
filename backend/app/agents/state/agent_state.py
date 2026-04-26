from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    question: str
    source_id: str
    sql: str = ""
    query_results: list[dict[str, Any]] = field(default_factory=list)
    insights: list[dict[str, str]] = field(default_factory=list)
    suggestions: list[dict[str, str]] = field(default_factory=list)
    executed_at: datetime | None = None
    documentation: dict[str, Any] = field(default_factory=dict)
    answer: str = ""
