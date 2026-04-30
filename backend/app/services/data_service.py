import io
import re
import time
import math
import pandas as pd
from typing import Dict, Any
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import inspect
from app.core.exceptions import CSVValidationError, DataCleaningError, DatabaseIngestionError

class DataSourceService:
    @staticmethod
    async def validate_csv(file: UploadFile) -> None:
        """
        Validates the uploaded file is a CSV by checking extension and content type.
        """
        if not file.filename.endswith(".csv"):
            raise CSVValidationError("File extension must be .csv")
        
        # Valid content types for CSV
        valid_types = ["text/csv", "application/vnd.ms-excel", "application/octet-stream"]
        if file.content_type not in valid_types:
            raise CSVValidationError(f"Invalid content type: {file.content_type}. Expected text/csv")

    @staticmethod
    def clean_csv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the DataFrame:
        - Lowercases column names
        - Replaces spaces and special characters with underscores
        """
        try:
            # Clean column names
            df.columns = (
                df.columns.str.lower()
                .str.replace(r'[^a-z0-9_]', '_', regex=True)
                .str.replace(r'_+', '_', regex=True)
                .str.strip('_')
            )
            return df
        except Exception as e:
            raise DataCleaningError(f"Failed to clean CSV data: {str(e)}")

    @staticmethod
    def _sanitize_table_name(filename: str) -> str:
        """
        Converts the original filename into a valid SQL table name.
        """
        name = Path(filename).stem.lower()
        name = re.sub(r'[^a-z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "uploaded_data"

    @staticmethod
    def _check_table_exists(conn, table_name: str) -> bool:
        """Synchronous helper for checking if a table exists."""
        insp = inspect(conn)
        return insp.has_table(table_name)

    @staticmethod
    def _load_data_to_sql(conn, df: pd.DataFrame, table_name: str) -> None:
        """Synchronous helper for loading DataFrame into SQL."""
        df.to_sql(name=table_name, con=conn, if_exists="fail", index=False)

    @classmethod
    async def ingest_to_db(cls, engine, df: pd.DataFrame, original_filename: str) -> str:
        """
        Dynamically creates a table and loads the dataframe into PostgreSQL.
        Handles table name collisions by appending a timestamp.
        """
        base_table_name = cls._sanitize_table_name(original_filename)
        table_name = base_table_name
        
        try:
            # We use engine.begin() and run_sync to allow pandas synchronous
            # to_sql to execute correctly on our async engine.
            async with engine.begin() as conn:
                exists = await conn.run_sync(cls._check_table_exists, table_name)
                
                # If table exists, append timestamp to make it unique
                if exists:
                    timestamp = int(time.time())
                    table_name = f"{base_table_name}_{timestamp}"
                
                # Ingest data
                await conn.run_sync(cls._load_data_to_sql, df, table_name)
                
            return table_name
        except Exception as e:
            raise DatabaseIngestionError(f"Database insertion failed: {str(e)}")

    @staticmethod
    def generate_metadata(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """
        Generates AI-ready metadata mapping pandas types to rough SQL equivalents
        and providing a small sample of the data.
        """
        type_mapping = {
            'int64': 'INTEGER',
            'float64': 'FLOAT',
            'object': 'VARCHAR',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP'
        }
        
        columns_info = {
            col: type_mapping.get(str(df[col].dtype), "VARCHAR")
            for col in df.columns
        }
        
        # Take first 3 rows, replace NaN with None for valid JSON serialization
        sample_df = df.head(3).replace({pd.NA: None})
        sample_data = sample_df.to_dict(orient="records")
        
        # Pandas to_dict leaves float nan as float('nan'), we need standard None
        for row in sample_data:
            for k, v in row.items():
                if isinstance(v, float) and math.isnan(v):
                    row[k] = None

        return {
            "table_name": table_name,
            "columns": columns_info,
            "sample_data": sample_data
        }

    @classmethod
    async def process_csv(cls, file: UploadFile, engine) -> Dict[str, Any]:
        """
        Orchestrates the entire upload pipeline:
        Validate -> Clean -> Ingest -> Metadata
        """
        await cls.validate_csv(file)
        
        # Read file into memory
        content = await file.read()
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise CSVValidationError(f"Could not parse CSV: {str(e)}")
            
        cleaned_df = cls.clean_csv(df)
        table_name = await cls.ingest_to_db(engine, cleaned_df, file.filename)
        metadata = cls.generate_metadata(cleaned_df, table_name)
        
        return metadata
