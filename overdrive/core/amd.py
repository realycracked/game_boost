"""Conseils AMD spécifiques à Counter-Strike 2 (GPU Radeon et CPU Ryzen).

Trois briques, toutes PURES sauf :func:`amd_overview` (qui lit le matériel
détecté) et donc testables sous Linux :

* :func:`gpu_arch` : génération d'un GPU AMD d'après son nom commercial
  (``"rdna4"``, ``"rdna3"``, ``"rdna2"``, ``"rdna1"``, ``"polaris"``,
  ``"vega"``, ``"other"`` pour un GPU AMD non reconnu, ``None`` si le GPU
  n'est pas un AMD ou si le nom est vide) ;
* :func:`adrenalin_checklist` : réglages du PROFIL DE JEU CS2 dans AMD
  Software: Adrenalin Edition, uniquement des options réelles et actuelles
  — formulées « si présent » quand leur présence dépend de la génération
  du GPU ou de la version du pilote ;
* :func:`ryzen_tips` : rappels honnêtes pour les Ryzen 7000/8000/9000 de
  bureau (pilote chipset, EXPO, plan d'alimentation, X3D bi-CCD).

Aucune promesse de gain chiffrée : seuls des effets qualitatifs sont
décrits. Aucune fonction publique ne lève d'exception.

Ce module n'importe rien de lourd au niveau module (``re`` uniquement) :
:mod:`overdrive.core.hardware` l'importe pour reconnaître les GPU Polaris.
"""

from __future__ import annotations

import re

#: Générations reconnues, de la plus récente à la plus ancienne.
ARCHS: tuple[str, ...] = ("rdna4", "rdna3", "rdna2", "rdna1", "vega", "polaris", "other")

#: Générations RDNA (Anti-Lag 2, Radeon Super Resolution...).
_RDNA = frozenset({"rdna1", "rdna2", "rdna3", "rdna4"})
#: Générations RDNA 2 et plus (HYPR-RX, AMD Fluid Motion Frames).
_RDNA2_PLUS = frozenset({"rdna2", "rdna3", "rdna4"})
#: Générations GCN passées par AMD en « mode maintenance » (pilotes).
_LEGACY = frozenset({"polaris", "vega"})

# Motifs testés dans l'ordre (nom en minuscules). Les noms Windows sont du
# type « AMD Radeon RX 9060 XT », « Radeon RX 570 Series »,
# « AMD Radeon(TM) Vega 8 Graphics », « AMD Radeon 780M Graphics ».
_ARCH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # RDNA 4 : RX 9060 / 9060 XT / 9070 / 9070 XT / 9070 GRE.
    ("rdna4", re.compile(r"\brx\s*9\d{3}\b")),
    # RDNA 3 : RX 7600 à 7900 XTX (+ mobiles), iGPU Radeon 740M-780M (RDNA 3)
    # et 840M-890M (RDNA 3.5).
    ("rdna3", re.compile(r"\brx\s*7\d{3}\b|\bradeon\s*(7[4-8]0|8[4-9]0)m\b")),
    # RDNA 2 : RX 6400 à 6950 XT (+ mobiles), iGPU Radeon 610M-680M.
    ("rdna2", re.compile(r"\brx\s*6\d{3}\b|\bradeon\s*6[1-8]0m\b")),
    # RDNA 1 : RX 5300 à 5700 XT (quatre chiffres, à ne pas confondre
    # avec les Polaris RX 550-590 à trois chiffres).
    ("rdna1", re.compile(r"\brx\s*5\d{3}\b")),
    # Vega : RX Vega 56/64, Radeon VII, APU « Radeon Vega 8 Graphics ».
    ("vega", re.compile(r"\bvega\b|\bradeon\s*vii\b")),
    # Polaris : RX 460-480, RX 540-590 (dont 580 2048SP, 590 GME), RX 640,
    # Radeon 540(X)/550(X).
    ("polaris", re.compile(r"\brx\s*(4[6-8]0|5[4-9]0|640)\b|\bradeon\s*(540|550)x?\b")),
)

