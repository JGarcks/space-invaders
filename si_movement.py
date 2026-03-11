"""
si_movement.py — Enemy movement patterns.

Each sector has a distinct movement pattern that controls how the alien
formation behaves.  All patterns write directly to alien.x / alien.y so
collision detection and rendering require no changes.
"""
from __future__ import annotations

import math
import random
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from si_entities import Alien

from si_constants import (
    WIDTH, HEIGHT,
    ALIEN_COLS,
    SINE_AMPLITUDE, SINE_FREQ, SINE_PHASE_OFFSET,
    ENTRY_DURATION, ENTRY_SQUAD_DELAY,
    ACCORDION_FREQ, ACCORDION_RANGE,
    ROLL_WAVE_AMPLITUDE, ROLL_WAVE_FREQ,
    PINCER_SPREAD, PINCER_TRIGGER_Y,
    ORBIT_RX, ORBIT_RY, ORBIT_SPEED, ORBIT_CENTER_Y, ORBIT_DRIFT_SPEED,
    PREDATOR_STALK_DURATION, PREDATOR_SURGE_DURATION, PREDATOR_SURGE_DROP,
    PREDATOR_RETREAT_SPEED, PREDATOR_ABORT_THRESHOLD, PREDATOR_MARCH_DROP,
    SERPENT_CENTER_X, SERPENT_CENTER_Y, SERPENT_AMP_X, SERPENT_AMP_Y,
    SERPENT_FREQ_X, SERPENT_FREQ_Y, SERPENT_PHASE_Y,
    SERPENT_CHAIN_DELAY, SERPENT_HISTORY_SIZE, SERPENT_MIN_ALIENS,
    SECTOR_ENTRY_STYLE,
)


# ── Ease-out cubic for smooth entry deceleration ─────────────────────────────

def _ease_out(t: float) -> float:
    """Cubic ease-out: fast start, gentle landing."""
    t = min(1.0, max(0.0, t))
    return 1.0 - (1.0 - t) ** 3


# ── Base class ───────────────────────────────────────────────────────────────

class MovementPattern:
    """Abstract base for alien movement patterns."""

    def __init__(self, sector: int, wave: int) -> None:
        self.sector = sector
        self.wave = wave
        self.time = 0.0
        self._entering = False

    # -- public API ----------------------------------------------------------

    def is_entering(self) -> bool:
        """True while the wave-entry fly-in animation is still playing."""
        return self._entering

    def update(self, aliens: list[Alien], dt: float,
               speed: float, direction: int,
               last_alien_mode: bool = False) -> tuple[int, float]:
        """Move aliens for one frame.

        Returns (new_direction, new_speed) so the Game can track them.
        """
        self.time += dt

        # Entry phase (fly-in)
        if self._entering:
            done = self._update_entry(aliens, dt)
            if done:
                self._entering = False
            return direction, speed

        return self._update_pattern(aliens, dt, speed, direction, last_alien_mode)

    def setup_entry(self, aliens: list[Alien], sector: int) -> None:
        """Configure wave-entry fly-in positions for all aliens."""
        style = SECTOR_ENTRY_STYLE.get(sector)
        if style is None:
            # Sector I: instant appear, no entry animation
            for a in aliens:
                a.entry_progress = 1.0
            self._entering = False
            return

        self._entering = True
        rows = max((a.grid_row for a in aliens), default=0) + 1
        cols = ALIEN_COLS

        if style == "row_sweep":
            for a in aliens:
                a.entry_progress = 0.0
                a.entry_start_x = -80 if a.grid_row % 2 == 0 else WIDTH + 80
                a.entry_start_y = a.base_y - 60
                a.entry_delay = a.grid_row * ENTRY_SQUAD_DELAY
        elif style == "column_cascade":
            for a in aliens:
                a.entry_progress = 0.0
                a.entry_start_x = a.base_x
                a.entry_start_y = -80
                a.entry_delay = a.grid_col * ENTRY_SQUAD_DELAY
        elif style == "pinch_sides":
            for a in aliens:
                a.entry_progress = 0.0
                if a.grid_col < cols // 2:
                    a.entry_start_x = -80
                else:
                    a.entry_start_x = WIDTH + 80
                a.entry_start_y = a.base_y
                a.entry_delay = a.grid_row * ENTRY_SQUAD_DELAY * 0.5
        elif style == "diagonal_slash":
            for a in aliens:
                a.entry_progress = 0.0
                a.entry_start_x = WIDTH + 80
                a.entry_start_y = -80
                a.entry_delay = (a.grid_row + a.grid_col) * ENTRY_SQUAD_DELAY * 0.4
        else:
            for a in aliens:
                a.entry_progress = 1.0
            self._entering = False

    # -- internal ------------------------------------------------------------

    def _update_entry(self, aliens: list[Alien], dt: float) -> bool:
        """Advance entry fly-in. Returns True when all aliens have landed."""
        # If only one alien remains, skip any remaining delay so it can't get
        # stuck off-screen waiting for a staggered entry that will never start.
        if len(aliens) == 1 and aliens[0].entry_progress < 1.0:
            aliens[0].entry_delay = min(aliens[0].entry_delay, self.time)

        all_done = True
        for a in aliens:
            if a.entry_progress >= 1.0:
                continue
            delay = a.entry_delay
            if self.time < delay:
                a.x = a.entry_start_x
                a.y = a.entry_start_y
                all_done = False
                continue
            elapsed = self.time - delay
            a.entry_progress = min(1.0, elapsed / ENTRY_DURATION)
            t = _ease_out(a.entry_progress)
            a.x = a.entry_start_x + (a.base_x - a.entry_start_x) * t
            a.y = a.entry_start_y + (a.base_y - a.entry_start_y) * t
            if a.entry_progress < 1.0:
                all_done = False
        return all_done

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        """Override in subclasses for the main movement logic."""
        return direction, speed


