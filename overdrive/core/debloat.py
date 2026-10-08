"""Applications préinstallées de Windows (bloatware) : liste sûre et suppression.

Le catalogue :data:`BLOAT` ne contient que des applications dont la
suppression est sans danger (actualités, météo, Solitaire…). Jamais de
composant système, ni Microsoft Store, ni Xbox, ni Calculatrice, Photos,
« Mobile connecté » ou Terminal. La suppression se fait pour l'utilisateur
courant uniquement (``Remove-AppxPackage`` sans ``-AllUsers``) et chaque
application reste réinstallable gratuitement depuis le Microsoft Store.

Tout est best effort : refus propres hors Windows, jamais d'exception.
"""

from __future__ import annotations

import json
import subprocess

from overdrive.paths import is_windows

#: Applications préinstallées sûres à supprimer : {"id", "name", "appx"
#: (nom de paquet Get-AppxPackage), "description", "description_en"}.
BLOAT: list[dict] = [
    {
        "id": "bingnews",
        "name": "Actualités (Microsoft News)",
        "appx": "Microsoft.BingNews",
        "description": "Agrégateur d'actualités Microsoft, redondant avec votre navigateur.",
        "description_en": "Microsoft news aggregator, redundant with your web browser.",
    },
    {
        "id": "bingweather",
        "name": "Météo (MSN Météo)",
        "appx": "Microsoft.BingWeather",
        "description": "Application météo MSN, l'information est déjà dans votre navigateur ou votre téléphone.",
        "description_en": "MSN weather app; the same information is already in your browser or phone.",
    },
    {
        "id": "gethelp",
        "name": "Obtenir de l'aide",
        "appx": "Microsoft.GetHelp",
        "description": "Assistant de support Microsoft, rarement utilisé sur un PC de jeu.",
        "description_en": "Microsoft support assistant, rarely used on a gaming PC.",
    },
    {
        "id": "getstarted",
        "name": "Conseils (Astuces Windows)",
        "appx": "Microsoft.Getstarted",
        "description": "Tutoriels de découverte de Windows, inutiles une fois le système pris en main.",
        "description_en": "Windows onboarding tips, useless once you know your way around.",
    },
    {
        "id": "officehub",
        "name": "Microsoft 365 (Office Hub)",
        "appx": "Microsoft.MicrosoftOfficeHub",
        "description": "Vitrine commerciale pour Microsoft 365, pas la suite Office elle-même.",
        "description_en": "Marketing front end for Microsoft 365, not the Office suite itself.",
    },
    {
        "id": "solitaire",
        "name": "Microsoft Solitaire Collection",
        "appx": "Microsoft.MicrosoftSolitaireCollection",
        "description": "Jeux de cartes avec publicités, dispensables si vous n'y jouez pas.",
        "description_en": "Ad-supported card games, safe to remove if you never play them.",
    },
    {
        "id": "mixedreality",
        "name": "Portail de réalité mixte",
        "appx": "Microsoft.MixedReality.Portal",
        "description": "Portail pour casques Windows Mixed Reality, inutile sans casque dédié.",
        "description_en": "Portal for Windows Mixed Reality headsets, useless without one.",
    },
    {
        "id": "3dviewer",
        "name": "Visionneuse 3D",
        "appx": "Microsoft.Microsoft3DViewer",
        "description": "Visionneuse de modèles 3D, très rarement utile hors impression 3D.",
        "description_en": "3D model viewer, very rarely useful outside 3D printing.",
    },
    {
        "id": "people",
        "name": "Contacts (People)",
        "appx": "Microsoft.People",
        "description": "Carnet d'adresses Windows, redondant avec votre messagerie.",
        "description_en": "Windows address book, redundant with your e-mail client.",
    },
    {
        "id": "skype",
        "name": "Skype",
        "appx": "Microsoft.SkypeApp",
        "description": "Version préinstallée de Skype, remplacée par Teams/Discord pour la plupart des joueurs.",
        "description_en": "Preinstalled Skype app, replaced by Teams/Discord for most gamers.",
    },
    {
        "id": "wallet",
        "name": "Microsoft Wallet",
        "appx": "Microsoft.Wallet",
        "description": "Portefeuille numérique abandonné par Microsoft, sans usage réel.",
        "description_en": "Digital wallet discontinued by Microsoft, with no real use.",
    },
    {
        "id": "feedbackhub",
        "name": "Hub de commentaires",
        "appx": "Microsoft.WindowsFeedbackHub",
        "description": "Application de retours à Microsoft, inutile si vous n'envoyez pas de rapports.",
        "description_en": "Feedback app for Microsoft, useless if you never send reports.",
    },
    {
        "id": "zunemusic",
        "name": "Groove Musique / Media Player",
        "appx": "Microsoft.ZuneMusic",
        "description": "Lecteur de musique préinstallé, redondant si vous utilisez Spotify ou un autre lecteur.",
        "description_en": "Preinstalled music player, redundant if you use Spotify or another player.",
    },
    {
        "id": "zunevideo",
        "name": "Films et TV",
        "appx": "Microsoft.ZuneVideo",
        "description": "Boutique et lecteur vidéo Microsoft, redondants avec VLC ou le streaming.",
        "description_en": "Microsoft video store and player, redundant with VLC or streaming.",
    },
]

