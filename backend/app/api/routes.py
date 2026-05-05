import time
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.api.deps import get_data_source_service, get_graph_orchestrator, get_history_service
from app.core.logger import get_logger
from app.models.schemas import (
    ConnectRequest,
    DataSourceResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    QueryHistoryResponse,
    SystemStatsResponse,
    ActivityFeedResponse,
    SchemaResponse,
)
from app.services.data_source_service import DataSourceService
from app.services.history_service import HistoryService
from app.services import db_service
from app.services.data_service import DataSourceService as CSVService
from app.services.database import engine


router = APIRouter(prefix="/api", tags=["api"])
logger = get_logger(__name__)


def _resp(success: bool, message: str, data: dict | list | None) -> JSONResponse:
    payload = {
        "success": success,
        "message": message,
        "data": data,
    }
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return JSONResponse(content=payload, headers=headers)


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/query")
def query_endpoint(
    payload: QueryRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
    graph=Depends(get_graph_orchestrator),
) -> dict:
    start_time = time.time()
    status = "SUCCESS"
    try:
        data_source_service.get_conn_string(payload.source_id)
        result = graph.run(payload.question, payload.source_id)
        # Return raw result dict but wrap in JSONResponse to include CORS headers
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(content=result, headers=headers)
    except Exception as e:
        status = "ERROR"
        logger.exception("Query failed")
        # Return an explicit error payload so callers (and dev tools)
        # can see the underlying exception text instead of a generic 500.
        return _resp(success=False, message=f"Query failed: {str(e)}", data=None)
    finally:
        latency = time.time() - start_time
        try:
            history_service.save_query(
                question=payload.question,
                source_id=payload.source_id,
                status=status,
                latency=latency
            )
        except Exception:
            logger.exception("Failed to save query history in finally block")


@router.post("/datasources/connect")
def connect_datasource(
    req: ConnectRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    logger.info("Connect attempt: %s://%s password=***", req.db_type, req.host)
    payload = {
        "name": req.name,
        "db_type": req.db_type,
        "host": req.host,
        "port": req.port,
        "db_name": req.db_name,
        "database": req.db_name,
        "username": req.username,
        "user": req.username,
        "password": req.password,
    }

    result = data_source_service.save_source(payload)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Connection failed")

    return _resp(success=True, message="Data source connected", data=result)


@router.get("/datasources")
def list_datasources(
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    sources = data_source_service.list_sources()
    data: list[dict[str, Any]] = []
    for source in sources:
        normalized = DataSourceResponse(
            id=str(source["id"]),
            name=source["name"],
            db_type=source["db_type"],
            host=source["host"],
            db_name=source["db_name"],
            created_at=source["created_at"],
        )
        data.append(normalized.model_dump())
    return _resp(success=True, message="Data sources fetched", data=data)


@router.delete("/datasources/{id}")
def delete_datasource(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    data_source_service.delete_source(id)
    return _resp(success=True, message="Data source deleted", data=None)


@router.get("/query-history", response_model=QueryHistoryResponse)
def get_query_history(
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    history = history_service.list_history()
    return _resp(success=True, message="Query history fetched", data=history)


@router.get("/datasources/{id}/schema", response_model=SchemaResponse)
def get_datasource_schema(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    data_source_service.get_conn_string(id)
    schema = db_service.get_source_schema(id)
    return _resp(success=True, message="Schema fetched", data=schema.get("tables", []))


@router.get("/system/stats", response_model=SystemStatsResponse)
def get_system_stats(
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    sources = data_source_service.list_sources()
    stats = history_service.get_stats()
    stats["total_sources"] = len(sources)
    return _resp(success=True, message="System stats fetched", data=stats)


@router.get("/system/feed", response_model=ActivityFeedResponse)
def get_system_feed(
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    feed = history_service.get_feed()
    return _resp(success=True, message="Activity feed fetched", data=feed)


@router.post('/data/csv')
async def upload_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a CSV and ingest it into the configured PostgreSQL database."""
    try:
        metadata = await CSVService.process_csv(file, engine)
        return _resp(success=True, message="CSV ingested", data=metadata)
    except Exception as e:
        logger.exception("CSV ingest failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/explain')
def explain_sql(payload: dict) -> dict[str, Any]:
    """Return a lightweight explanation of a SQL query. Expects JSON { sql: str }."""
    sql = payload.get('sql') if isinstance(payload, dict) else None
    if not sql:
        raise HTTPException(status_code=400, detail="Missing 'sql' in request body")

    try:
        s = sql.replace('\n', ' ').replace('\t', ' ')
        s = ' '.join(s.split())
        sel = (s.lower().split('select ')[1].split(' from')[0] if 'select ' in s.lower() and ' from' in s.lower() else '')
        from_part = ''
        import re
        m = re.search(r'from (.+?)( where| group by| order by| limit|$)', s, flags=re.IGNORECASE)
        if m:
            from_part = m.group(1)
        group = None
        m2 = re.search(r'group by (.+?)( order by| limit|$)', s, flags=re.IGNORECASE)
        if m2:
            group = m2.group(1)
        order = None
        m3 = re.search(r'order by (.+?)( limit|$)', s, flags=re.IGNORECASE)
        if m3:
            order = m3.group(1)
        limit = None
        m4 = re.search(r'limit (\d+)', s, flags=re.IGNORECASE)
        if m4:
            limit = m4.group(1)

        parts = []
        if sel:
            parts.append(f"Selects columns: {sel}")
        if from_part:
            parts.append(f"From tables / joins: {from_part}")
        if group:
            parts.append(f"Grouped by: {group}")
        if order:
            parts.append(f"Ordered by: {order}")
        if limit:
            parts.append(f"Limit: {limit}")

        explanation = '. '.join(parts) if parts else 'Could not parse SQL for explanation.'
        return _resp(success=True, message='Explained', data=explanation)
    except Exception as e:
        logger.exception('Explain failed')
        raise HTTPException(status_code=500, detail='Explain failed')
