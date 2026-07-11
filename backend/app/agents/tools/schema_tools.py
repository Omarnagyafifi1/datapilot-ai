import json
from typing import Any
from app.services.db_service import get_source_schema

def fetch_schema_context(schema_service: Any, source_id: str) -> str:
    schema = get_source_schema(source_id)
    return json.dumps(schema, separators=(',', ':'))
