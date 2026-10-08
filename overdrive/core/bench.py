"""Mini-benchmark système déterministe (CPU, RAM, disque) — sans mesure de FPS.

`run_bench()` exécute environ 10 à 15 s de charges reproductibles :

- ``cpu_single`` : boucle de hachage SHA-256 mono-thread (~3 s), en
  milliers d'itérations par seconde (k-itér/s) ;
- ``cpu_multi``  : même boucle répartie sur tous les cœurs via
  ``multiprocessing.Pool`` (repli mono-thread si le pool échoue, par
  exemple binaire gelé PyInstaller sans fork) ;
- ``ram_mbps``   : bande passante mémoire approximative par copies d'un
  ``bytearray`` de 256 Mo (réduit si peu de RAM disponible) ;
- ``disk_write_mbps`` / ``disk_read_mbps`` : écriture puis relecture d'un
  fichier temporaire de 256 Mo dans ``data_dir()`` (``os.fsync`` inclus
  dans le temps d'écriture, éviction du cache best effort via
  ``posix_fadvise`` quand disponible, fichier supprimé ensuite).

Normalisation du score global ``total`` : chaque sous-score est divisé
par la valeur de référence ``_REFS`` correspondante (ordre de grandeur
d'un PC gaming milieu de gamme ~2020, voir constantes), puis
``total = 100 × moyenne géométrique`` des ratios strictement positifs.
Un ``total`` de 100 correspond donc à la machine de référence ; une
sous-mesure en échec vaut 0.0 et est exclue de la moyenne.

Aucune fonction ne lève d'exception : toute sous-mesure en échec vaut
0.0, le reste du résultat est intact. L'historique (20 entrées max, le
plus récent en premier) est persisté dans ``data_dir()/bench_history.json``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from overdrive.paths import data_dir

_MB = 1024 * 1024

#: Durée cible de chaque boucle de hachage CPU (secondes).
_CPU_SECONDS = 3.0
#: Hachages par lot entre deux lectures de l'horloge.
_HASH_BATCH = 2000
#: Taille cible du tampon RAM et du fichier disque (octets).
_TARGET_SIZE = 256 * _MB
#: Taille minimale acceptée après réduction (octets).
_MIN_SIZE = 32 * _MB
#: Taille des blocs d'E/S disque (octets).
_IO_BLOCK = 4 * _MB
#: Durée minimale visée pour la mesure RAM (secondes).
_RAM_SECONDS = 1.5
#: Nombre maximal d'entrées conservées dans l'historique.
_HISTORY_MAX = 20

#: Valeurs de référence pour la normalisation du score global (``total``).
#: Ordres de grandeur d'un PC gaming milieu de gamme (~2020) : CPU en
#: k-itér/s de la boucle SHA-256, RAM et disque en Mo/s (NVMe d'entrée
#: de gamme). ``total = 100`` ⇔ machine équivalente à cette référence.
_REFS: dict[str, float] = {
    "cpu_single": 1000.0,
    "cpu_multi": 6000.0,
    "ram_mbps": 4000.0,
    "disk_write_mbps": 800.0,
    "disk_read_mbps": 1500.0,
}


# ---------------------------------------------------------------------------
# Charges élémentaires
# ---------------------------------------------------------------------------


def _hash_loop(duration_s: float) -> int:
    """Boucle de hachage SHA-256 chaînée ; renvoie le nombre d'itérations."""
    sha = hashlib.sha256
    data = b"overdrive-bench-charge-deterministe-sha256-0001"
    count = 0
    deadline = time.perf_counter() + duration_s
    while time.perf_counter() < deadline:
        for _ in range(_HASH_BATCH):
            data = sha(data).digest()
        count += _HASH_BATCH
    return count


def _hash_worker(duration_s: float) -> int:
    """Travailleur du pool multi-cœurs (fonction de module : picklable)."""
    return _hash_loop(duration_s)


