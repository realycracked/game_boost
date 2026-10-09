"""« Boost CS2 » en un clic : tweaks Windows ciblés, vidéo et autoexec par tier.

Deux fonctions publiques, sans aucune exception vers l'appelant :

* :func:`plan` : prévisualisation (rien n'est modifié) — tier retenu,
  étapes, tweaks prévus (ids RÉELS du catalogue), aperçu du plan vidéo,
  de l'autoexec et des étapes manuelles ;
* :func:`run` : exécution séquentielle — 1. point de restauration ;
  2. tweaks Windows pertinents pour CS2 non encore appliqués (risque
  « sûr » ou « modéré » uniquement) ; 3. réglages vidéo du tier via
  :func:`overdrive.core.games.cs2.apply_video_settings` (sauvegarde du
  coffre incluse, refus si CS2 tourne) ; 4. autoexec du tier via
  :func:`overdrive.core.games.cs2.write_autoexec` (un autoexec personnel
  n'est jamais écrasé ici).

Chaque étape rend ``{"step", "label", "label_en", "ok", "message",
"message_en", "details", "skipped"}`` ; ``manual_steps`` regroupe ce que
l'utilisateur doit faire lui-même (checklist AMD Adrenalin, options de
lancement du tier, constats utiles comme EXPO/XMP, options petite config).

Sous Linux, :func:`run` refuse proprement chaque étape et :func:`plan`
reste un aperçu (``supported: False``). Le plan ``lowend`` (ex. RX 570)
est volontairement différent : vidéo au plus bas utile, FSR Qualité
proposé comme option explicite, et rappel que la résolution est le levier
n°1 de FPS — à choisir par l'utilisateur dans le jeu, jamais modifiée.
"""

from __future__ import annotations

import re
import threading
from typing import Any

from overdrive.paths import is_windows

_TIERS: tuple[str, ...] = ("lowend", "midrange", "highend")

#: Libellés de repli des tiers (FR, EN) si cs2.py est indisponible.
_TIER_LABELS_FALLBACK: dict[str, tuple[str, str]] = {
    "lowend": ("Petite config", "Low-end machine"),
    "midrange": ("Milieu de gamme", "Mid-range machine"),
    "highend": ("Haut de gamme", "High-end machine"),
}

_WINDOWS_ONLY = "Disponible uniquement sous Windows."
_WINDOWS_ONLY_EN = "Windows only."

#: Risques acceptés pour une application automatique (catalogue des tweaks).
_ALLOWED_RISKS = frozenset({"sur", "modere"})

#: Sélection explicite d'ids du catalogue des tweaks, dans l'ordre
#: d'application. Un id absent du catalogue est ignoré proprement.
_BASE_TWEAKS: tuple[str, ...] = (
    "game_mode_on",             # Mode Jeu (actif par défaut, rétabli s'il a été coupé)
    "gamedvr_off",              # capture Game DVR en arrière-plan
    "game_bar_off",             # overlay Xbox Game Bar
    "hags_on",                  # HAGS, uniquement sur GPU compatible (voir _hags_decision)
    "power_plan_ultimate",      # plan d'alimentation performant (bureau uniquement)
    "games_task_gpu_priority",  # priorité MMCSS du profil « Games »
    "system_responsiveness_0",  # réserve MMCSS dédiée au jeu
    "mouse_accel_off",          # souris brute (cohérence bureau / jeux sans Raw Input)
)
#: Ajouts petite config : libèrent CPU/RAM sur une machine modeste.
_LOWEND_TWEAKS: tuple[str, ...] = (
    "background_apps_off",
    "edge_preload_off",
    "delivery_optimization_off",
)

#: GPU NVIDIA prenant en charge HAGS (Pascal / GTX 10 et plus récents).
_NVIDIA_HAGS_RE = re.compile(r"rtx\s*\d{4}|gtx\s*1[06]\d{2}", re.IGNORECASE)

#: Un seul Boost CS2 à la fois (restauration + registre + fichiers).
_RUN_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Contexte matériel
# ---------------------------------------------------------------------------


def _hardware() -> dict:
    """Matériel détecté (cache), ``{}`` en cas d'échec."""
    try:
        from overdrive.core.hardware import detect_hardware  # noqa: PLC0415

        hw = detect_hardware()
        return hw if isinstance(hw, dict) else {}
    except Exception:
        return {}


