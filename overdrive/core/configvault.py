"""Coffre de configurations de jeux : détection, sauvegarde zip et restauration.

Les sauvegardes sont des archives zip écrites dans ``data_dir()/vault/``
(``sauvegarde-AAAAMMJJ-HHMMSS.zip``), organisées par jeu
(``<game_id>/<n° de racine>/<chemin relatif>``) avec un ``manifest.json``
embarqué qui mémorise les racines d'origine pour la restauration.

Détection par variables d'environnement et outils maison (Steam via
``overdrive.core.games.detect``) : sous Linux sans ces chemins, tout est
proprement ``found=False``, sans exception. Les liens symboliques ne sont
jamais suivis et les fichiers de plus de 50 Mo sont ignorés.
"""

from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from ..paths import data_dir
from .games.detect import detect_games, find_steam_root

_MAX_FILE_BYTES = 50 * 1024 * 1024  # fichiers > 50 Mo ignorés
_BACKUP_PREFIX = "sauvegarde-"
_MANIFEST_NAME = "manifest.json"


def _vault_dir() -> Path:
    """Dossier des sauvegardes, créé si absent."""
    vault = data_dir() / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    return vault


def _userprofile() -> Path:
    """Profil utilisateur Windows (%USERPROFILE%), ou home en repli."""
    value = os.environ.get("USERPROFILE")
    return Path(value) if value else Path.home()


def _steam_userdata_cfg_dirs(appid: int, subpath: tuple[str, ...]) -> list[Path]:
    """Dossiers ``userdata/<id>/<appid>/<subpath>`` existants de chaque profil Steam."""
    dirs: list[Path] = []
    try:
        steam_root = find_steam_root()
        if steam_root is None:
            return dirs
        userdata = steam_root / "userdata"
        for entry in sorted(p for p in userdata.iterdir() if p.is_dir()):
            candidate = entry / str(appid)
            for part in subpath:
                candidate = candidate / part
            if candidate.is_dir():
                dirs.append(candidate)
    except OSError:
        pass
    return dirs


def _league_config_paths() -> list[Path]:
    """game.cfg et PersistedSettings.json du dossier Config de LoL (via detect)."""
    paths: list[Path] = []
    try:
        for game in detect_games():
            if game.get("id") != "league_of_legends":
                continue
            install = game.get("install_path")
            if not install:
                break
            config = Path(install) / "Config"
            for name in ("game.cfg", "PersistedSettings.json"):
                candidate = config / name
                if candidate.is_file():
                    paths.append(candidate)
            break
    except Exception:
        return []
    return paths


def _path_size_bytes(path: Path) -> int:
    """Taille totale des fichiers réguliers sous ce chemin (liens non suivis)."""
    total = 0
    try:
        if path.is_symlink():
            return 0
        if path.is_file():
            return path.stat().st_size
        for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
            for name in filenames:
                file = Path(dirpath) / name
                try:
                    if not file.is_symlink() and file.is_file():
                        total += file.stat().st_size
                except OSError:
                    continue
    except OSError:
        return total
    return total


def vault_targets() -> list[dict]:
    """Jeux dont la configuration est sauvegardable, avec détection.

    Retour : [{"game_id", "name", "paths": [str], "found": bool,
    "size_mb": float}]. Jamais d'exception ; sous Linux sans ces chemins,
    tout est found=False.
    """
    targets: list[dict] = []

    def _add(game_id: str, name: str, paths: list[Path]) -> None:
        existing: list[Path] = []
        for path in paths:
            try:
                if path.exists() and not path.is_symlink():
                    existing.append(path)
            except OSError:
                continue
        size = sum(_path_size_bytes(p) for p in existing)
        targets.append(
            {
                "game_id": game_id,
                "name": name,
                "paths": [str(p) for p in existing],
                "found": bool(existing),
                "size_mb": round(size / (1024 * 1024), 2),
            }
        )

    try:
        _add("cs2", "Counter-Strike 2",
             _steam_userdata_cfg_dirs(730, ("local", "cfg")))
    except Exception:
        targets.append({"game_id": "cs2", "name": "Counter-Strike 2",
                        "paths": [], "found": False, "size_mb": 0.0})

    try:
        local_appdata = os.environ.get("LOCALAPPDATA")
        valorant_paths = (
            [Path(local_appdata) / "VALORANT" / "Saved" / "Config"]
            if local_appdata else []
        )
        _add("valorant", "Valorant", valorant_paths)
    except Exception:
        targets.append({"game_id": "valorant", "name": "Valorant",
                        "paths": [], "found": False, "size_mb": 0.0})

    try:
        _add("league_of_legends", "League of Legends", _league_config_paths())
    except Exception:
        targets.append({"game_id": "league_of_legends", "name": "League of Legends",
                        "paths": [], "found": False, "size_mb": 0.0})

    try:
        rl_config = (_userprofile() / "Documents" / "My Games"
                     / "Rocket League" / "TAGame" / "Config")
        _add("rocket_league", "Rocket League", [rl_config])
    except Exception:
        targets.append({"game_id": "rocket_league", "name": "Rocket League",
                        "paths": [], "found": False, "size_mb": 0.0})

    try:
        _add("dota2", "Dota 2",
             _steam_userdata_cfg_dirs(570, ("remote", "cfg")))
    except Exception:
        targets.append({"game_id": "dota2", "name": "Dota 2",
                        "paths": [], "found": False, "size_mb": 0.0})

    return targets


