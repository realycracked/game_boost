"""Capteur de FPS temps réel basé sur PresentMon (Intel, licence MIT).

Flux temps réel uniquement (pas de benchmark) : PresentMon est lancé en
arrière-plan sur le processus du jeu, son CSV est parsé sur un thread et
une fenêtre glissante d'une seconde donne le FPS courant.

Hors Windows (ou sans PresentMon.exe embarqué) : aucune exception, les
fonctions renvoient des refus propres (None / False).
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from ..paths import data_dir, is_windows

# Fenêtre glissante (secondes) utilisée pour calculer le FPS.
_WINDOW_S = 1.0
# Au-delà de ce délai sans nouvelle frame, la capture est considérée inactive.
_STALE_S = 2.0
# Noms possibles de la colonne de temps de frame selon la version de PresentMon
# (v1 : MsBetweenPresents, variantes de casse ; v2 : FrameTime).
_FRAME_COLUMNS = ("msbetweenpresents", "frametime")

# État module (une seule capture à la fois), protégé par verrou.
_LOCK = threading.Lock()
_PROC: subprocess.Popen | None = None
_THREAD: threading.Thread | None = None
_GENERATION = 0
# (instant monotonic de réception, durée de frame en ms)
_FRAMES: deque[tuple[float, float]] = deque(maxlen=4000)
# Cache des options supportées par le binaire PresentMon trouvé.
_FLAG_CACHE: dict[tuple[str, str], bool] = {}


def presentmon_path() -> Path | None:
    """Chemin de PresentMon.exe, ou None si absent ou hors Windows.

    Cherche dans l'ordre : sys._MEIPASS/presentmon/ (exe PyInstaller),
    dossier de l'exécutable (et son sous-dossier presentmon/), puis
    data_dir()/bin/. Jamais d'exception.
    """
    try:
        if not is_windows():
            return None
        candidates: list[Path] = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "presentmon" / "PresentMon.exe")
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "PresentMon.exe")
        candidates.append(exe_dir / "presentmon" / "PresentMon.exe")
        candidates.append(data_dir() / "bin" / "PresentMon.exe")
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate
            except OSError:
                continue
        return None
    except Exception:
        return None


def _supports_flag(exe: Path, flag: str) -> bool:
    """Vérifie (best effort, mis en cache) qu'une option figure dans l'aide du binaire."""
    key = (str(exe), flag)
    cached = _FLAG_CACHE.get(key)
    if cached is not None:
        return cached
    supported = False
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0
        result = subprocess.run(
            [str(exe), "--help"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=flags,
        )
        supported = flag in (result.stdout or "") + (result.stderr or "")
    except Exception:
        supported = False
    _FLAG_CACHE[key] = supported
    return supported


def _frame_column_index(header_line: str) -> int | None:
    """Index de la colonne de temps de frame dans l'en-tête CSV, sinon None."""
    columns = [c.strip().lower() for c in header_line.split(",")]
    for name in _FRAME_COLUMNS:
        if name in columns:
            return columns.index(name)
    return None


def _reader(proc: subprocess.Popen, generation: int) -> None:
    """Thread lecteur : parse le CSV de PresentMon et alimente la fenêtre de frames.

    L'en-tête est détecté dynamiquement (colonne msBetweenPresents /
    MsBetweenPresents / FrameTime selon la version). Jamais d'exception.
    """
    column: int | None = None
    try:
        stdout = proc.stdout
        if stdout is None:
            return
        for line in stdout:
            with _LOCK:
                if generation != _GENERATION:
                    return  # capture arrêtée/remplacée entre-temps
            line = line.strip()
            if not line:
                continue
            if column is None:
                column = _frame_column_index(line)
                continue
            parts = line.split(",")
            if column >= len(parts):
                continue
            try:
                frame_ms = float(parts[column])
            except ValueError:
                # Nouvel en-tête éventuel (session relancée) : re-détecter.
                new_column = _frame_column_index(line)
                if new_column is not None:
                    column = new_column
                continue
            if frame_ms <= 0.0:
                continue
            received = time.monotonic()
            with _LOCK:
                if generation != _GENERATION:
                    return
                _FRAMES.append((received, frame_ms))
    except Exception:
        pass


def start(process_name: str) -> bool:
    """Lance la capture PresentMon sur un processus (ex. "cs2.exe").

    Arrête une capture précédente, démarre PresentMon en arrière-plan
    (--output_stdout --stop_existing_session --process_name <nom.exe>,
    plus --terminate_on_proc_exit si l'option est supportée) et parse son
    CSV sur un thread. Jamais d'exception ; False si impossible.
    """
    global _PROC, _THREAD, _GENERATION
    try:
        if not isinstance(process_name, str) or not process_name.strip():
            return False
        stop()
        exe = presentmon_path()
        if exe is None:
            return False
        args = [
            str(exe),
            "--output_stdout",
            "--stop_existing_session",
            "--process_name",
            process_name.strip(),
        ]
        if _supports_flag(exe, "--terminate_on_proc_exit"):
            args.append("--terminate_on_proc_exit")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if is_windows() else 0
        proc = subprocess.Popen(
            args,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            creationflags=flags,
        )
        with _LOCK:
            _GENERATION += 1
            generation = _GENERATION
            _FRAMES.clear()
            _PROC = proc
        thread = threading.Thread(
            target=_reader, args=(proc, generation), daemon=True, name="overdrive-fps"
        )
        with _LOCK:
            _THREAD = thread
        thread.start()
        return True
    except Exception:
        return False


def get_fps() -> float | None:
    """FPS courant (fenêtre glissante d'environ 1 s), ou None.

    None si aucune capture active ou aucune frame reçue depuis moins de 2 s.
    Jamais d'exception.
    """
    try:
        with _LOCK:
            if _PROC is None or not _FRAMES:
                return None
            frames = list(_FRAMES)
        now = time.monotonic()
        if now - frames[-1][0] > _STALE_S:
            return None
        # Remonte depuis la frame la plus récente jusqu'à couvrir ~1 s de jeu.
        total_ms = 0.0
        count = 0
        for received, frame_ms in reversed(frames):
            if now - received > _STALE_S:
                break
            total_ms += frame_ms
            count += 1
            if total_ms >= _WINDOW_S * 1000.0:
                break
        if count == 0 or total_ms <= 0.0:
            return None
        return round(count * 1000.0 / total_ms, 1)
    except Exception:
        return None


def stop() -> None:
    """Arrête proprement la capture (terminate puis kill). Jamais d'exception."""
    global _PROC, _THREAD, _GENERATION
    try:
        with _LOCK:
            _GENERATION += 1
            proc, _PROC = _PROC, None
            thread, _THREAD = _THREAD, None
            _FRAMES.clear()
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except Exception:
                    pass
            try:
                if proc.stdout is not None:
                    proc.stdout.close()
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=1)
            except Exception:
                pass
    except Exception:
        pass