def _tier_label(tier: str | None) -> tuple[str, str]:
    """Libellé lisible (FR, EN) du tier effectif, jamais l'identifiant brut."""
    labels: dict = _TIER_LABELS_FALLBACK
    try:
        from overdrive.core.games.cs2 import _TIER_LABELS  # noqa: PLC0415

        if isinstance(_TIER_LABELS, dict):
            labels = _TIER_LABELS
    except Exception:
        labels = _TIER_LABELS_FALLBACK
    pair = labels.get(tier) or _TIER_LABELS_FALLBACK.get(tier or "")
    if not pair:
        return (str(tier or "—"), str(tier or "—"))
    return (str(pair[0]), str(pair[1]))


def _context(tier: str | None) -> dict:
    """Tier retenu (forcé ou détecté), infos tier, GPU et CPU."""
    hw = _hardware()
    tier_info: dict = {}
    try:
        from overdrive.core.games.cs2 import detect_tier  # noqa: PLC0415

        tier_info = detect_tier(hw or None)
    except Exception:
        tier_info = {}
    detected = tier_info.get("tier") if tier_info.get("tier") in _TIERS else "midrange"
    forced = tier in _TIERS
    cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
    gpu_name = tier_info.get("gpu_name")
    arch = tier_info.get("gpu_arch")
    if not gpu_name:
        try:
            from overdrive.core.amd import gpu_arch, main_gpu_name  # noqa: PLC0415

            gpu_name = main_gpu_name(hw)
            arch = gpu_arch(gpu_name)
        except Exception:
            gpu_name, arch = None, None
    return {
        "hw": hw,
        "tier": tier if forced else detected,
        "tier_source": "forced" if forced else "detected",
        "tier_info": tier_info,
        "gpu_name": gpu_name,
        "gpu_vendor": tier_info.get("gpu_vendor"),
        "gpu_arch": arch,
        "cpu_name": str(cpu.get("name") or "").strip() or None,
    }


def _has_battery() -> bool:
    """Vrai si une batterie est détectée (PC portable), best effort."""
    try:
        import psutil  # noqa: PLC0415

        return psutil.sensors_battery() is not None
    except Exception:
        return False


def _cs2_running() -> bool:
    """Vrai si CS2 tourne (scan frais de cs2.is_cs2_running)."""
    try:
        from overdrive.core.games.cs2 import is_cs2_running  # noqa: PLC0415

        return bool(is_cs2_running())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Sélection des tweaks
# ---------------------------------------------------------------------------


def _hags_decision(ctx: dict) -> tuple[bool, str, str]:
    """(appliquer HAGS ?, raison FR, raison EN) selon la génération du GPU."""
    vendor = ctx.get("gpu_vendor")
    arch = ctx.get("gpu_arch")
    name = str(ctx.get("gpu_name") or "")
    if arch in ("rdna3", "rdna4"):
        return True, "GPU AMD RDNA 3/4 compatible HAGS.", "HAGS-capable AMD RDNA 3/4 GPU."
    if vendor == "nvidia" and _NVIDIA_HAGS_RE.search(name):
        return True, "GPU NVIDIA compatible HAGS.", "HAGS-capable NVIDIA GPU."
    if arch == "polaris":
        return (False,
                "HAGS non forcé : non pris en charge sur les Radeon Polaris (RX 400/500).",
                "HAGS not forced: not supported on Radeon Polaris (RX 400/500).")
    return (False,
            "HAGS non forcé : prise en charge non garantie sur ce GPU.",
            "HAGS not forced: support not guaranteed on this GPU.")


def _tweak_entry(tweak_id: str, catalog_entry: dict | None, status: str,
                 reason: str, reason_en: str) -> dict:
    """Ligne de tweak du plan/compte rendu."""
    entry = catalog_entry or {}
    return {
        "id": tweak_id,
        "name": entry.get("name") or tweak_id,
        "name_en": entry.get("name_en") or entry.get("name") or tweak_id,
        "risk": entry.get("risk"),
        "status": status,  # pending | already | skipped | unsupported
        "reason": reason,
        "reason_en": reason_en,
    }


