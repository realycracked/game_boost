"""Serveur FastAPI d'Overdrive : API REST locale + interface web statique."""

import ctypes
import os
import sys
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import APP_NAME, VERSION
from .core.ai.chat import ask
from .core.cleaner import clean, scan
from .core.games.cs2 import cs2_info, write_autoexec
from .core.games.detect import detect_games
from .core.hardware import detect_hardware
from .core.programs import PROGRAMS, install_program, winget_available
from .core.quiz import QUESTIONS, compute_profile
from .core.secure_store import PROVIDERS, delete_key, list_keys, set_key
from .core.tweaks.catalog import CATEGORIES
from .core.tweaks.engine import (
    apply_tweaks,
    create_restore_point,
    list_tweaks,
    revert_tweaks,
)
from .paths import is_windows, web_dir
from .store import get_settings, update_settings

_SIMPLE_TYPES = (str, int, float, bool, type(None))


def _platform_name() -> str:
    """Nom de plateforme lisible ("windows", "linux", "darwin"...)."""
    if is_windows():
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _is_admin() -> bool:
    """Vrai si le processus a des droits administrateur (best effort)."""
    try:
        if is_windows():
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0
    except Exception:
        return False


def _require_dict(payload: Any, label: str = "corps") -> dict:
    """Valide qu'un corps de requête est bien un objet JSON."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail=f"Le {label} doit être un objet JSON.")
    return payload


def _require_ids(payload: Any) -> list[str]:
    """Extrait et valide la liste d'identifiants d'un corps {"ids": [...]}."""
    data = _require_dict(payload)
    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise HTTPException(status_code=400, detail="Le champ 'ids' doit être une liste de chaînes.")
    return ids


def create_app() -> FastAPI:
    """Construit et retourne l'application FastAPI d'Overdrive."""
    application = FastAPI(title=APP_NAME, version=VERSION, docs_url=None, redoc_url=None)

    @application.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """Erreur imprévue → HTTP 500 avec un détail JSON."""
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # ----------------------------------------------------------------- static

    application.mount(
        "/static",
        StaticFiles(directory=str(web_dir()), check_dir=False),
        name="static",
    )

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        """Page d'accueil de l'interface."""
        index_path = web_dir() / "index.html"
        if not index_path.is_file():
            raise HTTPException(status_code=500, detail="Fichiers de l'interface introuvables.")
        return FileResponse(index_path, media_type="text/html")

    # ----------------------------------------------------------------- status

    @application.get("/api/status")
    async def api_status() -> dict:
        """État général de l'application."""
        settings = get_settings()
        return {
            "app": APP_NAME,
            "version": VERSION,
            "platform": _platform_name(),
            "is_windows": is_windows(),
            "is_admin": _is_admin(),
            "first_run": bool(settings.get("first_run", True)),
            "profile": settings.get("profile"),
            "theme": settings.get("theme", "light"),
        }

    # --------------------------------------------------------------- settings

    @application.get("/api/settings")
    async def api_get_settings() -> dict:
        """Réglages complets (jamais de clés API dedans)."""
        return get_settings()

    @application.post("/api/settings")
    async def api_post_settings(payload: Any = Body(...)) -> dict:
        """Met à jour des réglages simples (thème, etc.)."""
        data = _require_dict(payload)
        theme = data.get("theme")
        if theme is not None and theme not in ("light", "dark"):
            raise HTTPException(status_code=400, detail="Thème invalide : 'light' ou 'dark'.")
        updates = {
            key: value
            for key, value in data.items()
            if isinstance(key, str) and isinstance(value, _SIMPLE_TYPES)
        }
        if not updates:
            return get_settings()
        return update_settings(**updates)

    # --------------------------------------------------------------- hardware

    @application.get("/api/hardware")
    async def api_hardware(refresh: int = 0) -> dict:
        """Détection du matériel (?refresh=1 force une nouvelle analyse)."""
        return detect_hardware(refresh=bool(refresh))

    # ----------------------------------------------------------------- tweaks

    @application.get("/api/tweaks")
    async def api_tweaks() -> dict:
        """Catalogue des optimisations avec leur état."""
        return {"categories": CATEGORIES, "tweaks": list_tweaks()}

    @application.post("/api/tweaks/apply")
    async def api_tweaks_apply(payload: Any = Body(...)) -> dict:
        """Applique les optimisations demandées."""
        return {"results": apply_tweaks(_require_ids(payload))}

    @application.post("/api/tweaks/revert")
    async def api_tweaks_revert(payload: Any = Body(...)) -> dict:
        """Annule les optimisations demandées."""
        return {"results": revert_tweaks(_require_ids(payload))}

    @application.post("/api/restore-point")
    async def api_restore_point() -> dict:
        """Crée un point de restauration Windows."""
        return create_restore_point()

    # ------------------------------------------------------------------ games

    @application.get("/api/games")
    async def api_games() -> dict:
        """Catalogue des jeux avec détection d'installation."""
        return {"games": detect_games()}

    @application.get("/api/games/cs2")
    async def api_games_cs2() -> dict:
        """Informations détaillées Counter-Strike 2."""
        return cs2_info()

    @application.post("/api/games/cs2/autoexec")
    async def api_cs2_autoexec(payload: Any = Body(default=None)) -> dict:
        """Écrit l'autoexec recommandé pour CS2."""
        data = payload if isinstance(payload, dict) else {}
        user_id = data.get("user_id")
        if user_id is not None and not isinstance(user_id, str):
            raise HTTPException(status_code=400, detail="Le champ 'user_id' doit être une chaîne.")
        return write_autoexec(user_id=user_id)

    # --------------------------------------------------------------- programs

    @application.get("/api/programs")
    async def api_programs() -> dict:
        """Programmes recommandés et disponibilité de winget."""
        return {"programs": PROGRAMS, "winget": winget_available()}

    @application.post("/api/programs/install")
    async def api_programs_install(payload: Any = Body(...)) -> dict:
        """Installe un programme recommandé via winget."""
        data = _require_dict(payload)
        program_id = data.get("id")
        if not isinstance(program_id, str) or not program_id:
            raise HTTPException(status_code=400, detail="Le champ 'id' est requis.")
        return install_program(program_id)

    # ---------------------------------------------------------------- cleaner

    @application.get("/api/clean/scan")
    async def api_clean_scan() -> dict:
        """Analyse des cibles de nettoyage."""
        return {"targets": scan()}

    @application.post("/api/clean")
    async def api_clean(payload: Any = Body(...)) -> dict:
        """Nettoie les cibles sélectionnées."""
        return {"results": clean(_require_ids(payload))}

    # ------------------------------------------------------------------- quiz

    @application.get("/api/quiz")
    async def api_quiz() -> dict:
        """Questions du questionnaire de profil."""
        return {"questions": QUESTIONS}

    @application.post("/api/quiz")
    async def api_quiz_submit(payload: Any = Body(...)) -> dict:
        """Calcule le profil, le sauvegarde et le retourne."""
        data = _require_dict(payload)
        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise HTTPException(status_code=400, detail="Le champ 'answers' doit être un objet.")
        profile = compute_profile(answers)
        update_settings(profile=profile, quiz_answers=answers, first_run=False)
        return {"profile": profile}

    # --------------------------------------------------------------------- IA

    @application.get("/api/ai/keys")
    async def api_ai_keys() -> dict:
        """Clés API configurées (masquées) et fournisseur par défaut."""
        return {
            "keys": list_keys(),
            "default_provider": get_settings().get("ai_provider"),
        }

    @application.post("/api/ai/keys")
    async def api_ai_set_key(payload: Any = Body(...)) -> dict:
        """Enregistre une clé API ; la première devient le fournisseur par défaut."""
        data = _require_dict(payload)
        provider = data.get("provider")
        key = data.get("key")
        if not isinstance(provider, str) or not provider:
            raise HTTPException(status_code=400, detail="Le champ 'provider' est requis.")
        if not isinstance(key, str) or not key.strip():
            raise HTTPException(status_code=400, detail="Le champ 'key' est requis.")
        result = set_key(provider, key)
        if result.get("ok") and not get_settings().get("ai_provider"):
            update_settings(ai_provider=provider)
        result["default_provider"] = get_settings().get("ai_provider")
        return result

    @application.delete("/api/ai/keys/{provider}")
    async def api_ai_delete_key(provider: str) -> dict:
        """Supprime la clé API d'un fournisseur."""
        return delete_key(provider)

    @application.post("/api/ai/default")
    async def api_ai_default(payload: Any = Body(...)) -> dict:
        """Change le fournisseur IA par défaut."""
        data = _require_dict(payload)
        provider = data.get("provider")
        if provider not in PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Fournisseur inconnu. Choix possibles : {', '.join(PROVIDERS)}.",
            )
        return update_settings(ai_provider=provider)

    @application.post("/api/ai/chat")
    async def api_ai_chat(payload: Any = Body(...)) -> dict:
        """Question à l'assistant IA (toujours HTTP 200, 'ok' porte l'erreur)."""
        data = _require_dict(payload)
        messages = data.get("messages")
        provider = data.get("provider")
        if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
            return {
                "ok": False,
                "reply": None,
                "message": "Le champ 'messages' doit être une liste de messages {role, content}.",
                "provider": provider if isinstance(provider, str) else "",
            }
        if provider is not None and not isinstance(provider, str):
            provider = None
        try:
            return await ask(messages, provider=provider)
        except Exception as exc:  # garde-fou : jamais d'erreur HTTP ici
            return {
                "ok": False,
                "reply": None,
                "message": f"Erreur inattendue de l'assistant : {exc}",
                "provider": provider or "",
            }

    return application


app = create_app()
