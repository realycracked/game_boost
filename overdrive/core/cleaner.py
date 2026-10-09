"""Nettoyage des fichiers temporaires et caches (scan rapide, suppression tolérante).

Les caches de shaders AMD (``amd_dxcache``, ``amd_dxccache``,
``amd_vkcache``) et le cache de shaders Steam de CS2
(``steam_shadercache_cs2``) sont des cibles MANUELLES : utiles après une
mise à jour du pilote ou en cas de saccades persistantes, elles ne font
pas partie du nettoyage « sûr » automatique (boost, ``--clean-safe``
planifié, dont les listes d'identifiants sont fermées) et sont signalées
``default_selected: False`` dans :func:`scan`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from overdrive.paths import is_windows

#: Identifiants des cibles à ne jamais cocher ni nettoyer automatiquement
#: (recompilation des shaders = saccades temporaires aux parties suivantes).
MANUAL_ONLY_IDS = frozenset(
    {"amd_dxcache", "amd_dxccache", "amd_vkcache", "steam_shadercache_cs2"}
)

_SHADER_REBUILD_NOTE = (
    "À vider seulement après une mise à jour du pilote graphique ou en cas "
    "de saccades persistantes : les premières parties suivantes recompilent "
    "les shaders (saccades temporaires). Jamais inclus dans le nettoyage "
    "automatique."
)
_SHADER_REBUILD_NOTE_EN = (
    "Only clear it after a graphics driver update or if stutters persist: "
    "the next few matches recompile the shaders (temporary stutters). Never "
    "part of the automatic cleanup."
)


def _steam_cs2_shadercache_paths() -> list[Path]:
    """Dossiers ``steamapps/shadercache/730`` des bibliothèques Steam (best effort)."""
    try:
        from overdrive.core.games.detect import steam_libraries  # noqa: PLC0415

        return [lib / "steamapps" / "shadercache" / "730" for lib in steam_libraries()]
    except Exception:
        return []


def _amd_and_steam_targets(local: Path) -> list[dict]:
    """Cibles manuelles : caches de shaders AMD et cache de shaders Steam de CS2."""
    targets = [
        {
            "id": "amd_dxcache",
            "name": "Cache shaders AMD (DirectX 9/11)",
            "name_en": "AMD shader cache (DirectX 9/11)",
            "paths": [local / "AMD" / "DxCache"],
            "pattern": None,
            "special": None,
            "description": ("Shaders compilés par le pilote AMD pour les jeux "
                            "DirectX 9/11 (dont CS2 par défaut). "
                            + _SHADER_REBUILD_NOTE),
            "description_en": ("Shaders compiled by the AMD driver for DirectX "
                               "9/11 games (including CS2 by default). "
                               + _SHADER_REBUILD_NOTE_EN),
            "default_selected": False,
        },
        {
            "id": "amd_dxccache",
            "name": "Cache shaders AMD (DirectX 12)",
            "name_en": "AMD shader cache (DirectX 12)",
            "paths": [local / "AMD" / "DxcCache"],
            "pattern": None,
            "special": None,
            "description": ("Cache du compilateur de shaders DirectX 12 du "
                            "pilote AMD. " + _SHADER_REBUILD_NOTE),
            "description_en": ("The AMD driver's DirectX 12 shader compiler "
                               "cache. " + _SHADER_REBUILD_NOTE_EN),
            "default_selected": False,
        },
        {
            "id": "amd_vkcache",
            "name": "Cache shaders AMD (Vulkan)",
            "name_en": "AMD shader cache (Vulkan)",
            "paths": [local / "AMD" / "VkCache"],
            "pattern": None,
            "special": None,
            "description": ("Shaders Vulkan compilés par le pilote AMD (CS2 "
                            "lancé avec -vulkan, par exemple). "
                            + _SHADER_REBUILD_NOTE),
            "description_en": ("Vulkan shaders compiled by the AMD driver (CS2 "
                               "launched with -vulkan, for instance). "
                               + _SHADER_REBUILD_NOTE_EN),
            "default_selected": False,
        },
    ]
    steam_paths = _steam_cs2_shadercache_paths()
    if steam_paths:
        targets.append({
            "id": "steam_shadercache_cs2",
            "name": "Cache shaders Steam de CS2",
            "name_en": "CS2 Steam shader cache",
            "paths": steam_paths,
            "pattern": None,
            "special": None,
            "description": ("Cache de shaders tenu par Steam pour Counter-Strike "
                            "2 (steamapps/shadercache/730), reconstruit par "
                            "Steam et le jeu. " + _SHADER_REBUILD_NOTE),
            "description_en": ("Shader cache kept by Steam for Counter-Strike 2 "
                               "(steamapps/shadercache/730), rebuilt by Steam "
                               "and the game. " + _SHADER_REBUILD_NOTE_EN),
            "default_selected": False,
        })
    return targets


def _targets() -> list[dict]:
    """Cibles de nettoyage selon la plateforme.

    Chaque cible : id, name, paths (liste), pattern (préfixe de nom de fichier
    ou None = tous), special ("recycle_bin" ou None) ; facultativement
    name_en, description, description_en et default_selected (cibles
    manuelles, voir :data:`MANUAL_ONLY_IDS`).
    """
    if not is_windows():
        # Mode développement Linux : /tmp uniquement.
        return [
            {
                "id": "temp_user",
                "name": "Fichiers temporaires (/tmp)",
                "paths": [Path("/tmp")],
                "pattern": None,
                "special": None,
            }
        ]

    local = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local"))
    windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    system_drive = os.environ.get("SystemDrive", "C:")
    return [
        {
            "id": "temp_user",
            "name": "Fichiers temporaires utilisateur",
            "paths": [Path(os.environ.get("TEMP", str(local / "Temp")))],
            "pattern": None,
            "special": None,
        },
        {
            "id": "temp_windows",
            "name": "Fichiers temporaires Windows",
            "paths": [windir / "Temp"],
            "pattern": None,
            "special": None,
        },
        {
            "id": "shader_dx",
            "name": "Cache shaders DirectX",
            "paths": [local / "D3DSCache"],
            "pattern": None,
            "special": None,
        },
        {
            "id": "shader_nvidia",
            "name": "Cache shaders NVIDIA",
            "paths": [local / "NVIDIA" / "DXCache", local / "NVIDIA" / "GLCache"],
            "pattern": None,
            "special": None,
        },
        *_amd_and_steam_targets(local),
        {
            "id": "thumbnails",
            "name": "Cache des vignettes",
            "paths": [local / "Microsoft" / "Windows" / "Explorer"],
            "pattern": "thumbcache",
            "special": None,
        },
        {
            "id": "windows_update",
            "name": "Cache Windows Update",
            "paths": [windir / "SoftwareDistribution" / "Download"],
            "pattern": None,
            "special": None,
        },
        {
            "id": "recycle_bin",
            "name": "Corbeille",
            "paths": [Path(system_drive + "\\$Recycle.Bin")],
            "pattern": None,
            "special": "recycle_bin",
        },
    ]


def _iter_files(target: dict):
    """Itère les fichiers d'une cible (chemin, taille), erreurs ignorées fichier par fichier."""
    pattern = target.get("pattern")
    for root_path in target["paths"]:
        try:
            if not root_path.is_dir():
                continue
        except OSError:
            continue
        if pattern is not None:
            # Cible à motif : fichiers du dossier racine uniquement (ex. thumbcache*).
            try:
                entries = list(os.scandir(root_path))
            except OSError:
                continue
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False) and entry.name.lower().startswith(pattern):
                        yield Path(entry.path), entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
            continue
        for dirpath, _dirnames, filenames in os.walk(root_path, onerror=lambda _e: None):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                try:
                    yield file_path, file_path.lstat().st_size
                except OSError:
                    continue


