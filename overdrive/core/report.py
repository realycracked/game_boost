"""Rapport système texte exportable (matériel, profil, tweaks, jeux, nettoyage).

Chaque section est construite derrière un ``try/except`` avec imports
tardifs : une section en échec affiche « indisponible » mais le rapport
sort toujours. Texte en français, titres soulignés, colonnes alignées.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

_WIDTH = 72
_KEY_WIDTH = 26


def _underline(title: str, char: str = "-") -> str:
    """Titre suivi d'une ligne de soulignement de même longueur."""
    return f"{title}\n{char * len(title)}"


def _kv(key: str, value: object) -> str:
    """Ligne « clé : valeur » alignée sur la largeur de colonne commune."""
    return f"  {key:<{_KEY_WIDTH}}: {value}"


def _safe_section(title: str, builder: Callable[[], str]) -> str:
    """Construit une section ; en cas d'échec, affiche « indisponible »."""
    try:
        body = builder() or "  (vide)"
    except Exception:  # noqa: BLE001 — le rapport doit toujours sortir
        body = "  indisponible"
    return f"{_underline(title)}\n{body}"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _section_header() -> str:
    """En-tête : application, version et date locale."""
    from overdrive import APP_NAME, VERSION

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    title = f"{APP_NAME} {VERSION} — Rapport système"
    return f"{_underline(title, '=')}\nGénéré le {now}."


def _section_hardware() -> str:
    """Matériel complet : OS, CPU, RAM, GPU, disques, réseau."""
    from overdrive.core.hardware import detect_hardware

    hw = detect_hardware()
    lines: list[str] = [_kv("Résumé", hw.get("summary", "inconnu"))]

    os_info = hw.get("os") or {}
    lines.append(_kv("Système", f"{os_info.get('name', '?')} "
                                f"{os_info.get('version', '')} "
                                f"(build {os_info.get('build', '?')})".strip()))

    cpu = hw.get("cpu") or {}
    freq = cpu.get("freq_mhz_max")
    lines.append(_kv("Processeur", cpu.get("name", "inconnu")))
    lines.append(_kv("Cœurs", f"{cpu.get('cores_physical', '?')} physiques / "
                              f"{cpu.get('cores_logical', '?')} logiques"
                              + (f" — {freq} MHz max" if freq else "")))

    ram = hw.get("ram") or {}
    lines.append(_kv("Mémoire vive", f"{ram.get('total_gb', '?')} Go au total, "
                                     f"{ram.get('available_gb', '?')} Go disponibles "
                                     f"({ram.get('used_percent', '?')} % utilisés)"))

    gpus = hw.get("gpus") or []
    if gpus:
        for index, gpu in enumerate(gpus, start=1):
            extra: list[str] = []
            if gpu.get("vram_mb"):
                extra.append(f"{gpu['vram_mb']} Mo VRAM")
            if gpu.get("driver"):
                extra.append(f"pilote {gpu['driver']}")
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(_kv(f"GPU {index}", f"{gpu.get('name', 'inconnu')}{suffix}"))
    else:
        lines.append(_kv("GPU", "non détecté"))

    disks = hw.get("disks") or []
    for disk in disks:
        lines.append(_kv(f"Disque {disk.get('mountpoint', '?')}",
                         f"{disk.get('free_gb', '?')} Go libres / "
                         f"{disk.get('total_gb', '?')} Go ({disk.get('fstype', '?')})"))
    if not disks:
        lines.append(_kv("Disques", "non détectés"))

    network = hw.get("network") or {}
    lines.append(_kv("Nom d'hôte", network.get("hostname", "inconnu")))
    fast = [i for i in network.get("interfaces", []) if i.get("speed_mbps")]
    if fast:
        pretty = ", ".join(f"{i['name']} ({i['speed_mbps']} Mb/s)" for i in fast[:4])
        lines.append(_kv("Interfaces réseau", pretty))
    return "\n".join(lines)


def _section_profile() -> str:
    """Profil issu du questionnaire et notes personnalisées."""
    from overdrive.store import get_settings

    profile = get_settings().get("profile")
    if not isinstance(profile, dict):
        return "  Aucun profil : le questionnaire n'a pas encore été effectué."
    lines = [
        _kv("Profil", f"{profile.get('label', '?')} ({profile.get('id', '?')})"),
        _kv("Description", profile.get("description", "")),
        _kv("Risque maximal accepté", profile.get("risk_max", "?")),
        _kv("Tweaks recommandés", len(profile.get("recommended_tweaks") or [])),
    ]
    notes = profile.get("notes") or []
    if notes:
        lines.append("  Notes personnalisées :")
        lines.extend(f"    - {note}" for note in notes)
    return "\n".join(lines)


