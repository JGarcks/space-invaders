"""
Headless smoke tests for all new Harbinger, Colossus, and helper entities.
Verifies that .update() produces valid EnemyBullet / HomingMissile objects
without needing a pygame display or playing to wave 35.

Run:  python test_harbinger_smoke.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
# Minimal surface so draw calls don't crash if accidentally triggered
pygame.display.set_mode((1, 1))

from si_entities import (
    EnemyBullet, HomingMissile,
    Sentinel, Wraith, Leviathan, Archon,
    Colossus, ColossusTurret,
    WeightedPowerUp, SolarFlare, BonusEnemy,
    make_boss, PowerUp,
)
from si_constants import WIDTH, HEIGHT

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")


def validate_bullets(bullets: list, label: str) -> bool:
    """Every returned bullet must be a valid EnemyBullet with float vx/vy."""
    for i, b in enumerate(bullets):
        if not isinstance(b, EnemyBullet):
            check(f"{label} bullet[{i}] type", False,
                  f"expected EnemyBullet, got {type(b).__name__}")
            return False
        for attr in ("x", "y", "vx", "vy"):
            val = getattr(b, attr, None)
            if not isinstance(val, (int, float)):
                check(f"{label} bullet[{i}].{attr}", False,
                      f"expected number, got {type(val)}")
                return False
    return True


# ── Sentinel ─────────────────────────────────────────────────────────────────
print("\n=== Sentinel ===")
s = Sentinel(400, 80)
s.spawn_timer = 0  # clear spawn invuln so it can fire immediately
check("init", s.alive and s.hp > 0)
all_bullets: list[EnemyBullet] = []
# Run 300 frames (5 seconds) — enough for shoot_timer (2.5s) to fire
for _ in range(300):
    bullets = s.update(1 / 60)
    if validate_bullets(bullets, "Sentinel"):
        all_bullets.extend(bullets)
check("fires bullets", len(all_bullets) > 0, f"got {len(all_bullets)}")
check("shield check", isinstance(
    s.is_shot_blocked_by_shield(400, 80), bool))

# ── Wraith ───────────────────────────────────────────────────────────────────
print("\n=== Wraith ===")
w = Wraith(500, 80)
check("init", w.alive and w.hp > 0)
all_missiles: list[HomingMissile] = []
for _ in range(300):  # 5 seconds — enough for teleport + shoot
    missiles = w.update(1 / 60, 400, 600)
    for m in missiles:
        if not isinstance(m, HomingMissile):
            check("missile type", False, f"got {type(m).__name__}")
        else:
            all_missiles.append(m)
check("fires missiles", len(all_missiles) > 0, f"got {len(all_missiles)}")
# Update a missile
if all_missiles:
    m0 = all_missiles[0]
    m0.update(1 / 60, 400, 600)
    check("missile update", True)

# ── Leviathan ────────────────────────────────────────────────────────────────
print("\n=== Leviathan ===")
lev = Leviathan(300, 80)
lev.spawn_timer = 0  # clear spawn invuln
check("init", lev.alive and len(lev.segments) > 0,
      f"segments={len(lev.segments)}")
lev_bullets: list[EnemyBullet] = []
for _ in range(300):
    bullets = lev.update(1 / 60)
    if validate_bullets(bullets, "Leviathan"):
        lev_bullets.extend(bullets)
check("fires bullets", len(lev_bullets) > 0, f"got {len(lev_bullets)}")
# Test hit_segment
score, killed = lev.hit_segment(0, 1)
check("hit_segment returns tuple", isinstance(score, int) and isinstance(killed, int))

# ── Archon ───────────────────────────────────────────────────────────────────
print("\n=== Archon ===")
arc = Archon(600, 80)
check("init", arc.alive and arc.hp > 0)
arc_bullets: list[EnemyBullet] = []
for _ in range(300):  # 5 seconds for beam cycle + shooting
    bullets = arc.update(1 / 60, 400, 600)
    if validate_bullets(bullets, "Archon"):
        arc_bullets.extend(bullets)
check("fires bullets", len(arc_bullets) > 0, f"got {len(arc_bullets)}")
check("is_capturing returns bool", isinstance(arc.is_capturing(), bool))

# ── Colossus ─────────────────────────────────────────────────────────────────
print("\n=== Colossus ===")
col = Colossus(50)
check("init", col.alive and col.turrets_alive == 4)
check("should_shoot is False", col.should_shoot() is False)
col_bullets: list[EnemyBullet] = []
for _ in range(240):  # 4 seconds
    bullets = col.update(1 / 60, 400, 600)
    if validate_bullets(bullets, "Colossus"):
        col_bullets.extend(bullets)
check("fires bullets from turrets", len(col_bullets) > 0,
      f"got {len(col_bullets)}")

# Kill turrets one by one and verify phase transitions
for turret in col.turrets:
    turret.hp = 0
    turret.alive = False
check("core exposed after turrets dead", col.core_exposed is False)
# Need one more update to trigger exposure
col.update(1 / 60, 400, 600)
check("core exposed after update", col.core_exposed is True)
# Core should now take damage
col.take_damage(1)
check("core takes damage", col.hp == col.max_hp - 1)

# ── make_boss routing ────────────────────────────────────────────────────────
print("\n=== make_boss routing ===")
check("wave 50 -> Colossus", type(make_boss(50)).__name__ == "Colossus")
check("wave 70 -> Colossus", type(make_boss(70)).__name__ == "Colossus")
check("wave 55 -> SwarmQueen", type(make_boss(55)).__name__ == "SwarmQueen")
check("wave 25 -> Mothership", type(make_boss(25)).__name__ == "Mothership")

# ── WeightedPowerUp ──────────────────────────────────────────────────────────
print("\n=== WeightedPowerUp ===")
valid_kinds = {"rapid", "spread", "shield", "bomb",
               "homing", "emp", "overcharge", "timewarp"}
for wave in (10, 35, 50):
    kind = WeightedPowerUp.weighted_random_type(wave)
    check(f"wave {wave} kind valid", kind in valid_kinds, f"got '{kind}'")

# ── PowerUp with kind param ─────────────────────────────────────────────────
print("\n=== PowerUp(kind=) ===")
pu = PowerUp(100, 100, kind="homing")
check("PowerUp kind='homing'", pu.kind == "homing")
pu2 = PowerUp(100, 100)
check("PowerUp random kind", pu2.kind in valid_kinds, f"got '{pu2.kind}'")

# ── SolarFlare ───────────────────────────────────────────────────────────────
print("\n=== SolarFlare ===")
sf = SolarFlare()
check("init idle", sf.state == SolarFlare.STATE_IDLE)
# Fast-forward to warning
for _ in range(1000):
    sf.update(1 / 60)
check("transitions from idle", sf.state != SolarFlare.STATE_IDLE or sf.timer < 15)
# Run enough to cycle through all states
for _ in range(2000):
    sf.update(1 / 60)
check("is_hitting returns bool", isinstance(sf.is_hitting(400, 300), bool))

# ── BonusEnemy ───────────────────────────────────────────────────────────────
print("\n=== BonusEnemy ===")
path = [(0, 0), (400, 200), (800, 0)]
be = BonusEnemy(path, speed=200, delay=0)
check("init alive", be.alive)
for _ in range(300):
    be.update(1 / 60)
check("traverses path", be.x != 0 or be.y != 0 or not be.alive)

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    exit(1)
