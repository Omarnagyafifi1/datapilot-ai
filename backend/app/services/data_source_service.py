from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from uuid import UUID, uuid4
import uuid
import json

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, delete, insert, select, update, Text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logger import get_logger
from app.services import db_service


logger = get_logger(__name__)

_METADATA = MetaData()
_DATA_SOURCES = Table(
    "data_sources",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("db_type", String(32), nullable=False),
    Column("host", String(255), nullable=False, default=""),
    Column("port", Integer, nullable=True),
    Column("db_name", String(255), nullable=False),
    Column("username", String(255), nullable=False, default=""),
    Column("enc_password", String(2048), nullable=False),
    Column("created_at", DateTime, nullable=False),
)

_DATASET_METADATA = Table(
    "dataset_metadata",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column("source_id", String(36), nullable=False),
    Column("name", String(255), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("original_filename", String(255), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("file_hash", String(64), nullable=False),
    Column("import_timestamp", DateTime, nullable=False),
    Column("table_count", Integer, nullable=False),
    Column("total_row_count", Integer, nullable=False),
    Column("column_count", Integer, nullable=False),
    Column("tables_json", Text, nullable=True),
    Column("relationships_json", Text, nullable=True),
    Column("quality_report_json", Text, nullable=True),
    Column("ai_summary", Text, nullable=True),
)

_REGISTRY_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None


def _get_fernet() -> Fernet:
    key = settings.encryption_key.strip()
    if not key:
        raise HTTPException(status_code=500, detail="Encryption key is not configured")
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Invalid ENCRYPTION_KEY configuration")
        raise HTTPException(status_code=500, detail="Encryption key is invalid") from exc


def _migrate_sqlite_paths() -> None:
    """Migrate any SQLite source with a relative db_name to an absolute path."""
    try:
        session_local = _get_session_factory()
        session: Session = session_local()
        rows = session.execute(
            select(_DATA_SOURCES).where(_DATA_SOURCES.c.db_type == "sqlite")
        ).mappings().all()
        changed = False
        for row in rows:
            db_name = row["db_name"]
            if db_name and not os.path.isabs(db_name):
                abs_path = os.path.abspath(db_name)
                session.execute(
                    update(_DATA_SOURCES)
                    .where(_DATA_SOURCES.c.id == row["id"])
                    .values(db_name=abs_path)
                )
                logger.info("Migrated SQLite path: %s -> %s", db_name, abs_path)
                changed = True
        if changed:
            session.commit()
        session.close()
    except Exception as exc:
        logger.warning("Failed to migrate SQLite paths: %s", exc)


def _get_store_engine() -> Engine:
    global _REGISTRY_ENGINE

    if _REGISTRY_ENGINE is not None:
        return _REGISTRY_ENGINE

    db_url = settings.data_sources_db_url.strip()
    if not db_url:
        db_url = "sqlite:///./data_sources.db"

    connect_args = {"timeout": 5} if db_url.startswith("sqlite:///") else {"connect_timeout": 5}
    _REGISTRY_ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _METADATA.create_all(_REGISTRY_ENGINE, tables=[_DATA_SOURCES, _DATASET_METADATA])
    _migrate_sqlite_paths()
    return _REGISTRY_ENGINE


def _get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY

    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=_get_store_engine(), autoflush=False, autocommit=False)
    return _SESSION_FACTORY


def _build_conn_string_from_source(source: dict, password: str) -> str:
    db_type = str(source["db_type"]).lower()

    if db_type == "sqlite":
        return f"sqlite:///{source['db_name']}"

    encoded_password = quote_plus(password)
    username = source["username"]
    host = source["host"]
    port = source["port"]
    db_name = source["db_name"]

    if db_type == "postgresql":
        return f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{db_name}"
    if db_type == "mysql":
        return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{db_name}"
    if db_type == "mssql":
        return f"mssql+pymssql://{username}:{encoded_password}@{host}:{port or '1433'}/{db_name}"
    if db_type == "oracle":
        return f"oracle+oracledb://{username}:{encoded_password}@{host}:{port or '1521'}/?service_name={db_name}"

    raise HTTPException(status_code=400, detail="Unsupported database type")


def save_source(params: dict) -> dict:
    # For SQLite sources, skip the network test_connection
    db_type_lower = str(params.get("db_type", "")).lower()
    if db_type_lower != "sqlite":
        test_result = db_service.test_connection(params)
        if not test_result.get("success"):
            return test_result

    encrypted_password = _get_fernet().encrypt(str(params.get("password", "")).encode("utf-8")).decode("utf-8")

    db_name = str(params.get("db_name") or params.get("database") or params.get("path") or "")
    if db_type_lower == "sqlite" and db_name:
        db_name = os.path.abspath(db_name)

    source_uuid = str(uuid4())
    payload = {
        "id": source_uuid,
        "name": str(params.get("name", "")).strip() or source_uuid,
        "db_type": db_type_lower,
        "host": str(params.get("host", "")),
        "port": int(params["port"]) if params.get("port") is not None else None,
        "db_name": db_name,
        "username": str(params.get("username") or params.get("user") or ""),
        "enc_password": encrypted_password,
        "created_at": datetime.utcnow(),
    }

    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        session.execute(insert(_DATA_SOURCES).values(**payload))
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("Failed to save data source")
        raise HTTPException(status_code=500, detail="Failed to save data source") from exc
    finally:
        session.close()

    return {"success": True, "id": source_uuid}


def list_sources() -> list[dict]:
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        rows = session.execute(
            select(
                _DATA_SOURCES.c.id,
                _DATA_SOURCES.c.name,
                _DATA_SOURCES.c.db_type,
                _DATA_SOURCES.c.host,
                _DATA_SOURCES.c.port,
                _DATA_SOURCES.c.db_name,
                _DATA_SOURCES.c.username,
                _DATA_SOURCES.c.created_at,
            )
        ).mappings().all()
        result: list[dict] = []
        for row in rows:
            item = dict(row)
            item["id"] = str(item["id"])
            # Convert datetime to ISO string for JSON serialization
            if hasattr(item.get("created_at"), "isoformat"):
                item["created_at"] = item["created_at"].isoformat()
            result.append(item)
        return result
    finally:
        session.close()


def delete_source(id: str) -> None:
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        result = session.execute(delete(_DATA_SOURCES).where(_DATA_SOURCES.c.id == id))
        if result.rowcount == 0:
            session.rollback()
            raise HTTPException(status_code=404, detail="Data source not found")
        session.commit()
    finally:
        session.close()
        db_service.close_engine(id)


def get_conn_string(id: str) -> str:
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(select(_DATA_SOURCES).where(_DATA_SOURCES.c.id == id)).mappings().first()
    finally:
        session.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        password = _get_fernet().decrypt(str(row["enc_password"]).encode("utf-8")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        if str(row["db_type"]).lower() == "sqlite":
            password = ""
        else:
            logger.exception("Failed to decrypt password for source_id=%s", id)
            raise HTTPException(status_code=500, detail="Failed to load data source") from exc

    conn_string = _build_conn_string_from_source(dict(row), password)
    db_service.get_engine(source_id=id, conn_string=conn_string)
    return conn_string


# Dataset Metadata Methods
def save_dataset_metadata(
    source_id: str,
    name: str,
    source_type: str,
    original_filename: str,
    file_size: int,
    file_hash: str,
    tables: list,
    relationships: list,
    quality_report: dict,
    ai_summary: str = None,
) -> str:
    """Save dataset metadata to the registry."""
    dataset_uuid = str(uuid4())
    
    # Calculate summary stats
    table_count = len(tables)
    total_row_count = sum(t.get("row_count", 0) for t in tables)
    column_count = sum(len(t.get("columns", [])) for t in tables)
    
    payload = {
        "id": dataset_uuid,
        "source_id": source_id,
        "name": name,
        "source_type": source_type,
        "original_filename": original_filename,
        "file_size": file_size,
        "file_hash": file_hash,
        "import_timestamp": datetime.utcnow(),
        "table_count": table_count,
        "total_row_count": total_row_count,
        "column_count": column_count,
        "tables_json": json.dumps(tables) if tables else None,
        "relationships_json": json.dumps(relationships) if relationships else None,
        "quality_report_json": json.dumps(quality_report) if quality_report else None,
        "ai_summary": ai_summary,
    }
    
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        session.execute(insert(_DATASET_METADATA).values(**payload))
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to save dataset metadata")
        raise HTTPException(status_code=500, detail="Failed to save dataset metadata") from exc
    finally:
        session.close()
    
    return dataset_uuid


def get_dataset_by_hash(file_hash: str) -> Optional[dict]:
    """Check if a dataset with the same file hash already exists."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(
            select(_DATASET_METADATA).where(_DATASET_METADATA.c.file_hash == file_hash)
        ).mappings().first()
        if row:
            return dict(row)
        return None
    finally:
        session.close()


def list_datasets(search_query: str = None, source_type: str = None) -> list[dict]:
    """List all datasets with optional filtering."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        stmt = select(
            _DATASET_METADATA.c.id,
            _DATASET_METADATA.c.source_id,
            _DATASET_METADATA.c.name,
            _DATASET_METADATA.c.source_type,
            _DATASET_METADATA.c.original_filename,
            _DATASET_METADATA.c.file_size,
            _DATASET_METADATA.c.file_hash,
            _DATASET_METADATA.c.import_timestamp,
            _DATASET_METADATA.c.table_count,
            _DATASET_METADATA.c.total_row_count,
            _DATASET_METADATA.c.column_count,
            _DATASET_METADATA.c.ai_summary,
        )
        
        if search_query:
            stmt = stmt.where(_DATASET_METADATA.c.name.ilike(f"%{search_query}%"))
        if source_type:
            stmt = stmt.where(_DATASET_METADATA.c.source_type == source_type)
        
        rows = session.execute(stmt).mappings().all()
        result = []
        for row in rows:
            item = dict(row)
            if hasattr(item.get("import_timestamp"), "isoformat"):
                item["import_timestamp"] = item["import_timestamp"].isoformat()
            result.append(item)
        return result
    finally:
        session.close()


def get_dataset(id: str) -> Optional[dict]:
    """Get a single dataset by ID."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(
            select(_DATASET_METADATA).where(_DATASET_METADATA.c.id == id)
        ).mappings().first()
        if row:
            return dict(row)
        return None
    finally:
        session.close()


def delete_dataset(id: str) -> None:
    """Delete a dataset and its associated datasource."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        # Get source_id first
        row = session.execute(
            select(_DATASET_METADATA.c.source_id).where(_DATASET_METADATA.c.id == id)
        ).mappings().first()
        
        if row:
            # Delete dataset metadata
            session.execute(delete(_DATASET_METADATA).where(_DATASET_METADATA.c.id == id))
            # Delete the source
            session.execute(delete(_DATA_SOURCES).where(_DATA_SOURCES.c.id == row["source_id"]))
            session.commit()
        else:
            session.rollback()
            raise HTTPException(status_code=404, detail="Dataset not found")
    finally:
        session.close()


def update_dataset_name(id: str, name: str) -> None:
    """Update the name of a dataset."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        session.execute(
            _DATASET_METADATA.update().where(_DATASET_METADATA.c.id == id).values(name=name)
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update dataset") from exc
    finally:
        session.close()


def update_ai_summary(id: str, summary: str) -> None:
    """Update the AI summary for a dataset."""
    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        session.execute(
            _DATASET_METADATA.update().where(_DATASET_METADATA.c.id == id).values(ai_summary=summary)
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update AI summary") from exc
    finally:
        session.close()


class DataSourceService:
    def save_source(self, params: dict) -> dict:
        return save_source(params)

    def list_sources(self) -> list[dict]:
        return list_sources()

    def delete_source(self, id: str) -> None:
        delete_source(id)

    def get_conn_string(self, id: str) -> str:
        return get_conn_string(id)

    def save_dataset_metadata(self, **kwargs) -> str:
        return save_dataset_metadata(**kwargs)

    def get_dataset_by_hash(self, file_hash: str) -> Optional[dict]:
        return get_dataset_by_hash(file_hash)

    def list_datasets(self, search_query: str = None, source_type: str = None) -> list[dict]:
        return list_datasets(search_query=search_query, source_type=source_type)

    def get_dataset(self, id: str) -> Optional[dict]:
        return get_dataset(id)

    def delete_dataset(self, id: str) -> None:
        delete_dataset(id)

    def update_dataset_name(self, id: str, name: str) -> None:
        update_dataset_name(id, name)

    def update_ai_summary(self, id: str, summary: str) -> None:
        update_ai_summary(id, summary)