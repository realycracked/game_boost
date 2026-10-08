"""Détection du matériel (CPU, RAM, GPU, disques, réseau) avec cache module.

Le dict retourné par :func:`detect_hardware` porte aussi la clé ``"tier"``
(:func:`hardware_tier`) : classification « petite config » / milieu de
gamme / haut de gamme utilisée par le profil ``petite_config`` du quiz et
par la bannière de la page Optimisations.

VRAM sous Windows : ``Win32_VideoController.AdapterRAM`` est un uint32
plafonné à 4 Go (une carte de 16 Go remonte ≈ 4095 Mo). La VRAM réelle est
lue dans le registre de la classe d'affichage
(``HardwareInformation.qwMemorySize``, repli ``HardwareInformation.MemorySize``),
chaque sous-clé étant associée à son GPU par ``DriverDesc`` ; AdapterRAM
n'est plus qu'un dernier recours, traité comme inconnu s'il est saturé.
"""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
import threading

import psutil

from overdrive.core.amd import gpu_arch
from overdrive.paths import is_windows

_CACHE: dict | None = None
_CACHE_LOCK = threading.Lock()

_POWERSHELL_GPU_COMMAND = (
    "Get-CimInstance Win32_VideoController | "
    "Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json -Compress"
)

#: Classe de périphériques « Carte graphique » (GUID_DEVCLASS_DISPLAY) : une
#: sous-clé NNNN par adaptateur/pilote installé.
_DISPLAY_CLASS_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e968-e325-11ce-bfc1-08002be10318}"
)
_REG_QW_MEMORY = "HardwareInformation.qwMemorySize"
_REG_MEMORY = "HardwareInformation.MemorySize"

#: Au-delà de ce seuil (Mo), une valeur 32 bits (AdapterRAM, MemorySize en
#: DWORD) est saturée : la VRAM réelle est inconnue (>= 4 Go).
_SATURATED_32BIT_MB = 4095
_UINT32_MAX = 0xFFFFFFFF


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


# ---------------------------------------------------------------------------
# VRAM réelle (registre de la classe d'affichage) — fonctions pures testables
# ---------------------------------------------------------------------------


def normalize_gpu_name(name: object) -> str:
    """Nom de GPU comparable : minuscules, sans (TM)/(R)/™/®, espaces réduits."""
    if not isinstance(name, str):
        return ""
    low = re.sub(r"\((tm|r)\)|[™®]", " ", name.lower())
    return re.sub(r"\s+", " ", low).strip()


