"""Activité réseau par application : débits globaux, connexions, suspects.

``snapshot()`` renvoie le débit global montant/descendant (différence des
compteurs cumulés ``psutil`` entre deux appels, état conservé au niveau
module sous verrou — état propre à ce module, indépendant de
:mod:`overdrive.core.monitor`), le top 10 des applications par nombre de
connexions TCP/UDP actives, et une liste HONNÊTE de « suspects » :
téléchargeurs probables (Steam, Epic, OneDrive, services Windows Update
actifs). Chaque suspect est formulé au conditionnel — on signale une
activité *possible*, jamais une certitude.

Sous Linux : débits et applications réels si accessibles, ``suspects``
vide (les détections visent des logiciels Windows). Les processus en
``AccessDenied`` sont ignorés proprement ; l'appel complet reste < 2 s
et ne lève jamais d'exception.
"""

from __future__ import annotations

import threading
import time

import psutil

from overdrive.paths import is_windows

# Compteurs réseau du précédent appel (pour les débits), protégés par verrou.
# État distinct de celui de overdrive.core.monitor : les deux modules peuvent
# être appelés à des cadences différentes sans se fausser mutuellement.
_COUNTERS_LOCK = threading.Lock()
_PREV_NET: tuple[float, int, int] | None = None  # (timestamp, envoyés, reçus)

#: Nombre maximal d'applications retournées.
_TOP_APPS = 10
#: Débit descendant global (Mo/s) à partir duquel un lanceur connecté est
#: considéré comme téléchargeant probablement.
_HIGH_DOWN_MBPS = 1.0
#: Services Windows Update dont l'activité est détectée.
_UPDATE_SERVICES = ("wuauserv", "BITS", "DoSvc")


def _rate(delta_bytes: int, dt: float) -> float:
    """Débit en mégaoctets par seconde (0.0 si delta ou durée invalides)."""
    if dt <= 0 or delta_bytes < 0:
        return 0.0
    return round(delta_bytes / dt / 2**20, 2)


def _total_rates(now: float) -> dict:
    """Débits réseau globaux depuis l'appel précédent (premier appel : 0.0)."""
    global _PREV_NET

    total = {"down_mbps": 0.0, "up_mbps": 0.0}
    with _COUNTERS_LOCK:
        try:
            counters = psutil.net_io_counters()
            if counters is not None:
                sent = int(counters.bytes_sent)
                recv = int(counters.bytes_recv)
                if _PREV_NET is not None:
                    prev_ts, prev_sent, prev_recv = _PREV_NET
                    dt = now - prev_ts
                    total = {
                        "down_mbps": _rate(recv - prev_recv, dt),
                        "up_mbps": _rate(sent - prev_sent, dt),
                    }
                _PREV_NET = (now, sent, recv)
        except Exception:
            pass
    return total


def _connections_by_pid() -> dict[int, int]:
    """Nombre de connexions TCP/UDP actives par PID (best effort)."""
    counts: dict[int, int] = {}
    try:
        for conn in psutil.net_connections(kind="inet"):
            pid = conn.pid
            if pid is None:
                continue
            counts[pid] = counts.get(pid, 0) + 1
        return counts
    except Exception:
        counts = {}
    # Vue système inaccessible (droits restreints) : repli par processus.
    try:
        for proc in psutil.process_iter():
            try:
                n = len(proc.net_connections(kind="inet"))
            except Exception:
                continue  # AccessDenied/NoSuchProcess : ignoré proprement
            if n:
                counts[proc.pid] = n
    except Exception:
        pass
    return counts


def _apps_from_counts(counts: dict[int, int]) -> list[dict]:
    """Applications groupées par nom de processus, triées par connexions.

    Les doublons de nom sont fusionnés : ``pid`` est le premier PID
    rencontré, ``pids`` liste tous les PID regroupés.
    """
    merged: dict[str, dict] = {}
    for pid in sorted(counts):
        try:
            name = psutil.Process(pid).name()
        except Exception:
            continue  # AccessDenied/NoSuchProcess : ignoré proprement
        if not name:
            continue
        key = str(name).lower()
        entry = merged.get(key)
        if entry is None:
            merged[key] = {
                "name": str(name),
                "pid": pid,
                "pids": [pid],
                "connections": counts[pid],
            }
        else:
            entry["pids"].append(pid)
            entry["connections"] += counts[pid]
    apps = sorted(merged.values(),
                  key=lambda a: a["connections"], reverse=True)
    return apps[:_TOP_APPS]


