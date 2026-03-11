# Space Invaders

A neon-styled Space Invaders remake built in Python and Pygame. All assets, sprites, and audio are generated procedurally at runtime — no external files required.

---

## Download & Play

Pre-built executables are produced automatically via GitHub Actions on every push to `main`.

| Platform | Download |
|----------|----------|
| **Windows** | [SpaceInvaders.exe](../../releases/latest/download/SpaceInvaders.exe) |
| **macOS** | [SpaceInvaders-macOS.zip](../../releases/latest/download/SpaceInvaders-macOS.zip) |

> **macOS:** If prompted with "unidentified developer", right-click the app and select **Open**.

---

## Controls

| Key | Action |
|-----|--------|
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `Space` | Shoot |
| `P` | Pause / Resume |
| `↑` / `↓` | Change difficulty (title screen) |
| `←` / `→` | Cycle ship skin (title screen) |
| `ESC` | Quit |

**Konami Code:** ↑ ↑ ↓ ↓ ← → ← → B A on the title screen.

---

## Features

### Combat
- Three alien types (Squid, Crab, Octopus) with 2-frame animation
- Galaga-style dive bombers from wave 2 onwards
- Four destructible barriers that erode block-by-block
- UFO mystery ship for bonus points (50–300)
- Periodic pressure pulses that advance the formation and increase enemy fire rate

### Enemy Movement Patterns
Formation behaviour changes with each sector:

| Sector | Pattern | Behaviour |
|--------|---------|-----------|
| I – Deep Space | Classic March | Left-right sweep with downward drops |
| II – Nebula Field | Sinusoidal Sweep | Smooth sine-wave drift |
| III – Asteroid Belt | Accordion Pulse | Formation expands and contracts horizontally |
| IV – Solar Flare | Predator Lock-On | Formation tracks the player's position and surges |
| V – Deep Anomaly | Serpent Chain | Aliens flow as a connected Lissajous ribbon |
| VI – Event Horizon | Orbital Ring | Formation orbits a central anchor point |

Each sector also has a unique entry animation (instant spawn, row sweep, column cascade, diagonal slash, etc.).

### Bosses
Four boss types, each with a cinematic title card on entry:
- **The Mothership** — swooping saucer that accelerates into a second phase
- **The Dreadnought** — rotating energy shield with a gap to aim through
- **The Swarm Queen** — spawns drone reinforcements at 50% HP
- **The Phantom** — phases in and out; only vulnerable when fully visible

Bosses cycle every 5 waves and scale in HP and speed.

### Scoring & Progression
- Frenzy system with 4 tiers (Frenzy → Blazing → Inferno → MANIAC), escalating score multipliers and visual effects
- Combo multiplier up to 5× with a visible countdown bar
- Multi-kill callouts (Double Kill, Triple Kill, Massacre)
- Wave completion bonuses: Speed Clear, Flawless Wave, Accuracy Bonus
- Military codename assigned to each wave
- Persistent top-5 high score leaderboard

### Power-ups & Upgrades
- Four drop power-ups: Rapid Fire, Spread Shot, Shield, Bomb
- Post-boss upgrade selection (pierce shots, wingman drone, barrier regeneration, and more)
- Wingman drone that orbits the player and fires independently

### Visuals & Audio
- Six visual sectors, each with unique background, star tint, and an animated transition banner
- Sinusoidal screen shake on impacts and explosions
- Fully procedural chiptune music — four adaptive tiers, synthesised in real time
- Pre-baked CRT scanline overlay and vignette
- Three-layer parallax star field (140 stars)
- Particle system for explosions, death fragments, and pickups

### Other
- Three difficulty modes: Easy, Normal, Hard
- Four unlockable ship skins
- Achievement system (First Blood, Combo Star, Untouchable, Sharp Shooter, UFO Hunter, Boss Slayer, and more)

---

## Run from Source

```bash
pip install pygame
python si_game.py
```

Requires Python 3.9+.

---

## Build

```bash
pip install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceInvaders si_game.py
```

Output: `dist/SpaceInvaders.exe` (Windows) or `dist/SpaceInvaders` (macOS).

---

## Code Structure

| File | Purpose |
|------|---------|
| `si_game.py` | Game loop, state machine, update and draw logic |
| `si_entities.py` | Game object dataclasses and pixel-art sprite renderer |
| `si_movement.py` | Enemy movement patterns (ClassicMarch, SinusoidalSweep, AccordionPulse, RollingPincer, PredatorLockOn, SerpentChain, OrbitalRing) |
| `si_constants.py` | Constants, colour palette, sector and boss configuration |
| `si_audio.py` | Procedural sound and music synthesis |
| `si_persistence.py` | JSON save/load for high scores and achievements |