def _select_tweaks(ctx: dict) -> tuple[list[dict], list[str]]:
    """(lignes de tweaks, ids absents du catalogue) pour ce contexte.

    Lit le catalogue RÉEL (``engine.list_tweaks``) : id absent => ignoré
    proprement ; risque au-delà de « modéré » => écarté ; déjà appliqué
    (suivi Overdrive ou contrôle registre) => « already ».
    """
    try:
        from overdrive.core.tweaks.engine import list_tweaks  # noqa: PLC0415

        catalog = {t["id"]: t for t in list_tweaks() if isinstance(t, dict) and t.get("id")}
    except Exception:
        catalog = {}

    candidates = list(_BASE_TWEAKS)
    if ctx.get("tier") == "lowend":
        candidates += list(_LOWEND_TWEAKS)

    cpu_name = ctx.get("cpu_name")
    try:
        from overdrive.core.amd import is_dual_ccd_x3d  # noqa: PLC0415

        dual_x3d = is_dual_ccd_x3d(cpu_name)
    except Exception:
        dual_x3d = False
    laptop = _has_battery()
    hags_ok, hags_reason, hags_reason_en = _hags_decision(ctx)

    rows: list[dict] = []
    missing: list[str] = []
    for tweak_id in candidates:
        entry = catalog.get(tweak_id)
        if entry is None:
            missing.append(tweak_id)
            continue
        if tweak_id == "hags_on" and not hags_ok:
            rows.append(_tweak_entry(tweak_id, entry, "skipped", hags_reason, hags_reason_en))
            continue
        if dual_x3d and tweak_id in ("power_plan_ultimate", "game_bar_off"):
            rows.append(_tweak_entry(
                tweak_id, entry, "skipped",
                "Ryzen X3D à deux CCD : plan Équilibré et Game Bar nécessaires au "
                "placement du jeu sur le bon CCD.",
                "Dual-CCD Ryzen X3D: Balanced plan and Game Bar are needed to "
                "place the game on the right CCD."))
            continue
        if laptop and tweak_id == "power_plan_ultimate":
            rows.append(_tweak_entry(
                tweak_id, entry, "skipped",
                "PC portable détecté : plan non forcé (chauffe et autonomie).",
                "Laptop detected: plan not forced (heat and battery life)."))
            continue
        if entry.get("risk") not in _ALLOWED_RISKS:
            rows.append(_tweak_entry(
                tweak_id, entry, "skipped",
                "Risque au-delà de « modéré » : jamais appliqué automatiquement.",
                "Risk above “moderate”: never applied automatically."))
            continue
        if not entry.get("supported", False):
            rows.append(_tweak_entry(tweak_id, entry, "unsupported",
                                     _WINDOWS_ONLY, _WINDOWS_ONLY_EN))
            continue
        if entry.get("tracked") or entry.get("applied") is True:
            rows.append(_tweak_entry(tweak_id, entry, "already",
                                     "Déjà en place.", "Already in place."))
            continue
        reason, reason_en = ("", "")
        if tweak_id == "hags_on":
            reason = hags_reason + " Redémarrage requis."
            reason_en = hags_reason_en + " Reboot required."
        rows.append(_tweak_entry(tweak_id, entry, "pending", reason, reason_en))
    return rows, missing


# ---------------------------------------------------------------------------
# Étapes manuelles (checklist AMD, options de lancement, constats, options)
# ---------------------------------------------------------------------------


def _manual(step_id: str, kind: str, title: str, title_en: str, detail: str,
            detail_en: str, **extra: Any) -> dict:
    """Étape manuelle au format commun."""
    item = {"id": step_id, "kind": kind, "title": title, "title_en": title_en,
            "detail": detail, "detail_en": detail_en}
    item.update(extra)
    return item


def _lowend_steps() -> list[dict]:
    """Étapes propres à la petite config : résolution (levier n°1) et FSR."""
    return [
        _manual(
            "lowend_resolution", "lowend",
            "Levier n°1 : la résolution (à choisir vous-même)",
            "Lever #1: resolution (your choice)",
            "Quand la carte graphique est le facteur limitant (cas fréquent "
            "sur une petite config, une RX 570 par exemple), baisser la "
            "résolution est le levier n°1 de FPS, devant tous les autres "
            "réglages : par exemple 1280×960 en 4:3 étiré, ou 1600×900 / "
            "1280×720 en 16:9. À régler dans CS2 > Paramètres > Vidéo > "
            "Résolution. Si c'est le processeur qui limite, la résolution "
            "change peu : fermez plutôt les programmes en arrière-plan. "
            "Overdrive ne modifie jamais votre résolution.",
            "When the graphics card is the bottleneck (common on a low-end "
            "machine, an RX 570 for instance), lowering the resolution is the "
            "#1 FPS lever, ahead of every other setting: for example 1280×960 "
            "stretched 4:3, or 1600×900 / 1280×720 in 16:9. Set it in CS2 > "
            "Settings > Video > Resolution. If the CPU is the bottleneck, "
            "resolution changes little: close background programs instead. "
            "Overdrive never changes your resolution.",
            where="CS2 > Paramètres > Vidéo > Résolution",
            where_en="CS2 > Settings > Video > Resolution"),
        _manual(
            "fsr_quality", "option",
            "Option : FidelityFX Super Resolution en mode Qualité",
            "Option: FidelityFX Super Resolution on Quality",
            "Si vous préférez garder la résolution native de l'écran, FSR en "
            "mode Qualité fait le rendu 3D en plus basse définition puis "
            "l'agrandit : plus de FPS, image un peu plus douce (l'interface "
            "reste nette). Option à essayer, non appliquée automatiquement ; "
            "Radeon Image Sharpening peut compenser la douceur.",
            "If you would rather keep the monitor's native resolution, FSR on "
            "Quality renders the 3D scene at a lower resolution then upscales "
            "it: more FPS, slightly softer image (the HUD stays sharp). An "
            "option to try, not applied automatically; Radeon Image "
            "Sharpening can offset the softness.",
            optional=True,
            value="Qualité", value_en="Quality",
            where="CS2 > Paramètres > Vidéo avancé > FidelityFX Super Resolution",
            where_en="CS2 > Settings > Advanced Video > FidelityFX Super Resolution"),
    ]


