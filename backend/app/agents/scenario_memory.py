import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    faiss = None


@dataclass
class ScenarioEntry:
    created_at: str
    status: str
    question: str
    sql: str
    error: str | None = None
    validation_reason: str | None = None
    lesson: str | None = None


class ScenarioMemory:
    def __init__(self, scenarios_path: Path, similarity_threshold: float = 0.45) -> None:
        self.scenarios_path = scenarios_path
        self.similarity_threshold = similarity_threshold
        if not self.scenarios_path.exists():
            self.scenarios_path.write_text("# Query Scenarios\n\n", encoding="utf-8")

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    def _embed(self, text: str, dim: int = 512) -> np.ndarray:
        vec = np.zeros(dim, dtype=np.float32)
        for token in self._tokenize(text):
            vec[hash(token) % dim] += 1.0
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def _entry_to_text(self, entry: ScenarioEntry) -> str:
        parts = [entry.question, entry.sql]
        if entry.error:
            parts.append(entry.error)
        if entry.validation_reason:
            parts.append(entry.validation_reason)
        if entry.lesson:
            parts.append(entry.lesson)
        return " ".join(parts)

    def _load_entries(self) -> list[ScenarioEntry]:
        content = self.scenarios_path.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        entries: list[ScenarioEntry] = []
        for block in blocks:
            try:
                payload = json.loads(block)
                entries.append(
                    ScenarioEntry(
                        created_at=str(payload.get("created_at", "")),
                        status=str(payload.get("status", "failed")),
                        question=str(payload.get("question", "")),
                        sql=str(payload.get("sql", "")),
                        error=str(payload.get("error")) if payload.get("error") is not None else None,
                        validation_reason=str(payload.get("validation_reason"))
                        if payload.get("validation_reason") is not None
                        else None,
                        lesson=str(payload.get("lesson")) if payload.get("lesson") is not None else None,
                    )
                )
            except Exception:
                continue
        return entries

    def append_entry(
        self,
        *,
        status: str,
        question: str,
        sql: str,
        error: str | None = None,
        validation_reason: str | None = None,
        lesson: str | None = None,
    ) -> None:
        entry = ScenarioEntry(
            created_at=datetime.now(timezone.utc).isoformat(),
            status=status,
            question=question,
            sql=sql,
            error=error,
            validation_reason=validation_reason,
            lesson=lesson,
        )
        payload = {
            "created_at": entry.created_at,
            "status": entry.status,
            "question": entry.question,
            "sql": entry.sql,
            "error": entry.error,
            "validation_reason": entry.validation_reason,
            "lesson": entry.lesson,
        }
        with self.scenarios_path.open("a", encoding="utf-8") as f:
            f.write(f"## {entry.created_at} - {status}\n\n")
            if lesson:
                f.write(f"{lesson}\n\n")
            f.write("```json\n")
            f.write(json.dumps(payload, ensure_ascii=False, default=str, indent=2))
            f.write("\n```\n\n")

    def get_recent_context(self, n: int = 10) -> str:
        entries = self._load_entries()
        if not entries:
            return ""

        recent = entries[-n:]
        lines: list[str] = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"Example {i}:")
            lines.append(f"  Question: {entry.question}")
            lines.append(f"  SQL: {entry.sql}")
            if entry.error:
                lines.append(f"  Error: {entry.error}")
            if entry.validation_reason:
                lines.append(f"  Validation: {entry.validation_reason}")
            if entry.lesson:
                lesson_text = entry.lesson.replace("\n", "\n  ")
                lines.append(f"  Lesson: {lesson_text}")
            lines.append(f"  Status: {entry.status}")
            lines.append("")
        return "\n".join(lines)

    def find_similar_solution(self, question: str) -> dict[str, Any] | None:
        entries = [e for e in self._load_entries() if e.status == "resolved" and e.sql.strip()]
        if not entries:
            return None

        vectors = np.vstack([self._embed(self._entry_to_text(e)) for e in entries])
        query_vec = self._embed(question).reshape(1, -1)

        if faiss is not None:
            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)
            scores, idxs = index.search(query_vec, 1)
            best_score = float(scores[0][0])
            best_idx = int(idxs[0][0])
        else:
            scores = vectors @ query_vec.reshape(-1)
            best_idx = int(np.argmax(scores))
            best_score = float(scores[best_idx])

        if best_idx < 0 or best_score < self.similarity_threshold:
            return None

        best_entry = entries[best_idx]
        return {
            "sql": best_entry.sql,
            "score": best_score,
            "question": best_entry.question,
        }
