"""Icône de zone de notification (pystray + Pillow, dépendances optionnelles).

L'icône est dessinée par code (aucun fichier binaire embarqué). ``create_tray``
renvoie ``None`` si pystray ou Pillow sont indisponibles ou si la création
échoue : l'application doit fonctionner sans icône. Aucun import de pystray
ni de Pillow au niveau du module — importer ce fichier ne lève jamais
d'exception, y compris sous Linux.
"""

from __future__ import annotations

import logging
from typing import Callable

from . import APP_NAME

log = logging.getLogger("overdrive.tray")

#: Taille de l'icône générée (pixels) et bleu Overdrive (#2383e2).
_ICON_SIZE = 64
_ICON_COLOR = (35, 131, 226, 255)


def _make_image():
    """Dessine l'icône 64×64 : double cercle sobre bleu sur fond transparent.

    Anneau extérieur + disque central pleins, générés avec Pillow ; lève une
    exception si Pillow est absent (gérée par ``create_tray``).
    """
    from PIL import Image, ImageDraw  # noqa: PLC0415 — dépendance optionnelle

    size = _ICON_SIZE
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Cercle extérieur (anneau) puis disque intérieur plein.
    draw.ellipse((4, 4, size - 5, size - 5), outline=_ICON_COLOR, width=6)
    draw.ellipse((22, 22, size - 23, size - 23), fill=_ICON_COLOR)
    return image


def create_tray(
    on_open: Callable[[], None],
    on_widget: Callable[[], None],
    on_quit: Callable[[], None],
) -> object | None:
    """Crée et démarre l'icône de zone de notification (thread détaché).

    Menu : « Ouvrir Overdrive » (élément par défaut, déclenché aussi par le
    double-clic), « Lancer le widget », « Quitter ». Renvoie l'icône pystray
    démarrée via ``run_detached()``, ou ``None`` si pystray/Pillow sont
    indisponibles ou si la création échoue (avertissement dans le journal,
    jamais d'exception).
    """
    try:
        import pystray  # noqa: PLC0415 — dépendance optionnelle

        menu = pystray.Menu(
            pystray.MenuItem(
                f"Ouvrir {APP_NAME}", lambda icon, item: on_open(), default=True
            ),
            pystray.MenuItem("Lancer le widget", lambda icon, item: on_widget()),
            pystray.MenuItem("Quitter", lambda icon, item: on_quit()),
        )
        icon = pystray.Icon("overdrive", icon=_make_image(), title=APP_NAME, menu=menu)
        icon.run_detached()
        return icon
    except Exception as exc:  # noqa: BLE001 — l'app doit fonctionner sans icône
        log.warning("Icône de zone de notification indisponible (%s).", exc)
        return None


def stop_tray(icon: object) -> None:
    """Arrête l'icône de zone de notification (best effort, jamais d'exception)."""
    if icon is None:
        return
    try:
        icon.stop()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — arrêt best effort
        log.debug("Arrêt de l'icône de zone de notification impossible.", exc_info=True)
