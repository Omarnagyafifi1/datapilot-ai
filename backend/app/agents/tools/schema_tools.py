from app.services.schema_service import SchemaService


def fetch_schema_context(schema_service: SchemaService) -> dict:
    return schema_service.get_schema()
