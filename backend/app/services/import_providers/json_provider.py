"""JSON Import Provider - stub for future implementation."""

from typing import Any, List, Optional, Tuple
from fastapi import UploadFile

from app.services.import_providers import (
    ImportProvider,
    ImportPreview,
    ImportOptions,
    ImportResult,
)


class JSONProvider(ImportProvider):
    """Provider for importing JSON files (stub for future implementation)."""
    
    def __init__(self):
        pass
    
    @property
    def format_name(self) -> str:
        return "json"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]
    
    async def validate(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """Validate JSON file format."""
        if not file.filename:
            return False, "No filename provided"
        
        ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if ext not in ['json']:
            return False, f"File extension must be one of {self.supported_extensions}"
        
        # TODO: Implement actual validation
        raise NotImplementedError("JSON import is not yet implemented. Coming soon!")
    
    async def preview(self, file: UploadFile) -> ImportPreview:
        """Generate preview of JSON data without importing."""
        raise NotImplementedError("JSON import is not yet implemented. Coming soon!")
    
    async def parse(self, file: UploadFile, options: ImportOptions) -> Tuple[Any, ImportPreview]:
        """Parse JSON content."""
        raise NotImplementedError("JSON import is not yet implemented. Coming soon!")
    
    async def import_data(self, file: UploadFile, options: ImportOptions) -> ImportResult:
        """Import JSON data into the system."""
        raise NotImplementedError("JSON import is not yet implemented. Coming soon!")