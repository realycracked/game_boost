"""Moteur d'application des tweaks : registre, services, commandes.

Interprète les actions déclaratives du catalogue (`reg`, `reg_delete`,
`powershell`, `cmd`, `service`) via winreg et subprocess (shell=False,
liste d'arguments). L'état des tweaks appliqués est persisté dans
`data_dir()/tweaks_state.json`. Sous Linux, les tweaks `windows_only`
sont refusés proprement, sans exception.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from overdrive.paths import data_dir, is_windows

from .catalog import CATEGORIES, TWEAKS

_SUBPROCESS_TIMEOUT = 90  # secondes, par action
_SC_START_MAP = {
    "disabled": "disabled",
    "manual": "demand",
    "auto": "auto",
    # « Automatique (début différé) », défaut d'usine de WSearch/MapsBroker.
    "delayed-auto": "delayed-auto",
}
# Codes START_TYPE de `sc qc` : 2=AUTO_START, 3=DEMAND_START, 4=DISABLED.
_SC_QC_CODES = {"auto": "2", "manual": "3", "disabled": "4"}

_CATEGORY_IDS = {c["id"] for c in CATEGORIES}
_TWEAKS_BY_ID: dict[str, dict] = {t["id"]: t for t in TWEAKS}


# ---------------------------------------------------------------------------
# État persistant
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    """Chemin du fichier d'état des tweaks."""
    return data_dir() / "tweaks_state.json"


def _load_state() -> dict[str, dict]:
    """Charge l'état persistant (dict vide si absent ou corrompu)."""
    try:
        raw = json.loads(_state_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state: dict[str, dict]) -> None:
    """Écrit l'état persistant de façon atomique (best effort)."""
    try:
        target = _state_path()
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass


#: Sérialise les cycles lecture-modification-écriture de l'état.
_STATE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Instantané des valeurs d'origine de la machine
# ---------------------------------------------------------------------------
# Avant le premier apply d'un tweak, la valeur réellement présente sur CETTE
# machine (registre, type de démarrage des services) est capturée dans
# data_dir()/original_values.json. Au revert, ces valeurs-là sont restaurées
# de préférence aux actions revert « valeurs d'usine » du catalogue.
# Toutes les fonctions ci-dessous supposent _STATE_LOCK déjà détenu par
# l'appelant (apply_tweaks / revert_tweaks) : elles ne le prennent jamais.


def _original_path() -> Path:
    """Chemin du fichier d'instantanés des valeurs d'origine."""
    return data_dir() / "original_values.json"


