"""
Dataset metadata models for the Import Framework.

These models extend the existing datasource concept with richer metadata
for imported files including quality reports, AI summaries, and relationships.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnMetadataModel(BaseModel):
    """Metadata about a single column for API responses."""
    name: str
    original_name: Optional[str] = None
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    is_numeric: bool = False
    is_date: bool = False


class ForeignKeyInfoModel(BaseModel):
    """Information about a foreign key relationship for API responses."""
    column: str
    referenced_table: str
    referenced_column: str


class TableMetadataModel(BaseModel):
    """Metadata about a single table for API responses."""
    name: str
    original_name: Optional[str] = None
    row_count: int
    columns: List[ColumnMetadataModel] = Field(default_factory=list)


class DataQualityReportModel(BaseModel):
    """Data quality metrics for API responses."""
    total_rows: int
    total_columns: int
    missing_values: Dict[str, int] = Field(default_factory=dict)
    duplicate_rows: int
    has_nulls: bool = False
    has_duplicates: bool = False


class ImportPreviewModel(BaseModel):
    """Preview data returned before import confirmation."""
    filename: str
    file_size: int
    detected_format: str
    file_hash: str
    tables: List[TableMetadataModel] = Field(default_factory=list)
    quality_report: DataQualityReportModel
    relationships: List[ForeignKeyInfoModel] = Field(default_factory=list)


class ImportOptionsModel(BaseModel):
    """Options for the import process."""
    selected_tables: Optional[List[str]] = None
    renamed_columns: Optional[Dict[str, Dict[str, str]]] = None
    modified_types: Optional[Dict[str, Dict[str, str]]] = None
    dataset_name: Optional[str] = None


class ImportResultModel(BaseModel):
    """Result after import is complete."""
    source_id: str
    dataset_id: str
    table_names: List[str] = Field(default_factory=list)
    total_rows: int = 0
    message: str


class DatasetMetadataModel(BaseModel):
    """Extended metadata for imported datasets."""
    id: str
    source_id: str
    name: str
    source_type: str  # csv, sqlite, excel, json
    original_filename: str
    file_size: int
    file_hash: str
    import_timestamp: Any
    table_count: int
    total_row_count: int
    column_count: int
    tables: List[TableMetadataModel] = Field(default_factory=list)
    relationships: List[ForeignKeyInfoModel] = Field(default_factory=list)
    quality_report: Optional[DataQualityReportModel] = None
    ai_summary: Optional[str] = None


class DatasetListResponse(BaseModel):
    """Response for listing datasets."""
    success: bool
    message: str
    data: List[DatasetMetadataModel]


class DatasetDetailResponse(BaseModel):
    """Response for getting a single dataset."""
    success: bool
    message: str
    data: DatasetMetadataModel