def _bench_cpu_single() -> float:
    """Score mono-thread : k-itér/s de la boucle de hachage (~3 s)."""
    start = time.perf_counter()
    count = _hash_loop(_CPU_SECONDS)
    elapsed = time.perf_counter() - start
    if elapsed <= 0.0 or count <= 0:
        return 0.0
    return count / elapsed / 1000.0


def _bench_cpu_multi() -> float:
    """Score multi-cœurs : k-itér/s cumulées sur tous les cœurs (~3 s).

    Utilise ``multiprocessing.Pool`` pour contourner le GIL ; en cas
    d'échec du pool (environnement restreint, binaire gelé), repli sur
    une seconde mesure mono-thread.
    """
    workers = max(1, os.cpu_count() or 1)
    per_worker = _CPU_SECONDS - 0.5  # marge pour le démarrage du pool
    try:
        import multiprocessing

        start = time.perf_counter()
        with multiprocessing.Pool(processes=workers) as pool:
            counts = pool.map(_hash_worker, [per_worker] * workers)
        elapsed = time.perf_counter() - start
        total = sum(counts)
        if elapsed <= 0.0 or total <= 0:
            return 0.0
        # Rapporté à la durée de travail effective de chaque cœur, pas au
        # temps mural (qui inclut la création des processus).
        return total / max(per_worker, elapsed - 0.5, 0.1) / 1000.0
    except Exception:  # noqa: BLE001 — repli mono-thread, jamais d'exception
        return _bench_cpu_single()


def _available_ram() -> int | None:
    """Mémoire disponible en octets (None si indéterminable)."""
    try:
        import psutil

        return int(psutil.virtual_memory().available)
    except Exception:  # noqa: BLE001 — psutil optionnel pour cette mesure
        return None


