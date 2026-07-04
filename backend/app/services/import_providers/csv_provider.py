"""CSV Import Provider for importing CSV files into the system."""

import hashlib
import io
import re
import math
import pandas as pd
from typing import Any, List, Optional, Tuple
from fastapi import UploadFile
from datetime import datetime
from pathlib import Path

from app.core.logger import get_logger
from app.core.exceptions import CSVValidationError
from app.services.import_providers import (
    ImportProvider,
    ImportPreview,
    ImportOptions,
    ImportResult,
    TableMetadata,
    ColumnMetadata,
    DataQualityReport,
    ForeignKeyInfo,
)
from app.services.data_service import DataSourceService as CSVService
from app.services.database import engine

logger = get_logger(__name__)


class CSVProvider(ImportProvider):
    """Provider for importing CSV files."""
    
    def __init__(self):
        pass
    
    @property
    def format_name(self) -> str:
        return "csv"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _sanitize_column_name(self, col: str) -> str:
        """Sanitize column names to valid SQL identifiers."""
        name = str(col).lower()
        name = re.sub(r'[^a-z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "column"
    
    def _detect_data_type(self, series: pd.Series) -> str:
        """Detect pandas dtype and map to SQL type."""
        dtype = str(series.dtype)
        type_mapping = {
            'int64': 'INTEGER',
            'float64': 'FLOAT',
            'object': 'VARCHAR',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP',
        }
        return type_mapping.get(dtype, 'VARCHAR')
    
    def _is_numeric(self, series: pd.Series) -> bool:
        """Check if a column is numeric."""
        return pd.api.types.is_numeric_dtype(series)
    
    def _is_date(self, series: pd.Series) -> bool:
        """Check if a column appears to be a date/datetime."""
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        # Try to parse as date
        try:
            parsed = pd.to_datetime(series.dropna().iloc[:min(10, len(series))], errors='coerce')
            return parsed.notna().mean() > 0.8
        except Exception:
            return False
    
    async def validate(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate CSV file format."""
        try:
            # Check extension
            if not file.filename or not file.filename.endswith('.csv'):
                return False, "File extension must be .csv"
            
            # Valid content types for CSV
            valid_types = ["text/csv", "application/vnd.ms-excel", "application/octet-stream", "text/plain"]
            if file.content_type not in valid_types:
                return False, f"Invalid content type: {file.content_type}. Expected CSV."
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def preview(self, file: UploadFile) -> ImportPreview:
        """Generate preview of CSV data without importing."""
        content = await file.read()
        file_size = len(content)
        file_hash = self._calculate_file_hash(content)
        
        # Parse CSV
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise CSVValidationError(f"Could not parse CSV: {str(e)}")
        
        # Generate table metadata
        columns = []
        for col in df.columns:
            sanitized = self._sanitize_column_name(col)
            columns.append(ColumnMetadata(
                name=sanitized,
                original_name=str(col),
                data_type=self._detect_data_type(df[col]),
                nullable=df[col].isna().any(),
                is_numeric=self._is_numeric(df[col]),
                is_date=self._is_date(df[col]),
            ))
        
        table = TableMetadata(
            name=self._sanitize_column_name(file.filename),
            original_name=None,
            row_count=len(df),
            columns=columns,
        )
        
        # Generate quality report
        missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns if df[col].isna().any()}
        duplicate_rows = int(df.duplicated().sum())
        
        quality_report = DataQualityReport(
            total_rows=len(df),
            total_columns=len(df.columns),
            missing_values=missing_values,
            duplicate_rows=duplicate_rows,
            has_nulls=len(missing_values) > 0,
            has_duplicates=duplicate_rows > 0,
        )
        
        return ImportPreview(
            filename=file.filename or "unknown.csv",
            file_size=file_size,
            detected_format="csv",
            file_hash=file_hash,
            tables=[table],
            quality_report=quality_report,
            relationships=[],  # CSVs don't have relationships
        )
    
    async def parse(self, file: UploadFile, options: ImportOptions) -> Tuple[Any, ImportPreview]:
        """Parse CSV content."""
        content = await file.read()
        preview = await self.preview(file)
        
        # Apply column renames if specified
        df = pd.read_csv(io.BytesIO(content))
        
        if options.renamed_columns:
            for old_name, new_name in options.renamed_columns.get(preview.tables[0].name, {}).items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})
        
        # Clean column names
        df.columns = [self._sanitize_column_name(col) for col in df.columns]
        
        # Store original content for later import
        parsed_data = {
            "dataframe": df,
            "preview": preview,
        }
        
        return parsed_data, preview
    
    async def import_data(self, file: UploadFile, options: ImportOptions) -> ImportResult:
        """Import CSV data into the system."""
        # Use existing CSV service to process
        metadata = await CSVService.process_csv(file, engine)
        
        # Generate dataset name
        dataset_name = options.dataset_name or Path(file.filename or "upload").stem
        
        # The existing process_csv already creates a datasource entry
        # We need to get or create the source_id
        # For now, create a new source entry
        from app.services.data_source_service import save_source
        
        # Get the table name from metadata
        table_name = metadata["table_name"]
        
        # Create datasource entry for SQLite
        source_uuid = await self._register_datasource(dataset_name, table_name)
        
        return ImportResult(
            source_id=source_uuid,
            dataset_id=source_uuid,  # Same as source_id for CSV
            table_names=[table_name],
            total_rows=metadata.get("row_count", len(metadata.get("sample_data", []))),
            message=f"CSV '{dataset_name}' imported successfully with {len(metadata['columns'])} columns.",
        )
    
    async def _register_datasource(self, name: str, db_path: str) -> str:
        """Register a datasource in the registry."""
        from app.services.data_source_service import save_source
        
        result = save_source({
            "name": name,
            "db_type": "sqlite",
            "host": "",
            "port": None,
            "db_name": db_path,
            "username": "",
            "password": "",
        })
        return result.get("id", "")