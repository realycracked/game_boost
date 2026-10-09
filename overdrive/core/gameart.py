"""Visuels des jeux (jaquettes, bannières, logos) téléchargés à l'exécution.

Les images appartiennent à leurs éditeurs : elles ne sont JAMAIS livrées dans
le dépôt ni dans l'exécutable. Elles sont téléchargées à la demande depuis
les CDN officiels (Steam, Riot Data Dragon) ou des API communautaires
(valorant-api.com, fortnite-api.com), puis mises en cache sous
``data_dir()/art/<game_id>/<kind>.<ext>`` (voir THIRD_PARTY.md).

Types d'images (``KINDS``) :

- ``cover``    : jaquette portrait (2:3, ex. Steam ``library_600x900.jpg``) ;
- ``header``   : bannière paysage (ex. Steam ``header.jpg`` 460×215) ;
- ``hero``     : visuel très large pour les héros/bandeaux ;
- ``logo``     : logo détouré (PNG transparent) ;
- ``portrait`` : personnage détouré (PNG transparent, composé côté front).

Sécurité : l'identifiant de jeu est validé contre le catalogue, le type contre
``KINDS`` ; aucune URL ne vient de l'utilisateur (pas de SSRF) — les URL
téléchargées sont construites ici ou lues dans les API connues, puis
filtrées par une liste blanche d'hôtes HTTPS (redirections comprises). Les
noms de fichiers sont construits côté serveur et le contenu est vérifié par
ses octets magiques (PNG, JPEG, WebP uniquement).

Aucune fonction publique ne lève d'exception : un échec renvoie ``None`` (ou
un dict ``ok: False``) et est simplement journalisé.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Any, Iterable

from ..paths import data_dir
from .games.catalog import GAMES

log = logging.getLogger("overdrive.gameart")

#: Types d'images exposés.
KINDS: tuple[str, ...] = ("cover", "header", "hero", "logo", "portrait")

#: Délai réseau par opération (connexion, lecture...), en secondes.
_TIMEOUT = 8.0
#: Durée totale maximale d'un téléchargement (anti connexion au goutte-à-goutte).
_TOTAL_DEADLINE = 45.0
#: Taille maximale d'une image téléchargée.
_MAX_DOWNLOAD = 15 * 1024 * 1024
#: Taille maximale d'une réponse JSON d'API communautaire.
_MAX_JSON = 4 * 1024 * 1024
#: Taille maximale d'une image personnalisée fournie par l'utilisateur.
MAX_CUSTOM_BYTES = 8 * 1024 * 1024
#: Longueur maximale de la partie base64 d'une data URL (8 Mo décodés).
_MAX_B64_CHARS = ((MAX_CUSTOM_BYTES + 2) // 3) * 4
#: Longueur maximale d'une data URL complète (en-tête ``data:...`` compris).
MAX_DATA_URL_CHARS = _MAX_B64_CHARS + 64

_DAY = 24 * 3600
#: Durée de vie du cache selon la source (secondes).
_TTL = {"steam": 30 * _DAY, "riot": 30 * _DAY, "community": 7 * _DAY}
#: Délai avant de retenter un téléchargement échoué (évite de bloquer
#: l'interface 8 s par image quand la machine est hors ligne).
_RETRY_AFTER = 15 * 60

#: Extensions reconnues → type MIME servi.
_MIME = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

#: Hôtes autorisés pour TOUT téléchargement (suffixes, HTTPS uniquement).
_ALLOWED_HOST_SUFFIXES = (
    "steamstatic.com",       # CDN officiel Steam (Akamai, Cloudflare)
    "leagueoflegends.com",   # Data Dragon officiel Riot
    "valorant-api.com",      # API communautaire Valorant (+ media.)
    "fortnite-api.com",      # API communautaire Fortnite (+ cdn.)
    "epicgames.com",         # images d'actualité Fortnite (CDN Epic)
    "unrealengine.com",      # ancien CDN des actualités Fortnite
)

# ------------------------------------------------------------------ sources

#: Fichiers Steam par type d'image, du plus net au plus sûr. Sur
#: store_item_assets, ``library_600x900.jpg`` mesure en réalité 300×450 et
#: ``library_hero.jpg`` 1920×620 : les variantes ``_2x`` (600×900 et
#: 3840×1240, 0,1 à 1,1 Mo) restent nettes en mise à l'échelle 150-200 %.
_STEAM_FILES = {
    "cover": ("library_600x900_2x.jpg", "library_600x900.jpg"),
    "header": ("header.jpg",),
    "hero": ("library_hero_2x.jpg", "library_hero.jpg"),
    "logo": ("logo.png",),
}
#: Jaquettes et héros Steam mis en cache avant le passage aux variantes 2x
#: (horodatage Unix) : considérés comme périmés, donc rafraîchis en tâche de
#: fond au prochain affichage (l'ancienne image reste servie en attendant).
_STEAM_2X_SINCE = 1791524568.0
_STEAM_2X_KINDS = ("cover", "hero")
#: CDN Steam : officiel puis repli Cloudflare.
_STEAM_URLS = (
    "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/{file}",
    "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/{file}",
)
#: App ID Steam des visuels. Warzone : 1962663 (« Call of Duty: Warzone »,
#: même valeur que le catalogue) plutôt que 1938090 (lanceur « Call of
#: Duty » générique, visuels Black Ops). Un jeu du catalogue absent d'ici
#: mais doté d'un ``steam_appid`` utilise automatiquement le CDN Steam.
_STEAM_APPIDS = {
    "cs2": 730,
    "apex_legends": 1172470,
    "r6_siege": 359550,
    "rocket_league": 252950,
    "pubg": 578080,
    "dota2": 570,
    "gta_online": 271590,
    "overwatch2": 2357570,
    "warzone": 1962663,
}

#: League of Legends : Data Dragon officiel Riot (champion emblématique fixe).
_LOL_CHAMPION = "Jinx"
_DDRAGON = "https://ddragon.leagueoflegends.com/cdn/img/champion/{folder}/{champ}_0.jpg"

#: Valorant (valorant-api.com, non officielle) : carte et agent fixes.
_VALORANT_MAP = "Ascent"
_VALORANT_AGENT = "Jett"
_VALORANT_MAPS_API = "https://valorant-api.com/v1/maps"
_VALORANT_AGENTS_API = "https://valorant-api.com/v1/agents?isPlayableCharacter=true"

#: Fortnite (fortnite-api.com, non officielle) : 1re actualité Battle Royale.
_FORTNITE_NEWS_API = "https://fortnite-api.com/v2/news/br"

#: Alias d'identifiants acceptés (forme courte → id du catalogue).
_ALIASES = {"lol": "league_of_legends"}

_CATALOG_IDS = {g.get("id") for g in GAMES if isinstance(g.get("id"), str)}

# Spécification d'un type d'image pour un jeu :
#   ("urls", (url, ...))       URL fixes essayées dans l'ordre ;
#   ("alias", "hero")          même image qu'un autre type ;
#   ("resolve", resolver, arg) URL lue dans une API communautaire ;
#   absent                     aucune image connue (repli côté front).


def _plan(game_id: str) -> dict[str, Any] | None:
    """Source et spécifications des types d'images d'un jeu (sans réseau)."""
    if game_id == "league_of_legends":
        return {
            "source": "riot",
            "kinds": {
                "hero": ("urls", (_DDRAGON.format(folder="splash", champ=_LOL_CHAMPION),)),
                "header": ("alias", "hero"),
                "cover": ("urls", (_DDRAGON.format(folder="loading", champ=_LOL_CHAMPION),)),
            },
        }
    if game_id == "valorant":
        return {
            "source": "community",
            "kinds": {
                "hero": ("resolve", "valorant_map", _VALORANT_MAP),
                "header": ("alias", "hero"),
                "portrait": ("resolve", "valorant_agent", _VALORANT_AGENT),
            },
        }
    if game_id == "fortnite":
        return {
            "source": "community",
            "kinds": {
                "hero": ("resolve", "fortnite_news", "br"),
                "header": ("alias", "hero"),
            },
        }
    appid = _STEAM_APPIDS.get(game_id)
    if appid is None:
        for game in GAMES:
            if game.get("id") == game_id:
                raw = game.get("steam_appid")
                if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
                    appid = raw
                break
    if appid is None:
        return None
    # CDN d'abord, fichiers ensuite : un 404 sur la variante 2x passe
    # directement à la variante 1x du même CDN.
    return {
        "source": "steam",
        "kinds": {
            kind: ("urls", tuple(u.format(appid=appid, file=name) for u in _STEAM_URLS for name in names))
            for kind, names in _STEAM_FILES.items()
        },
    }


def _canon(game_id: Any) -> str | None:
    """Identifiant du catalogue validé (alias résolus), sinon None."""
    if not isinstance(game_id, str):
        return None
    gid = _ALIASES.get(game_id, game_id)
    return gid if gid in _CATALOG_IDS else None


def _valid_kind(kind: Any) -> bool:
    return isinstance(kind, str) and kind in KINDS


# ----------------------------------------------------------------- fichiers

def _art_root() -> Path:
    return data_dir() / "art"


def _cache_dir(game_id: str) -> Path:
    return _art_root() / game_id


def _custom_dir(game_id: str) -> Path:
    return _art_root() / "custom" / game_id


def _find(directory: Path, kind: str) -> Path | None:
    """Fichier ``<kind>.<ext>`` existant (le plus récent si plusieurs)."""
    best: Path | None = None
    best_mtime = -1.0
    for ext in _MIME:
        path = directory / f"{kind}{ext}"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if path.is_file() and mtime > best_mtime:
            best, best_mtime = path, mtime
    return best


def sniff_image(data: bytes) -> str | None:
    """Extension d'après les octets magiques (PNG, JPEG, WebP), sinon None."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 12:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def media_type(path: Path) -> str:
    """Type MIME d'une image servie (d'après son extension)."""
    return _MIME.get(path.suffix.lower(), "application/octet-stream")


