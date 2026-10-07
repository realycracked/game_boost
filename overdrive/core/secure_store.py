"""Stockage local chiffré des clés API (Fernet + PBKDF2HMAC-SHA256)."""

from __future__ import annotations

import base64
import getpass
import json
import os
import threading
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..paths import data_dir, is_windows

#: Fournisseurs supportés — Groq en premier (clé gratuite sur console.groq.com).
PROVIDERS: list[str] = ["groq", "openai", "anthropic", "gemini"]

_PBKDF2_ITERATIONS = 390_000
_SALT_SIZE = 16

_LOCK = threading.Lock()
_FERNET: Fernet | None = None


def _machine_id() -> str:
    """Identifiant machine stable : MachineGuid (Windows), /etc/machine-id (Linux), sinon uuid.getnode()."""
    if is_windows():
        try:
            import winreg  # import tardif : module Windows uniquement

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
            if value:
                return str(value)
        except OSError:
            pass
    else:
        try:
            text = Path("/etc/machine-id").read_text(encoding="utf-8").strip()
            if text:
                return text
        except OSError:
            pass
    return str(uuid.getnode())


def _username() -> str:
    """Nom d'utilisateur courant (repli sur les variables d'environnement)."""
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "overdrive"


def _salt() -> bytes:
    """Sel aléatoire de 16 octets, persisté dans data_dir()/salt.bin (créé au 1er usage)."""
    path = data_dir() / "salt.bin"
    try:
        salt = path.read_bytes()
        if len(salt) == _SALT_SIZE:
            return salt
    except OSError:
        pass
    salt = os.urandom(_SALT_SIZE)
    path.write_bytes(salt)
    return salt


def _fernet() -> Fernet:
    """Instance Fernet dérivée de machine_id + utilisateur (PBKDF2, 390 000 itérations), mise en cache."""
    global _FERNET
    if _FERNET is None:
        secret = (_machine_id() + _username()).encode("utf-8")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_salt(),
            iterations=_PBKDF2_ITERATIONS,
        )
        _FERNET = Fernet(base64.urlsafe_b64encode(kdf.derive(secret)))
    return _FERNET


def _keys_path() -> Path:
    return data_dir() / "keys.enc"


def _load_keys() -> dict[str, str]:
    """Déchiffre keys.enc ; renvoie {} si absent, illisible ou corrompu (jamais d'exception)."""
    try:
        token = _keys_path().read_bytes()
    except OSError:
        return {}
    try:
        raw = _fernet().decrypt(token)
        data = json.loads(raw.decode("utf-8"))
    except (InvalidToken, ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def _save_keys(keys: dict[str, str]) -> None:
    """Chiffre l'ensemble des clés d'un seul bloc JSON dans keys.enc."""
    payload = json.dumps(keys, ensure_ascii=False).encode("utf-8")
    _keys_path().write_bytes(_fernet().encrypt(payload))


def _mask(api_key: str) -> str:
    """Masque une clé : au plus les 4 derniers caractères, jamais la clé entière."""
    if len(api_key) > 12:
        return f"{api_key[:3]}…{api_key[-4:]}"
    if len(api_key) > 6:
        return f"…{api_key[-4:]}"
    return "…"


def set_key(provider: str, api_key: str) -> dict:
    """Enregistre (chiffrée) la clé API d'un fournisseur. Retour {"ok", "message"}."""
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        return {"ok": False, "message": f"Fournisseur inconnu : {provider!r}."}
    api_key = (api_key or "").strip()
    if not api_key:
        return {"ok": False, "message": "La clé API est vide."}
    try:
        with _LOCK:
            keys = _load_keys()
            keys[provider] = api_key
            _save_keys(keys)
    except Exception:
        return {"ok": False, "message": "Impossible d'enregistrer la clé (erreur de chiffrement ou d'écriture)."}
    return {"ok": True, "message": f"Clé enregistrée pour {provider}."}


def get_key(provider: str) -> str | None:
    """Renvoie la clé API en clair pour un fournisseur, ou None (jamais d'exception)."""
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        return None
    try:
        with _LOCK:
            return _load_keys().get(provider)
    except Exception:
        return None


def delete_key(provider: str) -> dict:
    """Supprime la clé d'un fournisseur. Retour {"ok", "message"}."""
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        return {"ok": False, "message": f"Fournisseur inconnu : {provider!r}."}
    try:
        with _LOCK:
            keys = _load_keys()
            if provider not in keys:
                return {"ok": False, "message": f"Aucune clé enregistrée pour {provider}."}
            del keys[provider]
            _save_keys(keys)
    except Exception:
        return {"ok": False, "message": "Impossible de supprimer la clé (erreur d'écriture)."}
    return {"ok": True, "message": f"Clé supprimée pour {provider}."}


def list_keys() -> list[dict]:
    """État des clés par fournisseur : [{"provider", "configured", "masked"}] (clé jamais en clair)."""
    try:
        with _LOCK:
            keys = _load_keys()
    except Exception:
        keys = {}
    result: list[dict] = []
    for provider in PROVIDERS:
        key = keys.get(provider)
        result.append(
            {
                "provider": provider,
                "configured": bool(key),
                "masked": _mask(key) if key else None,
            }
        )
    return result
