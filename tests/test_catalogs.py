"""Cohérence des catalogues : optimisations, jeux, questionnaire, viseurs."""

import re
from pathlib import Path

import pytest

from overdrive.core.crosshairs import CROSSHAIRS, console_commands, decode_code, encode_code
from overdrive.core.games.catalog import GAMES, get_game
from overdrive.core.quiz import QUESTIONS, compute_profile
from overdrive.core.tweaks.catalog import CATEGORIES, TWEAKS

ROOT = Path(__file__).resolve().parent.parent
TWEAK_IDS = {t["id"] for t in TWEAKS}


def test_tweak_ids_are_unique():
    assert len(TWEAK_IDS) == len(TWEAKS)


@pytest.mark.parametrize("tweak", TWEAKS, ids=lambda t: t["id"])
def test_tweak_is_well_formed(tweak):
    assert tweak["category"] in {c["id"] for c in CATEGORIES}
    assert tweak["risk"] in {"sur", "modere", "avance"}
    assert tweak["impact"] in {"faible", "moyen", "eleve"}
    assert tweak["name"] and tweak["description"]
    assert tweak["name_en"] and tweak["description_en"], "traduction anglaise manquante"
    # Toute optimisation doit pouvoir être annulée.
    assert tweak["apply"], "aucune action apply"
    assert tweak["revert"], "aucune action revert"


def test_no_tweak_touches_security_mitigations_or_defender():
    """Principe affiché dans le README : Spectre/Meltdown et Defender temps réel intouchables."""
    # Limiter la charge CPU des analyses planifiées (Set-MpPreference
    # -ScanAvgCPULoadFactor) reste permis ; couper une protection, non.
    forbidden = re.compile(
        r"FeatureSettingsOverride|DisableRealtimeMonitoring|DisableBehaviorMonitoring"
        r"|DisableIOAVProtection|DisableOnAccessProtection|DisableAntiSpyware"
        r"|ExclusionPath|WinDefend",
        re.IGNORECASE,
    )
    for tweak in TWEAKS:
        actions = repr(tweak["apply"]) + repr(tweak["revert"])
        assert not forbidden.search(actions), tweak["id"]


def test_readme_announces_the_real_tweak_count():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{len(TWEAKS)} optimisations" in readme or f"{len(TWEAKS)} réglages" in readme


def test_twelve_games_with_unique_ids():
    ids = [g["id"] for g in GAMES]
    assert len(ids) == 12
    assert len(set(ids)) == len(ids)
    assert get_game("cs2")["name"] == "Counter-Strike 2"
    assert get_game("inconnu") is None


def test_quiz_has_at_least_five_questions():
    assert len(QUESTIONS) >= 5
    for question in QUESTIONS:
        assert question["options"], question["id"]


@pytest.mark.parametrize("objectif", ["max_fps", "latence", "equilibre", "stream"])
@pytest.mark.parametrize("config", ["haut_de_gamme", "milieu_de_gamme", "modeste", "je_ne_sais_pas"])
def test_quiz_profile_only_recommends_known_tweaks(objectif, config):
    profile = compute_profile({"objectif": objectif, "config": config})
    assert profile["id"] in {"fps", "latence", "equilibre", "stream", "petite_config"}
    assert profile["recommended_tweaks"]
    assert set(profile["recommended_tweaks"]) <= TWEAK_IDS
    risk_order = {"sur": 0, "modere": 1, "avance": 2}
    by_id = {t["id"]: t for t in TWEAKS}
    for tweak_id in profile["recommended_tweaks"]:
        assert risk_order[by_id[tweak_id]["risk"]] <= risk_order[profile["risk_max"]]


def test_modest_pc_gets_low_end_profile():
    assert compute_profile({"objectif": "max_fps", "config": "modeste"})["id"] == "petite_config"


def test_quiz_tolerates_garbage_answers():
    assert compute_profile(None)["id"]  # type: ignore[arg-type]
    assert compute_profile({"objectif": 42, "config": ["x"]})["id"]


@pytest.mark.parametrize("crosshair", CROSSHAIRS, ids=lambda c: c["id"])
def test_crosshair_share_code_round_trip(crosshair):
    decoded = decode_code(crosshair["code"])
    assert decoded is not None
    assert encode_code(decoded) == crosshair["code"]
    assert "cl_crosshairsize" in console_commands(crosshair["params"])


def test_invalid_crosshair_code_is_rejected():
    assert decode_code("CSGO-pas-un-vrai-code") is None
