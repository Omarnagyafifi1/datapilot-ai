from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class AgentState:
    question: str
    source_id: str
    intent: str = "INQUIRE"  # ADD, DELETE, UPDATE, INQUIRE
    sql: str = ""
    query_results: list[dict[str, Any]] = field(default_factory=list)
    visualization: dict[str, Any] | None = None
    insights: list[dict[str, str]] = field(default_factory=list)
    suggestions: list[dict[str, str]] = field(default_factory=list)
    executed_at: datetime | None = None
    documentation: dict[str, Any] = field(default_factory=dict)
    answer: str = ""
    retry_count: int = 0
    success: bool = False
    error: str | None = None
    validation_passed: bool = True
    validation_reason: str | None = None
    scenario_matched: bool = False
    scenario_similarity: float = 0.0