def _launch_step(tier: str, hw: dict) -> dict | None:
    """Options de lancement Steam du tier, à coller par l'utilisateur."""
    try:
        from overdrive.core.games.cs2 import launch_options_for  # noqa: PLC0415

        launch = launch_options_for(tier, hw or None)
    except Exception:
        return None
    options = str(launch.get("options") or "")
    if not options:
        return None
    return _manual(
        "launch_options", "launch_options",
        "Options de lancement Steam",
        "Steam launch options",
        f"{launch.get('note') or ''} Indispensable pour que l'autoexec soit "
        "chargé (+exec autoexec.cfg).".strip(),
        f"{launch.get('note_en') or ''} Required for the autoexec to load "
        "(+exec autoexec.cfg).".strip(),
        value=options, value_en=options,
        where=("Steam > Bibliothèque > clic droit sur Counter-Strike 2 > "
               "Propriétés > Général > Options de lancement"),
        where_en=("Steam > Library > right-click Counter-Strike 2 > "
                  "Properties > General > Launch options"))


def _insight_steps(insights: list[dict]) -> list[dict]:
    """Constats utiles à CS2 convertis en étapes manuelles."""
    steps: list[dict] = []
    for insight in insights if isinstance(insights, list) else []:
        if not isinstance(insight, dict):
            continue
        insight_id = str(insight.get("id") or "")
        if not (insight_id.startswith(("display_refresh_", "overlay_"))
                or insight_id in ("ram_below_rated", "ram_single_channel")):
            continue
        steps.append(_manual(
            insight_id, "insight",
            str(insight.get("title") or ""), str(insight.get("title_en") or ""),
            str(insight.get("detail") or ""), str(insight.get("detail_en") or ""),
            severity=insight.get("severity")))
    # Constats « important » d'abord (EXPO, écran sous-cadencé).
    steps.sort(key=lambda s: 0 if s.get("severity") == "important" else 1)
    return steps


def _manual_steps(ctx: dict, insights: list[dict]) -> list[dict]:
    """Toutes les étapes manuelles, de la plus rentable à la plus optionnelle."""
    steps: list[dict] = []
    tier = ctx.get("tier")
    try:
        steps.extend(_insight_steps(insights))
    except Exception:
        pass
    if tier == "lowend":
        steps.append(_lowend_steps()[0])
    launch = _launch_step(str(tier), ctx.get("hw") or {})
    if launch is not None:
        steps.append(launch)
    try:
        from overdrive.core.amd import adrenalin_checklist, ryzen_tips  # noqa: PLC0415

        for item in adrenalin_checklist(ctx.get("gpu_arch"), tier):
            steps.append(_manual(
                f"adrenalin_{item['id']}", "adrenalin",
                item["title"], item["title_en"], item["why"], item["why_en"],
                value=item["value"], value_en=item["value_en"],
                where=item["where"], where_en=item["where_en"],
                optional=bool(item.get("optional"))))
        has_ram_insight = any(s.get("id") == "ram_below_rated" for s in steps)
        for tip in ryzen_tips(ctx.get("cpu_name")):
            if tip["id"] == "expo" and has_ram_insight:
                continue  # déjà couvert par le constat RAM détaillé
            steps.append(_manual(
                f"ryzen_{tip['id']}", "cpu",
                tip["title"], tip["title_en"], tip["detail"], tip["detail_en"]))
    except Exception:
        pass
    if tier == "lowend":
        steps.append(_lowend_steps()[1])
    return steps


