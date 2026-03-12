"""
si_entities.py — All game entities and procedural draw helpers.

Aliens, Bullets, and EnemyBullets are dataclasses instead of plain dicts.
This gives attribute access (a.x, b.pierce_remaining), type checking,
and makes it impossible to silently typo a key name.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from si_constants import (
    WIDTH, HEIGHT,
    BG, CYAN, HOT_PINK, LIME, ORANGE, YELLOW, RED, BLUE, WHITE, GOLD,
    POWERUP_FALL_SPEED, POWERUP_TYPES, POWERUP_COLOURS, POWERUP_WEIGHTS_EARLY,
    POWERUP_WEIGHTS_LATE,
    UFO_Y,
    BARRIER_BLOCK_W, BARRIER_BLOCK_H,
    DIVE_SPEED,
    BOSS_WAVE_INTERVAL,
    DIM_WHITE,
    SENTINEL_HP, SENTINEL_SCORE, SENTINEL_SPEED,
    SENTINEL_SHIELD_GAP, SENTINEL_SHIELD_SPEED, SENTINEL_SHIELD_SPEED_P2,
    SENTINEL_SHIELD_RADIUS, SENTINEL_SHOOT_INTERVAL,
    WRAITH_HP, WRAITH_SCORE, WRAITH_TELEPORT_INTERVAL,
    WRAITH_SHIMMER_DURATION, WRAITH_INVULN_DURATION,
    WRAITH_MISSILE_SPEED, WRAITH_MISSILE_TRACKING, WRAITH_MISSILE_LIFETIME,
    WRAITH_SHOOT_INTERVAL,
    LEVIATHAN_HEAD_HP, LEVIATHAN_SEGMENT_HP, LEVIATHAN_SEGMENTS,
    LEVIATHAN_SEGMENT_SPACING, LEVIATHAN_SPEED, LEVIATHAN_BOB_AMP,
    LEVIATHAN_BOB_FREQ, LEVIATHAN_SHOOT_INTERVAL, LEVIATHAN_REGROW_TIME,
    LEVIATHAN_HEAD_SCORE, LEVIATHAN_SEGMENT_SCORE,
    ARCHON_HP, ARCHON_SCORE, ARCHON_SPEED,
    ARCHON_BEAM_WARN_TIME, ARCHON_BEAM_ACTIVE_TIME, ARCHON_BEAM_COOLDOWN,
    ARCHON_CAPTURE_TIME, ARCHON_BEAM_WIDTH, ARCHON_SHOOT_INTERVAL,
    COLOSSUS_TURRET_BASE_HP, COLOSSUS_TURRET_HP_SCALE,
    COLOSSUS_CORE_BASE_HP, COLOSSUS_CORE_HP_SCALE, COLOSSUS_SPEED,
    COLOSSUS_TURRET_SCORE, COLOSSUS_WIDTH, COLOSSUS_HEIGHT,
    HOMING_BULLET_TRACKING,
)


# ── Alien ─────────────────────────────────────────────────────────────────────

@dataclass
class Alien:
    x: float
    y: float
    colour: tuple[int, int, int]
    hp: int
    hit_flash: float = 0.0
    sprite_tier: int = 0   # 0=squid (top rows), 1=crab (mid), 2=octopus (bottom)
    # Movement pattern fields
    grid_col: int = 0
    grid_row: int = 0
    base_x: float = 0.0
    base_y: float = 0.0
    entry_progress: float = 1.0   # 0.0=off-screen, 1.0=locked in grid
    entry_start_x: float = 0.0
    entry_start_y: float = 0.0
    entry_delay: float = 0.0     # seconds before this alien starts flying in
    is_anchor: bool = False       # True for the orbital ring anchor alien
    scatter_vx: float = 0.0
    scatter_vy: float = 0.0


# ── Player bullet ─────────────────────────────────────────────────────────────

@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    colour: tuple[int, int, int]
    pierce_remaining: int = 0
    is_frag: bool = False
    frag_life: float = 0.0
    is_drone: bool = False


# ── Enemy bullet ──────────────────────────────────────────────────────────────

@dataclass
class EnemyBullet:
    x: float
    y: float
    vx: float
    vy: float


# ── Particle ──────────────────────────────────────────────────────────────────

class Particle:
    def __init__(
        self,
        x: float,
        y: float,
        colour: tuple[int, int, int],
        speed: float | None = None,
        angle: float | None = None,
        size: float = 3,
        life: float = 0.5,
    ) -> None:
        self.x, self.y = x, y
        self.colour = colour
        self.size = size
        self.life = life
        self.max_life = life
        if angle is None:
            angle = random.uniform(0, 2 * math.pi)
        if speed is None:
            speed = random.uniform(60, 200)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        alpha = max(0.0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        c = tuple(int(ch * alpha) for ch in self.colour)
        pygame.draw.circle(
            surface, c,
            (int(self.x) + offset[0], int(self.y) + offset[1]),
            r,
        )


# ── Star (parallax background) ────────────────────────────────────────────────

class Star:
    def __init__(self, layer: int) -> None:
        self.layer = layer
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        speed_mult = [0.3, 0.7, 1.2][layer]
        self.speed = 20 + speed_mult * 40
        bright = [60, 120, 200][layer]
        self.colour = (bright, bright, bright + 30)
        self.size = [1, 2, 3][layer]

    def update(self, dt: float) -> None:
        self.y += self.speed * dt
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(
        self,
        surface: pygame.Surface,
        offset: list[int],
        tint: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        col = tuple(min(255, int(c * t / 255)) for c, t in zip(self.colour, tint))
        pygame.draw.circle(
            surface, col,  # type: ignore[arg-type]
            (int(self.x) + offset[0], int(self.y) + offset[1]),
            self.size,
        )


# ── PowerUp ───────────────────────────────────────────────────────────────────

class PowerUp:
    def __init__(self, x: float, y: float, kind: str | None = None) -> None:
        self.x, self.y = x, y
        self.kind: str = kind if kind is not None else random.choice(POWERUP_TYPES)
        self.colour: tuple[int, int, int] = POWERUP_COLOURS.get(
            self.kind, (200, 200, 200))
        self.angle = 0.0
        self.alive = True

    def update(self, dt: float) -> None:
        self.y += POWERUP_FALL_SPEED * dt
        self.angle += 3 * dt
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        r = 16
        pts = [
            (cx + int(r * math.cos(self.angle + i * math.pi / 2)),
             cy + int(r * math.sin(self.angle + i * math.pi / 2)))
            for i in range(4)
        ]
        pygame.draw.polygon(surface, self.colour, pts)
        glow = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.colour, 50), (22, 22), 22)
        surface.blit(glow, (cx - 22, cy - 22))


# ── Achievement Banner ────────────────────────────────────────────────────────

class AchievementBanner:
    def __init__(self, text: str, font: pygame.font.Font) -> None:
        self.text = text
        self.font = font
        self.timer = 3.0
        self.max_timer = 3.0
        self.y_target = 50.0
        self.y = -40.0

    def update(self, dt: float, slot: int) -> bool:
        self.y_target = 15 + slot * 70
        self.y += (self.y_target - self.y) * 5 * dt
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = min(1.0, self.timer / 0.5) if self.timer < 0.5 else 1.0
        txt_surf = self.font.render(f"  {self.text}  ", True, GOLD)
        w, h = txt_surf.get_width() + 24, txt_surf.get_height() + 12
        x = WIDTH - w - 20
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(box, (20, 20, 50, int(200 * alpha)), (0, 0, w, h), border_radius=8)
        pygame.draw.rect(box, (*GOLD, int(255 * alpha)), (0, 0, w, h), 2, border_radius=8)
        box.blit(txt_surf, (12, 6))
        box.set_alpha(int(255 * alpha))
        surface.blit(box, (x, int(self.y)))


# ── Combo / Score popup ───────────────────────────────────────────────────────

class ComboPopup:
    def __init__(
        self,
        x: float,
        y: float,
        multiplier: int,
        font: pygame.font.Font,
        text: str | None = None,
    ) -> None:
        self.x, self.y = x, y
        self.text = text if text else f"x{multiplier}!"
        self.font = font
        self.timer = 0.9
        self.max_timer = 0.9

    def update(self, dt: float) -> bool:
        self.y -= 60 * dt
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        alpha = self.timer / self.max_timer
        scale = 1.0 + (1 - alpha) * 0.3
        txt = self.font.render(self.text, True, YELLOW)
        w, h = txt.get_size()
        scaled = pygame.transform.scale(txt, (int(w * scale), int(h * scale)))
        scaled.set_alpha(int(255 * alpha))
        surface.blit(
            scaled,
            (int(self.x) + offset[0] - scaled.get_width() // 2,
             int(self.y) + offset[1] - scaled.get_height() // 2),
        )


# ── UFO ───────────────────────────────────────────────────────────────────────

class UFO:
    def __init__(self) -> None:
        if random.random() < 0.5:
            self.x = -70.0
            self.vx = float(380)   # UFO_SPEED
        else:
            self.x = float(WIDTH + 70)
            self.vx = float(-380)
        self.y = float(UFO_Y)
        self.score: int = random.choice([50, 100, 150, 200, 250, 300])
        self.alive = True
        self.anim_timer = 0.0
        self.anim_frame = 0

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.anim_timer += dt
        if self.anim_timer >= 0.18:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        if self.x < -120 or self.x > WIDTH + 120:
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        pygame.draw.ellipse(surface, RED,      (cx - 42, cy - 6,  84, 24))
        pygame.draw.ellipse(surface, HOT_PINK, (cx - 22, cy - 24, 44, 22))
        pygame.draw.ellipse(surface, (*CYAN, 160), (cx - 10, cy - 20, 20, 14))
        lc = YELLOW if self.anim_frame == 0 else WHITE
        for lx in [-26, -10, 6, 22]:
            pygame.draw.circle(surface, lc, (cx + lx, cy + 6), 4)
        glow = pygame.Surface((110, 52), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*RED, 28), (0, 0, 110, 52))
        surface.blit(glow, (cx - 55, cy - 22))


# ── Barrier ───────────────────────────────────────────────────────────────────

_BARRIER_SHAPE = [
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    "XXX    XXX",
    "XX      XX",
]


class Barrier:
    def __init__(self, cx: int, y: int) -> None:
        bw, bh = BARRIER_BLOCK_W, BARRIER_BLOCK_H
        total_w = len(_BARRIER_SHAPE[0]) * bw
        total_h = len(_BARRIER_SHAPE) * bh
        ox = cx - total_w // 2
        oy = y  - total_h // 2
        # Each block: [left_x, top_y, health]
        self.blocks: list[list[int]] = []
        for row_i, row in enumerate(_BARRIER_SHAPE):
            for col_i, ch in enumerate(row):
                if ch == "X":
                    self.blocks.append([ox + col_i * bw, oy + row_i * bh, 3])
        self.last_destroyed: tuple[int, int] | None = None

    def check_bullet_hit(self, bx: float, by: float) -> bool:
        self.last_destroyed = None
        for block in self.blocks:
            if block[2] <= 0:
                continue
            if (block[0] <= bx <= block[0] + BARRIER_BLOCK_W and
                    block[1] <= by <= block[1] + BARRIER_BLOCK_H):
                block[2] -= 1
                if block[2] == 0:
                    self.last_destroyed = (
                        block[0] + BARRIER_BLOCK_W // 2,
                        block[1] + BARRIER_BLOCK_H // 2,
                    )
                return True
        return False

    @property
    def alive(self) -> bool:
        return any(b[2] > 0 for b in self.blocks)

    def regen_blocks(self) -> None:
        for b in self.blocks:
            b[2] = 3

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        for block in self.blocks:
            if block[2] <= 0:
                continue
            h = block[2]
            colour = LIME if h == 3 else YELLOW if h == 2 else RED
            rect = pygame.Rect(
                block[0] + ox, block[1] + oy,
                BARRIER_BLOCK_W - 1, BARRIER_BLOCK_H - 1,
            )
            pygame.draw.rect(surface, colour, rect)
            pygame.draw.rect(surface, WHITE, (rect.x, rect.y, rect.width, 2))


# ── Dive Bomber ───────────────────────────────────────────────────────────────

class DiveBomber:
    def __init__(self, alien: Alien) -> None:
        self.x           = alien.x
        self.y           = alien.y
        self.colour      = alien.colour
        self.sprite_tier = alien.sprite_tier
        self.start_x = alien.x
        self.start_y = alien.y
        # Preserve grid identity for return-to-formation
        self.grid_col = alien.grid_col
        self.grid_row = alien.grid_row
        self.base_x   = alien.base_x
        self.base_y   = alien.base_y
        self.phase   = "dive"   # "dive" → "return" → alive = False
        self.vx      = 0.0
        self.alive   = True
        self.returned = False
        self.anim_timer = 0.0
        self.anim_frame = 0

    def update(self, dt: float, player_x: float) -> None:
        self.anim_timer += dt
        if self.anim_timer >= 0.12:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame

        if self.phase == "dive":
            dx = player_x - self.x
            self.vx += dx * 2.2 * dt
            self.vx = max(-320, min(320, self.vx))
            self.x += self.vx * dt
            self.y += DIVE_SPEED * dt
            if self.y >= HEIGHT - 80:
                self.phase = "return"
                self.vx = 0.0
        elif self.phase == "return":
            self.x += (self.start_x - self.x) * 3.5 * dt
            self.y -= DIVE_SPEED * 0.75 * dt
            if self.y <= self.start_y:
                self.y = self.start_y
                self.returned = True
                self.alive = False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        draw_fn = draw_alien_a if self.anim_frame == 0 else draw_alien_b
        draw_fn(surface, int(self.x) + ox, int(self.y) + oy, self.colour, 1.25,
                tier=self.sprite_tier)
        trail = pygame.Surface((50, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(trail, (*self.colour, 35), (0, 0, 50, 60))
        surface.blit(trail, (int(self.x) + ox - 25, int(self.y) + oy - 30))


# ── Galaga Diver ──────────────────────────────────────────────────────────────

class GalagaDiver:
    """Coordinated Galaga-style diver: follows a cubic Bezier arc toward the player."""

    def __init__(self, alien: Alien, player_x: float, player_y: float,
                 loop_side: int) -> None:
        self.x           = alien.x
        self.y           = alien.y
        self.colour      = alien.colour
        self.sprite_tier = alien.sprite_tier
        self.alive       = True
        self.t           = 0.0
        self.anim_timer  = 0.0
        self.anim_frame  = 0
        # Cubic Bezier control points:
        # P0 = alien start, P1 = arc out to side, P2 = swoop toward player,
        # P3 = near player
        px0, py0 = alien.x, alien.y
        px3, py3 = player_x, player_y - 60
        px1 = alien.x + loop_side * 480
        py1 = alien.y + 120
        px2 = player_x + loop_side * 220
        py2 = player_y - 320
        self._p        = [(px0, py0), (px1, py1), (px2, py2), (px3, py3)]
        self._duration = 2.5

    @staticmethod
    def _bezier(t: float, pts: list) -> tuple[float, float]:
        p0, p1, p2, p3 = pts
        u  = 1.0 - t
        bx = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
        by = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
        return bx, by

    def update(self, dt: float) -> None:
        self.anim_timer += dt
        if self.anim_timer >= 0.12:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        self.t = min(1.0, self.t + dt / self._duration)
        self.x, self.y = self._bezier(self.t, self._p)
        if self.t >= 1.0:
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        draw_fn = draw_alien_a if self.anim_frame == 0 else draw_alien_b
        draw_fn(surface, int(self.x) + ox, int(self.y) + oy, self.colour, 1.25,
                tier=self.sprite_tier)
        trail = pygame.Surface((50, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(trail, (*self.colour, 35), (0, 0, 50, 60))
        surface.blit(trail, (int(self.x) + ox - 25, int(self.y) + oy - 30))


# ── Boss base + variants ───────────────────────────────────────────────────────

class _BossBase:
    """
    Shared scaffolding for every boss variant.

    Subclasses MUST set self.max_hp before calling super().__init__() if they
    need a custom value, or rely on the default scaling formula.
    """

    x:         float
    y:         float
    alive:     bool
    hp:        int
    max_hp:    int
    hit_flash: float
    wave_timer: float
    anim_timer: float
    anim_frame: int
    shoot_timer: float
    vx:        float
    base_y:    float

    def _common_init(self, wave: int, hp_extra: int = 0) -> None:
        self.x          = float(WIDTH // 2)
        self.y          = 195.0
        self.base_y     = 195.0
        self.wave_timer = 0.0
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.hit_flash  = 0.0
        self.alive      = True
        boss_tier       = max(1, wave // BOSS_WAVE_INTERVAL)
        self.max_hp     = 12 + boss_tier * 8 + hp_extra
        self.hp         = self.max_hp
        self.vx         = float(min(180 + boss_tier * 25, 360))
        self.shoot_timer = 1.8

    def is_phase2(self) -> bool:
        return self.hp <= self.max_hp // 2

    def is_hittable(self, bx: float = 0.0, by: float = 0.0) -> bool:
        """Override in subclasses that have conditional invulnerability."""
        return True

    def _tick_common(self, dt: float) -> None:
        self.wave_timer += dt
        self.anim_timer += dt
        if self.anim_timer >= 0.20:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.shoot_timer -= dt

    def _move_horizontal(self, dt: float, margin: float = 140.0) -> None:
        self.x += self.vx * dt
        self.y  = self.base_y + 40.0 * math.sin(self.wave_timer * 1.6)
        if self.x > WIDTH - margin or self.x < margin:
            self.vx *= -1

    def take_hit(self) -> bool:
        """Returns True if this hit killed the boss."""
        self.hp -= 1
        self.hit_flash = 0.14
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def _draw_hp_bar(
        self,
        surface: pygame.Surface,
        cx: int,
        cy: int,
        bar_w: int = 220,
        bar_h: int = 12,
        bar_y_offset: int = -92,
    ) -> None:
        hp_frac = self.hp / self.max_hp
        bar_col = LIME if hp_frac > 0.5 else YELLOW if hp_frac > 0.25 else RED
        bx      = cx - bar_w // 2
        by_     = cy + bar_y_offset
        pygame.draw.rect(surface, (25, 25, 25), (bx, by_, bar_w, bar_h),              border_radius=4)
        pygame.draw.rect(surface, bar_col,      (bx, by_, int(bar_w * hp_frac), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE,         (bx, by_, bar_w, bar_h), 1,           border_radius=4)


class Mothership(_BossBase):
    """
    Classic flying saucer — the default boss.  Swoops horizontally and
    accelerates into phase 2 with spokes and a faster fire rate.
    """

    def __init__(self, wave: int) -> None:
        self._common_init(wave)

    def update(self, dt: float) -> None:
        self._tick_common(dt)
        self._move_horizontal(dt)

    def should_shoot(self) -> bool:
        interval = 0.42 if self.is_phase2() else 0.72
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.08, 0.08)
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy   = offset
        cx, cy   = int(self.x) + ox, int(self.y) + oy
        flashing = self.hit_flash > 0
        phase2   = self.is_phase2()

        glow_col = (255, 50, 50, 22) if phase2 else (255, 0, 255, 18)
        glow = pygame.Surface((280, 140), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, glow_col, (0, 0, 280, 140))
        surface.blit(glow, (cx - 140, cy - 70))

        hull_col = WHITE if flashing else (RED if phase2 else HOT_PINK)
        dome_col = WHITE if flashing else (ORANGE if phase2 else HOT_PINK)

        if phase2:
            for spoke in range(8):
                a  = math.radians(spoke * 45 + self.wave_timer * 55)
                sx = cx + int(118 * math.cos(a))
                sy = cy + int(30  * math.sin(a))
                pygame.draw.line(surface, (*RED, 120), (cx, cy), (sx, sy), 1)  # type: ignore[arg-type]

        pygame.draw.ellipse(surface, hull_col, (cx - 110, cy - 22, 220, 60))
        pygame.draw.ellipse(surface, BG,       (cx - 88,  cy - 12, 176, 40))
        pygame.draw.ellipse(surface, hull_col, (cx - 88,  cy - 12, 176, 40), 2)
        pygame.draw.ellipse(surface, dome_col, (cx - 60,  cy - 68, 120, 62))
        pygame.draw.ellipse(surface, CYAN,     (cx - 30,  cy - 60,  60, 38))
        glass_glow = pygame.Surface((60, 38), pygame.SRCALPHA)
        pygame.draw.ellipse(glass_glow, (*CYAN, 70), (0, 0, 60, 38))
        surface.blit(glass_glow, (cx - 30, cy - 60))

        lc = YELLOW if self.anim_frame == 0 else ORANGE
        for lx in [-80, -52, -24, 4, 32, 60, 80]:
            pygame.draw.circle(surface, lc, (cx + lx, cy + 22), 6)

        self._draw_hp_bar(surface, cx, cy)


class Dreadnought(_BossBase):
    """
    Armoured warship with a rotating energy shield.

    The shield has a single gap — bullets must pass through it to deal damage.
    The gap slowly narrows in phase 2.
    """

    _SHIELD_RADIUS    = 105
    _SHIELD_THICKNESS = 6
    _SHIELD_COLOUR    = (80, 180, 255)

    def __init__(self, wave: int) -> None:
        self._common_init(wave, hp_extra=10)
        self.shield_angle  = 0.0          # current gap start (radians)
        self.shield_speed  = 1.1          # rad/s rotation
        boss_tier          = max(1, wave // BOSS_WAVE_INTERVAL)
        self.gap_size      = math.pi * 0.45 - boss_tier * 0.02  # narrows with tier

    # ------------------------------------------------------------------
    def is_hittable(self, bx: float = 0.0, by: float = 0.0) -> bool:
        """Bullet can hit only when its angle falls inside the shield gap."""
        angle = math.atan2(by - self.y, bx - self.x) % (2 * math.pi)
        gap_start = self.shield_angle % (2 * math.pi)
        gap_end   = (gap_start + self.gap_size) % (2 * math.pi)
        if gap_start <= gap_end:
            return gap_start <= angle <= gap_end
        return angle >= gap_start or angle <= gap_end   # wraps past 2π

    def update(self, dt: float) -> None:
        self._tick_common(dt)
        # Faster, tighter movement than Mothership
        self.x += self.vx * dt
        self.y  = self.base_y + 28.0 * math.sin(self.wave_timer * 2.2)
        if self.x > WIDTH - 140 or self.x < 140:
            self.vx *= -1
        # Shield rotates; phase 2 spins faster
        speed = self.shield_speed * (1.6 if self.is_phase2() else 1.0)
        self.shield_angle = (self.shield_angle + speed * dt) % (2 * math.pi)

    def should_shoot(self) -> bool:
        # Dreadnought is a slow but relentless shooter — fires in bursts
        interval = 0.55 if self.is_phase2() else 0.90
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.05, 0.05)
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy   = offset
        cx, cy   = int(self.x) + ox, int(self.y) + oy
        flashing = self.hit_flash > 0
        phase2   = self.is_phase2()

        # Glow
        glow_col = (50, 100, 255, 20) if not phase2 else (50, 200, 255, 28)
        glow = pygame.Surface((300, 150), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, glow_col, (0, 0, 300, 150))
        surface.blit(glow, (cx - 150, cy - 75))

        # Hull — heavy rectangular saucer shape
        hull_col = WHITE if flashing else (CYAN if not phase2 else (180, 240, 255))
        pygame.draw.ellipse(surface, hull_col,     (cx - 118, cy - 18, 236, 52))
        pygame.draw.ellipse(surface, (20, 30, 60), (cx - 98,  cy - 10, 196, 36))
        pygame.draw.ellipse(surface, hull_col,     (cx - 98,  cy - 10, 196, 36), 2)
        # Dome
        pygame.draw.ellipse(surface, hull_col,     (cx - 46, cy - 62, 92, 54))
        pygame.draw.ellipse(surface, BLUE,         (cx - 30, cy - 54, 60, 38))

        # Exhaust lights
        lc = CYAN if self.anim_frame == 0 else BLUE
        for lx in range(-90, 95, 24):
            pygame.draw.circle(surface, lc, (cx + lx, cy + 24), 5)

        # Rotating shield ring (drawn as arc segments, leaving the gap open)
        r     = self._SHIELD_RADIUS
        sh_col = (200, 240, 255) if not phase2 else (255, 255, 255)
        # Full circle minus gap
        gap_rad   = self.gap_size
        arc_start = (self.shield_angle + gap_rad) % (2 * math.pi)
        arc_end   = self.shield_angle
        # pygame.draw.arc uses screen coords (y-down), angles anti-clockwise
        # We draw many tiny line segments for a smooth ring
        segments   = 64
        prev: tuple[int, int] | None = None
        for i in range(segments + 1):
            frac  = i / segments
            a     = arc_start + (2 * math.pi - gap_rad) * frac
            # Skip segment if it's in the gap region
            angle_in_gap = (a - self.shield_angle) % (2 * math.pi) < gap_rad
            if angle_in_gap:
                prev = None
                continue
            px = cx + int(r * math.cos(a))
            py = cy + int(r * 0.38 * math.sin(a))  # elliptical
            if prev is not None:
                pygame.draw.line(surface, sh_col, prev, (px, py), self._SHIELD_THICKNESS)
            prev = (px, py)

        # Gap indicator arrow — bright accent at gap centre
        gap_mid = (self.shield_angle + gap_rad / 2) % (2 * math.pi)
        arrow_x = cx + int((r - 14) * math.cos(gap_mid))
        arrow_y = cy + int((r - 14) * 0.38 * math.sin(gap_mid))
        pygame.draw.circle(surface, YELLOW, (arrow_x, arrow_y), 4)

        self._draw_hp_bar(surface, cx, cy, bar_y_offset=-98)


class SwarmQueen(_BossBase):
    """
    Organic hive-queen.  At 50 % HP she signals her swarm, spawning a fresh
    wave of small alien drones that rejoin the enemy grid.

    The game layer checks ``self.boss.spawn_pending`` each frame and, when
    True, calls ``self.boss.clear_spawn()`` after processing the spawn.
    """

    _SPAWN_HP_THRESHOLD = 0.50  # fraction of max_hp

    def __init__(self, wave: int) -> None:
        self._common_init(wave, hp_extra=4)
        self.spawn_pending  = False
        self._spawned_once  = False
        self.pulse_timer    = 0.0   # drives the organic pulsing effect

    def clear_spawn(self) -> None:
        self.spawn_pending = False
        self._spawned_once = True

    def take_hit(self) -> bool:
        killed = super().take_hit()
        if (
            not self._spawned_once
            and not self.spawn_pending
            and self.hp / self.max_hp <= self._SPAWN_HP_THRESHOLD
        ):
            self.spawn_pending = True
        return killed

    def update(self, dt: float) -> None:
        self._tick_common(dt)
        self.pulse_timer += dt
        self._move_horizontal(dt, margin=160.0)

    def should_shoot(self) -> bool:
        # Rapid spread pattern — fires frequently in phase 2
        interval = 0.38 if self.is_phase2() else 0.65
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.05, 0.05)
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy   = offset
        cx, cy   = int(self.x) + ox, int(self.y) + oy
        flashing = self.hit_flash > 0
        phase2   = self.is_phase2()

        pulse = 0.5 + 0.5 * math.sin(self.pulse_timer * 4.0)

        # Organic glow
        glow_r = int(28 + 12 * pulse)
        glow_a = 20 + int(12 * pulse)
        glow_col = (200, 50, 255, glow_a)
        glow = pygame.Surface((300, 150), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, glow_col, (0, 0, 300, 150))
        surface.blit(glow, (cx - 150, cy - 75))

        body_col  = WHITE if flashing else (HOT_PINK if not phase2 else RED)
        inner_col = WHITE if flashing else (LIME if not phase2 else ORANGE)

        # Main body — wide organic oval
        pygame.draw.ellipse(surface, body_col,  (cx - 105, cy - 20, 210, 58))
        pygame.draw.ellipse(surface, (30, 10, 30),(cx - 86,  cy - 12, 172, 40))
        pygame.draw.ellipse(surface, body_col,  (cx - 86,  cy - 12, 172, 40), 2)

        # Dome with pulsing core
        pygame.draw.ellipse(surface, body_col,  (cx - 52, cy - 64, 104, 58))
        core_r = 20 + int(8 * pulse)
        pygame.draw.circle(surface, inner_col, (cx, cy - 40), core_r)

        # Tendril legs (8 of them, wave with pulse)
        for i in range(8):
            base_a = math.pi * i / 4
            a      = base_a + 0.3 * math.sin(self.pulse_timer * 3 + base_a)
            tx     = cx + int(102 * math.cos(a))
            ty     = cy + int(28  * math.sin(a))
            pygame.draw.line(surface, body_col, (cx, cy + 18), (tx, ty), 2)
            pygame.draw.circle(surface, inner_col, (tx, ty), 4)

        # Lights
        lc = HOT_PINK if self.anim_frame == 0 else LIME
        for lx in range(-78, 82, 20):
            pygame.draw.circle(surface, lc, (cx + lx, cy + 26), 5)

        # Spawn-pending warning flash
        if self.spawn_pending:
            warn_a = int(128 + 127 * math.sin(self.pulse_timer * 14))
            warn_surf = pygame.Surface((240, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(warn_surf, (*LIME, warn_a), (0, 0, 240, 60))
            surface.blit(warn_surf, (cx - 120, cy - 30))

        self._draw_hp_bar(surface, cx, cy, bar_y_offset=-96)


class Phantom(_BossBase):
    """
    Cloaking boss — alternates between visible and invisible phases.

    While cloaked, bullets pass straight through (is_hittable returns False).
    The boss flickers briefly before vanishing as a warning to the player.
    """

    # Phase durations (seconds)
    _VISIBLE_TIME  = 3.0   # buffed: was 3.8
    _HIDDEN_TIME   = 2.6
    _FLICKER_TIME  = 0.6   # at the end of visible phase — rapid flicker warning

    def __init__(self, wave: int) -> None:
        self._common_init(wave, hp_extra=2)
        self._phase_timer  = 0.0
        self._visible      = True
        self._flicker_tick = 0.0
        self.decoys_spawned = False  # Phase 2 decoys

    @property
    def visual_alpha(self) -> int:
        """0-255 alpha for rendering the boss body."""
        if self._visible:
            time_left = self._VISIBLE_TIME - self._phase_timer
            if time_left < self._FLICKER_TIME:
                # Rapid flicker warning
                return 255 if int(self._flicker_tick * 10) % 2 == 0 else 60
            return 255
        # Hidden phase — ghost silhouette only
        return 22

    def is_hittable(self, bx: float = 0.0, by: float = 0.0) -> bool:
        return self._visible and self.visual_alpha > 128

    def update(self, dt: float) -> None:
        self._tick_common(dt)
        self._move_horizontal(dt)
        self._phase_timer  += dt
        self._flicker_tick += dt
        threshold = self._VISIBLE_TIME if self._visible else self._HIDDEN_TIME
        # Phase 2: shorter hidden windows keep pressure on
        if not self._visible and self.is_phase2():
            threshold = max(1.4, self._HIDDEN_TIME - 0.6)
        if self._phase_timer >= threshold:
            self._phase_timer = 0.0
            self._visible     = not self._visible

    def should_shoot(self) -> bool:
        # Phantom only shoots while visible
        if not self._visible:
            return False
        interval = 0.50 if self.is_phase2() else 0.80
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.07, 0.07)
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        alpha = self.visual_alpha
        if alpha < 5:
            return

        ox, oy   = offset
        cx, cy   = int(self.x) + ox, int(self.y) + oy
        flashing = self.hit_flash > 0
        phase2   = self.is_phase2()

        # Render onto an alpha surface so the whole sprite can fade
        ghost = pygame.Surface((300, 200), pygame.SRCALPHA)
        gcx, gcy = 150, 100    # centre within the ghost surface

        glow_col = (180, 50, 255, int(18 * alpha / 255))
        pygame.draw.ellipse(ghost, glow_col, (0, 30, 300, 140))

        hull_a   = alpha
        hull_col = (255, 255, 255, hull_a) if flashing else (
            (200, 80, 255, hull_a) if not phase2 else (255, 100, 100, hull_a)
        )
        dome_col = hull_col

        pygame.draw.ellipse(ghost, hull_col, (gcx - 110, gcy - 18, 220, 52))
        pygame.draw.ellipse(ghost, (0, 0, 0, hull_a), (gcx - 90, gcy - 10, 180, 36))
        pygame.draw.ellipse(ghost, hull_col,           (gcx - 90, gcy - 10, 180, 36), 2)
        pygame.draw.ellipse(ghost, dome_col,           (gcx - 52, gcy - 62, 104, 56))
        pygame.draw.ellipse(ghost, (100, 0, 200, hull_a), (gcx - 28, gcy - 52, 56, 36))

        # Lights
        lc = (200, 100, 255, hull_a) if self.anim_frame == 0 else (255, 200, 100, hull_a)
        for lx in range(-78, 82, 22):
            pygame.draw.circle(ghost, lc, (gcx + lx, gcy + 22), 5)

        surface.blit(ghost, (cx - 150, cy - 100))

        # Always draw HP bar at full opacity so the player has feedback
        self._draw_hp_bar(surface, cx, cy, bar_y_offset=-102)


# ── Harbinger Elite Squadron ──────────────────────────────────────────────────

class _HarbingerBase:
    """Shared functionality for Harbinger-class enemies."""

    kind: str = "harbinger"

    def __init__(self, x: float, y: float, hp: int, score: int) -> None:
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.score = score
        self.alive = True
        self.flash_timer = 0.0
        self.spawn_timer = 1.0  # brief invuln on spawn

    def take_damage(self, dmg: int = 1) -> bool:
        if self.spawn_timer > 0:
            return False
        self.hp -= dmg
        self.flash_timer = 0.12
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def _update_base(self, dt: float) -> None:
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt

    def _draw_hp_bar(self, surface: pygame.Surface, cx: int, cy: int,
                     bar_w: int = 40, bar_y_offset: int = -30) -> None:
        ratio = max(0, self.hp / self.max_hp)
        bx = cx - bar_w // 2
        by = cy + bar_y_offset
        pygame.draw.rect(surface, (60, 60, 60), (bx, by, bar_w, 4))
        col = LIME if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        pygame.draw.rect(surface, col, (bx, by, int(bar_w * ratio), 4))


class Sentinel(_HarbingerBase):
    """Rotating-shield elite. Player must shoot through the gap."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, SENTINEL_HP, SENTINEL_SCORE)
        self.speed = SENTINEL_SPEED
        self.direction = 1
        self.shield_angle = 0.0
        self.shield_gap = SENTINEL_SHIELD_GAP
        self.shield_speed = SENTINEL_SHIELD_SPEED
        self.shield_radius = SENTINEL_SHIELD_RADIUS
        self.shoot_timer = SENTINEL_SHOOT_INTERVAL
        self.size = 24  # collision radius

    def update(self, dt: float) -> list:
        self._update_base(dt)
        # Horizontal patrol
        self.x += self.speed * self.direction * dt
        if self.x < 60:
            self.x = 60
            self.direction = 1
        elif self.x > WIDTH - 60:
            self.x = WIDTH - 60
            self.direction = -1

        # Shield rotation speeds up below 50% HP
        spd = SENTINEL_SHIELD_SPEED_P2 if self.hp < self.max_hp * 0.5 else SENTINEL_SHIELD_SPEED
        self.shield_angle += spd * dt

        # Shooting
        bullets = []
        self.shoot_timer -= dt
        if self.shoot_timer <= 0 and self.spawn_timer <= 0:
            self.shoot_timer = SENTINEL_SHOOT_INTERVAL
            # Triple-shot spread
            for angle_off in (-0.3, 0.0, 0.3):
                bx = self.x + math.sin(angle_off) * 10
                bullets.append(EnemyBullet(
                    x=bx, y=self.y + 20,
                    vx=math.sin(angle_off) * 80,
                    vy=220 + angle_off * 40,
                ))
        return bullets

    def is_shot_blocked_by_shield(self, bx: float, by: float) -> bool:
        """Check if a player bullet at (bx, by) hits the shield instead of the body."""
        dx = bx - self.x
        dy = by - self.y
        dist = math.hypot(dx, dy)
        if dist < self.size:
            return False  # inside shield = hits body
        if abs(dist - self.shield_radius) > 12:
            return False  # too far from shield ring
        # Check if the bullet angle is outside the gap
        bullet_angle = math.atan2(dy, dx)
        gap_center = self.shield_angle
        diff = (bullet_angle - gap_center + math.pi) % (2 * math.pi) - math.pi
        return abs(diff) > self.shield_gap / 2

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        flashing = self.flash_timer > 0
        body_col = WHITE if flashing else (0, 200, 255)

        # Body - hexagonal shape
        pts = []
        for i in range(6):
            a = math.pi / 3 * i - math.pi / 6
            pts.append((cx + int(self.size * math.cos(a)),
                         cy + int(self.size * math.sin(a))))
        pygame.draw.polygon(surface, body_col, pts)
        pygame.draw.polygon(surface, CYAN, pts, 2)

        # Shield ring with gap
        sr = self.shield_radius
        gap_half = self.shield_gap / 2
        start_a = self.shield_angle + gap_half
        end_a = self.shield_angle + 2 * math.pi - gap_half
        # Draw shield as arc segments
        steps = 32
        shield_pts = []
        for i in range(steps + 1):
            t = start_a + (end_a - start_a) * i / steps
            shield_pts.append((cx + int(sr * math.cos(t)),
                               cy + int(sr * math.sin(t))))
        if len(shield_pts) > 1:
            pygame.draw.lines(surface, (0, 180, 255), False, shield_pts, 3)

        # Spawn shimmer
        if self.spawn_timer > 0:
            alpha = int(180 * self.spawn_timer)
            s = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 200, 255, alpha), (30, 30), 30)
            surface.blit(s, (cx - 30, cy - 30))

        self._draw_hp_bar(surface, cx, cy)


