"""Moniteur système temps réel : CPU, RAM, débits disque/réseau et top processus."""

from __future__ import annotations

import threading
import time

import psutil

# Compteurs du précédent échantillon (pour calculer les débits), protégés par verrou.
_COUNTERS_LOCK = threading.Lock()
_PREV_DISK: tuple[float, int, int] | None = None  # (timestamp, octets lus, octets écrits)
_PREV_NET: tuple[float, int, int] | None = None  # (timestamp, octets envoyés, octets reçus)

_TOP_PROCESSES = 5


def _cpu_info() -> tuple[float, list[float]]:
    """Charge CPU globale et par cœur (non bloquant, interval=None)."""
    try:
        cpu = float(psutil.cpu_percent(interval=None))
    except Exception:
        cpu = 0.0
    try:
        per_core = [float(v) for v in psutil.cpu_percent(interval=None, percpu=True)]
    except Exception:
        per_core = []
    return cpu, per_core


def _ram_info() -> dict:
    """Mémoire vive utilisée/totale en Go et pourcentage."""
    try:
        mem = psutil.virtual_memory()
        return {
            "used_gb": round((mem.total - mem.available) / 2**30, 2),
            "total_gb": round(mem.total / 2**30, 2),
            "percent": float(mem.percent),
        }
    except Exception:
        return {"used_gb": 0.0, "total_gb": 0.0, "percent": 0.0}


def _rate(delta_bytes: int, dt: float) -> float:
    """Débit en mégaoctets par seconde (0.0 si delta ou durée invalides)."""
    if dt <= 0 or delta_bytes < 0:
        return 0.0
    return round(delta_bytes / dt / 2**20, 2)


def _io_rates(now: float) -> tuple[dict, dict]:
    """Débits disque et réseau depuis l'échantillon précédent (premier appel : 0.0).

    Les compteurs cumulés du précédent appel sont conservés au niveau module,
    sous verrou ; un compteur qui recule (reset système) donne un débit nul.
    """
    global _PREV_DISK, _PREV_NET

    disk_io = {"read_mbps": 0.0, "write_mbps": 0.0}
    net_io = {"up_mbps": 0.0, "down_mbps": 0.0}

    with _COUNTERS_LOCK:
        try:
            counters = psutil.disk_io_counters()
            if counters is not None:
                read_bytes = int(counters.read_bytes)
                write_bytes = int(counters.write_bytes)
                if _PREV_DISK is not None:
                    prev_ts, prev_read, prev_write = _PREV_DISK
                    dt = now - prev_ts
                    disk_io = {
                        "read_mbps": _rate(read_bytes - prev_read, dt),
                        "write_mbps": _rate(write_bytes - prev_write, dt),
                    }
                _PREV_DISK = (now, read_bytes, write_bytes)
        except Exception:
            pass

        try:
            counters = psutil.net_io_counters()
            if counters is not None:
                sent = int(counters.bytes_sent)
                recv = int(counters.bytes_recv)
                if _PREV_NET is not None:
                    prev_ts, prev_sent, prev_recv = _PREV_NET
                    dt = now - prev_ts
                    net_io = {
                        "up_mbps": _rate(sent - prev_sent, dt),
                        "down_mbps": _rate(recv - prev_recv, dt),
                    }
                _PREV_NET = (now, sent, recv)
        except Exception:
            pass

    return disk_io, net_io


def _top_processes() -> list[dict]:
    """Top 5 des processus par CPU (best effort, jamais d'exception)."""
    processes: list[dict] = []
    try:
        for proc in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                name = info.get("name") or f"pid {proc.pid}"
                cpu = info.get("cpu_percent")
                mem = info.get("memory_info")
                processes.append(
                    {
                        "name": str(name),
                        "cpu_percent": round(float(cpu), 1) if cpu is not None else 0.0,
                        "ram_mb": round(mem.rss / 2**20, 1) if mem is not None else 0.0,
                    }
                )
            except Exception:
                continue
        processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
        return processes[:_TOP_PROCESSES]
    except Exception:
        return []


def sample() -> dict:
    """Échantillon instantané du système (rapide, non bloquant, jamais d'exception).

    Les débits disque (Mo/s) et réseau (Mo/s) sont calculés par rapport à
    l'échantillon précédent ; le tout premier appel renvoie des débits à 0.0.
    """
    now = time.time()
    cpu, per_core = _cpu_info()
    disk_io, net_io = _io_rates(now)
    return {
        "ts": now,
        "cpu_percent": cpu,
        "per_core": per_core,
        "ram": _ram_info(),
        "disk_io": disk_io,
        "net_io": net_io,
        "processes_top": _top_processes(),
    }
