"""
tests/test_logic.py — Pure-logic unit tests (no pygame required).

Run with:  pytest tests/
"""
import sys
import types

# ---------------------------------------------------------------------------
# Minimal pygame stub so importing si_constants doesn't crash without a
# display.  Only the symbols actually used at module-import time are stubbed.
# ---------------------------------------------------------------------------
_pygame_stub = types.ModuleType("pygame")
_pygame_stub.mixer = types.SimpleNamespace(
    set_num_channels=lambda *a, **k: None,
    init=lambda *a, **k: None,
    Channel=lambda n: None,
    Sound=lambda **k: None,
)
sys.modules.setdefault("pygame", _pygame_stub)

import pytest

from si_constants import (
    FRENZY_TIERS, FRENZY_BANNER_DURATION,
    EXTRA_LIFE_MILESTONES,
    GameState, PowerUpKind, UpgradeId,
)
from si_persistence import (
    load_highscores, save_highscore, load_achievements, save_achievement,
)
from si_entities import Alien, Bullet, EnemyBullet


# ── Enum smoke tests ──────────────────────────────────────────────────────────

def test_gamestate_values():
    assert GameState.TITLE.value      == "TITLE"
    assert GameState.PLAYING.value    == "PLAYING"
    assert GameState.PAUSED.value     == "PAUSED"
    assert GameState.GAME_OVER.value  == "GAME_OVER"
    assert GameState.WAVE_SUMMARY.value == "WAVE_SUMMARY"
    assert GameState.UPGRADE_PICK.value == "UPGRADE_PICK"


def test_powerup_kind_values():
    assert PowerUpKind.RAPID.value  == "rapid"
    assert PowerUpKind.SPREAD.value == "spread"
    assert PowerUpKind.SHIELD.value == "shield"
    assert PowerUpKind.BOMB.value   == "bomb"


def test_upgrade_id_values():
    assert UpgradeId.PIERCE.value    == "pierce"
    assert UpgradeId.EXTRALIFE.value == "extralife"
    assert UpgradeId.DRONE.value     == "drone"


# ── Frenzy tier calculation ───────────────────────────────────────────────────

def _calc_tier(streak: int) -> int:
    """Mirrors Game._frenzy_kill tier logic (pure calculation)."""
    tier = 0
    for i, td in enumerate(FRENZY_TIERS):
        if streak >= td["threshold"]:
            tier = i + 1
    return tier


def test_frenzy_no_tier_below_threshold():
    assert _calc_tier(0)  == 0
    assert _calc_tier(9)  == 0


def test_frenzy_tier1_at_threshold():
    assert _calc_tier(10) == 1
    assert _calc_tier(24) == 1


def test_frenzy_tier2_at_threshold():
    assert _calc_tier(25) == 2
    assert _calc_tier(44) == 2


def test_frenzy_tier3_at_threshold():
    assert _calc_tier(45) == 3
    assert _calc_tier(999) == 3


def test_frenzy_tiers_are_ordered():
    thresholds = [td["threshold"] for td in FRENZY_TIERS]
    assert thresholds == sorted(thresholds), "FRENZY_TIERS must be in ascending order"


# ── Combo multiplier ──────────────────────────────────────────────────────────

