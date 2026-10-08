"""Détection des jeux installés : Steam (parser VDF maison) et chemins typiques."""

from __future__ import annotations

from pathlib import Path

import psutil

from ...paths import is_windows
from .catalog import GAMES

# ---------------------------------------------------------------------------
# Parser VDF/KeyValues Valve minimal et tolérant (libraryfolders.vdf,
# appmanifest_*.acf, cs2_video.txt). Aucune dépendance externe.
# ---------------------------------------------------------------------------

_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def _tokenize_vdf(text: str) -> list[object]:
    """Découpe un texte KeyValues en tokens : '{', '}' ou ('str', valeur)."""
    tokens: list[object] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c in "{}":
            tokens.append(c)
            i += 1
        elif c == '"':
            i += 1
            buf: list[str] = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    buf.append(_ESCAPES.get(text[i + 1], text[i + 1]))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            i += 1  # guillemet fermant (ou fin de texte : toléré)
            tokens.append(("str", "".join(buf)))
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n{}"':
                j += 1
            tokens.append(("str", text[i:j]))
            i = j
    return tokens


def parse_vdf(text: str) -> dict:
    """Parse tolérant d'un document KeyValues Valve en dict imbriqué.

    Les blocs mal fermés ou tokens orphelins sont ignorés plutôt que de lever.
    """
    tokens = _tokenize_vdf(text)
    pos = 0

    def _block() -> dict:
        nonlocal pos
        out: dict = {}
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "}":
                pos += 1
                return out
            if tok == "{":  # bloc sans clé : consommé et ignoré
                pos += 1
                _block()
                continue
            key = tok[1]  # type: ignore[index]
            pos += 1
            if pos >= len(tokens):
                out[key] = ""
                break
            nxt = tokens[pos]
            if nxt == "{":
                pos += 1
                out[key] = _block()
            elif nxt == "}":
                out[key] = ""  # clé sans valeur avant fermeture : toléré
            else:
                out[key] = nxt[1]  # type: ignore[index]
                pos += 1
        return out

    try:
        return _block()
    except Exception:
        return {}


def _ci_get(data: dict, key: str) -> object | None:
    """Lecture insensible à la casse dans un dict KeyValues."""
    if not isinstance(data, dict):
        return None
    for k, v in data.items():
        if isinstance(k, str) and k.lower() == key.lower():
            return v
    return None


# ---------------------------------------------------------------------------
# Steam
# ---------------------------------------------------------------------------


def find_steam_root() -> Path | None:
    """Localise le dossier d'installation de Steam, ou None."""
    candidates: list[Path] = []
    if is_windows():
        try:
            import winreg  # import tardif : module Windows uniquement

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                value, _ = winreg.QueryValueEx(key, "SteamPath")
                if isinstance(value, str) and value.strip():
                    candidates.append(Path(value))
        except Exception:
            pass
        for root in _drive_roots():
            candidates.append(root / "Program Files (x86)" / "Steam")
            candidates.append(root / "Program Files" / "Steam")
            candidates.append(root / "Steam")
    else:
        home = Path.home()
        candidates.extend(
            [
                home / ".steam" / "steam",
                home / ".local" / "share" / "Steam",
                home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
            ]
        )
    for cand in candidates:
        try:
            if cand.is_dir():
                return cand
        except OSError:
            continue
    return None


def steam_libraries() -> list[Path]:
    """Liste les racines de bibliothèques Steam (via libraryfolders.vdf)."""
    root = find_steam_root()
    if root is None:
        return []
    libs: list[Path] = [root]
    vdf_path = root / "steamapps" / "libraryfolders.vdf"
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    if text:
        data = parse_vdf(text)
        folders = _ci_get(data, "libraryfolders")
        if not isinstance(folders, dict):
            folders = data
        for key, value in folders.items():
            if isinstance(value, dict):
                # Format récent : "0" { "path" "C:\\..." ... }
                path_val = _ci_get(value, "path")
                if isinstance(path_val, str) and path_val.strip():
                    libs.append(Path(path_val))
            elif isinstance(value, str) and str(key).isdigit() and value.strip():
                # Ancien format : "1" "D:\\SteamLibrary"
                libs.append(Path(value))
    out: list[Path] = []
    seen: set[str] = set()
    for lib in libs:
        try:
            if not lib.is_dir():
                continue
        except OSError:
            continue
        marker = str(lib).lower().rstrip("/\\")
        if marker not in seen:
            seen.add(marker)
            out.append(lib)
    return out


def steam_game_path(appid: int) -> Path | None:
    """Chemin d'installation d'un jeu Steam via son appmanifest, ou None."""
    for lib in steam_libraries():
        manifest = lib / "steamapps" / f"appmanifest_{appid}.acf"
        try:
            if not manifest.is_file():
                continue
            text = manifest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        data = parse_vdf(text)
        state = _ci_get(data, "AppState")
        if not isinstance(state, dict):
            state = data
        installdir = _ci_get(state, "installdir")
        if isinstance(installdir, str) and installdir.strip():
            game_dir = lib / "steamapps" / "common" / installdir
            try:
                if game_dir.is_dir():
                    return game_dir
            except OSError:
                continue
    return None


# ---------------------------------------------------------------------------
# Détection hors Steam : chemins typiques sur les lecteurs existants
# ---------------------------------------------------------------------------


def _drive_roots() -> list[Path]:
    """Racines des lecteurs/partitions existants (psutil), sans jamais lever."""
    roots: list[Path] = []
    try:
        for part in psutil.disk_partitions(all=False):
            mount = part.mountpoint
            if mount:
                roots.append(Path(mount))
    except Exception:
        pass
    if not roots:
        roots.append(Path("C:\\") if is_windows() else Path("/"))
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        marker = str(root).lower()
        if marker not in seen:
            seen.add(marker)
            out.append(root)
    return out


def _candidate_bases() -> list[Path]:
    """Dossiers de base sous lesquels tester les install_hints."""
    bases: list[Path] = []
    for root in _drive_roots():
        bases.append(root)
        bases.append(root / "Program Files")
        bases.append(root / "Program Files (x86)")
        bases.append(root / "Games")
    return bases


def detect_games() -> list[dict]:
    """Détecte chaque jeu du catalogue ; jamais d'exception.

    Retour : catalogue enrichi de "installed", "install_path", "detected_via".
    """
    try:
        bases = _candidate_bases()
    except Exception:
        bases = []
    results: list[dict] = []
    for game in GAMES:
        entry = dict(game)
        installed = False
        install_path: str | None = None
        detected_via: str | None = None

        appid = game.get("steam_appid")
        if appid is not None:
            try:
                path = steam_game_path(int(appid))
            except Exception:
                path = None
            if path is not None:
                installed, install_path, detected_via = True, str(path), "steam"

        if not installed:
            for base in bases:
                for hint in game.get("install_hints", []):
                    try:
                        parts = [p for p in str(hint).replace("\\", "/").split("/") if p]
                        candidate = base.joinpath(*parts)
                        if candidate.is_dir():
                            installed = True
                            install_path = str(candidate)
                            detected_via = "path"
                            break
                    except Exception:
                        continue
                if installed:
                    break

        entry["installed"] = installed
        entry["install_path"] = install_path
        entry["detected_via"] = detected_via
        results.append(entry)
    return results