def _bench_ram() -> float:
    """Bande passante RAM approximative (Mo/s) par copies de bytearray.

    Tampon de 256 Mo (ou moins si peu de RAM : au plus un quart de la
    mémoire disponible, deux tampons étant alloués), copié en boucle
    pendant ~1,5 s (3 copies minimum).
    """
    size = _TARGET_SIZE
    avail = _available_ram()
    if avail is not None:
        size = min(size, max(_MIN_SIZE, (avail // 4) // _MB * _MB))
    src = dst = None
    while src is None:
        try:
            src = bytearray(size)
            dst = bytearray(size)
        except MemoryError:
            src = dst = None
            size //= 2
            if size < _MIN_SIZE:
                return 0.0
    copies = 0
    start = time.perf_counter()
    while True:
        dst[:] = src
        copies += 1
        elapsed = time.perf_counter() - start
        if (elapsed >= _RAM_SECONDS and copies >= 3) or copies >= 256:
            break
    if elapsed <= 0.0:
        return 0.0
    return copies * size / _MB / elapsed


def _evict_cache(path: Path) -> None:
    """Demande au système d'évincer le fichier du cache disque (best effort)."""
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except OSError:
        pass


def _disk_size() -> int:
    """Taille du fichier de test (256 Mo, réduit si peu d'espace libre)."""
    size = _TARGET_SIZE
    try:
        import shutil

        free = shutil.disk_usage(data_dir()).free
        size = min(size, max(_MIN_SIZE, (free // 4) // _MB * _MB))
    except OSError:
        pass
    return size


def _bench_disk() -> tuple[float, float]:
    """(écriture Mo/s, lecture Mo/s) sur un fichier temporaire de data_dir().

    Écriture par blocs de 4 Mo (un bloc aléatoire réutilisé, temps de
    ``os.fsync`` inclus), éviction du cache best effort, relecture par
    blocs, fichier supprimé dans tous les cas.
    """
    path = data_dir() / "bench_io.tmp"
    size = _disk_size()
    blocks = max(1, size // _IO_BLOCK)
    write_mbps = read_mbps = 0.0
    try:
        block = os.urandom(_IO_BLOCK)
        start = time.perf_counter()
        with open(path, "wb") as fh:
            for _ in range(blocks):
                fh.write(block)
            fh.flush()
            os.fsync(fh.fileno())
        write_s = time.perf_counter() - start
        if write_s > 0.0:
            write_mbps = blocks * _IO_BLOCK / _MB / write_s

        _evict_cache(path)

        total = 0
        start = time.perf_counter()
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(_IO_BLOCK)
                if not chunk:
                    break
                total += len(chunk)
        read_s = time.perf_counter() - start
        if read_s > 0.0 and total > 0:
            read_mbps = total / _MB / read_s
    except OSError:
        pass
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return write_mbps, read_mbps


# ---------------------------------------------------------------------------
# Historique persistant
# ---------------------------------------------------------------------------


def _history_path() -> Path:
    """Chemin du fichier d'historique des benchmarks."""
    return data_dir() / "bench_history.json"


def _load_history() -> list[dict]:
    """Charge l'historique (liste vide si absent ou corrompu)."""
    try:
        raw = json.loads(_history_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _save_history(history: list[dict]) -> None:
    """Écrit l'historique de façon atomique (best effort)."""
    try:
        target = _history_path()
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def _safe_score(func) -> float:
    """Exécute une sous-mesure ; 0.0 en cas d'échec, jamais d'exception."""
    try:
        value = float(func())
    except Exception:  # noqa: BLE001 — une sous-mesure ne doit jamais lever
        return 0.0
    if value <= 0.0 or value != value or value in (float("inf"), float("-inf")):
        return 0.0
    return round(value, 1)


def _total_score(scores: dict[str, float]) -> float:
    """Score global : 100 × moyenne géométrique des ratios score/référence.

    Seuls les sous-scores strictement positifs participent (une mesure en
    échec, à 0.0, est exclue). 0.0 si aucune mesure n'a abouti.
    """
    ratios = [
        scores[name] / ref
        for name, ref in _REFS.items()
        if scores.get(name, 0.0) > 0.0 and ref > 0.0
    ]
    if not ratios:
        return 0.0
    product = 1.0
    for ratio in ratios:
        product *= ratio
    return round(100.0 * product ** (1.0 / len(ratios)), 1)


def run_bench() -> dict:
    """Exécute le benchmark complet (~10-15 s) et persiste le résultat.

    Renvoie ``{"ts", "duration_s", "scores": {...}, "total"}`` ; toute
    sous-mesure en échec vaut 0.0, la fonction ne lève jamais d'exception.
    Le résultat est ajouté en tête de ``data_dir()/bench_history.json``
    (20 entrées conservées au maximum).
    """
    started = time.perf_counter()
    cpu_single = _safe_score(_bench_cpu_single)
    cpu_multi = _safe_score(_bench_cpu_multi)
    ram_mbps = _safe_score(_bench_ram)
    try:
        disk_write, disk_read = _bench_disk()
    except Exception:  # noqa: BLE001 — jamais d'exception
        disk_write = disk_read = 0.0
    scores = {
        "cpu_single": cpu_single,
        "cpu_multi": cpu_multi,
        "ram_mbps": ram_mbps,
        "disk_write_mbps": round(max(disk_write, 0.0), 1),
        "disk_read_mbps": round(max(disk_read, 0.0), 1),
    }
    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.perf_counter() - started, 1),
        "scores": scores,
        "total": _total_score(scores),
    }
    try:
        history = [result] + _load_history()
        _save_history(history[:_HISTORY_MAX])
    except Exception:  # noqa: BLE001 — la persistance est best effort
        pass
    return result


def get_history() -> list[dict]:
    """Historique persisté des benchmarks, le plus récent en premier."""
    try:
        return _load_history()[:_HISTORY_MAX]
    except Exception:  # noqa: BLE001 — jamais d'exception
        return []
