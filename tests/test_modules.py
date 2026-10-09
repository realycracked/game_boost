"""Modules métier : sensibilité, coffre de clés API, réglages du widget."""

import pytest

from overdrive.core import secure_store, widgetcfg
from overdrive.core.sensitivity import GAMES_SENS, compute, convert


@pytest.mark.parametrize("target", [g["id"] for g in GAMES_SENS if g["id"] != "cs2"])
def test_sensitivity_round_trip_keeps_cm360(target):
    start = compute("cs2", 1.25, 800)["cm360"]
    there = next(c for c in convert("cs2", 1.25, 800)["conversions"] if c["game_id"] == target)
    back = next(c for c in convert(target, there["sens"], 800)["conversions"]
                if c["game_id"] == "cs2")
    assert compute("cs2", back["sens"], 800)["cm360"] == pytest.approx(start, rel=1e-3)


def test_sensitivity_rejects_invalid_input():
    assert convert("cs2", -1, 800)["ok"] is False
    assert convert("cs2", 1.0, 5)["ok"] is False
    assert convert("jeu_inconnu", 1.0, 800)["ok"] is False


def test_api_key_is_encrypted_at_rest():
    secret = "gsk_test_0123456789abcdefghijklmnopqrstuvwxyz"
    assert secure_store.set_key("groq", secret)["ok"] is True
    assert secure_store.get_key("groq") == secret
    stored = secure_store._keys_path().read_bytes()
    assert secret.encode() not in stored
    listed = {k["provider"]: k for k in secure_store.list_keys()}
    assert secret not in repr(listed)
    secure_store.delete_key("groq")
    assert secure_store.get_key("groq") is None


def test_widget_settings_ignore_invalid_values():
    before = widgetcfg.get_widget_settings()
    after = widgetcfg.update_widget_settings({"opacity": "beaucoup", "position": "partout"})
    assert after["opacity"] == before["opacity"]
    assert 0 < after["opacity"] <= 1
