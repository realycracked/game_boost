"""Appels HTTP asynchrones aux fournisseurs IA (Groq, OpenAI, Anthropic, Gemini)."""

from __future__ import annotations

from typing import Any

import httpx

from ..secure_store import get_key

#: Modèle par défaut de chaque fournisseur.
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-5-5",
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
}

_TIMEOUT = 60.0

_LABELS = {
    "groq": "Groq",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Google Gemini",
}


class ProviderError(Exception):
    """Erreur d'appel à un fournisseur IA, avec message clair en français."""


def _normalize_messages(messages: list[dict]) -> list[dict]:
    """Ne garde que les messages valides {"role": user|assistant, "content": str non vide}."""
    cleaned: list[dict] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip().lower()
        content = msg.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content})
    if not cleaned:
        raise ProviderError("Aucun message valide à envoyer à l'assistant.")
    return cleaned


def _build_request(
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict],
    system: str | None,
) -> tuple[str, dict[str, str], dict[str, str], dict[str, Any]]:
    """Construit (url, headers, params, payload) selon le format attendu par chaque API."""
    if provider in ("openai", "groq"):
        base = "https://api.openai.com/v1" if provider == "openai" else "https://api.groq.com/openai/v1"
        chat_messages = ([{"role": "system", "content": system}] if system else []) + messages
        return (
            f"{base}/chat/completions",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {},
            {"model": model, "messages": chat_messages},
        )
    if provider == "anthropic":
        payload: dict[str, Any] = {"model": model, "max_tokens": 1024, "messages": messages}
        if system:
            payload["system"] = system
        return (
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            {},
            payload,
        )
    # gemini
    contents = [
        {
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}],
        }
        for msg in messages
    ]
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"Content-Type": "application/json"},
        {"key": api_key},
        payload,
    )


def _error_detail(response: httpx.Response) -> str:
    """Extrait un court message d'erreur du corps de réponse (best effort)."""
    try:
        data = response.json()
    except Exception:
        return ""
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:200]
        if isinstance(err, str):
            return err[:200]
        if data.get("message"):
            return str(data["message"])[:200]
    return ""


def _http_error(provider: str, response: httpx.Response) -> ProviderError:
    """Transforme un statut HTTP d'erreur en ProviderError avec message français."""
    label = _LABELS.get(provider, provider)
    code = response.status_code
    detail = _error_detail(response)
    if code in (401, 403) or (
        provider == "gemini" and code == 400 and "api key" in detail.lower()
    ):
        return ProviderError(
            f"Clé API invalide ou non autorisée pour {label} (HTTP {code}). "
            "Vérifiez la clé dans Réglages."
        )
    if code == 429:
        return ProviderError(
            f"Quota ou limite de débit atteint pour {label} (HTTP 429). "
            "Réessayez dans quelques instants."
        )
    if 400 <= code < 500:
        suffix = f" : {detail}" if detail else "."
        return ProviderError(f"Requête refusée par {label} (HTTP {code}){suffix}")
    return ProviderError(f"Erreur du service {label} (HTTP {code}). Réessayez plus tard.")


def _extract_text(provider: str, data: Any) -> str:
    """Extrait le texte de la réponse JSON selon le format du fournisseur."""
    try:
        if provider in ("openai", "groq"):
            return str(data["choices"][0]["message"]["content"])
        if provider == "anthropic":
            blocks = data.get("content") or []
            text = "".join(
                b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            )
            if text:
                return text
            raise KeyError("content")
        # gemini
        candidates = data.get("candidates") or []
        parts = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if text:
            return text
        raise KeyError("candidates")
    except (KeyError, IndexError, TypeError) as exc:
        label = _LABELS.get(provider, provider)
        raise ProviderError(
            f"Réponse inattendue ou vide du fournisseur {label} (contenu bloqué ou format inconnu)."
        ) from exc


async def chat(
    provider: str,
    messages: list[dict],
    system: str | None = None,
    model: str | None = None,
) -> str:
    """Envoie une conversation au fournisseur et renvoie le texte de la réponse.

    Lève ProviderError (message en français) pour toute erreur : clé absente ou
    invalide (401), quota (429), réseau, délai dépassé, réponse inattendue.
    """
    provider = (provider or "").strip().lower()
    if provider not in DEFAULT_MODELS:
        raise ProviderError(f"Fournisseur IA inconnu : {provider!r}.")
    label = _LABELS[provider]
    api_key = get_key(provider)
    if not api_key:
        raise ProviderError(f"Aucune clé API configurée pour {label}. Ajoutez-la dans Réglages.")
    messages = _normalize_messages(messages)
    model = model or DEFAULT_MODELS[provider]
    url, headers, params, payload = _build_request(provider, api_key, model, messages, system)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, params=params, json=payload)
    except httpx.TimeoutException as exc:
        raise ProviderError(
            f"Délai d'attente dépassé (60 s) en contactant {label}. Vérifiez votre connexion réseau."
        ) from exc
    except httpx.RequestError as exc:
        raise ProviderError(
            f"Erreur réseau : impossible de joindre {label}. Vérifiez votre connexion internet."
        ) from exc
    if response.status_code != 200:
        raise _http_error(provider, response)
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError(f"Réponse illisible du fournisseur {label}.") from exc
    return _extract_text(provider, data)
