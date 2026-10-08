"""Vérification des mises à jour via les Releases GitHub du projet.

Compare le numéro de build local (``overdrive._build.BUILD``, injecté
par la CI, None en développement) au dernier build publié sur GitHub
(tag de la forme ``v1.0.0-build.N``). Aucune exception ne sort de ce
module : toute erreur (hors ligne, limite d'API, réponse inattendue)
est renvoyée dans un résultat structuré avec un message en français.
"""

from __future__ import annotations

import re
from typing import Any

#: Endpoint GitHub de la dernière release publiée.
_RELEASES_URL = (
    "https://api.github.com/repos/realycracked/game_boost/releases/latest")
#: Délai maximal de la requête HTTP (secondes).
_TIMEOUT = 10.0
#: Extraction du numéro de build depuis un tag « v1.0.0-build.N ».
_TAG_BUILD_RE = re.compile(r"-build\.(\d+)$")
#: Nom de l'asset exécutable attendu dans la release.
_ASSET_NAME = "overdrive.exe"


def current_build() -> int | None:
    """Numéro de build local (``overdrive._build.BUILD``), None si inconnu."""
    try:
        from overdrive._build import BUILD

        return int(BUILD) if BUILD is not None else None
    except Exception:  # noqa: BLE001 — jamais d'exception
        return None


def _result(**overrides: Any) -> dict:
    """Résultat structuré avec les champs par défaut, puis surcharges."""
    base: dict[str, Any] = {
        "ok": False,
        "current_build": current_build(),
        "latest_build": None,
        "latest_tag": None,
        "update_available": None,
        "download_url": None,
        "message": "",
    }
    base.update(overrides)
    return base


def _download_url(release: dict) -> str | None:
    """URL de l'asset Overdrive.exe, sinon la page HTML de la release."""
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        if str(asset.get("name", "")).lower() == _ASSET_NAME:
            url = asset.get("browser_download_url")
            if url:
                return str(url)
    html_url = release.get("html_url")
    return str(html_url) if html_url else None


def check_update() -> dict:
    """Interroge GitHub et indique si une mise à jour est disponible.

    Renvoie ``{"ok", "current_build", "latest_build", "latest_tag",
    "update_available", "download_url", "message"}``. ``update_available``
    vaut None quand le build local est inconnu (lancement hors CI) ou que
    le tag distant est illisible. Ne lève jamais d'exception.
    """
    try:
        import httpx

        from overdrive import APP_NAME, VERSION

        headers = {
            # GitHub exige un User-Agent identifiant l'application.
            "User-Agent": f"{APP_NAME}/{VERSION}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            response = httpx.get(
                _RELEASES_URL, headers=headers, timeout=_TIMEOUT,
                follow_redirects=True)
        except httpx.TimeoutException:
            return _result(message=(
                "Délai dépassé (10 s) en contactant GitHub. "
                "Réessayez plus tard."))
        except httpx.RequestError:
            return _result(message=(
                "Impossible de contacter GitHub : vérifiez votre "
                "connexion Internet (mode hors ligne ?)."))

        if response.status_code in (403, 429):
            return _result(message=(
                "Limite de l'API GitHub atteinte. Réessayez dans "
                "quelques minutes."))
        if response.status_code == 404:
            return _result(message=(
                "Aucune release publiée pour le moment sur GitHub."))
        if response.status_code != 200:
            return _result(message=(
                f"Réponse inattendue de GitHub (code "
                f"{response.status_code})."))

        try:
            release = response.json()
        except ValueError:
            release = None
        if not isinstance(release, dict):
            return _result(message="Réponse illisible de l'API GitHub.")

        tag = str(release.get("tag_name") or "") or None
        match = _TAG_BUILD_RE.search(tag or "")
        latest_build = int(match.group(1)) if match else None
        download_url = _download_url(release)
        current = current_build()

        if latest_build is None:
            return _result(
                ok=True, latest_tag=tag, download_url=download_url,
                message=(f"Dernière release trouvée ({tag or 'sans tag'}), "
                         "mais son numéro de build est illisible."))

        if current is None:
            update_available = None
            message = (f"Version de développement (build local inconnu) ; "
                       f"dernier build publié : {latest_build}.")
        elif latest_build > current:
            update_available = True
            message = (f"Mise à jour disponible : build {latest_build} "
                       f"(vous utilisez le build {current}).")
        else:
            update_available = False
            message = f"Overdrive est à jour (build {current})."

        return _result(
            ok=True, current_build=current, latest_build=latest_build,
            latest_tag=tag, update_available=update_available,
            download_url=download_url, message=message)
    except Exception:  # noqa: BLE001 — jamais d'exception
        return _result(message=(
            "Erreur interne lors de la vérification des mises à jour."))
