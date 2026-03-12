"""
si_simulation.py — Neon Invaders Balance Analyser

Standalone simulation and analysis tool that computes difficulty curves,
runs Monte Carlo playthroughs, and generates balance reports with charts.

Usage:
    python si_simulation.py                        # full run, all difficulties
    python si_simulation.py --charts-only          # generate charts only
    python si_simulation.py --difficulty Hard       # single difficulty
    python si_simulation.py --player expert --waves 120
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Import game constants (no pygame dependency)
from si_constants import (
    ALIEN_START_SPEED, ALIEN_DROP, ALIEN_COLS, ALIEN_ROWS, ALIEN_ROWS_MAX,
    ENEMY_BULLET_SPEED, ENEMY_BULLET_SPEED_CAP, ENEMY_SHOOT_INTERVAL,
    ENEMY_SHOOT_SCALING, ENEMY_SHOOT_FLOOR,
    DIFFICULTY_SETTINGS, DIFFICULTIES,
    BOSS_WAVE_INTERVAL,
    BONUS_ROUND_INTERVAL, BONUS_ROUND_ENEMIES, BONUS_ROUND_DURATION,
    BONUS_ROUND_SCORE, BONUS_ROUND_PERFECT, BONUS_ROUND_SPEED,
    EXTRA_LIFE_MILESTONES,
    FRENZY_TIERS,
    PRESSURE_PULSE_INTERVAL, PRESSURE_PULSE_BOOST, PRESSURE_PULSE_DURATION,
    SENTINEL_HP, WRAITH_HP, ARCHON_HP,
    LEVIATHAN_HEAD_HP, LEVIATHAN_SEGMENT_HP, LEVIATHAN_SEGMENTS,
    COLOSSUS_CORE_BASE_HP, COLOSSUS_CORE_HP_SCALE,
    COLOSSUS_TURRET_BASE_HP, COLOSSUS_TURRET_HP_SCALE,
    COLOSSUS_FIRST_WAVE,
    SENTINEL_INTRO_WAVE, SENTINEL_FULL_WAVE, SENTINEL_INTRO_HP,
    WRAITH_INTRO_WAVE, LEVIATHAN_INTRO_WAVE, ARCHON_INTRO_WAVE,
    HARBINGER_FIRST_WAVE,
    SECTOR_DATA,
    BASE_SHOOT_COOLDOWN, RAPID_SHOOT_COOLDOWN, BULLET_SPEED, POWERUP_DURATION,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Wave Parameter Computation
# ═══════════════════════════════════════════════════════════════════════════════

BOSS_ROTATION = {5: "Mothership", 10: "Dreadnought", 15: "SwarmQueen", 0: "Phantom"}
BOSS_HP_EXTRA = {"Mothership": 0, "Dreadnought": 12, "SwarmQueen": 4, "Phantom": 8}
BOSS_VULNERABILITY = {
    "Mothership": 1.0, "Dreadnought": 0.33, "SwarmQueen": 0.8,
    "Phantom": 0.53, "Colossus": 0.25,
}


@dataclass
class WaveParams:
    wave: int
    difficulty: str
    # Enemies
    alien_speed: float
    shoot_interval: float
    bullet_speed: float
    alien_hp: int
    alien_rows: int
    alien_count: int
    drop_distance: int
    # Power-ups
    powerup_drop_chance: float
    powerup_duration: float
    # Sector
    sector_index: int
    sector_name: str
    # Boss
    is_boss_wave: bool
    boss_type: str
    boss_hp: int
    is_colossus: bool
    colossus_total_hp: int
    # Bonus
    is_bonus_round: bool
    bonus_enemies: int
    # Harbingers
    harbinger_types: list[str] = field(default_factory=list)
    harbinger_total_hp: int = 0
    # Reinforcements
    has_reinforcements: bool = False
    # Derived
    threat_index: float = 0.0


def _harbinger_types_for_wave(wave: int) -> list[str]:
    """Return list of harbinger type names active at the given wave."""
    types: list[str] = []
    if wave < HARBINGER_FIRST_WAVE:
        return types
    if wave >= SENTINEL_INTRO_WAVE:
        types.append("Sentinel")
    if wave >= WRAITH_INTRO_WAVE:
        types.append("Wraith")
    if wave >= LEVIATHAN_INTRO_WAVE:
        types.append("Leviathan")
    if wave >= ARCHON_INTRO_WAVE:
        types.append("Archon")
    return types


def _harbinger_hp(wave: int) -> int:
    """Compute total harbinger HP for a wave, including wave-based scaling."""
    total = 0
    scaling_bonus = max(0, (wave - 35) // 10) * 2  # +2 HP per 10 waves past 35

    if wave >= SENTINEL_INTRO_WAVE:
        hp = SENTINEL_INTRO_HP if wave < SENTINEL_FULL_WAVE else SENTINEL_HP
        total += hp + scaling_bonus
    if wave >= WRAITH_INTRO_WAVE:
        total += WRAITH_HP + scaling_bonus
    if wave >= LEVIATHAN_INTRO_WAVE:
        total += LEVIATHAN_HEAD_HP + LEVIATHAN_SEGMENT_HP * LEVIATHAN_SEGMENTS + scaling_bonus
    if wave >= ARCHON_INTRO_WAVE:
        total += ARCHON_HP + scaling_bonus
    return total


def _boss_info(wave: int) -> tuple[str, int, bool, int]:
    """Return (boss_type, boss_hp, is_colossus, colossus_total_hp) for a boss wave."""
    slot = wave % 20
    is_colossus = (wave >= COLOSSUS_FIRST_WAVE and slot == 10)

    if is_colossus:
        boss_n = max(1, (wave - COLOSSUS_FIRST_WAVE) // 20 + 1)
        turret_hp = COLOSSUS_TURRET_BASE_HP + COLOSSUS_TURRET_HP_SCALE * boss_n
        core_hp = COLOSSUS_CORE_BASE_HP + COLOSSUS_CORE_HP_SCALE * boss_n
        colossus_total = 2 * turret_hp + core_hp
        return "Colossus", core_hp, True, colossus_total

    boss_type = BOSS_ROTATION.get(slot, "Mothership")
    hp_extra = BOSS_HP_EXTRA.get(boss_type, 0)
    boss_hp = 12 + (wave // 5) * 8 + hp_extra
    return boss_type, boss_hp, False, 0


# Baseline threat for normalisation (wave 1, Normal)
_BASELINE_THREAT: float | None = None


def compute_wave_params(wave: int, difficulty: str) -> WaveParams:
    """Compute all parameters for a given wave and difficulty."""
    global _BASELINE_THREAT

    if wave < 1:
        wave = 1

    diff = DIFFICULTY_SETTINGS[difficulty]

    # Core enemy stats
    alien_speed = min(ALIEN_START_SPEED * (1 + 0.010 * (wave - 1)) * diff["speed"], 340)
    shoot_interval = max(
        ENEMY_SHOOT_FLOOR,
        (ENEMY_SHOOT_INTERVAL - ENEMY_SHOOT_SCALING * (wave - 1)) / diff["fire_rate"],
    )
    bullet_speed = min(
        ENEMY_BULLET_SPEED_CAP,
        (ENEMY_BULLET_SPEED + 10 * (wave - 1)) * diff["bullet_speed"],
    )
    alien_hp = min(5, 1 + (wave - 1) // 15)
    alien_rows = min(ALIEN_ROWS_MAX, ALIEN_ROWS + (wave - 1) // 8)
    alien_count = alien_rows * ALIEN_COLS
    drop_distance = min(40, ALIEN_DROP + wave // 3)

    # Power-ups
    powerup_drop_chance = min(diff["powerup"] + wave * 0.003, 0.22)
    powerup_duration = min(8.0, 5.0 + (wave - 1) // 20)

    # Sector
    sector_index = min((wave - 1) // 10, len(SECTOR_DATA) - 1)
    sector_name = SECTOR_DATA[sector_index]["name"]

    # Boss
    is_boss_wave = (wave % BOSS_WAVE_INTERVAL == 0)
    boss_type, boss_hp, is_colossus, colossus_total = ("", 0, False, 0)
    if is_boss_wave:
        boss_type, boss_hp, is_colossus, colossus_total = _boss_info(wave)

    # Bonus round
    is_bonus_round = (wave % BONUS_ROUND_INTERVAL == 0) and not is_boss_wave
    bonus_enemies = 0
    if is_bonus_round:
        tier = max(1, wave // BONUS_ROUND_INTERVAL)
        bonus_enemies = BONUS_ROUND_ENEMIES + (tier - 1) * 20

    # Harbingers
    harb_types = _harbinger_types_for_wave(wave)
    harb_hp = _harbinger_hp(wave) if harb_types else 0

    # Reinforcements (waves with high alien count get reinforcement flag)
    has_reinforcements = (alien_rows >= 7 and wave >= 30)

    # Threat index
    raw_threat = (1.0 / shoot_interval) * bullet_speed * (alien_count / 50.0) * (alien_speed / 140.0)

    if _BASELINE_THREAT is None:
        d = DIFFICULTY_SETTINGS["Normal"]
        base_si = max(ENEMY_SHOOT_FLOOR, ENEMY_SHOOT_INTERVAL / d["fire_rate"])
        base_bs = ENEMY_BULLET_SPEED * d["bullet_speed"]
        base_count = ALIEN_ROWS * ALIEN_COLS
        base_speed = ALIEN_START_SPEED * d["speed"]
        _BASELINE_THREAT = (1.0 / base_si) * base_bs * (base_count / 50.0) * (base_speed / 140.0)

    threat_index = raw_threat / _BASELINE_THREAT if _BASELINE_THREAT else 1.0

    return WaveParams(
        wave=wave, difficulty=difficulty,
        alien_speed=alien_speed, shoot_interval=shoot_interval,
        bullet_speed=bullet_speed, alien_hp=alien_hp,
        alien_rows=alien_rows, alien_count=alien_count,
        drop_distance=drop_distance,
        powerup_drop_chance=powerup_drop_chance, powerup_duration=powerup_duration,
        sector_index=sector_index, sector_name=sector_name,
        is_boss_wave=is_boss_wave, boss_type=boss_type,
        boss_hp=boss_hp, is_colossus=is_colossus,
        colossus_total_hp=colossus_total,
        is_bonus_round=is_bonus_round, bonus_enemies=bonus_enemies,
        harbinger_types=harb_types, harbinger_total_hp=harb_hp,
        has_reinforcements=has_reinforcements,
        threat_index=threat_index,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Chart Generation
# ═══════════════════════════════════════════════════════════════════════════════

DIFF_COLOURS = {"Easy": "#00ff88", "Normal": "#00ffff", "Hard": "#ff3333"}


class ChartGenerator:
    """Generates 8 + 2 balance charts as PNG files."""

    def __init__(self, max_waves: int, output_dir: str) -> None:
        self.max_waves = max_waves
        self.output_dir = output_dir
        self.waves = list(range(1, max_waves + 1))
        # Pre-compute params for all difficulties
        self.params: dict[str, list[WaveParams]] = {}
        for d in DIFFICULTIES:
            self.params[d] = [compute_wave_params(w, d) for w in self.waves]

    def _save(self, fig: plt.Figure, name: str) -> None:
        path = os.path.join(self.output_dir, name)
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

    def generate_all(self) -> None:
        plt.style.use("dark_background")
        self.chart_speed_curves()
        self.chart_fire_rate()
        self.chart_bullet_speed()
        self.chart_enemy_scaling()
        self.chart_threat_index()
        self.chart_powerup()
        self.chart_boss_hp()
        self.chart_overview()

    # 1. Speed curves
    def chart_speed_curves(self) -> None:
        fig, ax = plt.subplots(figsize=(12, 5))
        for d in DIFFICULTIES:
            speeds = [p.alien_speed for p in self.params[d]]
            ax.plot(self.waves, speeds, color=DIFF_COLOURS[d], label=d, linewidth=1.5)
        ax.axhline(340, color="#ffff00", linestyle="--", alpha=0.5, label="Speed cap (340)")
        ax.set_xlabel("Wave")
        ax.set_ylabel("Alien Speed (px/s)")
        ax.set_title("Alien Speed vs Wave")
        ax.legend()
        ax.grid(alpha=0.2)
        self._save(fig, "sim_speed_curves.png")

    # 2. Fire rate (shoot interval)
    def chart_fire_rate(self) -> None:
        fig, ax = plt.subplots(figsize=(12, 5))
        for d in DIFFICULTIES:
            intervals = [p.shoot_interval for p in self.params[d]]
            ax.plot(self.waves, intervals, color=DIFF_COLOURS[d], label=d, linewidth=1.5)
        ax.axhline(ENEMY_SHOOT_FLOOR, color="#ffff00", linestyle="--", alpha=0.5,
                    label=f"Floor ({ENEMY_SHOOT_FLOOR}s)")
        ax.set_xlabel("Wave")
        ax.set_ylabel("Shoot Interval (s)")
        ax.set_title("Enemy Shoot Interval vs Wave")
        ax.legend()
        ax.grid(alpha=0.2)
        self._save(fig, "sim_fire_rate.png")

    # 3. Bullet speed
    def chart_bullet_speed(self) -> None:
        fig, ax = plt.subplots(figsize=(12, 5))
        for d in DIFFICULTIES:
            bspeeds = [p.bullet_speed for p in self.params[d]]
            ax.plot(self.waves, bspeeds, color=DIFF_COLOURS[d], label=d, linewidth=1.5)
        ax.axhline(ENEMY_BULLET_SPEED_CAP, color="#ffff00", linestyle="--", alpha=0.5,
                    label=f"Cap ({ENEMY_BULLET_SPEED_CAP})")
        ax.set_xlabel("Wave")
        ax.set_ylabel("Bullet Speed (px/s)")
        ax.set_title("Enemy Bullet Speed vs Wave")
        ax.legend()
        ax.grid(alpha=0.2)
        self._save(fig, "sim_bullet_speed.png")

    # 4. Enemy scaling (dual y-axis)
    def chart_enemy_scaling(self) -> None:
        fig, ax1 = plt.subplots(figsize=(12, 5))
        # Use Normal difficulty for scaling chart
        counts = [p.alien_count for p in self.params["Normal"]]
        hps = [p.alien_hp for p in self.params["Normal"]]

        ax1.plot(self.waves, counts, color="#00ffff", label="Alien Count", linewidth=1.5)
        ax1.set_xlabel("Wave")
        ax1.set_ylabel("Alien Count", color="#00ffff")
        ax1.tick_params(axis="y", labelcolor="#00ffff")

        ax2 = ax1.twinx()
        ax2.step(self.waves, hps, color="#ff8800", label="Alien HP", linewidth=1.5, where="post")
        ax2.set_ylabel("Alien HP", color="#ff8800")
        ax2.tick_params(axis="y", labelcolor="#ff8800")

        ax1.set_title("Enemy Scaling (Normal Difficulty)")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        ax1.grid(alpha=0.2)
        self._save(fig, "sim_enemy_scaling.png")

    # 5. Threat index (annotated)
    def chart_threat_index(self) -> None:
        fig, ax = plt.subplots(figsize=(14, 6))
        for d in DIFFICULTIES:
            threats = [p.threat_index for p in self.params[d]]
            ax.plot(self.waves, threats, color=DIFF_COLOURS[d], label=d, linewidth=1.5)

        # Boss wave markers (vertical dashed lines)
        for w in self.waves:
            if w % BOSS_WAVE_INTERVAL == 0:
                ax.axvline(w, color="#ff00ff", linestyle="--", alpha=0.25, linewidth=0.7)

        # Harbinger intro markers
        harb_waves = [SENTINEL_INTRO_WAVE, WRAITH_INTRO_WAVE, LEVIATHAN_INTRO_WAVE, ARCHON_INTRO_WAVE]
        harb_labels = ["Sentinel", "Wraith", "Leviathan", "Archon"]
        for hw, hl in zip(harb_waves, harb_labels):
            if hw <= self.max_waves:
                ax.axvline(hw, color="#ff8800", linestyle=":", alpha=0.5, linewidth=1)
                ax.text(hw + 0.5, ax.get_ylim()[1] * 0.9 if ax.get_ylim()[1] > 0 else 1,
                        hl, fontsize=7, color="#ff8800", rotation=90, va="top")

        # Bonus round shading
        for w in self.waves:
            if w % BONUS_ROUND_INTERVAL == 0 and w % BOSS_WAVE_INTERVAL != 0:
                ax.axvspan(w - 0.5, w + 0.5, alpha=0.15, color="#00ff88")

        # Sector boundaries
        for i in range(1, len(SECTOR_DATA)):
            boundary = i * 10 + 1
            if boundary <= self.max_waves:
                ax.axvline(boundary, color="#444488", linestyle="-", alpha=0.3, linewidth=1)

        ax.set_xlabel("Wave")
        ax.set_ylabel("Threat Index (normalised)")
        ax.set_title("Composite Threat Index vs Wave")
        ax.legend(loc="upper left")
        ax.grid(alpha=0.2)
        self._save(fig, "sim_threat_index.png")

    # 6. Power-up curves
    def chart_powerup(self) -> None:
        fig, ax1 = plt.subplots(figsize=(12, 5))
        for d in DIFFICULTIES:
            chances = [p.powerup_drop_chance for p in self.params[d]]
            ax1.plot(self.waves, chances, color=DIFF_COLOURS[d], label=f"{d} drop %", linewidth=1.5)
        ax1.set_xlabel("Wave")
        ax1.set_ylabel("Drop Chance")
        ax1.axhline(0.22, color="#ffff00", linestyle="--", alpha=0.4, label="Cap (0.22)")

        ax2 = ax1.twinx()
        durations = [p.powerup_duration for p in self.params["Normal"]]
        ax2.plot(self.waves, durations, color="#ff88ff", linestyle="-.", label="Duration (s)",
                 linewidth=1.2)
        ax2.set_ylabel("Duration (s)", color="#ff88ff")
        ax2.tick_params(axis="y", labelcolor="#ff88ff")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        ax1.set_title("Power-Up Economy")
        ax1.grid(alpha=0.2)
        self._save(fig, "sim_powerup.png")

    # 7. Boss HP
    def chart_boss_hp(self) -> None:
        fig, ax = plt.subplots(figsize=(12, 5))
        boss_colours = {
            "Mothership": "#ff00ff", "Dreadnought": "#ff8800",
            "SwarmQueen": "#00ff88", "Phantom": "#8888ff", "Colossus": "#ff3333",
        }
        plotted_types: set[str] = set()
        for d_name in ["Normal"]:
            for p in self.params[d_name]:
                if p.is_boss_wave:
                    hp = p.colossus_total_hp if p.is_colossus else p.boss_hp
                    c = boss_colours.get(p.boss_type, "#ffffff")
                    label = p.boss_type if p.boss_type not in plotted_types else None
                    plotted_types.add(p.boss_type)
                    ax.scatter(p.wave, hp, color=c, s=60, zorder=5, label=label)
                    ax.annotate(f"{hp}", (p.wave, hp), textcoords="offset points",
                                xytext=(0, 8), ha="center", fontsize=7, color=c)
        ax.set_xlabel("Wave")
        ax.set_ylabel("Boss HP")
        ax.set_title("Boss HP per Wave (Normal)")
        ax.legend()
        ax.grid(alpha=0.2)
        self._save(fig, "sim_boss_hp.png")

    # 8. Overview (2x3 subplot)
    def chart_overview(self) -> None:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("Neon Invaders Balance Overview", fontsize=16, y=0.98)

        # (0,0) Speed
        for d in DIFFICULTIES:
            axes[0, 0].plot(self.waves, [p.alien_speed for p in self.params[d]],
                            color=DIFF_COLOURS[d], label=d, linewidth=1)
        axes[0, 0].axhline(340, color="#ffff00", linestyle="--", alpha=0.4)
        axes[0, 0].set_title("Alien Speed")
        axes[0, 0].legend(fontsize=7)
        axes[0, 0].grid(alpha=0.2)

        # (0,1) Fire interval
        for d in DIFFICULTIES:
            axes[0, 1].plot(self.waves, [p.shoot_interval for p in self.params[d]],
                            color=DIFF_COLOURS[d], linewidth=1)
        axes[0, 1].set_title("Shoot Interval")
        axes[0, 1].grid(alpha=0.2)

        # (0,2) Bullet speed
        for d in DIFFICULTIES:
            axes[0, 2].plot(self.waves, [p.bullet_speed for p in self.params[d]],
                            color=DIFF_COLOURS[d], linewidth=1)
        axes[0, 2].axhline(ENEMY_BULLET_SPEED_CAP, color="#ffff00", linestyle="--", alpha=0.4)
        axes[0, 2].set_title("Bullet Speed")
        axes[0, 2].grid(alpha=0.2)

        # (1,0) Threat
        for d in DIFFICULTIES:
            axes[1, 0].plot(self.waves, [p.threat_index for p in self.params[d]],
                            color=DIFF_COLOURS[d], linewidth=1)
        axes[1, 0].set_title("Threat Index")
        axes[1, 0].grid(alpha=0.2)

        # (1,1) Enemy count + HP
        counts = [p.alien_count for p in self.params["Normal"]]
        axes[1, 1].plot(self.waves, counts, color="#00ffff", linewidth=1, label="Count")
        ax_hp = axes[1, 1].twinx()
        ax_hp.step(self.waves, [p.alien_hp for p in self.params["Normal"]],
                   color="#ff8800", linewidth=1, label="HP", where="post")
        axes[1, 1].set_title("Enemy Count & HP")
        axes[1, 1].grid(alpha=0.2)

        # (1,2) Powerup drop
        for d in DIFFICULTIES:
            axes[1, 2].plot(self.waves, [p.powerup_drop_chance for p in self.params[d]],
                            color=DIFF_COLOURS[d], linewidth=1)
        axes[1, 2].set_title("Powerup Drop %")
        axes[1, 2].grid(alpha=0.2)

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self._save(fig, "sim_overview.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Monte Carlo Simulation
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlayerProfile:
    name: str
    accuracy: float       # 0-1
    dodge_rate: float      # 0-1
    powerup_pickup: float  # 0-1


PROFILES: dict[str, PlayerProfile] = {
    # dodge_rate: fraction of bullets the player avoids through movement.
    # In Space Invaders the player is actively dodging, so most shots miss.
    # Calibrated so average player survives early waves with ~1-2 deaths.
    "beginner": PlayerProfile("Beginner", 0.30, 0.72, 0.40),
    "average":  PlayerProfile("Average",  0.50, 0.84, 0.60),
    "skilled":  PlayerProfile("Skilled",  0.70, 0.91, 0.80),
    "expert":   PlayerProfile("Expert",   0.85, 0.96, 0.95),
}


@dataclass
class WaveResult:
    wave: int
    lives_before: int
    lives_after: int
    score_gained: int
    time_seconds: float
    is_boss: bool
    is_bonus: bool
    died: bool


@dataclass
class SimulationResult:
    waves_reached: int
    final_score: int
    lives_left: int
    per_wave: list[WaveResult]
    game_over: bool


def simulate_playthrough(
    difficulty: str,
    profile: PlayerProfile,
    max_waves: int,
    rng: random.Random,
) -> SimulationResult:
    """Simulate a single complete playthrough."""
    lives = 4
    score = 0
    milestones_hit = 0
    per_wave: list[WaveResult] = []

    fire_rate = 1.0 / BASE_SHOOT_COOLDOWN  # shots per second

    for w in range(1, max_waves + 1):
        wp = compute_wave_params(w, difficulty)
        lives_before = lives
        wave_score = 0
        wave_time = 0.0

        if wp.is_bonus_round:
            # Bonus round: timed shooting gallery, no life loss
            effective_fire_rate = fire_rate * (1 + 0.3 * profile.powerup_pickup)
            expected_kills = min(wp.bonus_enemies,
                                int(BONUS_ROUND_DURATION * effective_fire_rate * profile.accuracy))
            wave_score = expected_kills * BONUS_ROUND_SCORE
            if expected_kills >= wp.bonus_enemies:
                wave_score += BONUS_ROUND_PERFECT
            wave_time = BONUS_ROUND_DURATION

        elif wp.is_boss_wave:
            # Boss fight
            vuln = BOSS_VULNERABILITY.get(wp.boss_type, 1.0)
            effective_hp = wp.colossus_total_hp if wp.is_colossus else wp.boss_hp
            player_dps = fire_rate * profile.accuracy * vuln
            time_to_kill = effective_hp / max(player_dps, 0.01)
            wave_time = time_to_kill

            # Bosses fire faster than regular aliens (0.7x interval), one bullet at a time
            boss_interval = max(wp.shoot_interval * 0.7, 0.2)
            hits_taken_raw = (time_to_kill / boss_interval) * (1 - profile.dodge_rate)

            # Shield power-ups can absorb hits
            shield_pickups = rng.random() < profile.powerup_pickup * 0.3
            hits_absorbed = 1 if shield_pickups else 0
            hits_taken = max(0, int(hits_taken_raw + 0.5) - hits_absorbed)

            lives -= hits_taken
            wave_score = effective_hp * 20 + 500

        else:
            # Normal wave
            total_enemy_hp = wp.alien_count * wp.alien_hp + wp.harbinger_total_hp
            player_dps = fire_rate * profile.accuracy
            # Power-up boosts (rapid fire, spread)
            if rng.random() < profile.powerup_pickup * wp.powerup_drop_chance * 3:
                player_dps *= 1.5  # rapid fire / spread boost
            wave_time = total_enemy_hp / max(player_dps, 0.01)

            # Enemy hits on player
            # The game fires ONE bullet every shoot_interval seconds (global timer, not per-alien)
            raw_shots = wave_time / wp.shoot_interval
            hits_raw = raw_shots * (1 - profile.dodge_rate)
            # After each hit the player has 0.5s invincibility, capping how many hits can land
            invincibility = 0.5
            max_hittable = wave_time / (wp.shoot_interval + invincibility)
            hits_raw = min(hits_raw, max_hittable)

            # Pressure pulse extra hits
            num_pulses = int(wave_time / PRESSURE_PULSE_INTERVAL)
            pulse_extra = num_pulses * PRESSURE_PULSE_DURATION * (1.0 / wp.shoot_interval) * 0.03 * (
                PRESSURE_PULSE_BOOST - 1) * (1 - profile.dodge_rate)
            hits_raw += pulse_extra

            # Shield pickups
            num_shield_pickups = int(
                wp.alien_count * wp.powerup_drop_chance * 0.25 * profile.powerup_pickup
            )
            hits_taken = max(0, int(hits_raw + 0.5) - num_shield_pickups)

            # Add randomness
            hits_taken = max(0, hits_taken + rng.randint(-1, 1))

            lives -= hits_taken
            wave_score = wp.alien_count * 10 * wp.alien_hp + wp.harbinger_total_hp * 20

        score += wave_score

        # Extra life milestones
        while milestones_hit < len(EXTRA_LIFE_MILESTONES) and score >= EXTRA_LIFE_MILESTONES[milestones_hit]:
            lives += 1
            milestones_hit += 1

        died = (lives <= 0)
        per_wave.append(WaveResult(
            wave=w, lives_before=lives_before, lives_after=max(lives, 0),
            score_gained=wave_score, time_seconds=wave_time,
            is_boss=wp.is_boss_wave, is_bonus=wp.is_bonus_round,
            died=died,
        ))

        if died:
            return SimulationResult(
                waves_reached=w, final_score=score,
                lives_left=0, per_wave=per_wave, game_over=True,
            )

    return SimulationResult(
        waves_reached=max_waves, final_score=score,
        lives_left=lives, per_wave=per_wave, game_over=False,
    )


@dataclass
class MonteCarloResults:
    difficulty: str
    profile: PlayerProfile
    n_runs: int
    max_waves: int
    results: list[SimulationResult]
    # Aggregates
    mean_waves: float
    median_waves: float
    std_waves: float
    mean_score: float
    median_score: float
    death_wave_freq: dict[int, int]  # wave -> count of deaths at that wave
    survival_rate: float  # fraction that reached max_waves


def run_monte_carlo(
    difficulty: str,
    profile: PlayerProfile,
    n_runs: int,
    max_waves: int,
    seed: Optional[int] = None,
) -> MonteCarloResults:
    """Run n_runs simulations and compute aggregate stats."""
    base_seed = seed if seed is not None else random.randint(0, 2**31)
    results: list[SimulationResult] = []

    for i in range(n_runs):
        rng = random.Random(base_seed + i)
        result = simulate_playthrough(difficulty, profile, max_waves, rng)
        results.append(result)

    waves_arr = np.array([r.waves_reached for r in results])
    scores_arr = np.array([r.final_score for r in results])

    death_freq: dict[int, int] = {}
    for r in results:
        if r.game_over:
            death_freq[r.waves_reached] = death_freq.get(r.waves_reached, 0) + 1

    survivors = sum(1 for r in results if not r.game_over)

    return MonteCarloResults(
        difficulty=difficulty, profile=profile,
        n_runs=n_runs, max_waves=max_waves,
        results=results,
        mean_waves=float(np.mean(waves_arr)),
        median_waves=float(np.median(waves_arr)),
        std_waves=float(np.std(waves_arr)),
        mean_score=float(np.mean(scores_arr)),
        median_score=float(np.median(scores_arr)),
        death_wave_freq=death_freq,
        survival_rate=survivors / n_runs if n_runs > 0 else 0.0,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Simulation Charts
# ═══════════════════════════════════════════════════════════════════════════════

def generate_sim_charts(mc_results: MonteCarloResults, output_dir: str) -> None:
    """Generate death distribution and score distribution charts from MC results."""
    plt.style.use("dark_background")

    # Death distribution
    fig, ax = plt.subplots(figsize=(12, 5))
    if mc_results.death_wave_freq:
        waves_sorted = sorted(mc_results.death_wave_freq.keys())
        counts = [mc_results.death_wave_freq[w] for w in waves_sorted]
        ax.bar(waves_sorted, counts, color="#ff3333", alpha=0.8, width=0.8)
    ax.set_xlabel("Wave")
    ax.set_ylabel("Death Count")
    ax.set_title(f"Death Distribution — {mc_results.difficulty} / {mc_results.profile.name}"
                 f"  (n={mc_results.n_runs})")
    ax.grid(alpha=0.2)
    path = os.path.join(output_dir, "sim_death_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    # Score distribution
    fig, ax = plt.subplots(figsize=(12, 5))
    scores = [r.final_score for r in mc_results.results]
    ax.hist(scores, bins=40, color="#00ffff", alpha=0.8, edgecolor="#004444")
    ax.axvline(mc_results.mean_score, color="#ff8800", linestyle="--", label=f"Mean: {mc_results.mean_score:,.0f}")
    ax.axvline(mc_results.median_score, color="#ff00ff", linestyle="--", label=f"Median: {mc_results.median_score:,.0f}")
    ax.set_xlabel("Final Score")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Score Distribution — {mc_results.difficulty} / {mc_results.profile.name}")
    ax.legend()
    ax.grid(alpha=0.2)
    path = os.path.join(output_dir, "sim_score_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Balance Report
# ═══════════════════════════════════════════════════════════════════════════════

class BalanceReporter:
    """Analyses wave parameters and simulation results to produce a balance report."""

    def __init__(
        self,
        wave_params_list: list[WaveParams],
        sim_results: MonteCarloResults,
        difficulty: str,
        profile: PlayerProfile,
    ) -> None:
        self.params = wave_params_list
        self.sim = sim_results
        self.difficulty = difficulty
        self.profile = profile
        self.threats = np.array([p.threat_index for p in self.params])

    def smoothness_score(self, start: int, end: int) -> float:
        """Second derivative variance of threat_index, inverted and scaled to 0-10."""
        segment = self.threats[max(0, start - 1): min(len(self.threats), end)]
        if len(segment) < 3:
            return 10.0
        first_deriv = np.diff(segment)
        second_deriv = np.diff(first_deriv)
        variance = float(np.var(second_deriv))
        # Invert: low variance = high smoothness
        score = max(0.0, min(10.0, 10.0 - variance * 50.0))
        return round(score, 1)

    def find_spikes(self) -> list[dict]:
        """Find waves where threat delta > 1.5x rolling 5-wave average."""
        spikes: list[dict] = []
        if len(self.threats) < 6:
            return spikes
        deltas = np.diff(self.threats)
        for i in range(5, len(deltas)):
            rolling_avg = float(np.mean(np.abs(deltas[max(0, i - 5):i])))
            if rolling_avg > 0 and abs(deltas[i]) > 1.5 * rolling_avg:
                wave = i + 2  # +2 because diff shifts by 1 and waves are 1-indexed
                wp = self.params[i + 1] if i + 1 < len(self.params) else self.params[-1]
                cause = "boss" if wp.is_boss_wave else (
                    "harbinger intro" if wp.harbinger_types and wave in [
                        SENTINEL_INTRO_WAVE, WRAITH_INTRO_WAVE, LEVIATHAN_INTRO_WAVE, ARCHON_INTRO_WAVE
                    ] else "scaling jump"
                )
                spikes.append({"wave": wave, "delta": float(deltas[i]), "cause": cause})
        return spikes

    def find_dead_zones(self) -> list[dict]:
        """Find 5+ consecutive waves with < 2% threat increase."""
        dead_zones: list[dict] = []
        if len(self.threats) < 6:
            return dead_zones
        run_start: Optional[int] = None
        run_length = 0

        for i in range(1, len(self.threats)):
            pct_change = (self.threats[i] - self.threats[i - 1]) / max(self.threats[i - 1], 0.01)
            if abs(pct_change) < 0.02:
                if run_start is None:
                    run_start = i  # wave index (0-based)
                run_length += 1
            else:
                if run_length >= 5 and run_start is not None:
                    dead_zones.append({
                        "start_wave": run_start + 1,
                        "end_wave": run_start + run_length,
                        "length": run_length,
                    })
                run_start = None
                run_length = 0

        if run_length >= 5 and run_start is not None:
            dead_zones.append({
                "start_wave": run_start + 1,
                "end_wave": run_start + run_length,
                "length": run_length,
            })
        return dead_zones

    def _boss_analysis(self) -> str:
        """Analyse boss encounters."""
        lines = ["", "  BOSS BALANCE", "  " + "-" * 50]
        boss_deaths: dict[str, int] = {}
        boss_encounters: dict[str, int] = {}

        for r in self.sim.results:
            for wr in r.per_wave:
                if wr.is_boss:
                    wp = self.params[wr.wave - 1]
                    bt = wp.boss_type
                    boss_encounters[bt] = boss_encounters.get(bt, 0) + 1
                    if wr.died:
                        boss_deaths[bt] = boss_deaths.get(bt, 0) + 1

        for bt in sorted(boss_encounters.keys()):
            enc = boss_encounters[bt]
            deaths = boss_deaths.get(bt, 0)
            rate = deaths / enc * 100 if enc > 0 else 0
            lines.append(f"    {bt:14s}  encounters: {enc:5d}  deaths: {deaths:4d}  "
                         f"death rate: {rate:.1f}%")
        return "\n".join(lines)

    def _harbinger_analysis(self) -> str:
        """Analyse harbinger impact."""
        lines = ["", "  HARBINGER ANALYSIS", "  " + "-" * 50]
        intro_waves = {
            "Sentinel": SENTINEL_INTRO_WAVE, "Wraith": WRAITH_INTRO_WAVE,
            "Leviathan": LEVIATHAN_INTRO_WAVE, "Archon": ARCHON_INTRO_WAVE,
        }
        for name, iw in intro_waves.items():
            if iw <= len(self.params):
                hp = _harbinger_hp(iw)
                lines.append(f"    {name:12s}  intro wave: {iw:3d}  HP at intro: {hp}")
            # Check death spike at intro wave
            deaths_at = self.sim.death_wave_freq.get(iw, 0)
            lines.append(f"    {'':12s}  deaths at intro: {deaths_at}")
        return "\n".join(lines)

    def _powerup_economy(self) -> str:
        """Summarise power-up economy."""
        lines = ["", "  POWER-UP ECONOMY", "  " + "-" * 50]
        drop_w1 = self.params[0].powerup_drop_chance
        drop_last = self.params[-1].powerup_drop_chance
        dur_w1 = self.params[0].powerup_duration
        dur_last = self.params[-1].powerup_duration
        lines.append(f"    Drop chance:  wave 1 = {drop_w1:.3f}  |  wave {len(self.params)} = {drop_last:.3f}")
        lines.append(f"    Duration:     wave 1 = {dur_w1:.1f}s   |  wave {len(self.params)} = {dur_last:.1f}s")
        lines.append(f"    Pickup rate for {self.profile.name}: {self.profile.powerup_pickup:.0%}")
        return "\n".join(lines)

    def format_report(self) -> str:
        """Generate the full balance report as a formatted string."""
        sep = "=" * 72
        lines: list[str] = [
            "",
            sep,
            f"  NEON INVADERS BALANCE REPORT",
            f"  Difficulty: {self.difficulty}  |  Profile: {self.profile.name}  "
            f"|  Simulations: {self.sim.n_runs}",
            sep,
            "",
            "  SUMMARY",
            "  " + "-" * 50,
            f"    Average waves reached:  {self.sim.mean_waves:.1f}",
            f"    Median waves reached:   {self.sim.median_waves:.0f}",
            f"    Std dev (waves):        {self.sim.std_waves:.1f}",
            f"    Survival rate:          {self.sim.survival_rate:.1%}",
            f"    Average score:          {self.sim.mean_score:,.0f}",
            f"    Median score:           {self.sim.median_score:,.0f}",
        ]

        # Estimated game time
        avg_time_per_wave = 25.0  # rough seconds
        est_time = self.sim.mean_waves * avg_time_per_wave / 60.0
        lines.append(f"    Est. avg game time:     {est_time:.0f} min")

        # Smoothness by bands
        lines += ["", "  SMOOTHNESS SCORES (0-10, higher = smoother)", "  " + "-" * 50]
        band_size = 20
        for start in range(1, len(self.params) + 1, band_size):
            end = min(start + band_size - 1, len(self.params))
            sc = self.smoothness_score(start, end)
            lines.append(f"    Waves {start:3d}-{end:3d}:  {sc:.1f}/10")

        # Spikes
        spikes = self.find_spikes()
        lines += ["", "  DIFFICULTY SPIKES", "  " + "-" * 50]
        if spikes:
            for sp in spikes[:15]:
                lines.append(f"    Wave {sp['wave']:3d}:  delta={sp['delta']:+.2f}  "
                             f"cause: {sp['cause']}")
        else:
            lines.append("    No significant spikes detected.")

        # Dead zones
        dead = self.find_dead_zones()
        lines += ["", "  DEAD ZONES (< 2% threat increase)", "  " + "-" * 50]
        if dead:
            for dz in dead:
                lines.append(f"    Waves {dz['start_wave']}-{dz['end_wave']} "
                             f"({dz['length']} waves)")
        else:
            lines.append("    No dead zones detected.")

        lines.append(self._boss_analysis())
        lines.append(self._harbinger_analysis())
        lines.append(self._powerup_economy())

        # Improvement suggestions
        lines += ["", "  SUGGESTIONS", "  " + "-" * 50]
        if self.sim.mean_waves < 20:
            lines.append("    - Early game may be too harsh. Consider reducing "
                         "fire rate scaling for first 15 waves.")
        if self.sim.survival_rate > 0.8:
            lines.append("    - Most players survive all waves. Consider increasing "
                         "late-game difficulty.")
        if self.sim.survival_rate < 0.05:
            lines.append("    - Very few players survive. Consider reducing bullet speed "
                         "scaling or adding more shield drops.")
        if dead:
            lines.append("    - Dead zones make mid-game feel flat. Consider adding "
                         "mini-events or mid-wave reinforcements.")
        if any(sp["cause"] == "scaling jump" for sp in spikes):
            lines.append("    - Scaling jumps cause abrupt difficulty spikes. Consider "
                         "smoothing alien_rows step function.")

        # Top death waves
        if self.sim.death_wave_freq:
            top_death = sorted(self.sim.death_wave_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            lines += ["", "  TOP DEATH WAVES", "  " + "-" * 50]
            for wave_num, count in top_death:
                pct = count / self.sim.n_runs * 100
                wp = self.params[wave_num - 1] if wave_num <= len(self.params) else None
                tag = ""
                if wp:
                    if wp.is_boss_wave:
                        tag = f" [{wp.boss_type}]"
                    elif wp.harbinger_types:
                        tag = f" [+{'|'.join(wp.harbinger_types)}]"
                lines.append(f"    Wave {wave_num:3d}: {count:4d} deaths ({pct:.1f}%){tag}")

        lines += ["", sep, ""]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Neon Invaders Balance Analyser")
    parser.add_argument("--difficulty", choices=["Easy", "Normal", "Hard", "all"],
                        default="all")
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--player", choices=list(PROFILES.keys()), default="average")
    parser.add_argument("--waves", type=int, default=100)
    parser.add_argument("--output-dir", default="./sim_output")
    parser.add_argument("--charts-only", action="store_true")
    parser.add_argument("--no-charts", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Generate balance charts
    if not args.no_charts:
        print("Generating balance charts...")
        gen = ChartGenerator(args.waves, args.output_dir)
        gen.generate_all()
        print(f"  8 charts saved to {args.output_dir}/")

    # Run Monte Carlo simulations
    if not args.charts_only:
        diffs = DIFFICULTIES if args.difficulty == "all" else [args.difficulty]
        profile = PROFILES[args.player]

        for diff in diffs:
            print(f"\nRunning {args.simulations} simulations: {diff} / {profile.name}...")
            mc = run_monte_carlo(diff, profile, args.simulations, args.waves, args.seed)

            # Generate simulation-specific charts
            if not args.no_charts:
                generate_sim_charts(mc, args.output_dir)
                print(f"  Death/score distribution charts saved.")

            # Build and print report
            wave_params = [compute_wave_params(w, diff) for w in range(1, args.waves + 1)]
            reporter = BalanceReporter(wave_params, mc, diff, profile)
            print(reporter.format_report())

    print(f"\nAll output saved to: {os.path.abspath(args.output_dir)}/")


if __name__ == "__main__":
    main()