# ── Sector I: Classic March ──────────────────────────────────────────────────

class ClassicMarch(MovementPattern):
    """The original L/R shuffle with downward drop on edge-hit."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        adx = direction * speed * (2.0 if last_alien_mode else 1.0) * dt
        for a in aliens:
            a.x += adx
            a.base_x += adx
        min_x = min(a.x for a in aliens)
        max_x = max(a.x for a in aliens)
        if max_x > WIDTH - 35 or min_x < 35:
            direction *= -1
            for a in aliens:
                a.y += self.drop_amount
                a.base_y += self.drop_amount
            speed = min(speed + 5, 340)

        return direction, speed


# ── Sector II: Sinusoidal Sweep ──────────────────────────────────────────────

class SinusoidalSweep(MovementPattern):
    """Horizontal march + per-row sine-wave Y oscillation."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        adx = direction * speed * (2.0 if last_alien_mode else 1.0) * dt

        # Amplitude scales up as aliens die (more dramatic with fewer)
        alive_ratio = max(0.1, len(aliens) / 50.0)
        amp = SINE_AMPLITUDE * (1.0 + 0.5 * (1.0 - alive_ratio))

        for a in aliens:
            a.base_x += adx
            a.x = a.base_x
            offset_y = amp * math.sin(
                self.time * SINE_FREQ * 2 * math.pi + a.grid_row * SINE_PHASE_OFFSET
            )
            a.y = a.base_y + offset_y

        min_x = min(a.x for a in aliens)
        max_x = max(a.x for a in aliens)
        if max_x > WIDTH - 35 or min_x < 35:
            direction *= -1
            for a in aliens:
                a.base_y += self.drop_amount
            speed = min(speed + 5, 340)

        return direction, speed


# ── Sector III: Accordion Pulse ──────────────────────────────────────────────

