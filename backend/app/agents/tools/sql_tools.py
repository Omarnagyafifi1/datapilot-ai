from app.services.db_service import DBService


def execute_sql(db_service: DBService, sql: str, source_id: str) -> list[dict]:
    return db_service.run_query(sql, source_id=source_id)
