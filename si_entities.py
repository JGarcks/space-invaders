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
    POWERUP_FALL_SPEED, POWERUP_TYPES, POWERUP_COLOURS,
    UFO_Y,
    BARRIER_BLOCK_W, BARRIER_BLOCK_H,
    DIVE_SPEED,
    BOSS_WAVE_INTERVAL,
    DIM_WHITE,
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
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.kind: str = random.choice(POWERUP_TYPES)
        self.colour: tuple[int, int, int] = POWERUP_COLOURS[self.kind]
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
    _VISIBLE_TIME  = 3.8
    _HIDDEN_TIME   = 2.6
    _FLICKER_TIME  = 0.6   # at the end of visible phase — rapid flicker warning

    def __init__(self, wave: int) -> None:
        self._common_init(wave, hp_extra=2)
        self._phase_timer  = 0.0
        self._visible      = True
        self._flicker_tick = 0.0

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


# ── Boss factory ───────────────────────────────────────────────────────────────

def make_boss(wave: int) -> _BossBase:
    """
    Return the appropriate boss for the given wave number.

    Wave 5  → Mothership (always first encounter)
    Wave 10 → Dreadnought
    Wave 15 → SwarmQueen
    Wave 20 → Phantom
    Wave 25 → Mothership (cycle repeats, scaling with wave)
    """
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
