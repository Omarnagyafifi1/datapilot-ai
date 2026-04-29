from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    source_id: str


class QueryDocument(BaseModel):
    question: str
    sql: str
    results_count: int
    insights: list[dict]
    suggestions: list[dict]
    executed_at: str


class QueryResponse(BaseModel):
    answer: str
    documentation: QueryDocument


class HealthResponse(BaseModel):
    status: str


class ConnectRequest(BaseModel):
    name: str
    db_type: Literal["postgresql", "mysql", "sqlite"]
    host: str
    port: int
    db_name: str
    username: str
    password: str


class DataSourceResponse(BaseModel):
    id: str
    name: str
    db_type: str
    host: str
    db_name: str
    created_at: datetime
