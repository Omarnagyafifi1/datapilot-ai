import json
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

SETTINGS_FILE = Path(__file__).resolve().parents[2] / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_provider": "litellm",
    "api_keys": {
        "groq": "",
        "openrouter": "",
        "gemini": "",
        "openai": "",
    },
    "visualization": {
        "default_chart_type": "auto",
        "max_bars": 20,
        "theme": "dark",
    },
    "features": {
        "scenario_memory": True,
        "arabic_column_rewrite": True,
        "context_filtering": True,
        "auto_visualization": True,
        "human_approval_write": True,
    },
}


def _load() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        if "api_keys" in data:
            merged["api_keys"].update(data["api_keys"])
        if "visualization" in data:
            merged["visualization"].update(data["visualization"])
        if "features" in data:
            merged["features"].update(data["features"])
        return merged
    except Exception as exc:
        logger.warning("Failed to load settings: %s", exc)
        return dict(DEFAULT_SETTINGS)


def _save(data: dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_settings() -> dict[str, Any]:
    return _load()


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    current = _load()
    if "llm_provider" in updates:
        current["llm_provider"] = updates["llm_provider"]
    if "api_keys" in updates and isinstance(updates["api_keys"], dict):
        for k, v in updates["api_keys"].items():
            if k in current["api_keys"] and v:
                current["api_keys"][k] = v
    if "visualization" in updates and isinstance(updates["visualization"], dict):
        current["visualization"].update(updates["visualization"])
    if "features" in updates and isinstance(updates["features"], dict):
        current["features"].update(updates["features"])
    _save(current)
    return get_public_settings()


def get_public_settings() -> dict[str, Any]:
    settings = _load()
    public = {
        "llm_provider": settings["llm_provider"],
        "api_keys": {
            k: "••••••••" if v else "" for k, v in settings["api_keys"].items()
        },
        "visualization": settings["visualization"],
        "features": settings["features"],
    }
    return public
