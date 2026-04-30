from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
import logging

from app.core.exceptions import CSVValidationError, DataCleaningError, DatabaseIngestionError
from app.models.schemas import UploadResponse, UploadMetadata
from app.services.database import engine
from app.services.data_service import DataSourceService

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Text-to-SQL Data Analyst System API",
    description="API for managing data uploads and text-to-SQL conversions",
    version="1.0.0"
)

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
