"""Résolution des chemins de données de l'application (multi-plateforme)."""

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform == "win32"


def data_dir() -> Path:
    """Dossier de données utilisateur de l'application (créé si absent)."""
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        d = base / "Overdrive"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        d = base / "overdrive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def web_dir() -> Path:
    """Dossier des fichiers statiques de l'interface (compatible PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "overdrive" / "web"  # type: ignore[attr-defined]
    return Path(__file__).parent / "web"