def _measure(target: dict) -> tuple[int, int]:
    """Taille totale (octets) et nombre de fichiers d'une cible."""
    total = 0
    count = 0
    for _path, size in _iter_files(target):
        total += size
        count += 1
    return total, count


def scan() -> list[dict]:
    """Analyse les cibles de nettoyage et renvoie leur taille et nombre de fichiers.

    Clés historiques : id, name, path, size_mb, files. Clés additives :
    name_en, description, description_en (``None`` si absentes) et
    default_selected (``False`` pour les cibles manuelles, à ne pas cocher
    d'office côté interface).
    """
    results: list[dict] = []
    for target in _targets():
        size_bytes, files = _measure(target)
        results.append(
            {
                "id": target["id"],
                "name": target["name"],
                "path": " ; ".join(str(p) for p in target["paths"]),
                "size_mb": round(size_bytes / 2**20, 1),
                "files": files,
                "name_en": target.get("name_en"),
                "description": target.get("description"),
                "description_en": target.get("description_en"),
                "default_selected": bool(target.get("default_selected", True)),
            }
        )
    return results


def _clean_recycle_bin(target: dict) -> dict:
    """Vide la corbeille via PowerShell (Windows uniquement)."""
    size_bytes, _files = _measure(target)
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction Stop"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0,
        )
    except Exception as exc:
        return {"id": target["id"], "ok": False, "freed_mb": 0.0, "message": f"Échec du vidage de la corbeille : {exc}"}
    if proc.returncode == 0:
        return {
            "id": target["id"],
            "ok": True,
            "freed_mb": round(size_bytes / 2**20, 1),
            "message": "Corbeille vidée.",
        }
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    last = detail[-1] if detail else f"code {proc.returncode}"
    return {"id": target["id"], "ok": False, "freed_mb": 0.0, "message": f"Échec du vidage de la corbeille : {last}"}


