"""Mode jeu automatique : plan d'alimentation performant + priorité haute.

À l'activation (jeu détecté par le widget), mémorise le plan
d'alimentation actif, bascule sur le plan le plus performant disponible
(plan Overdrive s'il existe, sinon Performances élevées) et passe le
processus du jeu en priorité haute. En option (``pause_updates=True``),
suspend aussi les services Windows Update (wuauserv, BITS, DoSvc) qui
tournaient — et uniquement ceux-là. À la désactivation (jeu fermé),
restaure le plan mémorisé et relance uniquement les services que nous
avions arrêtés — le processus n'est plus touché, il est déjà fermé.

L'état est persisté dans ``data_dir()/gamemode_state.json`` pour résister
à un redémarrage du widget. Tout est best effort : refus propres hors
Windows, fonctions idempotentes, jamais d'exception.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from overdrive.paths import data_dir, is_windows

#: Plan « Overdrive — Performances maximales » créé par le tweak dédié.
OVERDRIVE_PLAN_GUID = "0d0d0d0d-0d0d-0d0d-0d0d-0d0d0d0d0d0d"
#: Plan Windows « Performances élevées ».
HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
#: Plan Windows « Équilibré » (restauration par défaut).
BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"

_STATE_FILE = "gamemode_state.json"
_WINDOWS_ONLY_MESSAGE = "Disponible uniquement sous Windows."

#: Services Windows Update suspendus pendant le jeu (option ``pause_updates``).
_UPDATE_SERVICES = ("wuauserv", "BITS", "DoSvc")
#: Délai maximal d'une commande d'arrêt/démarrage de service (secondes).
_SERVICE_TIMEOUT = 30

_GUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


def _creation_flags() -> int:
    """Drapeaux subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _run_powercfg(*args: str) -> subprocess.CompletedProcess | None:
    """Exécute ``powercfg`` avec les arguments donnés (best effort, 10 s)."""
    try:
        return subprocess.run(
            ["powercfg", *args],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_creation_flags(),
        )
    except Exception:
        return None


def _active_scheme_guid() -> str | None:
    """GUID du plan d'alimentation actuellement actif, ou None."""
    proc = _run_powercfg("/getactivescheme")
    if proc is None or proc.returncode != 0:
        return None
    match = _GUID_RE.search(proc.stdout or "")
    return match.group(0).lower() if match else None


def _available_scheme_guids() -> set[str]:
    """GUID (minuscules) des plans listés par ``powercfg /list``."""
    proc = _run_powercfg("/list")
    if proc is None or proc.returncode != 0:
        return set()
    return {m.group(0).lower() for m in _GUID_RE.finditer(proc.stdout or "")}


def _best_plan_guid() -> str:
    """Plan le plus performant disponible : Overdrive sinon Performances élevées."""
    available = _available_scheme_guids()
    if OVERDRIVE_PLAN_GUID in available:
        return OVERDRIVE_PLAN_GUID
    return HIGH_PERF_GUID


def _set_active_plan(guid: str) -> bool:
    """Active le plan d'alimentation ``guid`` (best effort)."""
    proc = _run_powercfg("/setactive", guid)
    return proc is not None and proc.returncode == 0


# ---------------------------------------------------------------------------
# État persistant (data_dir()/gamemode_state.json)
# ---------------------------------------------------------------------------

def _state_path():
    return data_dir() / _STATE_FILE