def _relevant_insights() -> list[dict]:
    """Constats rapides utiles à CS2 (``[]`` hors Windows), jamais d'exception."""
    try:
        from overdrive.core.insights import cs2_relevant_insights  # noqa: PLC0415

        return cs2_relevant_insights()
    except Exception:
        return []


def _notes(tier: str) -> list[dict]:
    """Résumé de l'orientation du plan selon le tier."""
    if tier == "lowend":
        return [{
            "id": "lowend_focus",
            "text": ("Plan petite config : réglages vidéo au plus bas utile "
                     "(MSAA coupé, shaders, textures et particules au minimum, "
                     "ombres basses mais conservées car elles informent), cap "
                     "de FPS stable dans l'autoexec et tweaks qui libèrent le "
                     "CPU. La résolution reste votre choix : c'est le levier "
                     "n°1 sur ce GPU."),
            "text_en": ("Low-end plan: lowest useful video settings (MSAA off, "
                        "shaders, textures and particles at minimum, shadows "
                        "low but kept because they carry information), a "
                        "steady FPS cap in the autoexec and tweaks that free "
                        "up the CPU. Resolution remains your call: it is the "
                        "#1 lever on this GPU."),
        }]
    return [{
        "id": "balanced_focus",
        "text": ("Plan compétitif : réglages qui coûtent des FPS sans aider à "
                 "voir l'adversaire au minimum, lisibilité conservée (MSAA, "
                 "filtrage), cap de FPS adapté à votre écran dans l'autoexec."),
        "text_en": ("Competitive plan: settings that cost FPS without helping "
                    "you spot opponents at minimum, readability kept (MSAA, "
                    "filtering), FPS cap matched to your monitor in the "
                    "autoexec."),
    }]


# ---------------------------------------------------------------------------
# Aperçus vidéo / autoexec
# ---------------------------------------------------------------------------


def _video_preview(ctx: dict) -> list[dict]:
    """Plan vidéo du tier confronté au cs2_video.txt actuel (lecture seule)."""
    try:
        from overdrive.core.games.cs2 import (  # noqa: PLC0415
            max_refresh_hz,
            read_current_video_settings,
            video_plan,
        )

        current = read_current_video_settings()
        plan_rows = video_plan(ctx["tier"], current, tier_info=ctx.get("tier_info") or None,
                               hz_max=max_refresh_hz())
    except Exception:
        return []
    preview: list[dict] = []
    for row in plan_rows:
        if not isinstance(row, dict):
            continue
        preview.append({
            "id": row.get("id"),
            "label": row.get("label"),
            "label_en": row.get("label_en"),
            "current": row.get("current"),
            "recommended": row.get("recommended"),
            "applicable": bool(row.get("applicable")),
            "will_change": bool(row.get("applicable"))
            and row.get("current") != row.get("recommended"),
            "skip_reason": row.get("skip_reason"),
            "menu_path": row.get("menu_path"),
            "menu_path_en": row.get("menu_path_en"),
            "protected": bool(row.get("protected")),
        })
    return preview


def _autoexec_preview(tier: str) -> dict:
    """État de l'autoexec actuel et contenu qui serait écrit."""
    status: dict = {"profile": None, "path": None, "exists": False, "by_overdrive": False}
    content = ""
    try:
        from overdrive.core.games.cs2 import autoexec_status, generate_autoexec  # noqa: PLC0415

        status = autoexec_status()
        content = generate_autoexec(status.get("profile"), tier)
    except Exception:
        pass
    personal = bool(status.get("exists")) and not status.get("by_overdrive")
    return {"status": status, "preview": content, "personal_kept": personal}


# ---------------------------------------------------------------------------
# Comptes rendus d'étapes
# ---------------------------------------------------------------------------


def _step(step: str, label: str, label_en: str, ok: bool, message: str,
          message_en: str, details: list | None = None,
          skipped: bool = False) -> dict:
    """Compte rendu structuré d'une étape du Boost CS2."""
    return {
        "step": step,
        "label": label,
        "label_en": label_en,
        "ok": bool(ok),
        "message": message,
        "message_en": message_en,
        "details": details or [],
        "skipped": bool(skipped),
    }


_LABELS: dict[str, tuple[str, str]] = {
    "restore": ("Point de restauration", "Restore point"),
    "tweaks": ("Tweaks Windows pour CS2", "Windows tweaks for CS2"),
    "video": ("Réglages vidéo CS2", "CS2 video settings"),
    "autoexec": ("Autoexec CS2", "CS2 autoexec"),
}


