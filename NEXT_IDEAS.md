# Space Invaders — What's Next?
*Ideas reviewed March 2026 — all roadmap items confirmed complete*

---

## Session log

| Date | What was done |
|------|--------------|
| Mar 2026 | **Tier 1 complete (items 1–8).** Konami code, Last Alien tension mode, speed bonus, wave codenames, multi-kill callouts, ship fragment death effect, flawless wave bonus, difficulty badge — all shipped. |
| Mar 2026 | **Tier 3 items 17, 18, 19 complete.** Multiple boss types (Mothership / Dreadnought / SwarmQueen / Phantom + make_boss factory), pixel-art sprites (Squid / Crab / Octopus, 3 tiers × 2 frames, draw_sprite renderer), sector themes (5 sectors × 10 waves, background lerp, star tinting, transition banners, boss title cards). |
| Mar 2026 | **Difficulty rebalanced.** Alien HP scaling slowed (reaches max at wave 41 not 21), alien speed ramp reduced, enemy shoot interval floor raised to 0.55 s, enemy bullet speed capped at 450 px/s, starting lives increased to 4. |
| Mar 2026 | **Smoothness pass.** Screen shake replaced with smooth sinusoidal decay (was random-per-frame), `pygame.DOUBLEBUF` added, `tick_busy_loop` adopted for more consistent frame timing. |
| Mar 2026 | **Three visual polish features approved, paused for credits.** See items 26, 27, 28 below. Estimated ~1 hr 15 min total. |

---

## How to use this document

Ideas are grouped into four tiers by ambition and effort. Each idea includes a rough **effort estimate** so you can pick and choose based on how many credits you want to spend in a session. Lower tiers are the most credit-efficient — you get a lot of polish for very little work.

The game is already genuinely impressive. Everything below is about making something good into something *exceptional*.

---

## ✦ TIER 1 — Minor Changes
*Quick wins. Each one is a short focused session. High reward for low effort.*

---

### 1. Konami Code Easter Egg
**Effort: ~30 mins | Already in ideas bank**

On the title screen, entering ↑ ↑ ↓ ↓ ← → ← → B A activates a ridiculous god mode: 30 lives, all 7 upgrades active, MANIAC difficulty from wave 1, and a glowing "CHEATER!" badge on screen. Easter eggs like this get screenshot-shared constantly — especially by younger players — and cost almost nothing to build.

---

### 2. "Last Alien Standing" Tension Mode
**Effort: ~45 mins**

When only one alien remains in the grid, the music cuts to silence, the alien doubles in speed, and a pulsing red "LAST ONE!" label appears. It becomes a frantic cat-and-mouse moment. This is in the original 1978 arcade game and is one of its most memorable moments — recreating it here would feel like a loving callback.

---

### 3. Wave Completion Speed Bonus
**Effort: ~1 hour**

Track how long each wave takes to clear. If the player finishes under a threshold (e.g. 45 seconds), award a bonus: "SPEED CLEAR! +500". Show it prominently on the wave summary screen. This rewards aggressive play without changing any mechanics — just adds a scoring dimension that skilled players can chase.

---

### 4. Wave Codenames
**Effort: ~30 mins**

Give every wave a dramatic military codename on the wave summary screen: "OPERATION CRIMSON TIDE", "SQUADRON DELTA-7", "THE SWARM ARRIVES". Generate them from a pool of ~20 adjectives and ~20 nouns. Pure flavour with zero gameplay cost, but it makes each wave feel like an event rather than just a number incrementing.

---

### 5. Multi-Kill Callouts
**Effort: ~45 mins**

When the player kills 2 aliens within the same COMBO_WINDOW (already tracked), show a quick floating text callout: "DOUBLE KILL!", "TRIPLE KILL!", "MASSACRE!" for 4+. These should appear at the point of the last kill in a contrasting colour (bright yellow/white). Games like Unreal Tournament made these famous and they never get old.

---

### 6. Player Death Fragment Effect
**Effort: ~1 hour**

Currently when the player dies there's a particle burst. Upgrade it: the ship polygon shatters into 4-6 triangular fragments that spin outward with angular velocity before fading. Use the existing polygon points to drive the fragment shapes. It makes death feel more visceral and satisfying — important because in a high-difficulty game, death happens a lot and it should look good.

---

### 7. Flawless Wave Bonus
**Effort: ~45 mins**

