"""Point d'entrée d'Overdrive : serveur local + fenêtre native (ou navigateur)."""

import argparse
import ipaddress
import logging
import secrets
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn

from . import APP_NAME, VERSION
from .paths import data_dir, is_windows
from .server import app, configure_security
from .tray import create_tray, stop_tray

DEFAULT_PORT = 8787

#: Cibles de nettoyage jugées sûres pour le mode --clean-safe (alignées sur
#: overdrive.core.boost._SAFE_CLEAN_IDS : temporaire utilisateur et caches de
#: shaders — les deux graphies couvrent le contrat et les identifiants réels
#: du module cleaner).
_SAFE_CLEAN_IDS = frozenset(
    {"temp_user", "dx_cache", "shader_dx", "nvidia_cache", "shader_nvidia"}
)

log = logging.getLogger("overdrive")


def _setup_logging() -> None:
    """Logs vers la console si disponible ET vers data_dir()/overdrive.log.

    L'exécutable Windows est construit sans console : le fichier est alors la
    seule trace disponible.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    try:
        file_handler = logging.FileHandler(data_dir() / "overdrive.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        pass
    if sys.stderr is not None:  # absent en mode fenêtré PyInstaller
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Analyse des arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        prog="overdrive",
        description=f"{APP_NAME} {VERSION} — optimiseur PC gaming.",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="mode serveur : pas de fenêtre, accès par navigateur "
             "(127.0.0.1 par défaut ; --host 0.0.0.0 pour exposer sur le "
             "réseau local, protégé par un jeton affiché au démarrage)",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="force l'ouverture dans le navigateur au lieu de la fenêtre native",
    )
    parser.add_argument("--host", default=None, help="adresse d'écoute")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"port d'écoute (défaut {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="ne pas ouvrir de fenêtre ni de navigateur"
    )
    parser.add_argument(
        "--widget",
        action="store_true",
        help="lance uniquement le widget overlay (FPS, CPU, RAM...) sans le serveur",
    )
    parser.add_argument(
        "--wait-game",
        action="store_true",
        help="avec --widget : démarre caché et ne s'affiche que lorsqu'un jeu est détecté",
    )
    parser.add_argument(
        "--clean-safe",
        action="store_true",
        help="nettoie les cibles sûres (temporaires, caches de shaders) sans "
             "interface puis quitte — utilisé par le nettoyage planifié",
    )
    return parser.parse_args(argv)


def _make_server(host: str, port: int) -> uvicorn.Server:
    """Prépare le serveur uvicorn (logs délégués au logging global)."""
    config = uvicorn.Config(
        app, host=host, port=port, log_config=None, log_level="info", access_log=False
    )
    return uvicorn.Server(config)


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    """Attend que le port réponde (boucle socket, max `timeout` secondes)."""
    connect_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((connect_host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _local_network_ip() -> str | None:
    """Adresse IP locale (best effort, aucune donnée envoyée)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def _is_loopback(host: str) -> bool:
    """Vrai si l'adresse d'écoute reste sur la machine locale."""
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _print_banner(host: str, port: int, token: str | None) -> None:
    """Bannière sobre du mode serveur."""
    suffix = f"/?token={token}" if token else ""
    lines = [
        f"{APP_NAME} {VERSION} — mode serveur",
        f"Local  : http://127.0.0.1:{port}{suffix}",
    ]
    network_ip = _local_network_ip()
    if token and network_ip and host in ("0.0.0.0", "::", network_ip):
        lines.append(f"Réseau : http://{network_ip}:{port}{suffix}")
        lines.append("Accès protégé : ouvrez l'URL complète (jeton inclus).")
    lines.append("Ctrl+C pour arrêter.")
    width = max(len(line) for line in lines) + 2
    banner = "\n".join(["-" * width] + [" " + line for line in lines] + ["-" * width])
    print(banner, flush=True)


def _run_server_mode(host: str, port: int, token: str | None) -> None:
    """Mode --server : boucle bloquante, arrêt propre sur Ctrl+C."""
    _print_banner(host, port, token)
    server = _make_server(host, port)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    log.info("Serveur arrêté.")


