import asyncio
from typing import Any
from abc import ABC, abstractmethod

from app.models.schemas import DataSourceConfig, DataSourceType

class BaseSchemaService(ABC):
    @abstractmethod
    def get_schema(self, config: DataSourceConfig) -> dict[str, Any]:
        """Fetch and format the schema for a data source."""

class SchemaService(BaseSchemaService):
    def get_schema(self, config: DataSourceConfig) -> dict[str, Any]:
        """Fetch and format the schema for a data source."""
        if config.data_source_type == DataSourceType.POSTGRES:
            return self._fetch_generic_schema(config, "postgresql+asyncpg")
        elif config.data_source_type == DataSourceType.MYSQL:
            return self._fetch_generic_schema(config, "mysql+aiomysql")
        elif config.data_source_type == DataSourceType.ORACLE:
            return self._fetch_generic_schema(config, "oracle+oracledb")
        elif config.data_source_type == DataSourceType.SQLSERVER:
            return self._fetch_generic_schema(config, "mssql+pyodbc")
        elif config.data_source_type == DataSourceType.REDSHIFT:
            return self._fetch_generic_schema(config, "postgresql+asyncpg")
        elif config.data_source_type == DataSourceType.SPARK:
            # Spark typically requires specific JDBC drivers or API calls
            return {"tables": [], "error": "Spark schema fetching not implemented"}
        else:
            raise ValueError(f"Unsupported data source type: {config.data_source_type}")

    def _fetch_generic_schema(self, config: DataSourceConfig, dialect_prefix: str) -> dict[str, Any]:
        """Generic schema fetcher using SQLAlchemy Inspector."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import inspect

        # Build Connection URL
        if "oracle" in dialect_prefix:
            engine_url = f"{dialect_prefix}://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/?service_name={config.service_name or config.db_name}"
        else:
            engine_url = f"{dialect_prefix}://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"

        engine = create_async_engine(engine_url, echo=False, future=True)

        async def fetch() -> dict[str, Any]:
            try:
                async with engine.connect() as conn:
                    # SQLAlchemy's inspect is synchronous; use run_sync
                    def sync_inspect(sync_conn):
                        inspector = inspect(sync_conn)
                        tables = []
                        table_names = inspector.get_table_names()

                        for table_name in table_names:
                            columns = inspector.get_columns(table_name)
                            table_info = {
                                "name": table_name,
                                "columns": [
                                    {
                                        "name": col["name"],
                                        "type": str(col["type"]),
                                        "nullable": col.get("nullable", True),
                                        "primary_key": col.get("primary_key", False),
                                    }
                                    for col in columns
                                ],
                            }
                            
                            fks = inspector.get_foreign_keys(table_name)
                            table_info["foreign_keys"] = [
                                {
                                    "constrained_columns": fk["constrained_columns"],
                                    "referred_table": fk["referred_table"],
                                    "referred_columns": fk["referred_columns"],
                                }
                                for fk in fks
                            ]
                            tables.append(table_info)
                        return {"tables": tables}

                    return await conn.run_sync(sync_inspect)
            except Exception as e:
                return {"tables": [], "error": str(e)}
            finally:
                await engine.dispose()

        try:
            return asyncio.run(fetch())
        except Exception as e:
            return {"tables": [], "error": f"Async loop error: {str(e)}"}
