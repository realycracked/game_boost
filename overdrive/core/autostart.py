"""Démarrage automatique du widget via la clé Run du registre Windows.

Valeur ``OverdriveWidget`` sous ``HKCU\\Software\\Microsoft\\Windows\\
CurrentVersion\\Run`` : absente → « never », commande contenant
``--wait-game`` → « game », sinon → « always ». Hors Windows : refus propres,
jamais d'exception.
"""

from __future__ import annotations

import sys
from pathlib import Path

from overdrive.paths import is_windows

_RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "OverdriveWidget"
_MODES: tuple[str, ...] = ("never", "always", "game")


def _quote(part: str) -> str:
    """Encadre l'argument de guillemets si nécessaire (espaces) pour le registre."""
    text = str(part)
    if not text:
        return '""'
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        return text
    if any(ch.isspace() for ch in text):
        return f'"{text}"'
    return text


def _launch_command(args: list[str]) -> str:
    """Commande de lancement pour la clé Run, correctement quotée.

    Exécutable gelé (PyInstaller) → ``"<exe>"`` ; sinon
    ``"<python>" "<run.py absolu>"`` ; les ``args`` sont ajoutés à la suite.
    """
    if getattr(sys, "frozen", False):
        base = f'"{sys.executable}"'
    else:
        run_py = Path(__file__).resolve().parents[2] / "run.py"
        base = f'"{sys.executable}" "{run_py}"'
    parts = [base] + [_quote(arg) for arg in args]
    return " ".join(parts)


def get_autostart() -> dict:
    """Mode de démarrage automatique du widget lu dans le registre réel.

    Renvoie ``{"widget_mode": "never"|"always"|"game", "supported": bool}`` ;
    hors Windows : ``supported`` False et mode « never », sans exception.
    """
    if not is_windows():
        return {
            "widget_mode": "never",
            "supported": False,
            "message": "Disponible uniquement sous Windows.",
        }
    try:
        import winreg  # noqa: PLC0415 — module Windows uniquement

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_SUBKEY) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE_NAME)
    except FileNotFoundError:
        return {"widget_mode": "never", "supported": True}
    except Exception:
        return {"widget_mode": "never", "supported": True}
    command = str(value)
    mode = "game" if "--wait-game" in command else "always"
    return {"widget_mode": mode, "supported": True}


def set_widget_autostart(mode: str) -> dict:
    """Active/désactive le lancement automatique du widget (clé Run HKCU).

    ``never`` supprime la valeur ; ``always`` enregistre ``<cmd> --widget`` ;
    ``game`` enregistre ``<cmd> --widget --wait-game``.
    Renvoie ``{"ok": bool, "message": str}``.
    """
    if not isinstance(mode, str) or mode not in _MODES:
        return {
            "ok": False,
            "message": f"Mode inconnu : {mode!r} (attendu : never, always ou game).",
        }
    if not is_windows():
        return {"ok": False, "message": "Disponible uniquement sous Windows."}
    try:
        import winreg  # noqa: PLC0415

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, _RUN_SUBKEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if mode == "never":
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
                message = "Démarrage automatique du widget désactivé."
            else:
                args = ["--widget"] if mode == "always" else ["--widget", "--wait-game"]
                winreg.SetValueEx(
                    key, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command(args)
                )
                message = (
                    "Widget lancé à chaque démarrage de Windows."
                    if mode == "always"
                    else "Widget lancé avec Windows, affiché quand un jeu démarre."
                )
        return {"ok": True, "message": message}
    except Exception as exc:
        return {"ok": False, "message": f"Écriture du registre impossible : {exc}"}
