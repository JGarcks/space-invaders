# Neon Invaders

A deep, feature-rich Space Invaders remake built entirely in Python and Pygame. Every sprite, sound effect, and music track is generated procedurally at runtime — zero external assets required.

---

## Download & Play

Pre-built executables are produced automatically on every push to `main`.

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

### Combat & Enemies

- Three alien types (Squid, Crab, Octopus) with 2-frame animation arranged in a formation grid
- Galaga-style dive bombers swoop at the player from wave 2 onwards
- Coordinated Galaga divers follow Bezier curve attack paths from wave 10
- UFO mystery ship crosses the top of the screen for 50-300 bonus points
- Four destructible barriers that erode block-by-block from enemy and player fire
- Periodic pressure pulses advance the formation downward and temporarily double enemy fire rate

### Harbinger Elite Squadron (Wave 35+)

From wave 35, elite enemies begin appearing alongside the regular formation:

| Elite | HP | Mechanic |
|-------|----|----|
| **Sentinel** | 10 | Rotating energy shield with a gap to shoot through. Periodically swoops toward the player. |
| **Wraith** | 8 | Teleports every few seconds. Fires homing missiles that track the player. |
| **Leviathan** | 5 head + 2 per segment | Multi-segment chain that splits when a middle segment is destroyed. Slowly descends toward the player. |
| **Archon** | 12 | Orbits in a figure-8 pattern. Deploys a tractor beam that can capture the player's ship. |

Elite enemies have a 50% chance to drop a power-up on death.

### Bosses

Five boss types, each introduced with a cinematic title card:

| Boss | Intro Wave | Mechanic |
|------|-----------|----------|
| **The Mothership** | 5 | Swooping saucer that accelerates into a second phase |
| **The Dreadnought** | 10 | Rotating energy shield with a gap to aim through |
| **The Swarm Queen** | 15 | Spawns drone reinforcements at 50% HP |
| **The Phantom** | 20 | Phases in and out of visibility; only vulnerable when fully visible |
| **The Colossus** | 50+ | Multi-part fortress with destructible turrets and an armoured core |

The first four bosses rotate every 5 waves and scale in HP and speed. The Colossus replaces the normal rotation at waves 50, 70, 90, and beyond.

### Enemy Movement Sectors

Formation behaviour changes every 10 waves as you progress through six sectors:

| Sector | Pattern | Behaviour |
|--------|---------|-----------|
| I — Deep Space | Classic March | Left-right sweep with downward drops |
| II — Nebula Field | Sinusoidal Sweep | Smooth sine-wave vertical drift |
| III — Asteroid Belt | Accordion Pulse | Formation expands and contracts horizontally |
| IV — Solar Flare | Predator Lock-On | Formation tracks the player and surges downward; solar flare hazard |
| V — Deep Anomaly | Serpent Chain | Aliens flow as a connected Lissajous ribbon |
| VI — Event Horizon | Orbital Ring | Formation orbits a central anchor point |

Each sector has a unique entry animation (instant spawn, row sweep, column cascade, pincer, diagonal slash) and visual theme with its own background colour and star tint.

### Bonus Rounds

Every 25 waves (25, 50, 75, ...) a bonus round launches:

- 160 fast-moving enemies stream in on choreographed figure-8, spiral, and diamond paths
- Killing an enemy triggers a frag chain explosion that destroys nearby enemies within the blast radius
- A power-up drops every 5 kills, raining upgrades throughout the round
- Destroy all 160 for a 10,000-point perfect round bonus

### Power-Ups & Upgrades

**Drop power-ups** fall from destroyed enemies:

| Power-Up | Available | Effect |
|----------|-----------|--------|
| Rapid Fire | Wave 1+ | Doubles fire rate for 5 seconds |
| Spread Shot | Wave 1+ | Fires a 3-bullet fan pattern |
| Shield | Wave 1+ | Temporary invincibility |
| Bomb | Wave 1+ | Clears all enemies on screen |
| Homing | Wave 35+ | Bullets track nearby enemies |
| EMP | Wave 35+ | Stuns enemies and disables hazards |
| Overcharge | Wave 35+ | Doubles bullet damage |
| Time Warp | Wave 35+ | Slows all enemies |