class Wraith(_HarbingerBase):
    """Teleporting elite. Fires homing missiles."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, WRAITH_HP, WRAITH_SCORE)
        self.teleport_timer = WRAITH_TELEPORT_INTERVAL
        self.shimmer_timer = 0.0
        self.shimmer_dest = None  # (x, y) of next teleport destination
        self.invuln_timer = 0.0
        self.shoot_timer = WRAITH_SHOOT_INTERVAL
        self.size = 20

    def take_damage(self, dmg: int = 1) -> bool:
        if self.invuln_timer > 0:
            return False
        return super().take_damage(dmg)

    def update(self, dt: float, player_x: float, player_y: float) -> list:
        self._update_base(dt)
        missiles = []

        if self.invuln_timer > 0:
            self.invuln_timer -= dt

        # Shimmer phase: ghost visible at destination
        if self.shimmer_timer > 0:
            self.shimmer_timer -= dt
            if self.shimmer_timer <= 0:
                # Teleport!
                self.x, self.y = self.shimmer_dest
                self.shimmer_dest = None
                self.invuln_timer = WRAITH_INVULN_DURATION
        else:
            # Count down to next teleport
            self.teleport_timer -= dt
            if self.teleport_timer <= 0:
                self.teleport_timer = WRAITH_TELEPORT_INTERVAL
                self.shimmer_dest = (
                    random.uniform(60, WIDTH - 60),
                    random.uniform(60, HEIGHT * 0.45),
                )
                self.shimmer_timer = WRAITH_SHIMMER_DURATION

        # Shooting
        self.shoot_timer -= dt
        if self.shoot_timer <= 0 and self.spawn_timer <= 0 and self.shimmer_timer <= 0:
            self.shoot_timer = WRAITH_SHOOT_INTERVAL
            missiles.append(HomingMissile(
                x=self.x, y=self.y + 15,
                target_x=player_x, target_y=player_y,
            ))
        return missiles

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        flashing = self.flash_timer > 0

        # Draw shimmer ghost at destination
        if self.shimmer_dest:
            gx, gy = int(self.shimmer_dest[0]), int(self.shimmer_dest[1])
            alpha = int(120 * (1 - self.shimmer_timer / WRAITH_SHIMMER_DURATION))
            gs = pygame.Surface((50, 50), pygame.SRCALPHA)
            pygame.draw.circle(gs, (200, 0, 255, alpha), (25, 25), 20)
            surface.blit(gs, (gx - 25, gy - 25))

        # Main body - diamond shape
        col = WHITE if flashing else (200, 0, 255)
        if self.invuln_timer > 0:
            col = (100, 0, 128)  # dim while invulnerable
        pts = [(cx, cy - 22), (cx + 18, cy), (cx, cy + 22), (cx - 18, cy)]
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, HOT_PINK, pts, 2)

        # Eye
        pygame.draw.circle(surface, (255, 0, 200), (cx, cy), 5)
        pygame.draw.circle(surface, WHITE, (cx, cy), 2)

        if self.spawn_timer > 0:
            alpha = int(180 * self.spawn_timer)
            s = pygame.Surface((50, 50), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 0, 255, alpha), (25, 25), 25)
            surface.blit(s, (cx - 25, cy - 25))

        self._draw_hp_bar(surface, cx, cy)


@dataclass
class HomingMissile:
    """A homing projectile fired by a Wraith. Can be shot down (1 HP)."""
    x: float
    y: float
    target_x: float
    target_y: float
    speed: float = WRAITH_MISSILE_SPEED
    tracking: float = WRAITH_MISSILE_TRACKING
    lifetime: float = WRAITH_MISSILE_LIFETIME
    alive: bool = True
    angle: float = field(default=math.pi / 2)  # starts going down
    size: float = 6.0

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        if not self.alive:
            return
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        # Steer toward player
        desired = math.atan2(player_y - self.y, player_x - self.x)
        diff = (desired - self.angle + math.pi) % (2 * math.pi) - math.pi
        steer = max(-self.tracking * dt, min(self.tracking * dt, diff))
        self.angle += steer
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        # Off-screen check
        if self.x < -20 or self.x > WIDTH + 20 or self.y < -20 or self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        # Small triangle pointing in travel direction
        tip_x = cx + int(math.cos(self.angle) * 8)
        tip_y = cy + int(math.sin(self.angle) * 8)
        left_x = cx + int(math.cos(self.angle + 2.5) * 6)
        left_y = cy + int(math.sin(self.angle + 2.5) * 6)
        right_x = cx + int(math.cos(self.angle - 2.5) * 6)
        right_y = cy + int(math.sin(self.angle - 2.5) * 6)
        pygame.draw.polygon(surface, (255, 80, 80), [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)])
        # Trail
        tail_x = cx - int(math.cos(self.angle) * 10)
        tail_y = cy - int(math.sin(self.angle) * 10)
        pygame.draw.line(surface, (255, 150, 50), (cx, cy), (tail_x, tail_y), 2)


class LeviathanSegment:
    """One segment of a Leviathan chain."""

    def __init__(self, x: float, y: float, is_head: bool = False) -> None:
        self.x = x
        self.y = y
        self.is_head = is_head
        self.hp = LEVIATHAN_HEAD_HP if is_head else LEVIATHAN_SEGMENT_HP
        self.alive = True
        self.flash_timer = 0.0
        self.size = 16 if is_head else 12

    def take_damage(self, dmg: int = 1) -> int:
        """Returns damage actually dealt (0 if body absorbs for head protection)."""
        self.hp -= dmg
        self.flash_timer = 0.12
        if self.hp <= 0:
            self.alive = False
        return dmg

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        flashing = self.flash_timer > 0
        if self.is_head:
            col = WHITE if flashing else (0, 255, 180)
            pygame.draw.circle(surface, col, (cx, cy), self.size)
            # Eyes
            pygame.draw.circle(surface, (255, 255, 0), (cx - 5, cy - 4), 3)
            pygame.draw.circle(surface, (255, 255, 0), (cx + 5, cy - 4), 3)
            pygame.draw.circle(surface, (0, 0, 0), (cx - 5, cy - 4), 1)
            pygame.draw.circle(surface, (0, 0, 0), (cx + 5, cy - 4), 1)
        else:
            col = WHITE if flashing else (0, 200, 140)
            pygame.draw.circle(surface, col, (cx, cy), self.size)
            pygame.draw.circle(surface, (0, 140, 100), (cx, cy), self.size, 2)


class Leviathan(_HarbingerBase):
    """Multi-segment chain enemy that splits when a middle segment is hit."""

    def __init__(self, x: float, y: float, num_segments: int = LEVIATHAN_SEGMENTS) -> None:
        super().__init__(x, y, 999, 0)  # HP managed per-segment
        self.speed = LEVIATHAN_SPEED
        self.direction = 1
        self.bob_time = random.uniform(0, math.pi * 2)
        self.shoot_timer = LEVIATHAN_SHOOT_INTERVAL
        self.segments: list[LeviathanSegment] = []
        # Build chain: head first, then body
        for i in range(num_segments):
            sx = x + i * LEVIATHAN_SEGMENT_SPACING
            self.segments.append(LeviathanSegment(sx, y, is_head=(i == 0)))
        self.regrow_timers: list[float] = []  # for split halves that need new heads

    @property
    def head(self) -> LeviathanSegment | None:
        for s in self.segments:
            if s.is_head and s.alive:
                return s
        return None

    def update(self, dt: float) -> list:
        self._update_base(dt)
        bullets = []

        # Remove dead segments
        self.segments = [s for s in self.segments if s.alive]
        if not self.segments:
            self.alive = False
            return bullets

        # Flash timers
        for s in self.segments:
            if s.flash_timer > 0:
                s.flash_timer -= dt

        # Horizontal movement
        self.x += self.speed * self.direction * dt
        if self.x < 80:
            self.x = 80
            self.direction = 1
        elif self.x > WIDTH - 80:
            self.x = WIDTH - 80
            self.direction = -1

        # Sinusoidal bob
        self.bob_time += LEVIATHAN_BOB_FREQ * dt
        base_y = self.y
        for i, seg in enumerate(self.segments):
            seg.x = self.x + i * LEVIATHAN_SEGMENT_SPACING * self.direction
            seg.y = base_y + math.sin(self.bob_time + i * 0.5) * LEVIATHAN_BOB_AMP

        # Shooting from head
        head = self.head
        if head and self.spawn_timer <= 0:
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self.shoot_timer = LEVIATHAN_SHOOT_INTERVAL
                bullets.append(EnemyBullet(x=head.x, y=head.y + 18, vx=0.0, vy=200))

        return bullets

    def hit_segment(self, seg_index: int, dmg: int = 1) -> tuple[int, int]:
        """Hit a segment. Returns (score_gained, segments_killed).
        Hitting a middle segment splits the chain."""
        if seg_index < 0 or seg_index >= len(self.segments):
            return (0, 0)
        seg = self.segments[seg_index]
        if not seg.alive:
            return (0, 0)

        seg.take_damage(dmg)
        score = 0
        killed = 0
        if not seg.alive:
            score = LEVIATHAN_HEAD_SCORE if seg.is_head else LEVIATHAN_SEGMENT_SCORE
            killed = 1
        return (score, killed)

    def draw(self, surface: pygame.Surface) -> None:
        # Draw connections between segments
        alive_segs = [s for s in self.segments if s.alive]
        for i in range(len(alive_segs) - 1):
            a, b = alive_segs[i], alive_segs[i + 1]
            pygame.draw.line(surface, (0, 160, 120),
                             (int(a.x), int(a.y)), (int(b.x), int(b.y)), 3)
        # Draw each segment
        for s in alive_segs:
            s.draw(surface)
        # HP bar shows total remaining segments
        if alive_segs:
            head = alive_segs[0]
            total_hp = sum(s.hp for s in alive_segs)
            max_hp = len(alive_segs) * LEVIATHAN_SEGMENT_HP
            ratio = total_hp / max(1, max_hp)
            bx = int(head.x) - 25
            by = int(head.y) - 28
            pygame.draw.rect(surface, (60, 60, 60), (bx, by, 50, 4))
            col = LIME if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
            pygame.draw.rect(surface, col, (bx, by, int(50 * ratio), 4))


class Archon(_HarbingerBase):
    """Tractor beam elite. Can capture the player's ship for a dual-fighter reward."""

    STATE_IDLE = 0
    STATE_BEAM_WARN = 1
    STATE_BEAM_ACTIVE = 2
    STATE_COOLDOWN = 3

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, ARCHON_HP, ARCHON_SCORE)
        self.speed = ARCHON_SPEED
        self.direction = 1
        self.beam_state = self.STATE_IDLE
        self.beam_timer = ARCHON_BEAM_COOLDOWN  # start with cooldown
        self.beam_x = x  # X position of beam
        self.capture_progress = 0.0  # 0 to ARCHON_CAPTURE_TIME
        self.has_captured = False
        self.shoot_timer = ARCHON_SHOOT_INTERVAL
        self.size = 28
        self.beam_width = 8  # starts narrow during warning

    def update(self, dt: float, player_x: float, player_y: float) -> list:
        self._update_base(dt)
        bullets = []

        # Horizontal patrol
        self.x += self.speed * self.direction * dt
        if self.x < 80:
            self.x = 80
            self.direction = 1
        elif self.x > WIDTH - 80:
            self.x = WIDTH - 80
            self.direction = -1

        # Beam state machine
        self.beam_timer -= dt
        if self.beam_state == self.STATE_IDLE:
            if self.beam_timer <= 0:
                self.beam_state = self.STATE_BEAM_WARN
                self.beam_timer = ARCHON_BEAM_WARN_TIME
                self.beam_x = self.x
                self.beam_width = 8
        elif self.beam_state == self.STATE_BEAM_WARN:
            self.beam_width = 8 + (ARCHON_BEAM_WIDTH - 8) * (1 - self.beam_timer / ARCHON_BEAM_WARN_TIME)
            if self.beam_timer <= 0:
                self.beam_state = self.STATE_BEAM_ACTIVE
                self.beam_timer = ARCHON_BEAM_ACTIVE_TIME
                self.beam_width = ARCHON_BEAM_WIDTH
        elif self.beam_state == self.STATE_BEAM_ACTIVE:
            # Check if player is in beam
            if abs(player_x - self.beam_x) < self.beam_width / 2:
                self.capture_progress += dt
            else:
                self.capture_progress = max(0, self.capture_progress - dt * 0.5)
            if self.beam_timer <= 0:
                self.beam_state = self.STATE_COOLDOWN
                self.beam_timer = ARCHON_BEAM_COOLDOWN
                self.capture_progress = 0
        elif self.beam_state == self.STATE_COOLDOWN:
            if self.beam_timer <= 0:
                self.beam_state = self.STATE_IDLE
                self.beam_timer = 2.0  # short idle before next cycle

        # Shooting between beam activations
        if self.beam_state in (self.STATE_IDLE, self.STATE_COOLDOWN):
            self.shoot_timer -= dt
            if self.shoot_timer <= 0 and self.spawn_timer <= 0:
                self.shoot_timer = ARCHON_SHOOT_INTERVAL
                for angle_off in (-0.25, 0.0, 0.25):
                    bullets.append(EnemyBullet(
                        x=self.x + math.sin(angle_off) * 12,
                        y=self.y + 25,
                        vx=math.sin(angle_off) * 60,
                        vy=200,
                    ))

        return bullets

    def is_capturing(self) -> bool:
        return (self.beam_state == self.STATE_BEAM_ACTIVE and
                self.capture_progress >= ARCHON_CAPTURE_TIME)

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = int(self.x), int(self.y)
        flashing = self.flash_timer > 0
        col = WHITE if flashing else (255, 200, 0)

        # Main body - wider, imposing shape
        pts = [
            (cx, cy - 24), (cx + 28, cy - 8),
            (cx + 22, cy + 16), (cx - 22, cy + 16),
            (cx - 28, cy - 8),
        ]
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, GOLD, pts, 2)

        # Central orb
        orb_col = (255, 100, 0) if self.beam_state == self.STATE_BEAM_ACTIVE else (200, 150, 0)
        pygame.draw.circle(surface, orb_col, (cx, cy), 8)

        # Tractor beam
        if self.beam_state in (self.STATE_BEAM_WARN, self.STATE_BEAM_ACTIVE):
            bw = int(self.beam_width)
            beam_surf = pygame.Surface((bw, HEIGHT - cy), pygame.SRCALPHA)
            if self.beam_state == self.STATE_BEAM_WARN:
                alpha = int(60 + 40 * math.sin(pygame.time.get_ticks() * 0.01))
                beam_surf.fill((255, 200, 0, alpha))
            else:
                alpha = 100
                beam_surf.fill((255, 180, 0, alpha))
                # Capture progress indicator
                if self.capture_progress > 0:
                    prog = self.capture_progress / ARCHON_CAPTURE_TIME
                    inner_alpha = int(60 + 140 * prog)
                    beam_surf.fill((255, 255, 200, inner_alpha))
            surface.blit(beam_surf, (int(self.beam_x) - bw // 2, cy + 20))

        if self.spawn_timer > 0:
            alpha = int(180 * self.spawn_timer)
            s = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 200, 0, alpha), (35, 35), 35)
            surface.blit(s, (cx - 35, cy - 35))

        self._draw_hp_bar(surface, cx, cy)


