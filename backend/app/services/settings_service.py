import json
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

SETTINGS_FILE = Path(__file__).resolve().parents[2] / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_provider": "azure",
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.2,
    "max_tokens": 2048,
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
        return {
            "llm_provider": DEFAULT_SETTINGS["llm_provider"],
            "model": DEFAULT_SETTINGS["model"],
            "temperature": DEFAULT_SETTINGS["temperature"],
            "max_tokens": DEFAULT_SETTINGS["max_tokens"],
            "api_keys": dict(DEFAULT_SETTINGS["api_keys"]),
            "visualization": dict(DEFAULT_SETTINGS["visualization"]),
            "features": dict(DEFAULT_SETTINGS["features"]),
        }
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        api_keys = data.get("api_keys", {})
        clean_keys = {k: v for k, v in api_keys.items() if v and v != "••••••••"}
        return {
            "llm_provider": data.get("llm_provider", DEFAULT_SETTINGS["llm_provider"]),
            "model": data.get("model", DEFAULT_SETTINGS["model"]),
            "temperature": data.get("temperature", DEFAULT_SETTINGS["temperature"]),
            "max_tokens": data.get("max_tokens", DEFAULT_SETTINGS["max_tokens"]),
            "api_keys": {**DEFAULT_SETTINGS["api_keys"], **clean_keys},
            "visualization": {**DEFAULT_SETTINGS["visualization"], **data.get("visualization", {})},
            "features": {**DEFAULT_SETTINGS["features"], **data.get("features", {})},
        }
    except Exception as exc:
        logger.warning("Failed to load settings: %s", exc)
        return {
            "llm_provider": DEFAULT_SETTINGS["llm_provider"],
            "model": DEFAULT_SETTINGS["model"],
            "temperature": DEFAULT_SETTINGS["temperature"],
            "max_tokens": DEFAULT_SETTINGS["max_tokens"],
            "api_keys": dict(DEFAULT_SETTINGS["api_keys"]),
            "visualization": dict(DEFAULT_SETTINGS["visualization"]),
            "features": dict(DEFAULT_SETTINGS["features"]),
        }


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
    if "model" in updates:
        current["model"] = updates["model"]
    if "temperature" in updates:
        current["temperature"] = updates["temperature"]
    if "max_tokens" in updates:
        current["max_tokens"] = updates["max_tokens"]
    if "api_keys" in updates and isinstance(updates["api_keys"], dict):
        for k, v in updates["api_keys"].items():
            if k in current["api_keys"] and v and v != "••••••••":
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
        "model": settings["model"],
        "temperature": settings["temperature"],
        "max_tokens": settings["max_tokens"],
        "api_keys": {
            k: "••••••••" if v else "" for k, v in settings["api_keys"].items()
        },
        "visualization": settings["visualization"],
        "features": settings["features"],
    }
    return public
