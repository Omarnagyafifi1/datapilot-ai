from app.services.schema_service import SchemaService


def fetch_schema_context(schema_service: SchemaService) -> str:
    schema = schema_service.get_schema()
    if isinstance(schema, dict):
        import json
        return json.dumps(schema, indent=2)
    return str(schema)
