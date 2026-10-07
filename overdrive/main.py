"""Point d'entrée d'Overdrive : serveur local + fenêtre native (ou navigateur)."""

import argparse
import ipaddress
import logging
import secrets
import socket
import sys
import threading
import time

import uvicorn

from . import APP_NAME, VERSION
from .paths import data_dir
from .server import app, configure_security

DEFAULT_PORT = 8787

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


def _open_ui(url: str, force_browser: bool) -> bool:
    """Ouvre la fenêtre native pywebview, sinon le navigateur.

    Retourne True si une fenêtre native a été ouverte et fermée (fin de vie
    de l'application), False si le navigateur a été utilisé en secours.
    """
    if not force_browser:
        try:
            import webview  # dépendance optionnelle (pywebview)

            webview.create_window(
                APP_NAME, url, width=1280, height=820, min_size=(980, 640)
            )
            webview.start()
            return True
        except Exception as exc:
            log.warning("Fenêtre native indisponible (%s) ; ouverture du navigateur.", exc)
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
    try:
        if args.no_open:
            log.info("Interface disponible sur %s (--no-open).", url)
            thread.join()
            return
        if _open_ui(url, force_browser=args.browser):
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


if __name__ == "__main__":
    main()
