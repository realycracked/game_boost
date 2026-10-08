"""Constats intelligents : détections automatiques de réglages qui coûtent des FPS.

Chaque constat est un dict ``{"id", "severity", "title", "title_en",
"detail", "detail_en", "action_url"}`` avec ``severity`` valant
``"important"`` ou ``"conseil"``. Toutes les détections sont Windows
uniquement et best effort : chacune est isolée dans son propre
``try/except``, :func:`get_insights` ne lève jamais d'exception et
renvoie ``[]`` sous Linux.

Détections couvertes :

* écran configuré sous sa fréquence de rafraîchissement maximale
  (ctypes ``user32``, la plus importante) ;
* overlays gourmands actifs (processus via psutil) ;
* pilote graphique ancien (CIM ``Win32_VideoController``) ;
* plan d'alimentation Équilibré actif (``powercfg``).
"""

from __future__ import annotations

import ctypes
import json
import re
import subprocess
from datetime import datetime, timezone

from overdrive.paths import is_windows

# ---------------------------------------------------------------------------
# Constantes Windows (ctypes / powercfg)
# ---------------------------------------------------------------------------

#: Mode d'affichage actuel pour EnumDisplaySettingsW.
_ENUM_CURRENT_SETTINGS = -1
#: DISPLAY_DEVICE.StateFlags : écran réellement relié au bureau.
_DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001
#: DISPLAY_DEVICE.StateFlags : pseudo-périphérique de duplication (à ignorer).
_DISPLAY_DEVICE_MIRRORING_DRIVER = 0x00000008

#: GUID du plan d'alimentation Windows « Équilibré ».
_BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"

_GUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

#: Âge (en jours) au-delà duquel un pilote graphique est considéré ancien.
_DRIVER_MAX_AGE_DAYS = 180

#: Pages officielles de téléchargement des pilotes selon la marque du GPU.
_DRIVER_URLS: tuple[tuple[str, str], ...] = (
    ("nvidia", "https://www.nvidia.com/fr-fr/drivers/"),
    ("amd", "https://www.amd.com/fr/support/download/drivers.html"),
    ("radeon", "https://www.amd.com/fr/support/download/drivers.html"),
    ("intel", "https://www.intel.fr/content/www/fr/fr/download-center/home.html"),
)

#: Adaptateurs vidéo virtuels / génériques à ignorer pour le constat pilote.
_VIRTUAL_GPU_MARKERS = ("microsoft basic display", "virtual", "remote", "vnc")

_PS_DRIVER_COMMAND = (
    "Get-CimInstance Win32_VideoController | Select-Object Name, "
    "@{Name='DriverDate';Expression={if ($_.DriverDate) "
    "{ $_.DriverDate.ToString('yyyy-MM-dd') } else { $null }}} | "
    "ConvertTo-Json -Compress"
)

#: Overlays connus pour coûter des FPS : {nom de processus en minuscules:
#: (id, nom affiché, comment le couper FR, comment le couper EN)}.
#: Volontairement absents : Discord et MSI Afterburner (outils voulus par les
#: joueurs), et ``nvcontainer.exe`` (héberge de nombreux services NVIDIA sans
#: lien avec l'overlay : trop ambigu pour être signalé prudemment).
_OVERLAYS: dict[str, tuple[str, str, str, str]] = {
    "nvidia overlay.exe": (
        "overlay_nvidia",
        "Superposition NVIDIA",
        "Désactivez-la dans l'application NVIDIA (ou GeForce Experience) : "
        "Paramètres > Superposition en jeu.",
        "Disable it in the NVIDIA app (or GeForce Experience): "
        "Settings > In-game overlay.",
    ),
    "overwolf.exe": (
        "overlay_overwolf",
        "Overwolf",
        "Quittez Overwolf depuis son icône de la zone de notification, ou "
        "désinstallez-le s'il ne sert plus.",
        "Quit Overwolf from its tray icon, or uninstall it if you no longer "
        "use it.",
    ),
    "gamebarftserver.exe": (
        "overlay_gamebar",
        "Xbox Game Bar",
        "Désactivez-la dans Paramètres Windows > Jeux > Game Bar.",
        "Turn it off in Windows Settings > Gaming > Game Bar.",
    ),
    "gamebar.exe": (
        "overlay_gamebar",
        "Xbox Game Bar",
        "Désactivez-la dans Paramètres Windows > Jeux > Game Bar.",
        "Turn it off in Windows Settings > Gaming > Game Bar.",
    ),
    "medal.exe": (
        "overlay_medal",
        "Medal",
        "Quittez Medal depuis son icône de la zone de notification quand "
        "vous n'enregistrez pas vos parties.",
        "Quit Medal from its tray icon when you are not recording clips.",
    ),
}