_NON_AMD_MARKERS = ("nvidia", "geforce", "quadro", "intel", "microsoft basic display")


def is_amd_gpu(name: object) -> bool:
    """Vrai si le nom désigne un GPU AMD/Radeon (jamais d'exception)."""
    if not isinstance(name, str) or not name.strip():
        return False
    low = name.lower()
    if any(marker in low for marker in _NON_AMD_MARKERS):
        return False
    return ("radeon" in low or "amd" in low
            or re.search(r"\brx\s*\d", low) is not None)


def gpu_arch(name: object) -> str | None:
    """Génération d'un GPU AMD d'après son nom commercial.

    Retour : ``"rdna4"`` | ``"rdna3"`` | ``"rdna2"`` | ``"rdna1"`` |
    ``"polaris"`` | ``"vega"`` | ``"other"`` (GPU AMD non reconnu : APU
    « Radeon(TM) Graphics », anciennes Radeon HD/R9...) | ``None`` (nom
    vide ou GPU non AMD). Fonction pure, jamais d'exception.
    """
    try:
        if not is_amd_gpu(name):
            return None
        low = re.sub(r"\((tm|r)\)|[™®]", " ", str(name).lower())
        low = re.sub(r"\s+", " ", low).strip()
        for arch, pattern in _ARCH_PATTERNS:
            if pattern.search(low):
                return arch
        return "other"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Checklist Adrenalin (profil de jeu CS2)
# ---------------------------------------------------------------------------

_WHERE_GAME = "AMD Software: Adrenalin Edition > Jeux > Counter-Strike 2 (Graphiques)"
_WHERE_GAME_EN = "AMD Software: Adrenalin Edition > Gaming > Counter-Strike 2 (Graphics)"
_WHERE_ADV = ("AMD Software: Adrenalin Edition > Jeux > Counter-Strike 2 "
              "(Graphiques > Avancé)")
_WHERE_ADV_EN = ("AMD Software: Adrenalin Edition > Gaming > Counter-Strike 2 "
                 "(Graphics > Advanced)")


def _item(item_id: str, title: str, title_en: str, value: str, value_en: str,
          why: str, why_en: str, where: str = _WHERE_GAME,
          where_en: str = _WHERE_GAME_EN, optional: bool = False) -> dict:
    """Construit une entrée de la checklist Adrenalin au format commun."""
    return {
        "id": item_id,
        "title": title,
        "title_en": title_en,
        "value": value,
        "value_en": value_en,
        "why": why,
        "why_en": why_en,
        "where": where,
        "where_en": where_en,
        "optional": bool(optional),
    }


