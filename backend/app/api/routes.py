from fastapi import APIRouter, Depends

from app.api.deps import get_graph_orchestrator
from app.models.schemas import HealthResponse, QueryRequest, QueryResponse


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/query", response_model=QueryResponse)
def query_endpoint(
    payload: QueryRequest,
    graph=Depends(get_graph_orchestrator),
) -> QueryResponse:
    result = graph.run(payload.question)
    return QueryResponse(answer=result)
