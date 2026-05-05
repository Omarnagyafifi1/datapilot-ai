from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class DataSourceType(str, Enum):
    POSTGRES = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    REDSHIFT = "redshift"
    SPARK = "spark"

class DataSourceConfig(BaseModel):
    source_id: str
    data_source_type: DataSourceType
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str
    service_name: str | None = None


class HealthResponse(BaseModel):
    status: str


class QueryRequest(BaseModel):
    question: str
    source_id: str


class ApprovalPayload(BaseModel):
    run_id: str
    question: Optional[str] = None
    sql: Optional[str] = None
    message: Optional[str] = None


class QueryResponse(BaseModel):
    status: str = "completed"
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    documentation: Optional[Dict[str, Any]] = None
    approval: Optional[ApprovalPayload] = None
    message: Optional[str] = None


class ApprovalRequest(BaseModel):
    run_id: str
    approved: bool
    reason: Optional[str] = None


class ConnectRequest(BaseModel):
    name: str
    db_type: str
    host: str
    port: Optional[int] = None
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

class QueryDocument(BaseModel):
    question: str
    sql: str
    results: List[Dict[str, Any]]
    results_count: int
    visualization: Dict[str, Any] | None = None
    insights: List[Dict[str, str]]
    suggestions: List[Dict[str, str]]
    executed_at: str

class UploadMetadata(BaseModel):
    table_name: str
    columns: Dict[str, str]
    sample_data: List[Dict[str, Any]]

class UploadResponse(BaseModel):
    message: str
    metadata: UploadMetadata