class AccordionPulse(MovementPattern):
    """Horizontal march + periodic column expand/contract."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        adx = direction * speed * (2.0 if last_alien_mode else 1.0) * dt

        col_center = (ALIEN_COLS - 1) / 2.0
        pulse = math.sin(self.time * ACCORDION_FREQ * 2 * math.pi)

        for a in aliens:
            a.base_x += adx
            col_offset = (a.grid_col - col_center) * ACCORDION_RANGE * pulse
            a.x = a.base_x + col_offset
            a.y = a.base_y

        min_x = min(a.base_x for a in aliens)
        max_x = max(a.base_x for a in aliens)
        if max_x > WIDTH - 35 or min_x < 35:
            direction *= -1
            for a in aliens:
                a.base_y += self.drop_amount
            speed = min(speed + 5, 340)

        return direction, speed


# ── Sector IV: Rolling Column + Pincer Advance ──────────────────────────────

class RollingPincer(MovementPattern):
    """Per-column downward advance + formation split at threshold."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount
        self.split_progress = 0.0
        self.split_active = False
        self._spawn_max_y: float | None = None  # recorded on first frame

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        adx = direction * speed * (2.0 if last_alien_mode else 1.0) * dt
        half_cols = ALIEN_COLS // 2

        # Rolling wave: sinusoidal Y offset phased per column.
        # base_y NEVER accumulates here — only edge bounces move it down.
        # This gives the "rolling wave-front" visual with no runaway descent.
        for a in aliens:
            a.base_x += adx
            col_frac = a.grid_col / max(1, ALIEN_COLS - 1)   # 0.0 → 1.0
            roll_y = ROLL_WAVE_AMPLITUDE * math.sin(
                self.time * ROLL_WAVE_FREQ * 2 * math.pi + col_frac * 2 * math.pi
            )
            if self.split_active:
                if a.grid_col < half_cols:
                    a.x = a.base_x - PINCER_SPREAD * self.split_progress
                else:
                    a.x = a.base_x + PINCER_SPREAD * self.split_progress
            else:
                a.x = a.base_x
            a.y = a.base_y + roll_y

        # Pincer: activate once edge-bounce descent reaches threshold
        max_y = max(a.base_y for a in aliens)
        if self._spawn_max_y is None:
            self._spawn_max_y = max_y
        descended = max_y - self._spawn_max_y
        if descended >= PINCER_TRIGGER_Y and not self.split_active:
            self.split_active = True

        if self.split_active and self.split_progress < 1.0:
            self.split_progress = min(1.0, self.split_progress + dt * 0.4)

        # Edge bounce — use base_x (not pincer-offset x) so the split
        # doesn't trigger spurious extra bounces and extra Y drops.
        min_bx = min(a.base_x for a in aliens)
        max_bx = max(a.base_x for a in aliens)
        if max_bx > WIDTH - 35 or min_bx < 35:
            direction *= -1
            for a in aliens:
                a.base_y += self.drop_amount
            speed = min(speed + 5, 340)

        return direction, speed


# ── Sector V: Orbital Ring ───────────────────────────────────────────────────

