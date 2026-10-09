"""Nettoyage planifié hebdomadaire via le Planificateur de tâches Windows.

Tâche ``OverdriveNettoyage`` (schtasks) : chaque dimanche à 11 h, lance
Overdrive avec ``--clean-safe`` (nettoyage des cibles sûres, sans interface).
Hors Windows : refus propres, jamais d'exception.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from overdrive.paths import is_windows

_TASK_NAME = "OverdriveNettoyage"
_TIMEOUT_S = 30
_WINDOWS_ONLY_MESSAGE = "Disponible uniquement sous Windows."


def _creationflags() -> int:
    """Pas de fenêtre console pour schtasks sous Windows."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0


def _launch_command() -> str:
    """Commande lancée par la tâche planifiée, correctement quotée.

    Exécutable gelé (PyInstaller) → ``"<exe>" --clean-safe`` ; sinon
    ``"<python>" "<run.py absolu>" --clean-safe`` — même motif que
    ``overdrive.core.autostart._launch_command``.
    """
    if getattr(sys, "frozen", False):
        base = f'"{sys.executable}"'
    else:
        run_py = Path(__file__).resolve().parents[2] / "run.py"
        base = f'"{sys.executable}" "{run_py}"'
    return f"{base} --clean-safe"


def _run_schtasks(args: list[str]) -> subprocess.CompletedProcess:
    """Exécute schtasks sans shell, sortie capturée, délai maximal 30 s."""
    return subprocess.run(
        ["schtasks", *args],
        shell=False,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        creationflags=_creationflags(),
    )


def _error_detail(proc: subprocess.CompletedProcess) -> str:
    """Dernière ligne utile de la sortie de schtasks (ou le code retour)."""
    lines = (proc.stderr or proc.stdout or "").strip().splitlines()
    return lines[-1].strip() if lines else f"code {proc.returncode}"


def get_schedule() -> dict:
    """État du nettoyage planifié hebdomadaire.

    Renvoie ``{"enabled": bool, "supported": bool, "detail": str | None}`` ;
    ``enabled`` est vrai si la tâche planifiée « OverdriveNettoyage » existe
    (schtasks /Query /TN ... /XML). Hors Windows : ``supported`` False,
    jamais d'exception.
    """
    if not is_windows():
        return {"enabled": False, "supported": False, "detail": _WINDOWS_ONLY_MESSAGE}
    try:
        proc = _run_schtasks(["/Query", "/TN", _TASK_NAME, "/XML"])
    except subprocess.TimeoutExpired:
        return {
            "enabled": False,
            "supported": True,
            "detail": "schtasks ne répond pas (délai de 30 s dépassé).",
        }
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {
            "enabled": False,
            "supported": True,
            "detail": f"Lecture de la tâche planifiée impossible : {exc}",
        }
    if proc.returncode == 0:
        return {"enabled": True, "supported": True, "detail": "Chaque dimanche à 11 h."}
    # Tâche absente (ou /Query refusé) : nettoyage planifié désactivé.
    return {"enabled": False, "supported": True, "detail": None}


def set_schedule(enabled: bool) -> dict:
    """Active ou désactive le nettoyage hebdomadaire (dimanche 11 h).

    ``enabled`` crée (ou remplace, /F) la tâche « OverdriveNettoyage » qui
    lance Overdrive avec ``--clean-safe`` ; sinon la tâche est supprimée.
    Renvoie ``{"ok": bool, "message": str}`` ; refus propre hors Windows.
    """
    if not is_windows():
        return {"ok": False, "message": _WINDOWS_ONLY_MESSAGE}
    try:
        if bool(enabled):
            proc = _run_schtasks(
                [
                    "/Create",
                    "/TN", _TASK_NAME,
                    "/SC", "WEEKLY",
                    "/D", "SUN",
                    "/ST", "11:00",
                    "/F",
                    "/TR", _launch_command(),
                ]
            )
            if proc.returncode == 0:
                return {
                    "ok": True,
                    "message": "Nettoyage automatique programmé chaque dimanche à 11 h.",
                }
            return {
                "ok": False,
                "message": (
                    "Création de la tâche planifiée impossible : "
                    f"{_error_detail(proc)}"
                ),
            }
        if not get_schedule().get("enabled"):
            return {"ok": True, "message": "Aucun nettoyage planifié à désactiver."}
        proc = _run_schtasks(["/Delete", "/TN", _TASK_NAME, "/F"])
        if proc.returncode == 0:
            return {"ok": True, "message": "Nettoyage automatique désactivé."}
        return {
            "ok": False,
            "message": (
                "Suppression de la tâche planifiée impossible : "
                f"{_error_detail(proc)}"
            ),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "schtasks ne répond pas (délai de 30 s dépassé)."}
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {"ok": False, "message": f"Erreur inattendue : {exc}"}
