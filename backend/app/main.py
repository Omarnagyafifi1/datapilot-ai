from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import logging

from app.api.deps import close_graph_orchestrator
from app.api.routes import router as api_router
from app.core.exceptions import CSVValidationError, DataCleaningError, DatabaseIngestionError
from app.models.schemas import UploadResponse, UploadMetadata
from app.services.database import engine
from app.services.data_service import DataSourceService

from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import Response

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Text-to-SQL Data Analyst System API",
    description="API for managing data uploads and text-to-SQL conversions",
    version="1.0.0"
)
app.include_router(api_router)


@app.on_event("shutdown")
def _shutdown() -> None:
    close_graph_orchestrator()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fallback middleware to ensure CORS headers are present on all responses
@app.middleware("http")
async def _ensure_cors_headers(request, call_next):
    # Short-circuit preflight OPTIONS requests to ensure CORS headers are present
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        return Response(status_code=200, headers=headers)

    response = await call_next(request)
    # these are safe to set in development; in production refine as needed
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "*")
    return response
# Include Routes
app.include_router(api_router)


# Catch-all OPTIONS handler to ensure preflight requests return CORS headers
@app.options("/{full_path:path}")
async def catch_all_options(full_path: str):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=200, headers=headers)

# Mount frontend static files when available (built via `npm run build` into frontend/dist)
dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")

# Exception Handlers
@app.exception_handler(CSVValidationError)
async def csv_validation_exception_handler(request, exc: CSVValidationError):
    logger.warning(f"CSV Validation Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )

@app.exception_handler(DataCleaningError)
async def data_cleaning_exception_handler(request, exc: DataCleaningError):
    logger.error(f"Data Cleaning Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )

@app.exception_handler(DatabaseIngestionError)
async def database_ingestion_exception_handler(request, exc: DatabaseIngestionError):
    logger.error(f"Database Ingestion Error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )

# Routes
@app.post("/api/v1/data/upload-csv", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Uploads a CSV file, cleans it, and ingests it into the PostgreSQL database.
    Returns AI-ready metadata about the newly created table.
    """
    try:
        metadata = await DataSourceService.process_csv(file, engine)
        return UploadResponse(
            message="CSV successfully processed and ingested.",
            metadata=UploadMetadata(**metadata)
        )
    except (CSVValidationError, DataCleaningError, DatabaseIngestionError):
        # Allow custom exceptions to be handled by the specific handlers above
        raise
    except Exception as e:
        logger.exception("Unexpected error during CSV upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
