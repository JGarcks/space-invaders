# 👾 Space Invaders

A neon-themed Space Invaders remake built entirely in Python & Pygame — no assets, no libraries beyond pygame, everything procedurally generated. Features a deep combo/frenzy system, four distinct boss types, classic pixel-art alien sprites, five visual sectors, cinematic screen effects, procedural chiptune music, and a Konami code easter egg.

> *Built from scratch with zero coding experience using AI. Every line of code, every effect, every sound is generated at runtime.*

---

## ▶️ Download & Play (No Python needed)

Pre-built executables are automatically built via GitHub Actions on every push.

| Platform | Download |
|----------|----------|
| 🪟 **Windows** | [SpaceInvaders.exe](../../releases/latest/download/SpaceInvaders.exe) |
| 🍎 **macOS** | [SpaceInvaders-macOS.zip](../../releases/latest/download/SpaceInvaders-macOS.zip) |

> **macOS note:** If you see *"unidentified developer"*, right-click the app → **Open**.

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `Space` | Shoot |
| `P` | Pause / Resume |
| `↑` / `↓` | Change difficulty (title screen) |
| `←` / `→` | Cycle ship skin (title screen) |
| `ESC` | Quit |

**Secret:** Try the Konami code on the title screen. ↑ ↑ ↓ ↓ ← → ← → B A

---

## ✨ Features

### Aliens & Combat
- **Classic pixel-art alien sprites** — three distinct types across the formation: Squid (top rows), Crab (middle), Octopus (bottom), each with 2-frame animation
- **Dive-bombing aliens** — Galaga-style dive attacks from wave 2 onwards
- **Destructible barriers** — 4 bunkers that erode block-by-block under fire
- **UFO mystery ship** — flies across the top for bonus points (50–300)

### Boss Encounters
- **4 unique boss types**, each with a cinematic title card on entry:
  - 👾 **The Mothership** — classic swooping saucer, accelerates into phase 2
  - 🛡️ **The Dreadnought** — rotating energy shield with a gap you must aim through
  - 🐝 **The Swarm Queen** — spawns a wave of drone reinforcements at 50% HP
  - 👻 **The Phantom** — phases in and out of visibility; only hittable when solid
- Bosses cycle every 5 waves and scale in HP and speed with progression

### Scoring & Progression
- **Frenzy system** — 4 tiers (Frenzy → Blazing → Inferno → MANIAC) triggered by kill streaks, each escalating music, visual effects, and score multipliers
- **Combo multiplier** — up to 5× with a visible countdown bar
- **Multi-kill callouts** — Double Kill, Triple Kill, Massacre for 4+ rapid kills
- **Wave bonuses** — Speed Clear (+500 pts), Flawless Wave (+2,000 pts if untouched), Perfect Wave, Accuracy Bonus
- **Wave codenames** — every wave gets a dramatic military codename (e.g. OPERATION CRIMSON TIDE)
- **High score leaderboard** — top 5 with initials, persisted between sessions

### Power-ups & Upgrades
- **4 power-ups** — Rapid Fire, Spread Shot, Shield, Bomb (screen-clearing nuke)
- **Upgrade system** — choose from 3 upgrades after each boss wave (pierce shots, wingman drone, barrier regen, and more)
- **Wingman drone** — orbits the player and fires independently

### Visuals & Audio
- **5 visual sectors** — the game world evolves every 10 waves: Deep Space → Nebula Field → Asteroid Belt → Solar Flare → Deep Anomaly. Each sector has a unique background colour, star tint, and an animated transition banner
- **Smooth sinusoidal screen shake** — cinematic camera wobble on impacts and explosions
- **Procedural chiptune music** — 4 adaptive tiers that respond to frenzy level, all synthesised in real time (zero audio files)
- **CRT scanline overlay + vignette** — pre-baked for zero per-frame cost
- **3-layer parallax star field** — 140 stars with sector-aware tinting
- **Particle system** — explosions, ship death fragments, power-up pickups
- **Neon aesthetic** — hot pink, cyan, lime, gold colour palette throughout

### Other
- **3 difficulty modes** — Easy, Normal, Hard (speed, fire rate, power-up drops)
- **4 unlockable ship skins** — Cyan → Hot Pink → Gold → Rainbow
- **Achievement system** — First Blood, Combo Star, Untouchable, Sharp Shooter, UFO Hunter, Boss Slayer, and more
- **Konami code easter egg** — 30 lives, all upgrades, MANIAC difficulty, "CHEATER!" badge

---

## 🛠️ Run from Source

```bash
# Requires Python 3.9+
pip install pygame
python si_game.py
```

---

## 🏗️ Build Yourself

```bash
pip install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceInvaders si_game.py
# Output: dist/SpaceInvaders.exe  (Windows)  or  dist/SpaceInvaders  (macOS)
```

---

## 📦 Auto-builds

This repo uses **GitHub Actions** to automatically build executables for Windows and macOS on every push to `main`. Check the [Releases](../../releases) page for the latest download.

---

## 🗂️ Code structure

| File | Purpose |
|------|---------|
| `si_game.py` | Main game loop, state machine, all update/draw logic |
| `si_entities.py` | Dataclasses and classes for all game objects; pixel-art sprite renderer |
| `si_constants.py` | All tuneable constants, colour palette, sector/boss data |
| `si_audio.py` | Fully procedural sound synthesis — no audio files |
| `si_persistence.py` | JSON save/load for high scores and achievements |

---

*Zero assets. Zero audio files. Everything you see and hear is generated by the code at runtime.*
