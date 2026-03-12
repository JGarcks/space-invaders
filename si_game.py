"""
si_game.py — The Game class (refactored from space_invaders.py).

All entity lists now use typed dataclasses (Alien, Bullet, EnemyBullet) instead
of plain dicts.  All state comparisons use GameState enum values.  All sounds
are routed through SoundManager (self.sfx) rather than module-level globals.
"""
from __future__ import annotations

import math
import random
import sys

import pygame

from si_constants import (
    WIDTH, HEIGHT, FPS,
    BG, CYAN, HOT_PINK, LIME, ORANGE, YELLOW, RED, BLUE, WHITE, GOLD, DIM_WHITE,
    ALIEN_ROW_COLOURS, SHIP_COLOURS, SHIP_UNLOCK_THRESHOLDS,
    PLAYER_SPEED, BULLET_SPEED, ALIEN_START_SPEED, ALIEN_DROP,
    ALIEN_COLS, ALIEN_ROWS, ALIEN_ROWS_MAX,
    ALIEN_X_START, ALIEN_Y_START, ALIEN_X_SPACING, ALIEN_Y_SPACING,
    BASE_SHOOT_COOLDOWN, RAPID_SHOOT_COOLDOWN,
    COMBO_WINDOW, POWERUP_FALL_SPEED, POWERUP_DURATION, INVINCIBILITY_TIME,
    ENEMY_BULLET_SPEED, ENEMY_SHOOT_INTERVAL,
    EXTRA_LIFE_MILESTONES,
    UFO_SPEED, UFO_SCORE_VALUES, UFO_INTERVAL_MIN, UFO_INTERVAL_MAX, UFO_Y,
    BARRIER_COUNT, BARRIER_Y, BARRIER_BLOCK_W, BARRIER_BLOCK_H,
    DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX, DIVE_SPEED,
    BOSS_WAVE_INTERVAL,
    DRONE_ORBIT_RADIUS, DRONE_ORBIT_SPEED, DRONE_FIRE_COOLDOWN,
    CONTINUE_SCORE_THRESHOLD, CONTINUE_WAVE_PENALTY,
    FRENZY_TIERS, FRENZY_BANNER_DURATION,
    UPGRADE_DURATION_WAVES, UPGRADE_POOL,
    DIFFICULTIES, DIFFICULTY_SETTINGS,
    POWERUP_TYPES, POWERUP_COLOURS, POWERUP_LABELS,
    GameState, PowerUpKind, UpgradeId,
    CODENAME_ADJECTIVES, CODENAME_NOUNS,
    SPEED_BONUS_THRESHOLD, SPEED_BONUS_POINTS,
    FLAWLESS_BONUS_POINTS,
    SECTOR_DATA, SECTOR_TRANSITION_DURATION, SECTOR_BG_LERP_SPEED,
    BOSS_TITLES,
    PRESSURE_PULSE_INTERVAL, PRESSURE_PULSE_DROP,
    PRESSURE_PULSE_BOOST, PRESSURE_PULSE_DURATION,
    SENTINEL_HP, WRAITH_HP, ARCHON_HP,
    SOLAR_FLARE_INTERVAL,
    BONUS_ROUND_INTERVAL, BONUS_ROUND_ENEMIES, BONUS_ROUND_SCORE,
    BONUS_ROUND_PERFECT, BONUS_ROUND_DURATION,
    BONUS_FRAG_RADIUS, BONUS_POWERUP_EVERY,
    GRAZE_DISTANCE, GRAZE_INNER_DISTANCE, GRAZE_POINTS,
    PROXIMITY_KILL_DISTANCE, PROXIMITY_KILL_MULT,
    POWERUP_WEIGHTS_EARLY, POWERUP_WEIGHTS_LATE, PowerUpKindEx,
    SYNERGY_DEFINITIONS,
    COLOSSUS_TURRET_SCORE,
    ARCHON_CAPTURE_TIME,
    HOMING_BULLET_TRACKING,
)
from si_audio import SoundManager
from si_entities import (
    Alien, Bullet, EnemyBullet,
    Particle, Star, PowerUp, AchievementBanner, ComboPopup,
    UFO, Barrier, DiveBomber, GalagaDiver, ShipFragment,
    Mothership, Dreadnought, SwarmQueen, Phantom, Colossus, make_boss,
    draw_ship, draw_alien_a, draw_alien_b,
    Sentinel, Wraith, HomingMissile, Leviathan, LeviathanSegment,
    Archon, ColossusTurret, WeightedPowerUp, SolarFlare, BonusEnemy,
    _HarbingerBase,
)
from si_persistence import (
    load_highscores, save_highscore,
    load_achievements, save_achievement,
    save_json,
)
from si_movement import create_movement_pattern, OrbitalRing, PredatorLockOn, SerpentChain
from si_constants import HIGHSCORE_FILE


