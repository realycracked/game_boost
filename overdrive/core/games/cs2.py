"""Outils Counter-Strike 2 : tiers matériels, plan vidéo par tier, autoexec et launch options.

Réponse au retour utilisateur « petites configs mal servies » : les
recommandations (vidéo, autoexec, options de lancement) sont désormais
différenciées en trois tiers (``lowend`` / ``midrange`` / ``highend``)
détectés depuis :func:`overdrive.core.hardware.detect_hardware`.

Principe cardinal du plan vidéo : le catalogue ci-dessous sert à
*proposer*, le ``cs2_video.txt`` du joueur sert de *contrat* —
:func:`apply_video_settings` ne modifie **que** les clés effectivement
présentes dans son fichier et n'en ajoute jamais. Toute écriture est
précédée d'une sauvegarde du coffre (:func:`overdrive.core.configvault.backup`)
et refusée si CS2 tourne. Aucune fonction publique ne lève d'exception ;
sous Linux, tout se termine en refus propre ou en valeur neutre.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import psutil

from ...paths import is_windows
from ..amd import gpu_arch
from ..configvault import backup as _vault_backup
from ..hardware import detect_hardware
from ..latency import measure as _measure_latency
from .catalog import get_game
from .detect import find_steam_root, parse_vdf, steam_game_path

CS2_APPID = 730

#: Tiers matériels reconnus, du plus modeste au plus performant.
TIERS: tuple[str, ...] = ("lowend", "midrange", "highend")

_TIER_LABELS: dict[str, tuple[str, str]] = {
    "lowend": ("Petite config", "Low-end machine"),
    "midrange": ("Milieu de gamme", "Mid-range machine"),
    "highend": ("Haut de gamme", "High-end machine"),
}

# ---------------------------------------------------------------------------
# Plan vidéo par tier (cs2_video.txt)
# ---------------------------------------------------------------------------
# Remplace l'ancien _VIDEO_RECOMMENDATIONS (valeurs uniques, clés non
# validées). Trois niveaux de confiance :
#   - "confirmee" : clés observées dans des cs2_video.txt réels, stables ;
#   - "probable"  : orthographe plausible, appliquée seulement si présente ;
#   - "a_relever" : clé inconnue — les anciennes clés setting.videocfg_*
#     (jamais validées contre un vrai fichier) sont reléguées ici comme
#     simples candidates ; si aucune candidate n'est dans le fichier du
#     joueur, le réglage est affiché comme « réglage menu » sans écriture.
# "keys" : la PREMIÈRE clé trouvée dans le fichier du joueur est utilisée.
# "tiers" : valeur cible par tier (None = jamais écrite automatiquement).
# "dynamic" : résolution à l'exécution (refresh_hz / gpu_mem / cpu_mem /
# reflex). "protected" : affiché mais jamais modifié (choix personnel).
#
# Réglage « coop_fullscreen » volontairement absent : aucun intérêt
# compétitif, inutile d'encombrer le panneau.
_VIDEO_PLAN: list[dict] = [
    {
        "id": "resolution",
        "label": "Résolution",
        "label_en": "Resolution",
        "keys": ["setting.defaultres", "setting.defaultresheight"],
        "tiers": None,
        "confidence": "confirmee",
        "menu_path": "Vidéo > Résolution",
        "menu_path_en": "Video > Resolution",
        "note": ("Choix personnel (natif vs 4:3 étiré) : affichée, jamais "
                 "modifiée automatiquement par Overdrive."),
        "note_en": ("Personal choice (native vs stretched 4:3): shown, never "
                    "changed automatically by Overdrive."),
        "dynamic": None,
        "protected": True,
    },
    {
        "id": "aspect_ratio",
        "label": "Format d'image",
        "label_en": "Aspect ratio",
        "keys": ["setting.aspectratiomode"],
        "tiers": None,
        "confidence": "confirmee",
        "menu_path": "Vidéo > Format de l'image",
        "menu_path_en": "Video > Aspect ratio",
        "note": "Lié au choix résolution/étiré : jamais modifié automatiquement.",
        "note_en": "Tied to the resolution/stretched choice: never changed automatically.",
        "dynamic": None,
        "protected": True,
    },
    {
        "id": "hud_scale",
        "label": "Échelle du HUD",
        "label_en": "HUD scale",
        "keys": ["setting.hudscaling"],
        "tiers": None,
        "confidence": "confirmee",
        "menu_path": "Jeu > HUD > Échelle du HUD",
        "menu_path_en": "Game > HUD > HUD scale",
        "note": "Préférence personnelle : jamais modifiée automatiquement.",
        "note_en": "Personal preference: never changed automatically.",
        "dynamic": None,
        "protected": True,
    },
    {
        "id": "fullscreen",
        "label": "Mode d'affichage",
        "label_en": "Display mode",
        "keys": ["setting.fullscreen"],
        "tiers": {"lowend": "1", "midrange": "1", "highend": "1"},
        "confidence": "confirmee",
        "menu_path": "Vidéo > Mode d'affichage : Plein écran",
        "menu_path_en": "Video > Display mode: Fullscreen",
        "note": "Plein écran exclusif : latence minimale.",
        "note_en": "Exclusive fullscreen: minimal latency.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "window_border",
        "label": "Sans bordure",
        "label_en": "Borderless",
        "keys": ["setting.nowindowborder"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "confirmee",
        "menu_path": "Vidéo > Mode d'affichage : Plein écran",
        "menu_path_en": "Video > Display mode: Fullscreen",
        "note": ("Cohérent avec le plein écran exclusif (fenêtré sans bordure "
                 "= fullscreen 0 + nowindowborder 1, à éviter)."),
        "note_en": ("Consistent with exclusive fullscreen (borderless = "
                    "fullscreen 0 + nowindowborder 1, to avoid)."),
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "refresh_rate",
        "label": "Fréquence d'actualisation",
        "label_en": "Refresh rate",
        "keys": ["setting.refreshrate_numerator"],
        "tiers": None,  # résolu dynamiquement (Hz max de l'écran principal)
        "confidence": "confirmee",
        "menu_path": "Vidéo > Fréquence d'actualisation : maximum de l'écran",
        "menu_path_en": "Video > Refresh rate: your monitor's maximum",
        "note": ("Caler le jeu sur le Hz maximal de l'écran (numérateur ; le "
                 "dénominateur est laissé à 1)."),
        "note_en": ("Match the game to the monitor's maximum Hz (numerator; "
                    "the denominator is left at 1)."),
        "dynamic": "refresh_hz",
        "protected": False,
    },
    {
        "id": "shader_quality",
        "label": "Détail des shaders",
        "label_en": "Shader detail",
        "keys": ["setting.shaderquality", "setting.videocfg_shader_detail"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "confirmee",
        "menu_path": "Vidéo avancé > Détail des shaders : Faible",
        "menu_path_en": "Advanced video > Shader detail: Low",
        "note": ("Faible même en haut de gamme : gros gain dans les fumées, "
                 "les joueurs professionnels jouent Faible."),
        "note_en": ("Low even on high-end machines: a big gain in smokes, "
                    "professional players run Low."),
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "msaa",
        "label": "Anticrénelage MSAA",
        "label_en": "MSAA anti-aliasing",
        "keys": ["setting.msaa_samples"],
        # Petite config (vague 6, plan « au plus bas utile ») : MSAA coupé,
        # chaque image compte ; 2x dès le milieu de gamme.
        "tiers": {"lowend": "0", "midrange": "2", "highend": "4"},
        "confidence": "confirmee",
        "menu_path": "Vidéo avancé > Mode d'anticrénelage",
        "menu_path_en": "Advanced video > Anti-aliasing mode",
        # Correction de l'ancienne note : CMAA2 n'est PAS msaa_samples 2.
        # Un joueur en CMAA2 a msaa_samples "1" : choix valide en petite
        # config, on ne « recommande pas mieux » dans ce cas.
        "note": ("Petite config : aucun MSAA (le plus rapide). MSAA 2x = "
                 "compromis FPS/netteté dès le milieu de gamme ; 4x en haut "
                 "de gamme (lisibilité à longue distance). CMAA2 est un mode "
                 "distinct (msaa_samples vaut alors 1) : valide sur petite "
                 "config, conservé tel quel."),
        "note_en": ("Low-end machine: no MSAA (fastest). MSAA 2x = FPS/clarity "
                    "trade-off from mid-range up; 4x on high-end machines "
                    "(long-range readability). CMAA2 is a separate mode "
                    "(msaa_samples then reads 1): valid on low-end machines, "
                    "kept as-is."),
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "gpu_mem",
        "label": "Détail des modèles/textures (part GPU)",
        "label_en": "Model/texture detail (GPU share)",
        "keys": ["setting.gpu_mem_level", "setting.videocfg_texture_detail"],
        "tiers": {"lowend": "0", "midrange": "1", "highend": "2"},
        "confidence": "probable",
        "menu_path": "Vidéo avancé > Détail des modèles et des textures",
        "menu_path_en": "Advanced video > Model / texture detail",
        "note": ("Selon la VRAM détectée : un débordement de VRAM = des "
                 "saccades. Milieu de gamme sous 6 Go de VRAM : rester à 0."),
        "note_en": ("Based on detected VRAM: VRAM overflow = stutters. "
                    "Mid-range below 6 GB of VRAM: stay at 0."),
        "dynamic": "gpu_mem",
        "protected": False,
    },
    {
        "id": "cpu_mem",
        "label": "Détail des modèles/textures (part CPU/RAM)",
        "label_en": "Model/texture detail (CPU/RAM share)",
        "keys": ["setting.cpu_mem_level"],
        "tiers": {"lowend": "0", "midrange": "1", "highend": "2"},
        "confidence": "probable",
        "menu_path": "Vidéo avancé > Détail des modèles et des textures",
        "menu_path_en": "Advanced video > Model / texture detail",
        "note": "Selon la RAM : 0 sous 12 Go pour éviter la pagination.",
        "note_en": "Based on RAM: 0 below 12 GB to avoid paging.",
        "dynamic": "cpu_mem",
        "protected": False,
    },
    {
        "id": "aniso",
        "label": "Filtrage anisotrope",
        "label_en": "Anisotropic filtering",
        "keys": ["setting.r_texturefilteringquality"],
        "tiers": {"lowend": "2", "midrange": "4", "highend": "5"},
        "confidence": "probable",
        "menu_path": "Vidéo avancé > Mode de filtrage des textures",
        "menu_path_en": "Advanced video > Texture filtering mode",
        "note": ("Coût quasi nul dès le milieu de gamme, image plus nette au "
                 "sol et dans les angles (échelle 0-5 à confirmer au relevé)."),
        "note_en": ("Near-zero cost from mid-range up, sharper image on floors "
                    "and angles (0-5 scale to confirm from a real file)."),
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "reflex",
        "label": "NVIDIA Reflex",
        "label_en": "NVIDIA Reflex",
        "keys": ["setting.r_low_latency"],
        "tiers": {"lowend": "1", "midrange": "1", "highend": "2"},
        "confidence": "probable",
        "menu_path": "Vidéo avancé > NVIDIA Reflex Low Latency",
        "menu_path_en": "Advanced video > NVIDIA Reflex Low Latency",
        # Jamais écrit sur GPU AMD/Intel (résolution dynamique "reflex").
        "note": ("Réduit la latence système quand le GPU sature ; 2 = + Boost, "
                 "surtout utile en haut de gamme. GPU NVIDIA uniquement."),
        "note_en": ("Cuts system latency when the GPU is saturated; 2 = + "
                    "Boost, mostly useful on high-end machines. NVIDIA GPUs "
                    "only."),
        "dynamic": "reflex",
        "protected": False,
    },
    {
        "id": "shadows",
        "label": "Qualité des ombres globales",
        "label_en": "Global shadow quality",
        "keys": ["setting.videocfg_shadow_quality"],
        "tiers": {"lowend": "1", "midrange": "1", "highend": "1"},
        "confidence": "a_relever",
        "menu_path": "Vidéo avancé > Qualité des ombres globales : Faible",
        "menu_path_en": "Advanced video > Global shadow quality: Low",
        "note": ("Faible, jamais coupées : les ombres sont une information de "
                 "jeu."),
        "note_en": "Low, never off: shadows are game information.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "particles",
        "label": "Détail des particules",
        "label_en": "Particle detail",
        "keys": ["setting.videocfg_particle_detail"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "a_relever",
        "menu_path": "Vidéo avancé > Détail des particules : Faible",
        "menu_path_en": "Advanced video > Particle detail: Low",
        "note": "Faible : FPS stables en combat.",
        "note_en": "Low: steady FPS in fights.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "ambient_occlusion",
        "label": "Occlusion ambiante",
        "label_en": "Ambient occlusion",
        "keys": ["setting.videocfg_ao"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "a_relever",
        "menu_path": "Vidéo avancé > Occlusion ambiante : Désactivée",
        "menu_path_en": "Advanced video > Ambient occlusion: Disabled",
        "note": "Coût GPU élevé, apport nul en compétitif.",
        "note_en": "High GPU cost, no competitive benefit.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "hdr",
        "label": "Qualité HDR",
        "label_en": "HDR quality",
        "keys": ["setting.videocfg_hdr"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "a_relever",
        "menu_path": "Vidéo avancé > Qualité HDR : Performance",
        "menu_path_en": "Advanced video > HDR quality: Performance",
        "note": "Performance : aucun intérêt compétitif au-delà.",
        "note_en": "Performance: no competitive benefit beyond that.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "fsr",
        "label": "Super-résolution (FSR)",
        "label_en": "Super resolution (FSR)",
        "keys": ["setting.videocfg_fsr"],
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "a_relever",
        "menu_path": "Vidéo avancé > FidelityFX Super Resolution : Désactivé",
        "menu_path_en": "Advanced video > FidelityFX Super Resolution: Disabled",
        "note": "Désactivé (natif) : l'upscaling floute les silhouettes.",
        "note_en": "Disabled (native): upscaling blurs silhouettes.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "contrast_boost",
        "label": "Boost du contraste des joueurs",
        "label_en": "Boost player contrast",
        "keys": [],  # clé inconnue : aucune candidate fiable, menu uniquement
        "tiers": {"lowend": "1", "midrange": "1", "highend": "1"},
        "confidence": "a_relever",
        "menu_path": "Vidéo > Boost du contraste des joueurs : Activé",
        "menu_path_en": "Video > Boost player contrast: Enabled",
        "note": "Activé : silhouettes plus lisibles. Réglez-le dans le menu CS2.",
        "note_en": "Enabled: more readable silhouettes. Set it in the CS2 menu.",
        "dynamic": None,
        "protected": False,
    },
    {
        "id": "vsync",
        "label": "Synchronisation verticale",
        "label_en": "V-Sync",
        "keys": [],  # clé exacte inconnue : ne pas deviner « mat_vsync »
        "tiers": {"lowend": "0", "midrange": "0", "highend": "0"},
        "confidence": "a_relever",
        "menu_path": "Vidéo > Attente de la synchronisation verticale : Désactivée",
        "menu_path_en": "Video > Wait for vertical sync: Disabled",
        "note": "Désactivée : la V-Sync ajoute une latence d'entrée.",
        "note_en": "Disabled: V-Sync adds input latency.",
        "dynamic": None,
        "protected": False,
    },
]

# Options de lancement par tier : repli local si le catalogue est incomplet.
# Le cap FPS vit dans l'autoexec (une seule source de vérité), plus ici.
_LAUNCH_TIERS_FALLBACK: dict[str, str] = {
    "lowend": "-fullscreen -console +exec autoexec.cfg",
    "midrange": "-fullscreen -console -high +exec autoexec.cfg",
    "highend": "-fullscreen -console +exec autoexec.cfg",
}

_LAUNCH_TIERS_NOTE_FALLBACK: dict[str, tuple[str, str]] = {
    "lowend": (
        "Pas de -high : sur 4 cœurs physiques ou moins, la priorité haute "
        "peut affamer le thread audio et les services système (saccades, "
        "crachotements). Le cap FPS vit dans l'autoexec.",
        "No -high: on 4 physical cores or fewer, high priority can starve "
        "the audio thread and system services (stutters, crackling). The "
        "FPS cap lives in the autoexec.",
    ),
    "midrange": (
        "-high acceptable dès 6 cœurs : gain faible mais réel quand des "
        "tâches de fond tournent. Le cap FPS vit dans l'autoexec.",
        "-high is fine from 6 cores up: a small but real gain when "
        "background tasks are running. The FPS cap lives in the autoexec.",
    ),
    "highend": (
        "-high superflu (l'ordonnanceur Windows et Reflex suffisent) ; à "
        "tester en option. Le cap FPS vit dans l'autoexec.",
        "-high is unnecessary (the Windows scheduler and Reflex are enough); "
        "worth testing as an option. The FPS cap lives in the autoexec.",
    ),
}

_FALLBACK_LAUNCH_OPTIONS = _LAUNCH_TIERS_FALLBACK["midrange"]

# Bornes des paramètres d'autoexec (hors bornes => ligne commentée).
_FPS_MAX_RANGE = (60, 1000)  # 0 (illimité) également accepté
_MAXPING_RANGE = (25, 350)
_SENSITIVITY_RANGE = (0.0, 10.0)  # borne basse exclusive
_ZOOM_RATIO_RANGE = (0.5, 2.0)

# Cvars envisagés mais volontairement EXCLUS des autoexec générés :
# engine_low_latency_sleep_after_client_tick et cl_hud_telemetry_* —
# noms/effets à re-vérifier sur le build courant avant toute inclusion.
# Jamais expédier un cvar incertain.


# ---------------------------------------------------------------------------
# Détection du tier matériel et des capacités de l'écran
# ---------------------------------------------------------------------------

#: Marqueurs de GPU virtuels à ignorer (aligné sur hardware.py).
_VIRTUAL_GPU_MARKERS = ("microsoft basic display", "virtual", "remote", "vnc")

#: Marqueurs de puces graphiques intégrées (iGPU/APU).
_IGPU_MARKERS = ("intel(r) hd graphics", "intel hd graphics",
                 "intel(r) uhd graphics", "intel uhd graphics", "iris")

# Planchers / plafonds par nom commercial (la VRAM seule ne suffit pas :
# une RX 580 8 Go n'est pas un GPU haut de gamme).
#   - plancher haut : RTX 40/50, RX 7800-7900 (RDNA 3), RX 9070/9070 XT/
#     9070 GRE (RDNA 4) ;
#   - plancher milieu : RTX 20/30, RX 6600-6950 (RDNA 2), RX 7600-7700
#     (RDNA 3), RX 9060/9060 XT (RDNA 4), Intel Arc A7xx/B5xx ;
#   - plafond milieu : GTX 9xx/10xx/16xx, Polaris RX 4x0/5x0, RX 5300/5500
#     (RDNA 1 d'entrée), RX 6400/6500 (RDNA 2 d'entrée) ;
#   - plafond bas : RX 460/550/560, GT 710/730/1030 (entrée de gamme,
#     VRAM éventuellement inconnue).
_GPU_FLOOR_HIGH_RE = re.compile(r"rtx\s*[45]0\d{2}|rx\s*7[89]\d0|rx\s*90[7-9]0",
                                re.IGNORECASE)
_GPU_FLOOR_MID_RE = re.compile(
    r"rtx\s*[23]0\d{2}|rx\s*6[6-9]\d0|rx\s*7[67]\d0|rx\s*90[0-6]0"
    r"|arc\s*(a7\d{2}|b5\d{2})\b",
    re.IGNORECASE)
_GPU_CAP_MID_RE = re.compile(
    r"gtx\s*(9\d{2}|10\d{2}|16\d{2})|rx\s*[45]\d0\b|rx\s*(5[35]00|6[45]00)\b",
    re.IGNORECASE)
_GPU_CAP_LOW_RE = re.compile(r"\brx\s*(460|550|560)\b|\bgt\s*(7[1-3]0|1030)\b",
                             re.IGNORECASE)
#: Polaris RX 470/570 : très majoritairement en 4 Go ; VRAM inconnue =>
#: classées GPU faible par prudence (une RX 570 reste d'entrée de gamme
#: pour CS2).
_GPU_POLARIS_4GB_LIKELY_RE = re.compile(r"\brx\s*[45]70\b", re.IGNORECASE)
#: VRAM (Mo) jusqu'à laquelle un GPU est classé faible (4 Go inclus : la
#: VRAM registre d'une carte de 4 Go vaut exactement 4096).
_GPU_LOW_VRAM_MAX_MB = 4096
_AMD_APU_RE = re.compile(r"radeon(\(tm\))?\s+(r[2-7]\s+)?graphics$")


def _gpu_vendor(name: str) -> str | None:
    """Marque du GPU d'après son nom : "nvidia" | "amd" | "intel" | None."""
    low = name.lower()
    if any(m in low for m in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        return "nvidia"
    if any(m in low for m in ("amd", "radeon")) or re.search(r"\brx\s*\d", low):
        return "amd"
    if "intel" in low or re.search(r"\barc\s", low):
        return "intel"
    return None


def _is_igpu(name: str) -> bool:
    """Vrai si le nom désigne une puce graphique intégrée (iGPU/APU)."""
    low = name.lower().strip()
    if any(marker in low for marker in _IGPU_MARKERS):
        return True
    if "vega" in low and "graphics" in low:
        return True
    return _AMD_APU_RE.search(low) is not None


def _positive(value: object) -> float | None:
    """Nombre strictement positif, sinon None (booléens exclus)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def detect_tier(hw: dict | None = None) -> dict:
    """Classe la machine pour CS2 en « maillon faible » GPU/CPU/RAM.

    Retour : ``{"tier", "label", "label_en", "reasons", "reasons_en",
    "cpu_strong", "gpu_vendor", "vram_mb", "ram_gb", "gpu_name",
    "gpu_arch"}`` (``gpu_name``/``gpu_arch`` additifs, ``gpu_arch`` =
    :func:`overdrive.core.amd.gpu_arch`). Fonction pure sur le dict de
    :func:`detect_hardware` (``hw=None`` => détection), donc testable sous
    Linux avec des fixtures. VRAM/GPU indéterminables (Linux, AdapterRAM
    saturé) => composant classé ``midrange`` prudent avec raison explicite,
    sauf modèle d'entrée de gamme reconnu par son nom. VRAM <= 4 Go => GPU
    faible. Jamais d'exception.
    """
    fallback = {
        "tier": "midrange",
        "label": _TIER_LABELS["midrange"][0],
        "label_en": _TIER_LABELS["midrange"][1],
        "reasons": ["Détection matérielle en échec : milieu de gamme prudent."],
        "reasons_en": ["Hardware detection failed: cautious mid-range."],
        "cpu_strong": False,
        "gpu_vendor": None,
        "vram_mb": None,
        "ram_gb": None,
        "gpu_name": None,
        "gpu_arch": None,
    }
    try:
        if hw is None:
            hw = detect_hardware()
        if not isinstance(hw, dict):
            return fallback

        cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
        ram = hw.get("ram") if isinstance(hw.get("ram"), dict) else {}
        gpus = hw.get("gpus") if isinstance(hw.get("gpus"), list) else []

        reasons: list[str] = []
        reasons_en: list[str] = []

        # --- GPU : VRAM d'abord, affiné/encadré par le nom commercial. ---
        real_gpus = []
        for gpu in gpus:
            if not isinstance(gpu, dict):
                continue
            name = str(gpu.get("name") or "").strip()
            if not name or any(m in name.lower() for m in _VIRTUAL_GPU_MARKERS):
                continue
            real_gpus.append(gpu)

        gpu_score: int | None = None
        gpu_vendor: str | None = None
        vram_mb: int | None = None
        gpu_name = ""
        gpu_note: tuple[str, str] | None = None
        if real_gpus:
            # GPU dédié prioritaire sur l'iGPU pour la classification.
            chosen = next((g for g in real_gpus
                           if not _is_igpu(str(g.get("name") or ""))),
                          real_gpus[0])
            gpu_name = str(chosen.get("name") or "").strip()
            gpu_vendor = _gpu_vendor(gpu_name)
            vram_raw = _positive(chosen.get("vram_mb"))
            vram_mb = int(vram_raw) if vram_raw is not None else None
            if _is_igpu(gpu_name):
                gpu_score = 0
            elif vram_mb is not None:
                # 4 Go inclus : RX 570 4 Go, GTX 1050 Ti / 1650 4 Go => GPU
                # faible pour CS2 (même classement qu'avec l'ancienne lecture
                # AdapterRAM, qui remontait 4095 Mo pour ces cartes).
                if vram_mb <= _GPU_LOW_VRAM_MAX_MB:
                    gpu_score = 0
                elif vram_mb < 8192:
                    gpu_score = 1
                else:
                    gpu_score = 2
            if _GPU_FLOOR_HIGH_RE.search(gpu_name):
                gpu_score = 2 if gpu_score is None else max(gpu_score, 2)
            elif _GPU_FLOOR_MID_RE.search(gpu_name):
                gpu_score = 1 if gpu_score is None else max(gpu_score, 1)
            elif _GPU_CAP_LOW_RE.search(gpu_name):
                gpu_score = 0
            elif _GPU_CAP_MID_RE.search(gpu_name):
                if vram_mb is None and _GPU_POLARIS_4GB_LIKELY_RE.search(gpu_name):
                    gpu_score = 0
                    gpu_note = ("RX 470/570 à VRAM illisible : classée GPU "
                                "faible par prudence (le plus souvent 4 Go).",
                                "RX 470/570 with unreadable VRAM: cautiously "
                                "classed as a weak GPU (usually 4 GB).")
                else:
                    gpu_score = 1 if gpu_score is None else min(gpu_score, 1)
        if gpu_score is None:
            reasons.append("GPU ou VRAM non identifiables : classé milieu de "
                           "gamme prudent (corrigez le tier à la main si besoin).")
            reasons_en.append("GPU or VRAM not identifiable: cautiously "
                              "classed mid-range (override the tier manually "
                              "if needed).")
            gpu_score = 1
        else:
            vram_txt = f"{vram_mb} Mo de VRAM" if vram_mb else "VRAM inconnue"
            vram_txt_en = f"{vram_mb} MB of VRAM" if vram_mb else "unknown VRAM"
            reasons.append(f"GPU : {gpu_name or 'inconnu'} ({vram_txt}).")
            reasons_en.append(f"GPU: {gpu_name or 'unknown'} ({vram_txt_en}).")
            if gpu_note is not None:
                reasons.append(gpu_note[0])
                reasons_en.append(gpu_note[1])

        # --- CPU : cœurs physiques, modulés par la fréquence maximale. ---
        cores = _positive(cpu.get("cores_physical"))
        if cores is None:
            logical = _positive(cpu.get("cores_logical"))
            if logical is not None:
                cores = float(max(1, int(logical) // 2))
        freq = _positive(cpu.get("freq_mhz_max"))

        cpu_score: int | None = None
        if cores is not None:
            if cores <= 4:
                cpu_score = 0
            elif cores < 8:
                cpu_score = 1
            else:
                cpu_score = 2
            if cpu_score == 2 and freq is not None and freq < 3000:
                cpu_score = 1
            if cpu_score == 1 and freq is not None and freq < 2600:
                cpu_score = 0
            freq_txt = f" à {int(freq)} MHz" if freq else ""
            reasons.append(f"CPU : {int(cores)} cœurs physiques{freq_txt}.")
            reasons_en.append(f"CPU: {int(cores)} physical cores"
                              f"{f' at {int(freq)} MHz' if freq else ''}.")
        else:
            cpu_score = 1
            reasons.append("Cœurs CPU non détectés : milieu de gamme prudent.")
            reasons_en.append("CPU cores not detected: cautious mid-range.")

        # --- RAM : < 12 Go plafonne à lowend, >= 31 Go compatible highend. ---
        ram_gb = _positive(ram.get("total_gb"))
        if ram_gb is not None:
            if ram_gb < 12:
                ram_score = 0
            elif ram_gb < 31:  # 32 Go physiques remontent ~31,8 via psutil
                ram_score = 1
            else:
                ram_score = 2
            reasons.append(f"RAM : {ram_gb:g} Go.")
            reasons_en.append(f"RAM: {ram_gb:g} GB.")
        else:
            ram_score = 1
            reasons.append("RAM non détectée : milieu de gamme prudent.")
            reasons_en.append("RAM not detected: cautious mid-range.")

        tier = TIERS[min(gpu_score, cpu_score, ram_score)]
        cpu_strong = bool(
            cores is not None
            and (cores >= 8 or (cores >= 6 and freq is not None and freq >= 3800))
        )
        label, label_en = _TIER_LABELS[tier]
        return {
            "tier": tier,
            "label": label,
            "label_en": label_en,
            "reasons": reasons,
            "reasons_en": reasons_en,
            "cpu_strong": cpu_strong,
            "gpu_vendor": gpu_vendor,
            "vram_mb": vram_mb,
            "ram_gb": ram_gb,
            "gpu_name": gpu_name or None,
            "gpu_arch": gpu_arch(gpu_name) if gpu_name else None,
        }
    except Exception:  # jamais d'exception vers l'appelant
        return fallback


def _refresh_info() -> tuple[int | None, int | None]:
    """(Hz actuel, Hz max supporté) de l'écran principal à sa résolution.

    Réutilise les structures ctypes de :mod:`overdrive.core.insights`
    (``_DEVMODEW``, ``_max_frequency_at``) sans dupliquer la détection.
    ``(None, None)`` hors Windows ou en cas d'échec ; jamais d'exception.
    """
    if not is_windows():
        return (None, None)
    try:
        import ctypes  # noqa: PLC0415 — chemin Windows uniquement

        from ..insights import (  # noqa: PLC0415 — réutilisation ciblée
            _DEVMODEW,
            _DISPLAY_DEVICE_ATTACHED_TO_DESKTOP,
            _DISPLAY_DEVICE_MIRRORING_DRIVER,
            _DISPLAY_DEVICEW,
            _ENUM_CURRENT_SETTINGS,
            _max_frequency_at,
        )

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        primary_flag = 0x00000004  # DISPLAY_DEVICE_PRIMARY_DEVICE
        chosen: tuple[int, int] | None = None
        fallback_pair: tuple[int, int] | None = None
        device_index = 0
        while device_index < 32:
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
                continue
            hz_max = _max_frequency_at(user32, device.DeviceName, width, height)
            pair = (hz_now, max(hz_max, hz_now))
            if flags & primary_flag:
                chosen = pair
                break
            if fallback_pair is None:
                fallback_pair = pair
        result = chosen or fallback_pair
        return result if result is not None else (None, None)
    except Exception:
        return (None, None)


def max_refresh_hz() -> int | None:
    """Hz max supporté par l'écran principal à sa résolution actuelle.

    ``None`` hors Windows ou si la détection échoue. Jamais d'exception.
    """
    return _refresh_info()[1]


def recommended_fps_max(tier_info: dict, hz_max: int | None) -> int:
    """Cap de FPS conseillé pour l'autoexec, selon tier et Hz de l'écran.

    Sur un CPU modeste, ``fps_max 0`` produit des frametimes en dents de
    scie ; un cap ≈ 2×Hz stabilise le frame pacing subtick sans coûter de
    réactivité perceptible. Règle : illimité (0) uniquement en haut de
    gamme avec un CPU costaud ; sinon ``max(120, min(400, 2×Hz))`` avec
    60 Hz par défaut quand l'écran n'est pas détectable. Jamais d'exception.
    """
    try:
        tier = tier_info.get("tier") if isinstance(tier_info, dict) else None
        cpu_strong = bool(tier_info.get("cpu_strong")) if isinstance(tier_info, dict) else False
        if tier == "highend" and cpu_strong:
            return 0
        hz = int(hz_max) if isinstance(hz_max, (int, float)) and hz_max > 1 else 60
        return max(120, min(400, 2 * hz))
    except Exception:
        return 120


def suggest_maxping(results: list[dict] | None = None) -> dict:
    """Suggère ``mm_dedicated_search_maxping`` depuis la latence mesurée.

    ``results`` : sorties de :func:`overdrive.core.latency.measure` ; si
    ``None``, mesure uniquement proche/paris/europe_ouest (borné < 8 s).
    Retour : ``{"maxping", "basis_ms", "region", "measured"}`` ;
    ``maxping = clamp(arrondi sup. multiple de 5 de basis+30, 40, 150)``
    (borne basse 40 : en dessous le matchmaking devient trop restrictif ;
    la cvar accepte 25-350). Aucune mesure exploitable => 60, valeur sûre
    historique. Jamais d'exception.
    """
    fallback = {"maxping": 60, "basis_ms": None, "region": None, "measured": False}
    try:
        if results is None:
            results = _measure_latency(["proche", "paris", "europe_ouest"])
        best_ms: float | None = None
        best_region: str | None = None
        for entry in results or []:
            if not isinstance(entry, dict) or not entry.get("ok"):
                continue
            ms = entry.get("ms_avg")
            if isinstance(ms, bool) or not isinstance(ms, (int, float)) or ms <= 0:
                continue
            if best_ms is None or float(ms) < best_ms:
                best_ms = float(ms)
                region = entry.get("id")
                best_region = region if isinstance(region, str) else None
        if best_ms is None:
            return fallback
        maxping = int(math.ceil((best_ms + 30.0) / 5.0) * 5)
        maxping = max(40, min(150, maxping))
        return {"maxping": maxping, "basis_ms": round(best_ms, 1),
                "region": best_region, "measured": True}
    except Exception:
        return fallback


def is_cs2_running() -> bool:
    """Vrai si un processus CS2 tourne (scan psutil FRAIS, sans cache).

    Comparaison insensible à la casse avec les ``process_names`` du
    catalogue (``cs2.exe``) et leur variante sans extension (Linux/Proton).
    Le cache 3 s de ``gamewatch`` n'est volontairement pas réutilisé : une
    fausse réponse « pas lancé » pendant une écriture serait grave.
    Jamais d'exception (doute => False, les écritures restent refusables
    en amont).
    """
    try:
        names = {"cs2.exe", "cs2"}
        game = get_game("cs2")
        if game and isinstance(game.get("process_names"), list):
            for name in game["process_names"]:
                low = str(name).lower()
                names.add(low)
                if low.endswith(".exe"):
                    names.add(low[:-4])
        for proc in psutil.process_iter(["name"]):
            try:
                pname = proc.info.get("name")
            except Exception:
                continue
            if pname and str(pname).lower() in names:
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Plan vidéo résolu et application sécurisée
# ---------------------------------------------------------------------------


def _resolve_plan_value(entry: dict, tier: str, current: dict[str, str],
                        tier_info: dict, hz_max: int | None) -> tuple[str | None, str | None]:
    """(valeur cible, raison d'inapplicabilité) d'une entrée du plan.

    Valeur ``None`` = rien à écrire pour ce réglage (protégé, dynamique
    non résolu, ou GPU non éligible), avec la raison en second membre.
    """
    if entry.get("protected"):
        return None, "jamais modifiée automatiquement (choix personnel)"
    dynamic = entry.get("dynamic")
    tiers = entry.get("tiers")
    base = tiers.get(tier) if isinstance(tiers, dict) else None

    if dynamic == "refresh_hz":
        if isinstance(hz_max, int) and hz_max > 1:
            return str(hz_max), None
        return None, "fréquence maximale de l'écran non détectable"
    if dynamic == "gpu_mem":
        vram_mb = tier_info.get("vram_mb")
        if (tier == "midrange" and isinstance(vram_mb, int) and vram_mb < 6144):
            return "0", None
        return base, None
    if dynamic == "cpu_mem":
        ram_gb = tier_info.get("ram_gb")
        if isinstance(ram_gb, (int, float)) and ram_gb < 12:
            return "0", None
        return base, None
    if dynamic == "reflex":
        if tier_info.get("gpu_vendor") != "nvidia":
            return None, "GPU non NVIDIA : Reflex jamais écrit"
        return base, None
    if entry.get("id") == "msaa" and tier == "lowend" and current.get(
            "setting.msaa_samples") == "1":
        # CMAA2 (msaa_samples 1) : choix valide en petite config, conservé.
        return "1", None
    return base, None


def video_plan(tier: str, current: dict[str, str] | None, *,
               tier_info: dict | None = None,
               hz_max: int | None = None) -> list[dict]:
    """Plan vidéo résolu pour ce tier, confronté au fichier du joueur.

    Remplace l'ancien ``_video_recommendations`` : chaque entrée porte
    ``applicable`` (une clé candidate est présente dans le fichier ET une
    valeur cible est résolue), ``confidence``, ``menu_path`` et la valeur
    du tier résolu (entrées ``dynamic`` incluses). ``tier_info``/``hz_max``
    optionnels pour les tests (sinon détection réelle). Jamais d'exception.
    """
    try:
        resolved_tier = tier if tier in TIERS else "midrange"
        settings = current if isinstance(current, dict) else {}
        info = tier_info if isinstance(tier_info, dict) else detect_tier()
        hz = hz_max if isinstance(hz_max, int) else max_refresh_hz()

        plan: list[dict] = []
        for entry in _VIDEO_PLAN:
            keys = [k for k in entry.get("keys", []) if isinstance(k, str)]
            found_key = next((k for k in keys if k in settings), None)
            recommended, blocked_reason = _resolve_plan_value(
                entry, resolved_tier, settings, info, hz)
            applicable = (found_key is not None and recommended is not None
                          and not entry.get("protected"))
            skip_reason: str | None = None
            if not applicable:
                if entry.get("protected"):
                    skip_reason = "jamais modifiée automatiquement (choix personnel)"
                elif blocked_reason is not None:
                    skip_reason = blocked_reason
                elif not keys:
                    skip_reason = ("clé inconnue : réglez-le dans CS2 "
                                   "(Paramètres > Vidéo avancé)")
                elif found_key is None:
                    skip_reason = "absente du fichier"
            plan.append({
                "id": entry["id"],
                "label": entry["label"],
                "label_en": entry["label_en"],
                "key": found_key if found_key is not None else (keys[0] if keys else None),
                "keys": list(keys),
                "current": settings.get(found_key) if found_key else None,
                "recommended": recommended,
                "applicable": applicable,
                "skip_reason": skip_reason,
                "confidence": entry["confidence"],
                "menu_path": entry["menu_path"],
                "menu_path_en": entry["menu_path_en"],
                "note": entry["note"],
                "note_en": entry["note_en"],
                "protected": bool(entry.get("protected")),
            })
        return plan
    except Exception:  # jamais d'exception vers l'appelant
        return []


def _decode_video_bytes(raw: bytes) -> tuple[str, str] | None:
    """(texte, encodage) d'un cs2_video.txt, ou None si indéchiffrable.

    UTF-8 strict d'abord (format Valve standard), cp1252 en secours ; le
    même encodage est réutilisé à l'écriture pour un round-trip fidèle.
    """
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def _line_pattern(key: str) -> re.Pattern[str]:
    """Regex ligne à ligne pour la valeur d'une clé KV ("clé" "valeur")."""
    return re.compile(r'^(\s*"' + re.escape(key) + r'"\s+")([^"]*)(".*)$',
                      re.MULTILINE)


def apply_video_settings(user_id: str | None, tier: str) -> dict:
    """Applique le plan vidéo du tier au cs2_video.txt du joueur, sans risque.

    Déroulé strict : validation du tier et du profil ; refus si CS2 tourne
    (scan psutil frais) ; refus si le fichier est absent (jamais inventé) ;
    sauvegarde coffre préalable OBLIGATOIRE (``configvault.backup(["cs2"])``,
    abandon si elle échoue) ; édition ligne à ligne (jamais de
    re-sérialisation VDF : commentaires, ordre, indentation et clés
    inconnues préservés) ; re-parse de vérification avant écriture ;
    écriture atomique (fichier temporaire + ``os.replace``) avec copie
    ``.bak`` locale. Seules les clés PRÉSENTES dans le fichier sont
    modifiées, aucune n'est ajoutée.

    Retour : ``{"ok", "message", "backup", "path", "changed", "skipped"}``
    — jamais d'exception.
    """
    changed: list[dict] = []
    skipped: list[dict] = []
    try:
        if tier not in TIERS:
            return {"ok": False,
                    "message": f"Tier inconnu : '{tier}' (attendu : "
                               f"{', '.join(TIERS)}).",
                    "backup": None, "path": None, "changed": [], "skipped": []}

        steam_root = find_steam_root()
        if steam_root is None:
            return {"ok": False, "message": "Steam introuvable sur cette machine.",
                    "backup": None, "path": None, "changed": [], "skipped": []}
        profiles = _userdata_profiles(steam_root)
        if not profiles:
            return {"ok": False,
                    "message": "Aucun profil CS2 trouvé dans Steam/userdata "
                               "(lancez CS2 une première fois).",
                    "backup": None, "path": None, "changed": [], "skipped": []}
        if user_id is not None:
            profile = next((p for p in profiles if p["user_id"] == str(user_id)), None)
            if profile is None:
                return {"ok": False,
                        "message": f"Profil utilisateur '{user_id}' introuvable "
                                   "dans Steam/userdata.",
                        "backup": None, "path": None, "changed": [], "skipped": []}
        else:
            profile = profiles[0]

        if is_cs2_running():
            return {"ok": False,
                    "message": "CS2 est en cours d'exécution : fermez le jeu "
                               "avant d'appliquer (il écraserait les réglages "
                               "en quittant).",
                    "backup": None, "path": None, "changed": [], "skipped": []}

        video_file = Path(profile["cfg_dir"]) / "cs2_video.txt"
        if not video_file.is_file():
            return {"ok": False,
                    "message": "cs2_video.txt introuvable : lancez CS2 une "
                               "première fois pour qu'il crée le fichier "
                               "(Overdrive ne l'invente jamais).",
                    "backup": None, "path": None, "changed": [], "skipped": []}

        raw = video_file.read_bytes()
        decoded = _decode_video_bytes(raw)
        if decoded is None:
            return {"ok": False,
                    "message": "cs2_video.txt illisible (encodage inattendu) : "
                               "aucune modification.",
                    "backup": None, "path": None, "changed": [], "skipped": []}
        text, encoding = decoded

        flat: dict[str, str] = {}
        _flatten_kv(parse_vdf(text), flat)
        if not flat:
            return {"ok": False,
                    "message": "cs2_video.txt vide ou corrompu : aucune "
                               "modification.",
                    "backup": None, "path": None, "changed": [], "skipped": []}

        # Sauvegarde coffre préalable obligatoire (restaurable depuis l'UI).
        vault = _vault_backup(["cs2"])
        if not vault.get("ok"):
            return {"ok": False,
                    "message": "Sauvegarde du coffre impossible, application "
                               f"annulée : {vault.get('message')}",
                    "backup": None, "path": None, "changed": [], "skipped": []}
        backup_name = Path(str(vault.get("path"))).name if vault.get("path") else None

        plan = video_plan(tier, flat)
        new_text = text
        for item in plan:
            if item.get("protected"):
                continue  # affiché dans le panneau, jamais écrit
            key = item.get("key")
            target = item.get("recommended")
            if not item.get("applicable") or not key or target is None:
                skipped.append({"key": key or item["id"],
                                "reason": item.get("skip_reason")
                                or "absente du fichier"})
                continue
            if item["id"] == "refresh_rate":
                denominator = flat.get("setting.refreshrate_denominator")
                if denominator is not None and denominator != "1":
                    skipped.append({"key": key,
                                    "reason": "dénominateur de fréquence ≠ 1 : "
                                              "réglage laissé tel quel"})
                    continue
            if flat.get(key) == target:
                skipped.append({"key": key, "reason": "déjà réglée"})
                continue
            pattern = _line_pattern(key)
            replaced, count = pattern.subn(
                lambda m, v=target: f"{m.group(1)}{v}{m.group(3)}",
                new_text, count=1)
            if count != 1:
                skipped.append({"key": key,
                                "reason": "ligne introuvable dans le fichier"})
                continue
            new_text = replaced
            changed.append({"key": key, "old": flat.get(key), "new": target})

        if changed:
            # Vérification avant écriture : le texte modifié doit re-parser
            # avec exactement les nouvelles valeurs.
            verify: dict[str, str] = {}
            _flatten_kv(parse_vdf(new_text), verify)
            for change in changed:
                if verify.get(change["key"]) != change["new"]:
                    return {"ok": False,
                            "message": "Vérification après édition échouée "
                                       f"(clé {change['key']}) : aucune "
                                       "écriture effectuée.",
                            "backup": backup_name, "path": str(video_file),
                            "changed": [], "skipped": skipped}

            # Écriture atomique + copie .bak locale (en plus du zip du coffre).
            payload = new_text.encode(encoding)
            shutil.copy2(video_file, video_file.with_name("cs2_video.txt.bak"))
            fd, tmp_name = tempfile.mkstemp(prefix="cs2_video.",
                                            suffix=".tmp",
                                            dir=str(video_file.parent))
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                os.replace(tmp_name, video_file)
            except OSError:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise

        message = (f"{len(changed)} réglage(s) appliqué(s), {len(skipped)} "
                   f"ignoré(s) (absents de votre fichier ou déjà réglés).")
        if backup_name:
            message += (f" Sauvegarde : {backup_name} — restaurable depuis "
                        "le Coffre.")
        return {"ok": True, "message": message, "backup": backup_name,
                "path": str(video_file), "changed": changed, "skipped": skipped}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False,
                "message": f"Échec de l'application des réglages vidéo : {exc}",
                "backup": None, "path": None,
                "changed": changed, "skipped": skipped}


