import time
from typing import Any, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
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
# LLM settings service - fallback to empty settings if not available
try:
    from app.services.llm_settings_service import get_llm_settings, save_llm_settings
except ImportError:
    def get_llm_settings():
        return {}
    def save_llm_settings(**kwargs):
        return {}
from app.services.data_source_service import DataSourceService, save_dataset_metadata, get_dataset_by_hash, list_datasets as _list_datasets_func, get_dataset as _get_dataset_func, delete_dataset as _delete_dataset_func, update_dataset_name as _update_dataset_name_func, DataSourceService as _DataSourceService
from app.services.history_service import HistoryService
from app.services import db_service
from app.services.data_service import DataSourceService as CSVService
from app.services.database import engine
from app.services.import_providers import ImportPreview, ImportOptions
from app.services.import_providers.csv_provider import CSVProvider
from app.services.import_providers.sqlite_provider import SQLiteProvider


router = APIRouter(prefix="/api", tags=["api"])
logger = get_logger(__name__)

# Provider registry
_PROVIDERS = {
    "csv": CSVProvider(),
    "sqlite": SQLiteProvider(),
}


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


def _get_provider(file: UploadFile) -> Optional[object]:
    """Determine the appropriate provider based on file extension."""
    if not file.filename:
        return None
    
    ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    
    # Map extensions to providers
    if ext == 'csv':
        return _PROVIDERS.get('csv')
    elif ext in ['db', 'sqlite', 'sqlite3']:
        return _PROVIDERS.get('sqlite')
    
    return None


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/query")
def query_endpoint(
    payload: QueryRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
    history_service: HistoryService = Depends(get_history_service),
) -> dict:
    start_time = time.time()
    status = "SUCCESS"
    result = {}
    try:
        data_source_service.get_conn_string(payload.source_id)
        thread_id = payload.thread_id or str(uuid4())
        
        # Build LLM config override from payload or use saved settings
        llm_config = {
            "provider": payload.provider,
            "model": payload.model,
            "temperature": payload.temperature,
            "max_tokens": payload.max_tokens,
        }
        
        # Only pass non-None values to get_graph_orchestrator
        graph_kwargs = {k: v for k, v in llm_config.items() if v is not None}
        
        result = get_graph_orchestrator(**graph_kwargs).run(
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
        return JSONResponse(content=jsonable_encoder(result), headers=headers)
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

    # Fetch and cache the schema immediately upon connection
    try:
        source_id = result["id"]
        data_source_service.get_conn_string(source_id)
        db_service.get_source_schema(source_id)
        logger.info(f"Successfully pre-fetched schema for source_id={source_id}")
    except Exception as e:
        logger.warning(f"Failed to pre-fetch schema for new source: {e}", exc_info=True)

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


_SUGGESTIONS_CACHE: dict[str, list[dict[str, str]]] = {}

@router.get("/datasources/{id}/suggestions")
def get_datasource_suggestions(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
    graph=Depends(get_graph_orchestrator),
) -> dict[str, Any]:
    if id in _SUGGESTIONS_CACHE:
        return _resp(success=True, message="Suggestions fetched", data=_SUGGESTIONS_CACHE[id])

    data_source_service.get_conn_string(id)
    schema = db_service.get_source_schema(id)
    tables = schema.get("tables", [])

    # Build a compact schema summary for the LLM
    schema_lines = []
    for t in tables:
        cols = ", ".join(c["name"] for c in t.get("columns", []))
        schema_lines.append(f"- {t['name']}({cols})")
    schema_summary = "\n".join(schema_lines) if schema_lines else "No tables found."

    try:
        from app.agents.prompts import INITIAL_SUGGESTION_PROMPT
        from app.agents.graph import _parse_suggestions

        prompt = (
            f"{INITIAL_SUGGESTION_PROMPT}\n\n"
            f"### Database Schema\n{schema_summary}"
        )
        raw_response = graph.llm.generate(prompt)
        parsed = _parse_suggestions(raw_response)
        if parsed:
            _SUGGESTIONS_CACHE[id] = parsed[:4]
            return _resp(success=True, message="Suggestions fetched", data=parsed[:4])
    except Exception:
        logger.warning("LLM suggestion generation failed, using fallback", exc_info=True)

    # Fallback: generate generic suggestions from table names
    fallback = []
    for t in tables[:4]:
        fallback.append({"ar": f"أظهر أول 10 صفوف من {t['name']}", "en": f"Show first 10 rows from {t['name']}"})
    _SUGGESTIONS_CACHE[id] = fallback[:4]
    return _resp(success=True, message="Suggestions fetched", data=fallback[:4])


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


# ============================================================================
# NEW: Upload Preview and Import Endpoints
# ============================================================================

@router.post("/upload/preview")
async def upload_preview(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Upload a file and return a preview without importing.
    Supports CSV and SQLite files.
    """
    provider = _get_provider(file)
    if not provider:
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: CSV, SQLite (.db, .sqlite, .sqlite3)")
    
    try:
        # Validate the file
        is_valid, error = await provider.validate(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error or "Invalid file")
        
        # Get preview data
        preview = await provider.preview(file)
        
        # Check for duplicates using module-level function
        existing = get_dataset_by_hash(preview.file_hash)
        
        return _resp(
            success=True,
            message="File preview generated",
            data={
                "filename": preview.filename,
                "file_size": preview.file_size,
                "detected_format": preview.detected_format,
                "file_hash": preview.file_hash,
                "tables": [
                    {
                        "name": t.name,
                        "original_name": t.original_name,
                        "row_count": t.row_count,
                        "columns": [
                            {
                                "name": c.name,
                                "original_name": c.original_name,
                                "data_type": c.data_type,
                                "nullable": c.nullable,
                                "primary_key": c.primary_key,
                                "unique": c.unique,
                                "is_numeric": c.is_numeric,
                                "is_date": c.is_date,
                            }
                            for c in t.columns
                        ],
                    }
                    for t in preview.tables
                ],
                "quality_report": {
                    "total_rows": preview.quality_report.total_rows,
                    "total_columns": preview.quality_report.total_columns,
                    "missing_values": preview.quality_report.missing_values,
                    "duplicate_rows": preview.quality_report.duplicate_rows,
                    "has_nulls": preview.quality_report.has_nulls,
                    "has_duplicates": preview.quality_report.has_duplicates,
                },
                "relationships": [
                    {
                        "column": r.column,
                        "referenced_table": r.referenced_table,
                        "referenced_column": r.referenced_column,
                    }
                    for r in preview.relationships
                ],
                "is_duplicate": existing is not None,
                "existing_dataset": existing,
            }
        )
    except Exception as e:
        logger.exception("Upload preview failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/import")
async def upload_import(
    file: UploadFile = File(...),
    dataset_name: str = "",
    selected_tables: str = "[]",
    renamed_columns: str = "{}",
    modified_types: str = "{}",
) -> dict[str, Any]:
    """
    Import an uploaded file into the system.
    """
    import json as _json
    
    provider = _get_provider(file)
    if not provider:
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: CSV, SQLite (.db, .sqlite, .sqlite3)")
    
    try:
        # Parse options
        options = ImportOptions(
            selected_tables=_json.loads(selected_tables) if selected_tables else None,
            renamed_columns=_json.loads(renamed_columns) if renamed_columns else None,
            modified_types=_json.loads(modified_types) if modified_types else None,
            dataset_name=dataset_name or file.filename,
        )
        
        # Import the data
        result = await provider.import_data(file, options)
        
        # Get the preview for metadata storage
        preview = await provider.preview(file)
        
        # Save dataset metadata
        if preview:
            save_dataset_metadata(
                source_id=result.source_id,
                name=options.dataset_name or file.filename,
                source_type=preview.detected_format,
                original_filename=preview.filename,
                file_size=preview.file_size,
                file_hash=preview.file_hash,
                tables=[
                    {
                        "name": t.name,
                        "original_name": t.original_name,
                        "row_count": t.row_count,
                        "columns": [{"name": c.name, "data_type": c.data_type} for c in t.columns],
                    }
                    for t in preview.tables
                ],
                relationships=[
                    {"column": r.column, "referenced_table": r.referenced_table, "referenced_column": r.referenced_column}
                    for r in preview.relationships
                ],
                quality_report={
                    "total_rows": preview.quality_report.total_rows,
                    "total_columns": preview.quality_report.total_columns,
                    "missing_values": preview.quality_report.missing_values,
                    "duplicate_rows": preview.quality_report.duplicate_rows,
                },
            )
        
        return _resp(
            success=True,
            message=result.message,
            data={
                "source_id": result.source_id,
                "dataset_id": result.dataset_id,
                "table_names": result.table_names,
                "total_rows": result.total_rows,
            }
        )
    except Exception as e:
        logger.exception("Upload import failed")
        raise HTTPException(status_code=500, detail=str(e))


# Dataset Management Endpoints
@router.get("/datasets")
def list_datasets(
    search: str = None,
    source_type: str = None,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    """List all imported datasets."""
    datasets = data_source_service.list_datasets(search_query=search, source_type=source_type)
    return _resp(success=True, message="Datasets fetched", data=datasets)


@router.get("/datasets/{id}")
def get_dataset(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    """Get a single dataset by ID."""
    dataset = data_source_service.get_dataset(id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Parse JSON fields
    import json as _json
    if dataset.get("tables_json"):
        dataset["tables"] = _json.loads(dataset["tables_json"])
    if dataset.get("relationships_json"):
        dataset["relationships"] = _json.loads(dataset["relationships_json"])
    if dataset.get("quality_report_json"):
        dataset["quality_report"] = _json.loads(dataset["quality_report_json"])
    
    return _resp(success=True, message="Dataset fetched", data=dataset)


@router.delete("/datasets/{id}")
def delete_dataset(
    id: str,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    """Delete a dataset and its associated datasource."""
    data_source_service.delete_dataset(id)
    return _resp(success=True, message="Dataset deleted", data=None)


@router.patch("/datasets/{id}")
def update_dataset(
    id: str,
    name: str = None,
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> dict[str, Any]:
    """Update dataset metadata."""
    if name:
        data_source_service.update_dataset_name(id, name)
    return _resp(success=True, message="Dataset updated", data=None)


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
    from app.api.deps import reset_graph_orchestrator
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
    # Reset the graph orchestrator so the next request uses the new LLM provider/keys
    reset_graph_orchestrator()
    return _resp(success=True, message="Settings updated", data=result)


# ============================================================================
# LLM Settings Endpoints
# ============================================================================

@router.get("/settings/llm")
def get_llm_settings_endpoint() -> dict[str, Any]:
    """Get current LLM settings from database."""
    settings = get_llm_settings()
    # Sanitize API keys for response (don't expose full keys)
    sanitized = settings.copy()
    sanitized["api_keys"] = {
        k: ("***" + v[-4:] if v and len(v) > 4 else "***") if v else ""
        for k, v in settings.get("api_keys", {}).items()
    }
    return _resp(success=True, message="LLM settings retrieved", data=sanitized)


@router.put("/settings/llm")
def update_llm_settings_endpoint(
    body: dict = Body(...)
) -> dict[str, Any]:
    """Update LLM settings (provider, model, temperature, max_tokens, api_keys)."""
    provider = body.get("provider")
    model = body.get("model")
    temperature = body.get("temperature")
    max_tokens = body.get("max_tokens")
    api_keys = body.get("api_keys")
    
    try:
        updated = save_llm_settings(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_keys=api_keys,
        )
        # Sanitize response
        sanitized = updated.copy()
        sanitized["api_keys"] = {
            k: ("***" + v[-4:] if v and len(v) > 4 else "***") if v else ""
            for k, v in updated.get("api_keys", {}).items()
        }
        return _resp(success=True, message="LLM settings updated", data=sanitized)
    except Exception as e:
        logger.exception("Failed to save LLM settings")
        return _resp(success=False, message=f"Failed to update settings: {str(e)}", data=None)
