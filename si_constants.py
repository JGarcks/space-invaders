"""
si_constants.py — All game-wide constants, colours, and enumerations.

Keeping constants in one place means tuning a value (e.g. DIVE_SPEED) is a
one-line change with no risk of stale copies elsewhere.
"""
from __future__ import annotations

import os
from enum import Enum

# ── Screen ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080
FPS           = 60
GAME_DIR      = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE  = os.path.join(GAME_DIR, "highscores.json")
ACHIEVEMENT_FILE = os.path.join(GAME_DIR, "achievements.json")

# ── Colours ───────────────────────────────────────────────────────────────────
BG        = (10,  10,  46)
CYAN      = (0,   255, 255)
HOT_PINK  = (255, 0,   255)
LIME      = (0,   255, 136)
ORANGE    = (255, 136, 0)
YELLOW    = (255, 255, 0)
RED       = (255, 50,  50)
BLUE      = (80,  140, 255)
WHITE     = (255, 255, 255)
GOLD      = (255, 215, 0)
DIM_WHITE = (140, 140, 160)

# ── State machine ─────────────────────────────────────────────────────────────
class GameState(Enum):
    TITLE        = "TITLE"
    PLAYING      = "PLAYING"
    PAUSED       = "PAUSED"
    GAME_OVER    = "GAME_OVER"
    WAVE_SUMMARY = "WAVE_SUMMARY"
    UPGRADE_PICK = "UPGRADE_PICK"

# ── Power-up kinds ────────────────────────────────────────────────────────────
class PowerUpKind(Enum):
    RAPID  = "rapid"
    SPREAD = "spread"
    SHIELD = "shield"
    BOMB   = "bomb"

# ── Upgrade IDs ───────────────────────────────────────────────────────────────
class UpgradeId(Enum):
    PIERCE    = "pierce"
    REGEN     = "regen"
    BURST     = "burst"
    SPEED     = "speed"
    FRAG      = "frag"
    EXTRALIFE = "extralife"
    DRONE     = "drone"

# ── Ships ─────────────────────────────────────────────────────────────────────
ALIEN_ROW_COLOURS = [HOT_PINK, HOT_PINK, ORANGE, LIME, LIME, HOT_PINK, ORANGE]

SHIP_COLOURS: dict[str, tuple[int, int, int] | None] = {
    "Cyan": CYAN, "Hot Pink": HOT_PINK, "Gold": GOLD, "Rainbow": None,
}
SHIP_UNLOCK_THRESHOLDS: list[tuple[int, str]] = [
    (0,    "Cyan"),
    (500,  "Hot Pink"),
    (2000, "Gold"),
    (5000, "Rainbow"),
]

# ── Player / bullets ──────────────────────────────────────────────────────────
PLAYER_SPEED         = 850
BULLET_SPEED         = 1000
BASE_SHOOT_COOLDOWN  = 0.15
RAPID_SHOOT_COOLDOWN = 0.07
INVINCIBILITY_TIME   = 2.0

# ── Aliens ────────────────────────────────────────────────────────────────────
ALIEN_START_SPEED          = 140
ALIEN_DROP                 = 32
ALIEN_COLS, ALIEN_ROWS     = 10, 5
ALIEN_ROWS_MAX             = 9
ALIEN_X_START, ALIEN_Y_START   = 330, 140
ALIEN_X_SPACING, ALIEN_Y_SPACING = 140, 72

# ── Enemy bullets ─────────────────────────────────────────────────────────────
ENEMY_BULLET_SPEED   = 450
ENEMY_SHOOT_INTERVAL = 1.4

# ── Combo system ──────────────────────────────────────────────────────────────
COMBO_WINDOW = 1.5

# ── Power-ups ─────────────────────────────────────────────────────────────────
POWERUP_FALL_SPEED = 200
POWERUP_DURATION   = 5.0

POWERUP_TYPES   = [pk.value for pk in PowerUpKind]
POWERUP_COLOURS: dict[str, tuple[int, int, int]] = {
    "rapid": YELLOW, "spread": CYAN, "shield": BLUE, "bomb": ORANGE,
}
POWERUP_LABELS: dict[str, str] = {
    "rapid": "RAPID FIRE", "spread": "SPREAD SHOT",
    "shield": "SHIELD",    "bomb":   "BOMB",
}

# ── Extra-life milestones ─────────────────────────────────────────────────────
EXTRA_LIFE_MILESTONES = [1000, 3000, 7000, 15000, 30000]

# ── UFO ───────────────────────────────────────────────────────────────────────
UFO_SPEED        = 380
UFO_SCORE_VALUES = [50, 100, 150, 200, 250, 300]
UFO_INTERVAL_MIN = 20.0
UFO_INTERVAL_MAX = 40.0
UFO_Y            = 68

# ── Barriers ──────────────────────────────────────────────────────────────────
BARRIER_COUNT   = 4
BARRIER_Y       = HEIGHT - 230
BARRIER_BLOCK_W = 14
BARRIER_BLOCK_H = 10

# ── Dive bombers ──────────────────────────────────────────────────────────────
DIVE_INTERVAL_MIN = 14.0
DIVE_INTERVAL_MAX = 28.0
DIVE_SPEED        = 520

# ── Boss ──────────────────────────────────────────────────────────────────────
BOSS_WAVE_INTERVAL = 5

# ── Wingman drone ─────────────────────────────────────────────────────────────
DRONE_ORBIT_RADIUS  = 55
DRONE_ORBIT_SPEED   = 2.5
DRONE_FIRE_COOLDOWN = 0.45