def _suspect(*, name: str, name_en: str, detail: str, detail_en: str,
             process: str | None = None, service: str | None = None,
             active: bool = True) -> dict:
    """Construit une entrée « suspect » normalisée."""
    return {
        "name": name,
        "name_en": name_en,
        "detail": detail,
        "detail_en": detail_en,
        "process": process,
        "service": service,
        "active": active,
    }


def _windows_suspects(apps: list[dict], down_mbps: float) -> list[dict]:
    """Téléchargeurs probables sous Windows (détection honnête, best effort)."""
    suspects: list[dict] = []
    by_name = {str(a["name"]).lower(): a for a in apps}
    high_down = down_mbps >= _HIGH_DOWN_MBPS

    # Steam : connexions actives ET débit descendant global élevé.
    steam = by_name.get("steam.exe") or by_name.get("steamservice.exe")
    if steam and steam["connections"] > 0 and high_down:
        suspects.append(_suspect(
            name="Steam",
            name_en="Steam",
            detail=("Steam actif (mise à jour possible) : connexions ouvertes "
                    f"et débit descendant global de {down_mbps:.1f} Mo/s."),
            detail_en=("Steam is active (update possible): open connections "
                       f"with a global download rate of {down_mbps:.1f} MB/s."),
            process=str(steam["name"]),
        ))

    # Epic Games Launcher : même règle que Steam.
    epic = by_name.get("epicgameslauncher.exe")
    if epic and epic["connections"] > 0 and high_down:
        suspects.append(_suspect(
            name="Epic Games Launcher",
            name_en="Epic Games Launcher",
            detail=("Epic Games Launcher actif (téléchargement possible) : "
                    "connexions ouvertes et débit descendant global de "
                    f"{down_mbps:.1f} Mo/s."),
            detail_en=("Epic Games Launcher is active (download possible): "
                       "open connections with a global download rate of "
                       f"{down_mbps:.1f} MB/s."),
            process=str(epic["name"]),
        ))

    # OneDrive : des connexions suffisent, une synchronisation peut être lente.
    onedrive = by_name.get("onedrive.exe")
    if onedrive and onedrive["connections"] > 0:
        suspects.append(_suspect(
            name="OneDrive",
            name_en="OneDrive",
            detail="OneDrive est connecté : synchronisation de fichiers possible.",
            detail_en="OneDrive is connected: file synchronization is possible.",
            process=str(onedrive["name"]),
        ))

    # Services Windows Update en cours d'exécution.
    for service_name in _UPDATE_SERVICES:
        try:
            service = psutil.win_service_get(service_name)
            running = str(service.status()).lower() == "running"
        except Exception:
            continue
        if running:
            suspects.append(_suspect(
                name=f"Windows Update ({service_name})",
                name_en=f"Windows Update ({service_name})",
                detail=("Windows Update en cours d'activité possible : "
                        f"le service {service_name} est en cours d'exécution."),
                detail_en=("Windows Update possibly active: the "
                           f"{service_name} service is running."),
                service=service_name,
            ))
    return suspects


def snapshot() -> dict:
    """Instantané de l'activité réseau (rapide, < 2 s, jamais d'exception).

    Retourne ``{"total": {"down_mbps", "up_mbps"}, "apps": [{"name",
    "pid", "pids", "connections"}], "suspects": [...]}``. Les débits sont
    calculés par rapport à l'appel précédent (premier appel : 0.0) ;
    ``suspects`` est vide hors Windows.
    """
    try:
        total = _total_rates(time.time())
    except Exception:
        total = {"down_mbps": 0.0, "up_mbps": 0.0}
    try:
        apps = _apps_from_counts(_connections_by_pid())
    except Exception:
        apps = []
    suspects: list[dict] = []
    if is_windows():
        try:
            suspects = _windows_suspects(apps, float(total["down_mbps"]))
        except Exception:
            suspects = []
    return {"total": total, "apps": apps, "suspects": suspects}
