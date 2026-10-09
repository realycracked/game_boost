"""Assistant IA d'Overdrive : construction du contexte et appel du fournisseur."""

from __future__ import annotations

import json

from ..secure_store import PROVIDERS, get_key
from . import providers

_SYSTEM_BASE = (
    "Tu es l'assistant IA d'Overdrive, un optimiseur de PC gaming pour Windows 10/11. "
    "Tu aides l'utilisateur à améliorer les performances en jeu : FPS, latence, réglages "
    "Windows, pilotes, options de lancement des jeux. Réponds en français, de façon "
    "concise et concrète, avec des valeurs et des étapes précises quand c'est utile. "
    "Règles impératives de sécurité : ne suggère JAMAIS de désactiver les mitigations de "
    "sécurité du processeur (Spectre/Meltdown) ni la protection en temps réel de Windows "
    "Defender, et ne propose JAMAIS de commande destructrice ou irréversible (formatage, "
    "suppression de fichiers système, modification de partitions, ni modification du "
    "registre non documentée). Privilégie des actions réversibles et recommande un point "
    "de restauration avant tout changement avancé. "
    "Quand ta recommandation correspond exactement à une optimisation du catalogue "
    "Overdrive (liste d'identifiants fournie dans le contexte), ajoute à la fin de la "
    "phrase concernée le marqueur [[tweak:identifiant]] — l'application affichera alors "
    "un bouton « Appliquer ». N'utilise ce marqueur qu'avec un identifiant exact de la "
    "liste, au plus 3 par réponse, jamais pour un tweak déjà appliqué."
)


def _context_lines() -> list[str]:
    """Contexte machine/profil injecté dans le system prompt (imports tardifs protégés)."""
    lines: list[str] = []
    # Matériel détecté.
    try:
        from ..hardware import detect_hardware

        summary = detect_hardware().get("summary")
        if summary:
            lines.append(f"Matériel détecté : {summary}")
    except Exception:
        pass
    # Profil issu du questionnaire.
    try:
        from ...store import get_settings

        profile = get_settings().get("profile")
        if isinstance(profile, dict):
            label = profile.get("label") or profile.get("id")
            if label:
                lines.append(f"Profil d'optimisation de l'utilisateur : {label}")
    except Exception:
        pass
    # Tweaks appliqués via l'engine (ou son fichier d'état en repli).
    try:
        from ..tweaks.engine import list_tweaks

        tweaks = list_tweaks()
        # tracked = appliqué via Overdrive et non annulé (sémantique engine).
        applied = sum(1 for t in tweaks if t.get("tracked"))
        lines.append(f"Tweaks appliqués via Overdrive : {applied} sur {len(tweaks)} disponibles")
        pending = [t["id"] for t in tweaks if not t.get("tracked")]
        lines.append(
            "Identifiants d'optimisations utilisables avec [[tweak:...]] "
            "(non encore appliquées) : " + ", ".join(pending)
        )
    except Exception:
        try:
            from ...paths import data_dir

            state = json.loads((data_dir() / "tweaks_state.json").read_text(encoding="utf-8"))
            applied = sum(
                1 for v in state.values() if isinstance(v, dict) and not v.get("reverted")
            )
            lines.append(f"Tweaks appliqués via Overdrive : {applied}")
        except Exception:
            pass
    # Jeux détectés.
    try:
        from ..games.detect import detect_games

        installed = [g.get("name", g.get("id", "?")) for g in detect_games() if g.get("installed")]
        lines.append(
            "Jeux détectés : " + (", ".join(installed) if installed else "aucun pour l'instant")
        )
    except Exception:
        pass
    return lines


def build_system_prompt() -> str:
    """System prompt français complet, avec le contexte machine quand il est disponible."""
    lines = _context_lines()
    if not lines:
        return _SYSTEM_BASE
    return _SYSTEM_BASE + "\n\nContexte de la machine de l'utilisateur :\n" + "\n".join(
        f"- {line}" for line in lines
    )


def _default_provider() -> str | None:
    """Fournisseur par défaut : settings["ai_provider"] s'il a une clé, sinon le premier configuré."""
    preferred: str | None = None
    try:
        from ...store import get_settings

        value = get_settings().get("ai_provider")
        if isinstance(value, str) and value.strip():
            preferred = value.strip().lower()
    except Exception:
        preferred = None
    if preferred in PROVIDERS and get_key(preferred):
        return preferred
    for provider in PROVIDERS:
        if get_key(provider):
            return provider
    return None


async def ask(messages: list[dict], provider: str | None = None) -> dict:
    """Pose la conversation à l'assistant IA.

    Retour : {"ok": bool, "reply": str|None, "message": str|None, "provider": str}.
    Jamais d'exception : toute erreur est portée par ok=False + message en français.
    """
    chosen = (provider or "").strip().lower() or None
    if chosen is None:
        chosen = _default_provider()
        if chosen is None:
            return {
                "ok": False,
                "reply": None,
                "provider": "",
                "message": (
                    "Aucun fournisseur IA configuré. Ajoutez une clé API dans Réglages "
                    "(Groq propose une clé gratuite sur console.groq.com)."
                ),
            }
    if chosen not in PROVIDERS:
        return {
            "ok": False,
            "reply": None,
            "provider": chosen,
            "message": f"Fournisseur IA inconnu : {chosen!r}.",
        }
    if not get_key(chosen):
        return {
            "ok": False,
            "reply": None,
            "provider": chosen,
            "message": f"Aucune clé API enregistrée pour {chosen}. Ajoutez-la dans Réglages.",
        }
    try:
        # Le contexte (matériel, tweaks, jeux) fait des appels bloquants :
        # on le construit dans un thread pour ne pas geler l'event loop.
        import anyio

        system = await anyio.to_thread.run_sync(build_system_prompt)
    except Exception:
        system = _SYSTEM_BASE
    try:
        reply = await providers.chat(chosen, messages, system=system)
    except providers.ProviderError as exc:
        return {"ok": False, "reply": None, "provider": chosen, "message": str(exc)}
    except Exception:
        return {
            "ok": False,
            "reply": None,
            "provider": chosen,
            "message": "Erreur inattendue lors de l'appel au fournisseur IA.",
        }
    return {"ok": True, "reply": reply, "provider": chosen, "message": None}