# ── Continue system ───────────────────────────────────────────────────────────
CONTINUE_SCORE_THRESHOLD = 50_000
CONTINUE_WAVE_PENALTY    = 0.5

# ── Frenzy system ─────────────────────────────────────────────────────────────
FRENZY_TIERS: list[dict] = [
    {"threshold": 10, "name": "FRENZY!",      "colour": ORANGE,        "fire_mult": 0.67},
    {"threshold": 25, "name": "FRENZY  II!",  "colour": (255, 120, 0), "fire_mult": 0.50},
    {"threshold": 45, "name": "MAX  FRENZY!", "colour": HOT_PINK,      "fire_mult": 0.40},
]
FRENZY_BANNER_DURATION = 2.2

# ── Upgrades ──────────────────────────────────────────────────────────────────
UPGRADE_DURATION_WAVES = 5
UPGRADE_POOL: list[dict] = [
    {"id": "pierce",    "name": "Bullet Pierce", "colour": CYAN,
     "desc": ["Bullets pass through", "2 additional aliens"]},
    {"id": "regen",     "name": "Barrier Regen", "colour": LIME,
     "desc": ["Barriers restore 1 block", "at the start of each wave"]},
    {"id": "burst",     "name": "Burst Core",    "colour": HOT_PINK,
     "desc": ["Every 4th shot fires", "a 3-bullet burst"]},
    {"id": "speed",     "name": "Speed Boost",   "colour": YELLOW,
     "desc": ["Move 25% faster", "for 5 waves"]},
    {"id": "frag",      "name": "Frag Shots",    "colour": ORANGE,
     "desc": ["Bullets split into 2", "on alien impact"]},
    {"id": "extralife", "name": "Extra Life",    "colour": (100, 255, 100),
     "desc": ["Gain one additional", "life right now"]},
    {"id": "drone",     "name": "Wingman Drone", "colour": (80, 200, 255),
     "desc": ["A drone orbits you", "firing alongside"]},
]

# ── Difficulty ────────────────────────────────────────────────────────────────
DIFFICULTIES = ["Easy", "Normal", "Hard"]
DIFFICULTY_SETTINGS: dict[str, dict[str, float]] = {
    "Easy":   {"speed": 0.70, "fire_rate": 0.60, "powerup": 0.10, "bullet_speed": 0.70},
    "Normal": {"speed": 1.00, "fire_rate": 1.00, "powerup": 0.06, "bullet_speed": 1.00},
    "Hard":   {"speed": 1.40, "fire_rate": 1.50, "powerup": 0.04, "bullet_speed": 1.30},
}

# ── Wave codenames ─────────────────────────────────────────────────────────────
CODENAME_ADJECTIVES: list[str] = [
    "CRIMSON", "IRON", "DARK", "SILENT", "PHANTOM", "GHOST", "SHADOW",
    "NEON", "OMEGA", "ALPHA", "DELTA", "GOLDEN", "SILVER", "CHROME",
    "INFERNO", "VOID", "NEBULA", "COSMIC", "STELLAR", "BRUTAL",
]
CODENAME_NOUNS: list[str] = [
    "TIDE", "STORM", "FURY", "DAWN", "SQUADRON", "FLEET", "ARMADA",
    "SENTINEL", "THUNDER", "ECLIPSE", "VORTEX", "VECTOR", "PROTOCOL",
    "NEXUS", "HORIZON", "IMPACT", "BREACH", "SURGE", "ONSLAUGHT", "DIRECTIVE",
]

# ── Speed bonus ────────────────────────────────────────────────────────────────
SPEED_BONUS_THRESHOLD = 45.0    # seconds — clear faster than this = bonus
SPEED_BONUS_POINTS    = 500

# ── Flawless bonus ─────────────────────────────────────────────────────────────
FLAWLESS_BONUS_POINTS = 2000

# ── Sector themes ─────────────────────────────────────────────────────────────
# Each sector spans 10 waves.  bg is the target background colour (RGB int
# triple); star_tint is multiplied per-channel onto each star's base colour.
SECTOR_DATA: list[dict] = [
    {"name": "SECTOR  I",   "subtitle": "Deep Space",    "bg": (10,  10,  46),  "star_tint": (200, 210, 255)},
    {"name": "SECTOR  II",  "subtitle": "Nebula Field",  "bg": (22,   5,  38),  "star_tint": (255, 180, 255)},
    {"name": "SECTOR  III", "subtitle": "Asteroid Belt", "bg": (14,  11,   8),  "star_tint": (210, 180, 140)},
    {"name": "SECTOR  IV",  "subtitle": "Solar Flare",   "bg": (28,  14,   4),  "star_tint": (255, 240, 180)},
    {"name": "SECTOR  V",   "subtitle": "Deep Anomaly",  "bg": ( 4,   4,   6),  "star_tint": (180, 255, 255)},
]
SECTOR_TRANSITION_DURATION = 4.0   # seconds the banner stays on screen
SECTOR_BG_LERP_SPEED       = 0.8   # fraction per second (exponential lerp)

# ── Boss title cards ──────────────────────────────────────────────────────────
# Keyed by the class name returned by type(boss).__name__
BOSS_TITLES: dict[str, tuple[str, str]] = {
    "Mothership":  ("THE  MOTHERSHIP",   "Prepare for impact."),
    "Dreadnought": ("THE  DREADNOUGHT",  "Find the gap in the shield."),
    "SwarmQueen":  ("THE  SWARM  QUEEN", "She never fights alone."),
    "Phantom":     ("THE  PHANTOM",      "You can't hit what you can't see."),
}