def _run_clean_safe() -> None:
    """Mode --clean-safe : nettoie les cibles sûres sans interface puis rend la main.

    Intersection des cibles sûres avec ``cleaner.scan()`` (même logique que
    l'étape de nettoyage de ``overdrive.core.boost``), journalisation du
    résultat et résumé sur stdout si disponible. Ne lève jamais d'exception :
    rien à nettoyer n'est pas une erreur (code de sortie 0 dans tous les cas).
    """
    summary = "Nettoyage sûr : erreur inattendue (voir le journal)."
    try:
        from .core.cleaner import clean, scan

        log.info("Nettoyage sûr (--clean-safe) : analyse des cibles.")
        safe_ids = [t["id"] for t in scan() if t.get("id") in _SAFE_CLEAN_IDS]
        if not safe_ids:
            summary = "Nettoyage sûr : aucune cible détectée, rien à nettoyer."
            log.info(summary)
        else:
            results = clean(safe_ids)
            for result in results:
                log.info(
                    "Nettoyage %s : %s", result.get("id"), result.get("message")
                )
            freed = sum(float(r.get("freed_mb") or 0.0) for r in results)
            ok_count = sum(1 for r in results if r.get("ok"))
            summary = (
                f"Nettoyage sûr terminé : {freed:.1f} Mo libérés sur "
                f"{ok_count}/{len(results)} cible(s)."
            )
            log.info(summary)
    except Exception:  # noqa: BLE001 — mode planifié : jamais d'exception
        log.exception("Échec du nettoyage sûr (--clean-safe).")
    try:
        if sys.stdout is not None:  # absent en mode fenêtré PyInstaller
            print(summary, flush=True)
    except OSError:
        pass


def _launch_widget_detached() -> None:
    """Lance le widget en sous-processus détaché (même logique que /api/widget/launch)."""
    import subprocess

    if getattr(sys, "frozen", False):
        command = [sys.executable, "--widget"]
    else:
        run_py = Path(__file__).resolve().parent.parent / "run.py"
        command = [sys.executable, str(run_py), "--widget"]
    kwargs: dict[str, Any] = {}
    if is_windows():
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            **kwargs,
        )
    except Exception:
        log.exception("Échec du lancement du widget depuis la zone de notification.")


def _setup_tray(url: str, server: uvicorn.Server, ui_state: dict[str, Any]) -> object | None:
    """Crée l'icône de zone de notification reliée à la fenêtre et au serveur.

    ``ui_state`` est partagé avec ``_open_ui`` : ``window`` (fenêtre pywebview
    courante ou None) et ``quitting`` (vrai dès que « Quitter » est demandé).
    Renvoie l'icône, ou None si le tray est indisponible (l'app continue sans).
    """

    def _on_open() -> None:
        """Ré-affiche la fenêtre native, sinon ouvre le navigateur."""
        window = ui_state.get("window")
        if window is not None:
            try:
                window.show()
                try:
                    window.restore()
                except Exception:  # noqa: BLE001 — restore best effort
                    pass
                return
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Réaffichage de la fenêtre impossible (%s) ; "
                    "ouverture du navigateur.", exc
                )
        import webbrowser

        webbrowser.open(url)

    def _on_quit() -> None:
        """Arrêt propre : serveur, icône, puis fenêtre native s'il y en a une."""
        log.info("Arrêt demandé depuis la zone de notification.")
        ui_state["quitting"] = True
        server.should_exit = True
        stop_tray(ui_state.get("tray"))
        window = ui_state.get("window")
        if window is not None:
            try:
                window.destroy()
            except Exception:  # noqa: BLE001 — la fenêtre peut déjà être fermée
                log.debug("Destruction de la fenêtre impossible.", exc_info=True)

    icon = create_tray(_on_open, _launch_widget_detached, _on_quit)
    ui_state["tray"] = icon
    return icon


