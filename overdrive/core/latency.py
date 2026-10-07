"""Estimation de la latence réseau vers des zones géographiques de jeu.

Chaque région est représentée par un hôte public STABLE (CDN anycast,
miroirs de datacenters connus, endpoints Blizzard documentés). La mesure
ouvre 3 connexions TCP successives (refermées immédiatement, aucune
donnée envoyée) et relève le temps d'établissement : c'est une
« estimation de la latence vers chaque zone », pas une promesse de ping
in-game. Les régions sont sondées en parallèle, l'appel complet est
borné dans le temps et ne lève jamais d'exception.
"""

from __future__ import annotations

import socket
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

#: Nombre de connexions TCP par région.
_ATTEMPTS = 3
#: Délai maximal d'établissement d'une connexion (secondes).
_CONNECT_TIMEOUT = 2.0
#: Budget temps global d'un appel à measure() (secondes, total < 8 s).
_TOTAL_TIMEOUT = 7.5
#: Nombre maximal de sondes simultanées.
_MAX_WORKERS = 8

#: Régions sondées : hôtes publics stables, choisis comme références
#: géographiques pour un joueur FR/EU (ports 443/80, 1119 pour Battle.net).
REGIONS: list[dict] = [
    {
        "id": "proche",
        "label": "Point le plus proche (CDN anycast Cloudflare)",
        "host": "speed.cloudflare.com",
        "port": 443,
    },
    {
        "id": "paris",
        "label": "Paris (datacenter Scaleway/Online)",
        "host": "ping.online.net",
        "port": 80,
    },
    {
        "id": "france_nord",
        "label": "France Nord — Gravelines (OVHcloud)",
        "host": "gra.proof.ovh.net",
        "port": 443,
    },
    {
        "id": "europe_ouest",
        "label": "Europe Ouest (Blizzard eu.battle.net)",
        "host": "eu.battle.net",
        "port": 1119,
    },
    {
        "id": "amerique_est",
        "label": "Amérique du Nord Est (Blizzard us.battle.net)",
        "host": "us.battle.net",
        "port": 1119,
    },
    {
        "id": "canada",
        "label": "Canada — Beauharnois (OVHcloud)",
        "host": "ca.ovh.com",
        "port": 443,
    },
    {
        "id": "asie",
        "label": "Asie — Corée (Blizzard kr.battle.net)",
        "host": "kr.battle.net",
        "port": 1119,
    },
    {
        "id": "usa_web",
        "label": "États-Unis (GitHub, référence web)",
        "host": "github.com",
        "port": 443,
    },
]

_REGIONS_BY_ID: dict[str, dict] = {r["id"]: r for r in REGIONS}


def _result(region: dict, *, ok: bool, latencies: list[float] | None = None,
            message: str | None = None) -> dict:
    """Construit le dictionnaire de résultat d'une région."""
    latencies = latencies or []
    return {
        "id": region["id"],
        "label": region["label"],
        "host": region["host"],
        "ms_min": round(min(latencies), 1) if latencies else None,
        "ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "ms_max": round(max(latencies), 1) if latencies else None,
        "ok": ok,
        "message": message,
    }


def _probe_region(region: dict) -> dict:
    """Sonde une région : 3 connexions TCP chronométrées, refermées aussitôt."""
    host = str(region["host"])
    port = int(region["port"])
    latencies: list[float] = []
    error: str | None = None
    for _ in range(_ATTEMPTS):
        start = time.perf_counter()
        try:
            sock = socket.create_connection((host, port), timeout=_CONNECT_TIMEOUT)
        except socket.gaierror:
            # Résolution DNS impossible : inutile de réessayer.
            error = f"Résolution DNS impossible pour {host}."
            break
        except TimeoutError:
            error = f"Délai de connexion dépassé vers {host}:{port}."
            continue
        except ConnectionRefusedError:
            error = f"Connexion refusée par {host}:{port}."
            continue
        except OSError as exc:
            detail = getattr(exc, "strerror", None) or str(exc) or exc.__class__.__name__
            error = f"Connexion impossible vers {host}:{port} : {detail}"
            continue
        latencies.append((time.perf_counter() - start) * 1000.0)
        # Aucune donnée envoyée : la connexion est refermée immédiatement.
        try:
            sock.close()
        except OSError:
            pass
    if latencies:
        return _result(region, ok=True, latencies=latencies)
    return _result(region, ok=False,
                   message=error or f"Connexion impossible vers {host}:{port}.")


def measure(region_ids: list[str] | None = None) -> list[dict]:
    """Mesure la latence TCP estimée vers les régions demandées (toutes par défaut).

    Retourne, dans l'ordre du catalogue, un résultat par région :
    ``{"id", "label", "host", "ms_min", "ms_avg", "ms_max", "ok", "message"}``.
    Les identifiants inconnus sont ignorés. Jamais d'exception, durée bornée.
    """
    if region_ids is None:
        selected = list(REGIONS)
    else:
        wanted = {str(region_id) for region_id in region_ids}
        selected = [r for r in REGIONS if r["id"] in wanted]
    if not selected:
        return []

    results: list[dict] = []
    pool = ThreadPoolExecutor(
        max_workers=min(_MAX_WORKERS, len(selected)),
        thread_name_prefix="overdrive-latency",
    )
    try:
        futures = [(region, pool.submit(_probe_region, region)) for region in selected]
        deadline = time.monotonic() + _TOTAL_TIMEOUT
        for region, future in futures:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                results.append(future.result(timeout=remaining))
            except FutureTimeoutError:
                future.cancel()
                results.append(_result(
                    region, ok=False,
                    message="Délai global de mesure dépassé."))
            except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
                results.append(_result(
                    region, ok=False,
                    message=f"Erreur inattendue : {exc}"))
    finally:
        # Ne bloque pas sur d'éventuelles sondes encore en cours.
        pool.shutdown(wait=False, cancel_futures=True)
    return results