# ── Colossus Boss ─────────────────────────────────────────────────────────────

class ColossusTurret:
    """A destructible turret on the Colossus boss."""

    def __init__(self, offset_x: float, offset_y: float, hp: int) -> None:
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.flash_timer = 0.0
        self.shoot_timer = random.uniform(0.5, 2.0)  # stagger initial shots
        self.x = 0.0  # world position, updated by parent
        self.y = 0.0

    def take_damage(self, dmg: int = 1) -> bool:
        self.hp -= dmg
        self.flash_timer = 0.12
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        flashing = self.flash_timer > 0
        col = WHITE if flashing else (255, 100, 50)
        pygame.draw.rect(surface, col, (cx - 10, cy - 10, 20, 20))
        pygame.draw.rect(surface, ORANGE, (cx - 10, cy - 10, 20, 20), 2)
        # Turret barrel
        pygame.draw.rect(surface, (200, 80, 40), (cx - 3, cy + 10, 6, 8))
        # Mini HP bar
        ratio = self.hp / self.max_hp
        bx, by = cx - 12, cy - 16
        pygame.draw.rect(surface, (60, 60, 60), (bx, by, 24, 3))
        bar_col = LIME if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        pygame.draw.rect(surface, bar_col, (bx, by, int(24 * ratio), 3))


