import json
from app.services.db_service import get_source_schema
from app.services.schema_service import SchemaService

def fetch_schema_context(schema_service: SchemaService, source_id: str) -> str:
    del schema_service
    schema = get_source_schema(source_id)
    return json.dumps(schema, indent=2)
