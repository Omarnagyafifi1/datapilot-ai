from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_approval_store, get_data_source_service, get_graph_orchestrator
from app.core.logger import get_logger
from app.models.schemas import (
    ApprovalPayload,
    ApprovalRequest,
    ConnectRequest,
    DataSourceResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.approval_store import ApprovalStore
from app.services.data_source_service import DataSourceService


router = APIRouter(prefix="/api", tags=["api"])
logger = get_logger(__name__)


def _resp(success: bool, message: str, data: dict | list | None) -> dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "data": data,
    }


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/query", response_model=QueryResponse)
def query_endpoint(
    payload: QueryRequest,
    data_source_service: DataSourceService = Depends(get_data_source_service),
    approval_store: ApprovalStore = Depends(get_approval_store),
    graph=Depends(get_graph_orchestrator),
) -> QueryResponse:
    data_source_service.get_conn_string(payload.source_id)
    run_id = str(uuid4())
    result = graph.start(payload.question, payload.source_id, thread_id=run_id)
    final_state = result["state"]
    interrupts = final_state.get("__interrupt__")

    if interrupts:
        interrupt = interrupts[0]
        payload_value = interrupt.value if isinstance(interrupt.value, dict) else {"message": str(interrupt.value)}
        approval_store.save(
            run_id,
            {
                "thread_id": run_id,
                "approval": payload_value,
            },
        )
        approval = ApprovalPayload(
            run_id=run_id,
            question=payload_value.get("question"),
            sql=payload_value.get("sql"),
            message=payload_value.get("message"),
        )
        return QueryResponse(
            status="pending_approval",
            approval=approval,
            message="Approval required",
        )

    return QueryResponse(
        status="completed",
        sql=final_state.get("sql", ""),
        results=final_state.get("query_results", []),
        documentation=final_state.get("documentation", {}),
    )


@router.post("/approval", response_model=QueryResponse)
def approval_endpoint(
    payload: ApprovalRequest,
    approval_store: ApprovalStore = Depends(get_approval_store),
    graph=Depends(get_graph_orchestrator),
) -> QueryResponse:
    pending = approval_store.get(payload.run_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if not payload.approved:
        approval_store.delete(payload.run_id)
        return QueryResponse(
            status="denied",
            message=payload.reason or "Operation cancelled by user.",
        )

    final_state = graph.resume(payload.run_id, "approved")
    approval_store.delete(payload.run_id)
    return QueryResponse(
        status="completed",
        sql=final_state.get("sql", ""),
        results=final_state.get("query_results", []),
        documentation=final_state.get("documentation", {}),
    )


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
