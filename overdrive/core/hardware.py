"""Détection du matériel (CPU, RAM, GPU, disques, réseau) avec cache module.

Le dict retourné par :func:`detect_hardware` porte aussi la clé ``"tier"``
(:func:`hardware_tier`) : classification « petite config » / milieu de
gamme / haut de gamme utilisée par le profil ``petite_config`` du quiz et
par la bannière de la page Optimisations.
"""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
import threading

import psutil

from overdrive.paths import is_windows

_CACHE: dict | None = None
_CACHE_LOCK = threading.Lock()

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


# ---------------------------------------------------------------------------
# Classification en tier (« petite config » / milieu / haut de gamme)
# ---------------------------------------------------------------------------

#: Adaptateurs virtuels à ignorer (même liste que insights._VIRTUAL_GPU_MARKERS).
_VIRTUAL_GPU_MARKERS = ("microsoft basic display", "virtual", "remote", "vnc")

#: iGPU détectables par nom (minuscules, recherche par sous-chaîne).
_IGPU_MARKERS = (
    "intel(r) hd graphics", "intel hd graphics",
    "intel(r) uhd graphics", "intel uhd graphics",
    "iris",  # Iris / Iris Plus / Iris Xe
)

#: APU AMD : « AMD Radeon(TM) Graphics », « Radeon(TM) R5 Graphics »... —
#: un « radeon ... graphics » sans numéro de série dédié (RX/HD/R9 290, etc.).
_AMD_APU_RE = re.compile(r"radeon(\(tm\))?\s+(r[2-7]\s+)?graphics$")


def _is_igpu(name: str) -> bool:
    """Vrai si le nom de GPU désigne une puce graphique intégrée (iGPU/APU)."""
    low = name.lower().strip()
    if any(marker in low for marker in _IGPU_MARKERS):
        return True
    # APU AMD type « Radeon(TM) Vega 8 Graphics ».
    if "vega" in low and "graphics" in low:
        return True
    return _AMD_APU_RE.search(low) is not None


def _as_positive_number(value: object) -> float | None:
    """Nombre strictement positif, sinon ``None`` (entrée manquante/invalide)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def hardware_tier(hw: dict | None = None) -> str:
    """Classe la machine : ``"lowend"`` | ``"midrange"`` | ``"highend"`` | ``"unknown"``.

    Fonction PURE sur le dict de :func:`detect_hardware` (``hw=None`` =>
    ``detect_hardware()``), donc testable sous Linux avec des fixtures.

    Critères (chaque signal n'est évalué que si ses entrées existent) :

    * ``unknown`` : RAM indisponible/<= 0 **et** cœurs physiques **et**
      logiques indisponibles (le GPU seul ne suffit pas à classer) ;
    * ``lowend`` si au moins un signal : RAM <= 8,5 Go (8 Go = minimum CS2,
      psutil remonte 7,8–8,0 pour 8 Go physiques) ; iGPU uniquement ; tous
      les GPU réels à VRAM connue et <= 2048 Mo (AdapterRAM fiable sous
      4 Go) ; <= 2 cœurs physiques ; <= 4 cœurs physiques à moins de
      2600 MHz de fréquence de base ;
    * ``highend`` : aucun signal lowend, RAM >= 31 Go, >= 8 cœurs physiques
      et au moins un GPU dédié (VRAM volontairement ignorée : uint32) ;
    * ``midrange`` sinon.

    Ajustement documenté par rapport à la spécification : le repli
    ``cores_physical = cores_logical // 2`` est borné à 1 minimum (une
    machine à 1 cœur logique donnerait sinon 0 cœur physique, incohérent).
    """
    if hw is None:
        hw = detect_hardware()
    if not isinstance(hw, dict):
        return "unknown"

    ram = hw.get("ram") if isinstance(hw.get("ram"), dict) else {}
    cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
    gpus = hw.get("gpus") if isinstance(hw.get("gpus"), list) else []

    ram_gb = _as_positive_number(ram.get("total_gb"))
    cores_physical = _as_positive_number(cpu.get("cores_physical"))
    cores_logical = _as_positive_number(cpu.get("cores_logical"))
    freq_mhz = _as_positive_number(cpu.get("freq_mhz_max"))

    # Cas VM / détection en panne : rien d'exploitable pour classer.
    if ram_gb is None and cores_physical is None and cores_logical is None:
        return "unknown"

    # Repli : cœurs physiques inconnus mais cœurs logiques disponibles
    # (SMT supposé), borné à 1 pour rester cohérent.
    if cores_physical is None and cores_logical is not None:
        cores_physical = float(max(1, int(cores_logical) // 2))

    real_gpus: list[dict] = []
    for gpu in gpus:
        if not isinstance(gpu, dict):
            continue
        name = str(gpu.get("name") or "").strip()
        if not name:
            continue
        if any(marker in name.lower() for marker in _VIRTUAL_GPU_MARKERS):
            continue
        real_gpus.append(gpu)

    igpu_only = bool(real_gpus) and all(
        _is_igpu(str(gpu.get("name") or "")) for gpu in real_gpus
    )
    has_dgpu = any(not _is_igpu(str(gpu.get("name") or "")) for gpu in real_gpus)

    lowend = False
    # L1 — 8 Go de RAM ou moins (seuil 8,5 : inclut 8 Go, exclut 12 Go).
    if ram_gb is not None and ram_gb <= 8.5:
        lowend = True
    # L2 — aucune carte dédiée : aucun iGPU ne tient CS2 confortablement.
    if igpu_only:
        lowend = True
    # L3 — VRAM maximale <= 2 Go, uniquement si toutes les VRAM sont connues.
    if real_gpus:
        vrams = [_as_positive_number(gpu.get("vram_mb")) for gpu in real_gpus]
        if all(vram is not None for vram in vrams) and max(vrams) <= 2048:  # type: ignore[type-var]
            lowend = True
    # L4 — dual-core : la simulation subtick de CS2 + Windows saturent.
    if cores_physical is not None and cores_physical <= 2:
        lowend = True
    # L5 — quad-core basse fréquence (i5-8250U base 1,6 GHz...).
    if (cores_physical is not None and freq_mhz is not None
            and cores_physical <= 4 and freq_mhz < 2600):
        lowend = True

    if lowend:
        return "lowend"

    # 31 et non 32 : 32 Go physiques remontent ~31,8 via psutil.
    if (ram_gb is not None and ram_gb >= 31
            and cores_physical is not None and cores_physical >= 8
            and has_dgpu):
        return "highend"

    return "midrange"


def cached_tier() -> str | None:
    """Tier si la détection matérielle a déjà eu lieu, sinon ``None``.

    Ne déclenche JAMAIS une détection (appelé par ``/api/status`` qui doit
    rester instantané).
    """
    cache = _CACHE
    if cache is None:
        return None
    tier = cache.get("tier")
    # Secours : cache rempli par une version antérieure sans la clé "tier".
    return tier if isinstance(tier, str) else hardware_tier(cache)


def detect_hardware(refresh: bool = False) -> dict:
    """Détecte le matériel de la machine (résultat mis en cache au niveau module)."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE
    with _CACHE_LOCK:
        # Double vérification : une détection concurrente a pu remplir le cache.
        if _CACHE is not None and not refresh:
            return _CACHE
        return _detect_locked()


def _detect_locked() -> dict:
    """Détection effective (appelée sous _CACHE_LOCK)."""
    global _CACHE

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
    # Calculé en dernier, une fois le dict rempli : ?refresh=1 recalcule
    # donc aussi le tier.
    _CACHE["tier"] = hardware_tier(_CACHE)
    return _CACHE