class Colossus(_BossBase):
    """Endgame boss with 4 destructible turrets and an invulnerable core."""

    def __init__(self, wave: int) -> None:
        boss_tier = wave // 20
        turret_hp = COLOSSUS_TURRET_BASE_HP + boss_tier * COLOSSUS_TURRET_HP_SCALE
        core_hp = COLOSSUS_CORE_BASE_HP + boss_tier * COLOSSUS_CORE_HP_SCALE
        self._common_init(wave)
        # Override HP with Colossus-specific core HP
        self.max_hp = core_hp
        self.hp = core_hp
        self.boss_type = "Colossus"
        self.speed = COLOSSUS_SPEED
        self.direction = 1
        self.w = COLOSSUS_WIDTH
        self.h = COLOSSUS_HEIGHT
        self.core_exposed = False
        self.core_orb_timer = 0.0
        self.boss_tier = boss_tier

        # 4 turrets at corners
        hw, hh = self.w // 2, self.h // 2
        self.turrets = [
            ColossusTurret(-hw + 15, -hh + 15, turret_hp),  # top-left
            ColossusTurret(hw - 15, -hh + 15, turret_hp),   # top-right
            ColossusTurret(-hw + 15, hh - 15, turret_hp),   # bottom-left
            ColossusTurret(hw - 15, hh - 15, turret_hp),    # bottom-right
        ]

    @property
    def turrets_alive(self) -> int:
        return sum(1 for t in self.turrets if t.alive)

    def should_shoot(self) -> bool:
        return False  # Colossus handles shooting in update()

    def take_damage(self, dmg: int = 1) -> None:
        """Core only takes damage when exposed (all turrets destroyed)."""
        if not self.core_exposed:
            return
        self.hp -= dmg
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.alive = False

    def update(self, dt: float, player_x: float = 0, player_y: float = 0) -> list:
        bullets = []
        self.anim_timer += dt

        # Flash timers
        if self.hit_flash > 0:
            self.hit_flash -= dt
        for t in self.turrets:
            if t.flash_timer > 0:
                t.flash_timer -= dt

        # Movement
        self.x += self.speed * self.direction * dt
        left_bound = self.w // 2 + 20
        right_bound = WIDTH - self.w // 2 - 20
        if self.x < left_bound:
            self.x = left_bound
            self.direction = 1
        elif self.x > right_bound:
            self.x = right_bound
            self.direction = -1

        # Update turret world positions
        for t in self.turrets:
            t.x = self.x + t.offset_x
            t.y = self.y + t.offset_y

        # Check if core is exposed
        if not self.core_exposed and self.turrets_alive == 0:
            self.core_exposed = True
            self.y -= 20  # retreat upward slightly

        alive_count = self.turrets_alive

        # Turret shooting based on phase
        for t in self.turrets:
            if not t.alive:
                continue
            t.shoot_timer -= dt
            if t.shoot_timer <= 0:
                if alive_count == 4:
                    # Crossfire: aimed at player, staggered
                    t.shoot_timer = 2.0
                    dx = player_x - t.x
                    dy = player_y - t.y
                    dist = max(1, math.hypot(dx, dy))
                    bullets.append(EnemyBullet(
                        x=t.x, y=t.y + 12,
                        vx=dx / dist * 180,
                        vy=dy / dist * 180,
                    ))
                elif alive_count == 3:
                    # Sweeping beam: fire in arcs
                    t.shoot_timer = 1.5
                    sweep_angle = math.sin(self.anim_timer * 2) * 0.8
                    bullets.append(EnemyBullet(
                        x=t.x, y=t.y + 12,
                        vx=math.sin(sweep_angle) * 200,
                        vy=200,
                    ))
                elif alive_count == 2:
                    # Rapid aimed
                    t.shoot_timer = 1.0
                    dx = player_x - t.x
                    dy = player_y - t.y
                    dist = max(1, math.hypot(dx, dy))
                    bullets.append(EnemyBullet(
                        x=t.x, y=t.y + 12,
                        vx=dx / dist * 220,
                        vy=dy / dist * 220,
                    ))
                elif alive_count == 1:
                    # Desperate spiral
                    t.shoot_timer = 0.3
                    spiral_a = self.anim_timer * 4
                    bullets.append(EnemyBullet(
                        x=t.x, y=t.y + 12,
                        vx=math.sin(spiral_a) * 160,
                        vy=160,
                    ))

        # Core shooting when exposed
        if self.core_exposed:
            self.core_orb_timer -= dt
            if self.core_orb_timer <= 0:
                self.core_orb_timer = 2.0
                dx = player_x - self.x
                bullets.append(EnemyBullet(
                    x=self.x, y=self.y + 20,
                    vx=dx * 0.3,
                    vy=120,
                ))

        return bullets

    def draw(self, surface: pygame.Surface, offset: list[int] | None = None) -> None:
        cx, cy = int(self.x), int(self.y)
        hw, hh = self.w // 2, self.h // 2
        flashing = self.hit_flash > 0

        # Main hull
        hull_col = WHITE if flashing else (100, 100, 120)
        hull_rect = (cx - hw, cy - hh, self.w, self.h)
        pygame.draw.rect(surface, hull_col, hull_rect, border_radius=8)
        pygame.draw.rect(surface, (160, 160, 180), hull_rect, 3, border_radius=8)

        # Armour plates
        for plate_y in range(-hh + 20, hh - 10, 25):
            pygame.draw.line(surface, (80, 80, 100),
                             (cx - hw + 10, cy + plate_y),
                             (cx + hw - 10, cy + plate_y), 1)

        # Core
        if self.core_exposed:
            pulse = int(8 + 4 * math.sin(self.anim_timer * 5))
            pygame.draw.circle(surface, (255, 50, 50), (cx, cy), pulse)
            pygame.draw.circle(surface, (255, 200, 200), (cx, cy), pulse, 2)
        else:
            pygame.draw.circle(surface, (60, 60, 80), (cx, cy), 12)
            pygame.draw.circle(surface, (100, 100, 130), (cx, cy), 12, 2)

        # Turrets
        for t in self.turrets:
            t.draw(surface)

        # Destroyed turret sparks
        for t in self.turrets:
            if not t.alive:
                tx, ty = int(self.x + t.offset_x), int(self.y + t.offset_y)
                if random.random() < 0.3:
                    spark_col = random.choice([(255, 200, 50), (255, 100, 0), (200, 200, 200)])
                    sx = tx + random.randint(-8, 8)
                    sy = ty + random.randint(-8, 8)
                    pygame.draw.circle(surface, spark_col, (sx, sy), random.randint(1, 3))

        # HP bar (shows core HP when exposed, otherwise shows turret count)
        bar_y = cy - hh - 14
        bar_w = 80
        bx = cx - bar_w // 2
        if self.core_exposed:
            ratio = self.hp / self.max_hp
            pygame.draw.rect(surface, (60, 60, 60), (bx, bar_y, bar_w, 6))
            col = RED
            pygame.draw.rect(surface, col, (bx, bar_y, int(bar_w * ratio), 6))
        else:
            # Show turret count as segmented bar
            seg_w = bar_w // 4
            for i, t in enumerate(self.turrets):
                sx = bx + i * seg_w
                col = ORANGE if t.alive else (40, 40, 40)
                pygame.draw.rect(surface, col, (sx + 1, bar_y, seg_w - 2, 6))