def _clean_target(target: dict) -> dict:
    """Supprime les fichiers d'une cible un par un, en ignorant les verrous."""
    freed = 0
    deleted = 0
    skipped = 0
    for file_path, size in _iter_files(target):
        try:
            file_path.unlink()
            freed += size
            deleted += 1
        except OSError:
            skipped += 1
    # Suppression best effort des sous-dossiers vides (jamais la racine de la cible).
    if target.get("pattern") is None:
        for root_path in target["paths"]:
            try:
                if not root_path.is_dir():
                    continue
            except OSError:
                continue
            for dirpath, dirnames, _filenames in os.walk(root_path, topdown=False, onerror=lambda _e: None):
                for dirname in dirnames:
                    try:
                        os.rmdir(os.path.join(dirpath, dirname))
                    except OSError:
                        pass
    message = f"{deleted} fichier(s) supprimé(s)."
    if skipped:
        message += f" {skipped} fichier(s) verrouillé(s) ou inaccessibles ignorés."
    return {
        "id": target["id"],
        "ok": True,
        "freed_mb": round(freed / 2**20, 1),
        "message": message,
    }


def clean(ids: list[str]) -> list[dict]:
    """Nettoie les cibles demandées, fichier par fichier, sans jamais lever d'exception."""
    targets_by_id = {t["id"]: t for t in _targets()}
    results: list[dict] = []
    for target_id in ids:
        target = targets_by_id.get(target_id)
        if target is None:
            results.append(
                {"id": target_id, "ok": False, "freed_mb": 0.0, "message": f"Cible inconnue : {target_id}"}
            )
            continue
        try:
            if target.get("special") == "recycle_bin":
                results.append(_clean_recycle_bin(target))
            else:
                results.append(_clean_target(target))
        except Exception as exc:  # garde-fou : jamais d'exception vers l'appelant
            results.append(
                {"id": target_id, "ok": False, "freed_mb": 0.0, "message": f"Erreur inattendue : {exc}"}
            )
    return results