def _creation_flags() -> int:
    """Drapeaux subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _insight(insight_id: str, severity: str, title: str, title_en: str,
             detail: str, detail_en: str, action_url: str | None = None) -> dict:
    """Construit un constat au format commun de :func:`get_insights`."""
    return {
        "id": insight_id,
        "severity": severity,
        "title": title,
        "title_en": title_en,
        "detail": detail,
        "detail_en": detail_en,
        "action_url": action_url,
    }


# ---------------------------------------------------------------------------
# a) Écran configuré sous sa vraie fréquence (ctypes user32)
# ---------------------------------------------------------------------------

class _POINTL(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _DEVMODEW(ctypes.Structure):
    """Structure DEVMODEW (champs affichage) pour EnumDisplaySettingsW."""

    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort),
        ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort),
        ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_ulong),
        ("dmPosition", _POINTL),
        ("dmDisplayOrientation", ctypes.c_ulong),
        ("dmDisplayFixedOutput", ctypes.c_ulong),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort),
        ("dmBitsPerPel", ctypes.c_ulong),
        ("dmPelsWidth", ctypes.c_ulong),
        ("dmPelsHeight", ctypes.c_ulong),
        ("dmDisplayFlags", ctypes.c_ulong),
        ("dmDisplayFrequency", ctypes.c_ulong),
        ("dmICMMethod", ctypes.c_ulong),
        ("dmICMIntent", ctypes.c_ulong),
        ("dmMediaType", ctypes.c_ulong),
        ("dmDitherType", ctypes.c_ulong),
        ("dmReserved1", ctypes.c_ulong),
        ("dmReserved2", ctypes.c_ulong),
        ("dmPanningWidth", ctypes.c_ulong),
        ("dmPanningHeight", ctypes.c_ulong),
    ]


class _DISPLAY_DEVICEW(ctypes.Structure):
    """Structure DISPLAY_DEVICEW pour EnumDisplayDevicesW."""

    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", ctypes.c_ulong),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


def _max_frequency_at(user32: ctypes.WinDLL, device_name: str,  # type: ignore[name-defined]
                      width: int, height: int) -> int:
    """Fréquence maximale (Hz) supportée par l'écran à la résolution donnée."""
    best = 0
    mode_index = 0
    devmode = _DEVMODEW()
    while True:
        ctypes.memset(ctypes.byref(devmode), 0, ctypes.sizeof(devmode))
        devmode.dmSize = ctypes.sizeof(devmode)
        if not user32.EnumDisplaySettingsW(device_name, mode_index,
                                           ctypes.byref(devmode)):
            break
        mode_index += 1
        if mode_index > 10000:  # garde-fou contre une énumération sans fin
            break
        if (int(devmode.dmPelsWidth) == width
                and int(devmode.dmPelsHeight) == height
                and int(devmode.dmDisplayFrequency) > best):
            best = int(devmode.dmDisplayFrequency)
    return best