def adrenalin_checklist(arch: str | None, tier: str | None = None) -> list[dict]:
    """Réglages du profil de jeu CS2 dans AMD Software: Adrenalin Edition.

    Chaque entrée : ``{"id", "title", "title_en", "value", "value_en",
    "why", "why_en", "where", "where_en", "optional"}``. ``arch`` vient de
    :func:`gpu_arch` (``None`` => liste vide : pas de GPU AMD) ; ``tier``
    (``lowend`` / ``midrange`` / ``highend``) n'ajuste que la formulation.
    Les options dont la présence dépend de la génération ou de la version
    du pilote sont formulées « si présent ». Jamais d'exception.
    """
    try:
        if arch is None or arch not in ARCHS:
            return []
        lowend = tier == "lowend"
        rdna = arch in _RDNA
        items: list[dict] = []

        # 1. HYPR-RX (RDNA 2 et plus) : profil en un clic qui active des
        # fonctions indésirables en compétitif.
        if arch in _RDNA2_PLUS:
            items.append(_item(
                "hypr_rx_off",
                "HYPR-RX : désactivé pour CS2",
                "HYPR-RX: off for CS2",
                "Profil graphique du jeu : Personnalisé (pas HYPR-RX)",
                "Game graphics profile: Custom (not HYPR-RX)",
                "HYPR-RX active d'un coup plusieurs fonctions (Radeon Super "
                "Resolution, Radeon Boost, Radeon Anti-Lag et, selon la "
                "version, AMD Fluid Motion Frames). En compétitif, mieux vaut "
                "régler chacune à la main avec les valeurs ci-dessous.",
                "HYPR-RX turns on several features at once (Radeon Super "
                "Resolution, Radeon Boost, Radeon Anti-Lag and, depending on "
                "the version, AMD Fluid Motion Frames). For competitive play, "
                "set each one by hand with the values below."))

        # 2. Anti-Lag : version pilote + Anti-Lag 2 intégré au jeu (RDNA).
        if rdna:
            items.append(_item(
                "anti_lag",
                "Radeon Anti-Lag : activé (et AMD Anti-Lag 2 dans CS2 si présent)",
                "Radeon Anti-Lag: on (and AMD Anti-Lag 2 in CS2 if present)",
                "Activé",
                "Enabled",
                "Réduit le délai entre la souris et l'image quand le GPU est "
                "le facteur limitant. Si CS2 affiche l'option « AMD Anti-Lag "
                "2 » dans Vidéo avancé, activez-la dans le jeu : c'est la "
                "version intégrée à CS2 par Valve, celle qu'AMD recommande "
                "pour les jeux qui la proposent.",
                "Cuts the delay between your mouse and the image when the "
                "GPU is the bottleneck. If CS2 shows the “AMD Anti-Lag 2” "
                "option under Advanced Video, turn it on in the game: it is "
                "the version Valve built into CS2, the one AMD recommends "
                "for games that offer it."))
        elif arch in _LEGACY:
            items.append(_item(
                "anti_lag",
                "Radeon Anti-Lag (pilote) : activé si présent",
                "Radeon Anti-Lag (driver): on if present",
                "Activé (si l'option est présente)",
                "Enabled (if the option is present)",
                "AMD Anti-Lag 2 n'est pas pris en charge sur cette génération "
                "de GPU : seule la version pilote de Radeon Anti-Lag peut "
                "s'appliquer (CS2 tourne en DirectX 11 par défaut), si elle "
                "apparaît dans le profil du jeu. Utile surtout quand le GPU "
                "est saturé.",
                "AMD Anti-Lag 2 is not supported on this GPU generation: only "
                "the driver version of Radeon Anti-Lag can apply (CS2 runs on "
                "DirectX 11 by default), if it shows up in the game profile. "
                "Mostly useful when the GPU is maxed out."))
        else:
            # GPU AMD non identifié (APU « Radeon(TM) Graphics »...) : aucune
            # affirmation sur la prise en charge d'Anti-Lag 2.
            items.append(_item(
                "anti_lag",
                "Radeon Anti-Lag : activé si présent",
                "Radeon Anti-Lag: on if present",
                "Activé (si l'option est présente)",
                "Enabled (if the option is present)",
                "Réduit le délai entre la souris et l'image quand le GPU est "
                "le facteur limitant. Si CS2 affiche l'option « AMD Anti-Lag "
                "2 » dans Vidéo avancé, activez-la dans le jeu ; sinon, "
                "activez Radeon Anti-Lag dans le profil du jeu s'il y figure.",
                "Cuts the delay between your mouse and the image when the GPU "
                "is the bottleneck. If CS2 shows the “AMD Anti-Lag 2” option "
                "under Advanced Video, turn it on in the game; otherwise, "
                "enable Radeon Anti-Lag in the game profile if it is there."))

        # 3. Radeon Chill.
        items.append(_item(
            "chill_off",
            "Radeon Chill : désactivé",
            "Radeon Chill: off",
            "Désactivé",
            "Disabled",
            "Chill baisse volontairement les FPS quand la souris bouge peu : "
            "FPS irréguliers et latence variable, l'inverse du but recherché "
            "en compétitif.",
            "Chill deliberately lowers FPS when the mouse barely moves: "
            "uneven FPS and variable latency, the opposite of what you want "
            "in competitive play."))

        # 4. Radeon Boost.
        items.append(_item(
            "boost_off",
            "Radeon Boost : désactivé (si présent)",
            "Radeon Boost: off (if present)",
            "Désactivé",
            "Disabled",
            "Boost baisse la résolution pendant les mouvements rapides : "
            "l'image devient floue au moment précis où vous visez (flou de "
            "mouvement indésirable en compétitif).",
            "Boost lowers the resolution during fast movements: the image "
            "turns blurry exactly when you aim (unwanted motion blur in "
            "competitive play)."))

        # 5. AMD Fluid Motion Frames (RDNA 2 et plus).
        if arch in _RDNA2_PLUS:
            items.append(_item(
                "afmf_off",
                "AMD Fluid Motion Frames : désactivé (si présent)",
                "AMD Fluid Motion Frames: off (if present)",
                "Désactivé",
                "Disabled",
                "La génération d'images insère des images interpolées : le "
                "compteur de FPS monte, mais la latence d'entrée aussi, et "
                "ces images n'apportent aucune information de jeu. À éviter "
                "en compétitif.",
                "Frame generation inserts interpolated frames: the FPS "
                "counter goes up, but so does input latency, and those "
                "frames carry no game information. Avoid it in competitive "
                "play."))

        # 6. Radeon Super Resolution (RDNA).
        if rdna:
            items.append(_item(
                "rsr_off",
                "Radeon Super Resolution : désactivé",
                "Radeon Super Resolution: off",
                "Désactivé",
                "Disabled",
                "RSR agrandit toute l'image (interface comprise) rendue en "
                "plus basse résolution. Si vous avez besoin de FPS, préférez "
                "FSR directement dans les réglages vidéo de CS2 (si présent) : "
                "seule la scène 3D est concernée.",
                "RSR upscales the whole image (HUD included) rendered at a "
                "lower resolution. If you need FPS, prefer FSR directly in "
                "CS2's video settings (if present): only the 3D scene is "
                "affected."))

        # 7. Enhanced Sync.
        items.append(_item(
            "enhanced_sync_off",
            "Radeon Enhanced Sync : désactivé (si présent)",
            "Radeon Enhanced Sync: off (if present)",
            "Désactivé",
            "Disabled",
            "Cette synchronisation peut provoquer des saccades et une latence "
            "variable quand les FPS passent sous la fréquence de l'écran. "
            "Inutile quand on vise le maximum de FPS.",
            "This sync mode can cause stutters and variable latency when FPS "
            "drop below the monitor's refresh rate. Pointless when you aim "
            "for maximum FPS."))

        # 8. Synchronisation verticale imposée par le pilote.
        items.append(_item(
            "vsync_off",
            "Attendre la synchronisation verticale : Toujours désactivé",
            "Wait for Vertical Refresh: Always Off",
            "Toujours désactivé",
            "Always Off",
            "Empêche le pilote d'imposer la V-Sync, qui ajoute de la latence "
            "d'entrée. Le plafond de FPS se règle dans CS2 avec fps_max "
            "(autoexec Overdrive).",
            "Stops the driver from forcing V-Sync, which adds input latency. "
            "The FPS cap is set in CS2 with fps_max (Overdrive autoexec)."))

        # 9. Radeon Image Sharpening (optionnel).
        if lowend:
            ris_why = ("Accentue la netteté pour un coût minime. Surtout utile "
                       "si vous baissez la résolution ou activez FSR dans CS2 "
                       "pour gagner des FPS ; sinon, affaire de goût.")
            ris_why_en = ("Sharpens the image at a minimal cost. Mostly useful "
                          "if you lower the resolution or enable FSR in CS2 to "
                          "gain FPS; otherwise, a matter of taste.")
        else:
            ris_why = ("Accentue la netteté pour un coût minime. Affaire de "
                       "goût : laissez-le coupé si l'image vous convient.")
            ris_why_en = ("Sharpens the image at a minimal cost. A matter of "
                          "taste: leave it off if the image looks fine to you.")
        items.append(_item(
            "ris_optional",
            "Radeon Image Sharpening : optionnel (si présent)",
            "Radeon Image Sharpening: optional (if present)",
            "Au choix",
            "Your choice",
            ris_why, ris_why_en, optional=True))

        # 10. Optimisation du format de surface (Avancé).
        items.append(_item(
            "surface_format_on",
            "Optimisation du format de surface : activée (si présent)",
            "Surface Format Optimization: on (if present)",
            "Activée",
            "Enabled",
            "Valeur par défaut d'AMD, à rétablir si elle a été coupée : le "
            "pilote peut utiliser des formats de rendu plus légers sans "
            "perte visible. Effet faible sur CS2, mais aucune raison de la "
            "désactiver.",
            "AMD's default, to restore if it was turned off: the driver may "
            "use lighter render formats with no visible loss. Small effect "
            "on CS2, but no reason to disable it.",
            where=_WHERE_ADV, where_en=_WHERE_ADV_EN))

        # 11. Mode de tessellation (Avancé).
        items.append(_item(
            "tessellation_amd",
            "Mode de tessellation : Optimisé par AMD (si présent)",
            "Tessellation Mode: AMD Optimized (if present)",
            "Optimisé par AMD",
            "AMD Optimized",
            "Valeur par défaut, à rétablir si elle a été modifiée : CS2 "
            "sollicite peu la tessellation, forcer un autre réglage n'apporte "
            "rien de mesurable.",
            "The default, to restore if it was changed: CS2 makes little use "
            "of tessellation, forcing another setting brings nothing "
            "measurable.",
            where=_WHERE_ADV, where_en=_WHERE_ADV_EN))

        # 12. Cache de shaders (Avancé) : rappel lié aux saccades.
        items.append(_item(
            "shader_cache",
            "Cache de shaders : Optimisé par AMD (défaut)",
            "Shader Cache: AMD Optimized (default)",
            "Optimisé par AMD",
            "AMD Optimized",
            "Le cache évite de recompiler les shaders à chaque partie. Après "
            "une mise à jour du pilote, en cas de saccades persistantes, "
            "utilisez « Réinitialiser le cache de shaders » (ou le nettoyage "
            "des caches AMD d'Overdrive) : les premières parties suivantes "
            "recompilent les shaders (saccades temporaires).",
            "The cache avoids recompiling shaders every match. After a driver "
            "update, if stutters persist, use “Reset Shader Cache” (or "
            "Overdrive's AMD cache cleanup): the next few matches recompile "
            "the shaders (temporary stutters).",
            where=_WHERE_ADV, where_en=_WHERE_ADV_EN))

        # 13. Pilote des générations en maintenance (Polaris / Vega).
        if arch in _LEGACY:
            family = "RX 400/500 (Polaris)" if arch == "polaris" else "Vega"
            items.append(_item(
                "legacy_driver",
                "Pilote : dernière version proposée pour votre carte",
                "Driver: latest version offered for your card",
                "Dernière version listée pour votre modèle exact",
                "Latest version listed for your exact model",
                f"Selon AMD, les Radeon {family} sont en « mode maintenance » : "
                "plus d'optimisations par jeu, seulement des correctifs. "
                "Installez la dernière version listée pour votre modèle exact "
                "sur amd.com (sélection manuelle du produit) plutôt qu'un "
                "pilote modifié ou forcé.",
                f"According to AMD, Radeon {family} cards are in “maintenance "
                "mode”: no more per-game optimizations, only fixes. Install "
                "the latest version listed for your exact model on amd.com "
                "(manual product selection) rather than a modded or forced "
                "driver.",
                where="amd.com > Pilotes et assistance",
                where_en="amd.com > Drivers & Support"))

        return items
    except Exception:  # jamais d'exception vers l'appelant
        return []


