import json
from typing import Any

from redis import Redis


class ApprovalStore:
    def __init__(self, client: Redis, ttl_seconds: int, prefix: str = "approval:") -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._prefix = prefix

    def _key(self, run_id: str) -> str:
        return f"{self._prefix}{run_id}"

    def save(self, run_id: str, payload: dict[str, Any]) -> None:
        self._client.setex(self._key(run_id), self._ttl_seconds, json.dumps(payload))

    def get(self, run_id: str) -> dict[str, Any] | None:
        raw = self._client.get(self._key(run_id))
        if raw is None:
            return None
        return json.loads(raw)

    def delete(self, run_id: str) -> None:
        self._client.delete(self._key(run_id))
