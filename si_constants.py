"""
si_constants.py — All game-wide constants, colours, and enumerations.

Keeping constants in one place means tuning a value (e.g. DIVE_SPEED) is a
one-line change with no risk of stale copies elsewhere.
"""
from __future__ import annotations

import math
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
ALIEN_X_START, ALIEN_Y_START   = 510, 140
ALIEN_X_SPACING, ALIEN_Y_SPACING = 100, 72

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
DIVE_INTERVAL_MIN = 8.0
DIVE_INTERVAL_MAX = 16.0
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
    {"name": "SECTOR  VI",  "subtitle": "Event Horizon", "bg": ( 6,   2,  18),  "star_tint": (220, 180, 255)},
]
SECTOR_TRANSITION_DURATION = 4.0   # seconds the banner stays on screen
SECTOR_BG_LERP_SPEED       = 0.8   # fraction per second (exponential lerp)

# ── Movement patterns ────────────────────────────────────────────────────────
# Sinusoidal Sweep (Sector II)
SINE_AMPLITUDE    = 90       # pixels of vertical oscillation
SINE_FREQ         = 2.0      # oscillations per second
SINE_PHASE_OFFSET = 0.7      # radians of phase delay between rows

# Wave Entry
ENTRY_DURATION    = 1.5      # seconds for an alien to fly into position
ENTRY_SQUAD_DELAY = 0.3      # seconds between squadron groups

# Accordion Pulse (Sector III)
ACCORDION_FREQ    = 1.2      # pulses per second
ACCORDION_RANGE   = 55       # max pixels per unit of column distance

# Rolling Column + Pincer (Sector IV)
ROLL_WAVE_AMPLITUDE = 38     # pixels of sinusoidal Y wave height per column
ROLL_WAVE_FREQ      = 0.9    # wave cycles per second
ROLL_BASE_SPEED   = 8        # retained for import compatibility — no longer drives drift
ROLL_EDGE_BONUS   = 1.5      # retained for import compatibility
PINCER_SPREAD     = 80       # max horizontal separation in pixels
PINCER_TRIGGER_Y  = 96       # pixels descended (via edge bounces) before split activates

# Orbital Ring (Sector V — kept for import compatibility)
ORBIT_RX          = 400      # ellipse X radius
ORBIT_RY          = 260      # ellipse Y radius
ORBIT_SPEED       = 0.5      # radians per second
ORBIT_CENTER_Y    = 350      # center Y of orbit
ORBIT_DRIFT_SPEED = 60       # horizontal drift speed of orbit center

# ── Predator Lock-On (Sector IV) ─────────────────────────────────────────────
PREDATOR_STALK_DURATION  = 5.6   # seconds for lock-on bar to fill (buffed: was 8.0)
PREDATOR_SURGE_DURATION  = 1.6   # seconds for downward surge (buffed: was 2.0)
PREDATOR_SURGE_DROP      = 380   # pixels descended during surge
PREDATOR_RETREAT_SPEED   = 220   # pixels per second on return
PREDATOR_ABORT_THRESHOLD = 0.40  # surge aborts if alive_frac falls below this
PREDATOR_MARCH_DROP      = 32    # pixels down on each edge-bounce (= ALIEN_DROP)

# ── Serpent Chain (Sector V) ──────────────────────────────────────────────────
SERPENT_CENTER_X     = 960    # horizontal centre of Lissajous (screen midpoint)
SERPENT_CENTER_Y     = 500    # vertical centre of curve
SERPENT_AMP_X        = 500    # horizontal amplitude (pixels)
SERPENT_AMP_Y        = 280    # vertical amplitude   (pixels)
SERPENT_FREQ_X       = 0.18   # horizontal oscillations per second
SERPENT_FREQ_Y       = 0.29   # vertical oscillations per second (irrational ratio)
SERPENT_PHASE_Y      = 0.785  # vertical phase offset (π/4 radians)
SERPENT_CHAIN_DELAY  = 0.15   # seconds of delay between consecutive aliens
SERPENT_HISTORY_SIZE = 900    # ring buffer capacity (15 s @ 60 fps)
SERPENT_MIN_ALIENS   = 3      # minimum aliens; below this falls back to scatter