# ---------------------------------------------------------------------------
# Ryzen 7000 / 8000 / 9000 (bureau)
# ---------------------------------------------------------------------------

#: « AMD Ryzen 5 8400F 6-Core Processor », « AMD Ryzen 7 7800X3D 8-Core
#: Processor »... Le suffixe distingue bureau (X, X3D, F, G, aucun) et
#: portable (U, H, HS, HX), exclu : ni EXPO ni pilote chipset AM5.
_RYZEN_RE = re.compile(r"\bryzen\s+[3579]\s+(?P<num>[789]\d{3})(?P<suffix>[a-z0-9]*)\b")

#: Ryzen X3D à deux CCD : le placement des threads du jeu repose sur le
#: pilote chipset (3D V-Cache Performance Optimizer) et la Game Bar.
_DUAL_CCD_X3D = frozenset({"7900x3d", "7950x3d", "9900x3d", "9950x3d"})


def _ryzen_model(cpu_name: object) -> tuple[str, str] | None:
    """(numéro, suffixe) d'un Ryzen 7000/8000/9000 de bureau, sinon None."""
    if not isinstance(cpu_name, str):
        return None
    match = _RYZEN_RE.search(cpu_name.lower())
    if match is None:
        return None
    suffix = match.group("suffix")
    if suffix.startswith(("u", "h")):
        return None  # Ryzen mobile (U/H/HS/HX)
    return match.group("num"), suffix