_WINDOWS_ONLY_MESSAGE = "Disponible uniquement sous Windows."

#: Les noms de paquets ne contiennent que lettres, chiffres et points : ils
#: viennent de BLOAT (constante du module), jamais de l'utilisateur.
_PS_LIST_COMMAND = (
    "Get-AppxPackage | Select-Object -ExpandProperty Name | "
    "ConvertTo-Json -Compress"
)


def _creation_flags() -> int:
    """Drapeaux subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _installed_names() -> set[str] | None:
    """Noms (minuscules) des paquets AppX installés, ou None si indisponible.

    Une seule commande PowerShell ``Get-AppxPackage`` (timeout 30 s) pour
    tout le catalogue, best effort.
    """
    if not is_windows():
        return None
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", _PS_LIST_COMMAND],
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=_creation_flags(),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        data = json.loads(proc.stdout)
        if isinstance(data, str):  # un seul paquet : JSON scalaire
            data = [data]
        if not isinstance(data, list):
            return None
        return {str(name).lower() for name in data if isinstance(name, str)}
    except Exception:
        return None


def list_installed() -> list[dict]:
    """Catalogue :data:`BLOAT` enrichi du champ ``installed``.

    ``installed`` vaut True/False selon la présence du paquet pour
    l'utilisateur courant, ou None si l'état n'a pas pu être déterminé
    (échec PowerShell, Linux). Jamais d'exception.
    """
    installed = _installed_names()
    result: list[dict] = []
    for app in BLOAT:
        entry = dict(app)
        if installed is None:
            entry["installed"] = None
        else:
            entry["installed"] = str(app["appx"]).lower() in installed
        result.append(entry)
    return result


def _remove_one(app: dict) -> dict:
    """Supprime un paquet pour l'utilisateur courant (best effort)."""
    command = (
        f"Get-AppxPackage -Name '{app['appx']}' | Remove-AppxPackage"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            shell=False,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=_creation_flags(),
        )
    except subprocess.TimeoutExpired:
        return {
            "id": app["id"],
            "ok": False,
            "message": f"Suppression de {app['name']} interrompue : "
                       f"délai de 2 minutes dépassé.",
        }
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return {
            "id": app["id"],
            "ok": False,
            "message": f"Échec du lancement de PowerShell : {exc}",
        }

    if proc.returncode == 0:
        return {
            "id": app["id"],
            "ok": True,
            "message": f"{app['name']} supprimé pour votre compte. "
                       f"Réinstallable à tout moment depuis le Microsoft Store.",
        }
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    last = detail[-1] if detail else f"code {proc.returncode}"
    return {
        "id": app["id"],
        "ok": False,
        "message": f"Échec de la suppression de {app['name']} : {last}",
    }


def remove(ids: list[str]) -> list[dict]:
    """Supprime les applications demandées (``Remove-AppxPackage`` par paquet).

    Les identifiants sont validés contre :data:`BLOAT` (id inconnu →
    refus). Suppression pour l'utilisateur courant uniquement ; chaque
    application reste réinstallable depuis le Microsoft Store. Renvoie
    ``[{"id", "ok", "message"}]`` ; refus propre hors Windows, jamais
    d'exception.
    """
    by_id = {app["id"]: app for app in BLOAT}
    results: list[dict] = []
    for raw_id in ids or []:
        app_id = str(raw_id)
        app = by_id.get(app_id)
        if app is None:
            results.append({
                "id": app_id,
                "ok": False,
                "message": f"Application inconnue : {app_id}",
            })
            continue
        if not is_windows():
            results.append({
                "id": app_id,
                "ok": False,
                "message": _WINDOWS_ONLY_MESSAGE,
            })
            continue
        results.append(_remove_one(app))
    return results
