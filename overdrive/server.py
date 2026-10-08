"""Serveur FastAPI d'Overdrive : API REST locale + interface web statique."""

import ctypes
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

log = logging.getLogger("overdrive.server")

#: Hôtes acceptés dans l'en-tête Host (anti DNS rebinding). Complétés par
#: `configure_security()` quand l'écoute sort de la boucle locale.
_ALLOWED_HOSTS: set[str] = {"127.0.0.1", "localhost", "::1"}

#: Jeton d'accès exigé sur toutes les routes quand il est défini (mode réseau).
_ACCESS_TOKEN: str | None = None

_TOKEN_COOKIE = "overdrive_token"


def configure_security(token: str | None = None,
                       extra_hosts: list[str] | None = None) -> None:
    """Active le jeton d'accès et/ou élargit les hôtes autorisés (mode réseau)."""
    global _ACCESS_TOKEN
    _ACCESS_TOKEN = token
    for host in extra_hosts or []:
        if host:
            _ALLOWED_HOSTS.add(host.lower())

from . import APP_NAME, VERSION
from .core.ai.chat import ask
from .core.boost import run_boost
from .core.cleaner import clean, scan
from .core.games.cs2 import (
    TIERS,
    apply_video_settings,
    cs2_info,
    detect_tier,
    max_refresh_hz,
    recommended_fps_max,
    suggest_maxping,
    write_autoexec,
)
from .core.games.detect import detect_games
from .core.hardware import cached_tier, detect_hardware
from .core.latency import REGIONS, measure
from .core.monitor import sample
from .core.programs import PROGRAMS, install_program, winget_available
from .core.quiz import QUESTIONS, compute_profile
from .core.report import build_report, report_filename
from .core.secure_store import PROVIDERS, delete_key, list_keys, set_key
from .core.autostart import get_autostart, set_widget_autostart
from .core.startup import list_startup, set_startup_enabled
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

    # Warm-up matériel : la détection (cpu_percent 0,2 s + PowerShell GPU,
    # timeout 10 s) tourne en arrière-plan dès le démarrage, pour que
    # /api/status reste instantané (il lit cached_tier, jamais bloquant) et
    # que le tier soit prêt avant que l'utilisateur atteigne la page
    # Optimisations. La double vérification sous _CACHE_LOCK de
    # detect_hardware rend ce thread sûr face aux appels concurrents.
    threading.Thread(target=detect_hardware, daemon=True, name="hw-warmup").start()

    @application.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """Erreur imprévue → HTTP 500 générique (détail journalisé côté serveur)."""
        log.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Erreur interne du serveur."}
        )

    @application.middleware("http")
    async def _security(request: Request, call_next):
        """Valide l'en-tête Host et, en mode réseau, le jeton d'accès."""
        hostname = (request.url.hostname or "").lower()
        if hostname and hostname not in _ALLOWED_HOSTS:
            return JSONResponse(status_code=400, content={"detail": "Hôte non autorisé."})
        if _ACCESS_TOKEN is not None:
            supplied = (
                request.cookies.get(_TOKEN_COOKIE)
                or request.headers.get("X-Overdrive-Token")
                or request.query_params.get("token")
            )
            if supplied != _ACCESS_TOKEN:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Jeton d'accès requis : ouvrez l'URL "
                                       "complète affichée au démarrage du serveur."},
                )
            response = await call_next(request)
            if request.cookies.get(_TOKEN_COOKIE) != _ACCESS_TOKEN:
                response.set_cookie(
                    _TOKEN_COOKIE, _ACCESS_TOKEN, httponly=True, samesite="strict"
                )
            return response
        return await call_next(request)

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
        """État général de l'application.

        ``hardware_tier`` (et son alias ``tier``) vaut ``null`` tant que la
        détection matérielle n'a pas tourné : le front le traite comme
        inconnu et retente après un chargement de ``/api/hardware``. La
        lecture passe par :func:`cached_tier` qui ne déclenche JAMAIS de
        détection — cette route doit rester instantanée.
        """
        settings = get_settings()
        tier = cached_tier()
        return {
            "app": APP_NAME,
            "version": VERSION,
            "platform": _platform_name(),
            "is_windows": is_windows(),
            "is_admin": _is_admin(),
            "first_run": bool(settings.get("first_run", True)),
            "profile": settings.get("profile"),
            "theme": settings.get("theme", "light"),
            "lang": settings.get("lang", "fr"),
            "hardware_tier": tier,
            "tier": tier,
        }

    # --------------------------------------------------------------- settings

    @application.get("/api/settings")
    async def api_get_settings() -> dict:
        """Réglages complets (jamais de clés API dedans)."""
        return get_settings()

    @application.post("/api/settings")
    async def api_post_settings(payload: Any = Body(...)) -> dict:
        """Met à jour des réglages simples (liste blanche : thème, langue)."""
        data = _require_dict(payload)
        theme = data.get("theme")
        if theme is not None and theme not in ("light", "dark"):
            raise HTTPException(status_code=400, detail="Thème invalide : 'light' ou 'dark'.")
        lang = data.get("lang")
        if lang is not None and lang not in ("fr", "en"):
            raise HTTPException(status_code=400, detail="Langue invalide : 'fr' ou 'en'.")
        # Liste blanche stricte : les clés typées (profile, quiz_answers,
        # ai_provider, first_run) ont leurs propres routes validées.
        updates = {key: data[key] for key in ("theme", "lang") if data.get(key) is not None}
        if not updates:
            return get_settings()
        return update_settings(**updates)

    # --------------------------------------------------------------- hardware

    @application.get("/api/hardware")
    def api_hardware(refresh: int = 0) -> dict:
        """Détection du matériel (?refresh=1 force une nouvelle analyse)."""
        return detect_hardware(refresh=bool(refresh))

    # ----------------------------------------------------------------- tweaks

    @application.get("/api/tweaks")
    def api_tweaks() -> dict:
        """Catalogue des optimisations avec leur état."""
        return {"categories": CATEGORIES, "tweaks": list_tweaks()}

    @application.post("/api/tweaks/apply")
    def api_tweaks_apply(payload: Any = Body(...)) -> dict:
        """Applique les optimisations demandées."""
        return {"results": apply_tweaks(_require_ids(payload))}

    @application.post("/api/tweaks/revert")
    def api_tweaks_revert(payload: Any = Body(...)) -> dict:
        """Annule les optimisations demandées."""
        return {"results": revert_tweaks(_require_ids(payload))}

    @application.post("/api/restore-point")
    def api_restore_point() -> dict:
        """Crée un point de restauration Windows."""
        return create_restore_point()

    # ------------------------------------------------------------------ games

    @application.get("/api/games")
    def api_games() -> dict:
        """Catalogue des jeux avec détection d'installation."""
        return {"games": detect_games()}

    def _require_tier(value: Any) -> str | None:
        """Valide un tier optionnel (``None`` accepté, sinon un tier connu)."""
        if value is None:
            return None
        if not isinstance(value, str) or value not in TIERS:
            raise HTTPException(
                status_code=400,
                detail=f"Tier invalide : choix possibles : {', '.join(TIERS)}.",
            )
        return value

    @application.get("/api/games/cs2")
    def api_games_cs2(tier: str | None = None) -> dict:
        """Informations détaillées Counter-Strike 2 (``?tier=`` force un tier)."""
        return cs2_info(_require_tier(tier))

    @application.post("/api/games/cs2/video")
    def api_cs2_video(payload: Any = Body(default=None)) -> dict:
        """Applique le plan vidéo du tier au cs2_video.txt du joueur.

        Corps optionnel ``{"user_id": str|None, "tier": str|None}`` ; sans
        tier, le tier détecté est utilisé. L'écriture est sécurisée côté
        module (sauvegarde coffre, refus si CS2 tourne, clés présentes
        uniquement) ; sous Linux la réponse est un refus propre.
        """
        data = payload if isinstance(payload, dict) else {}
        user_id = data.get("user_id")
        if user_id is not None and not isinstance(user_id, str):
            raise HTTPException(status_code=400, detail="Le champ 'user_id' doit être une chaîne.")
        tier = _require_tier(data.get("tier"))
        if tier is None:
            tier = detect_tier().get("tier") or "midrange"
        return apply_video_settings(user_id, tier)

    @application.get("/api/games/cs2/suggestions")
    def api_cs2_suggestions() -> dict:
        """Suggestions dynamiques CS2 (appel coûteux isolé, à la demande).

        La mesure de latence (bornée à ~8 s) vit ici et non dans
        ``/api/games/cs2`` : le front l'appelle sur clic, pas au chargement.
        """
        tier_info = detect_tier()
        hz_max = max_refresh_hz()
        return {
            "maxping": suggest_maxping(),
            "fps_max": recommended_fps_max(tier_info, hz_max),
            "hz_max": hz_max,
            "tier": tier_info,
        }

    @application.post("/api/games/cs2/autoexec")
    def api_cs2_autoexec(payload: Any = Body(default=None)) -> dict:
        """Écrit l'autoexec recommandé pour CS2 (rétrocompatible sans corps).

        Corps optionnel ``{"user_id", "tier", "fps_max", "maxping",
        "sensitivity", "zoom_ratio"}`` ; bornes alignées sur celles de
        ``generate_autoexec`` (hors bornes => HTTP 400 plutôt qu'une ligne
        commentée silencieuse dans le fichier écrit).
        """
        data = payload if isinstance(payload, dict) else {}
        user_id = data.get("user_id")
        if user_id is not None and not isinstance(user_id, str):
            raise HTTPException(status_code=400, detail="Le champ 'user_id' doit être une chaîne.")
        tier = _require_tier(data.get("tier"))
        fps_max = data.get("fps_max")
        if fps_max is not None and (
                isinstance(fps_max, bool) or not isinstance(fps_max, int)
                or not (fps_max == 0 or 60 <= fps_max <= 1000)):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'fps_max' doit valoir 0 (illimité) ou un entier de 60 à 1000.",
            )
        maxping = data.get("maxping")
        if maxping is not None and (
                isinstance(maxping, bool) or not isinstance(maxping, int)
                or not 25 <= maxping <= 350):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'maxping' doit être un entier de 25 à 350.",
            )
        sensitivity = data.get("sensitivity")
        if sensitivity is not None and (
                isinstance(sensitivity, bool)
                or not isinstance(sensitivity, (int, float))
                or not 0 < float(sensitivity) <= 10):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'sensitivity' doit être un nombre entre 0 (exclu) et 10.",
            )
        zoom_ratio = data.get("zoom_ratio")
        if zoom_ratio is not None and (
                isinstance(zoom_ratio, bool)
                or not isinstance(zoom_ratio, (int, float))
                or not 0.5 <= float(zoom_ratio) <= 2.0):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'zoom_ratio' doit être un nombre entre 0,5 et 2,0.",
            )
        return write_autoexec(
            user_id=user_id,
            tier=tier,
            fps_max=fps_max,
            maxping=maxping,
            sensitivity=float(sensitivity) if sensitivity is not None else None,
            zoom_ratio=float(zoom_ratio) if zoom_ratio is not None else None,
        )

    # --------------------------------------------------------------- programs

    @application.get("/api/programs")
    def api_programs() -> dict:
        """Programmes recommandés et disponibilité de winget."""
        return {"programs": PROGRAMS, "winget": winget_available()}

    @application.post("/api/programs/install")
    def api_programs_install(payload: Any = Body(...)) -> dict:
        """Installe un programme recommandé via winget."""
        data = _require_dict(payload)
        program_id = data.get("id")
        if not isinstance(program_id, str) or not program_id:
            raise HTTPException(status_code=400, detail="Le champ 'id' est requis.")
        return install_program(program_id)

    # ---------------------------------------------------------------- cleaner

    @application.get("/api/clean/scan")
    def api_clean_scan() -> dict:
        """Analyse des cibles de nettoyage."""
        return {"targets": scan()}

    @application.post("/api/clean")
    def api_clean(payload: Any = Body(...)) -> dict:
        """Nettoie les cibles sélectionnées."""
        return {"results": clean(_require_ids(payload))}

    # ---------------------------------------------------------------- monitor

    @application.get("/api/monitor")
    def api_monitor() -> dict:
        """Échantillon instantané du moniteur système (CPU, RAM, débits, top)."""
        return sample()

    # ---------------------------------------------------------------- startup

    @application.get("/api/startup")
    def api_startup() -> dict:
        """Programmes lancés au démarrage de Windows."""
        return {"items": list_startup()}

    @application.post("/api/startup/toggle")
    def api_startup_toggle(payload: Any = Body(...)) -> dict:
        """Active ou désactive un programme au démarrage."""
        data = _require_dict(payload)
        item_id = data.get("id")
        enabled = data.get("enabled")
        if not isinstance(item_id, str) or not item_id:
            raise HTTPException(status_code=400, detail="Le champ 'id' est requis.")
        if not isinstance(enabled, bool):
            raise HTTPException(status_code=400, detail="Le champ 'enabled' doit être un booléen.")
        return set_startup_enabled(item_id, enabled)

    # ---------------------------------------------------------------- latency

    @application.get("/api/latency/regions")
    async def api_latency_regions() -> dict:
        """Régions disponibles pour l'estimation de latence."""
        return {"regions": REGIONS}

    @application.post("/api/latency")
    def api_latency(payload: Any = Body(default=None)) -> dict:
        """Mesure la latence TCP estimée vers les régions demandées (ou toutes)."""
        ids: list[str] | None = None
        if payload is not None:
            data = _require_dict(payload)
            raw_ids = data.get("ids")
            if raw_ids is not None:
                if not isinstance(raw_ids, list) or not all(isinstance(i, str) for i in raw_ids):
                    raise HTTPException(
                        status_code=400,
                        detail="Le champ 'ids' doit être une liste de chaînes.",
                    )
                ids = raw_ids
        return {"results": measure(ids)}

    # ----------------------------------------------------------------- report

    @application.get("/api/report")
    def api_report() -> PlainTextResponse:
        """Rapport système complet, servi en pièce jointe texte."""
        return PlainTextResponse(
            build_report(),
            headers={
                "Content-Disposition": f'attachment; filename="{report_filename()}"'
            },
        )

    # ------------------------------------------------------------------ boost

    @application.post("/api/boost")
    def api_boost(payload: Any = Body(default=None)) -> dict:
        """Boost en un clic : restauration, tweaks du profil, nettoyage sûr."""
        data = payload if isinstance(payload, dict) else {}
        restore_point = data.get("restore_point", True)
        if not isinstance(restore_point, bool):
            raise HTTPException(
                status_code=400, detail="Le champ 'restore_point' doit être un booléen."
            )
        return run_boost(create_restore=restore_point)

    # ------------------------------------------------------------------- quiz

    @application.get("/api/quiz")
    async def api_quiz() -> dict:
        """Questions du questionnaire de profil."""
        return {"questions": QUESTIONS}

    @application.post("/api/quiz")
    def api_quiz_submit(payload: Any = Body(...)) -> dict:
        """Calcule le profil, le sauvegarde et le retourne.

        Le tier matériel est transmis via :func:`cached_tier` (jamais de
        détection bloquante ici : le warm-up lancé par ``create_app`` rend
        le cache presque toujours chaud à ce stade) pour basculer sur le
        profil « petite_config » quand l'utilisateur ne connaît pas sa machine.
        """
        data = _require_dict(payload)
        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise HTTPException(status_code=400, detail="Le champ 'answers' doit être un objet.")
        profile = compute_profile(answers, tier=cached_tier())
        update_settings(profile=profile, quiz_answers=answers, first_run=False)
        return {"profile": profile}

    # --------------------------------------------------------------------- IA

    @application.get("/api/ai/keys")
    def api_ai_keys() -> dict:
        """Clés API configurées (masquées) et fournisseur par défaut."""
        return {
            "keys": list_keys(),
            "default_provider": get_settings().get("ai_provider"),
        }

    @application.post("/api/ai/keys")
    def api_ai_set_key(payload: Any = Body(...)) -> dict:
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
    def api_ai_delete_key(provider: str) -> dict:
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

    # ------------------------------------------------------- vague 3 (outils)
    # Imports tardifs : ces modules sont déployés progressivement et le
    # serveur doit démarrer même si l'un d'eux manque encore.

    @application.post("/api/bench")
    def api_bench_run() -> dict:
        """Lance le mini-benchmark (10-15 s) et renvoie le résultat."""
        from .core.bench import run_bench

        return run_bench()

    @application.get("/api/bench/history")
    def api_bench_history() -> dict:
        """Historique des benchmarks."""
        from .core.bench import get_history

        return {"history": get_history()}

    @application.get("/api/insights")
    def api_insights() -> dict:
        """Détections intelligentes (écran, overlays, pilotes, alimentation)."""
        from .core.insights import get_insights

        return {"insights": get_insights()}

    @application.get("/api/debloat")
    def api_debloat_list() -> dict:
        """Applications préinstallées supprimables."""
        from .core.debloat import list_installed

        return {"apps": list_installed()}

    @application.post("/api/debloat/remove")
    def api_debloat_remove(payload: Any = Body(...)) -> dict:
        """Supprime les applications préinstallées sélectionnées."""
        from .core.debloat import remove

        return {"results": remove(_require_ids(payload))}

    @application.get("/api/update/check")
    def api_update_check() -> dict:
        """Vérifie si une version plus récente est publiée."""
        from .core.updater import check_update

        return check_update()

    @application.get("/api/profile/export")
    def api_profile_export() -> JSONResponse:
        """Exporte le profil et les réglages dans un fichier JSON."""
        from datetime import datetime, timezone

        from .core.widgetcfg import get_widget_settings

        settings = get_settings()
        payload = {
            "app": APP_NAME,
            "version": VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "profile": settings.get("profile"),
            "quiz_answers": settings.get("quiz_answers"),
            "theme": settings.get("theme"),
            "lang": settings.get("lang", "fr"),
            "widget": get_widget_settings(),
        }
        filename = "overdrive-profil.json"
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @application.post("/api/profile/import")
    def api_profile_import(payload: Any = Body(...)) -> dict:
        """Importe un profil exporté (profil, réponses, réglages, widget)."""
        from .core.widgetcfg import update_widget_settings

        data = _require_dict(payload)
        if data.get("app") != APP_NAME:
            raise HTTPException(status_code=400, detail="Fichier d'export Overdrive invalide.")
        updates: dict[str, Any] = {}
        if isinstance(data.get("profile"), dict):
            updates["profile"] = data["profile"]
            updates["first_run"] = False
        if isinstance(data.get("quiz_answers"), dict):
            updates["quiz_answers"] = data["quiz_answers"]
        if data.get("theme") in ("light", "dark"):
            updates["theme"] = data["theme"]
        if data.get("lang") in ("fr", "en"):
            updates["lang"] = data["lang"]
        if updates:
            update_settings(**updates)
        if isinstance(data.get("widget"), dict):
            update_widget_settings(data["widget"])
        return {"ok": True, "message": "Profil importé.", "imported": sorted(updates.keys())}

    # ------------------------------------------------------- vague 4 (outils)

    @application.get("/api/sens/games")
    def api_sens_games() -> dict:
        """Jeux pris en charge par le convertisseur de sensibilité."""
        from .core.sensitivity import GAMES_SENS

        return {"games": GAMES_SENS}

    @application.post("/api/sens/convert")
    def api_sens_convert(payload: Any = Body(...)) -> dict:
        """Convertit une sensibilité (jeu, sens, DPI) vers tous les jeux."""
        from .core.sensitivity import convert

        data = _require_dict(payload)
        game = data.get("game")
        sens = data.get("sens")
        dpi = data.get("dpi")
        if not isinstance(game, str) or not isinstance(sens, (int, float)) \
                or not isinstance(dpi, int):
            raise HTTPException(
                status_code=400,
                detail="Champs requis : 'game' (str), 'sens' (nombre), 'dpi' (entier).",
            )
        return convert(game, float(sens), dpi)

    @application.get("/api/crosshairs")
    def api_crosshairs() -> dict:
        """Bibliothèque de viseurs CS2."""
        from .core.crosshairs import CROSSHAIRS

        return {"crosshairs": CROSSHAIRS}

    @application.get("/api/vault")
    def api_vault() -> dict:
        """Cibles sauvegardables et sauvegardes existantes du coffre de configs."""
        from .core.configvault import list_backups, vault_targets

        return {"targets": vault_targets(), "backups": list_backups()}

    @application.post("/api/vault/backup")
    def api_vault_backup(payload: Any = Body(default=None)) -> dict:
        """Sauvegarde les configurations de jeux sélectionnées (ou toutes)."""
        from .core.configvault import backup

        data = payload if isinstance(payload, dict) else {}
        ids = data.get("ids")
        if ids is not None and (not isinstance(ids, list)
                                or not all(isinstance(i, str) for i in ids)):
            raise HTTPException(status_code=400, detail="Le champ 'ids' doit être une liste de chaînes.")
        return backup(ids)

    @application.post("/api/vault/restore")
    def api_vault_restore(payload: Any = Body(...)) -> dict:
        """Restaure une sauvegarde du coffre (sauvegarde de sécurité automatique)."""
        from .core.configvault import restore

        data = _require_dict(payload)
        backup_id = data.get("id")
        ids = data.get("ids")
        if not isinstance(backup_id, str) or not backup_id:
            raise HTTPException(status_code=400, detail="Le champ 'id' est requis.")
        if ids is not None and (not isinstance(ids, list)
                                or not all(isinstance(i, str) for i in ids)):
            raise HTTPException(status_code=400, detail="Le champ 'ids' doit être une liste de chaînes.")
        return restore(backup_id, ids)

    @application.post("/api/vault/delete")
    def api_vault_delete(payload: Any = Body(...)) -> dict:
        """Supprime une sauvegarde du coffre."""
        from .core.configvault import delete_backup

        data = _require_dict(payload)
        backup_id = data.get("id")
        if not isinstance(backup_id, str) or not backup_id:
            raise HTTPException(status_code=400, detail="Le champ 'id' est requis.")
        return delete_backup(backup_id)

    @application.post("/api/netstab")
    def api_netstab(payload: Any = Body(default=None)) -> dict:
        """Test de stabilité réseau (perte de paquets et gigue)."""
        from .core.netstab import run_stability

        data = payload if isinstance(payload, dict) else {}
        region = data.get("region")
        duration = data.get("duration")
        if region is not None and not isinstance(region, str):
            raise HTTPException(status_code=400, detail="Le champ 'region' doit être une chaîne.")
        if duration is not None and not isinstance(duration, int):
            raise HTTPException(status_code=400, detail="Le champ 'duration' doit être un entier.")
        return run_stability(region, duration if duration is not None else 20)

    @application.get("/api/netusage")
    def api_netusage() -> dict:
        """Activité réseau : débits globaux, connexions par application, suspects."""
        from .core.netusage import snapshot

        return snapshot()

    @application.get("/api/schedule")
    def api_schedule_get() -> dict:
        """État du nettoyage planifié hebdomadaire."""
        from .core.scheduler import get_schedule

        return get_schedule()

    @application.post("/api/schedule")
    def api_schedule_set(payload: Any = Body(...)) -> dict:
        """Active ou désactive le nettoyage planifié hebdomadaire."""
        from .core.scheduler import set_schedule

        data = _require_dict(payload)
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            raise HTTPException(status_code=400, detail="Le champ 'enabled' doit être un booléen.")
        return set_schedule(enabled)

    # ----------------------------------------------------------------- widget

    @application.get("/api/widget")
    def api_widget_get() -> dict:
        """Réglages du widget et état réel du démarrage automatique."""
        from .core.widgetcfg import get_widget_settings

        return {"widget": get_widget_settings(), "autostart": get_autostart()}

    @application.post("/api/widget")
    def api_widget_post(payload: Any = Body(...)) -> dict:
        """Met à jour les réglages du widget (fusion partielle validée).

        Si "autostart" est fourni, l'entrée de démarrage Windows est
        synchronisée en plus du réglage persistant.
        """
        from .core.widgetcfg import update_widget_settings

        data = _require_dict(payload)
        config = update_widget_settings(data)
        autostart_result = None
        if "autostart" in data:
            autostart_result = set_widget_autostart(config["autostart"])
        return {
            "widget": config,
            "autostart": get_autostart(),
            "autostart_result": autostart_result,
        }

    @application.post("/api/widget/launch")
    def api_widget_launch() -> dict:
        """Lance le widget dans un processus détaché."""
        import subprocess

        if getattr(sys, "frozen", False):
            command = [sys.executable, "--widget"]
        else:
            run_py = Path(__file__).resolve().parent.parent / "run.py"
            command = [sys.executable, str(run_py), "--widget"]
        kwargs: dict[str, Any] = {}
        if is_windows():
            kwargs["creationflags"] = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                **kwargs,
            )
            return {"ok": True, "message": "Widget lancé."}
        except Exception:
            log.exception("Échec du lancement du widget")
            return {"ok": False, "message": "Impossible de lancer le widget."}

    return application


app = create_app()