def _collect_files(root: Path) -> list[tuple[Path, str]]:
    """(fichier, chemin relatif POSIX) sous une racine ; liens et > 50 Mo exclus."""
    collected: list[tuple[Path, str]] = []
    try:
        if root.is_symlink():
            return collected
        if root.is_file():
            if root.stat().st_size <= _MAX_FILE_BYTES:
                collected.append((root, root.name))
            return collected
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Ne pas descendre dans les dossiers qui sont des liens symboliques.
            dirnames[:] = [d for d in dirnames
                           if not (Path(dirpath) / d).is_symlink()]
            for name in sorted(filenames):
                file = Path(dirpath) / name
                try:
                    if file.is_symlink() or not file.is_file():
                        continue
                    if file.stat().st_size > _MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                relative = file.relative_to(root).as_posix()
                collected.append((file, relative))
    except OSError:
        pass
    return collected


def _new_backup_path(vault: Path) -> Path:
    """Chemin de sauvegarde horodaté, sans collision (suffixe -2, -3, …)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = vault / f"{_BACKUP_PREFIX}{stamp}.zip"
    counter = 2
    while path.exists():
        path = vault / f"{_BACKUP_PREFIX}{stamp}-{counter}.zip"
        counter += 1
    return path


def backup(game_ids: list[str] | None = None) -> dict:
    """Sauvegarde les configurations des jeux détectés dans un zip du coffre.

    Retour : {"ok", "path", "games": [ids], "files": int, "size_mb", "message"}.
    Jamais d'exception.
    """
    try:
        wanted = None if game_ids is None else {str(g) for g in game_ids}
        selected = [
            t for t in vault_targets()
            if t["found"] and (wanted is None or t["game_id"] in wanted)
        ]
        # (fichier, nom d'archive) et manifeste des racines par jeu.
        entries: list[tuple[Path, str]] = []
        manifest_games: dict[str, dict] = {}
        for target in selected:
            roots = [Path(p) for p in target["paths"]]
            game_files: list[tuple[Path, str]] = []
            for index, root in enumerate(roots):
                for file, relative in _collect_files(root):
                    game_files.append(
                        (file, f"{target['game_id']}/{index}/{relative}"))
            if game_files:
                entries.extend(game_files)
                manifest_games[target["game_id"]] = {
                    "roots": [str(r) for r in roots]
                }
        if not entries:
            return {"ok": False, "path": None, "games": [], "files": 0,
                    "size_mb": 0.0,
                    "message": "Aucun fichier de configuration à sauvegarder "
                               "(aucun jeu détecté ou dossiers vides)."}

        vault = _vault_dir()
        path = _new_backup_path(vault)
        manifest = {
            "version": 1,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "games": manifest_games,
            "files": len(entries),
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file, arcname in entries:
                try:
                    archive.write(file, arcname)
                except OSError:
                    continue
            archive.writestr(_MANIFEST_NAME,
                             json.dumps(manifest, ensure_ascii=False, indent=2))
        size_mb = round(path.stat().st_size / (1024 * 1024), 2)
        games = sorted(manifest_games)
        return {"ok": True, "path": str(path), "games": games,
                "files": len(entries), "size_mb": size_mb,
                "message": f"Sauvegarde créée : {path.name} "
                           f"({len(entries)} fichiers, {', '.join(games)})."}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "path": None, "games": [], "files": 0,
                "size_mb": 0.0, "message": f"Échec de la sauvegarde : {exc}"}


def _read_manifest(path: Path) -> dict | None:
    """manifest.json d'une archive du coffre, ou None si illisible."""
    try:
        with zipfile.ZipFile(path, "r") as archive:
            with archive.open(_MANIFEST_NAME) as handle:
                data = json.loads(handle.read().decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def list_backups() -> list[dict]:
    """Sauvegardes du coffre, la plus récente en premier.

    Retour : [{"id", "ts", "size_mb", "games": [...]}]. Jamais d'exception.
    """
    backups: list[dict] = []
    try:
        vault = _vault_dir()
        zips = sorted(vault.glob("*.zip"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        for path in zips:
            manifest = _read_manifest(path) or {}
            games = manifest.get("games")
            ts = manifest.get("ts")
            if not isinstance(ts, str):
                ts = datetime.fromtimestamp(
                    path.stat().st_mtime).isoformat(timespec="seconds")
            backups.append(
                {
                    "id": path.name,
                    "ts": ts,
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                    "games": sorted(games) if isinstance(games, dict) else [],
                }
            )
    except Exception:
        return backups
    return backups


def _resolve_backup_id(backup_id: str) -> Path | None:
    """Valide un identifiant de sauvegarde : nom de fichier exact du coffre.

    Refuse tout séparateur de chemin, « .. » et tout nom absent du coffre
    (aucune traversée de répertoire possible).
    """
    try:
        if not isinstance(backup_id, str) or not backup_id:
            return None
        if backup_id != Path(backup_id).name:
            return None
        if "/" in backup_id or "\\" in backup_id or ".." in backup_id:
            return None
        if not backup_id.endswith(".zip"):
            return None
        path = _vault_dir() / backup_id
        return path if path.is_file() else None
    except Exception:
        return None


def _safe_relative(relative: str) -> PurePosixPath | None:
    """Chemin relatif d'archive validé (ni absolu, ni « .. », ni lecteur)."""
    pure = PurePosixPath(relative)
    if pure.is_absolute():
        return None
    for part in pure.parts:
        if part in ("..", "") or ":" in part or "\\" in part:
            return None
    return pure


def restore(backup_id: str, game_ids: list[str] | None = None) -> dict:
    """Restaure les fichiers d'une sauvegarde vers leurs emplacements d'origine.

    Une sauvegarde de sécurité automatique des jeux concernés est tentée
    avant toute écriture. Retour : {"ok", "message", "restored": int}.
    Jamais d'exception.
    """
    try:
        path = _resolve_backup_id(backup_id)
        if path is None:
            return {"ok": False, "restored": 0,
                    "message": "Identifiant de sauvegarde invalide ou inconnu "
                               "(nom de fichier exact du coffre attendu)."}
        manifest = _read_manifest(path)
        games = manifest.get("games") if manifest else None
        if not isinstance(games, dict) or not games:
            return {"ok": False, "restored": 0,
                    "message": "Archive illisible ou sans manifeste : "
                               "restauration refusée."}
        wanted = None if game_ids is None else {str(g) for g in game_ids}
        selected = {gid: info for gid, info in games.items()
                    if wanted is None or gid in wanted}
        if not selected:
            return {"ok": False, "restored": 0,
                    "message": "Aucun des jeux demandés n'est présent dans "
                               "cette sauvegarde."}

        # Sauvegarde de sécurité avant écrasement (best effort : des dossiers
        # déjà vides ne produisent pas d'archive).
        safety = backup(sorted(selected))
        safety_note = (
            f" Sauvegarde de sécurité : {Path(safety['path']).name}."
            if safety.get("ok") and safety.get("path")
            else " Aucune sauvegarde de sécurité créée (rien à sauvegarder)."
        )

        restored = 0
        with zipfile.ZipFile(path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir() or info.filename == _MANIFEST_NAME:
                    continue
                parts = info.filename.split("/", 2)
                if len(parts) != 3:
                    continue
                gid, index_text, relative = parts
                if gid not in selected or not index_text.isdigit():
                    continue
                roots = selected[gid].get("roots")
                index = int(index_text)
                if not isinstance(roots, list) or index >= len(roots):
                    continue
                pure = _safe_relative(relative)
                if pure is None:
                    continue
                target = Path(roots[index]).joinpath(*pure.parts)
                try:
                    if target.is_symlink():
                        continue  # jamais d'écriture à travers un lien
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source:
                        target.write_bytes(source.read())
                    restored += 1
                except OSError:
                    continue
        return {"ok": restored > 0, "restored": restored,
                "message": f"{restored} fichier(s) restauré(s) depuis "
                           f"{backup_id}.{safety_note}"}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "restored": 0,
                "message": f"Échec de la restauration : {exc}"}


def delete_backup(backup_id: str) -> dict:
    """Supprime une sauvegarde du coffre. Retour : {"ok", "message"}."""
    try:
        path = _resolve_backup_id(backup_id)
        if path is None:
            return {"ok": False,
                    "message": "Identifiant de sauvegarde invalide ou inconnu."}
        path.unlink()
        return {"ok": True, "message": f"Sauvegarde {backup_id} supprimée."}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "message": f"Échec de la suppression : {exc}"}
