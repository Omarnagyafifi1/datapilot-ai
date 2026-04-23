from typing import Optional


class DBService:
    def __init__(self, read_only_user: str, read_only_password: str, dialect: str = "postgresql") -> None:
        self.read_only_user = read_only_user
        self.read_only_password = read_only_password
        self.dialect = dialect

    def get_dialect(self) -> str:
        return self.dialect

    def run_query(self, sql: str, timeout: Optional[int] = None) -> list[dict]:
        """Placeholder DB call. Replace with actual DB implementation."""
        return [{"sql": sql, "result": "stub"}]