# Sector-to-pattern mapping
SECTOR_MOVEMENT: dict[int, str] = {
    0: "classic",            # Sector I:   Deep Space      — familiar on-ramp
    1: "sinusoidal",         # Sector II:  Nebula Field    — flowing wave
    2: "accordion",          # Sector III: Asteroid Belt   — expanding pulse
    3: "predator",           # Sector IV:  Solar Flare     — lock-on surge
    4: "serpent",            # Sector V:   Deep Anomaly    — Lissajous chain
    5: "orbital",            # Sector VI:  Event Horizon   — ring formation
}

# Entry formation style per sector
SECTOR_ENTRY_STYLE: dict[int, str | None] = {
    0: None,                 # Sector I:   instant appear (gentle start)
    1: "row_sweep",          # Sector II:  alternating row sweep
    2: "column_cascade",     # Sector III: column-by-column drop
    3: "pinch_sides",        # Sector IV:  pinch from both sides
    4: "diagonal_slash",     # Sector V:   diagonal slash entry
    5: "diagonal_slash",     # Sector VI:  dramatic slash entry for the ring
}

# ── Boss title cards ──────────────────────────────────────────────────────────
# Keyed by the class name returned by type(boss).__name__
BOSS_TITLES: dict[str, tuple[str, str]] = {
    "Mothership":  ("THE  MOTHERSHIP",   "Prepare for impact."),
    "Dreadnought": ("THE  DREADNOUGHT",  "Find the gap in the shield."),
    "SwarmQueen":  ("THE  SWARM  QUEEN", "She never fights alone."),
    "Phantom":     ("THE  PHANTOM",      "You can't hit what you can't see."),
}

# ── Pressure Pulse ────────────────────────────────────────────────────────────
PRESSURE_PULSE_INTERVAL = 20.0   # seconds between pulses within a wave
PRESSURE_PULSE_DROP     = 24     # extra pixels the formation drops on pulse (halved — 48 was too aggressive)
PRESSURE_PULSE_BOOST    = 2.0    # enemy fire-rate multiplier during pulse
PRESSURE_PULSE_DURATION = 5.0    # seconds the fire-rate boost lasts

# ── Harbinger Elite Squadron ─────────────────────────────────────────────────
HARBINGER_FIRST_WAVE = 35

# Sentinel
SENTINEL_INTRO_WAVE     = 35
SENTINEL_HP             = 10
SENTINEL_SCORE          = 200
SENTINEL_SPEED          = 120     # px/s horizontal patrol
SENTINEL_SHIELD_GAP     = math.pi * 0.35   # radians
SENTINEL_SHIELD_SPEED   = math.pi / 2      # 90 deg/s
SENTINEL_SHIELD_SPEED_P2 = math.pi * 0.75  # 135 deg/s below 50% HP
SENTINEL_SHIELD_RADIUS  = 55
SENTINEL_SHOOT_INTERVAL = 2.5
SENTINEL_SWOOP_DEPTH    = 180     # px below patrol height
SENTINEL_SWOOP_INTERVAL = 5.0     # seconds between swoops
SENTINEL_DIVE_SPEED_MULT = 2      # multiplier on base speed during dive

# Wraith
WRAITH_INTRO_WAVE       = 40
WRAITH_HP               = 8
WRAITH_SCORE            = 300
WRAITH_TELEPORT_INTERVAL = 4.0
WRAITH_SHIMMER_DURATION = 0.8
WRAITH_INVULN_DURATION  = 0.3
WRAITH_MISSILE_SPEED    = 280
WRAITH_MISSILE_TRACKING = 2.5    # rad/s
WRAITH_MISSILE_LIFETIME = 3.0
WRAITH_SHOOT_INTERVAL   = 2.0