def _combo_mult(count: int) -> int:
    return min(5, 1 + count // 2)


def test_combo_mult_starts_at_1():
    assert _combo_mult(0) == 1


def test_combo_mult_increments():
    assert _combo_mult(2) == 2
    assert _combo_mult(4) == 3
    assert _combo_mult(8) == 5


def test_combo_mult_capped_at_5():
    assert _combo_mult(100) == 5


# ── Extra-life milestones ─────────────────────────────────────────────────────

def test_milestones_are_sorted():
    assert EXTRA_LIFE_MILESTONES == sorted(EXTRA_LIFE_MILESTONES)


def test_milestone_count():
    assert len(EXTRA_LIFE_MILESTONES) == 5


def _lives_at_score(score: int) -> int:
    """Simulates milestone tracking from score 0 → score."""
    lives = 3
    idx   = 0
    while idx < len(EXTRA_LIFE_MILESTONES) and score >= EXTRA_LIFE_MILESTONES[idx]:
        lives += 1
        idx   += 1
    return lives


def test_no_extra_life_below_first_milestone():
    assert _lives_at_score(EXTRA_LIFE_MILESTONES[0] - 1) == 3


def test_one_extra_life_at_first_milestone():
    assert _lives_at_score(EXTRA_LIFE_MILESTONES[0]) == 4


def test_all_milestones_give_correct_lives():
    for i, ms in enumerate(EXTRA_LIFE_MILESTONES):
        assert _lives_at_score(ms) == 3 + i + 1


# ── Dataclasses ───────────────────────────────────────────────────────────────

def test_alien_defaults():
    a = Alien(x=100.0, y=200.0, colour=(255, 0, 255), hp=2)
    assert a.x         == 100.0
    assert a.y         == 200.0
    assert a.colour    == (255, 0, 255)
    assert a.hp        == 2
    assert a.hit_flash == 0.0


def test_alien_hit_flash_mutation():
    a = Alien(x=0.0, y=0.0, colour=(0, 255, 0), hp=3)
    a.hit_flash = 0.12
    assert a.hit_flash == 0.12
    a.hp -= 1
    assert a.hp == 2


def test_bullet_defaults():
    b = Bullet(x=960.0, y=500.0, vx=0.0, vy=-1000.0, colour=(255, 255, 0))
    assert b.pierce_remaining == 0
    assert b.is_frag          is False
    assert b.frag_life        == 0.0
    assert b.is_drone         is False


def test_bullet_frag_fields():
    b = Bullet(x=0.0, y=0.0, vx=50.0, vy=-850.0, colour=(255, 136, 0),
               is_frag=True, frag_life=0.55)
    assert b.is_frag   is True
    assert b.frag_life == pytest.approx(0.55)


def test_enemy_bullet_fields():
    eb = EnemyBullet(x=400.0, y=300.0, vx=10.0, vy=450.0)
    assert eb.x  == 400.0
    assert eb.y  == 300.0
    assert eb.vx == 10.0
    assert eb.vy == 450.0


# ── Persistence (uses temp files) ─────────────────────────────────────────────

import json
import os
import tempfile


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


def test_save_and_load_highscore(tmp_path, monkeypatch):
    hs_file = str(tmp_path / "hs.json")
    monkeypatch.setattr("si_persistence.HIGHSCORE_FILE", hs_file)

    # Import the module-level constant patch
    import si_persistence
    monkeypatch.setattr(si_persistence, "HIGHSCORE_FILE", hs_file)

    result = save_highscore("ABC", 1500)
    assert result["scores"][0]["name"]  == "ABC"
    assert result["scores"][0]["score"] == 1500
    assert result["total_score"]        == 1500

    loaded = load_highscores()
    assert loaded["scores"][0]["score"] == 1500


def test_highscores_keeps_top_5(tmp_path, monkeypatch):
    import si_persistence
    monkeypatch.setattr(si_persistence, "HIGHSCORE_FILE",
                        str(tmp_path / "hs2.json"))

    for i, score in enumerate([100, 200, 300, 400, 500, 600]):
        save_highscore(f"P{i}", score)

    data = load_highscores()
    assert len(data["scores"]) == 5
    assert data["scores"][0]["score"] == 600  # highest first


def test_total_score_accumulates(tmp_path, monkeypatch):
    import si_persistence
    monkeypatch.setattr(si_persistence, "HIGHSCORE_FILE",
                        str(tmp_path / "hs3.json"))

    save_highscore("AAA", 1000)
    save_highscore("BBB", 2000)
    data = load_highscores()
    assert data["total_score"] == 3000


def test_save_and_load_achievement(tmp_path, monkeypatch):
    import si_persistence
    monkeypatch.setattr(si_persistence, "ACHIEVEMENT_FILE",
                        str(tmp_path / "achv.json"))

    assert save_achievement("First Blood") is True
    assert save_achievement("First Blood") is False   # already earned

    data = load_achievements()
    assert "First Blood" in data["earned"]


def test_multiple_achievements(tmp_path, monkeypatch):
    import si_persistence
    monkeypatch.setattr(si_persistence, "ACHIEVEMENT_FILE",
                        str(tmp_path / "achv2.json"))

    for name in ("Wave 5", "Wave 10", "Boss Slayer", "Untouchable"):
        assert save_achievement(name) is True

    data = load_achievements()
    assert len(data["earned"]) == 4
