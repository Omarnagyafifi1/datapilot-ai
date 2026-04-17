from dataclasses import dataclass


@dataclass
class AgentState:
    question: str
    sql: str = ""
    answer: str = ""
