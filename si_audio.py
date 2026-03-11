"""
si_audio.py — Procedural sound synthesis and the SoundManager.

All sounds are generated entirely from maths (no audio files).
The SoundManager synthesises each sound lazily on first access so startup is
instant; the small delay on first play is imperceptible in practice.

Usage:
    sfx = SoundManager()          # fast — no synthesis yet
    sfx.preload_all()             # optional: warm everything up front
    sfx.play("pew")               # lazy-synthesise then play
    sfx.music_channel.play(sfx.music_loop, loops=-1)
"""
from __future__ import annotations

import math
import random
from array import array
from typing import Callable

import pygame


# ── Low-level synthesis helpers ───────────────────────────────────────────────

def _make_sound(
    frequency: float,
    duration_ms: int,
    volume: float = 0.3,
    wave: str = "square",
) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        if wave == "square":
            val = max_amp if math.sin(2 * math.pi * frequency * t) >= 0 else -max_amp
        elif wave == "noise":
            val = random.randint(-max_amp, max_amp)
        elif wave == "sine":
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave == "sawtooth":
            val = int(max_amp * (2.0 * (frequency * t % 1.0) - 1.0))
        else:
            val = 0
        fade_start = int(n_samples * 0.8)
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_sweep(
    start_freq: float,
    end_freq: float,
    duration_ms: int,
    volume: float = 0.3,
) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = start_freq + (end_freq - start_freq) * progress
        val = int(max_amp * math.sin(2 * math.pi * freq * t))
        fade_start = int(n_samples * 0.7)
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_layered_explosion(volume: float = 0.25) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * 0.3)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env = math.exp(-5 * p)
        noise  = random.uniform(-1, 1) * env * 0.6
        rumble = math.sin(2 * math.pi * 55 * t) * env * 0.4
        rumble += math.sin(2 * math.pi * 80 * t) * env * 0.3
        val = int(max_amp * (noise + rumble))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_level_up_sfx(volume: float = 0.25) -> pygame.mixer.Sound:
    sample_rate = 44100
    notes = [523.25, 659.25, 783.99, 1046.50]
    note_dur = int(sample_rate * 0.08)
    n_samples = note_dur * len(notes) + int(sample_rate * 0.15)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for ni, freq in enumerate(notes):
        start = ni * note_dur
        dur = note_dur + int(sample_rate * 0.1)
        for i in range(dur):
            idx = start + i
            if idx >= n_samples:
                break
            t = i / sample_rate
            p = i / dur
            env = (1 - p) ** 1.5 * min(1.0, i / 200)
            val = int(max_amp * math.sin(2 * math.pi * freq * t) * env)
            buf[idx] = max(-32768, min(32767, buf[idx] + val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_bomb_sfx(volume: float = 0.30) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * 0.65)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env   = math.exp(-3.5 * p)
        noise = random.uniform(-1, 1) * env * 0.5
        bass  = math.sin(2 * math.pi * 40 * t) * env * 0.5
        bass += math.sin(2 * math.pi * 28 * t) * env * 0.3
        val = int(max_amp * (noise + bass))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_ufo_sfx(volume: float = 0.12) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * 0.5)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        freq = 440 + 220 * math.sin(2 * math.pi * 4 * t)
        val  = int(max_amp * math.sin(2 * math.pi * freq * t) * 0.6)
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_boss_sfx(volume: float = 0.28) -> pygame.mixer.Sound:
    sample_rate = 44100
    n_samples = int(sample_rate * 0.9)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env  = math.exp(-1.5 * p) * min(1.0, i / 500)
        freq = 220 - 120 * p
        val  = int(max_amp * (
            math.sin(2 * math.pi * freq * t) * 0.6 +
            math.sin(2 * math.pi * freq * 0.5 * t) * 0.4
        ) * env)
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_extra_life_sfx(volume: float = 0.30) -> pygame.mixer.Sound:
    sample_rate = 44100
    notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]
    note_dur = int(sample_rate * 0.07)
    n_samples = note_dur * len(notes) + int(sample_rate * 0.2)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for ni, freq in enumerate(notes):
        start = ni * note_dur
        dur = note_dur + int(sample_rate * 0.12)
        for i in range(dur):
            idx = start + i
            if idx >= n_samples:
                break
            t = i / sample_rate
            p = i / dur
            env = (1 - p) ** 1.2 * min(1.0, i / 150)
            val = int(max_amp * math.sin(2 * math.pi * freq * t) * env)
            buf[idx] = max(-32768, min(32767, buf[idx] + val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


def _make_ambient_loop(volume: float = 0.06) -> pygame.mixer.Sound:
    """~3.7 s procedural chiptune bass loop (130 BPM, 8 beats)."""
    sample_rate = 44100
    bpm = 130
    beat_dur = 60.0 / bpm
    n_beats = 8
    n_samples = int(sample_rate * beat_dur * n_beats)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    bass_pattern = {0: 110, 2: 110, 3: 147, 4: 130, 6: 110, 7: 98}
    for beat, freq in bass_pattern.items():
        start = int(beat * beat_dur * sample_rate)
        dur = int(sample_rate * 0.28)
        for i in range(dur):
            idx = start + i
            if idx >= n_samples:
                break
            t = i / sample_rate
            p = i / dur
            env = math.exp(-7 * p) * min(1.0, i / 80)
            v1 = int(max_amp * math.sin(2 * math.pi * freq * t) * env * 0.75)
            v2 = int(max_amp * math.sin(2 * math.pi * freq * 2 * t) * env * 0.25)
            buf[idx] = max(-32768, min(32767, buf[idx] + v1 + v2))
    rng = random.Random(42)
    for half in range(n_beats * 2):
        start = int(half * beat_dur * 0.5 * sample_rate)
        dur = int(sample_rate * 0.03)
        for i in range(dur):
            idx = start + i
            if idx >= n_samples:
                break
            p = i / dur
            env = math.exp(-25 * p)
            val = int(max_amp * rng.uniform(-1, 1) * env * 0.28)
            buf[idx] = max(-32768, min(32767, buf[idx] + val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound


# ── SoundManager ──────────────────────────────────────────────────────────────

class SoundManager:
    """Lazily synthesises and caches every game sound.

    Sounds are generated on first attribute access, not at import/init time.
    This keeps the window open instantly; each sound is synthesised at most once
    per session and then returned from the in-memory cache on subsequent calls.

    Access sounds as attributes:  sfx.pew.play()
    Or play by name:              sfx.play("pew")
    Pre-warm everything:          sfx.preload_all()
    """

    _MAKERS: dict[str, Callable[[], pygame.mixer.Sound]] = {
        "pew":         lambda: _make_sound(880, 80, 0.15, "square"),
        "explode":     lambda: _make_layered_explosion(0.25),
        "powerup":     lambda: _make_sweep(400, 1200, 200, 0.25),
        "achieve":     lambda: _make_sweep(600, 1400, 300, 0.2),
        "death":       lambda: _make_sweep(600, 150, 400, 0.3),
        "enemy_shoot": lambda: _make_sound(220, 100, 0.12, "sawtooth"),
        "player_hit":  lambda: _make_sound(150, 200, 0.2, "noise"),
        "level_up":    lambda: _make_level_up_sfx(0.25),
        "ufo_beacon":  lambda: _make_ufo_sfx(0.12),
        "ufo_hit":     lambda: _make_sweep(800, 150, 350, 0.28),
        "bomb":        lambda: _make_bomb_sfx(0.30),
        "dive":        lambda: _make_sweep(180, 640, 220, 0.15),
        "boss":        lambda: _make_boss_sfx(0.28),
        "extra_life":  lambda: _make_extra_life_sfx(0.30),
        "music_loop":  lambda: _make_ambient_loop(0.06),
    }

    def __init__(self) -> None:
        self._cache: dict[str, pygame.mixer.Sound] = {}
        self.music_channel: pygame.mixer.Channel = pygame.mixer.Channel(14)
        self.ufo_channel:   pygame.mixer.Channel = pygame.mixer.Channel(15)

    def __getattr__(self, name: str) -> pygame.mixer.Sound:
        if name in self._MAKERS:
            if name not in self._cache:
                self._cache[name] = self._MAKERS[name]()
            return self._cache[name]
        raise AttributeError(f"SoundManager has no sound {name!r}")

    def play(self, name: str) -> None:
        """Play a named sound, silently swallowing any pygame errors."""
        try:
            getattr(self, name).play()
        except Exception:
            pass

    def preload_all(self) -> None:
        """Eagerly synthesise every sound — useful after a loading indicator."""
        for name in self._MAKERS:
            getattr(self, name)