**Post-boss upgrades** — after every boss fight, choose one of three randomly offered upgrades that last 5 waves:

| Upgrade | Effect |
|---------|--------|
| Bullet Pierce | Bullets pass through 2 additional enemies |
| Barrier Regen | Barriers restore 1 block at the start of each wave |
| Burst Core | Every 4th shot fires a 3-bullet burst |
| Speed Boost | 25% faster movement |
| Frag Shots | Bullets split into 2 on impact |
| Extra Life | Gain one life immediately (permanent) |
| Wingman Drone | An orbiting drone fires alongside you |

**12 weapon synergies** activate automatically when two specific upgrades are active together:

| Synergy | Requirements | Effect |
|---------|-------------|--------|
| Shrapnel Storm | Pierce + Frag | Pierce and split on every hit |
| Bullet Hell | Burst + Spread | Burst fires a 5-bullet fan |
| Guardian Angel | Drone + Speed | Drone fires 2x faster |
| Glass Cannon | Rapid Fire + Frag | 2x frag damage, 2x damage taken |
| Fortress | Regen + Burst | Barriers regen 3 blocks |
| Predator | Pierce + Speed | 50% faster bullets, +1 pierce |
| Seeker Swarm | Homing + Frag | Homing frag splits track enemies |
| Chain Lightning | Homing + Pierce | Homing chains through 3 enemies |
| Magnetic Storm | EMP + Drone | EMP triggers drone burst |
| Berserker | Overcharge + Burst | Every shot is a burst |
| Frozen Barrage | Time Warp + Spread | 5-bullet spread with 1.5x damage |
| Annihilator | Overcharge + Pierce | 3x damage, pierces shields |

### Scoring & Progression

- **Combo multiplier** up to 5x with a visible countdown bar
- **Frenzy system** — 4 escalating tiers (Frenzy, Blazing, Inferno, MANIAC) that reduce enemy fire rate and change the music
- **Graze scoring** — 25 points for narrowly dodging enemy bullets
- **Proximity kill bonus** — 2x score for close-range kills
- **Wave completion bonuses:** Speed Clear, Flawless Wave, Accuracy Bonus
- **Military codenames** assigned to each wave
- **Extra lives** awarded at score milestones (1,000 / 3,000 / 7,000 / 15,000 / 30,000)
- **Reinforcement waves** from wave 50 onwards when the formation thins out
- **Persistent top-5 high score leaderboard**

### Visuals & Audio

- Six visual sectors with unique backgrounds, star tints, and animated transition banners
- Three-layer parallax star field (140 stars)
- Sinusoidal screen shake on impacts and explosions
- Pre-baked CRT scanline overlay and vignette
- Particle system for explosions, death fragments, and pickups
- All sound effects procedurally synthesised — retro machinegun fire, layered explosions, sweep effects
- Fully procedural chiptune music with four adaptive tiers that shift with the frenzy system
- Zero external audio or image files

### Other

- Three difficulty modes: Easy, Normal, Hard
- Four unlockable ship skins (Cyan, Hot Pink, Gold, Rainbow)
- 16+ achievements (First Blood, Combo Star, Untouchable, Sharp Shooter, UFO Hunter, Boss Slayer, and more)
- Continue system for scores above 50,000

---

## Run from Source

```bash
pip install pygame
python space_invaders.py
```

Requires Python 3.9+.

---

## Build

```bash
pip install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceInvaders space_invaders.py
```

Output: `dist/SpaceInvaders.exe` (Windows) or `dist/SpaceInvaders` (macOS).

---

## Code Structure

| File | Purpose |
|------|---------|
| `space_invaders.py` | Entry point |
| `si_game.py` | Game loop, state machine, update and draw logic |
| `si_entities.py` | All game objects — aliens, bosses, harbingers, particles, power-ups |
| `si_movement.py` | Enemy movement patterns (ClassicMarch, SinusoidalSweep, AccordionPulse, PredatorLockOn, SerpentChain, OrbitalRing) |
| `si_constants.py` | Constants, colour palette, sector/boss/synergy configuration |
| `si_audio.py` | Procedural sound and music synthesis |
| `si_persistence.py` | JSON save/load for high scores and achievements |
