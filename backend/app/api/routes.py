import time
from typing import Any
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.api.deps import get_data_source_service, get_graph_orchestrator, get_history_service
from app.core.logger import get_logger
from app.models.schemas import (
    ConnectRequest,
    DataSourceResponse,
    EvalRequest,
    EvalResponse,
    HealthResponse,
    QueryApprovalRequest,
    QueryRequest,
    QueryPageRequest,
    QueryHistoryResponse,
    QueryResponse,
    DataSourceResponse,
    DataSourceConfig,
    MetricsResponse,
    SchemaResponse,
    EvalScore,
    SettingsRequest,
)
from app.services.data_source_service import DataSourceService
from app.services.history_service import HistoryService
from app.services import db_service
from app.services.data_service import DataSourceService as CSVService
from app.services.database import engine


router = APIRouter(prefix="/api", tags=["api"])
logger = get_logger(__name__)


import json as _json
from datetime import datetime as _datetime

def _default_serializer(obj):
    if isinstance(obj, _datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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
    # Use custom serializer to handle datetime objects
    content_str = _json.dumps(payload, default=_default_serializer)
    return JSONResponse(content=_json.loads(content_str), headers=headers)


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
    result = {}
    try:
        data_source_service.get_conn_string(payload.source_id)
        thread_id = payload.thread_id or str(uuid4())
        result = graph.run(
            payload.question,
            payload.source_id,
            thread_id=thread_id,
            preview_only=payload.preview_only,
            sql=payload.sql
        )
        if result.get("requires_approval"):
            result["message"] = "Approval required for write query."
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(content=result, headers=headers)
    except Exception as e:
        status = "ERROR"
        logger.exception("Query failed")
        return _resp(success=False, message=f"Query failed: {str(e)}", data=None)
    finally:
        latency = time.time() - start_time
        try:
            viz_info = (result.get("documentation") or {}).get("visualization") or {}
            history_service.save_query(
                question=payload.question,
                source_id=payload.source_id,
                status=status,
                latency=latency,
                has_visualization=bool(viz_info.get("spec")),
                chart_type=viz_info.get("chart_type"),
            )
        except Exception:
            logger.exception("Failed to save query history in finally block")


@router.post("/query/approval", response_model=QueryResponse)
def approve_query_endpoint(
    payload: QueryApprovalRequest,
    graph=Depends(get_graph_orchestrator),
) -> QueryResponse:
    result = graph.resume(thread_id=payload.thread_id, approved=payload.approved)
    if not payload.approved:
        result["status"] = "cancelled"
        result["message"] = "Operation cancelled by user."
    else:
        result["status"] = "completed"
        result["message"] = "Operation approved and executed."
    return QueryResponse(**result)


@router.post("/query/page")
def query_page_endpoint(
    payload: QueryPageRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    try:
        data_source_service.get_conn_string(payload.source_id)
        # Execute query with offset/limit based on dialect
        dialect = db_service.DBService(source_id=payload.source_id).get_dialect()
        limit_sql = payload.sql
        offset = (payload.page - 1) * payload.page_size
        if dialect in ("sqlite", "postgresql", "mysql"):
            limit_sql = f"{payload.sql} LIMIT {payload.page_size} OFFSET {offset}"
        elif dialect == "mssql":
            limit_sql = f"{payload.sql} OFFSET {offset} ROWS FETCH NEXT {payload.page_size} ROWS ONLY"
        elif dialect == "oracle":
            limit_sql = f"{payload.sql} OFFSET {offset} ROWS FETCH NEXT {payload.page_size} ROWS ONLY"

        results = db_service.execute_query(limit_sql, payload.source_id)
        return _resp(success=True, message="Page fetched", data={"rows": results, "page": payload.page})
    except Exception as e:
        logger.exception("Query page failed")
        return _resp(success=False, message=f"Query page failed: {str(e)}", data=None)


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


@router.get("/datasources/{id}/suggestions")
def get_datasource_suggestions(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    data_source_service.get_conn_string(id)
    schema = db_service.get_source_schema(id)
    tables = schema.get("tables", [])
    
    suggestions = []
    table_names = [t["name"].lower() for t in tables]
    
    if "employees" in table_names:
        suggestions.extend(["Show all employees and their salaries", "ما هو إجمالي الرواتب لكل قسم؟", "من هم أعلى 5 موظفين راتباً؟"])
    if "sales" in table_names:
        suggestions.extend(["Show total sales revenue by category", "أظهر المبيعات الإجمالية حسب الفئة بالعربية", "What were total sales by month?"])
    if "inventory" in table_names:
        suggestions.extend(["Which products are below reorder level?", "عرض المنتجات التي نفد مخزونها"])
        
    if len(suggestions) < 3:
        for t in tables:
            suggestions.append(f"Show first 10 rows from {t['name']}")
            
    return _resp(success=True, message="Suggestions fetched", data=suggestions[:4])


@router.get("/system/stats")
def get_system_stats(
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    sources = data_source_service.list_sources()
    stats = history_service.get_stats()
    stats["total_sources"] = len(sources)
    return _resp(success=True, message="System stats fetched", data=stats)


@router.get("/system/feed")
def get_system_feed(
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    feed = history_service.get_feed()
    return _resp(success=True, message="Activity feed fetched", data=feed)


@router.get("/system/metrics", response_model=MetricsResponse)
def get_system_metrics(
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict[str, Any]:
    sources = data_source_service.list_sources()
    metrics = history_service.get_metrics()
    metrics["total_sources"] = len(sources)
    return _resp(success=True, message="System metrics fetched", data=metrics)


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
        import re
        s = sql.replace('\n', ' ').replace('\t', ' ')
        s = ' '.join(s.split())
        sel = (s.lower().split('select ')[1].split(' from')[0] if 'select ' in s.lower() and ' from' in s.lower() else '')
        from_part = ''
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


@router.post('/report/generate')
def generate_report(payload: dict) -> dict[str, Any]:
    """Generate a markdown report from a query document."""
    from app.services.report_service import build_report
    try:
        document = payload.get("document", payload)
        report = build_report(document)
        return _resp(success=True, message="Report generated", data=report)
    except Exception as e:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", response_model=EvalResponse)
def evaluate_query_endpoint(
    payload: EvalRequest,
) -> dict[str, Any]:
    """Evaluate a Text-to-SQL query for syntax, correctness, and schema relevance."""
    from app.services.evaluation_service import evaluate_sql
    try:
        scores = evaluate_sql(
            question=payload.question,
            sql=payload.sql,
            results=None,
            source_id=payload.source_id,
            thread_id=payload.thread_id,
        )
        return _resp(success=True, message="Evaluation complete", data=scores)
    except Exception as e:
        logger.exception("Evaluation failed")
        return _resp(success=False, message=f"Evaluation failed: {str(e)}", data=None)


@router.get("/settings")
def get_settings_endpoint() -> dict[str, Any]:
    from app.services.settings_service import get_public_settings
    return _resp(success=True, message="Settings retrieved", data=get_public_settings())


@router.post("/settings")
def update_settings_endpoint(payload: SettingsRequest) -> dict[str, Any]:
    from app.services.settings_service import update_settings
    updates = {}
    if payload.llm_provider is not None:
        updates["llm_provider"] = payload.llm_provider
    if payload.api_keys is not None:
        updates["api_keys"] = {k: v for k, v in payload.api_keys.items() if v}
    if payload.visualization is not None:
        updates["visualization"] = payload.visualization
    if payload.features is not None:
        updates["features"] = payload.features
    result = update_settings(updates)
    return _resp(success=True, message="Settings updated", data=result)
