# Space Invaders — Design Roadmap
*Last updated: March 2026 — CRT overlay complete; full software-engineering refactor complete (modular architecture, typed dataclasses, enums, lazy SoundManager, unit tests)*

---

## How to resume this project in a new session
1. Open Claude Cowork and select your SpaceInvaders folder
2. Say: *"I'm working on my Space Invaders game. Please read DESIGN_ROADMAP.md from my SpaceInvaders folder to get up to speed, then we'll continue from the Next Up section."*
3. Claude will read this file and be ready to go.

**Important:** The game is now split into modules. The entry point is still `space_invaders.py` — run that to play. The modules are:
- `si_constants.py` — all constants, colours, enums
- `si_audio.py` — procedural sound synthesis + `SoundManager`
- `si_entities.py` — dataclasses (`Alien`, `Bullet`, `EnemyBullet`) and all other entity classes
- `si_persistence.py` — JSON highscore/achievement read-write
- `si_game.py` — the full `Game` class
- `tests/test_logic.py` — 26 unit tests (no pygame required; run with `pytest tests/`)

---

## What's been built (current state of space_invaders.py)

### Core Game
- 1920×1080, 60 FPS, neon theme, parallax starfield
- Classic alien grid (10 cols × 5 rows = 50 aliens base) with lateral + drop movement
- Destructible barriers with block-level damage
- Bonus/mystery ship streaks across the top
- Wave summary screen between rounds

### Frenzy System (core USP)
Consecutive kills without dying build a streak. Tier is kept between waves, streak resets.

| Tier | Kills | Effect |
|------|-------|--------|
| FRENZY! | 10 | 1.5× fire rate, orange bullets, cyan edge pulse |
| FRENZY II! | 25 | 2.0× fire rate, deep orange bullets, wider glow |
| MAX FRENZY! | 45 | 2.5× fire rate, hot pink bullets, wild visual escalation |
| MANIAC MODE | 45 + every 15 more | Further 5% speed increase per level, floor 0.15× interval |

- Dying resets streak but not tier
- MANIAC mode is endless — the game never caps out, it just gets increasingly insane
- Streak counter + progress bar shown centre-bottom at all times
- Slam-in banner animation on tier-up

### Upgrade System
One upgrade offered per wave from a randomised pool:
- **Rapid Fire** — tighter shot cooldown
- **Wide Shot** — dual parallel bullets
- **Burst Fire** — every 3rd shot fires a triple spread
- **Piercing** — bullets punch through multiple aliens
- **Shield** — one free hit absorbed
- **Bomb** — wipe an entire alien row instantly (press B)
- **Extra Life** — +1 life immediately, capped at 5
- **Wingman Drone** — orbiting companion that fires independently, inherits frenzy multiplier

### Difficulty Scaling
- Tiered alien HP: 1 hit (waves 1–10), 2 hits (waves 11–20), 3 hits (waves 21+)
- Visual feedback: white flash on hit, colour dims as HP drops
- Alien speed scales per wave, hard cap at 340 px/s
- Enemy bullets gain aim-assist gradually (0% → 35% by wave 30)
- Alien row count scales: +1 row every 8 waves, capped at 9 rows (90 aliens max)

### Boss Encounters
- Boss arrives every 10 waves with a full cinematic fly-in sequence
- Multi-phase attack patterns: targeted shots, spread bursts, charge sweeps
- Multi-particle explosion on defeat
- Boss HP and aggression scale with wave number

### Visual Effects
- Screen shake on impacts and deaths
- Hit sparks on every alien strike
- Exhaust trail on player ship movement
- Wave-clear screen flash
- Frenzy glow that pulses and intensifies per tier
- Bonus ship spectacular particle explosion
- CRT-style neon colour palette throughout

### Audio (100% Procedural — zero audio files)
- All sound synthesised at runtime using numpy (sine/square/noise waves)
- Shoot, hit, explosion, shield, frenzy tier-up, achievement, drone fire
- Low-life heartbeat SFX when player is on 1 life

### Score & Progression
- Score persists across waves; high score tracked per session
- Score-based continue: if score ≥ 50,000, one continue offered on death, restarts at 50% through current wave
- Wave number displayed throughout

### GitHub / Distribution
- Repo: https://github.com/JGarcks/space-invaders
- GitHub Actions auto-builds Windows .exe and macOS .zip on every push
- Build workflow installs: `pygame numpy pyinstaller`
- Latest release always at: https://github.com/JGarcks/space-invaders/releases/latest

---

## Key constants (space_invaders.py)
```
ALIEN_COLS = 10, ALIEN_ROWS = 5 (base 50 aliens)
ALIEN_START_SPEED = 140 px/s
Alien speed cap   = 340 px/s
Speed scaling     = 0.015 × (wave-1)
Drop distance     = min(40, 32 + wave//3) px
BASE_SHOOT_COOLDOWN  = 0.15s
RAPID_SHOOT_COOLDOWN = 0.07s
BOSS_WAVE_INTERVAL   = 10
FRENZY thresholds    = 10 / 25 / 45 kills
MANIAC threshold     = every 15 kills past tier 3 → 5% faster (floor 0.15×)
DRONE_ORBIT_RADIUS   = 55
DRONE_FIRE_COOLDOWN  = 0.45s
CONTINUE_SCORE_THRESHOLD = 50,000
Burst fires on every 3rd shot (burst_shot_count % 3 == 0)
Barrier regen = full restore of all blocks to HP 3
Alpha values: all clamped with min(255, ...) to prevent pygame crash
```

