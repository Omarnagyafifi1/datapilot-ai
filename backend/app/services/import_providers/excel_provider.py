"""Excel Import Provider - stub for future implementation."""

from typing import Any, List, Optional, Tuple
from fastapi import UploadFile

from app.services.import_providers import (
    ImportProvider,
    ImportPreview,
    ImportOptions,
    ImportResult,
)


class ExcelProvider(ImportProvider):
    """Provider for importing Excel files (stub for future implementation)."""
    
    def __init__(self):
        pass
    
    @property
    def format_name(self) -> str:
        return "excel"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx", ".xls"]
    
    async def validate(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate Excel file format."""
        if not file.filename:
            return False, "No filename provided"
        
        ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if ext not in ['xlsx', 'xls']:
            return False, f"File extension must be one of {self.supported_extensions}"
        
        # TODO: Implement actual validation
        raise NotImplementedError("Excel import is not yet implemented. Coming soon!")
    
    async def preview(self, file: UploadFile) -> ImportPreview:
        """Generate preview of Excel data without importing."""
        raise NotImplementedError("Excel import is not yet implemented. Coming soon!")
    
    async def parse(self, file: UploadFile, options: ImportOptions) -> Tuple[Any, ImportPreview]:
        """Parse Excel content."""
        raise NotImplementedError("Excel import is not yet implemented. Coming soon!")
    
    async def import_data(self, file: UploadFile, options: ImportOptions) -> ImportResult:
        """Import Excel data into the system."""
        raise NotImplementedError("Excel import is not yet implemented. Coming soon!")