# Leviathan
LEVIATHAN_INTRO_WAVE    = 50
LEVIATHAN_HEAD_HP       = 5
LEVIATHAN_SEGMENT_HP    = 2
LEVIATHAN_SEGMENTS      = 4      # body segments (total = 1 head + N body)
LEVIATHAN_SEGMENT_SPACING = 36   # px between segments
LEVIATHAN_SPEED         = 80     # px/s horizontal drift
LEVIATHAN_BOB_AMP       = 40     # px vertical bob amplitude
LEVIATHAN_BOB_FREQ      = 0.8    # oscillations/s
LEVIATHAN_SHOOT_INTERVAL = 3.0
LEVIATHAN_REGROW_TIME   = 5.0    # seconds to regrow head after split
LEVIATHAN_HEAD_SCORE    = 300
LEVIATHAN_SEGMENT_SCORE = 100
LEVIATHAN_DESCENT_RATE  = 12      # px/s downward creep
LEVIATHAN_DESCENT_CAP   = 500     # max Y before stopping descent
LEVIATHAN_PHASE_OFFSET  = 0.5     # radians between segments in bob

# Archon
ARCHON_INTRO_WAVE       = 55
ARCHON_HP               = 12
ARCHON_SCORE            = 500
ARCHON_SPEED            = 100
ARCHON_BEAM_WARN_TIME   = 1.5    # seconds of warning glow
ARCHON_BEAM_ACTIVE_TIME = 3.0    # seconds beam stays active
ARCHON_BEAM_COOLDOWN    = 5.0    # seconds between beams
ARCHON_CAPTURE_TIME     = 2.0    # seconds in beam to capture
ARCHON_BEAM_WIDTH       = 40     # pixels wide
ARCHON_BEAM_INIT_WIDTH  = 8      # narrow width during warning phase
ARCHON_SHOOT_INTERVAL   = 2.0
ARCHON_ORBIT_SPEED      = 0.55   # rad/s figure-8 orbit
ARCHON_ORBIT_VERT_AMP   = 90     # px vertical amplitude
ARCHON_BEAM_DRIFT_SPEED = 45     # px/s beam tracks player during active

# Harbinger powerup drop chance (higher than regular aliens)
HARBINGER_DROP_CHANCE   = 0.50

# ── Colossus Boss ────────────────────────────────────────────────────────────
COLOSSUS_FIRST_WAVE     = 50
COLOSSUS_WAVE_INTERVAL  = 20
COLOSSUS_TURRET_BASE_HP = 15
COLOSSUS_TURRET_HP_SCALE = 4
COLOSSUS_CORE_BASE_HP   = 40
COLOSSUS_CORE_HP_SCALE  = 12
COLOSSUS_SPEED          = 80
COLOSSUS_TURRET_SCORE   = 200
COLOSSUS_WIDTH          = 400    # visual width
COLOSSUS_HEIGHT         = 200    # visual height

BOSS_TITLES["Colossus"] = ("THE  COLOSSUS", "Destroy the turrets to expose the core.")

# ── New Power-Up Kinds ───────────────────────────────────────────────────────
class PowerUpKindEx(Enum):
    """Extended power-up kinds (wave 35+)."""
    HOMING    = "homing"
    EMP       = "emp"
    OVERCHARGE = "overcharge"
    TIMEWARP  = "timewarp"

POWERUP_COLOURS["homing"]     = (180, 80, 255)   # purple
POWERUP_COLOURS["emp"]        = (100, 200, 255)   # light blue
POWERUP_COLOURS["overcharge"] = (255, 255, 100)   # bright yellow
POWERUP_COLOURS["timewarp"]   = (80, 180, 255)    # blue

POWERUP_LABELS["homing"]     = "HOMING"
POWERUP_LABELS["emp"]        = "EMP"
POWERUP_LABELS["overcharge"] = "OVERCHARGE"
POWERUP_LABELS["timewarp"]   = "TIME WARP"

# Drop weight table (wave 35+). Higher weight = more common.
POWERUP_WEIGHTS_EARLY: dict[str, float] = {
    "rapid": 1.0, "spread": 1.0, "shield": 1.0, "bomb": 1.0,
}
POWERUP_WEIGHTS_LATE: dict[str, float] = {
    "rapid": 0.6, "spread": 0.6, "shield": 1.0, "bomb": 1.0,
    "homing": 1.5, "overcharge": 1.5, "emp": 1.2, "timewarp": 1.2,
}