# ── Weighted Power-Up Selection ───────────────────────────────────────────────

class WeightedPowerUp(PowerUp):
    """Power-up created with weighted random type selection."""

    @staticmethod
    def weighted_random_type(wave: int) -> str:
        weights = POWERUP_WEIGHTS_LATE if wave >= 35 else POWERUP_WEIGHTS_EARLY
        types = list(weights.keys())
        w = list(weights.values())
        return random.choices(types, weights=w, k=1)[0]


# ── Solar Flare (Sector IV Hazard) ───────────────────────────────────────────

class SolarFlare:
    """Environmental hazard for Sector IV. A horizontal beam sweeps a Y-lane."""

    STATE_IDLE = 0
    STATE_WARNING = 1
    STATE_ACTIVE = 2

    def __init__(self) -> None:
        self.state = self.STATE_IDLE
        self.timer = 15.0  # first flare after 15s
        self.target_y = 0.0
        self.warn_duration = 2.0
        self.active_duration = 0.5

    def reset(self) -> None:
        self.state = self.STATE_IDLE
        self.timer = 15.0

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.state == self.STATE_IDLE:
            if self.timer <= 0:
                self.state = self.STATE_WARNING
                self.timer = self.warn_duration
                self.target_y = random.uniform(150, HEIGHT - 100)
        elif self.state == self.STATE_WARNING:
            if self.timer <= 0:
                self.state = self.STATE_ACTIVE
                self.timer = self.active_duration
        elif self.state == self.STATE_ACTIVE:
            if self.timer <= 0:
                self.state = self.STATE_IDLE
                self.timer = 15.0

    def is_hitting(self, x: float, y: float, radius: float = 12) -> bool:
        """Check if a position is in the active flare beam."""
        if self.state != self.STATE_ACTIVE:
            return False
        return abs(y - self.target_y) < 20 + radius

    def draw(self, surface: pygame.Surface) -> None:
        if self.state == self.STATE_IDLE:
            return
        ty = int(self.target_y)
        if self.state == self.STATE_WARNING:
            # Orange glow line
            progress = 1 - self.timer / self.warn_duration
            alpha = int(40 + 80 * progress)
            warn_surf = pygame.Surface((WIDTH, 20), pygame.SRCALPHA)
            warn_surf.fill((255, 150, 0, alpha))
            surface.blit(warn_surf, (0, ty - 10))
            # Pulsing outline
            if int(progress * 8) % 2 == 0:
                pygame.draw.line(surface, (255, 180, 0), (0, ty), (WIDTH, ty), 1)
        elif self.state == self.STATE_ACTIVE:
            # Full beam
            beam_surf = pygame.Surface((WIDTH, 40), pygame.SRCALPHA)
            beam_surf.fill((255, 200, 50, 180))
            surface.blit(beam_surf, (0, ty - 20))
            # Bright core
            pygame.draw.line(surface, (255, 255, 200), (0, ty), (WIDTH, ty), 4)
            # Edge glow
            for offset in (-18, -12, 12, 18):
                glow_alpha = 60
                pygame.draw.line(surface, (255, 150, 0),
                                 (0, ty + offset), (WIDTH, ty + offset), 1)


