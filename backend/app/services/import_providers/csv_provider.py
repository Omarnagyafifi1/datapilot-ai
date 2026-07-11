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
from app.services import db_service

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
    
    def _generate_preview(self, content: bytes, filename: str) -> ImportPreview:
        """Generate preview of CSV data from bytes content."""
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
                nullable=bool(df[col].isna().any()),
                is_numeric=bool(self._is_numeric(df[col])),
                is_date=bool(self._is_date(df[col])),
            ))
        
        preview_table_name = self._sanitize_column_name(filename)
        if preview_table_name and preview_table_name[0].isdigit():
            preview_table_name = f"table_{preview_table_name}"
            
        table = TableMetadata(
            name=preview_table_name,
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
            filename=filename or "unknown.csv",
            file_size=file_size,
            detected_format="csv",
            file_hash=file_hash,
            tables=[table],
            quality_report=quality_report,
            relationships=[],  # CSVs don't have relationships
        )

    async def preview(self, file: UploadFile) -> ImportPreview:
        """Generate preview of CSV data without importing."""
        await file.seek(0)
        content = await file.read()
        return self._generate_preview(content, file.filename)
    
    async def parse(self, file: UploadFile, options: ImportOptions) -> Tuple[Any, ImportPreview]:
        """Parse CSV content."""
        await file.seek(0)
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
        from sqlalchemy import text as sql_text
        import os
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        if not os.path.isabs(upload_dir):
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            upload_dir = os.path.join(backend_dir, upload_dir.lstrip("./"))
        UPLOAD_DIR = upload_dir
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        await file.seek(0)
        content = await file.read()
        file_hash = self._calculate_file_hash(content)

        preview = self._generate_preview(content, file.filename)

        safe_name = "".join(c for c in file.filename or "uploaded.csv" if c.isalnum() or c in "._-")
        stored_filename = f"{file_hash[:8]}_{safe_name}"
        if not stored_filename.endswith('.csv'):
            stored_filename = stored_filename + '.csv'
        stored_path = os.path.join(UPLOAD_DIR, stored_filename)

        # Save locally (required for SQLite conversion)
        with open(stored_path, "wb") as f:
            f.write(content)

        # Also store in blob storage if configured
        try:
            from app.storage.blob_service import get_blob_service
            blob = get_blob_service()
            if blob.use_azure:
                blob_name = f"datasets/{stored_filename}"
                await blob.upload_bytes(content, blob_name, "text/csv")
                logger.info("CSV also uploaded to blob storage: %s", blob_name)
        except Exception:
            pass
        
        # Generate dataset name
        dataset_name = options.dataset_name or Path(file.filename or "upload").stem
        source_id = f"csv_{file_hash[:8]}"
        
        try:
            # Use db_service.upload_csv_to_sqlite to create SQLite DB from CSV
            # This handles everything without needing an external DATABASE_URL
            target_table_name = preview.tables[0].name if preview.tables else "uploaded_csv"
            conn_string, table_name = db_service.upload_csv_to_sqlite(stored_path, source_id, target_table_name)
        except Exception as e:
            raise CSVValidationError(f"Failed to import CSV to database: {str(e)}")
        
        # Extract the SQLite file path from the connection string for registry
        db_path = conn_string[10:] if conn_string.startswith("sqlite:///") else conn_string
        
        # Create datasource entry for SQLite
        source_uuid = await self._register_datasource(dataset_name, db_path)
        
        # Save dataset metadata for it to appear in the library
        try:
            from dataclasses import asdict
            from app.services.data_source_service import save_dataset_metadata
            
            tables_dict = [asdict(t) for t in preview.tables]
            relationships_dict = [asdict(r) for r in preview.relationships]
            quality_report_dict = asdict(preview.quality_report)
            
            save_dataset_metadata(
                source_id=source_uuid,
                name=dataset_name,
                source_type="csv",
                original_filename=file.filename or "unknown.csv",
                file_size=len(content),
                file_hash=file_hash,
                tables=tables_dict,
                relationships=relationships_dict,
                quality_report=quality_report_dict,
            )
        except Exception as e:
            logger.exception("Failed to save dataset metadata during CSV import: %s", e)
            try:
                from app.services.data_source_service import delete_source
                delete_source(source_uuid)
            except Exception:
                logger.exception("Failed to roll back datasource after metadata failure")
            raise CSVValidationError(f"Failed to save dataset metadata: {str(e)}")
        
        # Get row count from the created table
        try:
            with db_service.get_engine(source_id, conn_string).connect() as conn:
                result = conn.execute(sql_text(f'SELECT COUNT(*) FROM "{table_name}"'))
                total_rows = result.scalar()
        except Exception:
            # Fallback: estimate from preview
            total_rows = preview.tables[0].row_count if preview.tables else 0
        
        return ImportResult(
            source_id=source_uuid,
            dataset_id=source_uuid,
            table_names=[table_name],
            total_rows=total_rows,
            message=f"CSV '{dataset_name}' imported successfully into table '{table_name}'.",
            stored_path=stored_path,
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
