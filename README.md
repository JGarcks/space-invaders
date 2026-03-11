# Space Invaders — Reimagined

A love letter to the arcade classic, rebuilt from scratch in Python and Pygame with zero external assets. Every sound is procedurally generated, every visual effect hand-coded. What started as a faithful remake evolved into something with its own identity — a high-intensity arcade shooter with a frenzy combo system, MANIAC escalation mode, wingman drones, boss cinematics, and more.

---

## Features

### Core Gameplay
- Classic wave-based alien grid with smooth lateral + drop movement
- **Tiered alien HP** — enemies take 1 hit (waves 1–10), 2 hits (waves 11–20), and 3 hits (waves 21+), rewarding precise play over spray-and-pray
- **Destructible barriers** — four shields with block-level damage that can be fully restored via upgrade
- **Bonus ship** — a mystery vessel that streaks across the top of the screen for bonus points and a spectacular explosion

### Frenzy Combo System
- Build your **Frenzy streak** by killing enemies without dying
- Three tiers unlock at 10 / 25 / 45 kills — increasing alien speed, visual intensity, and score multiplier
- **MANIAC Mode** — beyond tier 3, every 15 additional kills pushes a further 5% speed increase, stacking up to a minimum 0.15x interval (pure chaos)
- Dying resets your streak — play aggressive, but survive

### Upgrade System
- Earn an upgrade pick every wave from a randomised pool:
  - **Rapid Fire** — tighter shot cooldown
  - **Wide Shot** — dual parallel bullets
  - **Burst Fire** — every 3rd shot fires a triple spread
  - **Piercing** — bullets punch through multiple aliens
  - **Shield** — one free hit absorbed
  - **Bomb** — wipe an entire alien row instantly
  - **Extra Life** — +1 life (capped at 5)
  - **Wingman Drone** — an orbiting companion that fires independently and inherits your frenzy multiplier

### Boss Encounters
- A cinematic boss drops in every 10 waves with a dramatic fly-in sequence
- Multi-phase attack patterns including targeted shots, spread bursts, and charge sweeps
- Satisfying multi-particle explosion on defeat

### Audio (100% Procedural)
- Every sound effect is synthesised at runtime using numpy — no audio files required
- Shoot, hit, explosion, shield, frenzy escalation, and achievement cues all generated from sine/square/noise waves

### Visual Polish
- Screen shake on impacts and deaths
- Hit sparks on every alien strike
- Exhaust trail on player movement
- Wave-clear flash effect
- Frenzy glow that pulses and intensifies with tier
- Colour-coded alien hit flash (white to dim on multi-HP enemies)
- Low-life heartbeat audio cue when down to 1 life

### Score and Progression
- Wave number displayed throughout; score persists across waves
- **Score-based continues** — if you have scored 50,000+ points, you get one chance to continue from halfway through your current wave
- High score tracking within the session

---

## Controls

| Key | Action |
|-----|--------|
| Left / Right Arrow Keys | Move left / right |
| Space | Fire |
| B | Drop bomb (if unlocked) |
| Enter | Confirm / Start / Continue |
| Escape | Quit to menu |
| F | Toggle fullscreen |
| M | Mute / unmute audio |

---

## Download and Play (No Python needed)

Pre-built executables are automatically built via GitHub Actions on every push.

| Platform | Download |
|----------|----------|
| Windows | [SpaceInvaders-Windows.exe](../../releases/latest/download/SpaceInvaders-Windows.exe) |
| macOS | [SpaceInvaders-macOS.zip](../../releases/latest/download/SpaceInvaders-macOS.zip) |

macOS note: If you see "unidentified developer", right-click the app then choose Open.

---

## Run from Source

Requires Python 3.9+ and pip:

```bash
pip install pygame numpy
python space_invaders.py
```

---

## Technical Details

- **Resolution:** 1920x1080, locked 60 FPS
- **Language:** Python 3 / Pygame
- **Assets:** Zero — all graphics drawn via pygame primitives, all audio synthesised with numpy
- **Size:** Single .py file, approximately 2,900 lines