def is_dual_ccd_x3d(cpu_name: object) -> bool:
    """Vrai pour un Ryzen 9 X3D à deux CCD (7900X3D/7950X3D/9900X3D/9950X3D)."""
    model = _ryzen_model(cpu_name)
    return model is not None and (model[0] + model[1]) in _DUAL_CCD_X3D


def _tip(tip_id: str, title: str, title_en: str, detail: str,
         detail_en: str) -> dict:
    """Construit un rappel Ryzen au format commun."""
    return {"id": tip_id, "title": title, "title_en": title_en,
            "detail": detail, "detail_en": detail_en}


def ryzen_tips(cpu_name: object) -> list[dict]:
    """Rappels honnêtes pour un Ryzen 7000/8000/9000 de bureau.

    Chaque entrée : ``{"id", "title", "title_en", "detail", "detail_en"}``.
    Liste vide pour tout autre CPU (Intel, Ryzen plus anciens, Ryzen
    portables). Jamais d'exception.
    """
    try:
        model = _ryzen_model(cpu_name)
        if model is None:
            return []
        number, suffix = model
        tips = [
            _tip(
                "chipset_driver",
                "Pilote chipset AMD à jour",
                "Up-to-date AMD chipset driver",
                "Installez le dernier pilote chipset AMD pour votre carte mère "
                "AM5 depuis amd.com (Pilotes > Chipsets) : il apporte les "
                "réglages d'énergie et d'ordonnancement prévus pour votre "
                "processeur.",
                "Install the latest AMD chipset driver for your AM5 "
                "motherboard from amd.com (Drivers > Chipsets): it brings the "
                "power and scheduling settings intended for your CPU."),
            _tip(
                "expo",
                "EXPO activé dans le BIOS",
                "EXPO enabled in the BIOS",
                "Sans EXPO, la DDR5 tourne à sa vitesse de base (souvent 4800 "
                "MT/s) au lieu de la vitesse prévue par le kit (5600-6000 "
                "MT/s par exemple). Overdrive le vérifie dans la page "
                "Constats ; la marche à suivre y est détaillée.",
                "Without EXPO, DDR5 runs at its base speed (often 4800 MT/s) "
                "instead of the kit's rated speed (5600-6000 MT/s for "
                "example). Overdrive checks it on the Insights page, with "
                "step-by-step instructions."),
            _tip(
                "power_plan",
                "Pas de plan d'alimentation « Ryzen » spécial",
                "No special “Ryzen” power plan",
                "Sous Windows 11 (24H2 ou plus récent), aucun plan "
                "d'alimentation propre à Ryzen n'est nécessaire : l'ancien "
                "plan « AMD Ryzen Balanced » concernait d'anciennes "
                "générations sous Windows 10. Gardez Windows à jour.",
                "On Windows 11 (24H2 or newer), no Ryzen-specific power plan "
                "is needed: the old “AMD Ryzen Balanced” plan was for older "
                "generations on Windows 10. Keep Windows up to date."),
        ]
        if (number + suffix) in _DUAL_CCD_X3D:
            tips.append(_tip(
                "x3d_dual_ccd",
                "Ryzen X3D à deux CCD : pilote chipset et Game Bar requis",
                "Dual-CCD Ryzen X3D: chipset driver and Game Bar required",
                "Sur ce processeur, c'est le pilote chipset AMD (3D V-Cache "
                "Performance Optimizer) et la Xbox Game Bar à jour qui "
                "placent le jeu sur le CCD doté du cache 3D. Laissez le plan "
                "d'alimentation Windows sur Équilibré et ne désinstallez pas "
                "la Game Bar.",
                "On this CPU, the AMD chipset driver (3D V-Cache Performance "
                "Optimizer) and an up-to-date Xbox Game Bar place the game on "
                "the CCD with the 3D cache. Keep the Windows power plan on "
                "Balanced and do not uninstall the Game Bar."))
        if "g" in suffix:
            tips.append(_tip(
                "monitor_on_gpu",
                "Écran branché sur la carte graphique",
                "Monitor plugged into the graphics card",
                "Votre processeur a une puce graphique intégrée : si vous "
                "avez une carte graphique, branchez l'écran sur elle et non "
                "sur la carte mère, sinon CS2 tourne sur la puce intégrée.",
                "Your CPU has integrated graphics: if you have a graphics "
                "card, plug the monitor into it rather than the motherboard, "
                "otherwise CS2 runs on the integrated graphics."))
        return tips
    except Exception:  # jamais d'exception vers l'appelant
        return []


