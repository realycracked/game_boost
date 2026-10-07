"""Stockage JSON des réglages (profil, réponses au QCM, préférences)."""

import json
import threading
from typing import Any

from .paths import data_dir

_LOCK = threading.Lock()

_DEFAULTS: dict[str, Any] = {
    "first_run": True,
    "profile": None,          # résultat du QCM (dict) ou None
    "quiz_answers": {},       # {question_id: option_id | [option_id, ...]}
    "ai_provider": None,      # fournisseur IA par défaut ("groq", "openai", "anthropic", "gemini")
    "theme": "light",
}


def _settings_path():
    return data_dir() / "settings.json"


def get_settings() -> dict[str, Any]:
    with _LOCK:
        try:
            raw = json.loads(_settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        merged = dict(_DEFAULTS)
        merged.update(raw if isinstance(raw, dict) else {})
        return merged


def save_settings(settings: dict[str, Any]) -> None:
    with _LOCK:
        _settings_path().write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def update_settings(**kwargs: Any) -> dict[str, Any]:
    current = get_settings()
    current.update(kwargs)
    save_settings(current)
    return current