def _open_ui(url: str, force_browser: bool,
             ui_state: dict[str, Any] | None = None,
             hide_on_close: bool = False) -> bool:
    """Ouvre la fenêtre native pywebview, sinon le navigateur.

    Retourne True si une fenêtre native a été ouverte et fermée (fin de vie
    de l'application), False si le navigateur a été utilisé en secours.
    Avec ``hide_on_close`` (icône de zone de notification active), la
    fermeture de la fenêtre la masque au lieu de la détruire : l'application
    continue en arrière-plan et seule « Quitter » (``window.destroy()``)
    termine la boucle. ``ui_state`` reçoit la fenêtre courante (clé
    ``window``) pour le tray.
    """
    if not force_browser:
        try:
            import webview  # dépendance optionnelle (pywebview)

            window = webview.create_window(
                APP_NAME, url, width=1280, height=820, min_size=(980, 640)
            )
            if ui_state is not None:
                ui_state["window"] = window
            if hide_on_close:
                def _on_closing() -> bool:
                    """Fermeture → masquage (sauf « Quitter » du tray)."""
                    if ui_state is not None and ui_state.get("quitting"):
                        return True
                    try:
                        window.hide()
                    except Exception:  # noqa: BLE001 — masquage impossible
                        return True  # laisser la fenêtre se fermer vraiment
                    return False  # fermeture annulée : l'app reste active

                try:
                    window.events.closing += _on_closing
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "Masquage à la fermeture indisponible (%s) : la "
                        "fermeture de la fenêtre laissera l'app en "
                        "arrière-plan.", exc
                    )
            webview.start()
            if ui_state is not None:
                ui_state["window"] = None
            return True
        except Exception as exc:
            log.warning("Fenêtre native indisponible (%s) ; ouverture du navigateur.", exc)
            if ui_state is not None:
                ui_state["window"] = None
    import webbrowser

    webbrowser.open(url)
    return False


def main() -> None:
    """Lance Overdrive (fenêtre native, navigateur ou mode serveur)."""
    args = _parse_args()
    _setup_logging()
    if args.widget:
        # Mode widget : aucune fenêtre principale ni serveur HTTP.
        from .widget import run_widget

        run_widget(wait_game=args.wait_game)
        return
    if args.clean_safe:
        # Mode planifié : nettoyage des cibles sûres puis sortie immédiate
        # (code 0 dans tous les cas, voir _run_clean_safe).
        _run_clean_safe()
        return
    # Boucle locale par défaut, même en --server : l'exposition réseau exige
    # un --host explicite et active alors un jeton d'accès obligatoire.
    host = args.host or "127.0.0.1"
    port = args.port
    token: str | None = None
    if not _is_loopback(host):
        token = secrets.token_urlsafe(24)
        extra = [h for h in (_local_network_ip(), host) if h and h not in ("0.0.0.0", "::")]
        configure_security(token=token, extra_hosts=extra)
        log.info("Écoute réseau activée : jeton d'accès requis.")
    log.info("%s %s — démarrage (host=%s, port=%s)", APP_NAME, VERSION, host, port)

    if args.server:
        _run_server_mode(host, port, token)
        return

    # Mode normal (double-clic) : serveur en thread daemon + interface.
    server = _make_server(host, port)
    thread = threading.Thread(target=server.run, name="overdrive-uvicorn", daemon=True)
    thread.start()

    if not _wait_for_port(host, port):
        log.error("Le serveur ne répond pas sur le port %s après 15 s.", port)

    url = f"http://127.0.0.1:{port}"
    if token:
        url += f"/?token={token}"
    # Icône de zone de notification (Windows uniquement, best effort) : créée
    # avant l'ouverture de la fenêtre. tray=None → comportement historique.
    tray_icon: object | None = None
    ui_state: dict[str, Any] = {"window": None, "tray": None, "quitting": False}
    if is_windows() and not args.no_open:
        tray_icon = _setup_tray(url, server, ui_state)
    try:
        if args.no_open:
            log.info("Interface disponible sur %s (--no-open).", url)
            thread.join()
            return
        if _open_ui(url, force_browser=args.browser, ui_state=ui_state,
                    hide_on_close=tray_icon is not None):
            if tray_icon is not None and not ui_state.get("quitting"):
                # Fenêtre détruite sans « Quitter » (masquage indisponible) :
                # l'application continue en arrière-plan (serveur + tray).
                log.info(
                    "Fenêtre fermée : %s continue en arrière-plan "
                    "(zone de notification).", APP_NAME
                )
                thread.join()
            # Fenêtre native fermée : arrêt propre du serveur avant de quitter
            # (une écriture d'état en cours peut se terminer).
            server.should_exit = True
            thread.join(timeout=10)
            return
        log.info("Interface ouverte dans le navigateur : %s", url)
        thread.join()
    except KeyboardInterrupt:
        log.info("Arrêt demandé.")
        server.should_exit = True
        thread.join(timeout=10)
    finally:
        if tray_icon is not None:
            stop_tray(tray_icon)


if __name__ == "__main__":
    main()
