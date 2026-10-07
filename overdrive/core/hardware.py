"""Détection du matériel (CPU, RAM, GPU, disques, réseau) avec cache module."""

from __future__ import annotations

import json
import platform
import socket
import subprocess

import psutil

from overdrive.paths import is_windows

_CACHE: dict | None = None

_POWERSHELL_GPU_COMMAND = (
    "Get-CimInstance Win32_VideoController | "
    "Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json -Compress"
)


def _creation_flags() -> int:
    """Drapeaux subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _cpu_name() -> str:
    """Nom commercial du CPU (registre Windows, /proc/cpuinfo Linux)."""
    if is_windows():
        try:
            import winreg  # noqa: PLC0415 — import Windows uniquement

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                name = str(value).strip()
                if name:
                    return name
        except Exception:
            pass
    else:
        try:
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    return platform.processor() or "CPU inconnu"


def _cpu_info() -> dict:
    """Informations CPU via psutil, tolérant aux erreurs."""
    try:
        freq = psutil.cpu_freq()
        freq_max = round(freq.max) if freq and freq.max else None
    except Exception:
        freq_max = None
    try:
        usage = psutil.cpu_percent(interval=0.2)
    except Exception:
        usage = 0.0
    return {
        "name": _cpu_name(),
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "freq_mhz_max": freq_max,
        "usage_percent": usage,
    }


def _ram_info() -> dict:
    """Mémoire vive totale/disponible en Go."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / 2**30, 1),
        "available_gb": round(mem.available / 2**30, 1),
        "used_percent": mem.percent,
    }


def _gpus_windows() -> list[dict]:
    """GPU via PowerShell CIM Win32_VideoController (timeout 10 s)."""
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", _POWERSHELL_GPU_COMMAND],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_creation_flags(),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        data = json.loads(proc.stdout)
        if isinstance(data, dict):
            data = [data]
        gpus: list[dict] = []
        for entry in data:
            if not isinstance(entry, dict) or not entry.get("Name"):
                continue
            vram = entry.get("AdapterRAM")
            vram_mb = round(int(vram) / 2**20) if isinstance(vram, (int, float)) and vram > 0 else None
            gpus.append(
                {
                    "name": str(entry["Name"]).strip(),
                    "vram_mb": vram_mb,
                    "driver": str(entry["DriverVersion"]).strip() if entry.get("DriverVersion") else None,
                }
            )
        return gpus
    except Exception:
        return []


def _gpus_linux() -> list[dict]:
    """GPU via lspci si disponible, sinon liste vide."""
    try:
        proc = subprocess.run(
            ["lspci"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return []
        gpus: list[dict] = []
        for line in proc.stdout.splitlines():
            lower = line.lower()
            if "vga compatible controller" in lower or "3d controller" in lower or "display controller" in lower:
                name = line.split(":", 2)[-1].strip()
                if name:
                    gpus.append({"name": name, "vram_mb": None, "driver": None})
        return gpus
    except Exception:
        return []


def _disks_info() -> list[dict]:
    """Partitions montées avec capacité, accès best effort."""
    disks: list[dict] = []
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        return disks
    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue
        disks.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / 2**30, 1),
                "free_gb": round(usage.free / 2**30, 1),
            }
        )
    return disks


def _network_info() -> dict:
    """Nom d'hôte et interfaces réseau (débit si connu)."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "inconnu"
    interfaces: list[dict] = []
    try:
        for name, stats in psutil.net_if_stats().items():
            interfaces.append(
                {
                    "name": name,
                    "speed_mbps": stats.speed if stats.speed and stats.speed > 0 else None,
                }
            )
    except Exception:
        pass
    return {"hostname": hostname, "interfaces": interfaces}


def _summary(cpu: dict, ram: dict, gpus: list[dict]) -> str:
    """Résumé matériel sur une ligne : CPU / RAM / GPU."""
    gpu_name = gpus[0]["name"] if gpus else "GPU non détecté"
    return f"{cpu['name']} · {ram['total_gb']} Go RAM · {gpu_name}"


def detect_hardware(refresh: bool = False) -> dict:
    """Détecte le matériel de la machine (résultat mis en cache au niveau module)."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE

    cpu = _cpu_info()
    ram = _ram_info()
    gpus = _gpus_windows() if is_windows() else _gpus_linux()

    _CACHE = {
        "os": {
            "name": platform.system(),
            "version": platform.release(),
            "build": platform.version(),
        },
        "cpu": cpu,
        "ram": ram,
        "gpus": gpus,
        "disks": _disks_info(),
        "network": _network_info(),
        "summary": _summary(cpu, ram, gpus),
    }
    return _CACHE