class OrbitalRing(MovementPattern):
    """Aliens orbit in an ellipse. Anchor alien is visually distinct."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount
        self.center_x = WIDTH / 2.0
        self.center_y = float(ORBIT_CENTER_Y)
        self.drift_dir = 1.0
        self.anchor_index = 0
        self.scatter_timer = 0.0   # >0 while scattering after anchor kill

    def set_anchor(self, aliens: list[Alien]) -> None:
        """Mark the anchor alien (the largest/most central)."""
        # Clear old anchor flags
        for a in aliens:
            a.is_anchor = False
        if aliens:
            # Pick the alien closest to grid center
            center_col = (ALIEN_COLS - 1) / 2.0
            center_row = max((a.grid_row for a in aliens), default=0) / 2.0
            best_idx = 0
            best_dist = float('inf')
            for i, a in enumerate(aliens):
                d = abs(a.grid_col - center_col) + abs(a.grid_row - center_row)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            self.anchor_index = best_idx
            aliens[best_idx].is_anchor = True

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        # Drift the orbit center horizontally
        self.center_x += self.drift_dir * ORBIT_DRIFT_SPEED * dt
        if self.center_x > WIDTH - ORBIT_RX - 50:
            self.drift_dir = -1.0
        elif self.center_x < ORBIT_RX + 50:
            self.drift_dir = 1.0

        # Scatter phase after anchor killed
        if self.scatter_timer > 0:
            self.scatter_timer -= dt
            # Aliens jitter randomly during scatter
            for a in aliens:
                a.x += random.uniform(-120, 120) * dt
                a.y += random.uniform(-80, 80) * dt
                # Keep on screen
                a.x = max(40, min(WIDTH - 40, a.x))
                a.y = max(60, min(ORBIT_CENTER_Y + ORBIT_RY + 40, a.y))
            if self.scatter_timer <= 0:
                # Re-form ring with remaining aliens
                self.set_anchor(aliens)
            return direction, speed

        # Re-elect anchor if index went stale (clears old is_anchor flags too)
        if self.anchor_index >= len(aliens):
            self.set_anchor(aliens)

        speed_mult = 1.0 + 0.010 * (self.wave - 1)
        orbit_speed = ORBIT_SPEED * speed_mult

        total = len(aliens)
        # Ring expands as aliens die — the last few are hardest to catch
        alive_frac = min(1.0, total / 50.0)
        dynamic_rx = ORBIT_RX * (1.0 + 0.6 * (1.0 - alive_frac))
        dynamic_ry = ORBIT_RY * (1.0 + 0.6 * (1.0 - alive_frac))

        for i, a in enumerate(aliens):
            angle = (2 * math.pi * i / total) + self.time * orbit_speed
            a.x = self.center_x + dynamic_rx * math.cos(angle)
            a.y = self.center_y + dynamic_ry * math.sin(angle)
            a.base_x = a.x
            a.base_y = a.y

        return direction, speed

    def on_alien_killed(self, killed_index: int, aliens: list[Alien]) -> None:
        """Called when an alien is killed. Triggers scatter if it was the anchor."""
        if killed_index == self.anchor_index:
            self.scatter_timer = 3.0  # 3.0s scatter
            self.anchor_index = 0
        elif killed_index < self.anchor_index:
            self.anchor_index -= 1


# ── Sector IV: Predator Lock-On ──────────────────────────────────────────────

class PredatorLockOn(MovementPattern):
    """Compact march with a fill bar that triggers a formation surge-dive."""

    _STATE_STALK   = 0
    _STATE_SURGE   = 1
    _STATE_RETREAT = 2

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount         = drop_amount
        self.state               = self._STATE_STALK
        self.stalk_timer         = 0.0
        self.lock_on_progress    = 0.0   # 0.0 → 1.0 — read by HUD bar in si_game.py
        self.surge_y_offset      = 0.0   # extra Y during SURGE / RETREAT
        self.surge_drop          = PREDATOR_SURGE_DROP  # capped per-cycle to avoid overshoot
        self.formation_origin_y: float | None = None  # set on first pattern frame

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        # Capture formation anchor Y on the very first pattern frame.
        if self.formation_origin_y is None:
            self.formation_origin_y = min(a.base_y for a in aliens)

        alive_frac = len(aliens) / 50.0  # fraction alive (50 = full grid)

        # ── STALK ───────────────────────────────────────────────────────────
        if self.state == self._STATE_STALK:
            # Normal L/R march identical to ClassicMarch
            adx = direction * speed * (2.0 if last_alien_mode else 1.0) * dt
            for a in aliens:
                a.x      += adx
                a.base_x += adx
            min_x = min(a.x for a in aliens)
            max_x = max(a.x for a in aliens)
            if max_x > WIDTH - 35 or min_x < 35:
                direction *= -1
                for a in aliens:
                    a.y      += self.drop_amount
                    a.base_y += self.drop_amount
                speed = min(speed + 5, 340)

            # Breathing effect — columns undulate gently while stalking
            for a in aliens:
                col_frac = a.grid_col / max(1, ALIEN_COLS - 1)
                breathe_y = 30.0 * math.sin(
                    self.time * 0.8 * 2 * math.pi + col_frac * 2 * math.pi
                )
                a.y = a.base_y + breathe_y

            # Advance lock-on bar (only while enough aliens alive)
            if alive_frac >= PREDATOR_ABORT_THRESHOLD:
                self.stalk_timer += dt
                self.lock_on_progress = min(
                    1.0, self.stalk_timer / PREDATOR_STALK_DURATION)
            else:
                # Too few aliens — drain bar slowly, never surge
                self.stalk_timer = max(0.0, self.stalk_timer - dt * 0.5)
                self.lock_on_progress = self.stalk_timer / PREDATOR_STALK_DURATION

            if self.stalk_timer >= PREDATOR_STALK_DURATION:
                # Compute a safe surge depth so we can't overshoot the player
                player_y = HEIGHT - 80
                current_max_base_y = max(a.base_y for a in aliens)
                self.surge_drop = min(
                    PREDATOR_SURGE_DROP,
                    max(80, player_y - 200 - current_max_base_y),
                )
                self.state = self._STATE_SURGE
                self.stalk_timer = 0.0
                # Record current formation Y so retreat knows its target
                self.formation_origin_y = min(a.base_y for a in aliens)

        # ── SURGE ────────────────────────────────────────────────────────────
        elif self.state == self._STATE_SURGE:
            drop_rate = self.surge_drop / PREDATOR_SURGE_DURATION
            self.surge_y_offset += drop_rate * dt
            self.surge_y_offset  = min(self.surge_y_offset, self.surge_drop)
            for a in aliens:
                a.y = a.base_y + self.surge_y_offset   # only a.y, never base_y
            if self.surge_y_offset >= self.surge_drop:
                self.state = self._STATE_RETREAT

        # ── RETREAT ──────────────────────────────────────────────────────────
        elif self.state == self._STATE_RETREAT:
            self.surge_y_offset -= PREDATOR_RETREAT_SPEED * dt
            if self.surge_y_offset <= 0.0:
                self.surge_y_offset = 0.0
                for a in aliens:
                    a.y = a.base_y   # snap back — eliminates float drift
                self.state            = self._STATE_STALK
                self.stalk_timer      = 0.0
                self.lock_on_progress = 0.0
            else:
                for a in aliens:
                    a.y = a.base_y + self.surge_y_offset  # only a.y, never base_y

        return direction, speed


# ── Sector V: Serpent Chain ───────────────────────────────────────────────────

class SerpentChain(MovementPattern):
    """Aliens follow a Lissajous leader with a per-alien chain delay."""

    def __init__(self, sector: int, wave: int, drop_amount: float) -> None:
        super().__init__(sector, wave)
        self.drop_amount = drop_amount   # retained for API compatibility
        # Pre-fill buffer at the leader start position to avoid index errors
        # on the very first frame before the deque has built up history.
        self.center_y = float(SERPENT_CENTER_Y)
        start = (float(SERPENT_CENTER_X), self.center_y)
        self.history: deque[tuple[float, float]] = deque(
            [start] * SERPENT_HISTORY_SIZE, maxlen=SERPENT_HISTORY_SIZE
        )
        self._scatter = False  # True after too many aliens die

    def _update_pattern(self, aliens: list[Alien], dt: float,
                        speed: float, direction: int,
                        last_alien_mode: bool = False) -> tuple[int, float]:
        if not aliens:
            return direction, speed

        # Scatter fallback when chain collapses to too few aliens
        if len(aliens) < SERPENT_MIN_ALIENS or self._scatter:
            self._scatter = True
            for a in aliens:
                a.x = max(40, min(WIDTH - 40,
                          a.x + random.uniform(-180, 180) * dt))
                a.y = max(60, min(HEIGHT - 200,
                          a.y + random.uniform(-80, 80) * dt))
                a.base_x, a.base_y = a.x, a.y
            return direction, speed

        # ── Leader position (Lissajous figure, drifting downward) ───────────
        self.center_y = min(HEIGHT - 300, self.center_y + 4.0 * dt)
        lx = (SERPENT_CENTER_X
              + SERPENT_AMP_X * math.sin(2 * math.pi * SERPENT_FREQ_X * self.time))
        ly = (self.center_y
              + SERPENT_AMP_Y * math.sin(
                  2 * math.pi * SERPENT_FREQ_Y * self.time + SERPENT_PHASE_Y))
        self.history.appendleft((lx, ly))  # newest at index 0

        # ── Assign chain positions ───────────────────────────────────────────
        frames_step = max(1, int(SERPENT_CHAIN_DELAY * 60))
        hist_len    = len(self.history)
        for i, a in enumerate(aliens):
            idx      = min(i * frames_step, hist_len - 1)
            a.x, a.y = self.history[idx]
            a.base_x  = a.x
            a.base_y  = a.y

        return direction, speed

    def on_alien_killed(self, killed_index: int, aliens: list) -> None:
        """Trigger scatter when chain shrinks below the minimum threshold."""
        if len(aliens) < SERPENT_MIN_ALIENS:
            self._scatter = True


# ── Factory ──────────────────────────────────────────────────────────────────

def create_movement_pattern(sector: int, wave: int,
                            aliens: list[Alien],
                            drop_amount: float) -> MovementPattern:
    """Create the movement pattern for the given sector."""
    from si_constants import SECTOR_MOVEMENT

    pattern_name = SECTOR_MOVEMENT.get(sector, "classic")

    if pattern_name == "sinusoidal":
        pat = SinusoidalSweep(sector, wave, drop_amount)
    elif pattern_name == "accordion":
        pat = AccordionPulse(sector, wave, drop_amount)
    elif pattern_name == "rolling_pincer":
        pat = RollingPincer(sector, wave, drop_amount)
    elif pattern_name == "orbital":
        pat = OrbitalRing(sector, wave, drop_amount)
        pat.set_anchor(aliens)
    elif pattern_name == "predator":
        pat = PredatorLockOn(sector, wave, drop_amount)
    elif pattern_name == "serpent":
        pat = SerpentChain(sector, wave, drop_amount)
    else:
        pat = ClassicMarch(sector, wave, drop_amount)

    pat.setup_entry(aliens, sector)
    return pat