# ---------------------------------------------------------------------------
# Options de lancement et conseils « Pour ta machine »
# ---------------------------------------------------------------------------


def launch_options_for(tier: str, hw: dict | None = None) -> dict:
    """Options de lancement CS2 du tier (catalogue, repli local).

    Retour : ``{"options", "note", "note_en", "tier"}`` ; tier inconnu =>
    repli ``midrange``. Si ``hw`` révèle un CPU à 4 cœurs physiques ou
    moins, ``-high`` est retiré même en midrange (il peut affamer le
    thread audio). Jamais d'exception.
    """
    resolved = tier if tier in TIERS else "midrange"
    note_fr, note_en = _LAUNCH_TIERS_NOTE_FALLBACK[resolved]
    options = _LAUNCH_TIERS_FALLBACK[resolved]
    try:
        game = get_game("cs2") or {}
        tiers_map = game.get("launch_options_tiers")
        if isinstance(tiers_map, dict) and isinstance(tiers_map.get(resolved), str):
            options = tiers_map[resolved]
        notes = game.get("launch_options_tiers_note")
        if isinstance(notes, dict) and isinstance(notes.get(resolved), str):
            note_fr = notes[resolved]
        notes_en = game.get("launch_options_tiers_note_en")
        if isinstance(notes_en, dict) and isinstance(notes_en.get(resolved), str):
            note_en = notes_en[resolved]

        if "-high" in options.split() and isinstance(hw, dict):
            cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
            cores = _positive(cpu.get("cores_physical"))
            if cores is not None and cores <= 4:
                options = " ".join(o for o in options.split() if o != "-high")
                note_fr += (" -high retiré : seulement 4 cœurs physiques "
                            "détectés sur cette machine.")
                note_en += (" -high removed: only 4 physical cores detected "
                            "on this machine.")
        return {"options": options, "note": note_fr, "note_en": note_en,
                "tier": resolved}
    except Exception:  # jamais d'exception vers l'appelant
        return {"options": options, "note": note_fr, "note_en": note_en,
                "tier": resolved}


