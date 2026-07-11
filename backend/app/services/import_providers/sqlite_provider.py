"""SQLite Database Import Provider for importing SQLite database files."""

import hashlib
import io
import os
import sqlite3
import tempfile
from typing import Any, List, Optional, Tuple
from fastapi import UploadFile
from datetime import datetime
from pathlib import Path

from app.core.logger import get_logger
from app.core.exceptions import CSVValidationError, DatabaseIngestionError
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

logger = get_logger(__name__)


def _get_upload_dir() -> str:
    """Get the absolute path for the upload directory."""
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    # If relative, resolve from the project root (backend/app)
    if not os.path.isabs(upload_dir):
        # Get the backend directory (parent of app/)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(backend_dir, upload_dir.lstrip("./"))
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


# Directory to store uploaded SQLite files (absolute path)
UPLOAD_DIR = _get_upload_dir()


class SQLiteProvider(ImportProvider):
    """Provider for importing SQLite database files."""
    
    # SQLite magic header bytes
    SQLITE_MAGIC_HEADER = b"SQLite format 3\x00"
    
    def __init__(self):
        pass
    
    @property
    def format_name(self) -> str:
        return "sqlite"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".db", ".sqlite", ".sqlite3"]
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _validate_sqlite_header(self, content: bytes) -> bool:
        """Validate SQLite file magic header."""
        return content.startswith(self.SQLITE_MAGIC_HEADER)
    
    def _sanitize_table_name(self, name: str) -> str:
        """Sanitize table names to valid SQL identifiers."""
        import re
        sanitized = re.sub(r'[^a-z0-9_]', '_', name.lower())
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized if sanitized else "table"
    
    async def validate(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate SQLite file format."""
        try:
            # Check extension
            if not file.filename:
                return False, "No filename provided"
            
            ext = Path(file.filename).suffix.lower()
            if ext not in self.supported_extensions:
                return False, f"File extension must be one of {self.supported_extensions}"
            
            # Read first bytes to check SQLite magic header
            await file.seek(0)
            content = await file.read(16)
            if not self._validate_sqlite_header(content):
                return False, "Invalid SQLite file format - file header does not match"
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def preview(self, file: UploadFile) -> ImportPreview:
        """Generate preview of SQLite database without importing."""
        await file.seek(0)
        content = await file.read()
        file_size = len(content)
        file_hash = self._calculate_file_hash(content)
        
        # Validate header
        if not self._validate_sqlite_header(content):
            raise DatabaseIngestionError("Invalid SQLite file format")
        
        # Connect to the uploaded database in memory
        try:
            # Write to a temporary file for reading
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            tables = []
            all_missing_values = {}
            total_rows = 0
            total_columns = 0
            relationships = []
            
            for table_name in table_names:
                # Get column info from pragma_table_info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fk_info = cursor.fetchall()
                
                for fk in fk_info:
                    # fk format: [id, seq, table, from, to, ...]
                    relationships.append(ForeignKeyInfo(
                        column=fk[3],
                        referenced_table=fk[2],
                        referenced_column=fk[4],
                    ))
                
                columns = []
                for col in columns_info:
                    # col format: [cid, name, type, notnull, dflt_value, pk]
                    col_name = col[1]
                    col_type = col[2] or "VARCHAR"
                    is_pk = bool(col[5])
                    is_nullable = not bool(col[3])
                    
                    columns.append(ColumnMetadata(
                        name=col_name,
                        original_name=col_name,
                        data_type=col_type.upper(),
                        nullable=is_nullable,
                        primary_key=is_pk,
                    ))
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                total_rows += row_count
                total_columns += len(columns)
                
                # Check for missing values in each column
                for col in columns:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col.name} IS NULL")
                    null_count = cursor.fetchone()[0]
                    if null_count > 0:
                        all_missing_values[f"{table_name}.{col.name}"] = null_count
                
                tables.append(TableMetadata(
                    name=self._sanitize_table_name(table_name),
                    original_name=table_name,
                    row_count=row_count,
                    columns=columns,
                ))
            
            conn.close()
            os.unlink(tmp_path)
            
            quality_report = DataQualityReport(
                total_rows=total_rows,
                total_columns=total_columns,
                missing_values=all_missing_values,
                duplicate_rows=0,  # SQLite doesn't track duplicates easily
                has_nulls=len(all_missing_values) > 0,
                has_duplicates=False,
            )
            
            return ImportPreview(
                filename=file.filename or "unknown.db",
                file_size=file_size,
                detected_format="sqlite",
                file_hash=file_hash,
                tables=tables,
                quality_report=quality_report,
                relationships=relationships,
            )
        except Exception as e:
            logger.exception("Failed to preview SQLite database")
            raise DatabaseIngestionError(f"Could not parse SQLite database: {str(e)}")
    
    async def parse(self, file: UploadFile, options: ImportOptions) -> Tuple[Any, ImportPreview]:
        """Parse SQLite content (just returns preview for SQLite)."""
        await file.seek(0)
        preview = await self.preview(file)
        return {"preview": preview}, preview
    
    async def import_data(self, file: UploadFile, options: ImportOptions) -> ImportResult:
        """Import SQLite database into the system."""
        await file.seek(0)
        content = await file.read()
        
        # Validate header
        if not self._validate_sqlite_header(content):
            raise DatabaseIngestionError("Invalid SQLite file format")
        
        # Generate unique filename for storage
        file_hash = self._calculate_file_hash(content)
        safe_name = "".join(c for c in file.filename or "uploaded.db" if c.isalnum() or c in "._-")
        stored_filename = f"{file_hash[:8]}_{safe_name}"
        stored_path = os.path.join(UPLOAD_DIR, stored_filename)

        # Save file to managed storage
        with open(stored_path, "wb") as f:
            f.write(content)

        # Also store in blob storage if configured
        try:
            from app.storage.blob_service import get_blob_service
            blob = get_blob_service()
            if blob.use_azure:
                blob_name = f"datasets/{stored_filename}"
                await blob.upload_bytes(content, blob_name, "application/octet-stream")
                logger.info("SQLite DB also uploaded to blob storage: %s", blob_name)
        except Exception:
            pass
        
        # Get preview for table names
        await file.seek(0)
        preview = await self.preview(file)
        
        # Filter selected tables if specified
        table_names = [t.original_name for t in preview.tables]
        if options.selected_tables:
            sanitized_selected = {self._sanitize_table_name(t) for t in options.selected_tables}
            table_names = [t for t in table_names if self._sanitize_table_name(t) in sanitized_selected]
        
        # Generate dataset name
        dataset_name = options.dataset_name or Path(file.filename or "sqlite_db").stem
        
        # Register as datasource
        from app.services.data_source_service import save_source
        
        result = save_source({
            "name": dataset_name,
            "db_type": "sqlite",
            "host": "",
            "port": None,
            "db_name": stored_path,
            "username": "",
            "password": "",
        })
        
        source_id = result.get("id", "")
        
        # Save dataset metadata for it to appear in the library
        try:
            from dataclasses import asdict
            from app.services.data_source_service import save_dataset_metadata
            
            tables_dict = [asdict(t) for t in preview.tables if t.original_name in table_names]
            relationships_dict = [asdict(r) for r in preview.relationships]
            quality_report_dict = asdict(preview.quality_report)
            
            save_dataset_metadata(
                source_id=source_id,
                name=dataset_name,
                source_type="sqlite",
                original_filename=file.filename or "unknown.db",
                file_size=len(content),
                file_hash=file_hash,
                tables=tables_dict,
                relationships=relationships_dict,
                quality_report=quality_report_dict,
            )
        except Exception as e:
            logger.exception("Failed to save dataset metadata during SQLite import: %s", e)
        
        return ImportResult(
            source_id=source_id,
            dataset_id=source_id,
            table_names=table_names,
            total_rows=sum(t.row_count for t in preview.tables if t.original_name in table_names),
            message=f"SQLite database '{dataset_name}' imported with {len(table_names)} tables.",
            stored_path=stored_path,
        )