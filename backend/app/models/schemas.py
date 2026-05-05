from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


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


class UploadMetadata(BaseModel):
    table_name: str
    columns: Dict[str, str]
    sample_data: List[Dict[str, Any]]


class UploadResponse(BaseModel):
    message: str
    metadata: UploadMetadata


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


class QueryDocument(BaseModel):
    question: str
    sql: str
    results: List[Dict[str, Any]]
    results_count: int
    visualization: Dict[str, Any] | None = None
    insights: List[Dict[str, str]]
    suggestions: List[Dict[str, str]]
    executed_at: str


class QueryResponse(BaseModel):
    sql: str = ""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    visualization: Dict[str, Any] | None = None
    documentation: Any = None
    thread_id: str | None = None
    requires_approval: bool = False
    approval_request: Dict[str, Any] | None = None
    approval: ApprovalPayload | None = None
    status: str | None = None
    message: str | None = None
    answer: str = ""


class QueryRequest(BaseModel):
    question: str
    source_id: str
    thread_id: str | None = None


class QueryApprovalRequest(BaseModel):
    thread_id: str
    approved: bool


class ExplainRequest(BaseModel):
    sql: str


class ExplainResponse(BaseModel):
    success: bool
    message: str
    data: str

class ConnectRequest(BaseModel):
    name: str
    db_type: str
    host: str = ""
    port: int | None = None
    db_name: str
    username: str = ""
    password: str = ""

class DataSourceResponse(BaseModel):
    id: str
    name: str
    db_type: str
    host: str
    db_name: str
    created_at: datetime

class HealthResponse(BaseModel):
    status: str

class QueryHistoryItem(BaseModel):
    id: str
    question: str
    source_id: str
    status: str
    latency: float
    executed_at: datetime

class QueryHistoryResponse(BaseModel):
    success: bool
    message: str
    data: List[QueryHistoryItem]

class SystemStats(BaseModel):
    total_sources: int
    total_queries: int
    avg_latency: float
    success_rate: float

class SystemStatsResponse(BaseModel):
    success: bool
    message: str
    data: SystemStats

class ActivityFeedItem(BaseModel):
    id: str
    type: str
    content: str
    timestamp: datetime

class ActivityFeedResponse(BaseModel):
    success: bool
    message: str
    data: List[ActivityFeedItem]

class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool

class TableSchema(BaseModel):
    name: str
    columns: List[ColumnSchema]

class SchemaResponse(BaseModel):
    success: bool
    message: str
    data: List[TableSchema]
