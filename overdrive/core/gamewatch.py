"""Détection légère du jeu en cours via les processus du catalogue.

Parcourt les processus (``psutil``) et les compare, insensible à la casse,
aux ``process_names`` des jeux du catalogue. Un cache de 3 secondes (protégé
par un verrou) évite de rescanner la table des processus à chaque appel.
"""

from __future__ import annotations

import threading
import time
from typing import Any

_CACHE_TTL: float = 3.0

_LOCK = threading.Lock()
_cache_result: dict[str, Any] | None = None
_cache_at: float = 0.0
_cache_valid: bool = False


def _running_names() -> set[str]:
    """Noms (minuscules) des processus en cours, best effort."""
    names: set[str] = set()
    try:
        import psutil  # noqa: PLC0415 — import tardif pour un module léger

        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
            except Exception:
                continue
            if name:
                names.add(str(name).lower())
    except Exception:
        pass
    return names


def _scan() -> dict[str, Any] | None:
    """Premier jeu du catalogue dont un exécutable tourne, sinon None."""
    running = _running_names()
    if not running:
        return None
    try:
        from overdrive.core.games.catalog import GAMES  # noqa: PLC0415
    except Exception:
        return None
    for game in GAMES:
        for proc_name in game.get("process_names") or []:
            if str(proc_name).lower() in running:
                return {
                    "id": game.get("id"),
                    "name": game.get("name"),
                    "process": proc_name,
                }
    return None


def current_game() -> dict[str, Any] | None:
    """Jeu du catalogue actuellement lancé : ``{"id","name","process"}`` ou None.

    Comparaison insensible à la casse ; résultat mis en cache 3 s ;
    ne lève jamais d'exception.
    """
    global _cache_result, _cache_at, _cache_valid
    try:
        with _LOCK:
            now = time.monotonic()
            if _cache_valid and (now - _cache_at) < _CACHE_TTL:
                return dict(_cache_result) if _cache_result else None
            result = _scan()
            _cache_result = result
            _cache_at = now
            _cache_valid = True
            return dict(result) if result else None
    except Exception:
        return None


def invalidate_cache() -> None:
    """Force un nouveau scan au prochain appel de :func:`current_game`."""
    global _cache_valid
    with _LOCK:
        _cache_valid = False