def _read_state() -> dict[str, Any]:
    """État mémorisé (dict vide si absent/illisible), jamais d'exception."""
    try:
        raw = json.loads(_state_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _write_state(state: dict[str, Any]) -> None:
    """Persiste l'état (best effort)."""
    try:
        _state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _clear_state() -> None:
    """Supprime le fichier d'état (best effort, idempotent)."""
    try:
        _state_path().unlink()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Priorité du processus du jeu
# ---------------------------------------------------------------------------

def _boost_process_priority(process_name: str) -> bool:
    """Passe tous les processus de ce nom en priorité haute (Windows)."""
    boosted = False
    try:
        import psutil  # noqa: PLC0415 — import tardif pour un module léger

        target = process_name.lower()
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
                if name and str(name).lower() == target:
                    proc.nice(psutil.HIGH_PRIORITY_CLASS)
                    boosted = True
            except Exception:
                continue
    except Exception:
        return False
    return boosted


# ---------------------------------------------------------------------------
# Services Windows Update (option pause_updates)
# ---------------------------------------------------------------------------

def _service_running(service_name: str) -> bool:
    """Indique si le service Windows ``service_name`` tourne (best effort)."""
    try:
        import psutil  # noqa: PLC0415 — import tardif pour un module léger

        service = psutil.win_service_get(service_name)
        return str(service.status()).lower() == "running"
    except Exception:
        return False


def _run_service_command(*args: str) -> bool:
    """Exécute une commande de gestion de service (best effort, 30 s)."""
    try:
        proc = subprocess.run(
            list(args),
            shell=False,
            capture_output=True,
            text=True,
            timeout=_SERVICE_TIMEOUT,
            creationflags=_creation_flags(),
        )
        return proc.returncode == 0
    except Exception:
        return False


def _pause_update_services() -> list[str]:
    """Arrête les services Windows Update qui tournaient ; renvoie leurs noms.

    Un service n'est arrêté QUE s'il était en cours d'exécution. Échec
    par service toléré : seuls les services effectivement arrêtés par
    nous sont renvoyés (pour les relancer à la désactivation).
    """
    paused: list[str] = []
    for name in _UPDATE_SERVICES:
        if not _service_running(name):
            continue
        stopped = _run_service_command("net", "stop", name, "/y")
        if not stopped:
            stopped = _run_service_command("sc", "stop", name)
        if stopped or not _service_running(name):
            paused.append(name)
    return paused


def _resume_paused_services(names: list) -> list[str]:
    """Relance les services listés (``sc start``) ; renvoie ceux relancés.

    Seuls les noms connus de ``_UPDATE_SERVICES`` sont acceptés (l'état
    persistant pourrait être altéré). Échec par service toléré.
    """
    restarted: list[str] = []
    for name in names:
        if not isinstance(name, str) or name not in _UPDATE_SERVICES:
            continue
        if _run_service_command("sc", "start", name):
            restarted.append(name)
    return restarted


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def activate(process_name: str, pause_updates: bool = False) -> dict:
    """Active le mode jeu pour ``process_name`` (best effort, idempotent).

    Mémorise le plan d'alimentation actif (pour le restaurer à la
    désactivation), bascule sur le plan le plus performant disponible et
    passe le processus du jeu en priorité haute. Avec
    ``pause_updates=True`` (Windows), arrête aussi les services Windows
    Update (wuauserv, BITS, DoSvc) qui tournaient — leurs noms sont
    mémorisés dans l'état persistant (``paused_services``) pour être
    relancés par :func:`deactivate`. Renvoie ``{"ok", "active",
    "message", ...}`` ; refus propre hors Windows, jamais d'exception.
    """
    try:
        if not is_windows():
            return {"ok": False, "active": False,
                    "message": _WINDOWS_ONLY_MESSAGE}

        previous_state = _read_state()
        if previous_state.get("active"):
            # Déjà actif : on conserve le plan mémorisé à l'origine,
            # ainsi que les services déjà suspendus par nous.
            previous_guid = previous_state.get("previous_plan")
            paused_services = [
                s for s in (previous_state.get("paused_services") or [])
                if isinstance(s, str)
            ]
        else:
            previous_guid = _active_scheme_guid()
            paused_services = []

        target = _best_plan_guid()
        plan_ok = _set_active_plan(target)
        priority_ok = _boost_process_priority(str(process_name))

        if pause_updates:
            already = set(paused_services)
            paused_services += [
                s for s in _pause_update_services() if s not in already
            ]

        _write_state({
            "active": True,
            "previous_plan": previous_guid,
            "plan": target,
            "process": str(process_name),
            "paused_services": paused_services,
        })

        if plan_ok and priority_ok:
            message = ("Mode jeu activé : plan performant et priorité haute "
                       f"appliqués à {process_name}.")
        elif plan_ok:
            message = ("Mode jeu activé : plan performant appliqué "
                       f"(priorité de {process_name} inchangée).")
        elif priority_ok:
            message = (f"Mode jeu activé : priorité haute pour {process_name} "
                       "(bascule du plan d'alimentation impossible).")
        else:
            message = ("Mode jeu activé, mais ni le plan d'alimentation ni "
                       "la priorité n'ont pu être modifiés.")
        if pause_updates:
            if paused_services:
                message += (" Mises à jour Windows suspendues : "
                            + ", ".join(paused_services) + ".")
            else:
                message += (" Aucun service de mise à jour Windows actif "
                            "à suspendre.")
        return {
            "ok": plan_ok or priority_ok,
            "active": True,
            "plan": target,
            "previous_plan": previous_guid,
            "priority_set": priority_ok,
            "paused_services": paused_services,
            "message": message,
        }
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {"ok": False, "active": is_active(),
                "message": f"Erreur inattendue : {exc}"}


def deactivate() -> dict:
    """Désactive le mode jeu : restaure le plan mémorisé (idempotent).

    Le processus du jeu n'est plus touché (il est déjà fermé). Sans plan
    mémorisé, restaure le plan Équilibré. Relance uniquement les services
    Windows Update listés dans ``paused_services`` (ceux que nous avions
    arrêtés), best effort. Refus propre hors Windows, jamais d'exception.
    """
    try:
        if not is_windows():
            return {"ok": False, "active": False,
                    "message": _WINDOWS_ONLY_MESSAGE}

        state = _read_state()
        if not state.get("active"):
            return {"ok": True, "active": False,
                    "message": "Le mode jeu n'était pas actif."}

        previous = state.get("previous_plan")
        target = (previous if isinstance(previous, str)
                  and _GUID_RE.fullmatch(previous.strip())
                  else BALANCED_GUID)
        target = target.strip().lower()
        plan_ok = _set_active_plan(target)

        # Relance uniquement les services que NOUS avions arrêtés.
        paused = state.get("paused_services")
        paused = paused if isinstance(paused, list) else []
        restarted = _resume_paused_services(paused)

        _clear_state()

        if plan_ok:
            message = "Mode jeu désactivé : plan d'alimentation restauré."
        else:
            message = ("Mode jeu désactivé, mais la restauration du plan "
                       "d'alimentation a échoué.")
        if paused:
            if restarted:
                message += (" Services de mise à jour relancés : "
                            + ", ".join(restarted) + ".")
            else:
                message += (" La relance des services de mise à jour "
                            "a échoué.")
        return {"ok": plan_ok, "active": False, "plan": target,
                "restarted_services": restarted, "message": message}
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {"ok": False, "active": is_active(),
                "message": f"Erreur inattendue : {exc}"}


def is_active() -> bool:
    """Indique si le mode jeu est actuellement actif (jamais d'exception)."""
    try:
        return bool(_read_state().get("active"))
    except Exception:
        return False
