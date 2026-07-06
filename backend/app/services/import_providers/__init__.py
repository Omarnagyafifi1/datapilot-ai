"""
Import Provider Framework for Data Import System.

This module provides an abstract base class for importing various data formats
into the system, along with concrete implementations for specific formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional
from fastapi import UploadFile


@dataclass
class ColumnMetadata:
    """Metadata about a single column."""
    name: str
    original_name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    is_numeric: bool = False
    is_date: bool = False


@dataclass
class TableMetadata:
    """Metadata about a single table."""
    name: str
    original_name: Optional[str]
    row_count: int
    columns: List[ColumnMetadata]


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key relationship."""
    column: str
    referenced_table: str
    referenced_column: str


@dataclass
class DataQualityReport:
    """Data quality metrics for a dataset."""
    total_rows: int
    total_columns: int
    missing_values: dict[str, int]  # column_name -> count
    duplicate_rows: int
    has_nulls: bool
    has_duplicates: bool


@dataclass
class ImportPreview:
    """Preview data returned before import confirmation."""
    filename: str
    file_size: int
    detected_format: str
    file_hash: str
    tables: List[TableMetadata]
    quality_report: DataQualityReport
    relationships: List[ForeignKeyInfo]


@dataclass
class ImportOptions:
    """Options for the import process."""
    selected_tables: Optional[List[str]] = None
    renamed_columns: Optional[dict[str, str]] = None  # table -> {old_name: new_name}
    modified_types: Optional[dict[str, str]] = None  # table -> {col_name: new_type}
    dataset_name: Optional[str] = None


@dataclass
class ImportResult:
    """Result after import is complete."""
    source_id: str
    dataset_id: str
    table_names: List[str]
    total_rows: int
    message: str
    stored_path: Optional[str] = None


class ImportProvider(ABC):
    """
    Abstract base class for data import providers.
    
    Each provider handles a specific file format and implements the full
    import pipeline: validation, preview, parsing, and import.
    """
    
    @abstractmethod
    async def validate(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Validate that the file is of the correct format.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def preview(self, file: UploadFile) -> ImportPreview:
        """
        Generate a preview of the data without importing.
        
        Returns:
            ImportPreview with tables, columns, sample data, quality report
        """
        pass
    
    @abstractmethod
    async def parse(self, file: UploadFile, options: ImportOptions) -> tuple[Any, ImportPreview]:
        """
        Parse the file content into a structured format.
        
        Returns:
            Tuple of (parsed_data, preview)
        """
        pass
    
    @abstractmethod
    async def import_data(self, file: UploadFile, options: ImportOptions) -> ImportResult:
        """
        Import the data into the system.
        
        This should:
        - Create/modify tables in the database
        - Register as a datasource
        - Store metadata
        
        Returns:
            ImportResult with source_id and table info
        """
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """Return the format name this provider handles (e.g., 'csv', 'sqlite')."""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        pass


# Export convenience classes
from .csv_provider import CSVProvider
from .sqlite_provider import SQLiteProvider

__all__ = [
    'ImportProvider',
    'CSVProvider',
    'SQLiteProvider',
    'ColumnMetadata',
    'TableMetadata',
    'ForeignKeyInfo',
    'DataQualityReport',
    'ImportPreview',
    'ImportOptions',
    'ImportResult',
]