# ── Bonus Round Enemy ─────────────────────────────────────────────────────────

class BonusEnemy:
    """Non-shooting enemy that flies a Bezier path during bonus rounds."""

    def __init__(self, path_points: list[tuple[float, float]],
                 speed: float = 200, delay: float = 0.0) -> None:
        self.path = path_points  # list of (x, y) control points
        self.speed = speed
        self.delay = delay
        self.t = 0.0  # progress along path (0 to 1)
        self.alive = True
        self.active = False  # not active until delay expires
        self.x = path_points[0][0] if path_points else -50
        self.y = path_points[0][1] if path_points else -50
        self.size = 14
        self.score = 100
        self.colour = random.choice([CYAN, HOT_PINK, LIME, ORANGE, YELLOW])

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        if self.delay > 0:
            self.delay -= dt
            return
        self.active = True
        # Advance along path
        path_len = max(1, len(self.path) - 1)
        self.t += (self.speed / (path_len * 120)) * dt
        if self.t >= 1.0:
            self.alive = False
            return
        # Interpolate position along path segments
        seg = self.t * path_len
        idx = int(seg)
        frac = seg - idx
        idx = min(idx, len(self.path) - 2)
        ax, ay = self.path[idx]
        bx, by = self.path[idx + 1]
        self.x = ax + (bx - ax) * frac
        self.y = ay + (by - ay) * frac

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive or not self.active:
            return
        cx, cy = int(self.x), int(self.y)
        # Neon diamond shape
        pts = [(cx, cy - self.size), (cx + self.size, cy),
               (cx, cy + self.size), (cx - self.size, cy)]
        pygame.draw.polygon(surface, self.colour, pts)
        pygame.draw.polygon(surface, WHITE, pts, 1)
        # Trail effect
        trail_col = (*self.colour, 80) if len(self.colour) == 3 else self.colour
        ts = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(ts, trail_col if len(trail_col) == 4 else (*trail_col, 80),
                           (self.size, self.size), self.size)
        surface.blit(ts, (cx - self.size, cy - self.size))