def _detect_refresh_rate() -> list[dict]:
    """Écrans actifs réglés sous leur fréquence maximale (severity important)."""
    insights: list[dict] = []
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    screen_number = 0
    device_index = 0
    while device_index < 32:  # nombre d'adaptateurs raisonnable
        device = _DISPLAY_DEVICEW()
        device.cb = ctypes.sizeof(device)
        if not user32.EnumDisplayDevicesW(None, device_index,
                                          ctypes.byref(device), 0):
            break
        device_index += 1
        flags = int(device.StateFlags)
        if not flags & _DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            continue
        if flags & _DISPLAY_DEVICE_MIRRORING_DRIVER:
            continue
        screen_number += 1

        current = _DEVMODEW()
        current.dmSize = ctypes.sizeof(current)
        if not user32.EnumDisplaySettingsW(device.DeviceName,
                                           _ENUM_CURRENT_SETTINGS,
                                           ctypes.byref(current)):
            continue
        width = int(current.dmPelsWidth)
        height = int(current.dmPelsHeight)
        hz_now = int(current.dmDisplayFrequency)
        if hz_now <= 1 or width <= 0 or height <= 0:
            continue  # fréquence « matérielle par défaut » : indéterminable

        hz_max = _max_frequency_at(user32, device.DeviceName, width, height)
        if hz_max > hz_now:
            insights.append(_insight(
                f"display_refresh_{screen_number}",
                "important",
                f"Écran {screen_number} : fréquence de rafraîchissement "
                f"sous-exploitée",
                f"Display {screen_number}: refresh rate not fully used",
                f"Écran {screen_number} : {hz_now} Hz alors qu'il supporte "
                f"{hz_max} Hz à cette résolution ({width}×{height}). Vous "
                f"perdez de la fluidité gratuitement. Pour corriger : "
                f"Paramètres > Système > Affichage > Affichage avancé > "
                f"Choisir une fréquence d'actualisation, puis sélectionnez "
                f"{hz_max} Hz.",
                f"Display {screen_number}: running at {hz_now} Hz while it "
                f"supports {hz_max} Hz at this resolution ({width}×{height}). "
                f"You are losing smoothness for free. To fix it: Settings > "
                f"System > Display > Advanced display > Choose a refresh "
                f"rate, then pick {hz_max} Hz.",
            ))
    return insights


# ---------------------------------------------------------------------------
# b) Overlays actifs qui coûtent des FPS (psutil)
# ---------------------------------------------------------------------------

def _detect_overlays() -> list[dict]:
    """Overlays gourmands détectés parmi les processus (severity conseil)."""
    import psutil  # noqa: PLC0415 — import tardif pour un module léger

    running: set[str] = set()
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name")
        except Exception:
            continue
        if name:
            running.add(str(name).lower())

    insights: list[dict] = []
    seen_ids: set[str] = set()
    for proc_name, (insight_id, label, howto, howto_en) in _OVERLAYS.items():
        if proc_name not in running or insight_id in seen_ids:
            continue
        seen_ids.add(insight_id)
        insights.append(_insight(
            insight_id,
            "conseil",
            f"Overlay actif : {label}",
            f"Active overlay: {label}",
            f"{label} tourne en arrière-plan et dessine par-dessus vos jeux, "
            f"ce qui coûte quelques FPS et peut créer des micro-saccades. "
            f"{howto}",
            f"{label} is running in the background and draws on top of your "
            f"games, which costs a few FPS and can cause micro-stutter. "
            f"{howto_en}",
        ))
    return insights


# ---------------------------------------------------------------------------
# c) Pilote graphique ancien (CIM Win32_VideoController)
# ---------------------------------------------------------------------------

