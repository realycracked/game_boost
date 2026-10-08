"""Test de stabilité de la connexion vers une région de jeu.

Pendant une durée bornée (5 à 30 s), une connexion TCP est ouverte
toutes les 250 ms vers l'hôte de la région choisie (catalogue partagé
avec :mod:`overdrive.core.latency`), puis refermée aussitôt sans envoyer
de données. On en déduit la perte (échecs/total), les latences
min/moy/max et la gigue.

Gigue (``jitter_ms``) — formule RFC 3550 simplifiée : moyenne des écarts
absolus ``|L(i) - L(i-1)|`` entre latences successives des connexions
réussies (dans l'ordre de mesure, sans lissage exponentiel ; les échecs
intercalés sont ignorés). Moins de deux réussites → gigue de 0.0 ms.

Le verdict est « stable » si la perte est < 2 % ET la gigue < 10 ms,
« instable » sinon, « indisponible » si aucune connexion n'aboutit
(hôte bloqué par le pare-feu, DNS en échec…). L'appel ne lève jamais
d'exception et ne dépasse jamais ``duration_s + 3`` secondes au total.
"""

from __future__ import annotations

import socket
import time

from overdrive.core.latency import REGIONS

#: Délai maximal d'établissement d'une connexion (secondes).
_CONNECT_TIMEOUT = 1.5
#: Intervalle entre deux connexions (secondes).
_INTERVAL_S = 0.25
#: Bornes de la durée du test (secondes).
_MIN_DURATION_S = 5
_MAX_DURATION_S = 30
#: Échecs consécutifs sans aucune réussite avant abandon anticipé
#: (hôte manifestement injoignable : inutile d'attendre toute la durée).
_MAX_CONSECUTIVE_FAILURES = 12

#: Seuils du verdict « stable » : perte < 2 % ET gigue < 10 ms.
_STABLE_LOSS_PERCENT = 2.0
_STABLE_JITTER_MS = 10.0

#: Libellés FR/EN des verdicts.
_VERDICT_LABELS: dict[str, tuple[str, str]] = {
    "stable": ("Connexion stable", "Stable connection"),
    "instable": ("Connexion instable", "Unstable connection"),
    "indisponible": ("Test indisponible", "Test unavailable"),
}

_REGIONS_BY_ID: dict[str, dict] = {r["id"]: r for r in REGIONS}


def _clamp_duration(duration_s: int) -> int:
    """Durée du test bornée entre 5 et 30 secondes (20 si invalide)."""
    try:
        value = int(duration_s)
    except Exception:
        value = 20
    return max(_MIN_DURATION_S, min(_MAX_DURATION_S, value))


def _jitter_ms(latencies: list[float]) -> float:
    """Gigue RFC 3550 simplifiée : écart absolu moyen entre latences successives."""
    if len(latencies) < 2:
        return 0.0
    deltas = [abs(b - a) for a, b in zip(latencies, latencies[1:])]
    return sum(deltas) / len(deltas)


def _result(region: dict, *, ok: bool, verdict: str, message: str,
            samples: int = 0, loss_percent: float = 0.0,
            latencies: list[float] | None = None) -> dict:
    """Construit le dictionnaire de résultat du test."""
    latencies = latencies or []
    label_fr, label_en = _VERDICT_LABELS[verdict]
    return {
        "ok": ok,
        "region": {
            "id": region.get("id", ""),
            "label": region.get("label", ""),
            "host": region.get("host", ""),
        },
        "samples": samples,
        "loss_percent": round(loss_percent, 1),
        "ms_min": round(min(latencies), 1) if latencies else None,
        "ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "ms_max": round(max(latencies), 1) if latencies else None,
        "jitter_ms": round(_jitter_ms(latencies), 2),
        "verdict": verdict,
        "verdict_label": label_fr,
        "verdict_label_en": label_en,
        "message": message,
    }


def run_stability(region_id: str | None = None, duration_s: int = 20) -> dict:
    """Teste la stabilité de la connexion vers une région (jamais d'exception).

    Une connexion TCP (timeout 1,5 s, refermée aussitôt) est tentée
    toutes les 250 ms vers ``host:port`` de la région pendant
    ``duration_s`` secondes (bornées 5-30). Région par défaut : la
    première du catalogue de :mod:`overdrive.core.latency`.

    Retourne ``{"ok", "region": {id, label, host}, "samples",
    "loss_percent", "ms_min", "ms_avg", "ms_max", "jitter_ms",
    "verdict", "verdict_label", "verdict_label_en", "message"}``.
    Durée totale garantie ≤ ``duration_s + 3`` secondes.
    """
    try:
        if region_id is None:
            region = REGIONS[0] if REGIONS else None
        else:
            region = _REGIONS_BY_ID.get(str(region_id))
        if region is None:
            return _result(
                {"id": str(region_id or ""), "label": "Région inconnue", "host": ""},
                ok=False, verdict="indisponible",
                message=f"Région inconnue : {region_id!r}.")

        host = str(region["host"])
        port = int(region["port"])
        duration = _clamp_duration(duration_s)

        attempts = 0
        failures = 0
        consecutive_failures = 0
        latencies: list[float] = []
        error: str | None = None

        start = time.monotonic()
        deadline = start + duration
        next_at = start
        # Chaque tentative dure au plus 1,5 s : même entamée juste avant
        # l'échéance, la boucle respecte le budget duration_s + 3 s.
        while time.monotonic() < deadline:
            attempts += 1
            t0 = time.perf_counter()
            try:
                sock = socket.create_connection((host, port),
                                                timeout=_CONNECT_TIMEOUT)
            except socket.gaierror:
                # Résolution DNS impossible : inutile de réessayer.
                failures += 1
                error = f"Résolution DNS impossible pour {host}."
                break
            except OSError:
                failures += 1
                consecutive_failures += 1
                if not latencies and consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    error = f"Hôte injoignable : {host}:{port}."
                    break
            else:
                latencies.append((time.perf_counter() - t0) * 1000.0)
                consecutive_failures = 0
                # Aucune donnée envoyée : refermée immédiatement.
                try:
                    sock.close()
                except OSError:
                    pass
            # Cadence : une tentative toutes les 250 ms (sans rattrapage).
            next_at += _INTERVAL_S
            now = time.monotonic()
            if next_at <= now:
                next_at = now
            elif now < deadline:
                time.sleep(min(next_at - now, deadline - now))

        loss_percent = (failures / attempts * 100.0) if attempts else 100.0

        if not latencies:
            return _result(
                region, ok=False, verdict="indisponible",
                samples=attempts, loss_percent=loss_percent,
                message=error or f"Hôte injoignable : {host}:{port}.")

        jitter = _jitter_ms(latencies)
        stable = (loss_percent < _STABLE_LOSS_PERCENT
                  and jitter < _STABLE_JITTER_MS)
        verdict = "stable" if stable else "instable"
        message = (
            f"{len(latencies)} connexion(s) réussie(s) sur {attempts} vers "
            f"{host} : perte {loss_percent:.1f} %, gigue {jitter:.1f} ms."
        )
        return _result(region, ok=True, verdict=verdict,
                       samples=attempts, loss_percent=loss_percent,
                       latencies=latencies, message=message)
    except Exception as exc:  # noqa: BLE001 — jamais d'exception vers l'appelant
        return _result(
            {"id": str(region_id or ""), "label": "", "host": ""},
            ok=False, verdict="indisponible",
            message=f"Erreur inattendue : {exc}")
