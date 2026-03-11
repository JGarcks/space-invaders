# Tier 3 — Technical Specification
*Space Invaders — Major Changes*
*Specced March 2026 — based on current codebase*

---

## How to read this document

Each feature is broken down into: what it does, every file that changes, exact functions affected, estimated time in focused Claude sessions, and any risks to watch for. Features are ordered by recommended implementation sequence — earlier items are self-contained, later items build on them.

**Total estimate: 9–13 sessions across ~16–22 hours of focused work.**

---

## Feature 17 — Multiple Distinct Boss Types
**Estimated: 2–3 sessions (~4–5 hrs)**

### What it does
Replaces the single scaled-up boss with four completely distinct encounters that cycle every four boss waves. Each has a different silhouette, movement pattern, and attack mechanic. The first encounter is a lightly-reworked version of the existing boss.

| Wave | Boss | Defining mechanic |
|------|------|-------------------|
| 5, 25, 45… | **The Mothership** | Current boss — sine drift, phase 2 spread shot. Rename, tidy up. |
| 10, 30, 50… | **The Dreadnought** | Slow and heavily armoured. A rotating shield arc blocks all bullets except through a 60° gap. Gap widens in phase 2. |
| 15, 35, 55… | **The Swarm Queen** | Every 10 seconds she spawns 3 alien drones into the live grid, then retreats to the top. Kill the reinforcements or ignore them — your choice. |
| 20, 40, 60… | **The Phantom** | Phase-shifts: 2 seconds visible (hittable) then 1.5 seconds invisible (bullets pass through). Attacks during both phases. |

Each boss also gets a **title card** — a dramatic 2-second overlay with the boss name and a subtitle line when it first appears.

---

### File changes

#### `si_entities.py`
- Rename existing `Boss` → `Mothership`. Keep its interface identical.
- Add `Dreadnought` class:
  - Shared base attrs: `x, y, alive, hp, max_hp, hit_flash, wave_timer`
  - New attrs: `shield_angle` (rotates at 1.5 rad/s), `gap_size` (π/3 normal, π/2.2 phase 2)
  - `is_hittable(bullet_x, bullet_y) → bool` — checks if bullet angle falls inside the gap
  - Moves more slowly (speed 100 + tier×15), bobs on a gentle sine
  - Draw: same ellipse hull as Mothership but with 5 rotating shield-arc lines drawn around it; the gap rendered as a brighter colour
- Add `SwarmQueen` class:
  - New attr: `spawn_timer` (counts down from 10s), `spawn_pending: bool`
  - `update()` sets `spawn_pending = True` when timer fires, then resets
  - Game loop reads `boss.spawn_pending`, creates 3 Aliens, clears the flag
  - Phase 2: spawn interval drops to 7s, spawns 4 drones
  - Draw: elongated oval hull (wider than tall), rings of spines, pulsing green glow
- Add `Phantom` class:
  - New attrs: `phase_timer` (2s visible / 1.5s hidden), `is_visible: bool`
  - `is_hittable() → bool` returns `self.is_visible`
  - Draw: normal when visible; when hidden, draw at 20% alpha with a ghostly shimmer (wavy distortion lines)
- Add factory function `make_boss(wave: int) → Mothership | Dreadnought | SwarmQueen | Phantom`
  - `boss_index = (wave // BOSS_WAVE_INTERVAL - 1) % 4`

#### `si_constants.py`
- Add `BOSS_TITLES: dict[str, tuple[str, str]]` — maps class name to (title, subtitle)
  ```
  "Mothership":  ("THE  MOTHERSHIP",  "She has arrived."),
  "Dreadnought": ("THE  DREADNOUGHT", "Armour is impenetrable. Find the gap."),
  "SwarmQueen":  ("THE  SWARM  QUEEN","She never fights alone."),
  "Phantom":     ("THE  PHANTOM",     "You can't hit what you can't see."),
  ```

