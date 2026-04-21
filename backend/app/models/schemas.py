from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str


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