# ---------------------------------------------------------------------------
# Synthèse pour la machine détectée (route /api/amd)
# ---------------------------------------------------------------------------

_VIRTUAL_GPU_MARKERS = ("microsoft basic display", "virtual", "remote", "vnc")


def main_gpu_name(hw: dict | None) -> str | None:
    """Nom du GPU principal (dédié prioritaire, adaptateurs virtuels exclus)."""
    try:
        from overdrive.core.hardware import _is_igpu  # noqa: PLC0415 — cycle évité

        gpus = hw.get("gpus") if isinstance(hw, dict) else None
        names = []
        for gpu in gpus if isinstance(gpus, list) else []:
            if not isinstance(gpu, dict):
                continue
            name = str(gpu.get("name") or "").strip()
            if name and not any(m in name.lower() for m in _VIRTUAL_GPU_MARKERS):
                names.append(name)
        if not names:
            return None
        return next((n for n in names if not _is_igpu(n)), names[0])
    except Exception:
        return None


def amd_overview(hw: dict | None = None, tier: str | None = None) -> dict:
    """Conseils AMD pour la machine détectée (vides si pas d'AMD).

    Retour : ``{"arch", "gpu", "cpu", "tier", "checklist", "ryzen_tips"}``.
    ``arch``/``checklist`` concernent le GPU principal (dédié prioritaire) ;
    ``ryzen_tips`` le CPU. ``hw=None`` => :func:`detect_hardware` ;
    ``tier=None`` => tier CS2 détecté. Jamais d'exception.
    """
    result = {"arch": None, "gpu": None, "cpu": None, "tier": None,
              "checklist": [], "ryzen_tips": []}
    try:
        if hw is None:
            from overdrive.core.hardware import detect_hardware  # noqa: PLC0415

            hw = detect_hardware()
        if not isinstance(hw, dict):
            return result
        gpu = main_gpu_name(hw)
        cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
        cpu_name = str(cpu.get("name") or "").strip() or None
        arch = gpu_arch(gpu)
        if tier not in ("lowend", "midrange", "highend"):
            try:
                from overdrive.core.games.cs2 import detect_tier  # noqa: PLC0415

                tier = detect_tier(hw).get("tier")
            except Exception:
                tier = None
        result.update({
            "arch": arch,
            "gpu": gpu if arch is not None else None,
            "cpu": cpu_name,
            "tier": tier,
            "checklist": adrenalin_checklist(arch, tier),
            "ryzen_tips": ryzen_tips(cpu_name),
        })
        return result
    except Exception:  # jamais d'exception vers l'appelant
        return result