#### `si_game.py`
- **`_spawn_wave`**: replace `self.boss = Boss(self.wave)` with `self.boss = make_boss(self.wave)`. Set `self.boss_title_timer = 2.5` and `self.boss_title_name / subtitle` from `BOSS_TITLES`.
- **`_update_playing` — boss shooting block**: wrap bullet-vs-boss hit check with `if self.boss.is_hittable(b.x, b.y)` (Dreadnought shield / Phantom phase). Mothership and SwarmQueen always return `True`.
- **`_update_playing` — new SwarmQueen drone check**: after boss update, check `if isinstance(self.boss, SwarmQueen) and self.boss.spawn_pending`. If True: spawn 3 Aliens near the top of the screen (random x, y=160), clear flag, play `sfx.play("dive")`.
- **`_draw_playing`**: add boss title card overlay. Two-second full-width panel with boss name in `font_big` (RED or GOLD depending on type), subtitle in `font_sm`, fades in quickly and out slowly.
- **`_draw_hud`**: update "BOSS WAVE X" label to include boss type name.
- **Import**: add `make_boss, Dreadnought, SwarmQueen, Phantom` to si_entities import.

#### New achievement
- "Ghost Hunter" — kill the Phantom boss

---

### Risks / gotchas
- **Dreadnought hit detection** is geometric (angle of bullet relative to boss centre). Make sure to use `math.atan2(b.y - boss.y, b.x - boss.x)` and compare against the shield gap arc correctly. Test this with a simple print-debug run before finalising.
- **SwarmQueen drone spawning** mid-fight means `len(self.aliens)` can go up mid-wave. The wave-clear check `if not self.aliens and not self.dive_bombers and self.boss is None` already handles this correctly — the wave only clears when boss dies AND alien grid is empty.
- The `boss_cinematic_timer` block in the existing code fires for all bosses — leave it as-is since it applies universally.

---

## Feature 18 — Pixel Art Sprite Overhaul
**Estimated: 2–3 sessions (~4–5 hrs)**

### What it does
Replaces the procedural polygon aliens with hand-crafted pixel art sprites matching the three classic Space Invaders designs — squid (top rows), crab (middle rows), octopus (bottom rows) — each with two animation frames. The result is immediately recognisable as Space Invaders while retaining the neon colour palette already in the game.

The player ship and UFO are left as-is for now (the procedural ship is actually quite good; the UFO already has good character).

---

### File changes

#### `si_entities.py`
- Add sprite pattern constants near the top (after imports). Each is a list of strings where `#` = filled pixel and `.` = empty. 10-wide × 8-tall to match original arcade proportions:
  ```
  SPRITE_SQUID_A = [
    "...####...",
    ".########.",
    "##.####.##",
    "##########",
    ".#.####.#.",
    "...#..#...",
    "..#.##.#..",
    "#.......##",   ← antennae
  ]
  ```
  Define all 6: SQUID_A, SQUID_B, CRAB_A, CRAB_B, OCTOPUS_A, OCTOPUS_B.
  (Exact pixel grids to be finalised in session — iterate until they look right.)

- Add helper:
  ```python
  def draw_sprite(surface, cx, cy, colour, pattern, pixel_w=4, pixel_h=4):
      rows = len(pattern)
      cols = len(pattern[0])
      ox = cx - (cols * pixel_w) // 2
      oy = cy - (rows * pixel_h) // 2
      for r, row in enumerate(pattern):
          for c, ch in enumerate(row):
              if ch == '#':
                  pygame.draw.rect(surface, colour,
                      (ox + c*pixel_w, oy + r*pixel_h, pixel_w, pixel_h))
  ```
  `pixel_w=4, pixel_h=4` makes each "pixel" a 4×4 block — at 1080p this gives a 40×32 alien, crisp and retro.

- Replace `draw_alien_a` / `draw_alien_b` body with calls to `draw_sprite`. Keep the function signatures identical so `_draw_playing` needs zero changes:
  ```python
  def draw_alien_a(surface, x, y, colour, size=1.0):
      tier = getattr(draw_alien_a, '_tier_hint', 0)  # see below
      patterns = [SPRITE_SQUID_A, SPRITE_CRAB_A, SPRITE_OCTOPUS_A]
      draw_sprite(surface, x, y, colour, patterns[min(tier, 2)])
  ```

- The `_tier_hint` approach above is fragile. Better: add a `sprite_tier` field to the `Alien` dataclass (default 0), set it during `_spawn_wave`, and pass it through. See `si_game.py` changes below.

- The existing eye/highlight circles in `draw_alien_a`/b can be removed — the sprite art will have eyes baked in as `.` (empty) cells within the filled body.

