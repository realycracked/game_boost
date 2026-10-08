"""Runtime du widget overlay : fenêtre pywebview compacte au-dessus du jeu.

Lancé par ``overdrive --widget`` (ou ``--widget --wait-game`` pour n'apparaître
que lorsqu'un jeu du catalogue tourne). La fenêtre est sans cadre, au premier
plan, déplaçable (``easy_drag``) ; la page ``web/widget.html`` pilote tout via
le pont ``js_api``. L'import est sans effet de bord ; sans pywebview (Linux
dev) : message clair et retour propre, jamais d'exception.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .core import widgetcfg
from .paths import is_windows, web_dir

log = logging.getLogger("overdrive.widget")

#: Titre unique de la fenêtre — sert aussi à retrouver le HWND (cliquer-à-travers).
WINDOW_TITLE = "OverdriveWidgetOverlay"

_SCALE_FACTORS: dict[str, float] = {"s": 0.85, "m": 1.0, "l": 1.2}
_MIN_W, _MIN_H = 80, 40
_MAX_W, _MAX_H = 1600, 1200
_EDGE_MARGIN = 16        # marge avec le bord de l'écran (position par défaut)
_POLL_S = 3.0            # période de surveillance (jeu + config relue)
_MOVE_DEBOUNCE_S = 0.8   # anti-rebond de la sauvegarde de position

# Raccourci clavier global Ctrl+F10 (Windows uniquement) : afficher/masquer.
_HOTKEY_ID = 1
_MOD_CONTROL = 0x0002    # RegisterHotKey : modificateur Ctrl
_VK_F10 = 0x79           # touche virtuelle F10
_WM_HOTKEY = 0x0312      # message Windows reçu quand le raccourci est pressé


def _initial_size(cfg: dict[str, Any]) -> tuple[int, int]:
    """Taille initiale estimée selon l'échelle et les éléments actifs.

    La page ajuste ensuite précisément la fenêtre via ``resize_to`` ; cette
    estimation évite simplement une fenêtre absurde au premier affichage.
    """
    factor = _SCALE_FACTORS.get(str(cfg.get("scale", "m")), 1.0)
    elements = cfg.get("elements") or {}
    active = [name for name, on in elements.items() if on] or ["fps"]
    count = len(active)
    extra_game = 70 if "game" in active else 0
    extra_temp = 50 if "temp" in active else 0  # deux valeurs ("GPU 64° CPU 55°")
    if cfg.get("layout") == "column":
        width = 210 + (extra_game + extra_temp) // 2
        height = 34 + 40 * count
    else:
        width = 44 + 96 * count + extra_game + extra_temp
        height = 70
    width = int(width * factor)
    height = int(height * factor)
    return (max(_MIN_W, min(_MAX_W, width)), max(_MIN_H, min(_MAX_H, height)))


def _apply_click_through(enabled: bool) -> bool:
    """Applique (ou retire) le cliquer-à-travers sur le HWND de la fenêtre.

    Best effort, Windows uniquement : ctypes, ``FindWindowW`` par titre unique
    puis ``GWL_EXSTYLE |= WS_EX_TRANSPARENT | WS_EX_LAYERED``. Renvoie True si
    l'état est considéré appliqué (toujours True hors Windows : sans objet).
    Jamais d'exception.
    """
    if not is_windows():
        return True
    try:
        import ctypes  # noqa: PLC0415 — Windows uniquement

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.FindWindowW(None, WINDOW_TITLE)
        if not hwnd:
            return False
        gwl_exstyle = -20
        ws_ex_transparent = 0x00000020
        ws_ex_layered = 0x00080000
        style = user32.GetWindowLongW(hwnd, gwl_exstyle)
        if enabled:
            style |= ws_ex_transparent | ws_ex_layered
        else:
            style &= ~ws_ex_transparent
        user32.SetWindowLongW(hwnd, gwl_exstyle, style)
        return True
    except Exception:
        return False


def _hotkey_loop(runtime: _WidgetRuntime) -> None:
    """Boucle du raccourci global Ctrl+F10 : bascule afficher/masquer le widget.

    Windows uniquement (le thread n'est pas lancé ailleurs). RegisterHotKey
    doit être appelé depuis le thread qui pompe les messages, d'où la boucle
    ``GetMessageW`` ici même. Si le raccourci est déjà pris par une autre
    application : warning dans le log, aucun crash. Thread daemon : meurt
    avec le processus. Jamais d'exception.
    """
    try:
        import ctypes  # noqa: PLC0415 — Windows uniquement
        import ctypes.wintypes  # noqa: PLC0415

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.RegisterHotKey(None, _HOTKEY_ID, _MOD_CONTROL, _VK_F10):
            log.warning(
                "Raccourci Ctrl+F10 indisponible (déjà utilisé par une autre application)."
            )
            return
        try:
            msg = ctypes.wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == _WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                    runtime.toggle_visibility()
        finally:
            user32.UnregisterHotKey(None, _HOTKEY_ID)
    except Exception:
        pass


class _WidgetRuntime:
    """État partagé entre le pont JS, la fenêtre et la boucle de surveillance."""

    def __init__(self, wait_game: bool) -> None:
        self.wait_game = wait_game
        self.window: Any = None
        self.user_hidden = False
        #: Masquage manuel (Ctrl+F10) : tant qu'il est actif, le mode
        #: --wait-game ne re-montre PAS la fenêtre ; seul un nouveau Ctrl+F10
        #: (demande explicite de l'utilisateur) la ré-affiche.
        self.manual_hidden = False
        self._visible = not wait_game  # état suivi (create_window: hidden=wait_game)
        self._game_present = False
        self._fps_process: str | None = None
        self._gamemode_process: str | None = None
        self._ct_applied = False
        self._stop = threading.Event()
        self._move_lock = threading.Lock()
        self._move_timer: threading.Timer | None = None

    # ----- surveillance (jeu, FPS, config) ---------------------------------

    def watch_loop(self) -> None:
        """Boucle 3 s : capture FPS selon le jeu, config relue, fenêtre en mode jeu."""
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:  # la boucle ne doit jamais mourir
                pass
            self._stop.wait(_POLL_S)

    def _tick(self) -> None:
        from .core import fps, gamewatch  # noqa: PLC0415 — imports tardifs légers

        game = gamewatch.current_game()
        process = str(game["process"]) if game and game.get("process") else None

        # Capture FPS : suit le jeu en cours (démarrée/arrêtée au bon moment).
        if process is not None and process != self._fps_process:
            if fps.start(process):
                self._fps_process = process
        elif process is None and self._fps_process is not None:
            fps.stop()
            self._fps_process = None

        # Config relue toutes les 3 s : applique les changements faits depuis l'app.
        cfg = widgetcfg.get_widget_settings()
        wanted_ct = bool(cfg.get("click_through"))
        if wanted_ct != self._ct_applied and _apply_click_through(wanted_ct):
            self._ct_applied = wanted_ct

        # Mode jeu automatique : plan performant + priorité haute quand un jeu
        # tourne (gamemode.* est best effort et ne lève jamais d'exception).
        if bool(cfg.get("gamemode")):
            from .core import gamemode  # noqa: PLC0415 — import tardif léger

            if process is not None and process != self._gamemode_process:
                gamemode.activate(process)
                self._gamemode_process = process
            elif process is None and self._gamemode_process is not None:
                gamemode.deactivate()
                self._gamemode_process = None
        elif self._gamemode_process is not None:
            # Réglage décoché en cours de partie → plan d'origine restauré.
            from .core import gamemode  # noqa: PLC0415 — import tardif léger

            gamemode.deactivate()
            self._gamemode_process = None

        # Mode --wait-game : la fenêtre suit la présence d'un jeu — sauf si
        # l'utilisateur l'a masquée manuellement (Ctrl+F10) : on respecte son
        # choix tant qu'il ne la re-demande pas.
        if self.wait_game and self.window is not None:
            if game is not None and not self._game_present:
                self.user_hidden = False
                if not self.manual_hidden:
                    self._set_visible(True)
            elif game is None and self._game_present:
                self._set_visible(False)
        self._game_present = game is not None

    def _set_visible(self, visible: bool) -> None:
        try:
            if visible:
                self.window.show()
            else:
                self.window.hide()
            self._visible = visible
        except Exception:
            pass

    def toggle_visibility(self) -> None:
        """Bascule manuelle (Ctrl+F10) : force l'état affiché/caché.

        Masquer pose ``manual_hidden`` (le mode jeu ne re-montrera pas la
        fenêtre) ; ré-afficher lève ``manual_hidden`` et ``user_hidden``.
        Jamais d'exception (appelé depuis le thread du raccourci).
        """
        try:
            if self.window is None:
                return
            if self._visible:
                self.manual_hidden = True
                self._set_visible(False)
            else:
                self.manual_hidden = False
                self.user_hidden = False
                self._set_visible(True)
        except Exception:
            pass

    # ----- position (événement moved + secours à la fermeture) -------------

    def on_moved(self, *args: Any) -> None:
        """Événement ``moved`` (pywebview >= 4) : sauvegarde avec anti-rebond."""
        x, y = self._current_position(*args)
        if x is None or y is None:
            return
        with self._move_lock:
            if self._move_timer is not None:
                self._move_timer.cancel()
            timer = threading.Timer(_MOVE_DEBOUNCE_S, self._save_position, args=(x, y))
            timer.daemon = True
            self._move_timer = timer
            timer.start()

    def _current_position(self, *args: Any) -> tuple[int | None, int | None]:
        try:
            if (
                len(args) >= 2
                and isinstance(args[0], (int, float))
                and isinstance(args[1], (int, float))
            ):
                return int(args[0]), int(args[1])
            if self.window is not None and self.window.x is not None:
                return int(self.window.x), int(self.window.y)
        except Exception:
            pass
        return None, None

    def _save_position(self, x: int, y: int) -> None:
        try:
            widgetcfg.update_widget_settings({"position": {"x": x, "y": y}})
        except Exception:
            pass

    def on_closing(self) -> None:
        """Secours : position sauvée à la fermeture, puis arrêt des boucles."""
        x, y = self._current_position()
        if x is not None and y is not None:
            self._save_position(x, y)
        self.shutdown()

    # ----- arrêt ------------------------------------------------------------

    def shutdown(self) -> None:
        """Arrête la surveillance et la capture FPS (idempotent)."""
        self._stop.set()
        with self._move_lock:
            if self._move_timer is not None:
                self._move_timer.cancel()
                self._move_timer = None
        try:
            from .core import fps  # noqa: PLC0415

            fps.stop()
        except Exception:
            pass

    def quit(self) -> None:
        """Ferme la fenêtre et termine le widget."""
        self.shutdown()
        try:
            if self.window is not None:
                self.window.destroy()
        except Exception:
            pass


class _Bridge:
    """Pont ``js_api`` exposé à ``widget.html`` (appelé depuis la page)."""

    def __init__(self, runtime: _WidgetRuntime) -> None:
        self._runtime = runtime

    # ----- lecture -----------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Instantané : stats allégées (monitor + FPS + températures), config, jeu."""
        stats: dict[str, Any] = {
            "cpu_percent": None,
            "ram": {"percent": None, "used_gb": None},
            "net": {"down_mbps": None, "up_mbps": None},
            "fps": None,
            "temps": {"gpu_c": None, "cpu_c": None, "source": None},
        }
        try:
            from .core import monitor  # noqa: PLC0415

            sample = monitor.sample()
            ram = sample.get("ram") or {}
            net = sample.get("net_io") or {}
            stats["cpu_percent"] = sample.get("cpu_percent")
            stats["ram"] = {"percent": ram.get("percent"), "used_gb": ram.get("used_gb")}
            stats["net"] = {"down_mbps": net.get("down_mbps"), "up_mbps": net.get("up_mbps")}
        except Exception:
            pass
        try:
            from .core import fps  # noqa: PLC0415

            stats["fps"] = fps.get_fps()
        except Exception:
            pass
        try:
            from .core.temps import read_temps  # noqa: PLC0415 — import tardif

            stats["temps"] = read_temps()
        except Exception:
            pass
        game: dict[str, Any] | None = None
        try:
            from .core import gamewatch  # noqa: PLC0415

            game = gamewatch.current_game()
        except Exception:
            game = None
        try:
            config = widgetcfg.get_widget_settings()
        except Exception:
            config = dict(widgetcfg.DEFAULTS)
        return {"stats": stats, "config": config, "game": game}

    # ----- écritures de configuration ---------------------------------------

    def _update(self, partial: dict[str, Any]) -> dict[str, Any]:
        try:
            return widgetcfg.update_widget_settings(partial)
        except Exception:
            return widgetcfg.get_widget_settings()

    def save_position(self, x: Any, y: Any) -> dict[str, Any]:
        """Mémorise la position de la fenêtre (persistée)."""
        try:
            return self._update({"position": {"x": int(x), "y": int(y)}})
        except (TypeError, ValueError):
            return widgetcfg.get_widget_settings()

    def set_element(self, name: Any, visible: Any) -> dict[str, Any]:
        """Affiche/masque un élément (fps, game, cpu, ram, net, clock, temp)."""
        return self._update({"elements": {str(name): bool(visible)}})

    def set_opacity(self, value: Any) -> dict[str, Any]:
        """Opacité du fond (0.1 à 1.0)."""
        return self._update({"opacity": value})

    def set_scale(self, scale: Any) -> dict[str, Any]:
        """Taille d'affichage : "s" | "m" | "l"."""
        return self._update({"scale": scale})

    def set_theme(self, theme: Any) -> dict[str, Any]:
        """Thème : "dark" | "light" | "minimal"."""
        return self._update({"theme": theme})

    def set_layout(self, layout: Any) -> dict[str, Any]:
        """Disposition : "row" | "column"."""
        return self._update({"layout": layout})

    def set_click_through(self, enabled: Any) -> dict[str, Any]:
        """Active/désactive le cliquer-à-travers (ctypes, Windows, best effort)."""
        cfg = self._update({"click_through": bool(enabled)})
        wanted = bool(cfg.get("click_through"))
        if _apply_click_through(wanted):
            self._runtime._ct_applied = wanted
        return cfg

    # ----- fenêtre -----------------------------------------------------------

    def hide_widget(self) -> dict[str, Any]:
        """Cache la fenêtre (revient au prochain jeu en mode game, ou via l'app)."""
        self._runtime.user_hidden = True
        self._runtime._set_visible(False)
        return {"ok": True}

    def quit_widget(self) -> dict[str, Any]:
        """Quitte le widget proprement."""
        self._runtime.quit()
        return {"ok": True}

    def resize_to(self, width: Any, height: Any) -> dict[str, Any]:
        """Redimensionne la fenêtre au contenu mesuré par la page."""
        try:
            w = max(_MIN_W, min(_MAX_W, int(width)))
            h = max(_MIN_H, min(_MAX_H, int(height)))
        except (TypeError, ValueError):
            return {"ok": False}
        try:
            if self._runtime.window is not None:
                self._runtime.window.resize(w, h)
                return {"ok": True}
        except Exception:
            pass
        return {"ok": False}


def run_widget(wait_game: bool = False) -> None:
    """Lance la fenêtre du widget (bloquant jusqu'à sa fermeture).

    ``wait_game=True`` : démarre caché et ne s'affiche que lorsqu'un jeu du
    catalogue est détecté. Sans pywebview (Linux dev) : message clair et
    retour propre (code 0), jamais d'exception.
    """
    try:
        import webview  # noqa: PLC0415 — dépendance optionnelle (GUI)
    except Exception:
        message = (
            "Widget indisponible : pywebview n'est pas installé "
            "(interface graphique requise). "
            "Installez pywebview ou lancez Overdrive sans --widget."
        )
        print(message)
        log.info("%s", message)
        return

    try:
        html = (web_dir() / "widget.html").read_text(encoding="utf-8")
    except OSError as exc:
        log.error("widget.html introuvable ou illisible : %s", exc)
        print("Widget indisponible : fichier widget.html introuvable.")
        return

    cfg = widgetcfg.get_widget_settings()
    width, height = _initial_size(cfg)
    x: int | None = None
    y: int | None = None
    position = cfg.get("position")
    if isinstance(position, dict):
        x, y = position.get("x"), position.get("y")
    else:
        try:
            screen = webview.screens[0]
            x = max(0, int(screen.width) - width - _EDGE_MARGIN)
            y = _EDGE_MARGIN
        except Exception:
            x = y = None  # le backend centrera la fenêtre

    runtime = _WidgetRuntime(wait_game=wait_game)
    bridge = _Bridge(runtime)
    background = "#ffffff" if cfg.get("theme") == "light" else "#191919"
    try:
        window = webview.create_window(
            WINDOW_TITLE,
            html=html,
            js_api=bridge,
            width=width,
            height=height,
            x=x,
            y=y,
            frameless=True,
            easy_drag=True,
            on_top=True,
            resizable=False,
            hidden=wait_game,
            background_color=background,
        )
    except Exception as exc:
        log.error("Création de la fenêtre du widget impossible : %s", exc)
        return
    runtime.window = window
    try:
        window.events.moved += runtime.on_moved  # pywebview >= 4
    except Exception:
        pass
    try:
        window.events.closing += runtime.on_closing
    except Exception:
        pass
    if is_windows():
        # Raccourci global Ctrl+F10 (afficher/masquer) : thread daemon dédié,
        # RegisterHotKey + GetMessageW devant vivre sur le même thread.
        threading.Thread(
            target=_hotkey_loop, args=(runtime,), daemon=True, name="overdrive-hotkey"
        ).start()
    log.info("Widget démarré (wait_game=%s).", wait_game)
    try:
        webview.start(func=runtime.watch_loop)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log.error("Interface du widget interrompue : %s", exc)
    finally:
        runtime.shutdown()
    log.info("Widget arrêté.")
