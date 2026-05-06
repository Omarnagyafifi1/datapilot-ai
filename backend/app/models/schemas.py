from enum import Enum
from typing import Any, Dict, List, Optional

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


class VisualizationResponse(BaseModel):
    library: str
    chart_type: str
    x: str
    y: str
    spec: Dict[str, Any]


class QueryDocument(BaseModel):
    question: str
    sql: str
    results: List[Dict[str, Any]]
    results_count: int
    visualization: Optional[VisualizationResponse] = None
    insights: List[Dict[str, str]]
    suggestions: List[Dict[str, str]]
    executed_at: str


class QueryResponse(BaseModel):
    sql: str = ""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    visualization: Optional[VisualizationResponse] = None
    documentation: Dict[str, Any] = Field(default_factory=dict)
    thread_id: str | None = None
    requires_approval: bool = False
    approval_request: Dict[str, Any] | None = None
    status: str | None = None
    message: str | None = None


class QueryRequest(BaseModel):
    question: str
    source_id: str
    thread_id: str | None = None


class QueryApprovalRequest(BaseModel):
    thread_id: str
    approved: bool


class HealthResponse(BaseModel):
    status: str


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
    created_at: Any