def _registry_number(value: object) -> tuple[int, bool] | None:
    """(valeur, source 64 bits ?) d'une valeur registre numérique ou binaire.

    ``int`` (REG_DWORD / REG_QWORD) ou ``bytes`` (REG_BINARY, petit-boutiste,
    8 octets au plus). Une source est « 64 bits » si elle fait plus de 4
    octets ou dépasse la plage uint32. ``None`` si inexploitable.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return (value, value > _UINT32_MAX) if value > 0 else None
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw or len(raw) > 8:
            return None
        number = int.from_bytes(raw, "little")
        return (number, len(raw) > 4) if number > 0 else None
    return None


def vram_mb_from_registry(qw_memory_size: object = None,
                          memory_size: object = None) -> int | None:
    """VRAM (Mo) depuis les valeurs registre d'une sous-clé de la classe d'affichage.

    ``HardwareInformation.qwMemorySize`` (QWORD, octets) est prioritaire ;
    repli sur ``HardwareInformation.MemorySize`` (DWORD ou binaire). Une
    valeur 32 bits >= 4095 Mo est saturée => ``None`` (inconnue). Pure,
    jamais d'exception.
    """
    try:
        qword = _registry_number(qw_memory_size)
        if qword is not None:
            return round(qword[0] / 2**20) or None
        dword = _registry_number(memory_size)
        if dword is None:
            return None
        value_mb = round(dword[0] / 2**20)
        if not dword[1] and value_mb >= _SATURATED_32BIT_MB:
            return None
        return value_mb or None
    except Exception:
        return None


def vram_mb_from_adapter_ram(adapter_ram: object) -> int | None:
    """VRAM (Mo) depuis ``Win32_VideoController.AdapterRAM`` (dernier recours).

    uint32 : toute valeur >= 4095 Mo est saturée (cartes de 4 Go et plus)
    et traitée comme inconnue (``None``). Pure, jamais d'exception.
    """
    if isinstance(adapter_ram, bool) or not isinstance(adapter_ram, (int, float)):
        return None
    if adapter_ram <= 0:
        return None
    value_mb = round(float(adapter_ram) / 2**20)
    if value_mb >= _SATURATED_32BIT_MB:
        return None
    return value_mb or None


def parse_display_class_entries(entries: list[dict]) -> dict[str, int]:
    """Associe chaque GPU (nom normalisé) à sa VRAM d'après les sous-clés registre.

    ``entries`` : ``[{"DriverDesc": str, "HardwareInformation.qwMemorySize":
    int|bytes|None, "HardwareInformation.MemorySize": int|bytes|None}]``.
    Plusieurs sous-clés pour un même nom (pilote réinstallé) => valeur
    maximale. Pure (testable sous Linux), jamais d'exception.
    """
    result: dict[str, int] = {}
    try:
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            key = normalize_gpu_name(entry.get("DriverDesc"))
            if not key:
                continue
            vram = vram_mb_from_registry(entry.get(_REG_QW_MEMORY),
                                         entry.get(_REG_MEMORY))
            if vram is not None and vram > result.get(key, 0):
                result[key] = vram
    except Exception:
        return result
    return result


def _read_display_class_entries() -> list[dict]:
    """Sous-clés NNNN de la classe d'affichage (Windows), jamais d'exception."""
    entries: list[dict] = []
    try:
        import winreg  # noqa: PLC0415 — import Windows uniquement

        access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS_KEY,
                              0, access) as root:
            index = 0
            while index < 256:  # garde-fou
                try:
                    sub_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                if not re.fullmatch(r"\d{4}", sub_name):
                    continue  # « Properties » et autres sous-clés non adaptateur
                try:
                    with winreg.OpenKeyEx(root, sub_name, 0, access) as sub:
                        entry: dict = {}
                        for value_name in ("DriverDesc", _REG_QW_MEMORY, _REG_MEMORY):
                            try:
                                entry[value_name] = winreg.QueryValueEx(sub, value_name)[0]
                            except OSError:
                                entry[value_name] = None
                        entries.append(entry)
                except OSError:
                    continue
    except Exception:
        return entries
    return entries


def _registry_vram_by_name() -> dict[str, int]:
    """VRAM réelle par nom de GPU normalisé (registre Windows), ``{}`` si échec."""
    try:
        return parse_display_class_entries(_read_display_class_entries())
    except Exception:
        return {}


def resolve_gpu_vram(name: object, adapter_ram: object,
                     registry: dict[str, int],
                     single_adapter: bool = False) -> tuple[int | None, str | None]:
    """(VRAM en Mo, source) d'un GPU : registre d'abord, AdapterRAM en dernier recours.

    Association par nom normalisé (``DriverDesc`` = ``Name``). Si
    ``single_adapter`` (un seul GPU réel côté CIM) et une seule VRAM
    connue côté registre, elle lui est attribuée même si les noms
    diffèrent légèrement. Source : ``"registry"`` | ``"adapter_ram"`` |
    ``None``. Pure, jamais d'exception.
    """
    try:
        registry = registry if isinstance(registry, dict) else {}
        key = normalize_gpu_name(name)
        if key and key in registry:
            return registry[key], "registry"
        real_entries = [vram for reg_name, vram in registry.items()
                        if not any(m in reg_name for m in _VIRTUAL_GPU_MARKERS)]
        if single_adapter and len(real_entries) == 1:
            return real_entries[0], "registry"
        fallback = vram_mb_from_adapter_ram(adapter_ram)
        return (fallback, "adapter_ram") if fallback is not None else (None, None)
    except Exception:
        return None, None


def _gpus_windows() -> list[dict]:
    """GPU via PowerShell CIM Win32_VideoController (timeout 10 s) + VRAM registre."""
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
        entries = [e for e in data if isinstance(e, dict) and e.get("Name")]
        registry = _registry_vram_by_name()
        real_count = sum(
            1 for e in entries
            if not any(m in str(e["Name"]).lower() for m in _VIRTUAL_GPU_MARKERS)
        )
        gpus: list[dict] = []
        for entry in entries:
            name = str(entry["Name"]).strip()
            vram_mb, source = resolve_gpu_vram(
                name, entry.get("AdapterRAM"), registry,
                single_adapter=real_count == 1
                and not any(m in name.lower() for m in _VIRTUAL_GPU_MARKERS),
            )
            gpus.append(
                {
                    "name": name,
                    "vram_mb": vram_mb,
                    "vram_source": source,
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


#: GPU dédiés d'entrée de gamme reconnus par leur nom (VRAM éventuellement
#: inconnue) : Radeon RX 460/550/560, GeForce GT 710/730/1030.
_ENTRY_DGPU_RE = re.compile(r"\brx\s*(460|550|560)\b|\bgt\s*(7[1-3]0|1030)\b")

#: Sous ce seuil de VRAM connue (Mo), un GPU dédié ne peut pas classer la
#: machine en haut de gamme (cohérent avec overdrive.core.games.cs2).
_HIGHEND_MIN_VRAM_MB = 6144


def _is_weak_dgpu(gpu: dict) -> bool:
    """Vrai si un GPU dédié est trop modeste pour un classement haut de gamme.

    VRAM connue sous 6 Go, génération Polaris (RX 400/500) ou modèle
    d'entrée de gamme reconnu par son nom.
    """
    name = normalize_gpu_name(gpu.get("name"))
    vram = _as_positive_number(gpu.get("vram_mb"))
    if vram is not None and vram < _HIGHEND_MIN_VRAM_MB:
        return True
    if gpu_arch(name) == "polaris":
        return True
    return _ENTRY_DGPU_RE.search(name) is not None


def hardware_tier(hw: dict | None = None) -> str:
    """Classe la machine : ``"lowend"`` | ``"midrange"`` | ``"highend"`` | ``"unknown"``.

    Fonction PURE sur le dict de :func:`detect_hardware` (``hw=None`` =>
    ``detect_hardware()``), donc testable sous Linux avec des fixtures.

    Critères (chaque signal n'est évalué que si ses entrées existent) :

    * ``unknown`` : RAM indisponible/<= 0 **et** cœurs physiques **et**
      logiques indisponibles (le GPU seul ne suffit pas à classer) ;
    * ``lowend`` si au moins un signal : RAM <= 8,5 Go (8 Go = minimum CS2,
      psutil remonte 7,8–8,0 pour 8 Go physiques) ; iGPU uniquement ; tous
      les GPU réels à VRAM connue et <= 2048 Mo (VRAM lue dans le registre,
      AdapterRAM saturé traité comme inconnu) ; <= 2 cœurs physiques ;
      <= 4 cœurs physiques à moins de 2600 MHz de fréquence de base ;
    * ``highend`` : aucun signal lowend, RAM >= 31 Go, >= 8 cœurs physiques
      et au moins un GPU dédié qui n'est pas « modeste » (VRAM connue
      < 6 Go, Polaris RX 400/500 ou entrée de gamme reconnue par son nom) —
      cohérent avec le tier CS2 (:func:`overdrive.core.games.cs2.detect_tier`) ;
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
    has_capable_dgpu = any(
        not _is_igpu(str(gpu.get("name") or "")) and not _is_weak_dgpu(gpu)
        for gpu in real_gpus
    )

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
            and has_dgpu and has_capable_dgpu):
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