def _section_tweaks() -> str:
    """Optimisations : appliquées via Overdrive, détectées actives, par catégorie."""
    from overdrive.core.tweaks.catalog import CATEGORIES
    from overdrive.core.tweaks.engine import list_tweaks

    tweaks = list_tweaks()
    tracked = [t for t in tweaks if t.get("tracked")]
    active = [t for t in tweaks if t.get("applied") is True]
    lines = [
        _kv("Tweaks au catalogue", len(tweaks)),
        _kv("Appliqués via Overdrive", len(tracked)),
        _kv("Détectés actifs", len(active)),
        "",
    ]
    by_category: dict[str, list[dict]] = {}
    for tweak in tweaks:
        by_category.setdefault(str(tweak.get("category", "")), []).append(tweak)
    for category in CATEGORIES:
        entries = by_category.get(category["id"], [])
        if not entries:
            continue
        done = [t for t in entries if t.get("tracked") or t.get("applied") is True]
        lines.append(f"  {category['label']} — {len(done)}/{len(entries)} en place")
        for tweak in done:
            marks: list[str] = []
            if tweak.get("tracked"):
                marks.append("via Overdrive")
            if tweak.get("applied") is True:
                marks.append("actif")
            lines.append(f"    - {tweak.get('name', tweak.get('id', '?'))}"
                         f" ({', '.join(marks)})")
    return "\n".join(lines)


def _section_games() -> str:
    """Jeux détectés avec chemins et options de lancement recommandées."""
    from overdrive.core.games.detect import detect_games

    games = detect_games()
    installed = [g for g in games if g.get("installed")]
    lines = [_kv("Jeux détectés", f"{len(installed)}/{len(games)}")]
    for game in installed:
        via = game.get("detected_via") or "?"
        lines.append(f"  - {game.get('name', '?')} [{via}] : "
                     f"{game.get('install_path') or 'chemin inconnu'}")
    if not installed:
        lines.append("  Aucun jeu du catalogue n'a été détecté sur cette machine.")
    with_options = [g for g in (installed or games) if g.get("launch_options")]
    if with_options:
        lines.append("")
        lines.append("  Options de lancement recommandées :")
        for game in with_options:
            lines.append(f"    - {game.get('name', '?')} : {game['launch_options']}")
    return "\n".join(lines)


def _section_cleaning() -> str:
    """Cibles de nettoyage et tailles actuelles."""
    from overdrive.core.cleaner import scan

    targets = scan()
    if not targets:
        return "  Aucune cible de nettoyage détectée."
    lines: list[str] = []
    total = 0.0
    for target in targets:
        size = float(target.get("size_mb") or 0.0)
        total += size
        lines.append(_kv(target.get("name", target.get("id", "?")),
                         f"{size:.1f} Mo — {target.get('files', 0)} fichier(s)"))
    lines.append(_kv("Total récupérable", f"{total:.1f} Mo"))
    return "\n".join(lines)


def _section_programs() -> str:
    """Programmes recommandés installables (winget ou site officiel)."""
    from overdrive.core.programs import PROGRAMS, winget_available

    winget = winget_available()
    lines = [_kv("Installation via winget",
                 "disponible" if winget else "indisponible (liens site officiel)")]
    for program in PROGRAMS:
        source = program.get("winget_id") or program.get("url") or ""
        lines.append(f"  - {program.get('name', '?')} ({source})")
        lines.append(f"      {program.get('description', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def build_report() -> str:
    """Construit le rapport système complet (texte français, toujours rendu)."""
    try:
        header = _section_header()
    except Exception:  # noqa: BLE001 — même l'en-tête ne doit pas bloquer
        header = _underline("Overdrive — Rapport système", "=")
    sections = [
        header,
        _safe_section("Matériel", _section_hardware),
        _safe_section("Profil du questionnaire", _section_profile),
        _safe_section("Optimisations", _section_tweaks),
        _safe_section("Jeux", _section_games),
        _safe_section("Nettoyage", _section_cleaning),
        _safe_section("Programmes recommandés", _section_programs),
    ]
    return "\n\n".join(sections) + "\n"


def report_filename() -> str:
    """Nom de fichier horodaté : ``overdrive-rapport-AAAAMMJJ-HHMM.txt``."""
    return datetime.now().strftime("overdrive-rapport-%Y%m%d-%H%M.txt")