def _atomic_write(directory: Path, kind: str, data: bytes, ext: str) -> Path | None:
    """Écrit ``<kind><ext>`` atomiquement et supprime les autres extensions."""
    target = directory / f"{kind}{ext}"
    tmp = directory / f".{kind}{ext}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, target)
    except OSError as exc:
        # Sous Windows, remplacer un fichier en cours d'envoi peut échouer :
        # l'ancienne version reste en place.
        log.info("Écriture de %s impossible : %s", target, exc)
        try:
            tmp.unlink()
        except OSError:
            pass
        return None
    for other in _MIME:
        if other != ext:
            try:
                (directory / f"{kind}{other}").unlink()
            except OSError:
                pass
    return target


def _rev(path: Path | None) -> int:
    """Révision d'un fichier (mtime en ms) pour invalider le cache navigateur."""
    if path is None:
        return 0
    try:
        return int(path.stat().st_mtime_ns // 1_000_000)
    except OSError:
        return 0


# ------------------------------------------------------------------- réseau

class _BlockedURL(Exception):
    """URL hors liste blanche (schéma non HTTPS ou hôte inconnu)."""


class _SoftError(RuntimeError):
    """Réponse refusée (statut HTTP, taille) : l'hôte, lui, répond."""


def _host_allowed(host: str | None) -> bool:
    host = (host or "").lower().rstrip(".")
    return any(host == s or host.endswith("." + s) for s in _ALLOWED_HOST_SUFFIXES)


def _url_allowed(url: Any) -> bool:
    """Vrai pour une URL HTTPS vers un hôte de la liste blanche."""
    if not isinstance(url, str) or len(url) > 2048:
        return False
    match = re.match(r"^https://([^/?#:@]+)(?::443)?(?:[/?#]|$)", url, re.IGNORECASE)
    return bool(match) and _host_allowed(match.group(1))


_CLIENT_LOCK = threading.Lock()
_client_obj: Any = None


def _check_request(request: Any) -> None:
    """Crochet httpx : refuse toute requête (redirections comprises) hors liste."""
    if request.url.scheme != "https" or not _host_allowed(request.url.host):
        raise _BlockedURL(str(request.url))


def _client() -> Any:
    """Client httpx partagé (créé à la demande, import tardif)."""
    global _client_obj
    with _CLIENT_LOCK:
        if _client_obj is None:
            import httpx  # noqa: PLC0415 — import tardif : le module charge sans httpx

            try:
                from .. import APP_NAME, VERSION  # noqa: PLC0415
            except Exception:  # noqa: BLE001
                APP_NAME, VERSION = "Overdrive", "?"
            _client_obj = httpx.Client(
                timeout=_TIMEOUT,
                follow_redirects=True,
                max_redirects=3,
                headers={"User-Agent": f"{APP_NAME}/{VERSION} (game art)"},
                event_hooks={"request": [_check_request]},
            )
        return _client_obj


def _fetch(url: str, limit: int) -> bytes:
    """Télécharge ``url`` (HTTP 200 exigé, ``limit`` octets max). Peut lever."""
    if not _url_allowed(url):
        raise _BlockedURL(url)
    deadline = time.monotonic() + _TOTAL_DEADLINE
    with _client().stream("GET", url) as response:
        if response.status_code != 200:
            raise _SoftError(f"HTTP {response.status_code}")
        try:
            declared = int(response.headers.get("content-length") or 0)
        except ValueError:
            declared = 0
        if declared > limit:
            raise _SoftError("réponse trop volumineuse")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > limit:
                raise _SoftError("réponse trop volumineuse")
            if time.monotonic() > deadline:
                raise RuntimeError("téléchargement trop lent")
            chunks.append(chunk)
    return b"".join(chunks)


def _fetch_json(url: str) -> Any:
    return json.loads(_fetch(url, _MAX_JSON).decode("utf-8"))


def _url_host(url: str) -> str:
    match = re.match(r"^https://([^/?#:@]+)", url or "", re.IGNORECASE)
    return match.group(1).lower() if match else ""


def _download_image(urls: Iterable[str]) -> tuple[bytes, str] | None:
    """Première image valide parmi ``urls`` : (octets, extension) ou None.

    Un hôte qui ne répond pas (délai, connexion refusée, téléchargement trop
    lent) n'est pas réinterrogé pour les URL suivantes : réseau filtré ou
    hors ligne, l'échec arrive au bout d'un délai par CDN, pas par fichier.
    """
    dead: set[str] = set()
    for url in urls:
        host = _url_host(url)
        if host in dead:
            continue
        try:
            data = _fetch(url, _MAX_DOWNLOAD)
        except (_SoftError, _BlockedURL) as exc:
            log.info("Visuel indisponible (%s) : %s", url, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — réseau : jamais d'exception
            log.info("Visuel indisponible (%s) : %s", url, exc)
            dead.add(host)
            continue
        ext = sniff_image(data)
        if ext:
            return data, ext
        log.info("Contenu non reconnu comme image : %s", url)
    return None


# ------------------------------------------------- URL des API communautaires

def _resolve_valorant_map(name: str) -> str | None:
    payload = _fetch_json(_VALORANT_MAPS_API)
    for item in payload.get("data") or []:
        if isinstance(item, dict) and str(item.get("displayName", "")).lower() == name.lower():
            return item.get("splash")
    return None


def _resolve_valorant_agent(name: str) -> str | None:
    payload = _fetch_json(_VALORANT_AGENTS_API)
    for item in payload.get("data") or []:
        if isinstance(item, dict) and str(item.get("displayName", "")).lower() == name.lower():
            return item.get("fullPortrait") or item.get("fullPortraitV2")
    return None


def _resolve_fortnite_news(_arg: str) -> str | None:
    data = (_fetch_json(_FORTNITE_NEWS_API) or {}).get("data") or {}
    for motd in data.get("motds") or []:
        if isinstance(motd, dict):
            url = motd.get("image") or motd.get("tileImage")
            if url:
                return url
    return data.get("image")


_RESOLVERS = {
    "valorant_map": _resolve_valorant_map,
    "valorant_agent": _resolve_valorant_agent,
    "fortnite_news": _resolve_fortnite_news,
}

#: Fichier JSON des URL résolues : {"<resolver>:<arg>": {"url", "ts"}}.
_RESOLVED_FILE = "resolved.json"
_RESOLVE_LOCK = threading.Lock()


def _load_resolved() -> dict:
    try:
        data = json.loads((_art_root() / _RESOLVED_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 — fichier absent ou corrompu
        return {}


def _save_resolved(data: dict) -> None:
    root = _art_root()
    tmp = root / f".{_RESOLVED_FILE}.{os.getpid()}.tmp"
    try:
        root.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(tmp, root / _RESOLVED_FILE)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


_RESOLVE_KEY_LOCKS: dict[str, threading.Lock] = {}


def _resolved_entry(key: str, ttl: float) -> tuple[str | None, bool]:
    """(URL en cache pour ``key``, encore valide ?) — lecture sous verrou court."""
    with _RESOLVE_LOCK:
        cache = _load_resolved()
    entry = cache.get(key) if isinstance(cache.get(key), dict) else None
    url = entry.get("url") if entry else None
    try:
        fresh = entry is not None and (time.time() - float(entry.get("ts", 0))) < ttl
    except (TypeError, ValueError):
        fresh = False
    return (url if _url_allowed(url) else None), fresh


def _resolve(resolver: str, arg: str, ttl: float) -> str | None:
    """URL d'image lue dans une API (cache JSON ``ttl``), sinon None.

    L'appel réseau se fait HORS du verrou global du fichier JSON (un verrou
    par clé évite seulement deux appels simultanés à la même API) : une API
    lente ne bloque ni les autres jeux ni la lecture du cache.
    """
    key = f"{resolver}:{arg}"
    cached_url, fresh = _resolved_entry(key, ttl)
    if fresh and cached_url:
        return cached_url
    with _RESOLVE_LOCK:
        key_lock = _RESOLVE_KEY_LOCKS.setdefault(key, threading.Lock())
    with key_lock:
        # Un autre fil a peut-être résolu pendant l'attente du verrou.
        cached_url, fresh = _resolved_entry(key, ttl)
        if fresh and cached_url:
            return cached_url
        url = None
        func = _RESOLVERS.get(resolver)
        if func is not None:
            try:
                url = func(arg)
            except Exception as exc:  # noqa: BLE001 — API indisponible
                log.info("API de visuels indisponible (%s) : %s", key, exc)
        if _url_allowed(url):
            with _RESOLVE_LOCK:
                cache = _load_resolved()
                cache[key] = {"url": url, "ts": time.time()}
                _save_resolved(cache)
            return url
        # Repli : ancienne URL connue (même expirée) plutôt que rien.
        return cached_url


# ------------------------------------------------------------- API publique

_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[tuple[str, str], threading.Lock] = {}
#: Échecs récents : (jeu, type) → instant monotone de l'échec.
_FAILED: dict[tuple[str, str], float] = {}


def _lock_for(game_id: str, kind: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault((game_id, kind), threading.Lock())


def _is_fresh(path: Path, ttl: float) -> bool:
    try:
        return (time.time() - path.stat().st_mtime) < ttl
    except OSError:
        return False


def _is_current(path: Path, ttl: float, source: str, kind: str) -> bool:
    """Image du cache encore valide (TTL, et variante 2x pour Steam)."""
    if not _is_fresh(path, ttl):
        return False
    if source == "steam" and kind in _STEAM_2X_KINDS:
        try:
            return path.stat().st_mtime >= _STEAM_2X_SINCE
        except OSError:
            return False
    return True


def _available(plan: dict | None, kind: str, depth: int = 0) -> bool:
    """Une source est-elle connue pour ce type (alias suivis) ?"""
    if not plan or depth > 2:
        return False
    spec = plan["kinds"].get(kind)
    if spec is None:
        return False
    if spec[0] == "alias":
        return _available(plan, spec[1], depth + 1)
    return True


def _get(game_id: str, kind: str, depth: int = 0) -> Path | None:
    """Cœur de :func:`get_art` (identifiants déjà validés)."""
    custom = _find(_custom_dir(game_id), kind)
    if custom is not None:
        return custom
    plan = _plan(game_id)
    spec = plan["kinds"].get(kind) if plan else None
    if spec is None:
        return None
    if spec[0] == "alias":
        return _get(game_id, spec[1], depth + 1) if depth < 2 else None
    source = plan["source"]
    ttl = _TTL.get(source, 7 * _DAY)
    directory = _cache_dir(game_id)
    cached = _find(directory, kind)
    if cached is not None and _is_current(cached, ttl, source, kind):
        return cached
    key = (game_id, kind)
    with _lock_for(game_id, kind):
        # Un autre fil a peut-être téléchargé pendant l'attente du verrou.
        cached = _find(directory, kind)
        if cached is not None and _is_current(cached, ttl, source, kind):
            return cached
        failed_at = _FAILED.get(key)
        if failed_at is not None and (time.monotonic() - failed_at) < _RETRY_AFTER:
            return cached  # échec récent : image périmée ou None, sans réseau
        if spec[0] == "urls":
            urls: tuple[str, ...] = spec[1]
        else:  # "resolve"
            url = _resolve(spec[1], spec[2], ttl)
            urls = (url,) if url else ()
        result = _download_image(urls)
        if result is None:
            _FAILED[key] = time.monotonic()
            return cached  # repli : version périmée plutôt que rien
        written = _atomic_write(directory, kind, result[0], result[1])
        if written is None:
            _FAILED[key] = time.monotonic()
            return cached
        _FAILED.pop(key, None)
        return written


def get_art(game_id: str, kind: str) -> Path | None:
    """Chemin de l'image ``kind`` du jeu, téléchargée si besoin, sinon None.

    Ordre : image personnalisée, cache encore valide (30 j Steam/Riot, 7 j
    communautaire), téléchargement (verrou par jeu et type), image périmée
    du cache en dernier recours. Ne lève jamais d'exception.
    """
    try:
        gid = _canon(game_id)
        if gid is None or not _valid_kind(kind):
            return None
        return _get(gid, kind)
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec inattendu de get_art(%r, %r)", game_id, kind)
        return None


# ------------------------------------------- service HTTP sans attente réseau

#: Attente maximale (s) d'un téléchargement par la route GET quand rien n'est
#: en cache : au-delà, 404 immédiat et le téléchargement continue en fond.
SERVE_WAIT = 1.0
#: Fils de téléchargement de fond (à la demande de la route GET).
_BG_MAX_WORKERS = 3
_BG_GUARD = threading.Lock()
#: (jeu, type) en file → (événement de fin, instant monotone de mise en file).
_BG_PENDING: dict[tuple[str, str], tuple[threading.Event, float]] = {}
_BG_QUEUE: queue.Queue = queue.Queue()
_bg_workers = 0


def _bg_worker() -> None:
    """Télécharge les visuels demandés par la route GET (fil démon)."""
    global _bg_workers
    while True:
        try:
            key = _BG_QUEUE.get(timeout=20)
        except queue.Empty:
            with _BG_GUARD:
                if _BG_QUEUE.empty():
                    _bg_workers -= 1
                    return
            continue
        try:
            _get(key[0], key[1])
        except Exception:  # noqa: BLE001 — jamais d'exception
            log.exception("Échec du téléchargement de fond %r", key)
        finally:
            with _BG_GUARD:
                entry = _BG_PENDING.pop(key, None)
            if entry is not None:
                entry[0].set()


def _schedule(game_id: str, kind: str) -> tuple[threading.Event, float]:
    """Met (jeu, type) en file de téléchargement (dédoublonné) ; renvoie
    (événement signalé à la fin du téléchargement, instant de mise en file)."""
    global _bg_workers
    key = (game_id, kind)
    with _BG_GUARD:
        entry = _BG_PENDING.get(key)
        if entry is not None:
            return entry
        event = threading.Event()
        entry = (event, time.monotonic())
        _BG_PENDING[key] = entry
        _BG_QUEUE.put(key)
        if _bg_workers < _BG_MAX_WORKERS:
            _bg_workers += 1
            try:
                threading.Thread(target=_bg_worker, daemon=True, name="art-fetch").start()
            except Exception:  # noqa: BLE001 — fil impossible : rien ne bloque
                _bg_workers -= 1
                _BG_PENDING.pop(key, None)
                event.set()
    return entry


def _serve(game_id: str, kind: str, wait: float, depth: int = 0) -> Path | None:
    """Cœur de :func:`serve_art` (identifiants déjà validés)."""
    custom = _find(_custom_dir(game_id), kind)
    if custom is not None:
        return custom
    plan = _plan(game_id)
    spec = plan["kinds"].get(kind) if plan else None
    if spec is None:
        return None
    if spec[0] == "alias":
        return _serve(game_id, spec[1], wait, depth + 1) if depth < 2 else None
    source = plan["source"]
    directory = _cache_dir(game_id)
    cached = _find(directory, kind)
    if cached is not None:
        if not _is_current(cached, _TTL.get(source, 7 * _DAY), source, kind):
            _schedule(game_id, kind)   # rafraîchi en fond, l'ancienne est servie
        return cached
    failed_at = _FAILED.get((game_id, kind))
    if failed_at is not None and (time.monotonic() - failed_at) < _RETRY_AFTER:
        return None   # échec récent : 404 immédiat, sans réseau
    # Attente bornée depuis la MISE EN FILE : plusieurs requêtes pour la même
    # image n'attendent pas chacune une seconde de plus.
    event, queued_at = _schedule(game_id, kind)
    remaining = wait - (time.monotonic() - queued_at)
    if remaining > 0:
        event.wait(remaining)
    return _find(directory, kind)


def serve_art(game_id: str, kind: str, wait: float = SERVE_WAIT) -> Path | None:
    """Image à servir tout de suite, SANS jamais attendre le réseau longtemps.

    Pour la route HTTP : image personnalisée, sinon cache (même périmé : il
    est alors rafraîchi par un fil de fond), sinon téléchargement mis en file
    et attendu ``wait`` secondes au plus (1 s par défaut) avant de renvoyer
    None. Un CDN lent, un pare-feu ou un portail captif ne bloquent donc ni
    les autres appels de l'API ni l'interface. Ne lève jamais d'exception.
    """
    try:
        gid = _canon(game_id)
        if gid is None or not _valid_kind(kind):
            return None
        try:
            wait = max(0.0, min(float(wait), 5.0))
        except (TypeError, ValueError):
            wait = SERVE_WAIT
        return _serve(gid, kind, wait)
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec inattendu de serve_art(%r, %r)", game_id, kind)
        return None


def file_rev(path: Path | None) -> int:
    """Révision publique d'un fichier servi (identique à ``rev`` de art_info)."""
    return _rev(path)


def art_info() -> dict:
    """Capacités connues par jeu, sans réseau.

    ``{game_id: {"source": "steam"|"riot"|"community"|None, "name": str,
    "kinds": {kind: bool}, "custom": [kinds], "cached": [kinds],
    "rev": {kind: int}}}`` — ``kinds[k]`` est vrai si une image est
    disponible (source connue, cache ou image personnalisée) ; ``rev``
    change quand le fichier servi change (à ajouter en ``?v=`` côté front
    pour contourner le cache navigateur).
    """
    out: dict[str, Any] = {}
    try:
        for game in GAMES:
            gid = game.get("id")
            if not isinstance(gid, str):
                continue
            plan = _plan(gid)
            custom_dir, cache_dir = _custom_dir(gid), _cache_dir(gid)
            kinds: dict[str, bool] = {}
            custom: list[str] = []
            cached: list[str] = []
            rev: dict[str, int] = {}
            for kind in KINDS:
                custom_path = _find(custom_dir, kind)
                cached_path = _find(cache_dir, kind)
                if custom_path is not None:
                    custom.append(kind)
                if cached_path is not None:
                    cached.append(kind)
                kinds[kind] = bool(custom_path or cached_path or _available(plan, kind))
                served = custom_path or cached_path
                if served is None and plan:
                    spec = plan["kinds"].get(kind)
                    if spec and spec[0] == "alias":
                        served = _find(custom_dir, spec[1]) or _find(cache_dir, spec[1])
                rev[kind] = _rev(served)
            out[gid] = {
                "source": plan["source"] if plan else None,
                "name": game.get("name") or gid,
                "kinds": kinds,
                "custom": custom,
                "cached": cached,
                "rev": rev,
            }
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec inattendu de art_info()")
    return out


def _error(code: str, fr: str, en: str) -> dict:
    return {"ok": False, "error": code, "message": fr, "message_en": en}


def is_valid_target(game_id: Any, kind: Any) -> bool:
    """Vrai si le jeu (catalogue, alias compris) et le type d'image existent."""
    return _canon(game_id) is not None and _valid_kind(kind)


def _check_ids(game_id: Any, kind: Any) -> tuple[str | None, dict | None]:
    gid = _canon(game_id)
    if gid is None:
        return None, _error("unknown_game", "Jeu inconnu.", "Unknown game.")
    if not _valid_kind(kind):
        return None, _error("unknown_kind", "Type d'image inconnu.", "Unknown image type.")
    return gid, None


def parse_data_url(value: Any) -> tuple[bytes | None, str]:
    """Décode une data URL ``data:image/(png|jpeg|webp);base64,...``.

    Renvoie ``(octets, "")`` ou ``(None, code)`` avec ``code`` valant
    ``"too_large"`` (plus de 8 Mo) ou ``"invalid_image"`` (format ou
    encodage invalide). Le contenu lui-même (octets magiques) est vérifié
    ensuite par :func:`set_custom`.
    """
    if not isinstance(value, str):
        return None, "invalid_image"
    match = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,", value, re.IGNORECASE)
    if not match:
        return None, "invalid_image"
    payload = value[match.end():].strip()
    if not payload:
        return None, "invalid_image"
    if len(payload) > _MAX_B64_CHARS:
        return None, "too_large"
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None, "invalid_image"
    if not data:
        return None, "invalid_image"
    if len(data) > MAX_CUSTOM_BYTES:
        return None, "too_large"
    return data, ""


def decode_data_url(value: Any) -> bytes | None:
    """Octets d'une data URL image valide (≤ 8 Mo), sinon None."""
    if isinstance(value, str) and len(value) > MAX_DATA_URL_CHARS:
        return None
    return parse_data_url(value)[0]


def set_custom(game_id: str, kind: str, data: bytes) -> dict:
    """Enregistre une image fournie par l'utilisateur (≤ 8 Mo, PNG/JPEG/WebP).

    Stockée sous ``data_dir()/art/custom/<game_id>/<kind>.<ext>`` ; elle
    remplace l'image téléchargée jusqu'à :func:`delete_custom`. Renvoie
    ``{"ok", "game_id", "kind", "rev", "message", "message_en"}`` ou
    ``{"ok": False, "error", "message", "message_en"}``.
    """
    try:
        gid, err = _check_ids(game_id, kind)
        if err:
            return err
        if not isinstance(data, (bytes, bytearray)) or not data:
            return _error("invalid_image", "Image vide ou illisible.", "Empty or unreadable image.")
        if len(data) > MAX_CUSTOM_BYTES:
            return _error("too_large", "Image trop lourde (8 Mo maximum).",
                          "Image too large (8 MB maximum).")
        ext = sniff_image(bytes(data[:16]))
        if ext is None:
            return _error("invalid_image", "Format non pris en charge : PNG, JPEG ou WebP.",
                          "Unsupported format: PNG, JPEG or WebP.")
        written = _atomic_write(_custom_dir(gid), kind, bytes(data), ext)
        if written is None:
            return _error("io", "Impossible d'enregistrer l'image.", "Could not save the image.")
        return {
            "ok": True,
            "game_id": gid,
            "kind": kind,
            "custom": True,
            "rev": _rev(written),
            "message": "Image personnalisée enregistrée.",
            "message_en": "Custom image saved.",
        }
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec inattendu de set_custom(%r, %r)", game_id, kind)
        return _error("io", "Impossible d'enregistrer l'image.", "Could not save the image.")


def delete_custom(game_id: str, kind: str) -> dict:
    """Supprime l'image personnalisée (retour à l'image téléchargée)."""
    try:
        gid, err = _check_ids(game_id, kind)
        if err:
            return err
        removed = False
        failed = False
        for ext in _MIME:
            path = _custom_dir(gid) / f"{kind}{ext}"
            if path.exists():
                try:
                    path.unlink()
                    removed = True
                except OSError:
                    failed = True
        if failed:
            return _error("io", "Impossible de supprimer l'image personnalisée.",
                          "Could not delete the custom image.")
        # Révision de l'image désormais servie, sans réseau (la route GET
        # téléchargera si besoin au prochain affichage).
        served = _find(_cache_dir(gid), kind)
        if served is None:
            plan = _plan(gid)
            spec = plan["kinds"].get(kind) if plan else None
            if spec and spec[0] == "alias":
                served = _find(_custom_dir(gid), spec[1]) or _find(_cache_dir(gid), spec[1])
        return {
            "ok": True,
            "game_id": gid,
            "kind": kind,
            "removed": removed,
            "custom": False,
            "rev": _rev(served),
            "message": "Image d'origine restaurée." if removed else "Aucune image personnalisée.",
            "message_en": "Original image restored." if removed else "No custom image.",
        }
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec inattendu de delete_custom(%r, %r)", game_id, kind)
        return _error("io", "Impossible de supprimer l'image personnalisée.",
                      "Could not delete the custom image.")


# ----------------------------------------------------------------- prefetch

_PREFETCH_GUARD = threading.Lock()
_prefetch_running = False
#: Téléchargements simultanés maximum pendant le préchargement.
_PREFETCH_WORKERS = 4


def _game_running() -> bool:
    """Un jeu tourne-t-il ? (le préchargement s'efface alors : zéro coût FPS)."""
    try:
        from .gamewatch import current_game  # noqa: PLC0415

        return current_game() is not None
    except Exception:  # noqa: BLE001
        return False


def _prefetch_jobs(kinds: tuple[str, ...]) -> list[tuple[str, str]]:
    """Liste (jeu, type) à précharger, dans l'ordre du catalogue (CS2 d'abord)."""
    jobs: list[tuple[str, str]] = []
    for game in GAMES:
        gid = game.get("id")
        plan = _plan(gid) if isinstance(gid, str) else None
        if not plan:
            continue
        for kind in kinds:
            spec = plan["kinds"].get(kind)
            if spec is None and kind == "cover" and plan["kinds"].get("portrait"):
                kind, spec = "portrait", plan["kinds"]["portrait"]  # jaquette composée
            if spec is None or spec[0] == "alias":
                continue
            if (gid, kind) not in jobs:
                jobs.append((gid, kind))
    return jobs


def _prefetch_run(kinds: tuple[str, ...]) -> None:
    global _prefetch_running
    try:
        jobs: queue.Queue = queue.Queue()
        for job in _prefetch_jobs(kinds):
            jobs.put(job)
        stop = threading.Event()

        def worker() -> None:
            while not stop.is_set():
                try:
                    gid, kind = jobs.get_nowait()
                except queue.Empty:
                    return
                if _game_running():
                    log.info("Jeu en cours : préchargement des visuels interrompu.")
                    stop.set()
                    return
                get_art(gid, kind)

        # Fils démons (pas de ThreadPoolExecutor : ses fils retarderaient la
        # fermeture de l'application jusqu'à la fin des téléchargements).
        threads = [
            threading.Thread(target=worker, daemon=True, name=f"art-prefetch-{i}")
            for i in range(_PREFETCH_WORKERS)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        log.info("Préchargement des visuels de jeux terminé.")
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Échec du préchargement des visuels de jeux")
    finally:
        with _PREFETCH_GUARD:
            _prefetch_running = False


def prefetch(kinds: Iterable[str] = ("cover", "hero", "logo", "header")) -> None:
    """Précharge les visuels en tâche de fond (fil démon, 4 en parallèle).

    ``header`` (Steam 460×215, quelques dizaines de Ko) sert aux vignettes
    du héros de l'accueil ; les types alias (header des jeux non Steam) ne
    sont pas téléchargés deux fois.

    Rend la main immédiatement et ne lève jamais ; un second appel pendant
    un préchargement en cours est ignoré. Les jeux sans jaquette mais avec
    un portrait (Valorant) préchargent le portrait à la place.
    """
    global _prefetch_running
    try:
        wanted = tuple(k for k in kinds if _valid_kind(k))
        with _PREFETCH_GUARD:
            if _prefetch_running:
                return
            _prefetch_running = True
        try:
            threading.Thread(
                target=_prefetch_run, args=(wanted,), daemon=True, name="art-prefetch"
            ).start()
        except Exception:  # noqa: BLE001
            with _PREFETCH_GUARD:
                _prefetch_running = False
            raise
    except Exception:  # noqa: BLE001 — jamais d'exception
        log.exception("Impossible de lancer le préchargement des visuels")
