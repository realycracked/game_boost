"""Températures CPU/GPU pour le widget overlay (best effort, cache court).

GPU : NVIDIA uniquement, via ``nvidia-smi --query-gpu=temperature.gpu``
(cherché dans le PATH puis dans les emplacements Windows usuels). AMD et
Intel n'exposent pas d'outil équivalent fiable : ``gpu_c`` reste None,
honnêtement, plutôt qu'une estimation.

CPU : sous Windows, lecture best effort de la zone thermique ACPI via
PowerShell (``MSAcpi_ThermalZoneTemperature``, souvent indisponible selon
le constructeur → None sans erreur) ; sous Linux,
``psutil.sensors_temperatures()`` best effort.

Les appels viennent du widget toutes les secondes : le résultat est mis en
cache 3 s sous verrou pour ne pas relancer de sous-processus à chaque tick.
Jamais d'exception.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from ..paths import is_windows

# Durée de validité du cache (le widget interroge toutes les secondes).
_CACHE_TTL_S = 3.0
# Timeout des sous-processus (nvidia-smi, PowerShell).
_TIMEOUT_S = 5
# Fenêtre de plausibilité d'une température CPU (°C) : hors de cette plage,
# la zone ACPI renvoie une valeur figée/fantaisiste → ignorée.
_CPU_MIN_C, _CPU_MAX_C = 10.0, 110.0
# Fenêtre de plausibilité d'une température GPU (°C).
_GPU_MIN_C, _GPU_MAX_C = -40.0, 150.0

# Capteurs Linux considérés comme CPU (psutil.sensors_temperatures()).
_LINUX_CPU_SENSORS: tuple[str, ...] = (
    "coretemp", "k10temp", "zenpower", "cpu_thermal", "cpu-thermal", "acpitz",
)

_PS_CPU_COMMAND = (
    "(Get-CimInstance -Namespace root/wmi "
    "-ClassName MSAcpi_ThermalZoneTemperature).CurrentTemperature"
)

# Cache module protégé par verrou (une mesure à la fois, résultat partagé).
_LOCK = threading.Lock()
_CACHE: dict | None = None
_CACHE_AT = 0.0


def _creation_flags() -> int:
    """Drapeaux subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _nvidia_smi_path() -> str | None:
    """Chemin de nvidia-smi : PATH, puis System32 et NVSMI sous Windows.

    Renvoie None si introuvable (GPU AMD/Intel ou pilote absent).
    Jamais d'exception.
    """
    try:
        found = shutil.which("nvidia-smi")
        if found:
            return found
        if not is_windows():
            return None
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidates = (
            Path(system_root) / "System32" / "nvidia-smi.exe",
            Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
        )
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return str(candidate)
            except OSError:
                continue
        return None
    except Exception:
        return None


def _gpu_temp() -> tuple[float | None, str | None]:
    """Température GPU en °C via nvidia-smi (premier GPU), sinon (None, None).

    Jamais d'exception.
    """
    exe = _nvidia_smi_path()
    if exe is None:
        return None, None
    try:
        proc = subprocess.run(
            [exe, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            creationflags=_creation_flags(),
        )
        if proc.returncode != 0:
            return None, None
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            value = float(line.split(",")[0].strip())
            if _GPU_MIN_C <= value <= _GPU_MAX_C:
                return value, "nvidia-smi"
            return None, None
        return None, None
    except Exception:
        return None, None


def _cpu_temp_windows() -> tuple[float | None, str | None]:
    """Température CPU Windows via la zone thermique ACPI (PowerShell).

    ``CurrentTemperature`` est en dixièmes de kelvin ; la classe est souvent
    absente ou figée selon le constructeur → (None, None) sans erreur.
    Garde la zone la plus chaude dans la plage plausible 10-110 °C.
    Jamais d'exception.
    """
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", _PS_CPU_COMMAND],
            shell=False,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            creationflags=_creation_flags(),
        )
        if proc.returncode != 0:
            return None, None
        best: float | None = None
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                celsius = float(line) / 10.0 - 273.15
            except ValueError:
                continue
            if _CPU_MIN_C <= celsius <= _CPU_MAX_C and (best is None or celsius > best):
                best = celsius
        if best is None:
            return None, None
        return round(best, 1), "msacpi"
    except Exception:
        return None, None


def _cpu_temp_linux() -> tuple[float | None, str | None]:
    """Température CPU Linux via psutil.sensors_temperatures(), best effort.

    Parcourt les capteurs CPU connus (coretemp, k10temp, ...) et garde la
    valeur la plus chaude dans la plage plausible. Jamais d'exception.
    """
    try:
        import psutil  # noqa: PLC0415 — import tardif (module léger mais optionnel)

        readings = psutil.sensors_temperatures()
    except Exception:
        return None, None
    if not readings:
        return None, None
    for name in _LINUX_CPU_SENSORS:
        best: float | None = None
        for entry in readings.get(name) or ():
            current = getattr(entry, "current", None)
            if (
                isinstance(current, (int, float))
                and _CPU_MIN_C <= float(current) <= _CPU_MAX_C
                and (best is None or float(current) > best)
            ):
                best = float(current)
        if best is not None:
            return round(best, 1), "psutil"
    return None, None


def _measure() -> dict:
    """Mesure réelle (sans cache) : GPU puis CPU, sources agrégées."""
    gpu_c, gpu_source = _gpu_temp()
    if is_windows():
        cpu_c, cpu_source = _cpu_temp_windows()
    else:
        cpu_c, cpu_source = _cpu_temp_linux()
    sources = [s for s in (gpu_source, cpu_source) if s]
    return {"gpu_c": gpu_c, "cpu_c": cpu_c, "source": "+".join(sources) or None}


def read_temps() -> dict:
    """Températures GPU/CPU en °C, mises en cache 3 s.

    Renvoie ``{"gpu_c": float|None, "cpu_c": float|None, "source": str|None}``
    où ``source`` agrège les origines des mesures ("nvidia-smi", "msacpi",
    "psutil", jointes par "+"), ou None si rien n'est mesurable.
    Jamais d'exception.
    """
    global _CACHE, _CACHE_AT
    try:
        with _LOCK:
            now = time.monotonic()
            if _CACHE is not None and now - _CACHE_AT < _CACHE_TTL_S:
                return dict(_CACHE)
            result = _measure()
            _CACHE = result
            _CACHE_AT = time.monotonic()
            return dict(result)
    except Exception:
        return {"gpu_c": None, "cpu_c": None, "source": None}