#### `si_game.py`
- **`_spawn_wave`**: when creating aliens, compute `sprite_tier` based on row:
  - Rows 0-1: tier 0 (squid, top rows — hardest to reach, worth least)
  - Rows 2-3: tier 1 (crab)
  - Rows 4+: tier 2 (octopus, bottom rows — easiest to reach, worth most)
  - Pass `sprite_tier=min(2, row // 2)` to `Alien(...)` constructor

- **`_draw_playing`** — alien draw block: pass `a.sprite_tier` to the draw function:
  ```python
  for a in self.aliens:
      draw_fn(self.screen, int(a.x)+ox, int(a.y)+oy, col, tier=a.sprite_tier)
  ```

#### `si_entities.py` — `Alien` dataclass
- Add `sprite_tier: int = 0` field

---

### Risks / gotchas
- **Getting the pixel patterns right takes iteration.** Plan one sub-session purely for drawing and checking how each sprite looks at the 4×4 pixel scale. Render a test screen showing all 6 sprites side-by-side.
- **Hit detection is unchanged** — still uses `abs(b.x - a.x) < 28 and abs(b.y - a.y) < 24`, which is a box collision. The sprites are ~40×32, so this hitbox is slightly forgiving — the original arcade's hitbox was also forgiving. No change needed.
- **`size=1.0` parameter** in the existing draw function signatures. The hit-flash scaling is currently achieved by passing `col=WHITE`. The sprite approach handles this the same way (just renders in white). The `size` parameter is used in `draw_ship` calls for the HUD lives display — leave `draw_ship` unchanged.
- **The DiveBomber** draws aliens too (it copies the alien's appearance). Check `DiveBomber.draw()` in si_entities.py and update it to use `draw_sprite` with `self.sprite_tier` (add that field to DiveBomber).

---

## Feature 19 — Sector Themes (Visual Environment Progression)
**Estimated: 1–2 sessions (~2–3 hrs)**

### What it does
Divides the game into visual "sectors" of 10 waves each. Each sector has a distinct background colour, star tint, and a brief ambient effect. When the player crosses into a new sector, a full-width "ENTERING SECTOR X" overlay slides in over the wave summary. This is purely cosmetic — no gameplay impact.

| Sector | Waves | Theme | Background | Atmosphere |
|--------|-------|-------|------------|------------|
| 1 | 1-10 | Deep Space | (10, 10, 46) — current | Standard starfield |
| 2 | 11-20 | Nebula | (22, 5, 38) | Slow-drifting magenta particles |
| 3 | 21-30 | Asteroid Belt | (14, 11, 8) | Occasional tumbling debris specks |
| 4 | 31-40 | Near a Star | (28, 14, 4) | Warm amber vignette overlay |
| 5 | 41+ | Deep Anomaly | (4, 4, 6) | Rare distant cyan "galaxy" circles |

Background lerps smoothly over 3 seconds when transitioning.

---

### File changes

#### `si_constants.py`
- Add `SECTOR_DATA: list[dict]`:
  ```python
  SECTOR_DATA = [
    {"name": "SECTOR I",   "subtitle": "Deep Space",     "bg": (10,10,46),  "star_tint": (200,210,255)},
    {"name": "SECTOR II",  "subtitle": "Nebula",         "bg": (22,5,38),   "star_tint": (255,180,255)},
    {"name": "SECTOR III", "subtitle": "Asteroid Belt",  "bg": (14,11,8),   "star_tint": (210,180,140)},
    {"name": "SECTOR IV",  "subtitle": "Near a Star",    "bg": (28,14,4),   "star_tint": (255,240,180)},
    {"name": "SECTOR V",   "subtitle": "Deep Anomaly",   "bg": (4,4,6),     "star_tint": (180,255,255)},
  ]
  ```

#### `si_game.py`
- **`_init_game`**: add `self.current_sector = 0`, `self.current_bg = list(BG)`, `self.sector_transition_timer = 0.0`, `self.sector_transition_name = ""`, `self.sector_transition_sub = ""`
- **`_draw`**: replace `self.screen.fill(BG)` with `self.screen.fill(tuple(int(c) for c in self.current_bg))`
- **`_update_wave_summary`**: compute `new_sector = (self.wave - 1) // 10`. If `new_sector != self.current_sector`, set the transition name/sub from `SECTOR_DATA`, `sector_transition_timer = 3.5`, update `current_sector`. Also begin lerping `current_bg` toward the new sector's bg.
- **`_update_playing`** / **`_update_wave_summary`**: lerp `current_bg` toward target each frame: `current_bg[i] += (target_bg[i] - current_bg[i]) * min(1.0, dt * 0.8)`
- **`_draw_wave_summary`**: if `sector_transition_timer > 0`, draw the sector entry banner on top of the summary panel (slides down from top, fades out). Decrement timer.
- **`_draw_playing`**: add sector-specific ambient effects:
  - Sector 2 (Nebula): every 2s, spawn a very slow-moving, large (size=8), low-alpha (life=6s) magenta particle drifting across the background.
  - Sector 4 (Near a Star): draw a subtle amber gradient rect at the bottom quarter of the screen, alpha ~30.
  - Sector 5 (Anomaly): every 15s, draw a fleeting `pygame.draw.ellipse` "galaxy" smear in the background.
- **`Star.draw()`**: multiply star colour by `star_tint` (passed as a parameter or via a module-level variable). The simplest approach: store `self.base_colour` on each Star, then compute `draw_colour = tuple(int(b * t/255) for b, t in zip(base, tint))` each frame.

---

### Risks / gotchas
- **Background lerp**: store `current_bg` as a list of three floats, not ints, to allow smooth interpolation. Cast to int only at fill-time.
- **Star tinting**: changing how every star draws each frame has negligible cost (140 stars), but double-check there's no visible flicker when tint changes suddenly.
- **Sector 2 nebula particles**: be careful not to add too many — they live for 6 seconds so at 1 per 2s you'll have ~3 on screen at once. That's fine. Store them in `self.particles` with a very large `life` value.

---

## Feature 20 — Survival & Time Attack Game Modes
**Estimated: 2–3 sessions (~3–5 hrs)**

### What it does
Two new modes selectable from the title screen via a new mode selector row.

**Survival Mode** — endless waves, no upgrade picks, 1 life only, no wave summary pause. The alien grid respawns instantly. Score is the only measure. Separate top-5 leaderboard ("SURVIVAL BEST").

**Time Attack Mode** — clear exactly 10 waves as fast as possible. Timer runs from wave 1 start to wave 10 clear. One life (death restarts the run). Leaderboard shows fastest times. The HUD replaces the score counter with a large live timer.

---

### File changes

#### `si_constants.py`
- Add `GameMode` enum:
  ```python
  class GameMode(Enum):
      CLASSIC  = "CLASSIC"
      SURVIVAL = "SURVIVAL"
      TIME_ATTACK = "TIME ATTACK"
  ```
- Add `GAME_MODES = [GameMode.CLASSIC, GameMode.SURVIVAL, GameMode.TIME_ATTACK]`

#### `si_persistence.py`
- Add `load_survival_scores()` / `save_survival_score(name, score)` — mirrors `load_highscores` but uses key `"survival_scores"` in a new `survival.json`
- Add `load_time_scores()` / `save_time_score(name, seconds)` — stores times in `time_attack.json`, sorted ascending (lower = better)
- Add `SURVIVAL_FILE` and `TIME_ATTACK_FILE` constants to `si_constants.py`

#### `si_game.py`
- **`__init__`**: add `self.game_mode = GameMode.CLASSIC`, `self.mode_cursor = 0`, `self.time_attack_elapsed = 0.0`, load survival/time score data.
- **`_init_game`**: reset `time_attack_elapsed = 0.0`. Apply mode-specific starting conditions:
  - SURVIVAL: `self.lives = 1`; `self.powerup_drop_chance` unchanged but upgrades disabled (skip `UPGRADE_PICK` state)
  - TIME_ATTACK: `self.lives = 1`; upgrades also disabled
- **`_handle_keydown` (TITLE state)**: add left/right navigation for mode selector row (separate from ship selector). Map A/D to mode cycling, arrows to ship cycling (or vice versa — pick one and document it).
- **`_update_playing`**: in TIME_ATTACK mode, `self.time_attack_elapsed += dt` every frame while state is PLAYING.
- **Wave clear section**:
  - SURVIVAL: after wave clears, go directly to `_spawn_wave()` + state=PLAYING (no summary, no upgrade pick). No bonuses calculated.
  - TIME_ATTACK: after wave 10 clears, go to GAME_OVER with `pending_time = time_attack_elapsed`. After wave 10, set `self.state = GameState.GAME_OVER`.
- **`_player_hit`** (lives == 0): in TIME_ATTACK or SURVIVAL, no continue available. Skip the "continue?" check.
- **`_draw_title`**: add a mode selector row below the difficulty selector:
  ```
  MODE:  [ CLASSIC ]  |  SURVIVAL  |  TIME ATTACK
  ```
  Show brief one-line description of selected mode below the row.
  Show the appropriate leaderboard for the selected mode (survival best / fastest times / normal scores).
- **`_draw_hud`**:
  - SURVIVAL: show "SURVIVAL" badge; no upgrade/frenzy bars needed (though they can stay)
  - TIME_ATTACK: replace score display with a large bright timer `01:23.4` in the top-left panel
- **`_draw_gameover`**:
  - TIME_ATTACK: show "FINAL TIME: 01:23.4" instead of "Final Score". Name entry saves the time.
  - SURVIVAL: show normal score + "SURVIVAL MODE"

---

### Risks / gotchas
- **Title screen layout** is already fairly full (ships, difficulty, scores, control hints). The mode selector adds another row. May need to tighten spacing slightly — check at 1080p that nothing clips.
- **SURVIVAL instant-respawn**: removing the wave summary entirely means the frenzy streak is never reset between waves (it resets in the wave-clear block). Decide: should frenzy carry across waves in survival? Probably yes — that's interesting. But `_spawn_wave` also resets enemy bullets and dive bombers, so there's no stale state.
- **TIME_ATTACK wave 10 end**: the game goes to GAME_OVER after wave 10 clears. Use the existing `pending_score` mechanism but store `pending_time` separately. The name entry screen works for both.

---

## Feature 21 — Roguelite Meta-Progression
**Estimated: 2–3 sessions (~4–5 hrs)**

### What it does
Introduces a persistent out-of-run currency called **Scrap** and a **Hangar** screen accessible from the title. Scrap is earned at the end of every run (score ÷ 80, capped at 200 per run, plus a wave-bonus). It's spent in the Hangar on one-time passive upgrades that give a small leg-up at the start of future runs.

**Perks available in the Hangar:**

| Perk | Cost | Effect |
|------|------|--------|
| Reinforced Hull | 50 scrap | Start every run with 1 extra life |
| Hot Start | 60 scrap | Rapid Fire active for the first wave |
| Thick Barriers | 55 scrap | Barriers have 1 extra row of blocks |
| Dulled Rounds | 70 scrap | Enemy bullets 12% slower from wave 1 |
| Scrap Magnet | 45 scrap | Power-up drop chance +50% |
| Head Start | 90 scrap | Start on wave 3 (Classic mode only) |

Perks are bought once and persist forever. Total cost to unlock all: 370 scrap (~4-6 full runs at good performance).

---

### File changes

#### `si_constants.py`
- Add `SCRAP_FILE` path (alongside `HIGHSCORE_FILE`)
- Add `META_PERKS: list[dict]` — each has `id`, `name`, `cost`, `desc`, `colour`

#### `si_persistence.py`
- Add `load_meta() → dict` — loads `meta.json`, default `{"scrap": 0, "perks": []}`
- Add `save_meta(data: dict)` — saves to `meta.json`
- Add `award_scrap(score: int, wave: int) → int` — computes scrap earned: `min(200, score//80 + wave*2)`, loads meta, adds to balance, saves, returns amount earned

#### `si_game.py`
- **`__init__`**: load meta data. Build `self.owned_perks: set[str]` from `meta_data["perks"]`. Add `GameState.HANGAR` to the state machine (or keep it as a sub-state of TITLE).
- **`_init_game`**: apply owned perks:
  ```python
  if "hull" in self.owned_perks:      self.lives += 1
  if "hot_start" in self.owned_perks: self.active_powerups["rapid"] = POWERUP_DURATION
  if "barriers" in self.owned_perks:  # handled in _make_barriers
  if "slow_rounds" in self.owned_perks: self.enemy_bullet_speed *= 0.88
  if "magnet" in self.owned_perks:    self.powerup_drop_chance *= 1.5
  if "head_start" in self.owned_perks and self.game_mode == GameMode.CLASSIC:
      self.wave = 3; self._spawn_wave()
  ```
- **`_update_gameover`**: when entering GAME_OVER, call `award_scrap()` once, store result in `self.scrap_earned_this_run` for display. Add to `__init__` as `self.scrap_earned_this_run = 0`.
- **`_draw_gameover`**: show "SCRAP EARNED: +42 ⚙" below the final score.
- **`_draw_title`**: show current scrap balance in top-right corner ("⚙ 147 SCRAP"). Add "H = Hangar" to the control hints.
- **`_handle_keydown` (TITLE state)**: H key → `self.state = GameState.HANGAR` (or a dedicated HANGAR flag). Also need ESC/B to return from Hangar to title.
- **New methods**:
  - `_update_hangar(dt)` — mostly static; just handle input
  - `_draw_hangar()` — grid of 6 perk cards, each showing name/cost/desc/owned status. Navigation with arrows. ENTER to purchase if affordable and not owned. Visual style matches the existing upgrade-pick cards.
- **`_make_barriers`**: if "barriers" perk owned, add one extra row to `_BARRIER_SHAPE` (or just call `barrier.regen_blocks()` once per barrier after creation).

---

### Risks / gotchas
- **Hangar state**: `GameState` is an Enum in `si_constants.py`. Simply add `HANGAR = "HANGAR"` to it.
- **`award_scrap` called once**: use a flag `self.scrap_awarded_this_run = False` set in `_init_game`, flipped True when GAME_OVER is first entered. Without this it'll award scrap every frame.
- **Head Start perk + wave 3**: in `_init_game`, if head_start is owned, call `self.wave = 3` and re-call `_spawn_wave()`. But `_init_game` already calls `_spawn_wave()` at the end — it'll be called twice. Simplest fix: have `_init_game` skip the final `_spawn_wave()` call and instead call it once at the end after applying perks.
- **"Hot Start" rapid fire** applies `active_powerups["rapid"] = POWERUP_DURATION`. Since `POWERUP_DURATION = 5.0` this lasts 5 seconds. That's fine and consistent with the existing powerup system — no extra code needed.
- **Scrap display in Hangar**: the perk grid should show which perks are already owned clearly (greyed out card with "OWNED" badge, same style as the upgrade "already active" badge).

---

## Recommended implementation order

```
Session 1–2:   Feature 19 — Sector Themes
               Warm-up. Pure visual. Zero risk to gameplay systems.

Session 3–4:   Feature 17 — Multiple Boss Types
               Best done when the rest of the game is stable.
               Start with Dreadnought (most interesting mechanic), then SwarmQueen, then Phantom.

Session 5–6:   Feature 18 — Pixel Art Sprites
               Do this AFTER boss types so the Boss entity changes aren't
               made harder by simultaneously refactoring the draw system.
               Spend the first sub-session purely on drawing and testing sprites.

Session 7–8:   Feature 20 — Survival & Time Attack Modes
               Now that the core game is polished, add modes.
               Start with Survival (simpler), then Time Attack.

Session 9–11:  Feature 21 — Roguelite Meta-Progression
               The most architectural change. Leave until last so the
               game loop is settled and the Hangar screen doesn't need
               to account for unfinished features.
```

**Minimum viable order** (if you only want to do 2 or 3): start with **Sector Themes** (quick win, big atmosphere boost), then **Multiple Boss Types** (highest gameplay impact per hour), then **Pixel Art Sprites** (biggest visual transformation).

---

## Total effort summary

| Feature | Sessions | Est. hrs | Risk |
|---------|----------|----------|------|
| 19 — Sector Themes | 1–2 | 2–3 | Low |
| 17 — Boss Types | 2–3 | 4–5 | Medium |
| 18 — Pixel Art Sprites | 2–3 | 4–5 | Medium |
| 20 — Game Modes | 2–3 | 3–5 | Medium |
| 21 — Roguelite Meta | 2–3 | 4–5 | Medium–High |
| **Total** | **9–14** | **17–23** | |

*"Sessions" = focused 1–2 hour Claude conversations. "Risk" refers to complexity and chance of needing iteration, not anything breaking.*