def _advice(advice_id: str, icon: str, title: str, title_en: str,
            detail: str, detail_en: str, kind: str) -> dict:
    """Construit un conseil de :func:`machine_advice` au format commun."""
    return {"id": advice_id, "icon": icon, "title": title,
            "title_en": title_en, "detail": detail, "detail_en": detail_en,
            "kind": kind}


def machine_advice(tier_info: dict, hw: dict, info: dict) -> list[dict]:
    """Conseils CS2 « Pour ta machine » : 5 à 8 entrées adaptées au matériel.

    ``info`` : dict de contexte (celui de :func:`cs2_info`) ; si une clé
    ``suggested_maxping`` mesurée y figure (route suggestions), le conseil
    maxping est inclus. ``kind`` : ``"reco"`` (recommandation), ``"opinion"``
    (choix personnel assumé), ``"info"``. Jamais d'exception.
    """
    advice: list[dict] = []
    try:
        tinfo = tier_info if isinstance(tier_info, dict) else detect_tier()
        hw = hw if isinstance(hw, dict) else {}
        info = info if isinstance(info, dict) else {}
        tier = tinfo.get("tier") if tinfo.get("tier") in TIERS else "midrange"
        label = tinfo.get("label") or _TIER_LABELS[tier][0]
        label_en = tinfo.get("label_en") or _TIER_LABELS[tier][1]

        # 1. Tier détecté (toujours).
        reasons = tinfo.get("reasons") if isinstance(tinfo.get("reasons"), list) else []
        reasons_en = tinfo.get("reasons_en") if isinstance(tinfo.get("reasons_en"), list) else []
        advice.append(_advice(
            "tier", "🖥️",
            f"Machine classée « {label} »",
            f"Machine classed “{label_en}”",
            " ".join(str(r) for r in reasons) or "Classement par défaut.",
            " ".join(str(r) for r in reasons_en) or "Default classification.",
            "info"))

        # 2. fps_max conseillé (toujours).
        hz_now, hz_max = _refresh_info()
        fps = recommended_fps_max(tinfo, hz_max)
        if fps == 0:
            fps_detail = ("CPU costaud + haut de gamme : fps_max 0 (FPS "
                          "libres), le frame pacing subtick reste stable.")
            fps_detail_en = ("Strong CPU + high-end machine: fps_max 0 "
                             "(uncapped), subtick frame pacing stays stable.")
        else:
            hz_txt = f"{hz_max} Hz détectés" if hz_max else "écran supposé 60 Hz"
            hz_txt_en = f"{hz_max} Hz detected" if hz_max else "60 Hz assumed"
            fps_detail = (f"fps_max {fps} (≈ 2× la fréquence de l'écran, "
                          f"{hz_txt}) : sur un CPU modeste, fps_max 0 produit "
                          "des frametimes en dents de scie ; un cap stabilise "
                          "le frame pacing.")
            fps_detail_en = (f"fps_max {fps} (≈ 2× your monitor's refresh "
                             f"rate, {hz_txt_en}): on a modest CPU, fps_max 0 "
                             "produces sawtooth frametimes; a cap steadies "
                             "frame pacing.")
        advice.append(_advice(
            "fps_max", "🎯",
            f"Cap de FPS conseillé : {fps if fps else 'illimité (0)'}",
            f"Recommended FPS cap: {fps if fps else 'uncapped (0)'}",
            fps_detail, fps_detail_en, "reco"))

        # 3. Latence GPU : Reflex (NVIDIA) ou Anti-Lag 2 (AMD).
        vendor = tinfo.get("gpu_vendor")
        if vendor == "nvidia":
            boost = " + Boost" if tier == "highend" else ""
            advice.append(_advice(
                "reflex", "⚡",
                f"NVIDIA Reflex : Activé{boost}",
                f"NVIDIA Reflex: Enabled{boost}",
                "Réduit la latence système quand le GPU sature ; le Boost "
                "est surtout utile en haut de gamme.",
                "Cuts system latency when the GPU is saturated; Boost is "
                "mostly useful on high-end machines.",
                "reco"))
        elif vendor == "amd":
            arch = tinfo.get("gpu_arch")
            if arch in ("polaris", "vega"):
                # Anti-Lag 2 n'est pas pris en charge sur ces générations GCN.
                advice.append(_advice(
                    "antilag", "⚡",
                    "Radeon Anti-Lag (pilote) : à activer si présent",
                    "Radeon Anti-Lag (driver): enable it if present",
                    "AMD Anti-Lag 2 n'est pas pris en charge sur votre GPU : "
                    "activez Radeon Anti-Lag dans le profil CS2 d'AMD Software "
                    "Adrenalin si l'option y figure (voir la checklist AMD).",
                    "AMD Anti-Lag 2 is not supported on your GPU: enable "
                    "Radeon Anti-Lag in the CS2 profile of AMD Software "
                    "Adrenalin if the option is there (see the AMD checklist).",
                    "info"))
            else:
                advice.append(_advice(
                    "antilag", "⚡",
                    "AMD Anti-Lag 2 : à activer dans CS2 si présent",
                    "AMD Anti-Lag 2: enable it in CS2 if present",
                    "Si CS2 affiche « AMD Anti-Lag 2 » dans Vidéo avancé, "
                    "activez-le dans le jeu (équivalent de Reflex pour votre "
                    "GPU) ; sinon, activez Radeon Anti-Lag dans le profil CS2 "
                    "d'AMD Software Adrenalin.",
                    "If CS2 shows “AMD Anti-Lag 2” under Advanced Video, "
                    "enable it in the game (the Reflex equivalent for your "
                    "GPU); otherwise, enable Radeon Anti-Lag in the CS2 "
                    "profile of AMD Software Adrenalin.",
                    "info"))

        # 4. Écran sous-cadencé (réutilise la détection des Constats).
        if (isinstance(hz_now, int) and isinstance(hz_max, int)
                and hz_max > hz_now):
            advice.append(_advice(
                "refresh", "📺",
                f"Écran sous-cadencé : {hz_now} Hz au lieu de {hz_max} Hz",
                f"Monitor under-clocked: {hz_now} Hz instead of {hz_max} Hz",
                f"Votre écran supporte {hz_max} Hz mais tourne à {hz_now} Hz. "
                "Corrigez dans Paramètres Windows > Affichage avancé (voir "
                "aussi la page Constats d'Overdrive).",
                f"Your monitor supports {hz_max} Hz but runs at {hz_now} Hz. "
                "Fix it in Windows Settings > Advanced display (see also "
                "Overdrive's Insights page).",
                "reco"))

        # 5. maxping suggéré, uniquement si une mesure est fournie (pas de
        # réseau ici : la mesure vit dans la route suggestions dédiée).
        maxping = info.get("suggested_maxping")
        if (isinstance(maxping, dict) and maxping.get("measured")
                and isinstance(maxping.get("maxping"), int)):
            basis = maxping.get("basis_ms")
            region = maxping.get("region") or "région la plus proche"
            advice.append(_advice(
                "maxping", "📡",
                f"mm_dedicated_search_maxping {maxping['maxping']}",
                f"mm_dedicated_search_maxping {maxping['maxping']}",
                f"Votre latence mesurée (≈ {basis} ms vers {region}) suggère "
                f"un ping maximum de {maxping['maxping']} en matchmaking.",
                f"Your measured latency (≈ {basis} ms to {region}) suggests "
                f"a matchmaking ping cap of {maxping['maxping']}.",
                "reco"))

        # 6. Textures selon la VRAM réelle.
        vram_mb = tinfo.get("vram_mb")
        if isinstance(vram_mb, int) and vram_mb > 0:
            vram_gb = round(vram_mb / 1024)
            if vram_mb < 6144:
                vram_detail = (f"{vram_gb} Go de VRAM : restez en détail des "
                               "modèles/textures Faible — un débordement de "
                               "VRAM = des saccades en plein combat.")
                vram_detail_en = (f"{vram_gb} GB of VRAM: stay on Low "
                                  "model/texture detail — VRAM overflow means "
                                  "stutters mid-fight.")
            else:
                vram_detail = (f"{vram_gb} Go de VRAM : le détail des "
                               "modèles/textures Moyen (ou Élevé dès 8 Go) "
                               "passe sans saccades.")
                vram_detail_en = (f"{vram_gb} GB of VRAM: Medium model/texture "
                                  "detail (or High from 8 GB) runs without "
                                  "stutters.")
            advice.append(_advice(
                "vram", "🧠",
                f"Textures adaptées à vos {vram_gb} Go de VRAM",
                f"Textures matched to your {vram_gb} GB of VRAM",
                vram_detail, vram_detail_en, "reco"))

        # 7. Résolution / 4:3 étiré — opinion honnête imposée.
        advice.append(_advice(
            "stretched", "📐",
            "4:3 étiré : un confort personnel, pas un avantage",
            "Stretched 4:3: personal comfort, not an advantage",
            "Le 4:3 étiré (ex. 1280×960) donne des modèles plus larges et "
            "plus de FPS, mais réduit le champ visuel horizontal et l'image "
            "est moins nette. Aucun avantage mesuré en précision : c'est un "
            "confort personnel. Essayez 2 semaines avant de juger. Overdrive "
            "ne modifie jamais votre résolution automatiquement.",
            "Stretched 4:3 (e.g. 1280×960) gives wider player models and "
            "more FPS, but narrows the horizontal field of view and softens "
            "the image. No measured accuracy advantage: it is personal "
            "comfort. Try it for 2 weeks before judging. Overdrive never "
            "changes your resolution automatically.",
            "opinion"))

        # 8. Petite config : fermer les gourmands (overlays détectés inclus).
        if tier == "lowend":
            overlay_names: list[str] = []
            if is_windows():
                try:
                    from ..insights import _detect_overlays  # noqa: PLC0415

                    overlay_names = [str(i.get("title") or "")
                                     for i in _detect_overlays() if i.get("title")]
                except Exception:
                    overlay_names = []
            extra = (" Détectés en ce moment : "
                     + " ; ".join(overlay_names) + ".") if overlay_names else ""
            extra_en = (" Detected right now: "
                        + "; ".join(overlay_names) + ".") if overlay_names else ""
            advice.append(_advice(
                "lowend_background", "🧹",
                "Petite config : fermez navigateur et overlays avant de jouer",
                "Low-end machine: close browser and overlays before playing",
                "Chaque onglet et overlay vole du CPU à CS2. Fermez "
                "navigateur, launchers et overlays, et activez le plan "
                "d'alimentation performant (page Optimisations d'Overdrive)."
                + extra,
                "Every tab and overlay steals CPU from CS2. Close your "
                "browser, launchers and overlays, and enable the high "
                "performance power plan (Overdrive's Tweaks page)." + extra_en,
                "reco"))

        return advice[:8]
    except Exception:  # jamais d'exception vers l'appelant
        return advice[:8]


