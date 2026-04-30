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


