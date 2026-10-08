"""Boost en un clic : point de restauration, tweaks du profil, nettoyage sûr.

Orchestration séquentielle avec compte rendu structuré par étape.
Aucune exception ne remonte à l'appelant : chaque étape renvoie
``{"step", "label", "ok", "message", "details"}``. Sous Linux, chaque
étape répond par un refus propre et le ``ok`` global est ``False``.
"""

from __future__ import annotations

from typing import Any

from overdrive.paths import is_windows
from overdrive.store import get_settings

#: Cibles de nettoyage jugées sûres pour le boost automatique
#: (temporaire utilisateur et caches de shaders — les deux graphies
#: couvrent le contrat et les identifiants réels du module cleaner).
_SAFE_CLEAN_IDS = frozenset(
    {"temp_user", "dx_cache", "shader_dx", "nvidia_cache", "shader_nvidia"}
)

_WINDOWS_ONLY_MESSAGE = "Disponible uniquement sous Windows."


def _step(step: str, label: str, ok: bool, message: str,
          details: list[dict] | None = None) -> dict:
    """Construit le compte rendu structuré d'une étape du boost."""
    return {
        "step": step,
        "label": label,
        "ok": bool(ok),
        "message": message,
        "details": details or [],
    }


def _step_restore() -> dict:
    """Étape 1 : point de restauration système (refus propre hors Windows)."""
    label = "Point de restauration"
    try:
        from overdrive.core.tweaks.engine import create_restore_point

        result = create_restore_point("Overdrive Boost")
        return _step("restore", label, bool(result.get("ok")),
                     str(result.get("message") or ""))
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("restore", label, False, f"Erreur inattendue : {exc}")


def _step_tweaks() -> dict:
    """Étape 2 : application des tweaks recommandés du profil non encore appliqués."""
    label = "Tweaks du profil"
    try:
        if not is_windows():
            return _step("tweaks", label, False, _WINDOWS_ONLY_MESSAGE)

        profile = get_settings().get("profile")
        if not isinstance(profile, dict):
            return _step(
                "tweaks", label, False,
                "Étape sautée : aucun profil. Faites d'abord le questionnaire "
                "pour obtenir des recommandations personnalisées.")

        from overdrive.core.tweaks.engine import apply_tweaks, list_tweaks

        tweaks_by_id = {t["id"]: t for t in list_tweaks()}
        recommended = [str(tweak_id) for tweak_id in
                       (profile.get("recommended_tweaks") or [])
                       if str(tweak_id) in tweaks_by_id]
        if not recommended:
            return _step("tweaks", label, True,
                         "Aucun tweak recommandé pour ce profil.")
        pending = [tweak_id for tweak_id in recommended
                   if not tweaks_by_id[tweak_id].get("tracked")]
        if not pending:
            return _step(
                "tweaks", label, True,
                f"Les {len(recommended)} tweaks recommandés sont déjà appliqués.")

        results = apply_tweaks(pending)
        ok_count = sum(1 for r in results if r.get("ok"))
        message = (f"{ok_count}/{len(results)} tweak(s) appliqué(s)"
                   f" ({len(recommended) - len(pending)} déjà en place).")
        return _step("tweaks", label, ok_count == len(results), message,
                     details=results)
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("tweaks", label, False, f"Erreur inattendue : {exc}")


def _step_clean() -> dict:
    """Étape 3 : nettoyage des cibles sûres uniquement (temp, caches shaders)."""
    label = "Nettoyage des caches sûrs"
    try:
        if not is_windows():
            return _step("clean", label, False, _WINDOWS_ONLY_MESSAGE)

        from overdrive.core.cleaner import clean, scan

        safe_ids = [t["id"] for t in scan() if t.get("id") in _SAFE_CLEAN_IDS]
        if not safe_ids:
            return _step("clean", label, True,
                         "Aucune cible de nettoyage sûre détectée.")

        results = clean(safe_ids)
        freed = sum(float(r.get("freed_mb") or 0.0) for r in results)
        ok = all(r.get("ok") for r in results)
        message = f"{freed:.1f} Mo libérés sur {len(safe_ids)} cible(s) sûre(s)."
        return _step("clean", label, ok, message, details=results)
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _step("clean", label, False, f"Erreur inattendue : {exc}")


def run_boost(create_restore: bool = True) -> dict:
    """Lance le boost en un clic : restauration, tweaks du profil, nettoyage.

    Retourne ``{"ok": bool global, "steps": [compte rendu par étape]}``.
    Le ``ok`` global n'est vrai que si toutes les étapes ont réussi.
    """
    steps: list[dict[str, Any]] = []
    if create_restore:
        steps.append(_step_restore())
    steps.append(_step_tweaks())
    steps.append(_step_clean())
    return {"ok": all(step["ok"] for step in steps), "steps": steps}