# ── Boss factory ───────────────────────────────────────────────────────────────

def make_boss(wave: int) -> _BossBase:
    """
    Return the appropriate boss for the given wave number.

    Wave 5  → Mothership (always first encounter)
    Wave 10 → Dreadnought
    Wave 15 → SwarmQueen
    Wave 20 → Phantom
    Wave 25 → Mothership (cycle repeats, scaling with wave)
    Waves 50, 70, 90, 110... → Colossus (replaces normal rotation)
    """
    # Colossus at wave 50 and every 20 waves thereafter
    if wave >= 50 and wave % 20 == 10:
        return Colossus(wave)

    boss_number = (wave // BOSS_WAVE_INTERVAL - 1) % 4
    if boss_number == 0:
        return Mothership(wave)
    if boss_number == 1:
        return Dreadnought(wave)
    if boss_number == 2:
        return SwarmQueen(wave)
    return Phantom(wave)


# Alias kept for any external code that still imports 'Boss'
Boss = Mothership


# ── Ship Fragment (death effect) ──────────────────────────────────────────────

class ShipFragment:
    """A spinning triangular shard of the player's ship, spawned on death."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        colour: tuple[int, int, int],
        angle: float,
        rot_speed: float,
        size: float = 1.0,
    ) -> None:
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.colour = colour
        self.angle = angle
        self.rot_speed = rot_speed
        self.size = size
        self.life = 1.0
        self.max_life = 1.0

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 240 * dt   # gentle gravity
        self.vx *= 0.98
        self.angle += self.rot_speed * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        alpha = max(0.0, self.life / self.max_life)
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        s = 14 * self.size
        # Equilateral-ish triangle in local space
        local_pts = [
            (0.0,       -s),
            ( s * 0.8,   s * 0.6),
            (-s * 0.8,   s * 0.6),
        ]
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        pts = []
        for px, py in local_pts:
            rx = px * ca - py * sa
            ry = px * sa + py * ca
            pts.append((cx + int(rx), cy + int(ry)))
        col = tuple(max(0, int(c * alpha)) for c in self.colour)
        if alpha > 0.05 and len(pts) == 3:
            pygame.draw.polygon(surface, col, pts)   # type: ignore[arg-type]


# ── Pixel-art sprite patterns ─────────────────────────────────────────────────
#
# Each pattern is a tuple of 8 strings, each exactly 11 characters wide.
# '#' = filled pixel  ' ' = transparent
# Sprites are rendered via draw_sprite() which scales each pixel to pixel_size².
# There are 3 tiers matching the classic Space Invaders row layout:
#   tier 0 — Squid  (top 2 rows,  high score)
#   tier 1 — Crab   (middle rows, mid  score)
#   tier 2 — Octopus(bottom rows, base score)

SPRITE_SQUID_A: tuple[str, ...] = (
    "   ## ##   ",
    "  #######  ",
    " ######### ",
    "## ## ## ##",
    "###########",
    "  ## # ##  ",
    " #  # #  # ",
    "#  #   #  #",
)
SPRITE_SQUID_B: tuple[str, ...] = (
    "   ## ##   ",
    "  #######  ",
    " ######### ",
    "## ## ## ##",
    "###########",
    "  ## # ##  ",
    "##  # #  ##",
    " #       # ",
)

SPRITE_CRAB_A: tuple[str, ...] = (
    "#         #",
    " ##  #  ## ",
    " ######### ",
    "###  #  ###",
    " ######### ",
    "  #  #  #  ",
    " ## ### ## ",
    "#  #   #  #",
)
SPRITE_CRAB_B: tuple[str, ...] = (
    "#         #",
    " ##  #  ## ",
    " ######### ",
    "###  #  ###",
    " ######### ",
    "  #  #  #  ",
    "## ### ### ",
    "  #   #   #",
)

SPRITE_OCTOPUS_A: tuple[str, ...] = (
    "  ## # ##  ",
    " ######### ",
    "## #   # ##",
    " ######### ",
    "  ## # ##  ",
    " # # # # # ",
    "# #  #  # #",
    " #       # ",
)
SPRITE_OCTOPUS_B: tuple[str, ...] = (
    "  ## # ##  ",
    " ######### ",
    "## #   # ##",
    " ######### ",
    "  ## # ##  ",
    " # # # # # ",
    "  # # # #  ",
    "#  #   #  #",
)

# Lookup: tier → (frame_a, frame_b)
_ALIEN_SPRITES: dict[int, tuple[tuple[str, ...], tuple[str, ...]]] = {
    0: (SPRITE_SQUID_A,   SPRITE_SQUID_B),
    1: (SPRITE_CRAB_A,    SPRITE_CRAB_B),
    2: (SPRITE_OCTOPUS_A, SPRITE_OCTOPUS_B),
}

_PIXEL_SIZE = 4   # screen pixels per sprite "pixel"


def draw_sprite(
    surface: pygame.Surface,
    x: int,
    y: int,
    colour: tuple[int, int, int],
    pattern: tuple[str, ...],
    pixel_size: int = _PIXEL_SIZE,
    size_mult: float = 1.0,
) -> None:
    """
    Render a pixel-art sprite centred on (x, y).

    Each '#' in *pattern* becomes a solid square of side *pixel_size × size_mult*.
    A subtle highlight square (top-left corner, half size) is drawn at 1.4× brightness
    to give the classic CRT-lit pixel look.
    """
    ps = max(1, int(pixel_size * size_mult))
    hs = max(1, ps // 2)            # highlight size
    rows = len(pattern)
    cols = len(pattern[0]) if pattern else 0
    off_x = x - (cols * ps) // 2
    off_y = y - (rows * ps) // 2
    hi = tuple(min(255, int(c * 1.4)) for c in colour)
    for row_idx, row_str in enumerate(pattern):
        for col_idx, ch in enumerate(row_str):
            if ch == "#":
                rx = off_x + col_idx * ps
                ry = off_y + row_idx * ps
                pygame.draw.rect(surface, colour, (rx, ry, ps, ps))
                if ps >= 3:                   # only add highlight at a readable scale
                    pygame.draw.rect(surface, hi, (rx, ry, hs, hs))  # type: ignore[arg-type]


# ── Draw helpers ──────────────────────────────────────────────────────────────

def draw_ship(
    surface: pygame.Surface,
    x: int,
    y: int,
    colour: tuple[int, int, int],
    size: float = 1.0,
) -> None:
    w, h = int(30 * size), int(36 * size)
    pts = [
        (x,           y - h),
        (x - w,       y + h // 2),
        (x - w // 3,  y),
        (x + w // 3,  y),
        (x + w,       y + h // 2),
    ]
    pygame.draw.polygon(surface, colour, pts)
    pygame.draw.circle(surface, WHITE, (x, y - int(h * 0.3)), max(1, int(4 * size)))
    t = pygame.time.get_ticks() / 1000.0
    flame_h = int((10 + 6 * math.sin(t * 15)) * size)
    flame_w = int(8 * size)
    flame_pts = [
        (x - flame_w, y + h // 2),
        (x,           y + h // 2 + flame_h),
        (x + flame_w, y + h // 2),
    ]
    flame_col = ORANGE if int(t * 20) % 2 == 0 else YELLOW
    pygame.draw.polygon(surface, flame_col, flame_pts)
    inner_h   = int(flame_h * 0.6)
    inner_w   = int(flame_w * 0.5)
    inner_pts = [
        (x - inner_w, y + h // 2),
        (x,           y + h // 2 + inner_h),
        (x + inner_w, y + h // 2),
    ]
    pygame.draw.polygon(surface, WHITE, inner_pts)
    glow_surf = pygame.Surface((int(24 * size), int(16 * size)), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_surf, (*ORANGE, 80), glow_surf.get_rect())
    surface.blit(glow_surf, (x - int(12 * size), y + h // 2 - int(4 * size)))


def draw_alien_a(
    surface: pygame.Surface,
    x: int,
    y: int,
    colour: tuple[int, int, int],
    size: float = 1.0,
    tier: int = 0,
) -> None:
    """Draw animation frame A of an alien sprite centred on (x, y)."""
    pattern = _ALIEN_SPRITES[min(tier, 2)][0]
    draw_sprite(surface, x, y, colour, pattern, size_mult=size)


def draw_alien_b(
    surface: pygame.Surface,
    x: int,
    y: int,
    colour: tuple[int, int, int],
    size: float = 1.0,
    tier: int = 0,
) -> None:
    """Draw animation frame B of an alien sprite centred on (x, y)."""
    pattern = _ALIEN_SPRITES[min(tier, 2)][1]
    draw_sprite(surface, x, y, colour, pattern, size_mult=size)
