import re
from urllib.parse import quote_plus

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.logger import get_logger


logger = get_logger(__name__)

_ENGINE_CACHE: dict[str, Engine] = {}
_SOURCE_CONN_STRINGS: dict[str, str] = {}
_BLOCKED_SQL_PATTERN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE)\b",
    re.IGNORECASE,
)


def _build_conn_string(params: dict) -> str:
    db_type = str(params.get("db_type", "")).lower().strip()

    if db_type not in {"postgresql", "mysql", "sqlite"}:
        raise ValueError("Unsupported database type")

    if db_type == "sqlite":
        db_path = params.get("path") or params.get("database")
        if not db_path:
            raise ValueError("Missing sqlite path")
        return f"sqlite:///{db_path}"

    user = params.get("user")
    password = quote_plus(str(params.get("password", "")))
    host = params.get("host")
    port = params.get("port")
    database = params.get("database")

    if not all([user, host, port, database]):
        raise ValueError("Missing required connection fields")

    if db_type == "postgresql":
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def get_engine(source_id: str, conn_string: str) -> Engine:
    cached = _ENGINE_CACHE.get(source_id)
    if cached is not None:
        return cached

    connect_args = {"timeout": 5} if conn_string.startswith("sqlite:///") else {"connect_timeout": 5}
    engine = create_engine(
        conn_string,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _ENGINE_CACHE[source_id] = engine
    _SOURCE_CONN_STRINGS[source_id] = conn_string
    return engine


def close_engine(source_id: str) -> None:
    engine = _ENGINE_CACHE.pop(source_id, None)
    _SOURCE_CONN_STRINGS.pop(source_id, None)
    if engine is not None:
        engine.dispose()


def test_connection(params: dict) -> dict:
    source_id = str(params.get("source_id", "default"))

    try:
        conn_string = params.get("conn_string") or _build_conn_string(params)
        engine = get_engine(source_id=source_id, conn_string=conn_string)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed database connection test for source_id=%s", source_id)
        close_engine(source_id)
        return {"success": False, "error": "Could not connect to database"}


def execute_query(sql: str, source_id: str) -> list[dict]:
    if _BLOCKED_SQL_PATTERN.search(sql):
        raise HTTPException(status_code=403, detail="Query not allowed")

    conn_string = _SOURCE_CONN_STRINGS.get(source_id)
    if conn_string is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        engine = get_engine(source_id=source_id, conn_string=conn_string)
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            if not result.returns_rows:
                return []
            return [dict(row) for row in result.mappings().all()]
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed query execution for source_id=%s", source_id)
        raise HTTPException(status_code=500, detail="Failed to execute query")


class DBService:
    def __init__(self, source_id: str = "default", conn_string: str | None = None) -> None:
        self.source_id = source_id
        if conn_string:
            _SOURCE_CONN_STRINGS[source_id] = conn_string

    def run_query(self, sql: str) -> list[dict]:
        return execute_query(sql=sql, source_id=self.source_id)

    def test_connection(self, params: dict) -> dict:
        params_with_source = {"source_id": self.source_id, **params}
        return test_connection(params_with_source)

    def close(self) -> None:
        close_engine(self.source_id)