def _parse_driver_date(value: object) -> datetime | None:
    """Date de pilote depuis le JSON PowerShell (``yyyy-MM-dd`` ou /Date(ms)/)."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    match = re.search(r"/Date\((\d+)\)/", text)
    if match:
        try:
            return datetime.fromtimestamp(int(match.group(1)) / 1000.0,
                                          tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    return None


def _driver_url_for(gpu_name: str) -> str | None:
    """Page officielle de téléchargement selon la marque détectée dans le nom."""
    lowered = gpu_name.lower()
    for marker, url in _DRIVER_URLS:
        if marker in lowered:
            return url
    return None


def _detect_gpu_driver_age() -> list[dict]:
    """Pilotes graphiques datant de plus de 180 jours (severity conseil)."""
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", _PS_DRIVER_COMMAND],
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
    if not isinstance(data, list):
        return []

    insights: list[dict] = []
    now = datetime.now(timezone.utc)
    index = 0
    for entry in data:
        if not isinstance(entry, dict) or not entry.get("Name"):
            continue
        name = str(entry["Name"]).strip()
        if any(marker in name.lower() for marker in _VIRTUAL_GPU_MARKERS):
            continue
        driver_date = _parse_driver_date(entry.get("DriverDate"))
        if driver_date is None:
            continue
        age_days = (now - driver_date).days
        if age_days <= _DRIVER_MAX_AGE_DAYS:
            continue
        index += 1
        date_str = driver_date.strftime("%d/%m/%Y")
        date_str_en = driver_date.strftime("%Y-%m-%d")
        insights.append(_insight(
            f"gpu_driver_old_{index}",
            "conseil",
            f"Pilote graphique ancien ({name})",
            f"Outdated graphics driver ({name})",
            f"Le pilote de votre {name} date du {date_str}, soit environ "
            f"{age_days} jours. Les nouveaux pilotes apportent souvent des "
            f"gains de FPS et des correctifs pour les jeux récents : "
            f"installez la dernière version depuis le site officiel.",
            f"Your {name} driver dates back to {date_str_en}, about "
            f"{age_days} days old. Newer drivers often bring FPS gains and "
            f"fixes for recent games: install the latest version from the "
            f"official website.",
            action_url=_driver_url_for(name),
        ))
    return insights


# ---------------------------------------------------------------------------
# d) Plan d'alimentation non performant (powercfg)
# ---------------------------------------------------------------------------

def _detect_power_plan() -> list[dict]:
    """Plan Équilibré actif alors qu'un plan performant ferait mieux (conseil)."""
    proc = subprocess.run(
        ["powercfg", "/getactivescheme"],
        shell=False,
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=_creation_flags(),
    )
    if proc.returncode != 0:
        return []
    match = _GUID_RE.search(proc.stdout or "")
    if match is None or match.group(0).lower() != _BALANCED_GUID:
        return []
    return [_insight(
        "power_plan_balanced",
        "conseil",
        "Plan d'alimentation Équilibré actif",
        "Balanced power plan is active",
        "Windows utilise le plan d'alimentation Équilibré, qui bride le "
        "processeur pour économiser l'énergie. Pour jouer, activez un plan "
        "performant depuis la page Optimisations d'Overdrive (tweak « Plan "
        "d'alimentation ») : la bascule se fait en un clic et reste "
        "réversible.",
        "Windows is using the Balanced power plan, which throttles the CPU "
        "to save energy. For gaming, enable a high-performance plan from "
        "Overdrive's Optimizations page (the power plan tweak): it is a "
        "one-click, fully reversible switch.",
        action_url=None,
    )]


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def get_insights() -> list[dict]:
    """Constats intelligents détectés sur la machine (Windows uniquement).

    Chaque détection est best effort et isolée : une panne de l'une
    n'empêche pas les autres. Sous Linux : liste vide. Jamais d'exception.
    """
    if not is_windows():
        return []
    insights: list[dict] = []
    for detector in (_detect_refresh_rate, _detect_overlays,
                     _detect_gpu_driver_age, _detect_power_plan):
        try:
            insights.extend(detector())
        except Exception:  # noqa: BLE001 — chaque détection reste best effort
            continue
    return insights
