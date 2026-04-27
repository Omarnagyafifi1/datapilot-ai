class CSVValidationError(Exception):
    """Exception raised for invalid CSV file uploads."""
    pass

class DataCleaningError(Exception):
    """Exception raised when data cleaning fails."""
    pass

class DatabaseIngestionError(Exception):
    """Exception raised when database ingestion fails."""
    pass
