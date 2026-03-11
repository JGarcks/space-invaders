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
)


# ── Alien ─────────────────────────────────────────────────────────────────────

@dataclass
class Alien:
    x: float
    y: float
    colour: tuple[int, int, int]
    hp: int
    hit_flash: float = 0.0


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

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        pygame.draw.circle(
            surface, self.colour,
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
        self.x       = alien.x
        self.y       = alien.y
        self.colour  = alien.colour
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
        draw_fn(surface, int(self.x) + ox, int(self.y) + oy, self.colour, 1.25)
        trail = pygame.Surface((50, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(trail, (*self.colour, 35), (0, 0, 50, 60))
        surface.blit(trail, (int(self.x) + ox - 25, int(self.y) + oy - 30))


# ── Boss ──────────────────────────────────────────────────────────────────────

class Boss:
    def __init__(self, wave: int) -> None:
        self.x       = float(WIDTH // 2)
        self.y       = 195.0
        self.base_y  = 195.0
        self.wave_timer = 0.0
        boss_tier    = max(1, wave // BOSS_WAVE_INTERVAL)
        self.max_hp  = 12 + boss_tier * 8
        self.hp      = self.max_hp
        self.alive   = True
        self.vx      = float(min(180 + boss_tier * 25, 360))
        self.shoot_timer = 1.8
        self.anim_timer  = 0.0
        self.anim_frame  = 0
        self.hit_flash   = 0.0

    def is_phase2(self) -> bool:
        return self.hp <= self.max_hp // 2

    def update(self, dt: float) -> None:
        self.wave_timer += dt
        self.anim_timer += dt
        if self.anim_timer >= 0.20:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        self.x += self.vx * dt
        self.y = self.base_y + 40.0 * math.sin(self.wave_timer * 1.6)
        if self.x > WIDTH - 140 or self.x < 140:
            self.vx *= -1
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.shoot_timer -= dt

    def should_shoot(self) -> bool:
        interval = 0.42 if self.is_phase2() else 0.72
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.08, 0.08)
            return True
        return False

    def take_hit(self) -> bool:
        """Returns True if the boss was killed."""
        self.hp -= 1
        self.hit_flash = 0.14
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: list[int]) -> None:
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
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
                pygame.draw.line(surface, (*RED, 120), (cx, cy), (sx, sy), 1)

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

        bar_w   = 220
        bar_h   = 12
        hp_frac = self.hp / self.max_hp
        bar_col = LIME if hp_frac > 0.5 else YELLOW if hp_frac > 0.25 else RED
        bx      = cx - bar_w // 2
        by_     = cy - 92
        pygame.draw.rect(surface, (25, 25, 25), (bx, by_, bar_w, bar_h),              border_radius=4)
        pygame.draw.rect(surface, bar_col,      (bx, by_, int(bar_w * hp_frac), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE,         (bx, by_, bar_w, bar_h), 1,           border_radius=4)


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
) -> None:
    w, h = int(22 * size), int(18 * size)
    s = size
    pts = [
        (x - w,           y - h),
        (x - w - int(7*s),y - h - int(10*s)),
        (x - w + int(7*s),y - h),
        (x - int(5*s),    y - h - int(4*s)),
        (x + int(5*s),    y - h - int(4*s)),
        (x + w - int(7*s),y - h),
        (x + w + int(7*s),y - h - int(10*s)),
        (x + w,           y - h),
        (x + w + int(3*s),y),
        (x + w,           y + h),
        (x + w // 2,      y + h + int(7*s)),
        (x + int(4*s),    y + h + int(3*s)),
        (x,               y + h),
        (x - int(4*s),    y + h + int(3*s)),
        (x - w // 2,      y + h + int(7*s)),
        (x - w,           y + h),
        (x - w - int(3*s),y),
    ]
    pygame.draw.polygon(surface, colour, pts)
    eye_r = max(1, int(5*s))
    pygame.draw.circle(surface, BG,    (x - int(7*s), y - int(3*s)), eye_r)
    pygame.draw.circle(surface, BG,    (x + int(7*s), y - int(3*s)), eye_r)
    hr = max(1, int(2*s))
    pygame.draw.circle(surface, WHITE, (x - int(5*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, WHITE, (x + int(9*s), y - int(5*s)), hr)
    ar = max(1, int(2*s))
    pygame.draw.circle(surface, colour, (x - w - int(7*s), y - h - int(12*s)), ar)
    pygame.draw.circle(surface, colour, (x + w + int(7*s), y - h - int(12*s)), ar)


def draw_alien_b(
    surface: pygame.Surface,
    x: int,
    y: int,
    colour: tuple[int, int, int],
    size: float = 1.0,
) -> None:
    w, h = int(22 * size), int(18 * size)
    s = size
    pts = [
        (x,                y - h - int(5*s)),
        (x - int(8*s),    y - h),
        (x - w,            y - h),
        (x - w - int(10*s),y - int(4*s)),
        (x - w - int(12*s),y),
        (x - w - int(10*s),y + int(4*s)),
        (x - w,            y + h),
        (x - w // 2,       y + h - int(5*s)),
        (x - int(4*s),    y + h + int(4*s)),
        (x,                y + h),
        (x + int(4*s),    y + h + int(4*s)),
        (x + w // 2,       y + h - int(5*s)),
        (x + w,            y + h),
        (x + w + int(10*s),y + int(4*s)),
        (x + w + int(12*s),y),
        (x + w + int(10*s),y - int(4*s)),
        (x + w,            y - h),
        (x + int(8*s),    y - h),
    ]
    pygame.draw.polygon(surface, colour, pts)
    eye_r = max(1, int(5*s))
    pygame.draw.circle(surface, BG,    (x - int(7*s), y - int(3*s)), eye_r)
    pygame.draw.circle(surface, BG,    (x + int(7*s), y - int(3*s)), eye_r)
    hr = max(1, int(2*s))
    pygame.draw.circle(surface, WHITE, (x - int(5*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, WHITE, (x + int(9*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, colour, (x, y - h - int(7*s)), max(1, int(3*s)))
