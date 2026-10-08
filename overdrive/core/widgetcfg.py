"""Réglages persistants du widget overlay : défauts, validation et fusion.

Les défauts sont gérés ici (store.py accepte toute clé et n'est pas modifié).
Toute lecture passe par :func:`get_widget_settings` (fusion avec les défauts,
valeurs invalides remplacées), toute écriture par
:func:`update_widget_settings` (fusion partielle, revalidation, persistance
via ``store.update_settings(widget=...)``).
"""

from __future__ import annotations

import copy
from typing import Any

from overdrive import store

SCALES: tuple[str, ...] = ("s", "m", "l")
AUTOSTART_MODES: tuple[str, ...] = ("never", "always", "game")
THEMES: tuple[str, ...] = ("dark", "light", "minimal")
LAYOUTS: tuple[str, ...] = ("row", "column")

OPACITY_MIN: float = 0.1
OPACITY_MAX: float = 1.0

DEFAULTS: dict[str, Any] = {
    "elements": {
        "fps": True,
        "game": True,
        "cpu": True,
        "ram": True,
        "net": False,
        "clock": False,
    },
    "theme": "dark",       # "dark" | "light" | "minimal" (texte seul, sans fond)
    "layout": "row",       # "row" | "column"
    "opacity": 0.92,
    "scale": "m",          # "s" | "m" | "l"
    "autostart": "never",  # "never" | "always" | "game"
    "position": None,      # None ou {"x": int, "y": int}
    "click_through": False,
}


def _as_bool(value: Any, fallback: bool) -> bool:
    """Booléen depuis une valeur libre (bool ou 0/1), sinon ``fallback``."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return fallback


def _valid_opacity(value: Any) -> float:
    """Opacité bornée [0.1 ; 1.0], défaut si non numérique."""
    try:
        opacity = float(value)
    except (TypeError, ValueError):
        return float(DEFAULTS["opacity"])
    if opacity != opacity:  # NaN
        return float(DEFAULTS["opacity"])
    return max(OPACITY_MIN, min(OPACITY_MAX, opacity))


def _valid_position(value: Any) -> dict[str, int] | None:
    """Position ``{"x": int, "y": int}`` ou None si invalide/absente."""
    if not isinstance(value, dict):
        return None
    try:
        return {"x": int(value["x"]), "y": int(value["y"])}
    except (KeyError, TypeError, ValueError):
        return None


def _validate(raw: Any) -> dict[str, Any]:
    """Réglages complets et valides construits depuis ``raw`` (fusion défauts)."""
    cfg: dict[str, Any] = copy.deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return cfg

    elements = raw.get("elements")
    if isinstance(elements, dict):
        for name, default in DEFAULTS["elements"].items():
            if name in elements:
                cfg["elements"][name] = _as_bool(elements[name], default)

    if "opacity" in raw:
        cfg["opacity"] = _valid_opacity(raw.get("opacity"))

    scale = raw.get("scale")
    if isinstance(scale, str) and scale.lower() in SCALES:
        cfg["scale"] = scale.lower()

    theme = raw.get("theme")
    if isinstance(theme, str) and theme.lower() in THEMES:
        cfg["theme"] = theme.lower()

    layout = raw.get("layout")
    if isinstance(layout, str) and layout.lower() in LAYOUTS:
        cfg["layout"] = layout.lower()

    autostart = raw.get("autostart")
    if isinstance(autostart, str) and autostart.lower() in AUTOSTART_MODES:
        cfg["autostart"] = autostart.lower()

    if "position" in raw:
        cfg["position"] = _valid_position(raw.get("position"))

    if "click_through" in raw:
        cfg["click_through"] = _as_bool(raw.get("click_through"), bool(DEFAULTS["click_through"]))

    return cfg


def get_widget_settings() -> dict[str, Any]:
    """Réglages du widget fusionnés avec les défauts et validés (jamais d'exception)."""
    try:
        stored = store.get_settings().get("widget")
    except Exception:
        stored = None
    return _validate(stored)


def update_widget_settings(partial: dict[str, Any]) -> dict[str, Any]:
    """Fusionne ``partial`` dans les réglages, revalide, persiste et renvoie le tout.

    ``elements`` est fusionné clé par clé (les clés inconnues sont ignorées) ;
    les autres clés remplacent la valeur courante puis sont validées.
    """
    current = get_widget_settings()
    _ENUMS = {"scale": SCALES, "autostart": AUTOSTART_MODES,
              "theme": THEMES, "layout": LAYOUTS}
    if isinstance(partial, dict):
        for key, value in partial.items():
            if key == "elements" and isinstance(value, dict):
                merged = dict(current["elements"])
                merged.update(value)
                current["elements"] = merged
            elif key in _ENUMS:
                # Valeur d'énumération invalide → ignorée (valeur courante gardée).
                if isinstance(value, str) and value.lower() in _ENUMS[key]:
                    current[key] = value.lower()
            elif key == "opacity":
                try:
                    current[key] = max(OPACITY_MIN, min(OPACITY_MAX, float(value)))
                except (TypeError, ValueError):
                    pass
            elif key == "position":
                current[key] = _valid_position(value)
            elif key == "click_through":
                current[key] = _as_bool(value, bool(current["click_through"]))
    validated = _validate(current)
    try:
        store.update_settings(widget=validated)
    except Exception:
        pass  # best effort : les réglages restent utilisables en mémoire
    return validated
