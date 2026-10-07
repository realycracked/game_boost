"""Catalogue de programmes recommandés pour un PC gaming et installation via winget."""

from __future__ import annotations

import shutil
import subprocess

from overdrive.paths import is_windows

PROGRAMS: list[dict] = [
    {
        "id": "msi_afterburner",
        "name": "MSI Afterburner",
        "description": "Overclocking et undervolting du GPU avec affichage des FPS et températures en jeu.",
        "category": "monitoring",
        "url": "https://www.msi.com/Landing/afterburner",
        "winget_id": "Guru3D.Afterburner",
    },
    {
        "id": "hwinfo64",
        "name": "HWiNFO64",
        "description": "Surveillance très détaillée des capteurs (températures, tensions, fréquences) pour diagnostiquer throttling et surchauffe.",
        "category": "monitoring",
        "url": "https://www.hwinfo.com",
        "winget_id": "REALiX.HWiNFO",
    },
    {
        "id": "ddu",
        "name": "Display Driver Uninstaller (DDU)",
        "description": "Désinstallation propre des pilotes graphiques avant une réinstallation, pour repartir sur une base saine.",
        "category": "pilotes",
        "url": "https://www.wagnardsoft.com",
        "winget_id": "Wagnardsoft.DisplayDriverUninstaller",
    },
    {
        "id": "process_lasso",
        "name": "Process Lasso",
        "description": "Gestion automatique des priorités et affinités CPU pour garder les jeux réactifs même avec des applications en fond.",
        "category": "utilitaire",
        "url": "https://bitsum.com",
        "winget_id": "BitSum.ProcessLasso",
    },
    {
        "id": "latencymon",
        "name": "LatencyMon",
        "description": "Analyse des latences DPC/ISR pour identifier les pilotes qui provoquent micro-saccades et craquements audio.",
        "category": "monitoring",
        "url": "https://www.resplendence.com/latencymon",
        "winget_id": "Resplendence.LatencyMon",
    },
    {
        "id": "capframex",
        "name": "CapFrameX",
        "description": "Capture et analyse des frametimes pour mesurer objectivement l'effet de vos optimisations sur la fluidité.",
        "category": "monitoring",
        "url": "https://www.capframex.com",
        "winget_id": "CXWorld.CapFrameX",
    },
    {
        "id": "obs_studio",
        "name": "OBS Studio",
        "description": "Référence gratuite pour enregistrer et streamer ses parties avec encodage GPU peu coûteux en performances.",
        "category": "capture",
        "url": "https://obsproject.com",
        "winget_id": "OBSProject.OBSStudio",
    },
    {
        "id": "discord",
        "name": "Discord",
        "description": "Vocal et messagerie incontournables pour jouer en équipe et rejoindre les communautés de vos jeux.",
        "category": "communication",
        "url": "https://discord.com",
        "winget_id": "Discord.Discord",
    },
    {
        "id": "7zip",
        "name": "7-Zip",
        "description": "Archiveur gratuit et rapide pour décompresser mods, packs de textures et outils téléchargés.",
        "category": "utilitaire",
        "url": "https://www.7-zip.org",
        "winget_id": "7zip.7zip",
    },
    {
        "id": "crystaldiskinfo",
        "name": "CrystalDiskInfo",
        "description": "Surveillance de la santé des SSD/HDD (S.M.A.R.T.) pour anticiper une panne avant de perdre ses sauvegardes.",
        "category": "monitoring",
        "url": "https://crystalmark.info",
        "winget_id": "CrystalDewWorld.CrystalDiskInfo",
    },
    {
        "id": "steam",
        "name": "Steam",
        "description": "Plateforme de jeux la plus répandue, nécessaire pour la majorité des titres PC et leurs options de lancement.",
        "category": "utilitaire",
        "url": "https://store.steampowered.com",
        "winget_id": "Valve.Steam",
    },
    {
        "id": "eartrumpet",
        "name": "EarTrumpet",
        "description": "Réglage du volume par application depuis la barre des tâches, pratique pour équilibrer jeu, vocal et musique.",
        "category": "utilitaire",
        "url": "https://eartrumpet.app",
        "winget_id": "File-New-Project.EarTrumpet",
    },
]


def winget_available() -> bool:
    """Indique si winget est utilisable sur cette machine."""
    return is_windows() and shutil.which("winget") is not None


def install_program(program_id: str) -> dict:
    """Installe un programme du catalogue via winget (Windows uniquement)."""
    program = next((p for p in PROGRAMS if p["id"] == program_id), None)
    if program is None:
        return {"ok": False, "message": f"Programme inconnu : {program_id}"}
    if not is_windows():
        return {"ok": False, "message": "Installation disponible uniquement sous Windows."}
    if not program.get("winget_id"):
        return {"ok": False, "message": f"{program['name']} n'est pas disponible via winget."}
    if not winget_available():
        return {"ok": False, "message": "winget n'est pas disponible sur cette machine."}

    args = [
        "winget",
        "install",
        "--id",
        program["winget_id"],
        "-e",
        "--accept-source-agreements",
        "--accept-package-agreements",
    ]
    try:
        proc = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": f"Installation de {program['name']} interrompue : délai de 10 minutes dépassé."}
    except Exception as exc:  # pragma: no cover — dépend de l'environnement
        return {"ok": False, "message": f"Échec du lancement de winget : {exc}"}

    if proc.returncode == 0:
        return {"ok": True, "message": f"{program['name']} installé avec succès."}
    detail = (proc.stdout or proc.stderr or "").strip().splitlines()
    last = detail[-1] if detail else f"code {proc.returncode}"
    return {"ok": False, "message": f"Échec de l'installation de {program['name']} : {last}"}


# ---------------------------------------------------------------------------
# i18n — champ anglais additif (« description_en »), injecté dans PROGRAMS au
# chargement du module sans modifier aucune valeur existante.
# ---------------------------------------------------------------------------

# {id du programme: description_en}
_PROGRAMS_EN: dict[str, str] = {
    "msi_afterburner": (
        "GPU overclocking and undervolting with an in-game FPS and "
        "temperature overlay."
    ),
    "hwinfo64": (
        "Highly detailed sensor monitoring (temperatures, voltages, clocks) "
        "to diagnose throttling and overheating."
    ),
    "ddu": (
        "Clean removal of graphics drivers before a reinstall, to start over "
        "from a healthy base."
    ),
    "process_lasso": (
        "Automatic CPU priority and affinity management to keep games "
        "responsive even with applications running in the background."
    ),
    "latencymon": (
        "DPC/ISR latency analysis to pinpoint the drivers causing "
        "micro-stutter and audio crackling."
    ),
    "capframex": (
        "Frametime capture and analysis to measure objectively how your "
        "optimizations affect smoothness."
    ),
    "obs_studio": (
        "The free reference for recording and streaming your games, with GPU "
        "encoding that barely costs any performance."
    ),
    "discord": (
        "The essential voice chat and messaging app for playing as a team "
        "and joining your games' communities."
    ),
    "7zip": (
        "A free, fast archiver to extract mods, texture packs and downloaded "
        "tools."
    ),
    "crystaldiskinfo": (
        "SSD/HDD health monitoring (S.M.A.R.T.) to anticipate a failure "
        "before you lose your saves."
    ),
    "steam": (
        "The most widespread gaming platform, required for most PC titles "
        "and their launch options."
    ),
    "eartrumpet": (
        "Per-application volume control from the taskbar, handy for "
        "balancing game, voice chat and music."
    ),
}

for _program in PROGRAMS:
    _program["description_en"] = _PROGRAMS_EN.get(
        _program["id"], _program["description"])
