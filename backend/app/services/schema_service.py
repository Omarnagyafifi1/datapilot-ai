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
            return self._fetch_generic_schema(config, "postgresql+psycopg2")
        elif config.data_source_type == DataSourceType.MYSQL:
            return self._fetch_generic_schema(config, "mysql+pymysql")
        elif config.data_source_type == DataSourceType.ORACLE:
            return self._fetch_generic_schema(config, "oracle+oracledb")
        elif config.data_source_type == DataSourceType.SQLSERVER:
            return self._fetch_generic_schema(config, "mssql+pymssql")
        elif config.data_source_type == DataSourceType.REDSHIFT:
            return self._fetch_generic_schema(config, "postgresql+psycopg2")
        elif config.data_source_type == DataSourceType.SPARK:
            return {"tables": [], "error": "Spark schema fetching not implemented"}
        else:
            raise ValueError(f"Unsupported data source type: {config.data_source_type}")

    def _fetch_generic_schema(self, config: DataSourceConfig, dialect_prefix: str) -> dict[str, Any]:
        """Generic schema fetcher using SQLAlchemy Inspector (sync)."""
        from sqlalchemy import create_engine, inspect

        if "oracle" in dialect_prefix:
            engine_url = f"{dialect_prefix}://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/?service_name={config.service_name or config.db_name}"
        else:
            engine_url = f"{dialect_prefix}://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"

        try:
            engine = create_engine(engine_url, echo=False, future=True)
            with engine.connect() as conn:
                inspector = inspect(conn)
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
        except Exception as e:
            return {"tables": [], "error": str(e)}
        finally:
            engine.dispose()