If the player clears a wave without taking a single hit (not just without dying — without hitting the invincibility window at all), flash "FLAWLESS!" across the screen in gold and award 2,000 bonus points. Track the flag with a simple boolean that resets each wave and flips to False on any damage event. Ties directly into the existing score system.

---

### 8. Difficulty Badge on HUD
**Effort: ~20 mins**

Show a small coloured badge in a corner — "EASY" in green, "NORMAL" in cyan, "HARD" in red — throughout gameplay. Very small change, but when players screenshot their scores they can brag about the difficulty they were on. Also useful self-reminder mid-game.

---

## ✦✦ TIER 2 — Medium Changes
*Noticeable feature additions. Each is one focused session of a few hours.*

---

### 9. Bonus Challenging Stage
**Effort: ~3-4 hours | Already in ideas bank**

Every 5 waves, a Galaga-style interlude: "CHALLENGING STAGE" drops in on a banner, the regular music stops, and aliens fly through in preset formation patterns — chevrons, spirals, figure-eights — without shooting back. Hit them all for a PERFECT BONUS (10,000 pts). Even hitting most scores a GOOD BONUS. It's a breather that rewards precision, and the contrast with the intense main waves makes both feel better.

---

### 10. Splitter Alien
**Effort: ~2-3 hours**

One alien type (rare spawn, maybe 2 per wave from wave 5 onwards, shown in a distinct purple colour) splits into two smaller, faster versions when first hit. The smaller versions have 1HP each. This creates a risk/reward moment — do you shoot the splitter now and deal with two fast enemies, or save it for last? Directly inspired by *Space Invaders Infinity Gene* and *Galaga Arrangement*. Fits perfectly into the existing `Alien` dataclass with a `can_split: bool` flag.

---

### 11. Galaga Capture Mechanic
**Effort: ~3-4 hours**

The boss alien (or a special "Commander" alien) fires a tractor beam downward at the player. If it connects, your ship is captured and flies up to join the alien formation. You lose a life but your *old* ship is now up there, locked in place. If you shoot it free (without killing it), you recover the ship and temporarily fly with **two ships in formation**, doubling your firepower. One of the most beloved mechanics in arcade history. The dual-ship phase would work beautifully with the existing multi-bullet system.

---

### 12. Formation Variety
**Effort: ~2-3 hours**

Right now every wave starts with a standard rectangular grid. Add 4-5 alternative starting formations that rotate each wave: a V-shape, a diamond/rhombus, an X-shape, a scattered "swarm" pattern, an inverted triangle (pointing down, so the closest aliens are the strongest row). The aliens still behave the same — just a different visual arrangement. Makes each wave feel fresh and changes the tactical threat (a V-shape means the tip reaches you first).

---

### 13. Charge Shot Upgrade
**Effort: ~2 hours**

A new upgrade in the pool: hold SPACE to charge a beam, release to fire a full-height laser that punches through every alien and barrier in a straight column. Visual: the player ship glows increasingly intense while charging (0.8 second charge time), then a thick beam fires with a screen-wide shockwave flash. Balanced by the fact that you can't fire normal shots while charging. Inspired by every shoot-em-up ever, from R-Type to Ikaruga.

---

### 14. Homing Missile Upgrade
**Effort: ~2 hours**

Another new upgrade: every 4th shot fires a small missile that curves toward the nearest alien using a simple steering algorithm (lerp velocity toward target). It's slower than a normal bullet but can navigate around other aliens. Visually distinct — slightly larger, orange, with a little smoke trail. Inspired by *Gradius* and countless shmups. Adds satisfying variety to the shooting rhythm.

---

### 15. Animated Title Screen Demo
**Effort: ~2 hours**

The title screen currently shows static content. Add a "attract mode" demo: a small fleet of aliens slowly drifts across the top half of the screen while a ghost player auto-fires at them, aliens explode with particles, and the frenzy colour palette pulses. This plays on loop while nobody is pressing anything. Classic arcades used this to draw players in — it demonstrates the game's visual quality immediately and makes the title feel alive.

---

### 16. "No-Death Run" Tracker & Achievement
**Effort: ~1 hour**

Track whether the player has died at all in the current run. If they reach wave 10 without a single death, pop an achievement: "GHOST PILOT". Wave 20 without a death: "UNTOUCHABLE". These are already supported by the achievements system — just need the tracking logic and new achievement entries.

---

### 26. Explosion Shockwave Rings ⏳ APPROVED — PENDING CREDITS
**Effort: ~15 mins**