def _not_requested(step: str) -> dict:
    """Étape désactivée par l'appelant."""
    label, label_en = _LABELS[step]
    return _step(step, label, label_en, True, "Étape non demandée.",
                 "Step not requested.", skipped=True)


def _windows_only(step: str) -> dict:
    """Refus propre hors Windows."""
    label, label_en = _LABELS[step]
    return _step(step, label, label_en, False, _WINDOWS_ONLY, _WINDOWS_ONLY_EN)


def _run_restore() -> dict:
    """Étape 1 : point de restauration système."""
    label, label_en = _LABELS["restore"]
    try:
        from overdrive.core.tweaks.engine import create_restore_point  # noqa: PLC0415

        result = create_restore_point("Overdrive Boost CS2")
        ok = bool(result.get("ok"))
        return _step("restore", label, label_en, ok, str(result.get("message") or ""),
                     "Restore point created (or a recent one exists)." if ok
                     else "Could not create the restore point.")
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("restore", label, label_en, False, f"Erreur inattendue : {exc}",
                     f"Unexpected error: {exc}")


def _run_tweaks(ctx: dict) -> tuple[dict, bool]:
    """Étape 2 : tweaks ciblés non encore appliqués. (compte rendu, redémarrage ?)"""
    label, label_en = _LABELS["tweaks"]
    try:
        rows, missing = _select_tweaks(ctx)
        pending = [r["id"] for r in rows if r["status"] == "pending"]
        already = sum(1 for r in rows if r["status"] == "already")
        if not pending:
            return _step("tweaks", label, label_en, True,
                         f"Rien à appliquer ({already} tweak(s) déjà en place).",
                         f"Nothing to apply ({already} tweak(s) already in place).",
                         details=rows), False

        from overdrive.core.tweaks.engine import apply_tweaks  # noqa: PLC0415

        results = apply_tweaks(pending)
        by_id = {str(r.get("id")): r for r in results if isinstance(r, dict)}
        ok_count = 0
        for row in rows:
            result = by_id.get(row["id"])
            if result is None:
                continue
            row["status"] = "applied" if result.get("ok") else "failed"
            row["message"] = result.get("message")
            ok_count += 1 if result.get("ok") else 0
        reboot = any(r["id"] == "hags_on" and r["status"] == "applied" for r in rows)
        message = (f"{ok_count}/{len(pending)} tweak(s) appliqué(s) "
                   f"({already} déjà en place).")
        message_en = (f"{ok_count}/{len(pending)} tweak(s) applied "
                      f"({already} already in place).")
        if reboot:
            message += " Redémarrez le PC pour activer HAGS."
            message_en += " Restart the PC to enable HAGS."
        if missing:
            message += f" {len(missing)} id(s) absent(s) du catalogue ignoré(s)."
            message_en += f" {len(missing)} id(s) missing from the catalog ignored."
        return _step("tweaks", label, label_en, ok_count == len(pending), message,
                     message_en, details=rows), reboot
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("tweaks", label, label_en, False, f"Erreur inattendue : {exc}",
                     f"Unexpected error: {exc}"), False


def _run_video(tier: str) -> dict:
    """Étape 3 : plan vidéo du tier (sauvegarde coffre, refus si CS2 tourne)."""
    label, label_en = _LABELS["video"]
    try:
        if _cs2_running():
            return _step("video", label, label_en, False,
                         "CS2 est en cours d'exécution : fermez le jeu puis relancez "
                         "le Boost CS2 (il écraserait les réglages en quittant).",
                         "CS2 is running: close the game and run CS2 Boost again (it "
                         "would overwrite the settings on exit).")
        from overdrive.core.games.cs2 import apply_video_settings  # noqa: PLC0415

        result = apply_video_settings(None, tier)
        ok = bool(result.get("ok"))
        changed = result.get("changed") if isinstance(result.get("changed"), list) else []
        details = [{"key": c.get("key"), "old": c.get("old"), "new": c.get("new")}
                   for c in changed if isinstance(c, dict)]
        return _step("video", label, label_en, ok, str(result.get("message") or ""),
                     f"{len(details)} setting(s) applied; backup in the Vault." if ok
                     else "Video settings not applied (see the French message).",
                     details=details)
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("video", label, label_en, False, f"Erreur inattendue : {exc}",
                     f"Unexpected error: {exc}")


