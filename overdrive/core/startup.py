"""Programmes au démarrage de Windows : liste et activation/désactivation.

Lecture des clés Run (HKCU/HKLM, WOW6432Node best effort) et des dossiers
Démarrage, croisée avec l'état du Gestionnaire des tâches stocké dans
``Explorer\\StartupApproved``. Sous Linux : liste vide et refus propres.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from overdrive.paths import is_windows

_RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_WOW_SUBKEY = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
_APPROVED_BASE = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
_APPROVED_RUN = _APPROVED_BASE + r"\Run"
_APPROVED_RUN32 = _APPROVED_BASE + r"\Run32"
_APPROVED_FOLDER = _APPROVED_BASE + r"\StartupFolder"

_STARTUP_RELATIVE = r"Microsoft\Windows\Start Menu\Programs\Startup"

# Sources registre : (clé de slug, ruche, sous-clé Run, sous-clé StartupApproved, libellé).
_REG_SOURCES: list[dict] = [
    {"key": "hkcu", "hive": "HKCU", "run": _RUN_SUBKEY, "approved": _APPROVED_RUN, "source": "HKCU"},
    {"key": "hklm", "hive": "HKLM", "run": _RUN_SUBKEY, "approved": _APPROVED_RUN, "source": "HKLM"},
    {"key": "hklm32", "hive": "HKLM", "run": _RUN_WOW_SUBKEY, "approved": _APPROVED_RUN32, "source": "HKLM"},
]


def _slug(text: str) -> str:
    """Slug stable en minuscules (lettres/chiffres, tirets)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "entree"


def _hive_handle(hive: str):  # noqa: ANN202 — type winreg indisponible hors Windows
    """Handle winreg correspondant au nom de ruche ("HKCU" ou "HKLM")."""
    import winreg  # noqa: PLC0415 — import Windows uniquement

    return winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE


def _read_run_values(hive: str, subkey: str) -> list[tuple[str, str]]:
    """Valeurs (nom, commande) d'une clé Run, best effort."""
    entries: list[tuple[str, str]] = []
    try:
        import winreg  # noqa: PLC0415

        with winreg.OpenKey(_hive_handle(hive), subkey) as key:
            index = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                if name and value:
                    entries.append((str(name), str(value)))
    except Exception:
        pass
    return entries


def _approved_map(hive: str, subkey: str) -> dict[str, bool]:
    """État activé/désactivé par nom (insensible à la casse) d'une clé StartupApproved.

    Convention Windows : premier octet pair (0x02) = activé, impair (0x03) = désactivé.
    """
    approved: dict[str, bool] = {}
    try:
        import winreg  # noqa: PLC0415

        with winreg.OpenKey(_hive_handle(hive), subkey) as key:
            index = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                if name and isinstance(value, bytes) and value:
                    approved[str(name).lower()] = value[0] % 2 == 0
    except Exception:
        pass
    return approved


def _folder_sources() -> list[dict]:
    """Dossiers Démarrage (utilisateur et commun) avec leur clé StartupApproved."""
    sources: list[dict] = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        sources.append(
            {
                "key": "dossier-utilisateur",
                "hive": "HKCU",
                "path": Path(appdata) / _STARTUP_RELATIVE,
                "approved": _APPROVED_FOLDER,
                "source": "dossier utilisateur",
            }
        )
    if programdata:
        sources.append(
            {
                "key": "dossier-commun",
                "hive": "HKLM",
                "path": Path(programdata) / _STARTUP_RELATIVE,
                "approved": _APPROVED_FOLDER,
                "source": "dossier commun",
            }
        )
    return sources


def _collect() -> list[dict]:
    """Entrées de démarrage complètes (champs publics + champs internes d'écriture)."""
    items: list[dict] = []
    seen_ids: dict[str, int] = {}

    def _unique_id(base: str) -> str:
        count = seen_ids.get(base, 0) + 1
        seen_ids[base] = count
        return base if count == 1 else f"{base}-{count}"

    for src in _REG_SOURCES:
        approved = _approved_map(src["hive"], src["approved"])
        for name, command in _read_run_values(src["hive"], src["run"]):
            items.append(
                {
                    "id": _unique_id(f"{src['key']}--{_slug(name)}"),
                    "name": name,
                    "command": command,
                    "source": src["source"],
                    "enabled": approved.get(name.lower(), True),
                    "hive": src["hive"],
                    "approved_subkey": src["approved"],
                    "approved_name": name,
                }
            )

    for src in _folder_sources():
        approved = _approved_map(src["hive"], src["approved"])
        try:
            files = sorted(p for p in src["path"].iterdir() if p.is_file())
        except Exception:
            files = []
        for path in files:
            if path.name.lower() == "desktop.ini":
                continue
            items.append(
                {
                    "id": _unique_id(f"{src['key']}--{_slug(path.stem)}"),
                    "name": path.stem,
                    "command": str(path),
                    "source": src["source"],
                    "enabled": approved.get(path.name.lower(), True),
                    "hive": src["hive"],
                    "approved_subkey": src["approved"],
                    "approved_name": path.name,
                }
            )

    return items


def list_startup() -> list[dict]:
    """Liste les programmes au démarrage (Windows) ; liste vide sous Linux."""
    if not is_windows():
        return []
    try:
        return [
            {key: item[key] for key in ("id", "name", "command", "source", "enabled")}
            for item in _collect()
        ]
    except Exception:
        return []


def set_startup_enabled(item_id: str, enabled: bool) -> dict:
    """Active ou désactive une entrée de démarrage via StartupApproved.

    Écrit uniquement la valeur binaire StartupApproved (12 octets : 0x02 pour
    activer, 0x03 pour désactiver, le reste à zéro). La commande elle-même
    n'est JAMAIS supprimée. Refus propre hors Windows ou si l'id est inconnu.
    """
    if not is_windows():
        return {
            "ok": False,
            "message": "La gestion des programmes au démarrage est disponible uniquement sous Windows.",
        }
    if not isinstance(item_id, str) or not item_id.strip():
        return {"ok": False, "message": "Identifiant d'entrée de démarrage invalide."}

    try:
        items = _collect()
    except Exception as exc:
        return {"ok": False, "message": f"Lecture des entrées de démarrage impossible : {exc}"}

    record = next((item for item in items if item["id"] == item_id), None)
    if record is None:
        return {"ok": False, "message": f"Entrée de démarrage inconnue : {item_id}."}

    payload = bytes([0x02 if enabled else 0x03]) + b"\x00" * 11
    try:
        import winreg  # noqa: PLC0415

        with winreg.CreateKeyEx(
            _hive_handle(record["hive"]),
            record["approved_subkey"],
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, record["approved_name"], 0, winreg.REG_BINARY, payload)
    except PermissionError:
        return {
            "ok": False,
            "message": "Accès refusé : relancez Overdrive en administrateur pour modifier cette entrée.",
        }
    except Exception as exc:
        return {"ok": False, "message": f"Écriture dans le registre impossible : {exc}"}

    state = "activée" if enabled else "désactivée"
    return {"ok": True, "message": f"Entrée « {record['name']} » {state}."}