def _load_original() -> dict[str, dict]:
    """Charge les instantanés (dict vide si absent ou corrompu)."""
    try:
        raw = json.loads(_original_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_original(snapshots: dict[str, dict]) -> None:
    """Écrit les instantanés de façon atomique (best effort)."""
    try:
        target = _original_path()
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(snapshots, ensure_ascii=False, indent=2),
            encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Exécution des actions
# ---------------------------------------------------------------------------


def _creation_flags() -> int:
    """Flags subprocess : pas de fenêtre console sous Windows."""
    if is_windows():
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Exécute une commande (shell=False) et lève RuntimeError si échec."""
    proc = subprocess.run(
        args, shell=False, capture_output=True, text=True,
        timeout=_SUBPROCESS_TIMEOUT, creationflags=_creation_flags())
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        detail = re.sub(r"\s+", " ", detail)[:300]
        raise RuntimeError(
            f"{args[0]} a échoué (code {proc.returncode})"
            + (f" : {detail}" if detail else ""))
    return proc


def _hive(name: str) -> Any:
    """Résout un nom de ruche ('HKCU'/'HKLM') en constante winreg."""
    import winreg
    if name == "HKCU":
        return winreg.HKEY_CURRENT_USER
    if name == "HKLM":
        return winreg.HKEY_LOCAL_MACHINE
    raise RuntimeError(f"Ruche registre inconnue : {name}")


def _reg_data(kind: str, value: Any) -> tuple[int, Any]:
    """Convertit (kind, value) du catalogue en (type winreg, données)."""
    import winreg
    if kind == "dword":
        return winreg.REG_DWORD, int(value)
    if kind == "string":
        return winreg.REG_SZ, str(value)
    if kind == "binary":
        return winreg.REG_BINARY, bytes.fromhex(str(value))
    raise RuntimeError(f"Type registre inconnu : {kind}")


def _exec_reg(action: dict) -> None:
    """Écrit une valeur registre via winreg (crée la clé si besoin)."""
    import winreg
    rtype, data = _reg_data(action["kind"], action["value"])
    access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(_hive(action["hive"]), action["path"], 0,
                            access) as key:
        winreg.SetValueEx(key, action["name"], 0, rtype, data)


def _exec_reg_delete(action: dict) -> None:
    """Supprime une valeur registre (valeur/clé absente = déjà fait)."""
    import winreg
    access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    try:
        with winreg.OpenKeyEx(_hive(action["hive"]), action["path"], 0,
                              access) as key:
            winreg.DeleteValue(key, action["name"])
    except FileNotFoundError:
        return


def _exec_powershell(action: dict) -> None:
    """Exécute une commande PowerShell fixe du catalogue."""
    args = [str(a) for a in action.get("args", [])]
    _run(["powershell.exe"] + args)


def _exec_cmd(action: dict) -> None:
    """Exécute un exécutable avec ses arguments fixes."""
    args = [str(a) for a in action.get("args", [])]
    if not args:
        raise RuntimeError("Action cmd sans arguments.")
    _run(args)


def _exec_service(action: dict) -> None:
    """Configure le type de démarrage d'un service, l'arrête si demandé."""
    service = str(action["service"])
    startup = _SC_START_MAP.get(str(action.get("startup", "")))
    if startup is None:
        raise RuntimeError(f"Type de démarrage inconnu : {action.get('startup')}")
    # NB : sc.exe exige « start= valeur » ; en argv séparés l'espace est produit
    # automatiquement lors de la reconstruction de la ligne de commande Windows.
    _run(["sc.exe", "config", service, "start=", startup])
    if action.get("stop"):
        # Échec toléré : service déjà arrêté ou non démarré.
        _run(["sc.exe", "stop", service], check=False)


_ACTION_HANDLERS = {
    "reg": _exec_reg,
    "reg_delete": _exec_reg_delete,
    "powershell": _exec_powershell,
    "cmd": _exec_cmd,
    "service": _exec_service,
}


def _exec_action(action: dict) -> None:
    """Exécute une action du catalogue ; lève RuntimeError si échec."""
    handler = _ACTION_HANDLERS.get(action.get("type", ""))
    if handler is None:
        raise RuntimeError(f"Type d'action inconnu : {action.get('type')}")
    try:
        handler(action)
    except RuntimeError:
        raise
    except PermissionError:
        raise RuntimeError(
            "Accès refusé : lancez Overdrive en administrateur.") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("Commande trop longue (délai dépassé).") from None
    except FileNotFoundError as exc:
        raise RuntimeError(f"Commande introuvable : {exc}") from None
    except Exception as exc:  # noqa: BLE001 — remonté en message structuré
        raise RuntimeError(str(exc) or exc.__class__.__name__) from None


# ---------------------------------------------------------------------------
# Checks (lecture seule)
# ---------------------------------------------------------------------------


def _check_reg(check: dict) -> bool | None:
    """Compare une valeur registre à la valeur attendue."""
    import winreg
    access = winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_64KEY
    try:
        with winreg.OpenKeyEx(_hive(check["hive"]), check["path"], 0,
                              access) as key:
            value, rtype = winreg.QueryValueEx(key, check["name"])
    except FileNotFoundError:
        return False
    except OSError:
        return None
    expected = check.get("expected")
    if isinstance(value, bytes):
        try:
            return value == bytes.fromhex(str(expected))
        except ValueError:
            return None
    if isinstance(value, int):
        try:
            return value == int(expected)
        except (TypeError, ValueError):
            return None
    return str(value) == str(expected)


def _check_service(check: dict) -> bool | None:
    """Vérifie le type de démarrage d'un service via `sc qc` (code numérique)."""
    expected_code = _SC_QC_CODES.get(str(check.get("expected_startup", "")))
    if expected_code is None:
        return None
    try:
        proc = _run(["sc.exe", "qc", str(check["service"])], check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    match = re.search(r"START_TYPE\s*:\s*(\d+)", proc.stdout or "")
    if not match:
        return None
    return match.group(1) == expected_code


def _run_check(check: dict | None) -> bool | None:
    """Évalue un check best effort ; None si indéterminable."""
    if check is None or not is_windows():
        return None
    try:
        if check.get("type") == "reg":
            return _check_reg(check)
        if check.get("type") == "service":
            return _check_service(check)
    except Exception:  # noqa: BLE001 — un check ne doit jamais lever
        return None
    return None


# ---------------------------------------------------------------------------
# Capture et restauration des valeurs d'origine
# ---------------------------------------------------------------------------


def _capture_reg_entry(action: dict) -> dict:
    """Capture la valeur registre actuelle visée par une action reg/reg_delete.

    Renvoie {hive, path, name, existed, kind, value} ; ``kind`` reprend les
    types du catalogue (dword/string/binary, binaire encodé en hexadécimal)
    et vaut None pour un type non géré (la valeur ne sera pas restaurée).
    """
    import winreg
    entry: dict[str, Any] = {
        "hive": str(action["hive"]),
        "path": str(action["path"]),
        "name": str(action["name"]),
        "existed": False,
        "kind": None,
        "value": None,
    }
    access = winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_64KEY
    try:
        with winreg.OpenKeyEx(_hive(entry["hive"]), entry["path"], 0,
                              access) as key:
            value, rtype = winreg.QueryValueEx(key, entry["name"])
    except FileNotFoundError:
        return entry
    entry["existed"] = True
    if rtype == winreg.REG_DWORD:
        entry["kind"], entry["value"] = "dword", int(value)
    elif rtype == winreg.REG_SZ:
        entry["kind"], entry["value"] = "string", str(value)
    elif rtype == winreg.REG_BINARY:
        entry["kind"], entry["value"] = "binary", bytes(value or b"").hex()
    # Autre type (REG_QWORD, REG_EXPAND_SZ…) : kind reste None, la valeur
    # existante ne sera pas écrasée ni restaurée (best effort).
    return entry


def _capture_service_entry(action: dict) -> dict:
    """Capture le type de démarrage actuel d'un service (code `sc qc`).

    Renvoie {service, start_type_num} ; start_type_num vaut None si le
    service est introuvable ou la sortie illisible.
    """
    service = str(action["service"])
    num: int | None = None
    try:
        proc = _run(["sc.exe", "qc", service], check=False)
        if proc.returncode == 0:
            match = re.search(r"START_TYPE\s*:\s*(\d+)", proc.stdout or "")
            if match:
                num = int(match.group(1))
    except Exception:  # noqa: BLE001 — capture best effort
        num = None
    return {"service": service, "start_type_num": num}


def _capture_original(tweak: dict) -> dict | None:
    """Instantané des valeurs d'origine visées par les actions apply d'un tweak.

    Renvoie None (capture abandonnée, l'apply continue) si la plateforme
    n'est pas Windows, si aucune action reg/reg_delete/service n'est
    concernée, ou en cas d'échec de lecture. Ne lève jamais d'exception.
    """
    if not is_windows():
        return None
    try:
        reg_entries: list[dict] = []
        service_entries: list[dict] = []
        for action in tweak.get("apply") or []:
            kind = action.get("type")
            if kind in ("reg", "reg_delete"):
                reg_entries.append(_capture_reg_entry(action))
            elif kind == "service":
                service_entries.append(_capture_service_entry(action))
        if not reg_entries and not service_entries:
            return None
        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "reg": reg_entries,
            "services": service_entries,
        }
    except Exception:  # noqa: BLE001 — un échec de capture ne bloque rien
        return None


#: Codes START_TYPE de `sc qc` → valeurs `sc config start=` correspondantes.
#: NB : le drapeau « début différé » (AUTO_START (DELAYED)) n'est pas distingué
#: par le code numérique ; un service différé est restauré en `auto` simple.
_SC_NUM_TO_START = {2: "auto", 3: "demand", 4: "disabled"}


def _restore_reg_entry(entry: dict) -> None:
    """Restaure une valeur registre capturée (ou la supprime si absente)."""
    if not entry.get("existed"):
        _exec_reg_delete({"hive": entry["hive"], "path": entry["path"],
                          "name": entry["name"]})
        return
    if entry.get("kind") is None:
        return  # type non géré à la capture : laissé tel quel (best effort)
    _exec_reg({"hive": entry["hive"], "path": entry["path"],
               "name": entry["name"], "kind": entry["kind"],
               "value": entry["value"]})


def _restore_service_entry(entry: dict) -> None:
    """Restaure le type de démarrage d'origine d'un service."""
    startup = _SC_NUM_TO_START.get(entry.get("start_type_num"))
    if startup is None:
        return  # état d'origine inconnu : laissé tel quel (best effort)
    _run(["sc.exe", "config", str(entry["service"]), "start=", startup])


def _restore_snapshot(snapshot: dict) -> None:
    """Restaure toutes les valeurs d'un instantané ; RuntimeError si échec."""
    try:
        for entry in snapshot.get("reg") or []:
            _restore_reg_entry(entry)
        for entry in snapshot.get("services") or []:
            _restore_service_entry(entry)
    except RuntimeError:
        raise
    except PermissionError:
        raise RuntimeError(
            "Accès refusé : lancez Overdrive en administrateur.") from None
    except Exception as exc:  # noqa: BLE001 — remonté en message structuré
        raise RuntimeError(str(exc) or exc.__class__.__name__) from None


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def list_tweaks() -> list[dict]:
    """Catalogue enrichi : supported, applied (best effort) et tracked."""
    state = _load_state()
    windows = is_windows()
    out: list[dict] = []
    for tweak in TWEAKS:
        supported = windows or not tweak.get("windows_only", True)
        entry = dict(tweak)
        entry["supported"] = supported
        entry["applied"] = _run_check(tweak.get("check")) if supported else None
        state_entry = state.get(tweak["id"])
        # tracked = appliqué via Overdrive et pas encore annulé.
        entry["tracked"] = (
            isinstance(state_entry, dict) and not state_entry.get("reverted")
        )
        out.append(entry)
    return out


def _run_actions(tweak_id: str, kind: str) -> dict:
    """Exécute les actions apply/revert d'un tweak ; résultat structuré."""
    tweak = _TWEAKS_BY_ID.get(tweak_id)
    if tweak is None:
        return {"id": tweak_id, "ok": False, "message": "Tweak inconnu."}
    if tweak.get("windows_only", True) and not is_windows():
        return {"id": tweak_id, "ok": False,
                "message": "Disponible uniquement sous Windows."}
    actions = tweak.get(kind) or []
    try:
        for action in actions:
            _exec_action(action)
    except RuntimeError as exc:
        return {"id": tweak_id, "ok": False, "message": f"Échec : {exc}"}
    label = "Appliqué." if kind == "apply" else "Rétabli (valeurs par défaut)."
    return {"id": tweak_id, "ok": True, "message": label}


def apply_tweaks(ids: list[str]) -> list[dict]:
    """Applique les tweaks demandés ; enregistre les succès dans l'état.

    Avant les actions de chaque tweak, les valeurs actuelles de la machine
    sont capturées UNE SEULE fois dans original_values.json (jamais
    écrasées) ; un échec de capture n'empêche pas l'application.
    """
    results: list[dict] = []
    with _STATE_LOCK:
        state = _load_state()
        originals = _load_original()
        changed = False
        originals_changed = False
        for tweak_id in ids:
            tid = str(tweak_id)
            captured: dict | None = None
            tweak = _TWEAKS_BY_ID.get(tid)
            if tweak is not None and tid not in originals:
                captured = _capture_original(tweak)
            result = _run_actions(tid, "apply")
            if result["ok"]:
                if captured is not None and result["id"] not in originals:
                    originals[result["id"]] = captured
                    originals_changed = True
                state[result["id"]] = {
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "reverted": False,
                }
                changed = True
            results.append(result)
        if originals_changed:
            _save_original(originals)
        if changed:
            _save_state(state)
    return results


def _revert_one(tweak_id: str, snapshot: dict | None) -> dict:
    """Rétablit un tweak : instantané d'origine si disponible, sinon catalogue.

    Avec un instantané, les valeurs capturées sur CETTE machine sont
    restaurées à la place des actions revert reg/reg_delete/service du
    catalogue ; les actions powershell/cmd du revert catalogue restent
    exécutées telles quelles, dans l'ordre du catalogue.
    """
    tweak = _TWEAKS_BY_ID.get(tweak_id)
    if tweak is None:
        return {"id": tweak_id, "ok": False, "message": "Tweak inconnu."}
    if tweak.get("windows_only", True) and not is_windows():
        return {"id": tweak_id, "ok": False,
                "message": "Disponible uniquement sous Windows."}
    if not isinstance(snapshot, dict) or not is_windows():
        return _run_actions(tweak_id, "revert")
    try:
        _restore_snapshot(snapshot)
        for action in tweak.get("revert") or []:
            if action.get("type") in ("reg", "reg_delete", "service"):
                continue  # remplacé par la restauration de l'instantané
            _exec_action(action)
    except RuntimeError as exc:
        return {"id": tweak_id, "ok": False, "message": f"Échec : {exc}"}
    return {"id": tweak_id, "ok": True,
            "message": "Rétabli (état d'origine de cette machine)."}


def revert_tweaks(ids: list[str]) -> list[dict]:
    """Rétablit les tweaks demandés ; marque l'état comme réverti."""
    results: list[dict] = []
    with _STATE_LOCK:
        state = _load_state()
        originals = _load_original()
        changed = False
        for tweak_id in ids:
            result = _revert_one(str(tweak_id), originals.get(str(tweak_id)))
            if result["ok"]:
                # Ne trace que les tweaks réellement passés par Overdrive :
                # annuler un tweak jamais appliqué ne crée pas d'entrée.
                entry = state.get(result["id"])
                if isinstance(entry, dict):
                    entry["reverted"] = True
                    entry["reverted_at"] = datetime.now(timezone.utc).isoformat()
                    changed = True
            results.append(result)
        if changed:
            _save_state(state)
    return results


def create_restore_point(description: str = "Overdrive") -> dict:
    """Crée un point de restauration système (Windows uniquement)."""
    if not is_windows():
        return {"ok": False,
                "message": "Points de restauration disponibles uniquement sous Windows."}
    safe = re.sub(r"[^A-Za-z0-9 ._-]", "", description).strip() or "Overdrive"
    command = (f"Checkpoint-Computer -Description '{safe}' "
               f"-RestorePointType 'MODIFY_SETTINGS'")
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            shell=False, capture_output=True, text=True, timeout=180,
            creationflags=_creation_flags())
    except subprocess.TimeoutExpired:
        return {"ok": False,
                "message": "Délai dépassé lors de la création du point de restauration."}
    except OSError as exc:
        return {"ok": False, "message": f"Échec : {exc}"}
    output = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    if "1440" in output:
        # Fréquence limitée par Windows : un point existe depuis moins de 24 h.
        return {"ok": True,
                "message": "Un point de restauration récent existe déjà "
                           "(créé il y a moins de 24 h)."}
    if proc.returncode != 0:
        detail = re.sub(r"\s+", " ", (proc.stderr or proc.stdout or "").strip())[:300]
        return {"ok": False,
                "message": "Impossible de créer le point de restauration"
                           + (f" : {detail}" if detail else ". Vérifiez que la "
                              "protection du système est activée.")}
    return {"ok": True, "message": f"Point de restauration « {safe} » créé."}