When anything dies (alien, boss, UFO), emit an expanding circle outline that grows from ~0 to ~80 px radius and fades to transparent over ~0.4 s alongside the existing particle burst. A small `ShockwaveRing` dataclass (x, y, radius, max_radius, alpha, colour) updated each frame. This single effect is present in virtually every polished shooter and reads instantly as "expensive". Completely self-contained — zero impact on anything else.

---

### 27. Player Ship Banking ⏳ APPROVED — PENDING CREDITS
**Effort: ~15–20 mins**

When the player moves left, the ship polygon visually tilts a few degrees left; right input tilts right; no input smoothly returns to vertical. Implemented by tracking a `bank_angle: float` that lerps toward a target driven by movement direction, then offsetting the wing-tip x-coordinates in `draw_ship` proportionally. Makes movement feel physical and responsive — the ship feels like it has weight.

---

## ✦✦✦ TIER 3 — Major Changes
*Substantial features that meaningfully expand the game. Plan for a dedicated multi-session project.*

---

### 17. Multiple Distinct Boss Types ✅ COMPLETE
**Effort: ~1 day**

Currently every boss is the same ship, just scaled up. Replace this with 3-4 completely distinct boss designs, each with a unique attack pattern and personality:

- **The Mothership** (wave 5): Wide, slow, drops mines across the screen that sit there and must be shot.
- **The Dreadnought** (wave 10): Heavily armoured with a rotating shield that must be timed — only vulnerable during gaps.
- **The Swarm Queen** (wave 15): Spawns small drone aliens mid-fight that fill the screen.
- **The Phantom** (wave 20+): Phase-shifts in and out of visibility, only hittable for 2-second windows.

Each boss could announce itself with a unique title card. This transforms the boss system from a stat-scaling number into a series of genuinely different encounters — the single biggest gameplay impact of anything in Tier 3.

---

### 18. Pixel Art Sprite Overhaul ✅ COMPLETE
**Effort: ~1 day**

Replace the procedural polygon aliens with hand-crafted pixel art sprites drawn on pygame Surfaces. The classic arcade had three alien types — **Squid** (top row), **Crab** (middle rows), **Octopus** (bottom rows) — each with 2 animation frames. Recreating these with a neon palette would be an instant visual upgrade and immediately recognisable to anyone who's ever played the original. The two draw functions (`draw_alien_a`, `draw_alien_b`) make this a clean swap: build pre-rendered sprite surfaces in `__init__` and blit them instead. Could also add a third animation style for the new Splitter alien. This is the single biggest visual improvement available.

---

### 19. Sector Themes (Visual Environment Progression) ✅ COMPLETE
**Effort: ~4-5 hours**

Divide the game into "sectors" of 10 waves each, each with a distinct visual environment:

- **Sector 1 (waves 1-10):** Current deep-blue space ✓
- **Sector 2 (waves 11-20):** Nebula — background shifts to deep purple/magenta, stars tinted pink, subtle slow-moving cloud particles.
- **Sector 3 (waves 21-30):** Asteroid belt — occasional rocky debris crosses the screen (purely visual, no collision).
- **Sector 4 (waves 31-40):** Near a sun — orange/amber background tint, heat shimmer effect on CRT overlay.
- **Sector 5 (waves 41+):** Deep space anomaly — black with occasional distant galaxy spirals, alien colours shift to monochrome then back.

Each sector transition plays a brief "entering sector X" wipe animation. The game's narrative identity would jump dramatically from "Space Invaders clone" to something with genuine atmosphere.

---

### 28. Bloom / Glow Post-Processing ⏳ APPROVED — PENDING CREDITS
**Effort: ~30–45 mins**

Render the frame to an offscreen surface, scale it to ¼ size, scale it back up (the round-trip creates a natural box blur), then blit it back onto the frame with `pygame.BLEND_ADD` at low alpha. Two or three passes at different scales gives convincing soft neon glow around all bright objects — lasers, explosions, the boss — without any GPU shader code. This single effect is responsible for most of the "expensive indie shooter" aesthetic. Includes a safe fallback in case the scaling passes affect frame rate at 1920×1080.

---

### 20. Survival & Time Attack Game Modes
**Effort: ~4 hours**

Two new modes selectable from the title screen:

- **Survival Mode:** No upgrades, no wave structure — aliens spawn in endless waves that get progressively faster and denser. One life only. Pure score. Leaderboard separate from the main one. Appeals to hardcore players who want a no-frills test.
- **Time Attack:** Clear exactly 10 waves as fast as possible. Timer runs from wave 1, stops at wave 10 completion (or first death). The scoreboard shows times, not points. Gives speedrunners something to optimise.

Both modes reuse all existing code — the main work is the mode selection screen and the separate score tracking.

---

### 21. Roguelite Meta-Progression
**Effort: ~1 day**

Add a "hangar" between sessions: an out-of-run currency ("Scrap") earned for score milestones and achievements. Spent in a simple upgrade menu between games on passive starting bonuses:

- Start with 1 extra life
- Start with Rapid Fire pre-equipped
- Enemy bullets start 10% slower
- Barriers start with 4 blocks instead of 3

None of these are individually powerful — they just make a new run feel slightly more prepared. This is the *Vampire Survivors / Hades* model: each run improves you slightly, keeping the game fresh over many sessions. Persistent across launches via the existing JSON persistence layer.

---

## ✦✦✦✦ TIER 4 — Mega Changes
*Transformative. Each is a significant standalone project. Worth planning carefully before starting.*

---

### 22. Progressive Web App (Mobile Version)
**Effort: ~1 week | Already in ideas bank — top priority**

This is the single most important thing on this entire list. The game currently exists as a Windows `.exe`. A web version reaches *everyone* — phone, tablet, Mac, Chromebook — via a single link. The roadmap already identified Phaser.js + GitHub Pages as the path. Key decisions when starting:

- Port the Frenzy system and upgrade system faithfully — these are the game's unique identity.
- Touch controls: virtual joystick on left, fire button on right. Consider auto-fire option for accessibility.
- The procedural audio system will need rebuilding using the Web Audio API, which is actually *more* powerful than pygame's mixer.
- Host on GitHub Pages (free, already have the repo). Add "Add to Home Screen" prompt for the full PWA experience.
- The "built with no coding experience using AI" origin story is genuinely compelling for TikTok/YouTube content.

This is the version that could go viral.

---

### 23. Local Co-op
**Effort: ~1 day | Already in ideas bank**

Two ships, one keyboard: Player 1 on arrows + Space, Player 2 on WASD + Left Ctrl. Both ships on screen simultaneously, each with their own upgrade picks at wave end (offer 2 sets of 3 upgrades). Combined score. One shared life pool or separate pools — both have merit. The Wingman Drone already proves the engine can handle multiple shooting entities. The main work is the UI (two life counters, two upgrade pick sequences) and balancing alien count for two players.

---

### 24. Story Campaign Mode
**Effort: ~3-4 days**

Wrap the game in a minimal narrative: brief text-and-illustration cutscenes between boss waves. No voice acting, no animation — just stark pixel-art stills with scrolling text, like the era of 16-bit RPGs. The boss encounters are the dramatic beats:

> *"INCOMING TRANSMISSION: Admiral, the Mothership has entered the sector. All units are locked and loaded. This is not a drill."*

The story doesn't need to be complex — it just needs to make the player feel like the protagonist of something rather than just grinding waves. Add a final "wave 50" ending screen with a shareable graphic (your score, time, difficulty, kills). This ending screen alone would drive social sharing.

---

### 25. Online Leaderboard
**Effort: ~2-3 days**

A simple backend (a free-tier service like Supabase or a tiny Python Flask API hosted on Railway.app) stores name + score + wave reached + difficulty. The game's existing high-score name entry already collects names. Add a "HALL OF FAME" screen accessible from the title showing the global top 20. This turns a single-player game into a competitive one overnight. Combined with the PWA version, this is the feature that would make players return repeatedly to climb the board.

---

## Recommended order of attack

**✅ Done:** Items 1–8 (Tier 1), items 17, 18, 19 (Tier 3), difficulty rebalance, smoothness pass.

**Next session (quick wins, ~1h15m total):** Items 26, 27, 28 — shockwave rings, player banking, bloom glow. All three are approved and ready to go the moment credits allow.

**After that (meaningful new content):** Pick 2–3 from Tier 2. The Bonus Challenging Stage (#9), Formation Variety (#12), and Animated Title Screen (#15) are the highest-impact per-hour options.

**Future (the big one):** PWA/Mobile (#22). This is the project that changes the game's entire audience. Save it for when the desktop game feels complete.

---

*All ideas above are 100% buildable using the existing modular architecture. The code is well-structured enough that each of these can be implemented as contained changes without rewriting anything.*