class Game:
    def __init__(self) -> None:
        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF
        try:
            flags |= pygame.SCALED
        except Exception:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Space Invaders")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("consolas", 80, bold=True)
        self.font_lv  = pygame.font.SysFont("consolas", 52, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 36)
        self.font_sm  = pygame.font.SysFont("consolas", 26)
        self.font_xs  = pygame.font.SysFont("consolas", 20)

        # Sound manager
        self.sfx = SoundManager()
        self.sfx.preload_all()

        # CRT overlay (pre-baked; zero per-frame cost)
        self.crt_enabled = True
        self.scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for sy in range(0, HEIGHT, 2):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 77), (0, sy), (WIDTH, sy))
        self.vignette_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        vd = 220
        for i in range(vd):
            alpha = int(160 * ((1 - i / vd) ** 2))
            pygame.draw.line(self.vignette_surf, (0, 0, 0, alpha), (0, i), (WIDTH, i))
            pygame.draw.line(self.vignette_surf, (0, 0, 0, alpha), (0, HEIGHT-1-i), (WIDTH, HEIGHT-1-i))
            pygame.draw.line(self.vignette_surf, (0, 0, 0, alpha), (i, 0), (i, HEIGHT))
            pygame.draw.line(self.vignette_surf, (0, 0, 0, alpha), (WIDTH-1-i, 0), (WIDTH-1-i, HEIGHT))

        self.stars: list[Star] = []
        for layer in range(3):
            for _ in range([60, 50, 30][layer]):
                self.stars.append(Star(layer))

        self.state: GameState = GameState.TITLE
        self.hs_data   = load_highscores()
        self.achv_data = load_achievements()
        self.selected_ship = "Cyan"
        self._unlock_ships()

        self.title_pulse = 0.0

        # ── Konami code ───────────────────────────────────────────────────────
        self._konami_seq = [
            pygame.K_UP, pygame.K_UP, pygame.K_DOWN, pygame.K_DOWN,
            pygame.K_LEFT, pygame.K_RIGHT, pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_b, pygame.K_a,
        ]
        self.konami_buffer: list[int] = []
        self.konami_pending: bool    = False   # code entered, awaits next game
        self.konami_active:  bool    = False   # cheat mode ON this run

        self.entering_name = False
        self.name_chars = ["A", "A", "A"]
        self.name_cursor = 0
        self.pending_score = 0

        self.difficulty = "Normal"
        self.bomb_flash_timer = 0.0
        self._bomb_flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._frenzy_glow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._frenzy_vignette_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._frenzy_halo_surf = pygame.Surface((80, 80), pygame.SRCALPHA)

        self._init_game()

    # ── Ship helpers ──────────────────────────────────────────────────────────

    def _unlock_ships(self) -> None:
        total = self.hs_data.get("total_score", 0)
        self.unlocked_ships: list[str] = []
        for threshold, name in SHIP_UNLOCK_THRESHOLDS:
            if total >= threshold:
                self.unlocked_ships.append(name)

    def _get_ship_colour(self) -> tuple[int, int, int]:
        if self.selected_ship == "Rainbow":
            t = pygame.time.get_ticks() / 500
            r = int(127 + 128 * math.sin(t))
            g = int(127 + 128 * math.sin(t + 2.09))
            b = int(127 + 128 * math.sin(t + 4.19))
            return (r, g, b)
        return SHIP_COLOURS.get(self.selected_ship, CYAN)  # type: ignore[return-value]

    # ── Game initialisation ───────────────────────────────────────────────────

    def _init_game(self) -> None:
        self.player_x: float = WIDTH // 2
        self.player_y: float = HEIGHT - 80
        self.lives = 4
        self.score = 0
        self.wave = 1
        self.alien_dir = 1
        self.alien_speed = ALIEN_START_SPEED
        self.shoot_cooldown = 0.0
        self.bullets:       list[Bullet]      = []
        self.aliens:        list[Alien]       = []
        self.enemy_bullets: list[EnemyBullet] = []
        self.enemy_shoot_timer    = 0.0
        self.enemy_shoot_interval = ENEMY_SHOOT_INTERVAL
        self._base_shoot_interval = ENEMY_SHOOT_INTERVAL
        self.enemy_bullet_speed   = ENEMY_BULLET_SPEED
        self.current_alien_drop   = ALIEN_DROP
        self.powerups:    list[PowerUp]          = []
        self.particles:   list[Particle]         = []
        self.combo_popups: list[ComboPopup]      = []
        self.banners:     list[AchievementBanner] = []
        self.combo_count = 0
        self.combo_timer = 0.0
        self.combo_multiplier = 1
        self.active_powerups: dict[str, float] = {}
        self.has_shield = False
        self.invincible_timer = 0.0
        self.alien_anim_timer = 0.0
        self.alien_frame = 0
        self.shake_timer     = 0.0
        self.shake_intensity = 0
        self.shots_fired = 0
        self.shots_hit   = 0
        self.wave_damage_taken      = False
        self.powerups_collected_wave = 0
        self.bomb_flash_timer = 0.0
        self.last_stand_active = False
        self.pressure_pulse_timer  = PRESSURE_PULSE_INTERVAL
        self.pressure_pulse_active = 0.0
        self.ufo: UFO | None = None
        self.ufo_timer = random.uniform(UFO_INTERVAL_MIN, UFO_INTERVAL_MAX)
        self.barriers: list[Barrier] = self._make_barriers()
        self.dive_bombers: list[DiveBomber] = []
        self.galaga_divers: list[GalagaDiver] = []
        self.galaga_kill_counter = 0
        self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
        self.powerup_drop_chance = DIFFICULTY_SETTINGS[self.difficulty]["powerup"]

        self.next_life_milestone_idx = 0
        self.boss: Mothership | Dreadnought | SwarmQueen | Phantom | Colossus | None = None

        self.wave_summary_timer = 0.0
        self.wave_summary_data: dict[str, object] = {}
        self.wave_kills = 0
        self.wave_start_time = pygame.time.get_ticks() / 1000.0
        self.wave_flawless        = True    # True until any hit lands (even vs shield)
        self.last_alien_announced = False   # True once "LAST ONE!" has been shown
        self.wave_codename        = ""
        self.ship_fragments: list[ShipFragment] = []
        self.konami_active = False

        self.active_upgrades: dict[str, int] = {}
        self.upgrade_choices: list[dict[str, object]] = []
        self.upgrade_cursor = 1
        self.burst_shot_count = 0

        self.frenzy_streak       = 0
        self.frenzy_tier         = 0
        self.frenzy_banner_timer = 0.0
        self.frenzy_banner_tier  = 0
        self._music_tier: int    = 0

        self._low_life_timer  = 0.0
        self.wave_clear_flash = 0.0

        self.drone_angle      = 0.0
        self.drone_active     = False
        self.drone_fire_timer = 0.0

        self.continue_available = False
        self.continue_used      = False

        self.frenzy_beyond_kills = 0
        self.frenzy_beyond_level = 0

        self.boss_phase         = 0
        self.boss_phase_timer   = 3.0
        self.boss_spread_cooldown = 0.0

        self.boss_cinematic_timer = 0.0
        self.boss_cinematic_x     = 0.0
        self.boss_cinematic_y     = 0.0

        # ── Sector theme state ────────────────────────────────────────────────
        self.current_sector: int            = 0
        sector                              = SECTOR_DATA[0]
        self.sector_bg: list[float]         = list(float(c) for c in sector["bg"])
        self.sector_bg_target: list[float]  = list(float(c) for c in sector["bg"])
        self.sector_star_tint: tuple[int, int, int] = sector["star_tint"]
        self.sector_transition_timer: float = 0.0
        self.sector_transition_name:  str   = ""
        self.sector_transition_sub:   str   = ""

        # ── Boss title card state ─────────────────────────────────────────────
        self.boss_title_timer: float = 0.0
        self.boss_title_name:  str   = ""
        self.boss_title_sub:   str   = ""

        # ── Harbinger Elite Squadron ─────────────────────────────────────────
        self.harbingers: list[_HarbingerBase] = []
        self.homing_missiles: list[HomingMissile] = []

        # ── Solar Flare (Sector IV) ─────────────────────────────────────────
        self.solar_flare: SolarFlare = SolarFlare()

        # ── Bonus Round ──────────────────────────────────────────────────────
        self.bonus_round_active: bool = False
        self.bonus_round_enemies: list[BonusEnemy] = []
        self.bonus_round_killed: int = 0
        self.bonus_round_timer: float = 0.0

        # ── Graze Scoring ────────────────────────────────────────────────────
        self.graze_count: int = 0
        self.wave_graze_count: int = 0

        # ── Weapon Synergies ─────────────────────────────────────────────────
        self.active_synergies: set[str] = set()

        # ── Dual Fighter (Archon reward) ─────────────────────────────────────
        self.dual_fighter: bool = False
        self.dual_fighter_wave: int = 0  # wave it was activated on

        # ── Reinforcement wave tracking (waves 50+) ─────────────────────────
        self.reinforcement_sent: bool = False

        self._spawn_wave()

    def _spawn_swarm_queen_drones(self) -> None:
        """Spawn a mini alien swarm when the SwarmQueen calls for reinforcements."""
        drone_hp    = 1
        drone_colour = LIME
        sprite_tier = 0   # squid tier — small and fast-looking
        count       = min(6 + self.wave // 5, 14)
        xs = [
            ALIEN_X_START + col * ALIEN_X_SPACING
            for col in range(ALIEN_COLS)
        ]
        random.shuffle(xs)
        for i in range(count):
            ax = xs[i % len(xs)] + random.randint(-40, 40)
            ay = ALIEN_Y_START + random.randint(-40, 60)
            self.aliens.append(
                Alien(x=float(ax), y=float(ay), colour=drone_colour,
                      hp=drone_hp, sprite_tier=sprite_tier,
                      grid_col=i % ALIEN_COLS, grid_row=i // ALIEN_COLS,
                      base_x=float(ax), base_y=float(ay))
            )
        # Short flash/shake to signal the spawn event
        self._add_shake(6, 0.3)
        self.banners.append(AchievementBanner("SWARM!", self.font_sm))

    def _make_barriers(self) -> list[Barrier]:
        barriers = []
        margin  = 280
        spacing = (WIDTH - 2 * margin) // (BARRIER_COUNT - 1)
        for i in range(BARRIER_COUNT):
            cx = margin + i * spacing
            barriers.append(Barrier(cx, BARRIER_Y))
        return barriers

    def _spawn_wave(self) -> None:
        self.aliens = []
        self.boss   = None

        diff = DIFFICULTY_SETTINGS[self.difficulty]

        # ── Bonus round check (every 25 waves) ──────────────────────────
        if self.wave > 1 and self.wave % BONUS_ROUND_INTERVAL == 0:
            self._start_bonus_round()
            return

        if self.wave % BOSS_WAVE_INTERVAL == 0:
            self.boss = make_boss(self.wave)
            self.sfx.play("boss")
            # Show boss title card
            boss_key = type(self.boss).__name__
            title, sub = BOSS_TITLES.get(boss_key, (boss_key, ""))
            self.boss_title_name  = title
            self.boss_title_sub   = sub
            self.boss_title_timer = 3.8
        else:
            y_offset = min((self.wave - 1) * 8, 100)
            rows     = min(ALIEN_ROWS_MAX, ALIEN_ROWS + (self.wave - 1) // 8)
            alien_hp = min(3, 1 + (self.wave - 1) // 20)
            for row in range(rows):
                # Sprite tier: top rows=squid(0), mid=crab(1), bottom=octopus(2)
                sprite_tier = min(2, row // 2)
                for col in range(ALIEN_COLS):
                    ax     = ALIEN_X_START + col * ALIEN_X_SPACING
                    ay     = ALIEN_Y_START + row * ALIEN_Y_SPACING + y_offset
                    colour = ALIEN_ROW_COLOURS[row % len(ALIEN_ROW_COLOURS)]
                    self.aliens.append(
                        Alien(x=ax, y=ay, colour=colour, hp=alien_hp,
                              sprite_tier=sprite_tier,
                              grid_col=col, grid_row=row, base_x=ax, base_y=ay)
                    )

        self.alien_dir = 1
        raw_speed = ALIEN_START_SPEED * (1 + 0.010 * (self.wave - 1)) * diff["speed"]
        self.alien_speed = min(raw_speed, 340)
        self.enemy_shoot_interval = max(
            0.55, (ENEMY_SHOOT_INTERVAL - 0.09 * (self.wave - 1)) / diff["fire_rate"]
        )
        self.enemy_bullet_speed = min(
            450, (ENEMY_BULLET_SPEED + 10 * (self.wave - 1)) * diff["bullet_speed"]
        )
        # Drop rate rebalance: higher cap past wave 40
        drop_cap = 0.28 if self.wave >= 40 else 0.22
        self.powerup_drop_chance  = min(diff["powerup"] + self.wave * 0.003, drop_cap)
        # Power-up duration scales with wave
        self.powerup_duration = min(8, 5 + (self.wave - 1) // 20)
        self.current_alien_drop   = min(40, ALIEN_DROP + self.wave // 3)
        self.enemy_shoot_timer    = self.enemy_shoot_interval
        self._base_shoot_interval = self.enemy_shoot_interval
        self.enemy_bullets        = []
        self.wave_damage_taken    = False
        self.wave_flawless        = True
        self.last_alien_announced = False
        self.powerups_collected_wave = 0
        self.shots_fired = 0
        self.shots_hit   = 0
        self.dive_bombers = []
        self.galaga_divers = []
        self.galaga_kill_counter = 0
        # Faster divers past wave 50
        if self.wave > 50:
            self.dive_timer = random.uniform(6.0, 12.0)
        else:
            self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
        self.wave_kills   = 0
        self.last_stand_active = False
        self.pressure_pulse_timer  = PRESSURE_PULSE_INTERVAL
        self.pressure_pulse_active = 0.0
        self.wave_start_time = pygame.time.get_ticks() / 1000.0

        # Reset Harbinger state
        self.harbingers = []
        self.homing_missiles = []
        self.reinforcement_sent = False
        self.wave_graze_count = 0

        # Reset solar flare for Sector IV
        sector_idx = min(len(SECTOR_DATA) - 1, (self.wave - 1) // 10)
        if sector_idx == 3:  # Sector IV
            self.solar_flare.reset()

        # Dual-fighter expires at end of wave
        if self.dual_fighter and self.wave != self.dual_fighter_wave:
            self.dual_fighter = False

        # ── Spawn Harbinger elites (non-boss waves 35+) ─────────────────
        if self.wave >= 35 and self.boss is None:
            self._spawn_harbingers()

        # Detect active synergies
        self._update_synergies()

        # Create movement pattern for this sector
        sector = min(len(SECTOR_DATA) - 1, (self.wave - 1) // 10)
        if self.aliens:
            self.movement_pattern = create_movement_pattern(
                sector, self.wave, self.aliens, self.current_alien_drop)
        else:
            self.movement_pattern = None

        if self.active_upgrades.get("regen", 0) > 0:
            for barrier in self.barriers:
                barrier.regen_blocks()

    def _spawn_harbingers(self) -> None:
        """Spawn Harbinger elite enemies based on wave number."""
        w = self.wave
        spawns: list[type] = []

        if w >= 65:
            spawns = [Sentinel, Sentinel, Wraith, Leviathan, Leviathan, Archon]
        elif w >= 55:
            spawns = [Sentinel, Wraith, Leviathan, Leviathan, Archon]
        elif w >= 50:
            spawns = [Sentinel, Wraith, Leviathan, Archon]
        elif w >= 45:
            spawns = [Sentinel, Sentinel, Wraith, Leviathan]
        elif w >= 40:
            spawns = [Sentinel, Wraith]
        elif w >= 35:
            spawns = [Sentinel]

        for i, cls in enumerate(spawns):
            x = 100 + (WIDTH - 200) * (i + 1) / (len(spawns) + 1)
            y = 60 + random.uniform(-10, 10)
            self.harbingers.append(cls(x, y))

    def _start_bonus_round(self) -> None:
        """Start a Galaga-style bonus round."""
        self.bonus_round_active = True
        self.bonus_round_killed = 0
        self.bonus_round_timer = BONUS_ROUND_DURATION
        self.bonus_round_enemies = []

        # Create enemies on choreographed paths
        for i in range(BONUS_ROUND_ENEMIES):
            delay = i * 0.10
            pattern = i % 4
            path: list[tuple[float, float]] = []
            cx = WIDTH // 2
            cy = HEIGHT // 2

            if pattern == 0:
                # Figure-8
                for t_step in range(20):
                    t = t_step / 19
                    px = cx + 300 * math.sin(2 * math.pi * t)
                    py = 100 + 250 * math.sin(4 * math.pi * t)
                    path.append((px, py))
            elif pattern == 1:
                # Spiral in from left
                for t_step in range(20):
                    t = t_step / 19
                    px = -40 + (WIDTH + 80) * t
                    py = 200 + 150 * math.sin(3 * math.pi * t)
                    path.append((px, py))
            elif pattern == 2:
                # Diamond sweep
                path = [(-40, 200), (cx, 80), (WIDTH + 40, 200),
                        (cx, HEIGHT - 150), (-40, 200)]
            else:
                # Spiral in from right
                for t_step in range(20):
                    t = t_step / 19
                    px = WIDTH + 40 - (WIDTH + 80) * t
                    py = 150 + 200 * math.sin(2.5 * math.pi * t)
                    path.append((px, py))

            self.bonus_round_enemies.append(BonusEnemy(path, speed=250, delay=delay))

        self.banners.append(AchievementBanner("BONUS ROUND!", self.font_sm))
        self.enemy_bullets = []

    def _update_synergies(self) -> None:
        """Check active upgrades and power-ups for synergy combos."""
        self.active_synergies.clear()
        for syn in SYNERGY_DEFINITIONS:
            reqs = syn["reqs"]
            all_met = True
            for req in reqs:
                # Check both permanent upgrades and temporary power-ups
                if req not in self.active_upgrades and req not in self.active_powerups:
                    all_met = False
                    break
            if all_met:
                self.active_synergies.add(syn["id"])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _add_shake(self, intensity: int, duration: float) -> None:
        self.shake_intensity = intensity
        self.shake_timer     = duration

    def _try_achievement(self, name: str) -> None:
        if name not in self.achv_data.get("earned", []):
            if save_achievement(name):
                self.achv_data = load_achievements()
                self.banners.append(AchievementBanner(name, self.font_sm))
                self.sfx.play("achieve")

    def _spawn_explosion(self, x: float, y: float,
                         colour: tuple[int, int, int], count: int = 14) -> None:
        for _ in range(count):
            self.particles.append(Particle(x, y, colour,
                                           speed=random.uniform(120, 350),
                                           size=random.uniform(3, 7),
                                           life=random.uniform(0.3, 0.7)))
        for _ in range(count // 3):
            self.particles.append(Particle(x, y, WHITE,
                                           speed=random.uniform(180, 400),
                                           size=random.uniform(1, 3),
                                           life=random.uniform(0.15, 0.35)))

    def _trigger_bomb(self) -> None:
        pts = len(self.aliens) * 8

        if self.aliens:
            max_y = max(a.y for a in self.aliens)
            self.aliens = [a for a in self.aliens if a.y < max_y - 30]

            for _ in range(20):
                self.particles.append(Particle(
                    random.uniform(100, WIDTH - 100),
                    max_y,
                    random.choice([ORANGE, YELLOW, HOT_PINK]),
                    speed=random.uniform(60, 160),
                    angle=random.uniform(math.pi * 1.1, math.pi * 1.9),
                    size=random.randint(3, 6),
                    life=random.uniform(0.4, 0.8)
                ))

        for diver in self.dive_bombers:
            self._spawn_explosion(diver.x, diver.y, diver.colour, count=8)
        self.dive_bombers  = []
        self.enemy_bullets = []
        self.score += pts
        self._check_life_milestones()
        self._add_shake(6, 0.3)
        self.sfx.play("bomb")
        self.bomb_flash_timer = 0.18
        self._try_achievement("Nuclear Option")

    def _trigger_emp(self) -> None:
        """EMP pulse: stuns regular aliens, disables Harbinger shields/abilities."""
        # Stun all regular aliens for 1.5s (freeze movement)
        self.bomb_flash_timer = 0.25
        self._add_shake(4, 0.2)
        # Disable Harbinger shields for 3s
        for harb in self.harbingers:
            if isinstance(harb, Sentinel):
                harb.spawn_timer = 3.0  # repurpose as stun timer
            elif isinstance(harb, Wraith):
                harb.invuln_timer = 0  # break invulnerability
                harb.teleport_timer = 3.0  # delay next teleport
        # Kill all homing missiles
        for m in self.homing_missiles:
            self._spawn_explosion(m.x, m.y, CYAN, count=3)
            m.alive = False
        self.homing_missiles = []
        # Clear enemy bullets
        self.enemy_bullets = []
        self.banners.append(AchievementBanner("EMP!", self.font_sm))
        self.sfx.play("bomb")

    def _trigger_game_over(self) -> None:
        """Transition to game over state."""
        self.state = GameState.GAME_OVER
        self.sfx.music_channel.stop()

    def _check_life_milestones(self) -> None:
        while (self.next_life_milestone_idx < len(EXTRA_LIFE_MILESTONES) and
               self.score >= EXTRA_LIFE_MILESTONES[self.next_life_milestone_idx]):
            self.lives += 1
            self.next_life_milestone_idx += 1
            self.sfx.play("extra_life")
            self.banners.append(AchievementBanner("EXTRA LIFE!", self.font_sm))
            self.combo_popups.append(ComboPopup(
                WIDTH // 2, HEIGHT // 2, 0, self.font_med, text="+1 LIFE!"
            ))

    def _has_powerup(self, kind: str) -> bool:
        return self.active_powerups.get(kind, 0) > 0

    def _has_upgrade(self, uid: str) -> bool:
        return self.active_upgrades.get(uid, 0) > 0

    def _frenzy_kill(self) -> None:
        self.frenzy_streak += 1
        new_tier = 0
        for i, td in enumerate(FRENZY_TIERS):
            if self.frenzy_streak >= td["threshold"]:
                new_tier = i + 1
        if new_tier > self.frenzy_tier:
            self.frenzy_tier         = new_tier
            self.frenzy_banner_timer = FRENZY_BANNER_DURATION
            self.frenzy_banner_tier  = new_tier
            self._add_shake(5, 0.2)

        if self.frenzy_tier == 3:
            self.frenzy_beyond_kills += 1
            new_beyond = self.frenzy_beyond_kills // 15
            if new_beyond > self.frenzy_beyond_level:
                self.frenzy_beyond_level = new_beyond
                self._add_shake(3, 0.15)
                self.sfx.play("achieve")

    def _apply_upgrade(self, upgrade_id: str) -> None:
        if upgrade_id == "extralife":
            self.lives = min(self.lives + 1, 5)
            return
        current = self.active_upgrades.get(upgrade_id, 0)
        self.active_upgrades[upgrade_id] = current + UPGRADE_DURATION_WAVES

    def _fire_burst(self, base_x: float, base_y: float,
                    pierce_remaining: int) -> None:
        for offset_y in (0, -14, -28):
            self.bullets.append(Bullet(
                x=float(base_x), y=float(base_y + offset_y),
                vx=0.0, vy=-BULLET_SPEED,
                colour=HOT_PINK,
                pierce_remaining=pierce_remaining,
            ))

    def _apply_konami_cheats(self) -> None:
        """Apply Konami Code cheat mode: 30 lives + all upgrades."""
        self.lives = 30
        self.konami_active = True
        for upg in UPGRADE_POOL:
            if upg["id"] != "extralife":
                self.active_upgrades[upg["id"]] = 999
        self.banners.append(AchievementBanner(
            "CHEATER! 30 LIVES + ALL UPGRADES", self.font_sm))
        self.sfx.play("achieve")

    def _spawn_ship_fragments(self) -> None:
        """Shatter the player ship into spinning triangular fragments."""
        cx, cy = self.player_x, self.player_y
        col    = self._get_ship_colour()
        # Five shards matching the rough topology of the ship polygon
        shard_data = [
            ( 0.0, -1.0,  1.0),   # nose — flies upward
            (-1.0,  0.3,  0.85),  # left wing
            ( 1.0,  0.3,  0.85),  # right wing
            (-0.35, 0.65, 0.65),  # left body piece
            ( 0.35, 0.65, 0.65),  # right body piece
        ]
        for dx, dy, sz in shard_data:
            spd = random.uniform(160, 320)
            self.ship_fragments.append(ShipFragment(
                cx, cy,
                dx * spd + random.uniform(-40, 40),
                dy * spd + random.uniform(-40, 40),
                col,
                angle=random.uniform(0, math.tau),
                rot_speed=random.uniform(-8, 8),
                size=sz,
            ))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick_busy_loop(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self._handle_keydown(event)

            star_speed_mult = 1.0 + 0.5 * self.frenzy_tier
            for star in self.stars:
                star.update(dt * star_speed_mult)

            if self.state == GameState.TITLE:
                self._update_title(dt)
            elif self.state == GameState.PLAYING:
                self._update_playing(dt)
            elif self.state == GameState.PAUSED:
                pass
            elif self.state == GameState.GAME_OVER:
                self._update_gameover(dt)
            elif self.state == GameState.WAVE_SUMMARY:
                self._update_wave_summary(dt)
            elif self.state == GameState.UPGRADE_PICK:
                self._update_upgrade_pick(dt)

            self._draw()

        pygame.quit()
        sys.exit()

    # ── Input ─────────────────────────────────────────────────────────────────

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        # ── Konami code detector (any state) ──────────────────────────────────
        self.konami_buffer.append(event.key)
        if len(self.konami_buffer) > len(self._konami_seq):
            self.konami_buffer.pop(0)
        if self.konami_buffer == self._konami_seq:
            self.konami_pending = True
            self.sfx.play("achieve")
            self.banners.append(
                AchievementBanner("KONAMI CODE! Cheat mode ready...", self.font_sm))

        if event.key == pygame.K_c and self.state != GameState.GAME_OVER:
            self.crt_enabled = not self.crt_enabled
            return

        if self.state == GameState.TITLE:
            if event.key == pygame.K_RETURN:
                self._init_game()
                if self.konami_pending:
                    self._apply_konami_cheats()
                    self.konami_pending = False
                self.state = GameState.PLAYING
                self.sfx.music_channel.play(self.sfx.music_for_tier(0), loops=-1)
            elif event.key == pygame.K_LEFT:
                idx = (self.unlocked_ships.index(self.selected_ship)
                       if self.selected_ship in self.unlocked_ships else 0)
                self.selected_ship = self.unlocked_ships[(idx - 1) % len(self.unlocked_ships)]
            elif event.key == pygame.K_RIGHT:
                idx = (self.unlocked_ships.index(self.selected_ship)
                       if self.selected_ship in self.unlocked_ships else 0)
                self.selected_ship = self.unlocked_ships[(idx + 1) % len(self.unlocked_ships)]
            elif event.key == pygame.K_UP:
                idx = DIFFICULTIES.index(self.difficulty)
                self.difficulty = DIFFICULTIES[(idx - 1) % len(DIFFICULTIES)]
            elif event.key == pygame.K_DOWN:
                idx = DIFFICULTIES.index(self.difficulty)
                self.difficulty = DIFFICULTIES[(idx + 1) % len(DIFFICULTIES)]

        elif self.state == GameState.PLAYING:
            if event.key == pygame.K_p:
                self.state = GameState.PAUSED
                self.sfx.music_channel.pause()
                if self.sfx.ufo_channel.get_busy():
                    self.sfx.ufo_channel.pause()

        elif self.state == GameState.PAUSED:
            if event.key in (pygame.K_p, pygame.K_RETURN):
                self.state = GameState.PLAYING
                self.sfx.music_channel.unpause()
                if self.ufo and self.ufo.alive:
                    self.sfx.ufo_channel.unpause()

        elif self.state == GameState.WAVE_SUMMARY:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.wave_summary_timer = 0.0

        elif self.state == GameState.UPGRADE_PICK:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.upgrade_cursor = (self.upgrade_cursor - 1) % 3
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.upgrade_cursor = (self.upgrade_cursor + 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                chosen = self.upgrade_choices[self.upgrade_cursor]
                self._apply_upgrade(chosen["id"])
                self.wave_summary_timer = 3.5
                self._spawn_wave()
                self.state = GameState.WAVE_SUMMARY

        elif self.state == GameState.GAME_OVER:
            if self.entering_name:
                if event.key == pygame.K_UP:
                    c = ord(self.name_chars[self.name_cursor])
                    self.name_chars[self.name_cursor] = chr(c + 1 if c < ord("Z") else ord("A"))
                elif event.key == pygame.K_DOWN:
                    c = ord(self.name_chars[self.name_cursor])
                    self.name_chars[self.name_cursor] = chr(c - 1 if c > ord("A") else ord("Z"))
                elif event.key == pygame.K_RIGHT:
                    self.name_cursor = min(2, self.name_cursor + 1)
                elif event.key == pygame.K_LEFT:
                    self.name_cursor = max(0, self.name_cursor - 1)
                elif pygame.K_a <= event.key <= pygame.K_z:
                    letter = chr(event.key - pygame.K_a + ord("A"))
                    self.name_chars[self.name_cursor] = letter
                    self.name_cursor = min(2, self.name_cursor + 1)
                elif event.key == pygame.K_BACKSPACE and self.name_cursor > 0:
                    self.name_cursor -= 1
                elif event.key == pygame.K_RETURN:
                    name = "".join(self.name_chars)
                    self.hs_data = save_highscore(name, self.pending_score)
                    self._unlock_ships()
                    self.entering_name = False
            else:
                if event.key == pygame.K_c and self.continue_available and not self.continue_used:
                    self.continue_used = True
                    self.lives = 1
                    self.wave  = max(1, int(self.wave * CONTINUE_WAVE_PENALTY))
                    self.state = GameState.PLAYING
                    self._spawn_wave()
                    self.sfx.music_channel.play(self.sfx.music_for_tier(self.frenzy_tier), loops=-1)
                elif event.key == pygame.K_r:
                    self.state = GameState.TITLE

    # ── Title ─────────────────────────────────────────────────────────────────

    def _update_title(self, dt: float) -> None:
        self.title_pulse += dt * 3
        self.particles = [p for p in self.particles if p.update(dt)]

    # ── Wave Summary ──────────────────────────────────────────────────────────

    def _update_wave_summary(self, dt: float) -> None:
        self.wave_summary_timer -= dt
        self.wave_clear_flash = max(0.0, self.wave_clear_flash - dt * 2.0)
        # Keep sector lerp and transition banner ticking during summary screen
        for i in range(3):
            diff = self.sector_bg_target[i] - self.sector_bg[i]
            self.sector_bg[i] += diff * min(1.0, SECTOR_BG_LERP_SPEED * dt)
        if self.sector_transition_timer > 0:
            self.sector_transition_timer -= dt
        self.particles    = [p for p in self.particles if p.update(dt)]
        self.combo_popups = [c for c in self.combo_popups if c.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

        if self.wave_summary_timer <= 0:
            self._spawn_wave()
            self.state = GameState.PLAYING
            self.sfx.music_channel.unpause()

    # ── Upgrade pick ──────────────────────────────────────────────────────────

    def _update_upgrade_pick(self, dt: float) -> None:
        self.particles    = [p for p in self.particles if p.update(dt)]
        self.combo_popups = [c for c in self.combo_popups if c.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

    # ── Playing ───────────────────────────────────────────────────────────────

    def _update_playing(self, dt: float) -> None:
        if self.bomb_flash_timer > 0:
            self.bomb_flash_timer -= dt

        self.wave_clear_flash = max(0.0, self.wave_clear_flash - dt * 2.0)

        # Sector background colour lerp (exponential approach toward target)
        for i in range(3):
            diff = self.sector_bg_target[i] - self.sector_bg[i]
            self.sector_bg[i] += diff * min(1.0, SECTOR_BG_LERP_SPEED * dt)

        # Boss title card countdown
        if self.boss_title_timer > 0:
            self.boss_title_timer -= dt

        # Sector transition banner countdown
        if self.sector_transition_timer > 0:
            self.sector_transition_timer -= dt

        # Low-life heartbeat
        if self.lives == 1:
            self._low_life_timer -= dt
            if self._low_life_timer <= 0:
                self.sfx.play("player_hit")
                self._low_life_timer = 1.4
        else:
            self._low_life_timer = 0.0

        # Adaptive music — swap track when frenzy tier changes
        if self.frenzy_tier != self._music_tier:
            self._music_tier = self.frenzy_tier
            self.sfx.music_channel.stop()
            self.sfx.music_channel.play(self.sfx.music_for_tier(self.frenzy_tier), loops=-1)

        keys = pygame.key.get_pressed()

        # ── Player movement ───────────────────────────────────────────────
        speed_mult = 1.25 if self._has_upgrade("speed") else 1.0
        dx = 0.0
        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED * speed_mult * dt
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED * speed_mult * dt
            moving = True
        self.player_x = max(35, min(WIDTH - 35, self.player_x + dx))

        if moving:
            self.particles.append(Particle(
                self.player_x + random.uniform(-6, 6),
                self.player_y + 18,
                (0, 150, 255),
                speed=random.uniform(40, 80),
                angle=random.uniform(math.pi * 0.35, math.pi * 0.65),
                size=random.randint(2, 4),
                life=random.uniform(0.15, 0.35),
            ))

        # ── Player shooting ───────────────────────────────────────────────
        has_rapid  = self._has_powerup("rapid")
        has_spread = self._has_powerup("spread")
        has_burst  = self._has_upgrade("burst")
        pierce_lvl = 2 if self._has_upgrade("pierce") else 0

        frenzy_mult = (FRENZY_TIERS[self.frenzy_tier - 1]["fire_mult"]
                       if self.frenzy_tier > 0 else 1.0)
        if self.frenzy_tier == 3 and self.frenzy_beyond_level > 0:
            frenzy_mult = frenzy_mult * (0.95 ** self.frenzy_beyond_level)
            frenzy_mult = max(0.15, frenzy_mult)
        bullet_col = (FRENZY_TIERS[self.frenzy_tier - 1]["colour"]
                      if self.frenzy_tier > 0 else YELLOW)

        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            base_cd = RAPID_SHOOT_COOLDOWN if has_rapid else BASE_SHOOT_COOLDOWN
            self.shoot_cooldown = base_cd * frenzy_mult
            self.sfx.play("pew")
            self.shots_fired += 1
            by = self.player_y - 40

            if has_spread:
                for angle in (-0.15, 0.0, 0.15):
                    vx_ = math.sin(angle) * BULLET_SPEED
                    vy_ = -math.cos(angle) * BULLET_SPEED
                    self.bullets.append(Bullet(
                        x=float(self.player_x), y=float(by),
                        vx=vx_, vy=vy_,
                        colour=bullet_col,
                        pierce_remaining=pierce_lvl,
                    ))
            else:
                self.bullets.append(Bullet(
                    x=float(self.player_x), y=float(by),
                    vx=0.0, vy=-BULLET_SPEED,
                    colour=bullet_col,
                    pierce_remaining=pierce_lvl,
                ))

            # ── Dual-fighter second shot ──────────────────────────────
            if self.dual_fighter:
                self.bullets.append(Bullet(
                    x=float(self.player_x + 20), y=float(by),
                    vx=0.0, vy=-BULLET_SPEED,
                    colour=bullet_col,
                    pierce_remaining=pierce_lvl,
                ))

            if has_burst:
                self.burst_shot_count += 1
                if self.burst_shot_count % 3 == 0:
                    self._fire_burst(self.player_x, by, pierce_lvl)

            for _ in range(3):
                self.particles.append(Particle(
                    self.player_x + random.uniform(-6, 6),
                    self.player_y - 42,
                    YELLOW,
                    speed=random.uniform(50, 120),
                    angle=random.uniform(-0.5, 0.5) - math.pi / 2,
                    size=3, life=0.2,
                ))

        # ── Move player bullets ───────────────────────────────────────────
        homing_active = "homing" in self.active_powerups
        if homing_active and self.aliens:
            _alien_positions = [(a.x, a.y, a) for a in self.aliens]
        else:
            _alien_positions = []
        alive_bullets: list[Bullet] = []
        for b in self.bullets:
            # Homing: curve toward nearest enemy
            if homing_active and _alien_positions:
                best_dist_sq = float('inf')
                nearest = _alien_positions[0][2]
                for ax, ay, alien_obj in _alien_positions:
                    dx = ax - b.x
                    dy = ay - b.y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < best_dist_sq:
                        best_dist_sq = dist_sq
                        nearest = alien_obj
                desired = math.atan2(nearest.y - b.y, nearest.x - b.x)
                current = math.atan2(b.vy, b.vx)
                diff_a = (desired - current + math.pi) % (2 * math.pi) - math.pi
                steer = max(-HOMING_BULLET_TRACKING * dt,
                            min(HOMING_BULLET_TRACKING * dt, diff_a))
                spd = math.hypot(b.vx, b.vy)
                new_a = current + steer
                b.vx = math.cos(new_a) * spd
                b.vy = math.sin(new_a) * spd
            b.x += b.vx * dt
            b.y += b.vy * dt
            if b.frag_life > 0:
                b.frag_life -= dt
                if b.frag_life <= 0:
                    continue
            if 0 < b.y < HEIGHT and 0 < b.x < WIDTH:
                alive_bullets.append(b)
        self.bullets = alive_bullets

        # ── Player bullets vs barriers ────────────────────────────────────
        barrier_blocked: set[int] = set()
        for bi, b in enumerate(self.bullets):
            for barrier in self.barriers:
                if barrier.check_bullet_hit(b.x, b.y):
                    barrier_blocked.add(bi)
                    if barrier.last_destroyed:
                        dx2, dy2 = barrier.last_destroyed
                        for _ in range(5):
                            self.particles.append(Particle(
                                dx2, dy2, LIME,
                                speed=random.uniform(50, 140),
                                size=random.uniform(2, 4),
                                life=random.uniform(0.2, 0.4),
                            ))
                    break
        if barrier_blocked:
            self.bullets = [b for i, b in enumerate(self.bullets)
                            if i not in barrier_blocked]

        # ── Wingman drone ─────────────────────────────────────────────────
        self.drone_active = self._has_upgrade("drone")
        if self.drone_active:
            self.drone_angle += DRONE_ORBIT_SPEED * dt
            drone_fm = (FRENZY_TIERS[self.frenzy_tier - 1]["fire_mult"]
                        if self.frenzy_tier > 0 else 1.0)
            drone_cooldown = DRONE_FIRE_COOLDOWN * drone_fm
            self.drone_fire_timer -= dt
            if self.drone_fire_timer <= 0 and (self.aliens or self.boss):
                self.drone_fire_timer = drone_cooldown
                drone_x = self.player_x + math.cos(self.drone_angle) * DRONE_ORBIT_RADIUS
                drone_y = self.player_y + math.sin(self.drone_angle) * DRONE_ORBIT_RADIUS
                self.bullets.append(Bullet(
                    x=float(drone_x), y=float(drone_y),
                    vx=0.0, vy=-BULLET_SPEED,
                    colour=CYAN, is_drone=True,
                ))
                self.sfx.play("pew")

        # ── Alien animation ───────────────────────────────────────────────
        total_aliens_this_wave = ALIEN_COLS * min(
            ALIEN_ROWS_MAX, ALIEN_ROWS + (self.wave - 1) // 8)
        if self.aliens:
            anim_threshold = max(
                0.08, 0.5 * (len(self.aliens) / max(1, total_aliens_this_wave)))
        else:
            anim_threshold = 0.15
        self.alien_anim_timer += dt
        if self.alien_anim_timer > anim_threshold:
            self.alien_anim_timer -= anim_threshold
            self.alien_frame = 1 - self.alien_frame

        # ── Ship fragment update ──────────────────────────────────────────
        self.ship_fragments = [f for f in self.ship_fragments if f.update(dt)]

        # ── Pressure pulse ────────────────────────────────────────────────
        entering = self.movement_pattern and self.movement_pattern.is_entering()
        if (self.aliens and not entering
                and self.boss is None
                and not getattr(self, 'last_stand_active', False)):
            self.pressure_pulse_timer -= dt
            if self.pressure_pulse_timer <= 0:
                self.pressure_pulse_timer = PRESSURE_PULSE_INTERVAL
                for a in self.aliens:
                    a.base_y = min(a.base_y + PRESSURE_PULSE_DROP, BARRIER_Y - 100)
                self.pressure_pulse_active = PRESSURE_PULSE_DURATION
                self._add_shake(8, 0.3)
                self.bomb_flash_timer = 0.4
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 80, 0, self.font_lv,
                    text="PRESSURE!"))
        if self.pressure_pulse_active > 0:
            self.pressure_pulse_active -= dt
            # Apply boost against the BASE interval, not the current one
            # so the rate restores correctly once the pulse expires
            self.enemy_shoot_interval = max(
                0.35,
                self._base_shoot_interval / PRESSURE_PULSE_BOOST,
            )
        else:
            # Restore to base interval when pulse not active
            self.enemy_shoot_interval = self._base_shoot_interval

        # ── Time Warp slow-down ───────────────────────────────────────────
        time_warp = "timewarp" in self.active_powerups
        enemy_dt = dt * 0.5 if time_warp else dt

        # ── Move aliens ───────────────────────────────────────────────────
        if self.aliens and self.movement_pattern:
            if self.last_stand_active:
                for a in self.aliens:
                    a.x += a.scatter_vx * enemy_dt
                    a.y += a.scatter_vy * enemy_dt
                    a.base_x, a.base_y = a.x, a.y
                    if a.x < 40:
                        a.x = 40
                        a.scatter_vx = abs(a.scatter_vx)
                    elif a.x > WIDTH - 40:
                        a.x = WIDTH - 40
                        a.scatter_vx = -abs(a.scatter_vx)
                    if a.y < 60:
                        a.y = 60
                        a.scatter_vy = abs(a.scatter_vy)
                    elif a.y > BARRIER_Y - 100:
                        # Bounce off bottom so scattered aliens don't
                        # silently pass through the player zone / barriers
                        a.y = BARRIER_Y - 100
                        a.scatter_vy = -abs(a.scatter_vy)
            else:
                last_alien_mode = (len(self.aliens) == 1
                                   and not self.boss and not self.dive_bombers)
                self.alien_dir, self.alien_speed = self.movement_pattern.update(
                    self.aliens, enemy_dt, self.alien_speed, self.alien_dir,
                    last_alien_mode)
            for a in self.aliens:
                if a.hit_flash > 0:
                    a.hit_flash = max(0.0, a.hit_flash - dt)
                # Hard ceiling: aliens must never descend into the barrier zone
                a.base_y = min(a.base_y, BARRIER_Y - 100)
                a.y      = min(a.y,      BARRIER_Y - 100)

        # ── Cull aliens that fell off the bottom of the screen ────────────
        # Safety net: silently remove any alien that exits the play area.
        # No player penalty — the movement-pattern bug (B-1) that caused this
        # has been fixed; this guard remains as a defensive measure only.
        if self.aliens:
            self.aliens = [a for a in self.aliens if a.y <= HEIGHT + 30]

        # ── Enemy shooting (bottom-row only) ──────────────────────────────
        if self.aliens:
            self.enemy_shoot_timer -= dt
            if self.enemy_shoot_timer <= 0:
                landed = [a for a in self.aliens if a.entry_progress >= 1.0]
                if isinstance(self.movement_pattern, OrbitalRing):
                    # Orbital: any of the bottom-half aliens can shoot
                    if landed:
                        mid_y = sum(a.y for a in landed) / len(landed)
                        shooters = [a for a in landed if a.y >= mid_y]
                        shooter = random.choice(shooters) if shooters else random.choice(landed)
                    else:
                        shooter = None
                elif isinstance(self.movement_pattern, SerpentChain):
                    # Serpent: the chain segment currently lowest on screen shoots
                    shooter = max(landed, key=lambda a: a.y) if landed else None
                else:
                    col_bottoms: dict[int, Alien] = {}
                    for a in landed:
                        col_key = a.grid_col
                        if col_key not in col_bottoms or a.y > col_bottoms[col_key].y:
                            col_bottoms[col_key] = a
                    shooter = random.choice(list(col_bottoms.values())) if col_bottoms else None
                if shooter:
                    aim     = min(0.35, max(0.0, (self.wave - 10) * 0.018))
                    raw_dx  = self.player_x - shooter.x
                    dist    = max(1.0, abs(raw_dx))
                    vx_eb   = (raw_dx / dist) * self.enemy_bullet_speed * aim
                    self.enemy_bullets.append(EnemyBullet(
                        x=shooter.x, y=shooter.y + 20,
                        vx=vx_eb, vy=self.enemy_bullet_speed,
                    ))
                    self.sfx.play("enemy_shoot")
                self.enemy_shoot_timer = (self.enemy_shoot_interval
                                          + random.uniform(-0.3, 0.3))

        # ── Boss update & shooting ────────────────────────────────────────
        if self.boss and self.boss.alive:
            if not isinstance(self.boss, Colossus):
                self.boss.update(dt)
            # Phantom decoys on phase 2
            if (isinstance(self.boss, Phantom) and self.boss.is_phase2()
                    and not self.boss.decoys_spawned):
                self.boss.decoys_spawned = True
                for dx_off in (-120, 120):
                    self.aliens.append(Alien(
                        x=self.boss.x + dx_off, y=self.boss.y,
                        colour=(200, 80, 255), hp=1, sprite_tier=0,
                        grid_col=0, grid_row=0,
                        base_x=self.boss.x + dx_off, base_y=self.boss.y,
                    ))
                self.banners.append(AchievementBanner("DECOYS!", self.font_sm))
            if self.boss.should_shoot():
                if self.boss.is_phase2():
                    for spread_angle in (-0.22, 0.0, 0.22):
                        raw_dx = self.player_x - self.boss.x
                        raw_dy = self.player_y - self.boss.y
                        dist   = max(1.0, math.sqrt(raw_dx**2 + raw_dy**2))
                        spd    = self.enemy_bullet_speed * 1.1
                        bvx    = (raw_dx / dist) * spd
                        bvy    = (raw_dy / dist) * spd
                        ca, sa = math.cos(spread_angle), math.sin(spread_angle)
                        self.enemy_bullets.append(EnemyBullet(
                            x=self.boss.x, y=self.boss.y + 35,
                            vx=bvx * ca - bvy * sa,
                            vy=bvx * sa + bvy * ca,
                        ))
                else:
                    raw_dx = self.player_x - self.boss.x
                    raw_dy = self.player_y - self.boss.y
                    dist   = max(1.0, math.sqrt(raw_dx**2 + raw_dy**2))
                    spd    = self.enemy_bullet_speed * 1.2
                    self.enemy_bullets.append(EnemyBullet(
                        x=self.boss.x, y=self.boss.y + 35,
                        vx=(raw_dx / dist) * spd,
                        vy=(raw_dy / dist) * spd,
                    ))
                self.sfx.play("enemy_shoot")

        # ── Colossus turret shooting (handled by boss.update) ────────────
        if self.boss and self.boss.alive and isinstance(self.boss, Colossus):
            colossus_bullets = self.boss.update(dt, self.player_x, self.player_y)
            for cb in colossus_bullets:
                self.enemy_bullets.append(cb)

        # ── Harbinger Elite update & shooting ────────────────────────────
        for harb in self.harbingers:
            if not harb.alive:
                continue
            if isinstance(harb, Sentinel):
                new_bullets = harb.update(dt, self.player_x)
                self.enemy_bullets.extend(new_bullets)
            elif isinstance(harb, Wraith):
                new_missiles = harb.update(dt, self.player_x, self.player_y)
                self.homing_missiles.extend(new_missiles)
            elif isinstance(harb, Leviathan):
                new_bullets = harb.update(dt)
                self.enemy_bullets.extend(new_bullets)
            elif isinstance(harb, Archon):
                new_bullets = harb.update(dt, self.player_x, self.player_y)
                self.enemy_bullets.extend(new_bullets)
                # Check capture completion
                if harb.is_capturing() and not harb.has_captured:
                    harb.has_captured = True
                    self.lives -= 1
                    self._add_shake(8, 0.4)
                    self.sfx.play("player_hit")
                    if self.lives <= 0:
                        self._trigger_game_over()
                        return

        self.harbingers = [h for h in self.harbingers if h.alive]

        # ── Update homing missiles ───────────────────────────────────────
        for m in self.homing_missiles:
            m.update(dt, self.player_x, self.player_y)
        self.homing_missiles = [m for m in self.homing_missiles if m.alive]

        # ── Solar flare update (Sector IV only) ──────────────────────────
        sector_idx = min(len(SECTOR_DATA) - 1, (self.wave - 1) // 10)
        if sector_idx == 3:
            self.solar_flare.update(dt)
            # Check if flare hits player
            if self.solar_flare.is_hitting(self.player_x, self.player_y):
                self._player_hit()
            # Check if flare hits aliens
            if self.solar_flare.state == SolarFlare.STATE_ACTIVE:
                for a in self.aliens:
                    if self.solar_flare.is_hitting(a.x, a.y, 12):
                        a.hp = 0
                # Remove dead aliens from flare
                flare_killed = [a for a in self.aliens if a.hp <= 0]
                for a in flare_killed:
                    self._spawn_explosion(a.x, a.y, ORANGE, count=6)
                    self.score += 10
                self.aliens = [a for a in self.aliens if a.hp > 0]

        # ── Bonus round update ───────────────────────────────────────────
        if self.bonus_round_active:
            self.bonus_round_timer -= dt
            for be in self.bonus_round_enemies:
                be.update(dt)
            self.bonus_round_enemies = [be for be in self.bonus_round_enemies if be.alive]
            # Check if bonus round is over
            if self.bonus_round_timer <= 0 or not self.bonus_round_enemies:
                perfect = self.bonus_round_killed >= BONUS_ROUND_ENEMIES
                if perfect:
                    self.score += BONUS_ROUND_PERFECT
                    self.banners.append(AchievementBanner("PERFECT!", self.font_sm))
                    self.sfx.play("achieve")
                self.bonus_round_active = False
                self.bonus_round_enemies = []
                # Proceed to next wave
                self.wave += 1
                self.wave_summary_timer = 3.5
                self.state = GameState.WAVE_SUMMARY
                return

        # ── Graze scoring ────────────────────────────────────────────────
        for eb in self.enemy_bullets:
            dx_g = eb.x - self.player_x
            dy_g = eb.y - self.player_y
            dist_g = math.hypot(dx_g, dy_g)
            if dist_g < GRAZE_DISTANCE and dist_g > GRAZE_INNER_DISTANCE:  # close but not a hit
                self.score += GRAZE_POINTS
                self.graze_count += 1
                self.wave_graze_count += 1
                # Spark particle
                self.particles.append(Particle(
                    self.player_x + dx_g * 0.5,
                    self.player_y + dy_g * 0.5,
                    WHITE, speed=80, size=2, life=0.15,
                ))

        # ── Reinforcement waves (wave 50+, every 3rd non-boss wave) ─────
        if (self.wave > 50 and not self.reinforcement_sent
                and self.wave % BOSS_WAVE_INTERVAL != 0
                and (self.wave - 51) % 3 == 0 and self.aliens):
            initial_count = (min(ALIEN_ROWS_MAX, ALIEN_ROWS + (self.wave - 1) // 8)
                             * ALIEN_COLS)
            if len(self.aliens) < initial_count * 0.5:
                self.reinforcement_sent = True
                alien_hp = min(3, 1 + (self.wave - 1) // 20)
                y_offset = min((self.wave - 1) * 8, 100)
                for row in range(3):
                    sprite_tier = min(2, row // 2)
                    for col in range(ALIEN_COLS):
                        ax = ALIEN_X_START + col * ALIEN_X_SPACING
                        ay = ALIEN_Y_START + row * ALIEN_Y_SPACING + y_offset - 40
                        colour = ALIEN_ROW_COLOURS[row % len(ALIEN_ROW_COLOURS)]
                        self.aliens.append(
                            Alien(x=ax, y=ay, colour=colour, hp=alien_hp,
                                  sprite_tier=sprite_tier,
                                  grid_col=col, grid_row=row,
                                  base_x=ax, base_y=ay))
                self.banners.append(AchievementBanner("REINFORCEMENTS!", self.font_sm))
                self._add_shake(4, 0.2)

        # ── Update synergies each frame ──────────────────────────────────
        self._update_synergies()

        # ── Move enemy bullets ────────────────────────────────────────────
        alive_eb: list[EnemyBullet] = []
        for eb in self.enemy_bullets:
            eb.x += eb.vx * dt
            eb.y += eb.vy * dt
            if 0 < eb.y < HEIGHT + 20 and 0 < eb.x < WIDTH + 50:
                alive_eb.append(eb)
        self.enemy_bullets = alive_eb

        # ── Enemy bullets vs barriers ─────────────────────────────────────
        enemy_barrier_blocked: set[int] = set()
        for ei, eb in enumerate(self.enemy_bullets):
            for barrier in self.barriers:
                if barrier.check_bullet_hit(eb.x, eb.y):
                    enemy_barrier_blocked.add(ei)
                    if barrier.last_destroyed:
                        dx2, dy2 = barrier.last_destroyed
                        for _ in range(4):
                            self.particles.append(Particle(
                                dx2, dy2, RED,
                                speed=random.uniform(40, 110),
                                size=random.uniform(2, 3),
                                life=random.uniform(0.15, 0.3),
                            ))
                    break
        if enemy_barrier_blocked:
            self.enemy_bullets = [eb for i, eb in enumerate(self.enemy_bullets)
                                   if i not in enemy_barrier_blocked]

        # ── Enemy bullets vs player ───────────────────────────────────────
        hit_indices: list[int] = []
        for ei, eb in enumerate(self.enemy_bullets):
            if abs(eb.x - self.player_x) < 28 and abs(eb.y - self.player_y) < 24:
                hit_indices.append(ei)
                self._spawn_explosion(self.player_x, self.player_y, RED, count=8)
                self._player_hit()
        for ei in sorted(hit_indices, reverse=True):
            if ei < len(self.enemy_bullets):
                self.enemy_bullets.pop(ei)

        # ── UFO spawn timer ───────────────────────────────────────────────
        if self.ufo is None:
            self.ufo_timer -= dt
            if self.ufo_timer <= 0:
                self.ufo = UFO()
                self.sfx.ufo_channel.play(self.sfx.ufo_beacon, loops=-1)
                self.ufo_timer = random.uniform(UFO_INTERVAL_MIN, UFO_INTERVAL_MAX)
        else:
            self.ufo.update(dt)
            if not self.ufo.alive:
                self.ufo = None
                self.sfx.ufo_channel.stop()
            else:
                ufo_hit_bi = -1
                for bi, b in enumerate(self.bullets):
                    if abs(b.x - self.ufo.x) < 48 and abs(b.y - self.ufo.y) < 22:
                        ufo_hit_bi = bi
                        break
                if ufo_hit_bi >= 0:
                    pts = self.ufo.score
                    self._spawn_explosion(self.ufo.x, self.ufo.y, RED, count=22)
                    self.combo_popups.append(ComboPopup(
                        self.ufo.x, self.ufo.y, 0, self.font_med,
                        text=f"+{pts}!",
                    ))
                    self.score += pts
                    self._check_life_milestones()
                    self._add_shake(5, 0.2)
                    self.sfx.play("ufo_hit")
                    self.sfx.ufo_channel.stop()
                    self.ufo.alive = False
                    self.ufo = None
                    self.bullets.pop(ufo_hit_bi)
                    self._try_achievement("UFO Hunter")

        # ── Dive bomber spawn (wave 2+) ───────────────────────────────────
        entering = self.movement_pattern and self.movement_pattern.is_entering()
        if self.wave >= 2 and self.aliens and not self.dive_bombers and not entering:
            self.dive_timer -= dt
            if self.dive_timer <= 0:
                idx   = random.randint(0, len(self.aliens) - 1)
                diver = DiveBomber(self.aliens[idx])
                self.aliens.pop(idx)
                self.dive_bombers.append(diver)
                self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
                self.sfx.play("dive")

        # ── Update dive bombers ───────────────────────────────────────────
        alive_divers: list[DiveBomber] = []
        for diver in self.dive_bombers:
            diver.update(dt, self.player_x)
            if diver.alive:
                alive_divers.append(diver)
            elif diver.returned:
                # Use current formation base_y rather than stale dive-capture
                # value, so the alien rejoins where the formation actually is.
                from si_movement import RollingPincer
                if isinstance(self.movement_pattern, RollingPincer) and self.aliens:
                    # Snap to median base_y of same-column aliens if possible
                    col_peers = [a for a in self.aliens if a.grid_col == diver.grid_col]
                    rejoined_base_y = (sum(a.base_y for a in col_peers) / len(col_peers)
                                       if col_peers else diver.base_y)
                else:
                    rejoined_base_y = diver.base_y
                # Clamp so a rejoining alien can never appear below the safe zone
                rejoined_base_y = min(rejoined_base_y, HEIGHT - 300)
                self.aliens.append(Alien(
                    x=diver.start_x, y=rejoined_base_y, colour=diver.colour,
                    hp=min(3, 1 + (self.wave - 1) // 10),
                    grid_col=diver.grid_col, grid_row=diver.grid_row,
                    base_x=diver.base_x, base_y=rejoined_base_y,
                ))
        self.dive_bombers = alive_divers

        for diver in self.dive_bombers:
            if abs(diver.x - self.player_x) < 36 and abs(diver.y - self.player_y) < 36:
                self._spawn_explosion(diver.x, diver.y, diver.colour, count=14)
                diver.alive = False
                self._player_hit()

        # ── Galaga divers update ───────────────────────────────────────────
        alive_galaga: list[GalagaDiver] = []
        for diver in self.galaga_divers:
            diver.update(dt)
            if diver.alive:
                alive_galaga.append(diver)
        self.galaga_divers = alive_galaga

        # ── Combo timer ───────────────────────────────────────────────────
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo_count      = 0
            self.combo_multiplier = 1

        # ── Player bullets vs aliens ──────────────────────────────────────
        bullets_hit:    set[int] = set()
        aliens_touched: set[int] = set()
        aliens_killed:  set[int] = set()
        frag_to_spawn:  list[tuple[float, float]] = []

        frag_lvl = 1 if self._has_upgrade("frag") else 0

        # ── Player bullets vs Galaga divers ───────────────────────────────
        for bi, b in enumerate(self.bullets):
            if bi in bullets_hit:
                continue
            for diver in self.galaga_divers:
                if not diver.alive:
                    continue
                if abs(b.x - diver.x) < 30 and abs(b.y - diver.y) < 28:
                    bullets_hit.add(bi)
                    diver.alive = False
                    self.score += 50
                    self._add_shake(4, 0.12)
                    self.sfx.play("explode")
                    for _ in range(20):
                        self.particles.append(Particle(
                            diver.x, diver.y,
                            random.choice([diver.colour, ORANGE, YELLOW]),
                            speed=random.uniform(100, 300),
                            size=random.uniform(2, 5), life=0.5,
                        ))
                    break

        # ── Galaga diver vs player collision ──────────────────────────────
        for diver in self.galaga_divers:
            if (diver.alive
                    and abs(diver.x - self.player_x) < 36
                    and abs(diver.y - self.player_y) < 36):
                self._spawn_explosion(diver.x, diver.y, diver.colour, count=14)
                diver.alive = False
                self._player_hit()

        for bi, b in enumerate(self.bullets):
            for ai, a in enumerate(self.aliens):
                if ai in aliens_touched:
                    continue
                if abs(b.x - a.x) < 28 and abs(b.y - a.y) < 24:
                    aliens_touched.add(ai)
                    dmg = 2 if "overcharge" in self.active_powerups else 1
                    a.hp -= dmg
                    self.shots_hit += 1

                    if b.pierce_remaining > 0:
                        b.pierce_remaining -= 1
                    else:
                        bullets_hit.add(bi)

                    if a.hp <= 0:
                        aliens_killed.add(ai)
                        if frag_lvl > 0 and not b.is_frag:
                            frag_to_spawn.append((a.x, a.y))
                    else:
                        a.hit_flash = 0.12
                        for _ in range(5):
                            self.particles.append(Particle(
                                a.x, a.y, WHITE,
                                speed=random.uniform(60, 140),
                                size=2, life=0.25,
                            ))

        aliens_to_remove: set[int] = set()  # set of id(alien)
        # Pre-collect alien objects BEFORE the loop.
        # The galaga trigger (and future hooks) can remove extra aliens
        # mid-loop, invalidating any remaining indices from aliens_killed.
        # Snapshotting by object reference makes every subsequent lookup safe.
        _killed_snapshot = [
            (ai, self.aliens[ai])
            for ai in sorted(aliens_killed, reverse=True)
            if ai < len(self.aliens)
        ]
        for ai, a in _killed_snapshot:
            if a not in self.aliens:
                continue  # already removed by a previous iteration's side-effect
            self.combo_count  += 1
            self.combo_timer   = COMBO_WINDOW
            self.combo_multiplier = min(5, 1 + self.combo_count // 2)
            pdist_a = math.hypot(a.x - self.player_x, a.y - self.player_y)
            prox = PROXIMITY_KILL_MULT if pdist_a < PROXIMITY_KILL_DISTANCE else 1
            pts = 10 * self.combo_multiplier * prox
            self.score += pts
            if prox > 1:
                self.combo_popups.append(ComboPopup(
                    int(a.x), int(a.y) - 20, 0, self.font_sm,
                    text="DANGER KILL!"))
            self._check_life_milestones()
            self.wave_kills += 1

            # ── Galaga pair dive trigger ──────────────────────────────────────
            self.galaga_kill_counter += 1
            entering_now = self.movement_pattern and self.movement_pattern.is_entering()
            galaga_threshold = 6 if self.wave > 50 else 8
            if (self.galaga_kill_counter % galaga_threshold == 0
                    and len(self.aliens) >= 4
                    and self.boss is None
                    and not self.galaga_divers
                    and not entering_now):
                max_row = max(al.grid_row for al in self.aliens)
                # Exclude 'a' (already being killed this frame) from candidates
                candidates = sorted(
                    [al for al in self.aliens if al.grid_row == max_row and al is not a],
                    key=lambda al: al.x
                )
                pair = candidates[:2] if len(candidates) >= 2 else candidates
                for k, target in enumerate(pair):
                    side = -1 if k == 0 else 1
                    self.galaga_divers.append(
                        GalagaDiver(target, self.player_x, self.player_y, side))
                    aliens_to_remove.add(id(target))
                self.sfx.play("dive")

            # ── Multi-kill callout ────────────────────────────────────────────
            if self.combo_count == 2:
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 120, 0, self.font_lv,
                    text="DOUBLE  KILL!"))
            elif self.combo_count == 3:
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 120, 0, self.font_lv,
                    text="TRIPLE  KILL!"))
            elif self.combo_count == 4:
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 120, 0, self.font_lv,
                    text="MASSACRE!"))

            if self.wave <= 10:
                death_count  = 6
                death_size_max = 4
                death_colours  = [a.colour, WHITE]
            elif self.wave <= 20:
                death_count  = 10
                death_size_max = 5
                death_colours  = [a.colour, WHITE, ORANGE]
            else:
                death_count  = 15
                death_size_max = 7
                death_colours  = [a.colour, ORANGE, RED, YELLOW, HOT_PINK]

            for _ in range(death_count):
                self.particles.append(Particle(
                    a.x, a.y, random.choice(death_colours),
                    speed=random.uniform(120, 350),
                    size=random.uniform(3, death_size_max),
                    life=random.uniform(0.3, 0.7),
                ))
            self._add_shake(3, 0.1)
            self.sfx.play("explode")
            if self.combo_multiplier > 1:
                self.combo_popups.append(
                    ComboPopup(a.x, a.y, self.combo_multiplier, self.font_med))
            if random.random() < self.powerup_drop_chance:
                pu_kind = WeightedPowerUp.weighted_random_type(self.wave)
                self.powerups.append(PowerUp(a.x, a.y, kind=pu_kind))
            aliens_to_remove.add(id(a))
            self._frenzy_kill()
            if self.combo_multiplier >= 5:
                self._try_achievement("Combo Star")

            # ── Last alien detection ──────────────────────────────────────────
            _eff_count = sum(1 for al in self.aliens if id(al) not in aliens_to_remove)
            if (_eff_count == 1 and not self.last_alien_announced
                    and not self.boss and not self.dive_bombers):
                self.last_alien_announced = True
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 60, 0, self.font_lv,
                    text="LAST  ONE!"))

            # ── Last-stand scatter trigger ────────────────────────────────────
            if (not self.last_stand_active
                    and not self.boss
                    and _eff_count > 0
                    and _eff_count <= max(1, 50 // 4)):
                self.last_stand_active = True
                for a in self.aliens:
                    angle = random.uniform(0, 2 * math.pi)
                    spd   = random.uniform(180, 320)
                    a.scatter_vx = math.cos(angle) * spd
                    a.scatter_vy = math.sin(angle) * spd
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 - 80, 0, self.font_lv,
                    text="SCATTER!"))

        # ── Deferred alien removal ────────────────────────────────────────
        if aliens_to_remove:
            mp = self.movement_pattern
            has_hook = mp and hasattr(mp, "on_alien_killed")
            if has_hook:
                # Remove one-by-one in reverse index order so indices stay
                # valid and the movement-pattern hook sees the correct state.
                for i in sorted(
                    [j for j, al in enumerate(self.aliens) if id(al) in aliens_to_remove],
                    reverse=True,
                ):
                    self.aliens.pop(i)
                    mp.on_alien_killed(i, self.aliens)
            else:
                self.aliens = [a for a in self.aliens if id(a) not in aliens_to_remove]

        for fx, fy in frag_to_spawn:
            for angle_deg in (-22, 22):
                rad = math.radians(angle_deg)
                spd = BULLET_SPEED * 0.85
                self.bullets.append(Bullet(
                    x=float(fx), y=float(fy),
                    vx=math.sin(rad) * spd,
                    vy=-math.cos(rad) * spd,
                    colour=ORANGE,
                    is_frag=True,
                    frag_life=0.55,
                ))

        # ── Player bullets vs dive bombers ────────────────────────────────
        for bi, b in enumerate(self.bullets):
            if bi in bullets_hit:
                continue
            for diver in self.dive_bombers:
                if not diver.alive:
                    continue
                if abs(b.x - diver.x) < 30 and abs(b.y - diver.y) < 28:
                    bullets_hit.add(bi)
                    diver.alive = False
                    for _ in range(30):
                        self.particles.append(Particle(
                            diver.x, diver.y,
                            random.choice([ORANGE, YELLOW, HOT_PINK, WHITE, RED]),
                            speed=random.uniform(40, 200),
                            size=random.randint(3, 7),
                            life=random.uniform(0.4, 1.0),
                        ))
                    self._add_shake(8, 0.4)
                    self.sfx.play("explode")
                    pts = 50 * self.combo_multiplier
                    self.score += pts
                    self._check_life_milestones()
                    self.combo_count  += 1
                    self.combo_timer   = COMBO_WINDOW
                    self.combo_multiplier = min(5, 1 + self.combo_count // 2)
                    self.wave_kills += 1
                    self._frenzy_kill()
                    break

        # ── Player bullets vs Harbingers ──────────────────────────────────
        for bi, b in enumerate(self.bullets):
            if bi in bullets_hit:
                continue
            for harb in self.harbingers:
                if not harb.alive:
                    continue
                dist_h = math.hypot(b.x - harb.x, b.y - harb.y)
                hit_radius = getattr(harb, "size", 20)
                if dist_h < hit_radius + 10:
                    # Sentinel: check shield block
                    if isinstance(harb, Sentinel) and harb.is_shot_blocked_by_shield(b.x, b.y):
                        bullets_hit.add(bi)
                        self.sfx.play("explode")
                        self.particles.append(Particle(
                            b.x, b.y, CYAN, speed=100, size=3, life=0.2))
                        break
                    self.shots_hit += 1
                    killed = harb.take_damage(1)
                    bullets_hit.add(bi)
                    self.sfx.play("explode")
                    # Proximity kill bonus
                    pdist = math.hypot(harb.x - self.player_x, harb.y - self.player_y)
                    prox_mult = PROXIMITY_KILL_MULT if pdist < PROXIMITY_KILL_DISTANCE else 1
                    if killed:
                        pts = harb.score * prox_mult
                        self.score += pts
                        self._check_life_milestones()
                        self._spawn_explosion(harb.x, harb.y, HOT_PINK, count=20)
                        self.combo_popups.append(ComboPopup(
                            int(harb.x), int(harb.y), 0, self.font_med,
                            text=f"+{pts}!"))
                        if pdist < PROXIMITY_KILL_DISTANCE:
                            self.combo_popups.append(ComboPopup(
                                int(harb.x), int(harb.y) - 20, 0, self.font_sm,
                                text="DANGER KILL!"))
                        # Archon: dual fighter reward
                        if isinstance(harb, Archon) and harb.has_captured:
                            self.dual_fighter = True
                            self.dual_fighter_wave = self.wave
                            self.banners.append(
                                AchievementBanner("DUAL FIGHTER!", self.font_sm))
                        # 50% power-up drop from Harbingers
                        if random.random() < 0.5:
                            pu_type = WeightedPowerUp.weighted_random_type(self.wave)
                            self.powerups.append(PowerUp(
                                int(harb.x), int(harb.y), kind=pu_type))
                    else:
                        self._add_shake(2, 0.08)
                    break

            # Leviathan segment collision (separate check)
            for harb in self.harbingers:
                if bi in bullets_hit:
                    break
                if not isinstance(harb, Leviathan) or not harb.alive:
                    continue
                for si, seg in enumerate(harb.segments):
                    if not seg.alive:
                        continue
                    if math.hypot(b.x - seg.x, b.y - seg.y) < seg.size + 8:
                        bullets_hit.add(bi)
                        self.shots_hit += 1
                        score_g, killed_c = harb.hit_segment(si)
                        if score_g > 0:
                            self.score += score_g
                            self._spawn_explosion(seg.x, seg.y, LIME, count=8)
                        else:
                            self.particles.append(Particle(
                                seg.x, seg.y, WHITE, speed=80, size=2, life=0.2))
                        self.sfx.play("explode")
                        break

        # ── Player bullets vs Colossus turrets ───────────────────────────
        if self.boss and self.boss.alive and isinstance(self.boss, Colossus):
            for bi, b in enumerate(self.bullets):
                if bi in bullets_hit:
                    continue
                # Check turrets first
                hit_turret = False
                for turret in self.boss.turrets:
                    if not turret.alive:
                        continue
                    if abs(b.x - turret.x) < 16 and abs(b.y - turret.y) < 16:
                        bullets_hit.add(bi)
                        self.shots_hit += 1
                        killed_t = turret.take_damage(1)
                        self.sfx.play("explode")
                        self._add_shake(2, 0.08)
                        if killed_t:
                            self.score += COLOSSUS_TURRET_SCORE
                            self._spawn_explosion(turret.x, turret.y, ORANGE, count=16)
                            self.combo_popups.append(ComboPopup(
                                int(turret.x), int(turret.y), 0, self.font_sm,
                                text=f"+{COLOSSUS_TURRET_SCORE}"))
                        hit_turret = True
                        break
                # Check core (only if exposed and not hit turret)
                if not hit_turret and self.boss.core_exposed:
                    if abs(b.x - self.boss.x) < 20 and abs(b.y - self.boss.y) < 20:
                        bullets_hit.add(bi)
                        self.shots_hit += 1
                        self.boss.take_damage(1)
                        self.sfx.play("explode")
                        self._add_shake(3, 0.1)
                        if not self.boss.alive:
                            pts = 1000 + self.wave * 75
                            self.score += pts
                            self._check_life_milestones()
                            self._spawn_explosion(self.boss.x, self.boss.y, RED, count=30)
                            self._spawn_explosion(self.boss.x, self.boss.y, GOLD, count=30)
                            self.boss_cinematic_timer = 2.5
                            self.boss_cinematic_x = self.boss.x
                            self.boss_cinematic_y = self.boss.y
                            self._add_shake(20, 1.0)
                            self.sfx.play("bomb")
                            # Drop 2 upgrade choices
                            self.combo_popups.append(ComboPopup(
                                int(self.boss.x), int(self.boss.y), 0,
                                self.font_med, text=f"+{pts}!"))
                            for _ in range(4):
                                self.powerups.append(PowerUp(
                                    int(self.boss.x) + random.randint(-120, 120),
                                    int(self.boss.y)))
                            self.boss = None
                            self._try_achievement("Boss Slayer")
                            break

        # ── Player bullets vs homing missiles (shoot them down) ──────────
        for bi, b in enumerate(self.bullets):
            if bi in bullets_hit:
                continue
            for m in self.homing_missiles:
                if not m.alive:
                    continue
                if math.hypot(b.x - m.x, b.y - m.y) < m.size + 8:
                    m.alive = False
                    bullets_hit.add(bi)
                    self.shots_hit += 1
                    self.score += 5
                    self._spawn_explosion(m.x, m.y, RED, count=4)
                    break

        # ── Player bullets vs bonus round enemies ────────────────────────
        if self.bonus_round_active:
            for bi, b in enumerate(self.bullets):
                if bi in bullets_hit:
                    continue
                for be in self.bonus_round_enemies:
                    if not be.alive or not be.active:
                        continue
                    if math.hypot(b.x - be.x, b.y - be.y) < be.size + 8:
                        be.alive = False
                        bullets_hit.add(bi)
                        self.bonus_round_killed += 1
                        self.score += BONUS_ROUND_SCORE
                        self._spawn_explosion(be.x, be.y, be.colour, count=18)
                        self.sfx.play("explode")
                        # Frag chain: kill nearby bonus enemies (1-level only)
                        for other in self.bonus_round_enemies:
                            if not other.alive or not other.active or other is be:
                                continue
                            if math.hypot(be.x - other.x, be.y - other.y) < BONUS_FRAG_RADIUS:
                                other.alive = False
                                self.bonus_round_killed += 1
                                self.score += BONUS_ROUND_SCORE
                                self._spawn_explosion(other.x, other.y, other.colour, count=12)
                        # Drop power-up every N kills
                        if self.bonus_round_killed % BONUS_POWERUP_EVERY == 0:
                            pu_kind = WeightedPowerUp.weighted_random_type(self.wave)
                            self.powerups.append(PowerUp(be.x, be.y, kind=pu_kind))
                            self.sfx.play("powerup")
                        break

        # ── Homing missiles vs player ────────────────────────────────────
        for m in self.homing_missiles:
            if not m.alive:
                continue
            if math.hypot(m.x - self.player_x, m.y - self.player_y) < 20:
                m.alive = False
                self._player_hit()

        # ── Player bullets vs boss ────────────────────────────────────────
        if self.boss and self.boss.alive and not isinstance(self.boss, Colossus):
            for bi, b in enumerate(self.bullets):
                if bi in bullets_hit:
                    continue
                if abs(b.x - self.boss.x) < 108 and abs(b.y - self.boss.y) < 42:
                    # Check variant-specific hit rules (Dreadnought shield gap,
                    # Phantom cloaking).  Bullets that fail just pass through.
                    if not self.boss.is_hittable(b.x, b.y):
                        continue
                    bullets_hit.add(bi)
                    self.shots_hit += 1
                    killed = self.boss.take_hit()
                    self._add_shake(3, 0.1)
                    self.sfx.play("explode")
                    # SwarmQueen: spawn a mini-drone wave when she signals
                    if isinstance(self.boss, SwarmQueen) and self.boss.spawn_pending:
                        self._spawn_swarm_queen_drones()
                        self.boss.clear_spawn()
                    if killed:
                        pts = 500 + self.wave * 50
                        self.score += pts
                        self._check_life_milestones()
                        self.combo_popups.append(ComboPopup(
                            int(self.boss.x), int(self.boss.y), 0,
                            self.font_med, text=f"+{pts}!",
                        ))
                        self.boss_cinematic_timer = 2.0
                        self.boss_cinematic_x     = self.boss.x
                        self.boss_cinematic_y     = self.boss.y
                        for _ in range(3):
                            ox_ = random.randint(-60, 60)
                            oy_ = random.randint(-30, 30)
                            self._spawn_explosion(
                                int(self.boss.x) + ox_,
                                int(self.boss.y) + oy_, RED, count=18)
                        self._spawn_explosion(int(self.boss.x), int(self.boss.y), GOLD,  count=30)
                        self._spawn_explosion(int(self.boss.x), int(self.boss.y), WHITE, count=20)
                        for _ in range(3):
                            self.powerups.append(PowerUp(
                                int(self.boss.x) + random.randint(-100, 100),
                                int(self.boss.y),
                            ))
                        self._add_shake(16, 0.7)
                        self.sfx.play("bomb")
                        self.boss = None
                        # Give remaining drones (SwarmQueen) a movement pattern
                        if self.aliens and not self.movement_pattern:
                            from si_movement import ClassicMarch
                            self.movement_pattern = ClassicMarch(
                                self.current_sector, self.wave,
                                self.current_alien_drop)
                        self._try_achievement("Boss Slayer")
                    break

        for bi in sorted(bullets_hit, reverse=True):
            if bi < len(self.bullets):
                self.bullets.pop(bi)

        if aliens_killed and self.score > 0:
            self._try_achievement("First Blood")

        # ── Power-ups ─────────────────────────────────────────────────────
        alive_powerups: list[PowerUp] = []
        for pu in self.powerups:
            pu.update(dt)
            if pu.alive:
                if abs(pu.x - self.player_x) < 36 and abs(pu.y - self.player_y) < 36:
                    self.sfx.play("powerup")
                    self.powerups_collected_wave += 1
                    if pu.kind == "shield":
                        self.has_shield = True
                    elif pu.kind == "bomb":
                        self._trigger_bomb()
                        self._try_achievement("Nuclear Option")
                    elif pu.kind == "emp":
                        self._trigger_emp()
                    else:
                        dur = getattr(self, "powerup_duration", POWERUP_DURATION)
                        self.active_powerups[pu.kind] = dur
                    if self.powerups_collected_wave >= 3:
                        self._try_achievement("Power Collector")
                else:
                    alive_powerups.append(pu)
        self.powerups = alive_powerups

        expired = [k for k, t in self.active_powerups.items() if t - dt <= 0]
        for k in expired:
            del self.active_powerups[k]
        for k in list(self.active_powerups):
            self.active_powerups[k] -= dt

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        # ── Alien invasion check ──────────────────────────────────────────
        # Use base_y (stable grid position) not y, so sine/accordion
        # oscillations don't trigger false invasions on the downswing.
        landed = [a for a in self.aliens if a.entry_progress >= 1.0]
        if landed:
            max_alien_y = max(a.base_y for a in landed)
            if max_alien_y >= self.player_y - 25:
                self._player_hit()
                # Prevent rapid re-triggering: invasion hits need a full
                # respawn window, not just the 0.01 s set by _player_hit().
                if self.invincible_timer < 1.5:
                    self.invincible_timer = 1.5

        # ── Frenzy banner timer ───────────────────────────────────────────
        if self.frenzy_banner_timer > 0:
            self.frenzy_banner_timer = max(0.0, self.frenzy_banner_timer - dt)

        # ── Boss cinematic ────────────────────────────────────────────────
        if self.boss_cinematic_timer > 0:
            self.boss_cinematic_timer -= dt
            if random.random() < 0.4:
                ox_b = random.uniform(-50, 50)
                oy_b = random.uniform(-30, 30)
                for _ in range(8):
                    self.particles.append(Particle(
                        self.boss_cinematic_x + ox_b,
                        self.boss_cinematic_y + oy_b,
                        random.choice([ORANGE, YELLOW, RED, WHITE, HOT_PINK]),
                        speed=random.uniform(50, 180),
                        size=random.randint(4, 9),
                        life=random.uniform(0.5, 1.2),
                    ))
            if random.random() < 0.15:
                self.sfx.play("explode")
                self._add_shake(5, 0.2)

        # ── Particles / popups / banners ──────────────────────────────────
        self.particles    = [p for p in self.particles if p.update(dt)]
        self.combo_popups = [c for c in self.combo_popups if c.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self.score >= CONTINUE_SCORE_THRESHOLD and not self.continue_used:
            self.continue_available = True

        # ── Wave clear ────────────────────────────────────────────────────
        if (not self.aliens and not self.dive_bombers and not self.galaga_divers
                and self.boss is None and not self.harbingers
                and not self.bonus_round_active):
            if not self.wave_damage_taken:
                self._try_achievement("Untouchable")
            if self.shots_fired > 0 and self.shots_hit / self.shots_fired >= 0.9:
                self._try_achievement("Sharp Shooter")

            self.wave_clear_flash = 0.5
            self.sfx.play("level_up")

            self.frenzy_streak       = 0
            self.frenzy_banner_timer = 0.0

            for k in list(self.active_upgrades):
                self.active_upgrades[k] -= 1
            expired_up = [k for k, v in self.active_upgrades.items() if v <= 0]
            for k in expired_up:
                del self.active_upgrades[k]

            cleared_wave = self.wave
            self.wave   += 1

            # ── Sector transition check ───────────────────────────────────────
            new_sector = min(len(SECTOR_DATA) - 1, (self.wave - 1) // 10)
            if new_sector != self.current_sector:
                self.current_sector        = new_sector
                sd                         = SECTOR_DATA[new_sector]
                self.sector_bg_target      = [float(c) for c in sd["bg"]]
                self.sector_star_tint      = sd["star_tint"]
                self.sector_transition_name = sd["name"]
                self.sector_transition_sub  = sd["subtitle"]
                self.sector_transition_timer = SECTOR_TRANSITION_DURATION
            if self.wave == 5:
                self._try_achievement("Wave 5")
            if self.wave == 10:
                self._try_achievement("Wave 10")
            self.sfx.play("level_up")

            elapsed  = pygame.time.get_ticks() / 1000.0 - self.wave_start_time
            accuracy = (self.shots_hit / self.shots_fired * 100
                        if self.shots_fired > 0 else 0.0)
            perfect_bonus  = 500 if not self.wave_damage_taken else 0
            acc_bonus      = int(accuracy * 5) if accuracy >= 90.0 else 0
            speed_bonus    = SPEED_BONUS_POINTS if elapsed < SPEED_BONUS_THRESHOLD else 0
            flawless_bonus = FLAWLESS_BONUS_POINTS if self.wave_flawless else 0

            # Wave codename (deterministic per wave number)
            adj  = CODENAME_ADJECTIVES[(cleared_wave * 7 + 3) % len(CODENAME_ADJECTIVES)]
            noun = CODENAME_NOUNS[(cleared_wave * 11 + 5) % len(CODENAME_NOUNS)]
            self.wave_codename = f"OPERATION  {adj}  {noun}"

            total_bonus = perfect_bonus + acc_bonus + speed_bonus + flawless_bonus
            if total_bonus > 0:
                self.score += total_bonus
                self._check_life_milestones()

            if flawless_bonus > 0:
                self.banners.append(
                    AchievementBanner("FLAWLESS WAVE!", self.font_sm))
                self.sfx.play("achieve")

            if speed_bonus > 0:
                self.combo_popups.append(ComboPopup(
                    WIDTH // 2, HEIGHT // 2 + 40, 0, self.font_med,
                    text=f"SPEED  CLEAR!  +{speed_bonus}"))

            self.wave_summary_data = {
                "wave":           cleared_wave,
                "kills":          self.wave_kills,
                "accuracy":       accuracy,
                "time":           elapsed,
                "perfect_bonus":  perfect_bonus,
                "acc_bonus":      acc_bonus,
                "speed_bonus":    speed_bonus,
                "flawless_bonus": flawless_bonus,
                "codename":       self.wave_codename,
            }
            self.sfx.music_channel.pause()

            if cleared_wave % BOSS_WAVE_INTERVAL == 0:
                available = list(UPGRADE_POOL)
                random.shuffle(available)
                self.upgrade_choices = available[:3]
                self.upgrade_cursor  = 1
                self.state = GameState.UPGRADE_PICK
            else:
                self.wave_summary_timer = 3.5
                self.state = GameState.WAVE_SUMMARY

    def _player_hit(self) -> None:
        if self.invincible_timer > 0:
            return
        self.invincible_timer = 0.01
        self.wave_flawless = False   # any hit — even absorbed by shield — breaks flawless

        if self.has_shield:
            self.has_shield = False
            self._spawn_explosion(self.player_x, self.player_y, BLUE, count=20)
            self._add_shake(4, 0.15)
            self.sfx.play("player_hit")
            self.invincible_timer = 0.5
            return

        self.lives -= 1
        self.wave_damage_taken = True
        self._spawn_ship_fragments()
        self._spawn_explosion(self.player_x, self.player_y,
                              self._get_ship_colour(), count=20)
        self._add_shake(6, 0.2)
        self.sfx.play("death")

        if self.frenzy_tier > 0:
            self.frenzy_tier -= 1
            if self.frenzy_tier > 0:
                self.frenzy_streak = FRENZY_TIERS[self.frenzy_tier - 1]["threshold"]
            else:
                self.frenzy_streak = 0
        else:
            self.frenzy_streak = 0
        self.frenzy_banner_timer = 0.0
        self.frenzy_beyond_kills = 0
        self.frenzy_beyond_level = 0

        if self.lives <= 0:
            self.state = GameState.GAME_OVER
            self.pending_score = self.score
            self.sfx.music_channel.stop()
            self.sfx.ufo_channel.stop()
            scores = [s["score"] for s in self.hs_data.get("scores", [])]
            if len(scores) < 5 or self.score > min(scores):
                self.entering_name = True
                self.name_chars    = ["A", "A", "A"]
                self.name_cursor   = 0
            else:
                self.hs_data["total_score"] = (
                    self.hs_data.get("total_score", 0) + self.score)
                save_json(HIGHSCORE_FILE, self.hs_data)
                self._unlock_ships()
        else:
            self.invincible_timer = INVINCIBILITY_TIME
            self.player_x = WIDTH // 2

    # ── Game Over ─────────────────────────────────────────────────────────────

    def _update_gameover(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        # Dynamic sector background colour
        bg_col = tuple(max(0, min(255, int(c))) for c in self.sector_bg)
        self.screen.fill(bg_col)  # type: ignore[arg-type]

        offset = [0, 0]
        if self.shake_timer > 0:
            # Smooth sinusoidal shake: two offset sine waves at different
            # frequencies give a convincing 2-D camera wobble without the
            # per-frame random jumps that cause visual noise.
            t   = pygame.time.get_ticks() / 1000.0
            amp = min(self.shake_intensity, 12) * min(1.0, self.shake_timer * 6)
            offset[0] = int(math.sin(t * 97.3) * amp)
            offset[1] = int(math.sin(t * 73.1) * amp)

        for star in self.stars:
            star.draw(self.screen, offset, tint=self.sector_star_tint)

        if self.state == GameState.TITLE:
            self._draw_title(offset)
        elif self.state == GameState.PLAYING:
            self._draw_playing(offset)
        elif self.state == GameState.PAUSED:
            self._draw_playing(offset)
            self._draw_paused()
        elif self.state == GameState.GAME_OVER:
            self._draw_gameover(offset)
        elif self.state == GameState.WAVE_SUMMARY:
            self._draw_playing(offset)
            self._draw_wave_summary()
        elif self.state == GameState.UPGRADE_PICK:
            self._draw_playing(offset)
            self._draw_upgrade_pick()

        for p in self.particles:
            p.draw(self.screen, offset)
        for b in self.banners:
            b.draw(self.screen)

        if self.bomb_flash_timer > 0:
            alpha = min(255, int(200 * (self.bomb_flash_timer / 0.18)))
            self._bomb_flash_surf.fill((255, 200, 50, alpha))
            self.screen.blit(self._bomb_flash_surf, (0, 0))

        if self.crt_enabled:
            self.screen.blit(self.scanline_surf, (0, 0))
            self.screen.blit(self.vignette_surf, (0, 0))

        pygame.display.flip()

    def _draw_title(self, offset: list[int]) -> None:
        pulse = 0.8 + 0.2 * math.sin(self.title_pulse)
        title = self.font_big.render("SPACE INVADERS", True, CYAN)
        tw, th = title.get_size()
        scaled = pygame.transform.scale(title, (int(tw * pulse), int(th * pulse)))
        self.screen.blit(scaled, (WIDTH // 2 - scaled.get_width() // 2, 120))

        sub = self.font_med.render("Press ENTER to play", True, WHITE)
        if int(pygame.time.get_ticks() / 500) % 2:
            self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 250))

        ship_colour = self._get_ship_colour()
        draw_ship(self.screen, WIDTH // 2, 360, ship_colour, 2.0)
        ship_label = self.font_sm.render(f"< {self.selected_ship} >", True, WHITE)
        self.screen.blit(ship_label,
                         (WIDTH // 2 - ship_label.get_width() // 2, 420))

        diff_y = 462
        diff_parts = []
        for d in DIFFICULTIES:
            if d == self.difficulty:
                diff_parts.append((f"[{d}]", GOLD))
            else:
                diff_parts.append((f" {d} ", DIM_WHITE))
        diff_label = self.font_sm.render("DIFFICULTY:", True, WHITE)
        total_parts_w = (sum(self.font_sm.size(p[0])[0] for p in diff_parts)
                         + self.font_sm.size("  |  ")[0] * 2)
        full_w = diff_label.get_width() + 16 + total_parts_w
        cx = WIDTH // 2 - full_w // 2
        self.screen.blit(diff_label, (cx, diff_y))
        cx += diff_label.get_width() + 16
        for i, (text, colour) in enumerate(diff_parts):
            t = self.font_sm.render(text, True, colour)
            self.screen.blit(t, (cx, diff_y))
            cx += t.get_width()
            if i < len(diff_parts) - 1:
                sep = self.font_sm.render(" | ", True, DIM_WHITE)
                self.screen.blit(sep, (cx, diff_y))
                cx += sep.get_width()
        diff_hint = self.font_xs.render("Up / Down = change difficulty", True, DIM_WHITE)
        self.screen.blit(diff_hint,
                         (WIDTH // 2 - diff_hint.get_width() // 2, diff_y + 30))

        next_unlock = None
        total = self.hs_data.get("total_score", 0)
        for threshold, name in SHIP_UNLOCK_THRESHOLDS:
            if total < threshold:
                next_unlock = (threshold, name)
                break
        if next_unlock:
            info = self.font_xs.render(
                f"Next unlock: {next_unlock[1]} at {next_unlock[0]} total pts "
                f"({total} earned)", True, DIM_WHITE)
            self.screen.blit(info, (WIDTH // 2 - info.get_width() // 2, 508))

        hs_title = self.font_med.render("HIGH SCORES", True, GOLD)
        self.screen.blit(hs_title, (WIDTH // 2 - hs_title.get_width() // 2, 548))

        scores = self.hs_data.get("scores", [])
        if scores:
            for i, entry in enumerate(scores[:5]):
                txt = self.font_sm.render(
                    f"{i+1}. {entry['name']}  {entry['score']}", True, WHITE)
                self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 596 + i * 40))
        else:
            txt = self.font_sm.render("No scores yet!", True, DIM_WHITE)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 596))

        ctrl = self.font_xs.render(
            "A/D or Arrows = Move  |  Space = Shoot  |  P = Pause  |  "
            "C = CRT  |  ESC = Quit",
            True, DIM_WHITE)
        self.screen.blit(ctrl, (WIDTH // 2 - ctrl.get_width() // 2, HEIGHT - 30))

        if self.konami_pending:
            kn = self.font_sm.render("★ CHEAT MODE ARMED — Press ENTER ★", True, GOLD)
            t_kn = pygame.time.get_ticks() / 1000.0
            kn.set_alpha(int(180 + 75 * abs(math.sin(t_kn * 3))))
            self.screen.blit(kn, (WIDTH // 2 - kn.get_width() // 2, HEIGHT - 62))

    def _draw_playing(self, offset: list[int]) -> None:
        ox, oy = offset

        if self.aliens:
            max_alien_y = max(a.y for a in self.aliens)
            danger_zone = HEIGHT - 350
            if max_alien_y > danger_zone:
                danger_frac = min(1.0, (max_alien_y - danger_zone) / 250)
                pulse_alpha = int(60 + 80 * abs(math.sin(pygame.time.get_ticks() / 180)))
                border_alpha = int(pulse_alpha * danger_frac)
                if border_alpha > 0:
                    border_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    bw = 14
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, 0, WIDTH, bw))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, HEIGHT - bw, WIDTH, bw))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, 0, bw, HEIGHT))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (WIDTH - bw, 0, bw, HEIGHT))
                    self.screen.blit(border_surf, (0, 0))

        for barrier in self.barriers:
            barrier.draw(self.screen, offset)

        if self.has_shield:
            glow = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*BLUE, 60), (50, 50), 50)
            pygame.draw.circle(glow, (*BLUE, 120), (50, 50), 48, 2)
            self.screen.blit(glow,
                             (int(self.player_x) - 50 + ox, int(self.player_y) - 50 + oy))

        if not (self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2):
            draw_ship(self.screen, int(self.player_x) + ox, int(self.player_y) + oy,
                      self._get_ship_colour())

        if self.drone_active:
            drone_x = int(self.player_x + math.cos(self.drone_angle) * DRONE_ORBIT_RADIUS)
            drone_y = int(self.player_y + math.sin(self.drone_angle) * DRONE_ORBIT_RADIUS)
            pts = [
                (drone_x + ox, drone_y + oy - 10),
                (drone_x + ox + 8, drone_y + oy),
                (drone_x + ox, drone_y + oy + 10),
                (drone_x + ox - 8, drone_y + oy),
            ]
            pygame.draw.polygon(self.screen, CYAN, pts)
            pygame.draw.polygon(self.screen, WHITE, pts, 1)
            glow = pygame.Surface((30, 30), pygame.SRCALPHA)
            t_glow = pygame.time.get_ticks() / 1000.0
            ga = int(30 + 20 * math.sin(t_glow * 4))
            pygame.draw.circle(glow, (*CYAN[:3], ga), (15, 15), 13)
            self.screen.blit(glow, (drone_x + ox - 15, drone_y + oy - 15))

        draw_fn = draw_alien_a if self.alien_frame == 0 else draw_alien_b
        max_hp_this_wave = min(3, 1 + (self.wave - 1) // 10)
        for a in self.aliens:
            if a.hit_flash > 0:
                col: tuple[int, int, int] = WHITE
            elif a.hp == 2:
                col = tuple(max(0, c - 60) for c in a.colour)   # type: ignore[assignment]
            elif a.hp == 1 and a.hp < max_hp_this_wave:
                col = tuple(max(0, c - 120) for c in a.colour)  # type: ignore[assignment]
            else:
                col = a.colour
            if a.is_anchor:
                # Pulsing glow for anchor alien
                t_a = pygame.time.get_ticks() / 1000.0
                glow_a = int(40 + 25 * math.sin(t_a * 5))
                glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*GOLD[:3], glow_a), (30, 30), 28)
                self.screen.blit(glow_surf, (int(a.x) + ox - 30,
                                             int(a.y) + oy - 30))
                draw_fn(self.screen, int(a.x) + ox, int(a.y) + oy, col,
                        1.4, tier=a.sprite_tier)
            else:
                draw_fn(self.screen, int(a.x) + ox, int(a.y) + oy, col,
                        tier=a.sprite_tier)

        for diver in self.dive_bombers:
            diver.draw(self.screen, offset)

        for diver in self.galaga_divers:
            diver.draw(self.screen, offset)

        # ── Harbinger elites ─────────────────────────────────────────────
        for harb in self.harbingers:
            if harb.alive:
                harb.draw(self.screen)

        # ── Homing missiles ─────────────────────────────────────────────
        for m in self.homing_missiles:
            m.draw(self.screen)

        # ── Bonus round enemies ──────────────────────────────────────────
        if self.bonus_round_active:
            for be in self.bonus_round_enemies:
                be.draw(self.screen)
            # Bonus round HUD
            br_txt = self.font_sm.render(
                f"BONUS: {self.bonus_round_killed}/{BONUS_ROUND_ENEMIES}  "
                f"TIME: {max(0, self.bonus_round_timer):.1f}s",
                True, GOLD)
            self.screen.blit(br_txt, (WIDTH // 2 - br_txt.get_width() // 2, 20))

        # ── Solar flare ──────────────────────────────────────────────────
        sector_idx = min(len(SECTOR_DATA) - 1, (self.wave - 1) // 10)
        if sector_idx == 3:
            self.solar_flare.draw(self.screen)

        if self.boss and self.boss.alive:
            self.boss.draw(self.screen, offset)

        if self.ufo:
            self.ufo.draw(self.screen, offset)

        for b in self.bullets:
            bx, by_ = int(b.x) + ox, int(b.y) + oy
            col_b = b.colour
            if b.is_frag:
                pygame.draw.rect(self.screen, col_b,
                                 (bx - 3, by_ - 7, 6, 14), border_radius=3)
                pygame.draw.rect(self.screen, WHITE,
                                 (bx - 1, by_ - 5, 2, 8), border_radius=1)
            else:
                glow = pygame.Surface((16, 36), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*col_b[:3], 30), (0, 0, 16, 36), border_radius=8)
                self.screen.blit(glow, (bx - 8, by_ - 10))
                trail = pygame.Surface((12, 30), pygame.SRCALPHA)
                pygame.draw.rect(trail, (*col_b[:3], 50), (0, 0, 12, 30), border_radius=6)
                self.screen.blit(trail, (bx - 6, by_ - 6))
                pygame.draw.rect(self.screen, col_b,
                                 (bx - 3, by_ - 10, 6, 20), border_radius=3)
                pygame.draw.rect(self.screen, WHITE,
                                 (bx - 1, by_ - 8, 2, 12), border_radius=1)

        for eb in self.enemy_bullets:
            ex, ey = int(eb.x) + ox, int(eb.y) + oy
            glow = pygame.Surface((20, 28), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*HOT_PINK, 40), (0, 0, 20, 28))
            self.screen.blit(glow, (ex - 10, ey - 10))
            pts_eb = [(ex, ey - 10), (ex - 5, ey), (ex, ey + 10), (ex + 5, ey)]
            pygame.draw.polygon(self.screen, RED, pts_eb)
            pygame.draw.circle(self.screen, HOT_PINK, (ex, ey), 3)

        for pu in self.powerups:
            pu.draw(self.screen, offset)
            lbl = self.font_xs.render(POWERUP_LABELS.get(pu.kind, ""), True, pu.colour)
            lx = int(pu.x) + ox - lbl.get_width() // 2
            ly = int(pu.y) + oy + 22
            self.screen.blit(lbl, (lx, ly))

        for cp in self.combo_popups:
            cp.draw(self.screen, offset)

        # ── Ship fragments ────────────────────────────────────────────────
        for frag in self.ship_fragments:
            frag.draw(self.screen, offset)

        # ── Last Alien pulsing label ──────────────────────────────────────
        if (len(self.aliens) == 1 and not self.boss
                and not self.dive_bombers and self.boss_cinematic_timer <= 0):
            t_la = pygame.time.get_ticks() / 1000.0
            pulse_a = int(180 + 75 * abs(math.sin(t_la * 5)))
            last_txt = self.font_lv.render("LAST  ONE!", True, RED)
            last_txt.set_alpha(pulse_a)
            self.screen.blit(last_txt, (WIDTH // 2 - last_txt.get_width() // 2, 82))

        if self.wave_clear_flash > 0:
            alpha = int(180 * self.wave_clear_flash)
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((0, 220, 255, alpha))
            self.screen.blit(flash, (0, 0))

        if self.boss_cinematic_timer > 0:
            bt = self.font_med.render("BOSS  DESTROYED!", True, ORANGE)
            self.screen.blit(bt, (WIDTH // 2 - bt.get_width() // 2, HEIGHT // 2 - 40))

        # ── Boss title card ───────────────────────────────────────────────────
        if self.boss_title_timer > 0:
            self._draw_boss_title_card()

        # ── Sector transition banner ──────────────────────────────────────────
        if self.sector_transition_timer > 0:
            self._draw_sector_transition()

        # ── Predator lock-on targeting laser ─────────────────────────────────
        lock_prog = getattr(self.movement_pattern, "lock_on_progress", None)
        if lock_prog is not None and lock_prog > 0.3 and self.aliens:
            # Draw red line from locked alien to player
            nearest_alien = min(self.aliens, key=lambda a: math.hypot(
                a.x - self.player_x, a.y - self.player_y))
            laser_alpha = int(80 + 120 * lock_prog)
            laser_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(laser_surf, (255, 0, 0, laser_alpha),
                             (int(nearest_alien.x), int(nearest_alien.y)),
                             (int(self.player_x), int(self.player_y)), 2)
            self.screen.blit(laser_surf, (0, 0))
            # Red screen border tint at high progress
            if lock_prog > 0.7:
                tint_alpha = int(30 * (lock_prog - 0.7) / 0.3)
                tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                tint.fill((255, 0, 0, tint_alpha))
                self.screen.blit(tint, (0, 0))

        # ── Active synergy indicators ────────────────────────────────────────
        if self.active_synergies:
            sy = 70
            for syn in SYNERGY_DEFINITIONS:
                if syn["id"] in self.active_synergies:
                    stxt = self.font_xs.render(syn["name"], True, syn.get("colour", WHITE))
                    self.screen.blit(stxt, (10, sy))
                    sy += 16

        # ── Predator lock-on bar ──────────────────────────────────────────────
        if lock_prog is not None:
            bar_x, bar_y, bar_w, bar_h = 1550, 18, 280, 22
            # Background track
            pygame.draw.rect(self.screen, (60, 20, 20),
                             (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            # Fill (orange → hot-pink as bar approaches full)
            fill_w = int(bar_w * lock_prog)
            r = 255
            g = int(136 * (1.0 - lock_prog))
            b = int(lock_prog * 120)
            if fill_w > 0:
                pygame.draw.rect(self.screen, (r, g, b),
                                 (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            # Border
            pygame.draw.rect(self.screen, (180, 80, 0),
                             (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)
            # Label
            lbl = self.font_sm.render("LOCK-ON", True, (255, 180, 60))
            self.screen.blit(lbl, (bar_x, bar_y + bar_h + 2))
            # Flash "SURGE!" when bar is full
            if lock_prog >= 1.0 and int(pygame.time.get_ticks() / 1000.0 * 6) % 2 == 0:
                surge_txt = self.font_med.render("SURGE!", True, (255, 50, 50))
                sr = surge_txt.get_rect(centerx=bar_x + bar_w // 2, y=bar_y - 28)
                self.screen.blit(surge_txt, sr)

        self._draw_hud()
        self._draw_frenzy_overlay()

    def _draw_frenzy_overlay(self) -> None:
        if self.frenzy_tier == 0 and self.frenzy_streak == 0 and self.frenzy_banner_timer == 0:
            return

        t    = pygame.time.get_ticks() / 1000.0
        tier = self.frenzy_tier

        if tier > 0:
            td    = FRENZY_TIERS[tier - 1]
            col   = td["colour"]
            pulse = 0.5 + 0.5 * math.sin(t * (3 + tier * 1.5))
            bw    = 6 + tier * 4 + int(tier * 8 * abs(math.sin(t * 2)))
            alpha = min(255, int(70 + 110 * pulse + tier * 30))
            self._frenzy_glow_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self._frenzy_glow_surf, (*col[:3], alpha), (0,          0,           WIDTH, bw))
            pygame.draw.rect(self._frenzy_glow_surf, (*col[:3], alpha), (0,          HEIGHT - bw, WIDTH, bw))
            pygame.draw.rect(self._frenzy_glow_surf, (*col[:3], alpha), (0,          0,           bw,    HEIGHT))
            pygame.draw.rect(self._frenzy_glow_surf, (*col[:3], alpha), (WIDTH - bw, 0,           bw,    HEIGHT))
            self.screen.blit(self._frenzy_glow_surf, (0, 0))

            if tier == 3:
                pulse_pulse = abs(math.sin(t * 3))
                self._frenzy_vignette_surf.fill((0, 0, 0, 0))
                pygame.draw.ellipse(self._frenzy_vignette_surf,
                                    (255, 0, 100, int(15 * pulse_pulse)),
                                    (WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2))
                self.screen.blit(self._frenzy_vignette_surf, (0, 0))

        if tier > 0:
            hcol   = FRENZY_TIERS[tier - 1]["colour"]
            hpulse = int(40 + 40 * math.sin(t * 6))
            self._frenzy_halo_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(self._frenzy_halo_surf, (*hcol[:3], hpulse), (40, 40), 36 + tier * 2)
            self.screen.blit(self._frenzy_halo_surf, (int(self.player_x) - 40, int(self.player_y) - 40))

        streak_col = FRENZY_TIERS[tier - 1]["colour"] if tier > 0 else CYAN
        sy_base    = HEIGHT - 130

        streak_surf = self.font_med.render(str(self.frenzy_streak), True, streak_col)
        self.screen.blit(streak_surf,
                         (WIDTH // 2 - streak_surf.get_width() // 2, sy_base))

        bar_y = sy_base + streak_surf.get_height() + 6
        bar_w = 220

        if tier < 3:
            next_td  = FRENZY_TIERS[tier]
            prev_thr = FRENZY_TIERS[tier - 1]["threshold"] if tier > 0 else 0
            progress = ((self.frenzy_streak - prev_thr)
                        / max(1, next_td["threshold"] - prev_thr))
            progress = max(0.0, min(1.0, progress))
            ncol     = next_td["colour"]
            pygame.draw.rect(self.screen, (40, 40, 40),
                             (WIDTH // 2 - bar_w // 2, bar_y, bar_w, 8), border_radius=4)
            pygame.draw.rect(self.screen, streak_col,
                             (WIDTH // 2 - bar_w // 2, bar_y,
                              int(bar_w * progress), 8), border_radius=4)
            lbl = self.font_xs.render(f"→ {next_td['name']}", True, ncol)
            self.screen.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, bar_y + 12))
        else:
            mp  = 0.85 + 0.15 * math.sin(t * 5)
            lbl = self.font_xs.render("✦ MAX FRENZY ✦", True, HOT_PINK)
            lw, lh = lbl.get_size()
            ls = pygame.transform.scale(lbl, (int(lw * mp), int(lh * mp)))
            self.screen.blit(ls, (WIDTH // 2 - ls.get_width() // 2, bar_y + 4))
            if self.frenzy_beyond_level > 0:
                beyond_txt = self.font_xs.render(
                    f"✦ MANIAC  +{self.frenzy_beyond_level} ✦", True, HOT_PINK)
                self.screen.blit(beyond_txt,
                                 (WIDTH // 2 - beyond_txt.get_width() // 2, bar_y + 28))

        if self.frenzy_banner_timer > 0 and self.frenzy_banner_tier > 0:
            td   = FRENZY_TIERS[self.frenzy_banner_tier - 1]
            prog = self.frenzy_banner_timer / FRENZY_BANNER_DURATION
            scale = (1.0 + 1.5 * (prog - 0.75) / 0.25) if prog > 0.75 else 1.0
            alpha = int(255 * min(1.0, prog * 3.5))
            txt   = self.font_med.render(td["name"], True, td["colour"])
            tw, th = txt.get_size()
            scaled = pygame.transform.scale(txt, (int(tw * scale), int(th * scale)))
            scaled.set_alpha(alpha)
            bx  = WIDTH  // 2 - scaled.get_width()  // 2
            by_ = HEIGHT // 2 - scaled.get_height() // 2 - 80
            shadow   = self.font_med.render(td["name"], True, (0, 0, 0))
            sw, sh_  = shadow.get_size()
            shadow_s = pygame.transform.scale(shadow, (int(sw * scale), int(sh_ * scale)))
            shadow_s.set_alpha(alpha // 2)
            self.screen.blit(shadow_s, (bx + 4, by_ + 4))
            self.screen.blit(scaled,   (bx,     by_))

    def _draw_boss_title_card(self) -> None:
        """Full-width cinematic title card that appears when a boss spawns."""
        t         = self.boss_title_timer
        duration  = 3.8
        # Fade in for first 0.5 s, stay solid, fade out in last 0.6 s
        if t > duration - 0.5:
            alpha = int(255 * (duration - t) / 0.5)
        elif t < 0.6:
            alpha = int(255 * (t / 0.6))
        else:
            alpha = 255

        # Dark overlay bar
        overlay = pygame.Surface((WIDTH, 180), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(alpha * 0.65)))
        self.screen.blit(overlay, (0, HEIGHT // 2 - 90))

        # Red scan line accent
        for dy in (0, 178):
            line_surf = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
            line_surf.fill((*RED, alpha))
            self.screen.blit(line_surf, (0, HEIGHT // 2 - 90 + dy))

        # Title text
        title_surf = self.font_big.render(self.boss_title_name, True, RED)
        title_surf.set_alpha(alpha)
        tx = WIDTH // 2 - title_surf.get_width() // 2
        self.screen.blit(title_surf, (tx, HEIGHT // 2 - 72))

        # Subtitle text
        sub_surf = self.font_med.render(self.boss_title_sub, True, DIM_WHITE)
        sub_surf.set_alpha(alpha)
        sx = WIDTH // 2 - sub_surf.get_width() // 2
        self.screen.blit(sub_surf, (sx, HEIGHT // 2 + 20))

    def _draw_sector_transition(self) -> None:
        """Slide-in banner announcing a new sector."""
        t         = self.sector_transition_timer
        duration  = SECTOR_TRANSITION_DURATION
        # Slide in from top during first 0.4 s, hold, fade out in last 0.5 s
        if t > duration - 0.4:
            slide = 1.0 - (duration - t) / 0.4
        elif t < 0.5:
            slide = 0.0
            alpha = int(255 * (t / 0.5))
        else:
            slide = 0.0
            alpha = 255
        if t >= 0.5:
            alpha = 255

        slide_offset = int(-220 * slide)
        banner_h     = 110
        banner_y     = 36 + slide_offset

        overlay = pygame.Surface((WIDTH, banner_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(alpha * 0.75)))
        self.screen.blit(overlay, (0, banner_y))

        # Accent lines
        for dy in (0, banner_h - 2):
            line_surf = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
            line_surf.fill((*CYAN, alpha))
            self.screen.blit(line_surf, (0, banner_y + dy))

        name_surf = self.font_lv.render(self.sector_transition_name, True, CYAN)
        name_surf.set_alpha(alpha)
        self.screen.blit(name_surf,
                         (WIDTH // 2 - name_surf.get_width() // 2,
                          banner_y + 10))

        sub_surf = self.font_med.render(self.sector_transition_sub, True, DIM_WHITE)
        sub_surf.set_alpha(alpha)
        self.screen.blit(sub_surf,
                         (WIDTH // 2 - sub_surf.get_width() // 2,
                          banner_y + 62))

    def _draw_hud(self) -> None:
        panel = pygame.Surface((400, 45), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 80),   (0, 0, 400, 45), border_radius=6)
        pygame.draw.rect(panel, (*CYAN, 60),      (0, 0, 400, 45), 1, border_radius=6)
        self.screen.blit(panel, (10, 6))

        score_txt = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_txt, (20, 12))

        if self.combo_multiplier > 1 and self.combo_timer > 0:
            combo_txt = self.font_med.render(f"x{self.combo_multiplier}", True, YELLOW)
            self.screen.blit(combo_txt, (score_txt.get_width() + 30, 12))

        is_boss_wave = (self.wave % BOSS_WAVE_INTERVAL == 0)
        lv_str = f"BOSS  WAVE  {self.wave}" if (is_boss_wave and self.boss) else f"LEVEL {self.wave}"
        lv_col = RED if (is_boss_wave and self.boss) else GOLD
        lv_txt = self.font_lv.render(lv_str, True, lv_col)
        lv_w, lv_h = lv_txt.get_size()
        lv_x = WIDTH // 2 - lv_w // 2
        lv_y = 6
        lv_panel = pygame.Surface((lv_w + 30, lv_h + 10), pygame.SRCALPHA)
        pygame.draw.rect(lv_panel, (0, 0, 0, 100),
                         (0, 0, lv_w + 30, lv_h + 10), border_radius=8)
        pygame.draw.rect(lv_panel, (*lv_col, 120),
                         (0, 0, lv_w + 30, lv_h + 10), 2, border_radius=8)
        self.screen.blit(lv_panel, (lv_x - 15, lv_y - 2))
        glow_txt = self.font_lv.render(lv_str, True, lv_col)
        glow_txt.set_alpha(60)
        self.screen.blit(glow_txt, (lv_x + 2, lv_y + 2))
        self.screen.blit(lv_txt,   (lv_x, lv_y))

        for i in range(self.lives):
            draw_ship(self.screen, WIDTH - 50 - i * 50, 28,
                      self._get_ship_colour(), 0.6)

        diff_colour = {"Easy": LIME, "Normal": CYAN, "Hard": RED}.get(
            self.difficulty, WHITE)
        diff_str  = self.difficulty.upper()
        if self.konami_active:
            diff_str = "CHEATER!"
            diff_colour = GOLD
        diff_badge = self.font_xs.render(diff_str, True, diff_colour)
        db_w = diff_badge.get_width() + 10
        db_x = WIDTH - db_w - 10
        db_y = 50
        db_bg = pygame.Surface((db_w, 18), pygame.SRCALPHA)
        pygame.draw.rect(db_bg, (*diff_colour[:3], 40),  (0, 0, db_w, 18), border_radius=4)
        pygame.draw.rect(db_bg, (*diff_colour[:3], 160), (0, 0, db_w, 18), 1, border_radius=4)
        self.screen.blit(db_bg,    (db_x, db_y))
        self.screen.blit(diff_badge, (db_x + 5, db_y + 1))

        if self.aliens:
            alien_count_txt = self.font_xs.render(
                f"\u25a0 x{len(self.aliens)}", True, HOT_PINK)
            self.screen.blit(alien_count_txt,
                             (WIDTH - alien_count_txt.get_width() - 16, 70))

        bar_y_start = 58
        row_h = 18
        for idx, (kind, remaining) in enumerate(self.active_powerups.items()):
            bar_y   = bar_y_start + idx * row_h
            label   = POWERUP_LABELS.get(kind, kind.upper())
            colour  = POWERUP_COLOURS.get(kind, WHITE)
            bar_w_  = int(350 * min(remaining / POWERUP_DURATION, 1.0))
            pygame.draw.rect(self.screen, (*colour[:3], 80),
                             (20, bar_y, 350, 13), border_radius=4)
            pygame.draw.rect(self.screen, (*colour[:3],),
                             (20, bar_y, bar_w_, 13), border_radius=4)
            pygame.draw.rect(self.screen, colour,
                             (20, bar_y, 350, 13), 1, border_radius=4)
            lbl = self.font_xs.render(label, True, colour)
            self.screen.blit(lbl, (376, bar_y - 1))

        if self.has_shield:
            sh_y = bar_y_start + len(self.active_powerups) * row_h
            sh   = self.font_xs.render("SHIELD ACTIVE", True, BLUE)
            self.screen.blit(sh, (20, sh_y))

        badge_x = 20
        badge_y = HEIGHT - 34
        upgrade_badge_info = {
            "pierce": ("PIERCE", CYAN),
            "regen":  ("REGEN",  LIME),
            "burst":  ("BURST",  HOT_PINK),
            "speed":  ("SPEED",  YELLOW),
            "frag":   ("FRAG",   ORANGE),
        }
        for uid, (label, colour) in upgrade_badge_info.items():
            waves_left = self.active_upgrades.get(uid, 0)
            if waves_left == 0:
                continue
            badge_str  = f"{label} {waves_left}w"
            badge_surf = self.font_xs.render(badge_str, True, colour)
            bw_        = badge_surf.get_width() + 10
            badge_bg   = pygame.Surface((bw_, 18), pygame.SRCALPHA)
            pygame.draw.rect(badge_bg, (*colour[:3], 40),  (0, 0, bw_, 18), border_radius=4)
            pygame.draw.rect(badge_bg, (*colour[:3], 160), (0, 0, bw_, 18), 1, border_radius=4)
            self.screen.blit(badge_bg,  (badge_x, badge_y))
            self.screen.blit(badge_surf, (badge_x + 5, badge_y + 1))
            badge_x += bw_ + 6

        if self.combo_count > 0 and self.combo_timer > 0:
            bar_x, bar_y2 = 20, 98
            bar_max_w     = 280
            remaining_c   = self.combo_timer / COMBO_WINDOW
            pygame.draw.rect(self.screen, (50, 50, 0),
                             (bar_x, bar_y2, bar_max_w, 7), border_radius=3)
            pulse  = int(190 + 65 * math.sin(pygame.time.get_ticks() / 90))
            fill_c = (pulse, pulse, 0)
            pygame.draw.rect(self.screen, fill_c,
                             (bar_x, bar_y2, int(bar_max_w * remaining_c), 7),
                             border_radius=3)
            pygame.draw.rect(self.screen, YELLOW,
                             (bar_x, bar_y2, bar_max_w, 7), 1, border_radius=3)
            lbl = self.font_xs.render("COMBO", True, YELLOW)
            self.screen.blit(lbl, (bar_x + bar_max_w + 8, bar_y2 - 4))

        if self.next_life_milestone_idx < len(EXTRA_LIFE_MILESTONES):
            next_ms = EXTRA_LIFE_MILESTONES[self.next_life_milestone_idx]
            needed  = next_ms - self.score
            if needed > 0:
                life_txt = self.font_xs.render(f"+1 life at {next_ms}", True, DIM_WHITE)
                self.screen.blit(life_txt, (20, 118))

    def _draw_upgrade_pick(self) -> None:
        t = pygame.time.get_ticks() / 1000.0

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

        title = self.font_big.render("CHOOSE AN UPGRADE", True, GOLD)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))

        hint = self.font_xs.render("← → to select   ENTER to confirm", True, DIM_WHITE)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 172))

        card_w, card_h = 300, 260
        gap    = 40
        total_w = 3 * card_w + 2 * gap
        start_x = WIDTH // 2 - total_w // 2
        card_y  = HEIGHT // 2 - card_h // 2 - 20

        for idx, upg in enumerate(self.upgrade_choices):
            cx       = start_x + idx * (card_w + gap)
            selected = (idx == self.upgrade_cursor)
            col      = upg["colour"]

            card     = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_alpha = 210 if selected else 130
            pygame.draw.rect(card, (10, 10, 40, bg_alpha),
                             (0, 0, card_w, card_h), border_radius=14)

            if selected:
                p      = 0.7 + 0.3 * math.sin(t * 5)
                border_col: tuple = (int(255 * p), int(200 * p), 0, 255)
                border_w = 3
            else:
                border_col = (*col[:3], 100)
                border_w   = 1
            pygame.draw.rect(card, border_col,
                             (0, 0, card_w, card_h), border_w, border_radius=14)
            self.screen.blit(card, (cx, card_y))

            name_surf = self.font_med.render(
                upg["name"], True, col if not selected else WHITE)
            self.screen.blit(name_surf,
                             (cx + card_w // 2 - name_surf.get_width() // 2,
                              card_y + 28))

            pygame.draw.rect(self.screen, col, (cx + 20, card_y + 56, card_w - 40, 2))

            for li, line in enumerate(upg["desc"]):
                dl = self.font_xs.render(line, True, (200, 200, 200))
                self.screen.blit(dl,
                                 (cx + card_w // 2 - dl.get_width() // 2,
                                  card_y + 74 + li * 22))

            waves_left = self.active_upgrades.get(upg["id"], 0)
            if waves_left > 0:
                badge_str = f"+{UPGRADE_DURATION_WAVES}w  ({waves_left}w left)"
                badge     = self.font_xs.render(badge_str, True, LIME)
                badge_bg  = pygame.Surface((badge.get_width() + 12, 18), pygame.SRCALPHA)
                pygame.draw.rect(badge_bg, (0, 180, 0, 60),
                                 (0, 0, *badge_bg.get_size()), border_radius=5)
                pygame.draw.rect(badge_bg, (0, 220, 0, 160),
                                 (0, 0, *badge_bg.get_size()), 1, border_radius=5)
                bx_ = cx + card_w // 2 - badge_bg.get_width() // 2
                self.screen.blit(badge_bg, (bx_, card_y + card_h - 50))
                self.screen.blit(badge,    (bx_ + 6, card_y + card_h - 49))

            if selected:
                arrow_pts = [
                    (cx + card_w // 2,      card_y + card_h + 12),
                    (cx + card_w // 2 - 14, card_y + card_h + 30),
                    (cx + card_w // 2 + 14, card_y + card_h + 30),
                ]
                pygame.draw.polygon(self.screen, GOLD, arrow_pts)

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        t     = pygame.time.get_ticks() / 1000.0
        pulse = 0.92 + 0.08 * math.sin(t * 4)
        txt   = self.font_big.render("PAUSED", True, CYAN)
        tw, th = txt.get_size()
        scaled = pygame.transform.scale(txt, (int(tw * pulse), int(th * pulse)))
        self.screen.blit(scaled, (WIDTH // 2 - scaled.get_width() // 2,
                                   HEIGHT // 2 - scaled.get_height() // 2 - 30))

        hint = self.font_med.render("Press P or ENTER to resume", True, WHITE)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 60))

    def _draw_wave_summary(self) -> None:
        d = self.wave_summary_data
        if not d:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        panel_w, panel_h = 700, 400
        panel_x = WIDTH  // 2 - panel_w // 2
        panel_y = HEIGHT // 2 - panel_h // 2

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 50, 220),
                         (0, 0, panel_w, panel_h), border_radius=16)
        pygame.draw.rect(panel, (*GOLD, 180),
                         (0, 0, panel_w, panel_h), 2, border_radius=16)
        self.screen.blit(panel, (panel_x, panel_y))

        cx = WIDTH // 2

        title_txt = self.font_big.render(f"WAVE  {d['wave']}  CLEAR!", True, GOLD)
        self.screen.blit(title_txt, (cx - title_txt.get_width() // 2, panel_y + 18))

        if d.get("codename"):
            cn_txt = self.font_xs.render(d["codename"], True, DIM_WHITE)
            self.screen.blit(cn_txt, (cx - cn_txt.get_width() // 2, panel_y + 88))

        row_y   = panel_y + 108
        row_gap = 46

        def stat_row(label: str, value: str,
                     colour: tuple[int, int, int] = WHITE) -> None:
            nonlocal row_y
            lbl = self.font_med.render(label, True, DIM_WHITE)
            val = self.font_med.render(value, True, colour)
            self.screen.blit(lbl, (cx - 280, row_y))
            self.screen.blit(val, (cx + 160 - val.get_width(), row_y))
            row_y += row_gap

        stat_row("Enemies destroyed:", str(d["kills"]), LIME)
        stat_row("Accuracy:", f"{d['accuracy']:.0f}%",
                 LIME if d["accuracy"] >= 90 else YELLOW if d["accuracy"] >= 60 else RED)
        stat_row("Time:", f"{d['time']:.1f}s", CYAN)

        if d.get("flawless_bonus", 0) > 0:
            stat_row("FLAWLESS bonus:", f"+{d['flawless_bonus']}", GOLD)
        if d["perfect_bonus"] > 0:
            stat_row("Perfect wave bonus:", f"+{d['perfect_bonus']}", GOLD)
        if d["acc_bonus"] > 0:
            stat_row("Accuracy bonus:", f"+{d['acc_bonus']}", GOLD)
        if d.get("speed_bonus", 0) > 0:
            stat_row("Speed clear bonus:", f"+{d['speed_bonus']}", CYAN)

        next_wave = d["wave"] + 1
        is_boss   = (next_wave % BOSS_WAVE_INTERVAL == 0)
        next_col  = RED if is_boss else WHITE
        next_str  = f"BOSS WAVE {next_wave}!" if is_boss else f"Next: Wave {next_wave}"
        next_txt  = self.font_sm.render(next_str, True, next_col)
        self.screen.blit(next_txt, (cx - next_txt.get_width() // 2,
                                     panel_y + panel_h - 72))

        if int(pygame.time.get_ticks() / 500) % 2:
            skip_txt = self.font_xs.render("SPACE / ENTER to continue", True, DIM_WHITE)
            self.screen.blit(skip_txt, (cx - skip_txt.get_width() // 2,
                                         panel_y + panel_h - 36))

        # Show sector transition banner if one just triggered
        if self.sector_transition_timer > 0:
            self._draw_sector_transition()

    def _draw_gameover(self, offset: list[int]) -> None:
        draw_fn = draw_alien_a if self.alien_frame == 0 else draw_alien_b
        for a in self.aliens:
            draw_fn(self.screen,
                    int(a.x) + offset[0], int(a.y) + offset[1], a.colour,
                    tier=a.sprite_tier)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        go_txt = self.font_big.render("GAME OVER", True, RED)
        self.screen.blit(go_txt, (WIDTH // 2 - go_txt.get_width() // 2, 280))

        score_txt = self.font_med.render(
            f"Final Score: {self.score}  |  Level: {self.wave}", True, WHITE)
        self.screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 390))

        if self.entering_name:
            prompt = self.font_med.render("NEW HIGH SCORE! Enter initials:", True, GOLD)
            self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 470))

            for i, ch in enumerate(self.name_chars):
                colour = YELLOW if i == self.name_cursor else WHITE
                char_txt = self.font_big.render(ch, True, colour)
                x = WIDTH // 2 - 80 + i * 70
                self.screen.blit(char_txt, (x, 530))
                if i == self.name_cursor:
                    arrow_up = self.font_sm.render("^", True, colour)
                    arrow_dn = self.font_sm.render("v", True, colour)
                    self.screen.blit(arrow_up, (x + 15, 500))
                    self.screen.blit(arrow_dn, (x + 15, 620))

            confirm = self.font_sm.render(
                "Type letters or use Up/Down arrows, then ENTER", True, DIM_WHITE)
            self.screen.blit(confirm,
                             (WIDTH // 2 - confirm.get_width() // 2, 670))
        else:
            if self.continue_available and not self.continue_used:
                ct = self.font_med.render(
                    "PRESS  C  TO  CONTINUE  (WAVE {})".format(
                        max(1, int(self.wave * CONTINUE_WAVE_PENALTY))),
                    True, CYAN)
                self.screen.blit(ct, (WIDTH // 2 - ct.get_width() // 2, 450))
                restart_y = 520
            else:
                restart_y = 500

            restart = self.font_med.render("Press R to return to title", True, WHITE)
            if int(pygame.time.get_ticks() / 500) % 2:
                self.screen.blit(restart,
                                 (WIDTH // 2 - restart.get_width() // 2, restart_y))
