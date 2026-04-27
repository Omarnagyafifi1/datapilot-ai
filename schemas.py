from pydantic import BaseModel
from typing import List, Dict, Any

class UploadMetadata(BaseModel):
    table_name: str
    columns: Dict[str, str]
    sample_data: List[Dict[str, Any]]

class UploadResponse(BaseModel):
    message: str
    metadata: UploadMetadata
