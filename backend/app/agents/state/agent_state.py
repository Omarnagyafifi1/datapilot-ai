from dataclasses import dataclass, field


@dataclass
class AgentState:
    question: str
    sql: str = ""
    answer: str = ""
    retry_count: int = 0
    success: bool = False
    error: str = None
    sql_results: list = field(default_factory=list)
