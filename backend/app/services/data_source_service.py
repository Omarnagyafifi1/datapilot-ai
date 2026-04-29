from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, delete, insert, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
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
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("db_type", String(32), nullable=False),
    Column("host", String(255), nullable=False, default=""),
    Column("port", Integer, nullable=True),
    Column("db_name", String(255), nullable=False),
    Column("username", String(255), nullable=False, default=""),
    Column("enc_password", String(2048), nullable=False),
    Column("created_at", DateTime, nullable=False),
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


def _get_store_engine() -> Engine:
    global _REGISTRY_ENGINE

    if _REGISTRY_ENGINE is not None:
        return _REGISTRY_ENGINE

    db_url = settings.data_sources_db_url.strip()
    if not db_url:
        raise HTTPException(status_code=500, detail="Data source store is not configured")

    connect_args = {"timeout": 5} if db_url.startswith("sqlite:///") else {"connect_timeout": 5}
    _REGISTRY_ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _METADATA.create_all(_REGISTRY_ENGINE, tables=[_DATA_SOURCES])
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

    raise HTTPException(status_code=400, detail="Unsupported database type")


def save_source(params: dict) -> dict:
    test_result = db_service.test_connection(params)
    if not test_result.get("success"):
        return test_result

    encrypted_password = _get_fernet().encrypt(str(params.get("password", "")).encode("utf-8")).decode("utf-8")

    source_uuid = uuid4()
    payload = {
        "id": source_uuid,
        "name": str(params.get("name", "")).strip() or str(source_uuid),
        "db_type": str(params.get("db_type", "")).lower().strip(),
        "host": str(params.get("host", "")),
        "port": int(params["port"]) if params.get("port") is not None else None,
        "db_name": str(params.get("db_name") or params.get("database") or params.get("path") or ""),
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

    return {"success": True, "id": str(source_uuid)}


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
            result.append(item)
        return result
    finally:
        session.close()


def delete_source(id: str) -> None:
    try:
        source_uuid = UUID(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid data source id") from exc

    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        result = session.execute(delete(_DATA_SOURCES).where(_DATA_SOURCES.c.id == source_uuid))
        if result.rowcount == 0:
            session.rollback()
            raise HTTPException(status_code=404, detail="Data source not found")
        session.commit()
    finally:
        session.close()
        db_service.close_engine(id)


def get_conn_string(id: str) -> str:
    try:
        source_uuid = UUID(id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid data source id") from exc

    session_local = _get_session_factory()
    session: Session = session_local()
    try:
        row = session.execute(select(_DATA_SOURCES).where(_DATA_SOURCES.c.id == source_uuid)).mappings().first()
    finally:
        session.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        password = _get_fernet().decrypt(str(row["enc_password"]).encode("utf-8")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to decrypt password for source_id=%s", id)
        raise HTTPException(status_code=500, detail="Failed to load data source") from exc

    conn_string = _build_conn_string_from_source(dict(row), password)
    db_service.get_engine(source_id=id, conn_string=conn_string)
    return conn_string


class DataSourceService:
    def save_source(self, params: dict) -> dict:
        return save_source(params)

    def list_sources(self) -> list[dict]:
        return list_sources()

    def delete_source(self, id: str) -> None:
        delete_source(id)

    def get_conn_string(self, id: str) -> str:
        return get_conn_string(id)

