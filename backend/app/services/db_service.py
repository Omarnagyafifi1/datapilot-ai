import os
import re

import pandas as pd
import sqlite3
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from fastapi import HTTPException
from urllib.parse import quote_plus
from app.core.logger import get_logger

logger = get_logger(__name__)

_ENGINE_CACHE: dict[str, Engine] = {}
_SOURCE_CONN_STRINGS: dict[str, str] = {}
_MONTH_NAME_TO_NUMBER = {
    "january": "01",
    "jan": "01",
    "february": "02",
    "feb": "02",
    "march": "03",
    "mar": "03",
    "april": "04",
    "apr": "04",
    "may": "05",
    "june": "06",
    "jun": "06",
    "july": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "sept": "09",
    "october": "10",
    "oct": "10",
    "november": "11",
    "nov": "11",
    "december": "12",
    "dec": "12",
}


def _normalize_numeric_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric-like text columns (currency/comma formatted) into numeric values."""
    normalized = df.copy()
    candidate_columns = normalized.select_dtypes(include=["object"]).columns
    strong_numeric_ratio = 0.98

    for column_name in candidate_columns:
        series = normalized[column_name].astype(str).str.strip()
        cleaned = (
            series.str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("€", "", regex=False)
            .str.replace("£", "", regex=False)
        )
        numeric = pd.to_numeric(cleaned, errors="coerce")
        ratio = float(numeric.notna().mean())
        if ratio >= strong_numeric_ratio:
            normalized[column_name] = numeric

    return normalized


def _dialect_from_conn_string(conn_string: str) -> str:
    prefix = conn_string.split(":", 1)[0].lower()
    return prefix.split("+", 1)[0]


def _strip_identifier_quotes(identifier: str) -> str:
    return identifier.strip().strip('"').strip("`").strip("[]")


def _rewrite_month_name_like_filters(sql: str) -> str:
    """Rewrite Date LIKE '%May%' patterns into month-aware SQLite filtering for DD/MM/YYYY text."""

    def replace(match: re.Match[str]) -> str:
        column_expr = match.group("column")
        month_name = match.group("month").lower()
        month_number = _MONTH_NAME_TO_NUMBER.get(month_name)
        if month_number is None:
            return match.group(0)

        normalized_column_name = _strip_identifier_quotes(column_expr).lower()
        if "date" not in normalized_column_name:
            return match.group(0)

        return f"SUBSTR({column_expr}, 4, 2) = '{month_number}'"

    pattern = re.compile(
        r"(?P<column>\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|\w+)\s+LIKE\s+'%(?P<month>[A-Za-z]+)%'",
        re.IGNORECASE,
    )
    return pattern.sub(replace, sql)


def _rewrite_month_extraction_filters(sql: str) -> str:
    """Rewrite non-SQLite month extraction into DD/MM/YYYY-friendly predicates."""

    def month_replacement(column_expr: str, month_value: str, original: str) -> str:
        normalized_column_name = _strip_identifier_quotes(column_expr).lower()
        if "date" not in normalized_column_name:
            return original

        month_number = month_value.zfill(2)
        return f"SUBSTR({column_expr}, 4, 2) = '{month_number}'"

    extract_pattern = re.compile(
        r"EXTRACT\s*\(\s*MONTH\s+FROM\s+"
        r"(?:TO_DATE\s*\(\s*(?P<extract_to_date_col>\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|\w+)\s*,\s*'[^']*'\s*\)"
        r"|(?P<extract_col>\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|\w+))\s*\)\s*=\s*'?(?P<extract_month>\d{1,2})'?",
        re.IGNORECASE,
    )

    def replace_extract(match: re.Match[str]) -> str:
        column_expr = match.group("extract_to_date_col") or match.group("extract_col")
        month_value = match.group("extract_month")
        return month_replacement(column_expr, month_value, match.group(0))

    rewritten = extract_pattern.sub(replace_extract, sql)

    strftime_pattern = re.compile(
        r"STRFTIME\s*\(\s*'%m'\s*,\s*(?P<strftime_col>\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|\w+)\s*\)\s*=\s*'?(?P<strftime_month>\d{1,2})'?",
        re.IGNORECASE,
    )

    def replace_strftime(match: re.Match[str]) -> str:
        column_expr = match.group("strftime_col")
        month_value = match.group("strftime_month")
        return month_replacement(column_expr, month_value, match.group(0))

    return strftime_pattern.sub(replace_strftime, rewritten)


def _normalize_conn_string_for_sync(conn_string: str) -> str:
    lowered = conn_string.lower()
    if lowered.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + conn_string[len("postgresql+asyncpg://") :]
    return conn_string


def upload_csv_to_sqlite(csv_path: str, source_id: str) -> tuple[str, str]:
    """Uploads a CSV to a temporary SQLite database and returns (conn_string, table_name)."""
    try:
        df = pd.read_csv(csv_path)
        df = _normalize_numeric_text_columns(df)
        # Create a filename for the sqlite db based on source_id
        db_path = os.path.join(os.getcwd(), f"{source_id}.db")
        conn_string = f"sqlite:///{db_path}"
        
        engine = create_engine(conn_string)
        # Use the filename (without extension) as the table name
        table_name = os.path.splitext(os.path.basename(csv_path))[0].replace(" ", "_").replace("(", "").replace(")", "").lower()
        
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        
        _SOURCE_CONN_STRINGS[source_id] = conn_string
        logger.info(f"Successfully uploaded {csv_path} to {db_path} as table {table_name}")
        return conn_string, table_name
    except Exception as e:
        logger.error(f"Failed to upload CSV: {e}")
        raise HTTPException(status_code=500, detail=f"CSV upload failed: {str(e)}")

def get_engine(source_id: str, conn_string: str) -> Engine:
    normalized_conn_string = _normalize_conn_string_for_sync(conn_string)
    cached = _ENGINE_CACHE.get(source_id)
    if cached is not None and _SOURCE_CONN_STRINGS.get(source_id) == normalized_conn_string:
        return cached
    engine = create_engine(normalized_conn_string)
    _ENGINE_CACHE[source_id] = engine
    _SOURCE_CONN_STRINGS[source_id] = normalized_conn_string
    return engine

def execute_query(sql: str, source_id: str) -> list[dict]:
    conn_string = _SOURCE_CONN_STRINGS.get(source_id)
    if conn_string is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        dialect = _dialect_from_conn_string(conn_string)
        rewritten_sql = sql
        if dialect == "sqlite":
            rewritten_sql = _rewrite_month_extraction_filters(_rewrite_month_name_like_filters(sql))
        engine = get_engine(source_id=source_id, conn_string=conn_string)
        with engine.connect() as connection:
            result = connection.execute(text(rewritten_sql))
            if not result.returns_rows:
                return []
            return [dict(row) for row in result.mappings().all()]
    except Exception as exc:
        logger.exception("Failed query execution for source_id=%s", source_id)
        raise HTTPException(status_code=500, detail=f"Failed to execute query: {str(exc)}")


def test_connection(params: dict) -> dict:
    """Test a database connection using the provided parameters.

    Builds a temporary connection string from the params dict and executes
    a lightweight query (``SELECT 1``) to validate connectivity.

    Returns ``{"success": True}`` on success, or
    ``{"success": False, "error": "<message>"}`` on failure.
    """
    db_type = str(params.get("db_type", "")).lower().strip()
    host = str(params.get("host", ""))
    port = params.get("port")
    db_name = str(params.get("db_name") or params.get("database") or params.get("path") or "")
    username = str(params.get("username") or params.get("user") or "")
    password = str(params.get("password", ""))

    try:
        from urllib.parse import quote_plus
        if db_type == "sqlite":
            conn_string = f"sqlite:///{db_name}"
        elif db_type == "postgresql":
            conn_string = f"postgresql+psycopg2://{username}:{quote_plus(password)}@{host}:{port}/{db_name}"
        elif db_type == "mysql":
            conn_string = f"mysql+pymysql://{username}:{quote_plus(password)}@{host}:{port}/{db_name}"
        elif db_type == "mssql":
            conn_string = f"mssql+pyodbc://{username}:{quote_plus(password)}@{host}:{port or '1433'}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
        elif db_type == "oracle":
            conn_string = f"oracle+cx_oracle://{username}:{quote_plus(password)}@{host}:{port or '1521'}/?service_name={db_name}"
        else:
            return {"success": False, "error": f"Unsupported database type: {db_type}"}

        engine = create_engine(conn_string, connect_args={"connect_timeout": 5} if db_type != "sqlite" else {})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return {"success": True}
    except Exception as exc:
        logger.warning("test_connection failed for db_type=%s host=%s: %s", db_type, host, exc)
        return {"success": False, "error": str(exc)}


def close_engine(source_id: str) -> None:
    """Dispose and remove the cached engine for a given source_id."""
    engine = _ENGINE_CACHE.pop(source_id, None)
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            logger.exception("Failed to dispose engine for source_id=%s", source_id)
    _SOURCE_CONN_STRINGS.pop(source_id, None)


def get_source_schema(source_id: str) -> dict:
    conn_string = _SOURCE_CONN_STRINGS.get(source_id)
    if conn_string is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        engine = get_engine(source_id=source_id, conn_string=conn_string)
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables: list[dict] = []

            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                tables.append(
                    {
                        "name": table_name,
                        "columns": [
                            {
                                "name": column["name"],
                                "type": str(column["type"]),
                                "nullable": column.get("nullable", True),
                                "primary_key": column.get("primary_key", False),
                            }
                            for column in columns
                        ],
                    }
                )

            return {"tables": tables}
    except Exception as exc:
        logger.exception("Failed schema fetch for source_id=%s", source_id)
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(exc)}")

class DBService:
    def __init__(self, source_id: str = "default", conn_string: str | None = None) -> None:
        self.source_id = source_id
        if conn_string:
            _SOURCE_CONN_STRINGS[source_id] = _normalize_conn_string_for_sync(conn_string)

    def get_dialect(self, source_id: str | None = None) -> str:
        resolved_source_id = source_id or self.source_id
        conn_string = _SOURCE_CONN_STRINGS.get(resolved_source_id)
        if conn_string is None:
            return "sqlite"
        return _dialect_from_conn_string(conn_string)

    def run_query(self, sql: str, source_id: str | None = None, timeout: int | None = None) -> list[dict]:
        resolved_source_id = source_id or self.source_id
        return execute_query(sql=sql, source_id=resolved_source_id)