# Homing bullet tracking
HOMING_BULLET_TRACKING = 3.0     # rad/s

# ── Solar Flare Hazard (Sector IV) ──────────────────────────────────────────
SOLAR_FLARE_INTERVAL   = 15.0    # seconds between flares
SOLAR_FLARE_WARN_TIME  = 2.0     # seconds of warning before beam
SOLAR_FLARE_ACTIVE_TIME = 0.5    # seconds beam stays active
SOLAR_FLARE_BEAM_HEIGHT = 40     # pixels tall

# ── Bonus Round ─────────────────────────────────────────────────────────────
BONUS_ROUND_INTERVAL   = 25      # every 25 waves
BONUS_ROUND_ENEMIES    = 160
BONUS_ROUND_SCORE      = 100     # per enemy
BONUS_ROUND_PERFECT    = 10000   # perfect bonus
BONUS_ROUND_DURATION   = 30.0    # seconds
BONUS_FRAG_RADIUS      = 75.0    # pixels — chain-kill radius on explosion
BONUS_POWERUP_EVERY    = 5       # drop a power-up every N kills

# ── Graze Scoring ───────────────────────────────────────────────────────────
GRAZE_DISTANCE         = 15      # pixels (outer threshold)
GRAZE_INNER_DISTANCE   = 18      # pixels (inner — closer is a hit, not a graze)
GRAZE_POINTS           = 25

# ── Proximity Kill ──────────────────────────────────────────────────────────
PROXIMITY_KILL_DISTANCE = 120    # pixels
PROXIMITY_KILL_MULT     = 2      # score multiplier

# ── Weapon Synergies ────────────────────────────────────────────────────────
SYNERGY_DEFINITIONS: list[dict] = [
    {"id": "shrapnel_storm",  "name": "SHRAPNEL STORM",  "reqs": ["pierce", "frag"],
     "colour": ORANGE,        "desc": "Pierce + split on every hit"},
    {"id": "bullet_hell",     "name": "BULLET HELL",     "reqs": ["burst", "spread"],
     "colour": HOT_PINK,      "desc": "Burst fires 5-bullet fan"},
    {"id": "guardian_angel",  "name": "GUARDIAN ANGEL",   "reqs": ["drone", "speed"],
     "colour": CYAN,          "desc": "Drone fires 2x faster"},
    {"id": "glass_cannon",    "name": "GLASS CANNON",    "reqs": ["rapid_pu", "frag"],
     "colour": RED,           "desc": "2x frag damage, 2x damage taken"},
    {"id": "fortress",        "name": "FORTRESS",        "reqs": ["regen", "burst"],
     "colour": LIME,          "desc": "Barriers regen 3 blocks"},
    {"id": "predator_syn",    "name": "PREDATOR",        "reqs": ["pierce", "speed"],
     "colour": YELLOW,        "desc": "50% faster bullets, +1 pierce"},
    {"id": "seeker_swarm",    "name": "SEEKER SWARM",    "reqs": ["homing_pu", "frag"],
     "colour": (180, 80, 255), "desc": "Homing frag splits track enemies"},
    {"id": "chain_lightning",  "name": "CHAIN LIGHTNING", "reqs": ["homing_pu", "pierce"],
     "colour": (100, 200, 255), "desc": "Homing chains through 3 enemies"},
    {"id": "magnetic_storm",  "name": "MAGNETIC STORM",  "reqs": ["emp_pu", "drone"],
     "colour": BLUE,          "desc": "EMP triggers drone burst"},
    {"id": "berserker",       "name": "BERSERKER",       "reqs": ["overcharge_pu", "burst"],
     "colour": (255, 255, 100), "desc": "Every shot is a burst"},
    {"id": "frozen_barrage",  "name": "FROZEN BARRAGE",  "reqs": ["timewarp_pu", "spread"],
     "colour": (80, 180, 255), "desc": "5-bullet spread with 1.5x damage"},
    {"id": "annihilator",     "name": "ANNIHILATOR",     "reqs": ["overcharge_pu", "pierce"],
     "colour": WHITE,         "desc": "3x damage, pierces shields"},
]