# ---------------------------------------------------------------------------
# Profils userdata et lecture de cs2_video.txt (inchangés)
# ---------------------------------------------------------------------------


def _recommended_launch_options() -> str:
    """Options de lancement recommandées (depuis le catalogue, avec repli)."""
    game = get_game("cs2")
    if game and isinstance(game.get("launch_options"), str):
        return game["launch_options"]
    return _FALLBACK_LAUNCH_OPTIONS


def _flatten_kv(data: object, out: dict[str, str]) -> None:
    """Aplatit un arbre KeyValues en dict {clé: valeur str} (feuilles uniquement)."""
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        if isinstance(value, dict):
            _flatten_kv(value, out)
        elif isinstance(key, str) and isinstance(value, str):
            out[key] = value


def _userdata_profiles(steam_root: Path) -> list[dict]:
    """Profils Steam ayant des données CS2 (userdata/<id>/730)."""
    profiles: list[dict] = []
    userdata = steam_root / "userdata"
    try:
        entries = sorted(p for p in userdata.iterdir() if p.is_dir())
    except OSError:
        return profiles
    for entry in entries:
        local_730 = entry / str(CS2_APPID) / "local"
        try:
            if not local_730.is_dir():
                continue
        except OSError:
            continue
        cfg_dir = local_730 / "cfg"
        autoexec = cfg_dir / "autoexec.cfg"
        config_files: list[str] = []
        try:
            if cfg_dir.is_dir():
                config_files = sorted(
                    p.name for p in cfg_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in (".cfg", ".txt")
                )
        except OSError:
            config_files = []
        has_autoexec = autoexec.name in config_files
        profiles.append(
            {
                "user_id": entry.name,
                "cfg_dir": str(cfg_dir),
                "has_autoexec": has_autoexec,
                "autoexec_path": str(autoexec) if has_autoexec else None,
                "config_files": config_files,
            }
        )
    return profiles