def _run_autoexec(tier: str) -> dict:
    """Étape 4 : autoexec du tier (jamais d'écrasement d'un autoexec personnel)."""
    label, label_en = _LABELS["autoexec"]
    try:
        from overdrive.core.games.cs2 import autoexec_status, write_autoexec  # noqa: PLC0415

        status = autoexec_status()
        if status.get("exists") and not status.get("by_overdrive"):
            return _step("autoexec", label, label_en, True,
                         "autoexec.cfg personnel détecté : conservé tel quel. "
                         "Remplacez-le depuis le panneau CS2 si vous le souhaitez "
                         "(copie .bak automatique).",
                         "Personal autoexec.cfg detected: kept as-is. Replace it "
                         "from the CS2 panel if you wish (automatic .bak copy).",
                         details=[{"path": status.get("path")}], skipped=True)
        result = write_autoexec(user_id=None, tier=tier)
        ok = bool(result.get("ok"))
        return _step("autoexec", label, label_en, ok, str(result.get("message") or ""),
                     "autoexec.cfg written for this tier." if ok
                     else "autoexec.cfg not written (see the French message).",
                     details=[{"path": result.get("path")}] if result.get("path") else [])
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("autoexec", label, label_en, False, f"Erreur inattendue : {exc}",
                     f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def plan(tier: str | None = None) -> dict:
    """Prévisualise le Boost CS2 (aucune modification). Jamais d'exception.

    ``tier`` : ``lowend`` / ``midrange`` / ``highend`` pour forcer, sinon
    tier CS2 détecté. Retour : ``{"ok", "supported", "message",
    "message_en", "tier", "tier_source", "tier_label", "tier_label_en"
    (libellé du tier effectif, forcé ou détecté), "tier_info" (détection,
    même quand le tier est forcé), "gpu", "cs2_running",
    "steps", "tweaks", "missing_tweaks", "video", "autoexec",
    "manual_steps", "notes"}``.
    """
    try:
        ctx = _context(tier)
        supported = is_windows()
        rows, missing = _select_tweaks(ctx)
        video = _video_preview(ctx)
        autoexec = _autoexec_preview(ctx["tier"])
        insights = _relevant_insights()
        running = _cs2_running() if supported else False
        pending = [r for r in rows if r["status"] == "pending"]
        changes = [v for v in video if v["will_change"]]

        steps = [
            {"step": "restore", "label": _LABELS["restore"][0],
             "label_en": _LABELS["restore"][1], "will_run": supported,
             "description": "Point de restauration système avant toute modification.",
             "description_en": "System restore point before any change.",
             "details": []},
            {"step": "tweaks", "label": _LABELS["tweaks"][0],
             "label_en": _LABELS["tweaks"][1],
             "will_run": supported and bool(pending),
             "description": (f"{len(pending)} tweak(s) à appliquer, risque sûr ou "
                             "modéré uniquement, tous réversibles depuis la page "
                             "Optimisations."),
             "description_en": (f"{len(pending)} tweak(s) to apply, safe or "
                                "moderate risk only, all revertible from the "
                                "Tweaks page."),
             "details": rows},
            {"step": "video", "label": _LABELS["video"][0],
             "label_en": _LABELS["video"][1], "will_run": supported,
             "description": (f"Plan vidéo « {_tier_label(ctx['tier'])[0]} » : {len(changes)} "
                             "réglage(s) à modifier dans votre cs2_video.txt "
                             "(sauvegarde du coffre avant écriture, refus si CS2 "
                             "tourne)."),
             "description_en": (f"“{_tier_label(ctx['tier'])[1]}” video plan: {len(changes)} "
                                "setting(s) to change in your cs2_video.txt "
                                "(Vault backup before writing, refused while CS2 "
                                "is running)."),
             "details": video},
            {"step": "autoexec", "label": _LABELS["autoexec"][0],
             "label_en": _LABELS["autoexec"][1],
             "will_run": supported and not autoexec["personal_kept"],
             "description": ("autoexec.cfg personnel détecté : il sera conservé."
                             if autoexec["personal_kept"] else
                             "Écriture de l'autoexec du tier (ancien fichier "
                             "sauvegardé en .bak)."),
             "description_en": ("Personal autoexec.cfg detected: it will be kept."
                                if autoexec["personal_kept"] else
                                "Writes the tier's autoexec (previous file saved "
                                "as .bak)."),
             "details": []},
        ]
        if supported:
            message = ("Aperçu du Boost CS2 : rien n'est modifié tant que vous "
                       "n'avez pas lancé le Boost.")
            message_en = ("CS2 Boost preview: nothing changes until you run the "
                          "Boost.")
            if running:
                message += " CS2 est lancé : fermez-le avant de lancer le Boost."
                message_en += " CS2 is running: close it before running the Boost."
        else:
            message = "Aperçu uniquement : le Boost CS2 ne s'applique que sous Windows."
            message_en = "Preview only: CS2 Boost only applies on Windows."
        return {
            "ok": True,
            "supported": supported,
            "message": message,
            "message_en": message_en,
            "tier": ctx["tier"],
            "tier_source": ctx["tier_source"],
            "tier_label": _tier_label(ctx["tier"])[0],
            "tier_label_en": _tier_label(ctx["tier"])[1],
            "tier_info": ctx["tier_info"],
            "gpu": {"name": ctx["gpu_name"], "vendor": ctx["gpu_vendor"],
                    "arch": ctx["gpu_arch"]},
            "cs2_running": running,
            "steps": steps,
            "tweaks": rows,
            "missing_tweaks": missing,
            "video": video,
            "autoexec": autoexec,
            "manual_steps": _manual_steps(ctx, insights),
            "notes": _notes(ctx["tier"]),
        }
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {
            "ok": False, "supported": is_windows(),
            "message": f"Aperçu du Boost CS2 impossible : {exc}",
            "message_en": f"CS2 Boost preview failed: {exc}",
            "tier": tier if tier in _TIERS else None, "tier_source": None,
            "tier_info": {}, "gpu": {}, "cs2_running": False, "steps": [],
            "tweaks": [], "missing_tweaks": [], "video": [],
            "autoexec": {}, "manual_steps": [], "notes": [],
        }


def run(tier: str | None = None, apply_video: bool = True,
        write_autoexec: bool = True, restore_point: bool = True) -> dict:
    """Lance le Boost CS2 : restauration, tweaks, vidéo, autoexec. Jamais d'exception.

    Retour : ``{"ok", "supported", "message", "message_en", "tier",
    "tier_source", "steps", "manual_steps", "notes", "reboot_required"}``.
    Le ``ok`` global n'est vrai que si toutes les étapes (non désactivées)
    ont réussi. Un seul Boost CS2 à la fois.
    """
    if not _RUN_LOCK.acquire(blocking=False):
        return {"ok": False, "supported": is_windows(),
                "message": "Un Boost CS2 est déjà en cours.",
                "message_en": "A CS2 Boost is already running.",
                "tier": tier if tier in _TIERS else None, "tier_source": None,
                "steps": [], "manual_steps": [], "notes": [],
                "reboot_required": False}
    try:
        ctx = _context(tier)
        supported = is_windows()
        steps: list[dict] = []
        reboot = False
        if not supported:
            steps.append(_windows_only("restore") if restore_point
                         else _not_requested("restore"))
            steps.append(_windows_only("tweaks"))
            steps.append(_windows_only("video") if apply_video
                         else _not_requested("video"))
            steps.append(_windows_only("autoexec") if write_autoexec
                         else _not_requested("autoexec"))
        else:
            steps.append(_run_restore() if restore_point else _not_requested("restore"))
            tweaks_step, reboot = _run_tweaks(ctx)
            steps.append(tweaks_step)
            steps.append(_run_video(ctx["tier"]) if apply_video
                         else _not_requested("video"))
            steps.append(_run_autoexec(ctx["tier"]) if write_autoexec
                         else _not_requested("autoexec"))
        ok = all(step["ok"] for step in steps)
        insights = _relevant_insights()
        if not supported:
            message, message_en = (_WINDOWS_ONLY, _WINDOWS_ONLY_EN)
        elif ok:
            message = ("Boost CS2 terminé. Terminez avec les étapes manuelles "
                       "ci-dessous (Adrenalin, options de lancement...).")
            message_en = ("CS2 Boost done. Finish with the manual steps below "
                          "(Adrenalin, launch options...).")
        else:
            message = "Boost CS2 terminé avec des étapes en échec (voir le détail)."
            message_en = "CS2 Boost finished with failed steps (see details)."
        return {
            "ok": ok,
            "supported": supported,
            "message": message,
            "message_en": message_en,
            "tier": ctx["tier"],
            "tier_source": ctx["tier_source"],
            "steps": steps,
            "manual_steps": _manual_steps(ctx, insights),
            "notes": _notes(ctx["tier"]),
            "reboot_required": reboot,
        }
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {"ok": False, "supported": is_windows(),
                "message": f"Boost CS2 interrompu : {exc}",
                "message_en": f"CS2 Boost aborted: {exc}",
                "tier": tier if tier in _TIERS else None, "tier_source": None,
                "steps": [], "manual_steps": [], "notes": [],
                "reboot_required": False}
    finally:
        _RUN_LOCK.release()