---

## ⭐ NEXT UP — Two features remaining (one is done)

### ✅ 1. CRT Scanline Overlay — COMPLETE
- Horizontal scanlines every 2px at 30% opacity (`alpha=77`)
- Vignette: 220px dark gradient inward from all four edges
- Toggle on/off with **C** key (works in all states; C in GAME_OVER still = continue)
- Both surfaces pre-baked in `__init__` — zero per-frame CPU cost
- Title screen controls hint updated to show `C = CRT`

### 2. Galaga Dive-Bombing (2–3 hours)
Aliens periodically break formation and swoop at the player:
- 1–2 aliens per wave peel off and follow a swooping arc (sin/cos curve)
- They target the player's X position during the dive
- After sweeping through, they either loop off-screen (removed) or return to grid
- Grid continues moving normally while divers are away
- Collision detection works normally during dive
- Cap on simultaneous divers (max 2–3 at once) to keep it fair
- Divers move faster than the grid — they're a genuine threat
- Tuning is key: should feel exciting, not cheap
- Reference: Galaga (1981) — the defining mechanic of that era

### 3. Procedural Chiptune Music (3–4 hours) — SAVE FOR LAST
Background music generated entirely with numpy — no audio files:
- Square wave melody + triangle bass + noise hi-hat rhythm
- Loops seamlessly during gameplay
- Evolves with frenzy tier:
  - Tier 0: calm, steady tempo (~120 BPM)
  - Tier 1: slightly faster, higher pitch melody
  - Tier 2: faster again, more aggressive tone
  - MAX FRENZY/MANIAC: distorted, frenetic, chaotic
- Transitions between tiers smoothly (crossfade or next-loop swap)
- Respects the existing mute toggle (M key)
- Title screen gets its own simpler loop
- This is the single highest-impact addition — transforms the entire feel of the game
- Most time is tuning, not coding

---

## Future Ideas Bank (discussed, not yet scoped)

### Bonus Challenging Stage (Medium effort)
Every 5 waves, a Galaga-style bonus round:
- "CHALLENGING STAGE" banner drops in
- Upbeat music (or silence from main loop)
- Aliens fly through in preset formation patterns — no shooting back
- Hit them all: PERFECT BONUS (10,000 pts)
- Brief breather that rewards accuracy

### Konami Code Easter Egg (1 hour)
Up Up Down Down Left Right Left Right B A on title screen → something ridiculous:
- 30 lives, all upgrades, MANIAC mode from wave 1
- Easter eggs get shared — especially by teenagers

### Local Co-op (1 day)
Two players, one keyboard:
- Player 1: Arrow keys + Space
- Player 2: WASD + Left Ctrl
- Both ships on screen simultaneously
- Perfect for playing alongside kids/family
- Would need UI rework for two life displays

### ⭐ Smartphone / PWA Version (Major — identified as Phase 2 priority)
This is the agreed long-term goal. A web version massively expands the audience and is the most realistic path to monetisation.

Pygame can't compile to iOS/Android natively. Best path:
- Rewrite game in JavaScript/HTML5 Canvas (Phaser.js recommended)
- Host on GitHub Pages (free, already on your repo)
- Becomes a Progressive Web App — users tap "Add to Home Screen", plays like a proper app
- Touch controls: virtual joystick left, fire button right
- Works on any phone, any platform, via a single link
- Estimated effort: full rewrite, 2–3 days of solid work
- Note: Windows .exe files cannot run on phones — this rewrite is the only path to mobile play
- Complete the three "Next Up" features first, then tackle this as a fresh phase

### Wave Milestone Events (Heavy)
Give specific waves a distinct identity:
- Wave 10: Galaga dive-bombing formation attack (links to Next Up above)
- Wave 20: "Shield Carrier" alien row — must be flanked, not shot head-on
- Wave 30: "Commander" alien that speeds up all others until killed first
- Wave 40: Lights-Out mode — reduced visibility, player has a spotlight

### Legendary Mode (Epic)
Wave 100 secret achievement:
- Triggers "LEGENDARY MODE" — one life, all upgrades, special visual theme
- Special ending screen with shareable score card
- The ultimate skill ceiling

---

### Monetisation — Buy Me a Coffee
Once the smartphone version is live:
- Set up a free page at buymeacoffee.com (takes 5 minutes)
- Add the link to the GitHub README and the game's end/title screen
- The story angle — "built from scratch with no coding experience using AI" — is genuinely shareable and would get traction on TikTok/YouTube Shorts
- No pressure model: free to play, optional tip for people who enjoy it
- Won't make a fortune but a nice acknowledgement — and a real foundation if the game grows

---

## Balance targets
- Normal difficulty: first death expected around wave 12–18
- Skilled play: should reach wave 40–50
- Perfect run target: wave 80+
- Wave 100: secret achievement, extreme skill ceiling