def _read_video_settings(cfg_dir: str) -> dict[str, str] | None:
    """Parse cs2_video.txt (KV Valve "setting.xxx" "val") dans ce dossier cfg."""
    video_file = Path(cfg_dir) / "cs2_video.txt"
    try:
        if not video_file.is_file():
            return None
        text = video_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    flat: dict[str, str] = {}
    _flatten_kv(parse_vdf(text), flat)
    return flat or None


# ---------------------------------------------------------------------------
# Autoexec par tier
# ---------------------------------------------------------------------------


def _valid_fps_max(value: object) -> bool:
    """Vrai si la valeur est un fps_max acceptable (0, ou 60 à 1000)."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    low, high = _FPS_MAX_RANGE
    return value == 0 or low <= value <= high


def generate_autoexec(profile_id: str | None = None, tier: str | None = None, *,
                      fps_max: int | None = None, maxping: int | None = None,
                      sensitivity: float | None = None,
                      zoom_ratio: float | None = None) -> str:
    """Contenu d'autoexec.cfg par tier, commenté en français (cvars CS2 valides).

    Rétrocompatible : ``tier=None`` => ``midrange``. Les paramètres hors
    bornes (``fps_max`` ∉ {0} ∪ [60;1000], ``maxping`` ∉ [25;350],
    ``sensitivity`` ∉ ]0;10], ``zoom_ratio`` ∉ [0,5;2,0]) sont ignorés et
    signalés en ligne commentée. Les cvars réseau hérités de CS:GO (rate,
    cl_interp, cl_interp_ratio, cl_updaterate, cl_cmdrate) n'existent plus
    dans CS2 (subtick) et sont volontairement absents. Jamais d'exception.
    """
    try:
        resolved_tier = tier if tier in TIERS else "midrange"
        tier_label = _TIER_LABELS[resolved_tier][0]
        header_profile = profile_id if profile_id else "par défaut"

        try:
            summary = str(detect_hardware().get("summary") or "machine inconnue")
        except Exception:
            summary = "machine inconnue"
        try:
            today = datetime.now().strftime("%Y-%m-%d")
        except Exception:
            today = "date inconnue"

        detected = detect_tier()
        hz_max = max_refresh_hz()

        # --- fps_max : borne vérifiée, sinon calcul par tier/Hz. ---
        ignored_fps: int | None = None
        if fps_max is not None and not _valid_fps_max(fps_max):
            ignored_fps, fps_max = fps_max, None
        if fps_max is None:
            fps_max = recommended_fps_max(
                {"tier": resolved_tier, "cpu_strong": detected.get("cpu_strong")},
                hz_max)
        if fps_max == 0:
            fps_comment = "FPS libres : CPU costaud, frame pacing subtick stable"
        elif hz_max:
            fps_comment = (f"≈ 2× {hz_max} Hz : frametimes stables, pas de "
                           "dents de scie")
        else:
            fps_comment = "cap prudent (écran non détecté) : frametimes stables"

        # --- maxping : borne vérifiée, repli sûr 60. ---
        ignored_maxping: int | None = None
        if maxping is not None and (isinstance(maxping, bool)
                                    or not isinstance(maxping, int)
                                    or not _MAXPING_RANGE[0] <= maxping <= _MAXPING_RANGE[1]):
            ignored_maxping, maxping = maxping if isinstance(maxping, int) else None, None
        if maxping is None:
            maxping_line = ("mm_dedicated_search_maxping 60      "
                            "// valeur sûre par défaut ; mesurez votre latence "
                            "(bouton Suggestions) pour affiner")
        else:
            maxping_line = (f"mm_dedicated_search_maxping {maxping}      "
                            "// basé sur votre latence mesurée")

        # --- sensibilité / zoom : bornes serveur, sinon lignes commentées. ---
        sens_valid = (isinstance(sensitivity, (int, float))
                      and not isinstance(sensitivity, bool)
                      and _SENSITIVITY_RANGE[0] < float(sensitivity) <= _SENSITIVITY_RANGE[1])
        zoom_valid = (isinstance(zoom_ratio, (int, float))
                      and not isinstance(zoom_ratio, bool)
                      and _ZOOM_RATIO_RANGE[0] <= float(zoom_ratio) <= _ZOOM_RATIO_RANGE[1])
        sens_line = (f"sensitivity {float(sensitivity):g}" if sens_valid else
                     "// sensitivity 1.00                 // décommentez et "
                     "ajustez à votre valeur")
        zoom_line = (f"zoom_sensitivity_ratio {float(zoom_ratio):g}       "
                     "// sensibilité sous lunette" if zoom_valid else
                     "// zoom_sensitivity_ratio 1.00      // sensibilité sous "
                     "lunette")

        lines = [
            "// ============================================================",
            f"// Overdrive — autoexec.cfg Counter-Strike 2 — profil {tier_label}",
            f"// Machine : {summary} — généré le {today}",
            f"// Profil Steam : {header_profile}",
            "// Emplacement : Steam/userdata/<id>/730/local/cfg/autoexec.cfg",
            "//",
            "// Les cvars réseau CS:GO (rate, cl_interp, cl_updaterate,",
            "// cl_cmdrate) n'existent plus dans CS2 (subtick) : absents.",
            "// ============================================================",
            "",
            "con_enable 1                        // console accessible (touche ²/~)",
            "",
            "// --- Performances ---",
        ]
        if resolved_tier == "lowend":
            lines += [
                "// Petite config : stabilité d'abord — un cap bas = des",
                "// frametimes stables, pas de dents de scie.",
                f"fps_max {fps_max}                         // {fps_comment}",
                "fps_max_ui 60                       // menus bridés plus fort",
                "// Conseil (hors autoexec) : fermez navigateur et launchers",
                "// avant de jouer.",
            ]
        else:
            if resolved_tier == "highend" and fps_max != 0:
                lines.append("// Haut de gamme mais CPU non costaud : cap "
                             "2×Hz plutôt que fps_max 0.")
            lines += [
                f"fps_max {fps_max}                         // {fps_comment}",
                "fps_max_ui 120                      // limite les FPS dans les menus",
            ]
        if ignored_fps is not None:
            lines.append(f"// fps_max {ignored_fps} demandé : hors bornes "
                         "(0 ou 60-1000), ignoré.")
        lines += [
            "",
            "// --- Souris ---",
            sens_line,
            zoom_line,
            "",
            "// --- Matchmaking ---",
            maxping_line,
        ]
        if ignored_maxping is not None:
            lines.append(f"// mm_dedicated_search_maxping {ignored_maxping} "
                         "demandé : hors bornes (25-350), ignoré.")
        lines += [
            "",
            "// --- Lisibilité ---",
            "r_drawtracers_firstperson 1         // tracers visibles (contrôle du spray)",
            "// viewmodel_fov 68                 // champ de vision de l'arme (54-68)",
            "",
            f'echo "Overdrive : autoexec {resolved_tier} charge."',
            "",
        ]
        return "\n".join(lines)
    except Exception:  # jamais d'exception vers l'appelant
        return ('// Overdrive : generation de l\'autoexec en echec, fichier '
                'minimal.\ncon_enable 1\n'
                'echo "Overdrive : autoexec charge."\n')


def write_autoexec(user_id: str | None = None, content: str | None = None,
                   tier: str | None = None, *, fps_max: int | None = None,
                   maxping: int | None = None, sensitivity: float | None = None,
                   zoom_ratio: float | None = None) -> dict:
    """Écrit l'autoexec du tier dans le profil CS2 ; sauvegarde l'ancien en .bak.

    Mêmes garanties qu'avant (backup ``.bak``, jamais d'exception) + refus
    si CS2 tourne (il écraserait/ignorerait le fichier en quittant).
    Retour : ``{"ok": bool, "message": str, "path": str | None}``.
    """
    try:
        if is_cs2_running():
            return {"ok": False,
                    "message": "CS2 est en cours d'exécution : fermez le jeu "
                               "avant d'écrire l'autoexec (il écraserait les "
                               "réglages en quittant).",
                    "path": None}
        steam_root = find_steam_root()
        if steam_root is None:
            return {"ok": False, "message": "Steam introuvable sur cette machine.", "path": None}
        profiles = _userdata_profiles(steam_root)
        if not profiles:
            return {
                "ok": False,
                "message": "Aucun profil CS2 trouvé dans Steam/userdata (lancez CS2 une première fois).",
                "path": None,
            }
        if user_id is not None:
            profile = next((p for p in profiles if p["user_id"] == str(user_id)), None)
            if profile is None:
                return {
                    "ok": False,
                    "message": f"Profil utilisateur '{user_id}' introuvable dans Steam/userdata.",
                    "path": None,
                }
        else:
            profile = profiles[0]

        cfg_dir = Path(profile["cfg_dir"])
        cfg_dir.mkdir(parents=True, exist_ok=True)
        target = cfg_dir / "autoexec.cfg"

        backed_up = False
        if target.is_file():
            shutil.copy2(target, target.with_name("autoexec.cfg.bak"))
            backed_up = True

        text = content if content is not None else generate_autoexec(
            profile["user_id"], tier, fps_max=fps_max, maxping=maxping,
            sensitivity=sensitivity, zoom_ratio=zoom_ratio)
        target.write_text(text, encoding="utf-8")

        message = f"autoexec.cfg écrit pour le profil {profile['user_id']}."
        if backed_up:
            message += " Ancien fichier sauvegardé en autoexec.cfg.bak."
        return {"ok": True, "message": message, "path": str(target)}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "message": f"Échec de l'écriture de l'autoexec : {exc}", "path": None}


def read_current_video_settings(user_id: str | None = None) -> dict[str, str] | None:
    """Réglages actuels du cs2_video.txt du profil que viserait une écriture.

    Même choix de profil que :func:`apply_video_settings` et
    :func:`write_autoexec` : ``user_id`` s'il est donné, sinon le premier
    profil CS2 de Steam/userdata — l'aperçu correspond donc au fichier
    réellement modifié. Lecture seule, ``None`` si Steam, le profil ou le
    fichier est introuvable. Jamais d'exception.
    """
    try:
        steam_root = find_steam_root()
        if steam_root is None:
            return None
        profiles = _userdata_profiles(steam_root)
        if user_id is not None:
            profile = next((p for p in profiles if p["user_id"] == str(user_id)), None)
        else:
            profile = profiles[0] if profiles else None
        if profile is None:
            return None
        return _read_video_settings(profile["cfg_dir"])
    except Exception:  # jamais d'exception vers l'appelant
        return None


#: Marqueur des autoexec générés par Overdrive (en-tête de generate_autoexec
#: et de son repli minimal).
_AUTOEXEC_MARKER = "// Overdrive"


def autoexec_status(user_id: str | None = None) -> dict:
    """État de l'autoexec.cfg du profil CS2 (lecture seule).

    Retour : ``{"profile", "path", "exists", "by_overdrive"}`` —
    ``by_overdrive`` vrai si le fichier porte l'en-tête généré par
    Overdrive (un autoexec personnel, avec binds, ne doit pas être écrasé
    sans demande explicite). ``profile`` vaut ``None`` si Steam ou le
    profil est introuvable. Jamais d'exception.
    """
    result: dict = {"profile": None, "path": None, "exists": False,
                    "by_overdrive": False}
    try:
        steam_root = find_steam_root()
        if steam_root is None:
            return result
        profiles = _userdata_profiles(steam_root)
        if user_id is not None:
            profile = next((p for p in profiles if p["user_id"] == str(user_id)), None)
        else:
            profile = profiles[0] if profiles else None
        if profile is None:
            return result
        target = Path(profile["cfg_dir"]) / "autoexec.cfg"
        result["profile"] = profile["user_id"]
        result["path"] = str(target)
        if not target.is_file():
            return result
        result["exists"] = True
        with open(target, encoding="utf-8", errors="replace") as handle:
            head = handle.read(4096)
        result["by_overdrive"] = _AUTOEXEC_MARKER in head
        return result
    except Exception:  # jamais d'exception vers l'appelant
        return result


# ---------------------------------------------------------------------------
# État complet pour le panneau CS2
# ---------------------------------------------------------------------------


def cs2_info(tier: str | None = None) -> dict:
    """État complet de l'installation CS2 ; jamais d'exception.

    ``tier`` optionnel (``?tier=`` côté API) force le tier des
    recommandations ; sinon le tier détecté est utilisé. Les clés
    historiques (``installed``, ``userdata_profiles``, ``video_settings``,
    ``video_recommendations``, ``recommended_launch_options``,
    ``autoexec_recommended``) sont conservées ; les nouvelles sont
    additives. La suggestion de maxping n'est PAS incluse ici (coût
    réseau) : route suggestions dédiée.
    """
    install_path: str | None = None
    try:
        path = steam_game_path(CS2_APPID)
        install_path = str(path) if path is not None else None
    except Exception:
        install_path = None

    profiles: list[dict] = []
    try:
        steam_root = find_steam_root()
        if steam_root is not None:
            profiles = _userdata_profiles(steam_root)
    except Exception:
        profiles = []

    video_settings: dict[str, str] | None = None
    for profile in profiles:
        try:
            video_settings = _read_video_settings(profile["cfg_dir"])
        except Exception:
            video_settings = None
        if video_settings is not None:
            break

    tier_info = detect_tier()
    selected_tier = tier if tier in TIERS else (
        tier_info.get("tier") if tier_info.get("tier") in TIERS else "midrange")

    try:
        hw = detect_hardware()
    except Exception:
        hw = {}

    hz_now, hz_max = _refresh_info()
    suggested_fps_max = recommended_fps_max(
        {"tier": selected_tier, "cpu_strong": tier_info.get("cpu_strong")},
        hz_max)

    try:
        recommendations = video_plan(selected_tier, video_settings,
                                     tier_info=tier_info, hz_max=hz_max)
    except Exception:
        recommendations = []

    try:
        advice = machine_advice(tier_info, hw, {})
    except Exception:
        advice = []

    launch_tiers: dict[str, str] = dict(_LAUNCH_TIERS_FALLBACK)
    launch_tiers_note: dict[str, str] = {
        t: _LAUNCH_TIERS_NOTE_FALLBACK[t][0] for t in TIERS}
    try:
        game = get_game("cs2") or {}
        if isinstance(game.get("launch_options_tiers"), dict):
            launch_tiers = dict(game["launch_options_tiers"])
        if isinstance(game.get("launch_options_tiers_note"), dict):
            launch_tiers_note = dict(game["launch_options_tiers_note"])
    except Exception:
        pass

    first_profile = profiles[0]["user_id"] if profiles else None
    return {
        "installed": install_path is not None,
        "install_path": install_path,
        "userdata_profiles": profiles,
        "video_settings": video_settings,
        "video_recommendations": recommendations,
        "recommended_launch_options": _recommended_launch_options(),
        "autoexec_recommended": generate_autoexec(first_profile, selected_tier),
        # --- clés additives (tiers / conseils / dynamiques) ---
        "tier": tier_info,
        "selected_tier": selected_tier,
        "advice": advice,
        "launch_options": launch_options_for(selected_tier, hw),
        "launch_options_tiers": launch_tiers,
        "launch_options_tiers_note": launch_tiers_note,
        "suggested_fps_max": suggested_fps_max,
        "hz_max": hz_max,
        "hz_current": hz_now,
    }
