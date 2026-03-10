import pygame
import math
import random
import json
import os
import sys
from array import array

# ── Initialise Pygame ─────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.set_num_channels(16)
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 1920, 1080
FPS = 60
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(GAME_DIR, "highscores.json")
ACHIEVEMENT_FILE = os.path.join(GAME_DIR, "achievements.json")

# ── Colours (Neon Theme) ─────────────────────────────────────────────────────
BG = (10, 10, 46)
CYAN = (0, 255, 255)
HOT_PINK = (255, 0, 255)
LIME = (0, 255, 136)
ORANGE = (255, 136, 0)
YELLOW = (255, 255, 0)
RED = (255, 50, 50)
BLUE = (80, 140, 255)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
DIM_WHITE = (140, 140, 160)

ALIEN_ROW_COLOURS = [HOT_PINK, HOT_PINK, ORANGE, LIME, LIME, HOT_PINK, ORANGE]

SHIP_COLOURS = {
    "Cyan": CYAN,
    "Hot Pink": HOT_PINK,
    "Gold": GOLD,
    "Rainbow": None,
}
SHIP_UNLOCK_THRESHOLDS = [
    (0, "Cyan"),
    (500, "Hot Pink"),
    (2000, "Gold"),
    (5000, "Rainbow"),
]

# ── Game constants ────────────────────────────────────────────────────────────
PLAYER_SPEED = 850
BULLET_SPEED = 1000
ALIEN_START_SPEED = 140
ALIEN_DROP = 32
ALIEN_COLS, ALIEN_ROWS = 10, 5
ALIEN_X_START, ALIEN_Y_START = 330, 140
ALIEN_X_SPACING, ALIEN_Y_SPACING = 140, 72
BASE_SHOOT_COOLDOWN = 0.20
RAPID_SHOOT_COOLDOWN = 0.08
COMBO_WINDOW = 1.5
POWERUP_FALL_SPEED = 200
POWERUP_DURATION = 5.0
INVINCIBILITY_TIME = 2.0
ENEMY_BULLET_SPEED = 450
ENEMY_SHOOT_INTERVAL = 1.4

# ── Extra life milestones ─────────────────────────────────────────────────────
# IMPROVEMENT 2: Award extra lives at these score thresholds
EXTRA_LIFE_MILESTONES = [1000, 3000, 7000, 15000, 30000]

# ── UFO constants ─────────────────────────────────────────────────────────────
UFO_SPEED = 380
UFO_SCORE_VALUES = [50, 100, 150, 200, 250, 300]
UFO_INTERVAL_MIN = 20.0
UFO_INTERVAL_MAX = 40.0
UFO_Y = 68

# ── Barrier constants ─────────────────────────────────────────────────────────
BARRIER_COUNT = 4
BARRIER_Y = HEIGHT - 230
BARRIER_BLOCK_W = 14
BARRIER_BLOCK_H = 10

# ── Dive bomber constants ─────────────────────────────────────────────────────
DIVE_INTERVAL_MIN = 14.0
DIVE_INTERVAL_MAX = 28.0
DIVE_SPEED = 520

# ── Boss constants ────────────────────────────────────────────────────────────
# IMPROVEMENT 6: Boss wave every 5th level
BOSS_WAVE_INTERVAL = 5

# ── Difficulty settings ───────────────────────────────────────────────────────
DIFFICULTIES = ["Easy", "Normal", "Hard"]
DIFFICULTY_SETTINGS = {
    "Easy":   {"speed": 0.70, "fire_rate": 0.60, "powerup": 0.10, "bullet_speed": 0.70},
    "Normal": {"speed": 1.00, "fire_rate": 1.00, "powerup": 0.06, "bullet_speed": 1.00},
    "Hard":   {"speed": 1.40, "fire_rate": 1.50, "powerup": 0.04, "bullet_speed": 1.30},
}

# ── Sound generation ──────────────────────────────────────────────────────────
def _make_sound(frequency, duration_ms, volume=0.3, wave="square"):
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

def _make_sweep(start_freq, end_freq, duration_ms, volume=0.3):
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

def _make_layered_explosion(volume=0.25):
    sample_rate = 44100
    n_samples = int(sample_rate * 0.3)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env = math.exp(-5 * p)
        noise = random.uniform(-1, 1) * env * 0.6
        rumble = math.sin(2 * math.pi * 55 * t) * env * 0.4
        rumble += math.sin(2 * math.pi * 80 * t) * env * 0.3
        val = int(max_amp * (noise + rumble))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound

def _make_level_up_sfx(volume=0.25):
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

def _make_bomb_sfx(volume=0.30):
    """Deep screen-clearing boom."""
    sample_rate = 44100
    n_samples = int(sample_rate * 0.65)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env = math.exp(-3.5 * p)
        noise = random.uniform(-1, 1) * env * 0.5
        bass = math.sin(2 * math.pi * 40 * t) * env * 0.5
        bass += math.sin(2 * math.pi * 28 * t) * env * 0.3
        val = int(max_amp * (noise + bass))
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound

def _make_ufo_sfx(volume=0.12):
    """Looping UFO beacon wobble — 0.5 s chunk."""
    sample_rate = 44100
    n_samples = int(sample_rate * 0.5)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        freq = 440 + 220 * math.sin(2 * math.pi * 4 * t)
        val = int(max_amp * math.sin(2 * math.pi * freq * t) * 0.6)
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound

def _make_dive_sfx(volume=0.15):
    """Quick whoosh when a dive-bomber breaks formation."""
    return _make_sweep(180, 640, 220, volume)

def _make_boss_sfx(volume=0.28):
    """Deep ominous boss arrival sweep."""
    sample_rate = 44100
    n_samples = int(sample_rate * 0.9)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        p = i / n_samples
        env = math.exp(-1.5 * p) * min(1.0, i / 500)
        freq = 220 - 120 * p
        val = int(max_amp * (math.sin(2 * math.pi * freq * t) * 0.6 +
                             math.sin(2 * math.pi * freq * 0.5 * t) * 0.4) * env)
        buf[i] = max(-32768, min(32767, val))
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(volume)
    return sound

def _make_extra_life_sfx(volume=0.30):
    """Bright ascending arpeggio for extra life."""
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

def _make_ambient_loop(volume=0.06):
    """
    ~3.7 s procedural chiptune bass loop (130 BPM, 8 beats).
    Pure-math bass + seeded-noise hi-hat so it's deterministic.
    """
    sample_rate = 44100
    bpm = 130
    beat_dur = 60.0 / bpm          # ≈ 0.4615 s
    n_beats = 8
    n_samples = int(sample_rate * beat_dur * n_beats)
    buf = array("h", [0] * n_samples)
    max_amp = int(32767 * volume)

    # Bass pattern  {beat_index: Hz}
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

    # Hi-hat: short seeded noise burst on every half-beat
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

# ── Create all sounds ─────────────────────────────────────────────────────────
SFX_PEW          = _make_sound(880, 80, 0.15, "square")
SFX_EXPLODE      = _make_layered_explosion(0.25)
SFX_POWERUP      = _make_sweep(400, 1200, 200, 0.25)
SFX_ACHIEVE      = _make_sweep(600, 1400, 300, 0.2)
SFX_DEATH        = _make_sweep(600, 150, 400, 0.3)
SFX_ENEMY_SHOOT  = _make_sound(220, 100, 0.12, "sawtooth")
SFX_PLAYER_HIT   = _make_sound(150, 200, 0.2, "noise")
SFX_LEVEL_UP     = _make_level_up_sfx(0.25)
SFX_UFO_BEACON   = _make_ufo_sfx(0.12)
SFX_UFO_HIT      = _make_sweep(800, 150, 350, 0.28)
SFX_BOMB         = _make_bomb_sfx(0.30)
SFX_DIVE         = _make_dive_sfx(0.15)
SFX_BOSS         = _make_boss_sfx(0.28)
SFX_EXTRA_LIFE   = _make_extra_life_sfx(0.30)
MUSIC_LOOP       = _make_ambient_loop(0.06)

MUSIC_CHANNEL    = pygame.mixer.Channel(14)
UFO_CHANNEL      = pygame.mixer.Channel(15)

# ── Persistence ───────────────────────────────────────────────────────────────
def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_highscores():
    data = load_json(HIGHSCORE_FILE, {"scores": [], "total_score": 0})
    if "total_score" not in data:
        data["total_score"] = 0
    return data

def save_highscore(name, score):
    data = load_highscores()
    data["scores"].append({"name": name, "score": score})
    data["scores"].sort(key=lambda x: x["score"], reverse=True)
    data["scores"] = data["scores"][:5]
    data["total_score"] = data.get("total_score", 0) + score
    save_json(HIGHSCORE_FILE, data)
    return data

def load_achievements():
    return load_json(ACHIEVEMENT_FILE, {"earned": []})

def save_achievement(name):
    data = load_achievements()
    if name not in data["earned"]:
        data["earned"].append(name)
        save_json(ACHIEVEMENT_FILE, data)
        return True
    return False

# ── Particle ──────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, colour, speed=None, angle=None, size=3, life=0.5):
        self.x, self.y = x, y
        self.colour = colour
        self.size = size
        self.life = life
        self.max_life = life
        if angle is None:
            angle = random.uniform(0, 2 * math.pi)
        if speed is None:
            speed = random.uniform(60, 200)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt
        return self.life > 0

    def draw(self, surface, offset):
        alpha = max(0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        c = tuple(int(ch * alpha) for ch in self.colour)
        pygame.draw.circle(surface, c, (int(self.x) + offset[0], int(self.y) + offset[1]), r)

# ── Star (background) ────────────────────────────────────────────────────────
class Star:
    def __init__(self, layer):
        self.layer = layer
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        speed_mult = [0.3, 0.7, 1.2][layer]
        self.speed = 20 + speed_mult * 40
        bright = [60, 120, 200][layer]
        self.colour = (bright, bright, bright + 30)
        self.size = [1, 2, 3][layer]

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface, offset):
        pygame.draw.circle(surface, self.colour,
                           (int(self.x) + offset[0], int(self.y) + offset[1]), self.size)

# ── PowerUp ───────────────────────────────────────────────────────────────────
POWERUP_TYPES   = ["rapid", "spread", "shield", "bomb"]
POWERUP_COLOURS = {"rapid": YELLOW, "spread": CYAN, "shield": BLUE, "bomb": ORANGE}
POWERUP_LABELS  = {"rapid": "RAPID FIRE", "spread": "SPREAD SHOT",
                   "shield": "SHIELD", "bomb": "BOMB"}

class PowerUp:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.kind = random.choice(POWERUP_TYPES)
        self.colour = POWERUP_COLOURS[self.kind]
        self.angle = 0
        self.alive = True

    def update(self, dt):
        self.y += POWERUP_FALL_SPEED * dt
        self.angle += 3 * dt
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surface, offset):
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        r = 16
        pts = []
        for i in range(4):
            a = self.angle + i * math.pi / 2
            pts.append((cx + int(r * math.cos(a)), cy + int(r * math.sin(a))))
        pygame.draw.polygon(surface, self.colour, pts)
        # Label on the powerup so players know what it is
        glow = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.colour, 50), (22, 22), 22)
        surface.blit(glow, (cx - 22, cy - 22))

# ── Achievement Banner ────────────────────────────────────────────────────────
class AchievementBanner:
    def __init__(self, text, font):
        self.text = text
        self.font = font
        self.timer = 3.0
        self.max_timer = 3.0
        self.y_target = 50
        self.y = -40

    def update(self, dt, slot):
        self.y_target = 15 + slot * 70
        self.y += (self.y_target - self.y) * 5 * dt
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface):
        alpha = min(1.0, self.timer / 0.5) if self.timer < 0.5 else 1.0
        txt_surf = self.font.render(f"  {self.text}  ", True, GOLD)
        w, h = txt_surf.get_width() + 24, txt_surf.get_height() + 12
        x = WIDTH - w - 20
        box = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(box, (20, 20, 50, int(200 * alpha)), (0, 0, w, h), border_radius=8)
        pygame.draw.rect(box, (*GOLD, int(255 * alpha)), (0, 0, w, h), 2, border_radius=8)
        box.blit(txt_surf, (12, 6))
        box.set_alpha(int(255 * alpha))
        surface.blit(box, (x, int(self.y)))

# ── Combo / Score popup ───────────────────────────────────────────────────────
class ComboPopup:
    def __init__(self, x, y, multiplier, font, text=None):
        self.x, self.y = x, y
        self.text = text if text else f"x{multiplier}!"
        self.font = font
        self.timer = 0.9
        self.max_timer = 0.9

    def update(self, dt):
        self.y -= 60 * dt
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface, offset):
        alpha = self.timer / self.max_timer
        scale = 1.0 + (1 - alpha) * 0.3
        txt = self.font.render(self.text, True, YELLOW)
        w, h = txt.get_size()
        scaled = pygame.transform.scale(txt, (int(w * scale), int(h * scale)))
        scaled.set_alpha(int(255 * alpha))
        surface.blit(scaled, (int(self.x) + offset[0] - scaled.get_width() // 2,
                              int(self.y) + offset[1] - scaled.get_height() // 2))

# ── UFO ───────────────────────────────────────────────────────────────────────
class UFO:
    def __init__(self):
        if random.random() < 0.5:
            self.x = -70
            self.vx = UFO_SPEED
        else:
            self.x = WIDTH + 70
            self.vx = -UFO_SPEED
        self.y = UFO_Y
        self.score = random.choice(UFO_SCORE_VALUES)
        self.alive = True
        self.anim_timer = 0.0
        self.anim_frame = 0

    def update(self, dt):
        self.x += self.vx * dt
        self.anim_timer += dt
        if self.anim_timer >= 0.18:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        if self.x < -120 or self.x > WIDTH + 120:
            self.alive = False

    def draw(self, surface, offset):
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        # Hull
        pygame.draw.ellipse(surface, RED, (cx - 42, cy - 6, 84, 24))
        # Dome
        pygame.draw.ellipse(surface, HOT_PINK, (cx - 22, cy - 24, 44, 22))
        # Cockpit glass
        pygame.draw.ellipse(surface, (*CYAN, 160), (cx - 10, cy - 20, 20, 14))
        # Blinking lights
        lc = YELLOW if self.anim_frame == 0 else WHITE
        for lx in [-26, -10, 6, 22]:
            pygame.draw.circle(surface, lc, (cx + lx, cy + 6), 4)
        # Glow halo
        glow = pygame.Surface((110, 52), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*RED, 28), (0, 0, 110, 52))
        surface.blit(glow, (cx - 55, cy - 22))

# ── Barrier ───────────────────────────────────────────────────────────────────
_BARRIER_SHAPE = [
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    "XXX    XXX",
    "XX      XX",
]

class Barrier:
    def __init__(self, cx, y):
        bw, bh = BARRIER_BLOCK_W, BARRIER_BLOCK_H
        total_w = len(_BARRIER_SHAPE[0]) * bw
        total_h = len(_BARRIER_SHAPE) * bh
        ox = cx - total_w // 2
        oy = y - total_h // 2
        # Each block: [bx, by, health]
        self.blocks = []
        for row_i, row in enumerate(_BARRIER_SHAPE):
            for col_i, ch in enumerate(row):
                if ch == "X":
                    self.blocks.append([ox + col_i * bw, oy + row_i * bh, 3])
        # IMPROVEMENT 8: Track last destroyed block center for particle spawning
        self.last_destroyed = None

    def check_bullet_hit(self, bx, by):
        self.last_destroyed = None
        for block in self.blocks:
            if block[2] <= 0:
                continue
            if block[0] <= bx <= block[0] + BARRIER_BLOCK_W and \
               block[1] <= by <= block[1] + BARRIER_BLOCK_H:
                block[2] -= 1
                if block[2] == 0:
                    # Store center position so Game can spawn debris particles
                    self.last_destroyed = (
                        block[0] + BARRIER_BLOCK_W // 2,
                        block[1] + BARRIER_BLOCK_H // 2
                    )
                return True
        return False

    @property
    def alive(self):
        return any(b[2] > 0 for b in self.blocks)

    def draw(self, surface, offset):
        ox, oy = offset
        for block in self.blocks:
            if block[2] <= 0:
                continue
            h = block[2]
            colour = LIME if h == 3 else YELLOW if h == 2 else RED
            rect = pygame.Rect(
                block[0] + ox, block[1] + oy,
                BARRIER_BLOCK_W - 1, BARRIER_BLOCK_H - 1
            )
            pygame.draw.rect(surface, colour, rect)
            # Thin top highlight
            pygame.draw.rect(surface, WHITE, (rect.x, rect.y, rect.width, 2))

# ── Dive Bomber ───────────────────────────────────────────────────────────────
class DiveBomber:
    def __init__(self, alien):
        self.x = alien["x"]
        self.y = alien["y"]
        self.colour = alien["colour"]
        self.start_x = alien["x"]
        self.start_y = alien["y"]
        self.phase = "dive"        # "dive" → "return" → alive=False
        self.vx = 0.0
        self.alive = True
        self.returned = False
        self.anim_timer = 0.0
        self.anim_frame = 0

    def update(self, dt, player_x):
        self.anim_timer += dt
        if self.anim_timer >= 0.12:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame

        if self.phase == "dive":
            # Steer horizontally toward player
            dx = player_x - self.x
            self.vx += dx * 2.2 * dt
            self.vx = max(-320, min(320, self.vx))
            self.x += self.vx * dt
            self.y += DIVE_SPEED * dt
            if self.y >= HEIGHT - 80:
                self.phase = "return"
                self.vx = 0.0
        elif self.phase == "return":
            self.x += (self.start_x - self.x) * 3.5 * dt
            self.y -= DIVE_SPEED * 0.75 * dt
            if self.y <= self.start_y:
                self.y = self.start_y
                self.returned = True
                self.alive = False

    def draw(self, surface, offset):
        ox, oy = offset
        draw_fn = draw_alien_a if self.anim_frame == 0 else draw_alien_b
        draw_fn(surface, int(self.x) + ox, int(self.y) + oy, self.colour, 1.25)
        # Trail glow to show it's special
        trail = pygame.Surface((50, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(trail, (*self.colour, 35), (0, 0, 50, 60))
        surface.blit(trail, (int(self.x) + ox - 25, int(self.y) + oy - 30))

# ── Boss ──────────────────────────────────────────────────────────────────────
# IMPROVEMENT 6: Boss that appears every BOSS_WAVE_INTERVAL waves
class Boss:
    def __init__(self, wave):
        self.x = float(WIDTH // 2)
        self.y = 195.0
        self.base_y = 195.0
        self.wave_timer = 0.0
        boss_tier = max(1, wave // BOSS_WAVE_INTERVAL)
        self.max_hp = 12 + boss_tier * 8
        self.hp = self.max_hp
        self.alive = True
        self.vx = min(180 + boss_tier * 25, 360)
        self.shoot_timer = 1.8   # Initial delay before first shot
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.hit_flash = 0.0

    def is_phase2(self):
        return self.hp <= self.max_hp // 2

    def update(self, dt):
        self.wave_timer += dt
        self.anim_timer += dt
        if self.anim_timer >= 0.20:
            self.anim_timer = 0.0
            self.anim_frame = 1 - self.anim_frame
        self.x += self.vx * dt
        self.y = self.base_y + 40.0 * math.sin(self.wave_timer * 1.6)
        if self.x > WIDTH - 140 or self.x < 140:
            self.vx *= -1
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.shoot_timer -= dt

    def should_shoot(self):
        interval = 0.42 if self.is_phase2() else 0.72
        if self.shoot_timer <= 0:
            self.shoot_timer = interval + random.uniform(-0.08, 0.08)
            return True
        return False

    def take_hit(self):
        self.hp -= 1
        self.hit_flash = 0.14
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface, offset):
        ox, oy = offset
        cx, cy = int(self.x) + ox, int(self.y) + oy
        flashing = self.hit_flash > 0
        phase2 = self.is_phase2()

        # Outer glow
        glow_col = (255, 50, 50, 22) if phase2 else (255, 0, 255, 18)
        glow = pygame.Surface((280, 140), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, glow_col, (0, 0, 280, 140))
        surface.blit(glow, (cx - 140, cy - 70))

        hull_col = WHITE if flashing else (RED if phase2 else HOT_PINK)
        dome_col = WHITE if flashing else (ORANGE if phase2 else HOT_PINK)

        # Phase 2: spinning threat spokes
        if phase2:
            for spoke in range(8):
                a = math.radians(spoke * 45 + self.wave_timer * 55)
                sx = cx + int(118 * math.cos(a))
                sy = cy + int(30 * math.sin(a))
                pygame.draw.line(surface, (*RED, 120), (cx, cy), (sx, sy), 1)

        # Main hull
        pygame.draw.ellipse(surface, hull_col, (cx - 110, cy - 22, 220, 60))
        # Inner hull panel
        pygame.draw.ellipse(surface, BG,       (cx - 88,  cy - 12, 176, 40))
        pygame.draw.ellipse(surface, hull_col, (cx - 88,  cy - 12, 176, 40), 2)

        # Dome
        pygame.draw.ellipse(surface, dome_col, (cx - 60,  cy - 68, 120, 62))
        # Cockpit glass
        pygame.draw.ellipse(surface, CYAN,     (cx - 30,  cy - 60,  60, 38))
        glass_glow = pygame.Surface((60, 38), pygame.SRCALPHA)
        pygame.draw.ellipse(glass_glow, (*CYAN, 70), (0, 0, 60, 38))
        surface.blit(glass_glow, (cx - 30, cy - 60))

        # Blinking engine lights
        lc = YELLOW if self.anim_frame == 0 else ORANGE
        for lx in [-80, -52, -24, 4, 32, 60, 80]:
            pygame.draw.circle(surface, lc, (cx + lx, cy + 22), 6)

        # HP bar above boss
        bar_w = 220
        bar_h = 12
        hp_frac = self.hp / self.max_hp
        bar_col = LIME if hp_frac > 0.5 else YELLOW if hp_frac > 0.25 else RED
        bx = cx - bar_w // 2
        by_ = cy - 92
        pygame.draw.rect(surface, (25, 25, 25), (bx, by_, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(surface, bar_col,      (bx, by_, int(bar_w * hp_frac), bar_h), border_radius=4)
        pygame.draw.rect(surface, WHITE,         (bx, by_, bar_w, bar_h), 1, border_radius=4)

# ── Draw helpers ──────────────────────────────────────────────────────────────
def draw_ship(surface, x, y, colour, size=1.0):
    w, h = int(30 * size), int(36 * size)
    pts = [
        (x, y - h),
        (x - w, y + h // 2),
        (x - w // 3, y),
        (x + w // 3, y),
        (x + w, y + h // 2),
    ]
    pygame.draw.polygon(surface, colour, pts)
    # Cockpit highlight
    pygame.draw.circle(surface, WHITE, (x, y - int(h * 0.3)), max(1, int(4 * size)))
    # Thruster flame (animated)
    t = pygame.time.get_ticks() / 1000.0
    flame_h = int((10 + 6 * math.sin(t * 15)) * size)
    flame_w = int(8 * size)
    flame_pts = [
        (x - flame_w, y + h // 2),
        (x, y + h // 2 + flame_h),
        (x + flame_w, y + h // 2),
    ]
    flame_col = ORANGE if int(t * 20) % 2 == 0 else YELLOW
    pygame.draw.polygon(surface, flame_col, flame_pts)
    # Inner flame
    inner_h = int(flame_h * 0.6)
    inner_w = int(flame_w * 0.5)
    inner_pts = [
        (x - inner_w, y + h // 2),
        (x, y + h // 2 + inner_h),
        (x + inner_w, y + h // 2),
    ]
    pygame.draw.polygon(surface, WHITE, inner_pts)
    # Engine glow
    glow_surf = pygame.Surface((int(24 * size), int(16 * size)), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_surf, (*ORANGE, 80), glow_surf.get_rect())
    surface.blit(glow_surf, (x - int(12 * size), y + h // 2 - int(4 * size)))

def draw_alien_a(surface, x, y, colour, size=1.0):
    w, h = int(22 * size), int(18 * size)
    s = size
    pts = [
        (x - w, y - h), (x - w - int(7*s), y - h - int(10*s)),
        (x - w + int(7*s), y - h),
        (x - int(5*s), y - h - int(4*s)),
        (x + int(5*s), y - h - int(4*s)),
        (x + w - int(7*s), y - h),
        (x + w + int(7*s), y - h - int(10*s)), (x + w, y - h),
        (x + w + int(3*s), y),
        (x + w, y + h),
        (x + w // 2, y + h + int(7*s)),
        (x + int(4*s), y + h + int(3*s)),
        (x, y + h),
        (x - int(4*s), y + h + int(3*s)),
        (x - w // 2, y + h + int(7*s)),
        (x - w, y + h),
        (x - w - int(3*s), y),
    ]
    pygame.draw.polygon(surface, colour, pts)
    eye_r = max(1, int(5*s))
    pygame.draw.circle(surface, BG, (x - int(7*s), y - int(3*s)), eye_r)
    pygame.draw.circle(surface, BG, (x + int(7*s), y - int(3*s)), eye_r)
    hr = max(1, int(2*s))
    pygame.draw.circle(surface, WHITE, (x - int(5*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, WHITE, (x + int(9*s), y - int(5*s)), hr)
    ar = max(1, int(2*s))
    pygame.draw.circle(surface, colour, (x - w - int(7*s), y - h - int(12*s)), ar)
    pygame.draw.circle(surface, colour, (x + w + int(7*s), y - h - int(12*s)), ar)

def draw_alien_b(surface, x, y, colour, size=1.0):
    w, h = int(22 * size), int(18 * size)
    s = size
    pts = [
        (x, y - h - int(5*s)),
        (x - int(8*s), y - h),
        (x - w, y - h), (x - w - int(10*s), y - int(4*s)),
        (x - w - int(12*s), y),
        (x - w - int(10*s), y + int(4*s)),
        (x - w, y + h),
        (x - w // 2, y + h - int(5*s)),
        (x - int(4*s), y + h + int(4*s)),
        (x, y + h),
        (x + int(4*s), y + h + int(4*s)),
        (x + w // 2, y + h - int(5*s)),
        (x + w, y + h),
        (x + w + int(10*s), y + int(4*s)),
        (x + w + int(12*s), y),
        (x + w + int(10*s), y - int(4*s)),
        (x + w, y - h),
        (x + int(8*s), y - h),
    ]
    pygame.draw.polygon(surface, colour, pts)
    eye_r = max(1, int(5*s))
    pygame.draw.circle(surface, BG, (x - int(7*s), y - int(3*s)), eye_r)
    pygame.draw.circle(surface, BG, (x + int(7*s), y - int(3*s)), eye_r)
    hr = max(1, int(2*s))
    pygame.draw.circle(surface, WHITE, (x - int(5*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, WHITE, (x + int(9*s), y - int(5*s)), hr)
    pygame.draw.circle(surface, colour, (x, y - h - int(7*s)), max(1, int(3*s)))

# ── Main Game ─────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        flags = pygame.FULLSCREEN
        try:
            flags |= pygame.SCALED
        except Exception:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Space Invaders")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("consolas", 80, bold=True)
        self.font_lv  = pygame.font.SysFont("consolas", 52, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 36)
        self.font_sm  = pygame.font.SysFont("consolas", 26)
        self.font_xs  = pygame.font.SysFont("consolas", 20)

        # Scanline overlay (cached for performance)
        self.scanline_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for sy in range(0, HEIGHT, 3):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 10), (0, sy), (WIDTH, sy))

        self.stars = []
        for layer in range(3):
            for _ in range([60, 50, 30][layer]):
                self.stars.append(Star(layer))

        self.state = "TITLE"
        self.hs_data = load_highscores()
        self.achv_data = load_achievements()
        self.selected_ship = "Cyan"
        self._unlock_ships()

        self.title_pulse = 0.0

        self.entering_name = False
        self.name_chars = ["A", "A", "A"]
        self.name_cursor = 0
        self.pending_score = 0

        self.difficulty = "Normal"
        self.bomb_flash_timer = 0.0

        self._init_game()

    def _unlock_ships(self):
        total = self.hs_data.get("total_score", 0)
        self.unlocked_ships = []
        for threshold, name in SHIP_UNLOCK_THRESHOLDS:
            if total >= threshold:
                self.unlocked_ships.append(name)

    def _get_ship_colour(self):
        if self.selected_ship == "Rainbow":
            t = pygame.time.get_ticks() / 500
            r = int(127 + 128 * math.sin(t))
            g = int(127 + 128 * math.sin(t + 2.09))
            b = int(127 + 128 * math.sin(t + 4.19))
            return (r, g, b)
        return SHIP_COLOURS.get(self.selected_ship, CYAN)

    def _init_game(self):
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT - 80
        self.lives = 3
        self.score = 0
        self.wave = 1
        self.alien_dir = 1
        self.alien_speed = ALIEN_START_SPEED
        self.shoot_cooldown = 0
        self.bullets = []
        self.aliens = []
        self.enemy_bullets = []
        self.enemy_shoot_timer = 0
        self.enemy_shoot_interval = ENEMY_SHOOT_INTERVAL
        self.enemy_bullet_speed = ENEMY_BULLET_SPEED
        self.current_alien_drop = ALIEN_DROP
        self.powerups = []
        self.particles = []
        self.combo_popups = []
        self.banners = []
        self.combo_count = 0
        self.combo_timer = 0
        self.combo_multiplier = 1
        self.active_powerup = None
        self.powerup_timer = 0
        self.has_shield = False
        self.invincible_timer = 0
        self.alien_anim_timer = 0
        self.alien_frame = 0
        self.shake_timer = 0
        self.shake_intensity = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.wave_damage_taken = False
        self.powerups_collected_wave = 0
        self.bomb_flash_timer = 0.0
        self.ufo = None
        self.ufo_timer = random.uniform(UFO_INTERVAL_MIN, UFO_INTERVAL_MAX)
        self.barriers = self._make_barriers()
        self.dive_bombers = []
        self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
        self.powerup_drop_chance = DIFFICULTY_SETTINGS[self.difficulty]["powerup"]

        # IMPROVEMENT 2: Extra life milestone tracking
        self.next_life_milestone_idx = 0

        # IMPROVEMENT 6: Boss tracking
        self.boss = None

        # IMPROVEMENT 7: Wave summary state
        self.wave_summary_timer = 0.0
        self.wave_summary_data = {}
        self.wave_kills = 0
        self.wave_start_time = pygame.time.get_ticks() / 1000.0

        self._spawn_wave()

    def _make_barriers(self):
        barriers = []
        margin = 280
        spacing = (WIDTH - 2 * margin) // (BARRIER_COUNT - 1)
        for i in range(BARRIER_COUNT):
            cx = margin + i * spacing
            barriers.append(Barrier(cx, BARRIER_Y))
        return barriers

    def _spawn_wave(self):
        self.aliens = []
        self.boss = None

        diff = DIFFICULTY_SETTINGS[self.difficulty]

        # IMPROVEMENT 6: Boss every BOSS_WAVE_INTERVAL waves
        if self.wave % BOSS_WAVE_INTERVAL == 0:
            self.boss = Boss(self.wave)
            SFX_BOSS.play()
        else:
            y_offset = min((self.wave - 1) * 8, 100)
            rows = min(7, ALIEN_ROWS + (self.wave - 1) // 8)
            for row in range(rows):
                for col in range(ALIEN_COLS):
                    ax = ALIEN_X_START + col * ALIEN_X_SPACING
                    ay = ALIEN_Y_START + row * ALIEN_Y_SPACING + y_offset
                    colour = ALIEN_ROW_COLOURS[row % len(ALIEN_ROW_COLOURS)]
                    self.aliens.append({"x": ax, "y": ay, "colour": colour})

        self.alien_dir = 1
        self.alien_speed = ALIEN_START_SPEED * (1 + 0.05 * (self.wave - 1)) * diff["speed"]
        self.enemy_shoot_interval = max(
            0.4, (ENEMY_SHOOT_INTERVAL - 0.15 * (self.wave - 1)) / diff["fire_rate"]
        )
        self.enemy_bullet_speed = min(
            650, (ENEMY_BULLET_SPEED + 18 * (self.wave - 1)) * diff["bullet_speed"]
        )
        self.powerup_drop_chance = diff["powerup"]
        self.current_alien_drop = min(50, ALIEN_DROP + self.wave)
        self.enemy_shoot_timer = self.enemy_shoot_interval
        self.enemy_bullets = []
        self.wave_damage_taken = False
        self.powerups_collected_wave = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.dive_bombers = []
        self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
        # IMPROVEMENT 7: Per-wave tracking
        self.wave_kills = 0
        self.wave_start_time = pygame.time.get_ticks() / 1000.0

    def _add_shake(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def _try_achievement(self, name):
        if name not in self.achv_data.get("earned", []):
            if save_achievement(name):
                self.achv_data = load_achievements()
                self.banners.append(AchievementBanner(name, self.font_sm))
                SFX_ACHIEVE.play()

    def _spawn_explosion(self, x, y, colour, count=14):
        for _ in range(count):
            self.particles.append(Particle(x, y, colour,
                                           speed=random.uniform(120, 350),
                                           size=random.uniform(3, 7),
                                           life=random.uniform(0.3, 0.7)))
        for _ in range(count // 3):
            self.particles.append(Particle(x, y, WHITE,
                                           speed=random.uniform(180, 400),
                                           size=random.uniform(1, 3),
                                           life=random.uniform(0.15, 0.35)))

    def _trigger_bomb(self):
        """Detonate a bomb: clear all aliens and enemy bullets."""
        pts = len(self.aliens) * 8
        for a in self.aliens:
            self._spawn_explosion(a["x"], a["y"], a["colour"], count=8)
        for diver in self.dive_bombers:
            self._spawn_explosion(diver.x, diver.y, diver.colour, count=8)
        self.aliens = []
        self.dive_bombers = []
        self.enemy_bullets = []
        self.score += pts
        self._check_life_milestones()
        self._add_shake(12, 0.5)
        SFX_BOMB.play()
        self.bomb_flash_timer = 0.18
        self._try_achievement("Nuclear Option")

    # IMPROVEMENT 2: Check and award extra lives on score milestones
    def _check_life_milestones(self):
        while (self.next_life_milestone_idx < len(EXTRA_LIFE_MILESTONES) and
               self.score >= EXTRA_LIFE_MILESTONES[self.next_life_milestone_idx]):
            self.lives += 1
            self.next_life_milestone_idx += 1
            SFX_EXTRA_LIFE.play()
            self.banners.append(AchievementBanner("EXTRA LIFE!", self.font_sm))
            self.combo_popups.append(ComboPopup(
                WIDTH // 2, HEIGHT // 2, 0, self.font_med, text="+1 LIFE!"
            ))

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self._handle_keydown(event)

            for star in self.stars:
                star.update(dt)

            if self.state == "TITLE":
                self._update_title(dt)
            elif self.state == "PLAYING":
                self._update_playing(dt)
            elif self.state == "PAUSED":
                pass   # freeze — only banners/particles still rendered
            elif self.state == "GAME_OVER":
                self._update_gameover(dt)
            elif self.state == "WAVE_SUMMARY":
                self._update_wave_summary(dt)

            self._draw()

        pygame.quit()
        sys.exit()

    # ── Input ─────────────────────────────────────────────────────────────────
    def _handle_keydown(self, event):
        if self.state == "TITLE":
            if event.key == pygame.K_RETURN:
                self._init_game()
                self.state = "PLAYING"
                MUSIC_CHANNEL.play(MUSIC_LOOP, loops=-1)
            elif event.key == pygame.K_LEFT:
                idx = self.unlocked_ships.index(self.selected_ship) if self.selected_ship in self.unlocked_ships else 0
                idx = (idx - 1) % len(self.unlocked_ships)
                self.selected_ship = self.unlocked_ships[idx]
            elif event.key == pygame.K_RIGHT:
                idx = self.unlocked_ships.index(self.selected_ship) if self.selected_ship in self.unlocked_ships else 0
                idx = (idx + 1) % len(self.unlocked_ships)
                self.selected_ship = self.unlocked_ships[idx]
            elif event.key == pygame.K_UP:
                idx = DIFFICULTIES.index(self.difficulty)
                self.difficulty = DIFFICULTIES[(idx - 1) % len(DIFFICULTIES)]
            elif event.key == pygame.K_DOWN:
                idx = DIFFICULTIES.index(self.difficulty)
                self.difficulty = DIFFICULTIES[(idx + 1) % len(DIFFICULTIES)]

        elif self.state == "PLAYING":
            if event.key == pygame.K_p:
                self.state = "PAUSED"
                MUSIC_CHANNEL.pause()
                if UFO_CHANNEL.get_busy():
                    UFO_CHANNEL.pause()

        elif self.state == "PAUSED":
            if event.key == pygame.K_p or event.key == pygame.K_RETURN:
                self.state = "PLAYING"
                MUSIC_CHANNEL.unpause()
                if self.ufo and self.ufo.alive:
                    UFO_CHANNEL.unpause()

        # IMPROVEMENT 7: Skip wave summary early with SPACE or ENTER
        elif self.state == "WAVE_SUMMARY":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.wave_summary_timer = 0.0

        elif self.state == "GAME_OVER":
            if self.entering_name:
                if event.key == pygame.K_UP:
                    c = ord(self.name_chars[self.name_cursor])
                    c = c + 1 if c < ord("Z") else ord("A")
                    self.name_chars[self.name_cursor] = chr(c)
                elif event.key == pygame.K_DOWN:
                    c = ord(self.name_chars[self.name_cursor])
                    c = c - 1 if c > ord("A") else ord("Z")
                    self.name_chars[self.name_cursor] = chr(c)
                elif event.key == pygame.K_RIGHT:
                    self.name_cursor = min(2, self.name_cursor + 1)
                elif event.key == pygame.K_LEFT:
                    self.name_cursor = max(0, self.name_cursor - 1)
                # IMPROVEMENT 9: Keyboard name entry — type letters directly
                elif pygame.K_a <= event.key <= pygame.K_z:
                    letter = chr(event.key - pygame.K_a + ord('A'))
                    self.name_chars[self.name_cursor] = letter
                    self.name_cursor = min(2, self.name_cursor + 1)
                elif event.key == pygame.K_BACKSPACE and self.name_cursor > 0:
                    self.name_cursor -= 1
                elif event.key == pygame.K_RETURN:
                    name = "".join(self.name_chars)
                    self.hs_data = save_highscore(name, self.pending_score)
                    self._unlock_ships()
                    self.entering_name = False
            else:
                if event.key == pygame.K_r:
                    self.state = "TITLE"

    # ── Title ─────────────────────────────────────────────────────────────────
    def _update_title(self, dt):
        self.title_pulse += dt * 3
        self.particles = [p for p in self.particles if p.update(dt)]

    # ── Wave Summary ──────────────────────────────────────────────────────────
    # IMPROVEMENT 7: Show stats between waves
    def _update_wave_summary(self, dt):
        self.wave_summary_timer -= dt
        self.particles   = [p for p in self.particles if p.update(dt)]
        self.combo_popups = [c for c in self.combo_popups if c.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

        if self.wave_summary_timer <= 0:
            self._spawn_wave()
            self.state = "PLAYING"
            MUSIC_CHANNEL.unpause()

    # ── Playing ───────────────────────────────────────────────────────────────
    def _update_playing(self, dt):
        # Bomb flash countdown (visual only)
        if self.bomb_flash_timer > 0:
            self.bomb_flash_timer -= dt

        keys = pygame.key.get_pressed()

        # ── Player movement ───────────────────────────────────────────────
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED * dt
        self.player_x = max(35, min(WIDTH - 35, self.player_x + dx))

        # ── Player shooting ───────────────────────────────────────────────
        self.shoot_cooldown = max(0, self.shoot_cooldown - dt)
        if keys[pygame.K_SPACE] and self.shoot_cooldown <= 0:
            cooldown = RAPID_SHOOT_COOLDOWN if self.active_powerup == "rapid" else BASE_SHOOT_COOLDOWN
            self.shoot_cooldown = cooldown
            SFX_PEW.play()
            self.shots_fired += 1

            if self.active_powerup == "spread":
                for angle in [-0.15, 0, 0.15]:
                    vx = math.sin(angle) * BULLET_SPEED
                    vy = -math.cos(angle) * BULLET_SPEED
                    self.bullets.append({"x": self.player_x, "y": self.player_y - 40,
                                         "vx": vx, "vy": vy})
            else:
                self.bullets.append({"x": self.player_x, "y": self.player_y - 40,
                                     "vx": 0, "vy": -BULLET_SPEED})

            for _ in range(3):
                self.particles.append(Particle(
                    self.player_x + random.uniform(-6, 6),
                    self.player_y - 42,
                    YELLOW, speed=random.uniform(50, 120),
                    angle=random.uniform(-0.5, 0.5) - math.pi / 2,
                    size=3, life=0.2))

        # ── Move player bullets ───────────────────────────────────────────
        alive_bullets = []
        for b in self.bullets:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if 0 < b["y"] < HEIGHT and 0 < b["x"] < WIDTH:
                alive_bullets.append(b)
        self.bullets = alive_bullets

        # ── Player bullets vs barriers ────────────────────────────────────
        # IMPROVEMENT 8: Spawn debris particles when blocks are destroyed
        barrier_blocked = set()
        for bi, b in enumerate(self.bullets):
            for barrier in self.barriers:
                if barrier.check_bullet_hit(b["x"], b["y"]):
                    barrier_blocked.add(bi)
                    if barrier.last_destroyed:
                        dx2, dy2 = barrier.last_destroyed
                        for _ in range(5):
                            self.particles.append(Particle(
                                dx2, dy2, LIME,
                                speed=random.uniform(50, 140),
                                size=random.uniform(2, 4),
                                life=random.uniform(0.2, 0.4)))
                    break
        if barrier_blocked:
            self.bullets = [b for i, b in enumerate(self.bullets) if i not in barrier_blocked]

        # ── IMPROVEMENT 4: Alien animation speed tied to remaining count ──
        # Fewer aliens → faster animation (classic Space Invaders tension)
        total_aliens_this_wave = ALIEN_COLS * min(7, ALIEN_ROWS + (self.wave - 1) // 8)
        if self.aliens:
            anim_threshold = max(0.08, 0.5 * (len(self.aliens) / max(1, total_aliens_this_wave)))
        else:
            anim_threshold = 0.15
        self.alien_anim_timer += dt
        if self.alien_anim_timer > anim_threshold:
            self.alien_anim_timer -= anim_threshold
            self.alien_frame = 1 - self.alien_frame

        # ── Move aliens ───────────────────────────────────────────────────
        if self.aliens:
            adx = self.alien_dir * self.alien_speed * dt
            for a in self.aliens:
                a["x"] += adx
            min_x = min(a["x"] for a in self.aliens)
            max_x = max(a["x"] for a in self.aliens)
            if max_x > WIDTH - 35 or min_x < 35:
                self.alien_dir *= -1
                for a in self.aliens:
                    a["y"] += self.current_alien_drop
                self.alien_speed += 5

        # ── IMPROVEMENT 3: Only bottom-row aliens shoot ───────────────────
        # Build a set of the lowest alien in each column
        if self.aliens:
            self.enemy_shoot_timer -= dt
            if self.enemy_shoot_timer <= 0:
                # Group by approximate column, find the lowest alien in each
                col_bottoms = {}
                for a in self.aliens:
                    col_key = round(a["x"] / ALIEN_X_SPACING)
                    if col_key not in col_bottoms or a["y"] > col_bottoms[col_key]["y"]:
                        col_bottoms[col_key] = a
                if col_bottoms:
                    shooter = random.choice(list(col_bottoms.values()))
                    self.enemy_bullets.append({
                        "x": shooter["x"],
                        "y": shooter["y"] + 20,
                        "vx": 0,
                        "vy": self.enemy_bullet_speed
                    })
                    SFX_ENEMY_SHOOT.play()
                self.enemy_shoot_timer = self.enemy_shoot_interval + random.uniform(-0.3, 0.3)

        # ── IMPROVEMENT 6: Boss update & shooting ─────────────────────────
        if self.boss and self.boss.alive:
            self.boss.update(dt)
            if self.boss.should_shoot():
                if self.boss.is_phase2():
                    # Phase 2: 3-way aimed spread shot
                    for spread_angle in [-0.22, 0, 0.22]:
                        raw_dx = self.player_x - self.boss.x
                        raw_dy = self.player_y - self.boss.y
                        dist = max(1.0, math.sqrt(raw_dx**2 + raw_dy**2))
                        spd = self.enemy_bullet_speed * 1.1
                        base_vx = (raw_dx / dist) * spd
                        base_vy = (raw_dy / dist) * spd
                        ca = math.cos(spread_angle)
                        sa = math.sin(spread_angle)
                        self.enemy_bullets.append({
                            "x": self.boss.x,
                            "y": self.boss.y + 35,
                            "vx": base_vx * ca - base_vy * sa,
                            "vy": base_vx * sa + base_vy * ca
                        })
                else:
                    # Phase 1: single aimed shot
                    raw_dx = self.player_x - self.boss.x
                    raw_dy = self.player_y - self.boss.y
                    dist = max(1.0, math.sqrt(raw_dx**2 + raw_dy**2))
                    spd = self.enemy_bullet_speed * 1.2
                    self.enemy_bullets.append({
                        "x": self.boss.x,
                        "y": self.boss.y + 35,
                        "vx": (raw_dx / dist) * spd,
                        "vy": (raw_dy / dist) * spd
                    })
                SFX_ENEMY_SHOOT.play()

        # ── Move enemy bullets (supports vx for boss aimed shots) ─────────
        alive_enemy_bullets = []
        for eb in self.enemy_bullets:
            eb["x"] += eb.get("vx", 0) * dt
            eb["y"] += eb["vy"] * dt
            if 0 < eb["y"] < HEIGHT + 20 and 0 < eb["x"] < WIDTH + 50:
                alive_enemy_bullets.append(eb)
        self.enemy_bullets = alive_enemy_bullets

        # ── Enemy bullets vs barriers ─────────────────────────────────────
        enemy_barrier_blocked = set()
        for ei, eb in enumerate(self.enemy_bullets):
            for barrier in self.barriers:
                if barrier.check_bullet_hit(eb["x"], eb["y"]):
                    enemy_barrier_blocked.add(ei)
                    if barrier.last_destroyed:
                        dx2, dy2 = barrier.last_destroyed
                        for _ in range(4):
                            self.particles.append(Particle(
                                dx2, dy2, RED,
                                speed=random.uniform(40, 110),
                                size=random.uniform(2, 3),
                                life=random.uniform(0.15, 0.3)))
                    break
        if enemy_barrier_blocked:
            self.enemy_bullets = [eb for i, eb in enumerate(self.enemy_bullets)
                                   if i not in enemy_barrier_blocked]

        # ── Enemy bullets vs player ───────────────────────────────────────
        hit_indices = []
        for ei, eb in enumerate(self.enemy_bullets):
            if abs(eb["x"] - self.player_x) < 28 and abs(eb["y"] - self.player_y) < 24:
                hit_indices.append(ei)
                self._spawn_explosion(self.player_x, self.player_y, RED, count=8)
                self._player_hit()
        for ei in sorted(hit_indices, reverse=True):
            if ei < len(self.enemy_bullets):
                self.enemy_bullets.pop(ei)

        # ── UFO: spawn timer ──────────────────────────────────────────────
        if self.ufo is None:
            self.ufo_timer -= dt
            if self.ufo_timer <= 0:
                self.ufo = UFO()
                UFO_CHANNEL.play(SFX_UFO_BEACON, loops=-1)
                self.ufo_timer = random.uniform(UFO_INTERVAL_MIN, UFO_INTERVAL_MAX)
        else:
            self.ufo.update(dt)
            if not self.ufo.alive:
                self.ufo = None
                UFO_CHANNEL.stop()
            else:
                # Player bullet vs UFO
                ufo_hit_bi = -1
                for bi, b in enumerate(self.bullets):
                    if abs(b["x"] - self.ufo.x) < 48 and abs(b["y"] - self.ufo.y) < 22:
                        ufo_hit_bi = bi
                        break
                if ufo_hit_bi >= 0:
                    pts = self.ufo.score
                    self._spawn_explosion(self.ufo.x, self.ufo.y, RED, count=22)
                    self.combo_popups.append(ComboPopup(
                        self.ufo.x, self.ufo.y, 0, self.font_med,
                        text=f"+{pts}!"
                    ))
                    self.score += pts
                    self._check_life_milestones()
                    self._add_shake(5, 0.2)
                    SFX_UFO_HIT.play()
                    UFO_CHANNEL.stop()
                    self.ufo.alive = False
                    self.ufo = None
                    self.bullets.pop(ufo_hit_bi)
                    self._try_achievement("UFO Hunter")

        # ── Dive bomber: spawn timer (wave 2+) ────────────────────────────
        if self.wave >= 2 and self.aliens and not self.dive_bombers:
            self.dive_timer -= dt
            if self.dive_timer <= 0:
                idx = random.randint(0, len(self.aliens) - 1)
                diver = DiveBomber(dict(self.aliens[idx]))
                self.aliens.pop(idx)
                self.dive_bombers.append(diver)
                self.dive_timer = random.uniform(DIVE_INTERVAL_MIN, DIVE_INTERVAL_MAX)
                SFX_DIVE.play()

        # ── Update dive bombers ───────────────────────────────────────────
        alive_divers = []
        for diver in self.dive_bombers:
            diver.update(dt, self.player_x)
            if diver.alive:
                alive_divers.append(diver)
            elif diver.returned:
                # Safely returned — put alien back in grid
                self.aliens.append({
                    "x": diver.start_x,
                    "y": diver.start_y,
                    "colour": diver.colour
                })
        self.dive_bombers = alive_divers

        # Dive bomber vs player collision
        for diver in self.dive_bombers:
            if abs(diver.x - self.player_x) < 36 and abs(diver.y - self.player_y) < 36:
                self._spawn_explosion(diver.x, diver.y, diver.colour, count=14)
                diver.alive = False
                self._player_hit()

        # ── Combo timer ───────────────────────────────────────────────────
        self.combo_timer = max(0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo_count = 0
            self.combo_multiplier = 1

        # ── Player bullets vs aliens ──────────────────────────────────────
        bullets_hit = set()
        aliens_hit  = set()
        for bi, b in enumerate(self.bullets):
            for ai, a in enumerate(self.aliens):
                if ai in aliens_hit:
                    continue
                if abs(b["x"] - a["x"]) < 28 and abs(b["y"] - a["y"]) < 24:
                    bullets_hit.add(bi)
                    aliens_hit.add(ai)

        for ai in sorted(aliens_hit, reverse=True):
            a = self.aliens[ai]
            self.combo_count += 1
            self.combo_timer = COMBO_WINDOW
            self.combo_multiplier = min(5, 1 + self.combo_count // 2)
            pts = 10 * self.combo_multiplier
            self.score += pts
            self._check_life_milestones()
            self.shots_hit += 1
            self.wave_kills += 1
            self._spawn_explosion(a["x"], a["y"], a["colour"])
            self._add_shake(3, 0.1)
            SFX_EXPLODE.play()
            if self.combo_multiplier > 1:
                self.combo_popups.append(ComboPopup(a["x"], a["y"],
                                                    self.combo_multiplier, self.font_med))
            if random.random() < self.powerup_drop_chance:
                self.powerups.append(PowerUp(a["x"], a["y"]))
            self.aliens.pop(ai)
            if self.combo_multiplier >= 5:
                self._try_achievement("Combo Star")

        # ── Player bullets vs dive bombers ────────────────────────────────
        for bi, b in enumerate(self.bullets):
            if bi in bullets_hit:
                continue
            for diver in self.dive_bombers:
                if not diver.alive:
                    continue
                if abs(b["x"] - diver.x) < 30 and abs(b["y"] - diver.y) < 28:
                    bullets_hit.add(bi)
                    diver.alive = False
                    self._spawn_explosion(diver.x, diver.y, diver.colour, count=18)
                    self._add_shake(4, 0.12)
                    SFX_EXPLODE.play()
                    pts = 50 * self.combo_multiplier
                    self.score += pts
                    self._check_life_milestones()
                    self.combo_count += 1
                    self.combo_timer = COMBO_WINDOW
                    self.combo_multiplier = min(5, 1 + self.combo_count // 2)
                    self.wave_kills += 1
                    break

        # ── IMPROVEMENT 6: Player bullets vs boss ─────────────────────────
        if self.boss and self.boss.alive:
            for bi, b in enumerate(self.bullets):
                if bi in bullets_hit:
                    continue
                if abs(b["x"] - self.boss.x) < 108 and abs(b["y"] - self.boss.y) < 42:
                    bullets_hit.add(bi)
                    self.shots_hit += 1
                    killed = self.boss.take_hit()
                    self._add_shake(3, 0.1)
                    SFX_EXPLODE.play()
                    if killed:
                        pts = 500 + self.wave * 50
                        self.score += pts
                        self._check_life_milestones()
                        self.combo_popups.append(ComboPopup(
                            int(self.boss.x), int(self.boss.y), 0,
                            self.font_med, text=f"+{pts}!"
                        ))
                        # Big multi-stage explosion
                        for _ in range(3):
                            ox_ = random.randint(-60, 60)
                            oy_ = random.randint(-30, 30)
                            self._spawn_explosion(int(self.boss.x) + ox_,
                                                  int(self.boss.y) + oy_, RED, count=18)
                        self._spawn_explosion(int(self.boss.x), int(self.boss.y), GOLD, count=30)
                        self._spawn_explosion(int(self.boss.x), int(self.boss.y), WHITE, count=20)
                        # Drop 3 power-ups
                        for i in range(3):
                            self.powerups.append(PowerUp(
                                int(self.boss.x) + random.randint(-100, 100),
                                int(self.boss.y)
                            ))
                        self._add_shake(16, 0.7)
                        self.boss = None
                        self._try_achievement("Boss Slayer")
                    break

        for bi in sorted(bullets_hit, reverse=True):
            if bi < len(self.bullets):
                self.bullets.pop(bi)

        if aliens_hit and self.score > 0:
            self._try_achievement("First Blood")

        # ── Power-ups ─────────────────────────────────────────────────────
        alive_powerups = []
        for pu in self.powerups:
            pu.update(dt)
            if pu.alive:
                if abs(pu.x - self.player_x) < 36 and abs(pu.y - self.player_y) < 36:
                    SFX_POWERUP.play()
                    self.powerups_collected_wave += 1
                    if pu.kind == "shield":
                        self.has_shield = True
                    elif pu.kind == "bomb":
                        self._trigger_bomb()
                        self._try_achievement("Nuclear Option")
                    else:
                        self.active_powerup = pu.kind
                        self.powerup_timer = POWERUP_DURATION
                    if self.powerups_collected_wave >= 3:
                        self._try_achievement("Power Collector")
                else:
                    alive_powerups.append(pu)
        self.powerups = alive_powerups

        if self.active_powerup:
            self.powerup_timer -= dt
            if self.powerup_timer <= 0:
                self.active_powerup = None

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        # ── Alien invasion check ──────────────────────────────────────────
        if self.aliens:
            max_alien_y = max(a["y"] for a in self.aliens)
            if max_alien_y >= self.player_y - 25:
                self._player_hit()

        # ── Particles / popups / banners ──────────────────────────────────
        self.particles    = [p for p in self.particles if p.update(dt)]
        self.combo_popups = [c for c in self.combo_popups if c.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

        if self.shake_timer > 0:
            self.shake_timer -= dt

        # ── Wave clear ────────────────────────────────────────────────────
        # IMPROVEMENT 6: Also wait for boss to be defeated
        if not self.aliens and not self.dive_bombers and self.boss is None:
            if not self.wave_damage_taken:
                self._try_achievement("Untouchable")
            if self.shots_fired > 0 and self.shots_hit / self.shots_fired >= 0.9:
                self._try_achievement("Sharp Shooter")

            cleared_wave = self.wave
            self.wave += 1
            if self.wave == 5:
                self._try_achievement("Wave 5")
            if self.wave == 10:
                self._try_achievement("Wave 10")
            SFX_LEVEL_UP.play()

            # IMPROVEMENT 7: Compute wave summary before spawning next wave
            elapsed = pygame.time.get_ticks() / 1000.0 - self.wave_start_time
            accuracy = (self.shots_hit / self.shots_fired * 100) if self.shots_fired > 0 else 0.0
            perfect_bonus = 500 if not self.wave_damage_taken else 0
            acc_bonus = int(accuracy * 5) if accuracy >= 90.0 else 0
            if perfect_bonus + acc_bonus > 0:
                self.score += perfect_bonus + acc_bonus
                self._check_life_milestones()
            self.wave_summary_data = {
                "wave": cleared_wave,
                "kills": self.wave_kills,
                "accuracy": accuracy,
                "time": elapsed,
                "perfect_bonus": perfect_bonus,
                "acc_bonus": acc_bonus,
            }
            self.wave_summary_timer = 3.5
            self.state = "WAVE_SUMMARY"
            MUSIC_CHANNEL.pause()

    def _player_hit(self):
        # IMPROVEMENT 5: Set invincible immediately to prevent multi-hit in same frame
        if self.invincible_timer > 0:
            return
        self.invincible_timer = 0.01   # Block any further hits this frame

        if self.has_shield:
            self.has_shield = False
            self._spawn_explosion(self.player_x, self.player_y, BLUE, count=20)
            self._add_shake(4, 0.15)
            SFX_PLAYER_HIT.play()
            self.invincible_timer = 0.5
            return

        self.lives -= 1
        self.wave_damage_taken = True
        self._spawn_explosion(self.player_x, self.player_y, self._get_ship_colour(), count=20)
        self._add_shake(6, 0.2)
        SFX_DEATH.play()

        if self.lives <= 0:
            self.state = "GAME_OVER"
            self.pending_score = self.score
            MUSIC_CHANNEL.stop()
            UFO_CHANNEL.stop()
            scores = [s["score"] for s in self.hs_data.get("scores", [])]
            if len(scores) < 5 or self.score > min(scores):
                self.entering_name = True
                self.name_chars = ["A", "A", "A"]
                self.name_cursor = 0
            else:
                self.hs_data["total_score"] = self.hs_data.get("total_score", 0) + self.score
                save_json(HIGHSCORE_FILE, self.hs_data)
                self._unlock_ships()
        else:
            self.invincible_timer = INVINCIBILITY_TIME
            self.player_x = WIDTH // 2

    # ── Game Over ─────────────────────────────────────────────────────────────
    def _update_gameover(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        alive_banners = []
        for i, b in enumerate(self.banners):
            if b.update(dt, i):
                alive_banners.append(b)
        self.banners = alive_banners

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(BG)

        offset = [0, 0]
        if self.shake_timer > 0:
            offset[0] = random.randint(-self.shake_intensity, self.shake_intensity)
            offset[1] = random.randint(-self.shake_intensity, self.shake_intensity)

        for star in self.stars:
            star.draw(self.screen, offset)

        if self.state == "TITLE":
            self._draw_title(offset)
        elif self.state == "PLAYING":
            self._draw_playing(offset)
        elif self.state == "PAUSED":
            self._draw_playing(offset)
            self._draw_paused()
        elif self.state == "GAME_OVER":
            self._draw_gameover(offset)
        elif self.state == "WAVE_SUMMARY":
            self._draw_playing(offset)
            self._draw_wave_summary()

        for p in self.particles:
            p.draw(self.screen, offset)

        for b in self.banners:
            b.draw(self.screen)

        # Bomb flash overlay
        if self.bomb_flash_timer > 0:
            alpha = int(200 * (self.bomb_flash_timer / 0.18))
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 200, 50, alpha))
            self.screen.blit(flash, (0, 0))

        # Scanline overlay
        self.screen.blit(self.scanline_surf, (0, 0))

        pygame.display.flip()

    def _draw_title(self, offset):
        pulse = 0.8 + 0.2 * math.sin(self.title_pulse)
        title = self.font_big.render("SPACE INVADERS", True, CYAN)
        tw, th = title.get_size()
        scaled = pygame.transform.scale(title, (int(tw * pulse), int(th * pulse)))
        self.screen.blit(scaled, (WIDTH // 2 - scaled.get_width() // 2, 120))

        sub = self.font_med.render("Press ENTER to play", True, WHITE)
        if int(pygame.time.get_ticks() / 500) % 2:
            self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 250))

        ship_colour = self._get_ship_colour()
        draw_ship(self.screen, WIDTH // 2, 360, ship_colour, 2.0)
        ship_label = self.font_sm.render(f"< {self.selected_ship} >", True, WHITE)
        self.screen.blit(ship_label, (WIDTH // 2 - ship_label.get_width() // 2, 420))

        # Difficulty selector
        diff_y = 462
        diff_parts = []
        for i, d in enumerate(DIFFICULTIES):
            if d == self.difficulty:
                diff_parts.append((f"[{d}]", GOLD))
            else:
                diff_parts.append((f" {d} ", DIM_WHITE))
        diff_label = self.font_sm.render("DIFFICULTY:", True, WHITE)
        total_parts_w = sum(self.font_sm.size(p[0])[0] for p in diff_parts) + \
                        self.font_sm.size("  |  ")[0] * 2
        full_w = diff_label.get_width() + 16 + total_parts_w
        cx = WIDTH // 2 - full_w // 2
        self.screen.blit(diff_label, (cx, diff_y))
        cx += diff_label.get_width() + 16
        for i, (text, colour) in enumerate(diff_parts):
            t = self.font_sm.render(text, True, colour)
            self.screen.blit(t, (cx, diff_y))
            cx += t.get_width()
            if i < len(diff_parts) - 1:
                sep = self.font_sm.render(" | ", True, DIM_WHITE)
                self.screen.blit(sep, (cx, diff_y))
                cx += sep.get_width()
        diff_hint = self.font_xs.render("Up / Down = change difficulty", True, DIM_WHITE)
        self.screen.blit(diff_hint, (WIDTH // 2 - diff_hint.get_width() // 2, diff_y + 30))

        next_unlock = None
        total = self.hs_data.get("total_score", 0)
        for threshold, name in SHIP_UNLOCK_THRESHOLDS:
            if total < threshold:
                next_unlock = (threshold, name)
                break
        if next_unlock:
            info = self.font_xs.render(
                f"Next unlock: {next_unlock[1]} at {next_unlock[0]} total pts ({total} earned)",
                True, DIM_WHITE
            )
            self.screen.blit(info, (WIDTH // 2 - info.get_width() // 2, 508))

        hs_title = self.font_med.render("HIGH SCORES", True, GOLD)
        self.screen.blit(hs_title, (WIDTH // 2 - hs_title.get_width() // 2, 548))

        scores = self.hs_data.get("scores", [])
        if scores:
            for i, entry in enumerate(scores[:5]):
                txt = self.font_sm.render(f"{i+1}. {entry['name']}  {entry['score']}", True, WHITE)
                self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 596 + i * 40))
        else:
            txt = self.font_sm.render("No scores yet!", True, DIM_WHITE)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 596))

        ctrl = self.font_xs.render(
            "A/D or Arrows = Move  |  Space = Shoot  |  P = Pause  |  ESC = Quit",
            True, DIM_WHITE
        )
        self.screen.blit(ctrl, (WIDTH // 2 - ctrl.get_width() // 2, HEIGHT - 30))

    def _draw_playing(self, offset):
        ox, oy = offset

        # ── IMPROVEMENT 10: Alarm border when aliens approach the player ──
        if self.aliens:
            max_alien_y = max(a["y"] for a in self.aliens)
            danger_zone = HEIGHT - 350
            if max_alien_y > danger_zone:
                danger_frac = min(1.0, (max_alien_y - danger_zone) / 250)
                pulse_alpha = int(60 + 80 * abs(math.sin(pygame.time.get_ticks() / 180)))
                border_alpha = int(pulse_alpha * danger_frac)
                if border_alpha > 0:
                    border_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    bw = 14
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, 0, WIDTH, bw))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, HEIGHT - bw, WIDTH, bw))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (0, 0, bw, HEIGHT))
                    pygame.draw.rect(border_surf, (255, 30, 30, border_alpha),
                                     (WIDTH - bw, 0, bw, HEIGHT))
                    self.screen.blit(border_surf, (0, 0))

        # ── Barriers ─────────────────────────────────────────────────────
        for barrier in self.barriers:
            barrier.draw(self.screen, offset)

        # ── Shield glow ───────────────────────────────────────────────────
        if self.has_shield:
            glow = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*BLUE, 60), (50, 50), 50)
            pygame.draw.circle(glow, (*BLUE, 120), (50, 50), 48, 2)
            self.screen.blit(glow, (int(self.player_x) - 50 + ox, int(self.player_y) - 50 + oy))

        # ── Player ship ───────────────────────────────────────────────────
        if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2:
            pass
        else:
            draw_ship(self.screen, int(self.player_x) + ox, int(self.player_y) + oy,
                      self._get_ship_colour())

        # ── Aliens ───────────────────────────────────────────────────────
        draw_fn = draw_alien_a if self.alien_frame == 0 else draw_alien_b
        for a in self.aliens:
            draw_fn(self.screen, int(a["x"]) + ox, int(a["y"]) + oy, a["colour"])

        # ── Dive bombers ──────────────────────────────────────────────────
        for diver in self.dive_bombers:
            diver.draw(self.screen, offset)

        # ── IMPROVEMENT 6: Draw boss ──────────────────────────────────────
        if self.boss and self.boss.alive:
            self.boss.draw(self.screen, offset)

        # ── UFO ───────────────────────────────────────────────────────────
        if self.ufo:
            self.ufo.draw(self.screen, offset)

        # ── Player bullets ────────────────────────────────────────────────
        for b in self.bullets:
            bx, by = int(b["x"]) + ox, int(b["y"]) + oy
            glow = pygame.Surface((16, 36), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*YELLOW, 30), (0, 0, 16, 36), border_radius=8)
            self.screen.blit(glow, (bx - 8, by - 10))
            trail = pygame.Surface((12, 30), pygame.SRCALPHA)
            pygame.draw.rect(trail, (*YELLOW, 50), (0, 0, 12, 30), border_radius=6)
            self.screen.blit(trail, (bx - 6, by - 6))
            pygame.draw.rect(self.screen, YELLOW, (bx - 3, by - 10, 6, 20), border_radius=3)
            pygame.draw.rect(self.screen, WHITE, (bx - 1, by - 8, 2, 12), border_radius=1)

        # ── Enemy bullets ─────────────────────────────────────────────────
        for eb in self.enemy_bullets:
            ex, ey = int(eb["x"]) + ox, int(eb["y"]) + oy
            glow = pygame.Surface((20, 28), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*HOT_PINK, 40), (0, 0, 20, 28))
            self.screen.blit(glow, (ex - 10, ey - 10))
            pts = [(ex, ey - 10), (ex - 5, ey), (ex, ey + 10), (ex + 5, ey)]
            pygame.draw.polygon(self.screen, RED, pts)
            pygame.draw.circle(self.screen, HOT_PINK, (ex, ey), 3)

        # ── Power-ups ─────────────────────────────────────────────────────
        for pu in self.powerups:
            pu.draw(self.screen, offset)
            # Label overlay so player knows what the powerup does
            lbl = self.font_xs.render(POWERUP_LABELS.get(pu.kind, ""), True, pu.colour)
            lx = int(pu.x) + ox - lbl.get_width() // 2
            ly = int(pu.y) + oy + 22
            self.screen.blit(lbl, (lx, ly))

        # ── Combo popups ──────────────────────────────────────────────────
        for cp in self.combo_popups:
            cp.draw(self.screen, offset)

        self._draw_hud()

    def _draw_hud(self):
        # Score panel
        panel = pygame.Surface((400, 45), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 80), (0, 0, 400, 45), border_radius=6)
        pygame.draw.rect(panel, (*CYAN, 60), (0, 0, 400, 45), 1, border_radius=6)
        self.screen.blit(panel, (10, 6))

        score_txt = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_txt, (20, 12))

        if self.combo_multiplier > 1 and self.combo_timer > 0:
            combo_txt = self.font_med.render(f"x{self.combo_multiplier}", True, YELLOW)
            self.screen.blit(combo_txt, (score_txt.get_width() + 30, 12))

        # Level counter (centre-top)
        lv_str = f"LEVEL {self.wave}"
        # IMPROVEMENT 6: Show BOSS label during boss wave
        is_boss_wave = (self.wave % BOSS_WAVE_INTERVAL == 0)
        if is_boss_wave and self.boss:
            lv_str = f"BOSS  WAVE  {self.wave}"
        lv_col = RED if is_boss_wave and self.boss else GOLD
        lv_txt = self.font_lv.render(lv_str, True, lv_col)
        lv_w, lv_h = lv_txt.get_size()
        lv_x = WIDTH // 2 - lv_w // 2
        lv_y = 6
        lv_panel = pygame.Surface((lv_w + 30, lv_h + 10), pygame.SRCALPHA)
        pygame.draw.rect(lv_panel, (0, 0, 0, 100), (0, 0, lv_w + 30, lv_h + 10), border_radius=8)
        pygame.draw.rect(lv_panel, (*lv_col, 120), (0, 0, lv_w + 30, lv_h + 10), 2, border_radius=8)
        self.screen.blit(lv_panel, (lv_x - 15, lv_y - 2))
        glow_txt = self.font_lv.render(lv_str, True, (*lv_col[:3],))
        glow_txt.set_alpha(60)
        self.screen.blit(glow_txt, (lv_x + 2, lv_y + 2))
        self.screen.blit(lv_txt, (lv_x, lv_y))

        # Lives
        for i in range(self.lives):
            draw_ship(self.screen, WIDTH - 50 - i * 50, 28, self._get_ship_colour(), 0.6)

        # Difficulty badge (top-right, below lives)
        diff_colour = {
            "Easy": LIME, "Normal": CYAN, "Hard": RED
        }.get(self.difficulty, WHITE)
        diff_badge = self.font_xs.render(self.difficulty.upper(), True, diff_colour)
        self.screen.blit(diff_badge, (WIDTH - diff_badge.get_width() - 16, 52))

        # IMPROVEMENT 1: Alien counter
        if self.aliens:
            alien_count_txt = self.font_xs.render(
                f"\u25a0 x{len(self.aliens)}", True, HOT_PINK
            )
            self.screen.blit(alien_count_txt, (WIDTH - alien_count_txt.get_width() - 16, 70))

        # Powerup timer bar
        if self.active_powerup and self.powerup_timer > 0:
            label = POWERUP_LABELS.get(self.active_powerup, "")
            colour = POWERUP_COLOURS.get(self.active_powerup, WHITE)
            bar_w = int(350 * (self.powerup_timer / POWERUP_DURATION))
            pygame.draw.rect(self.screen, (*colour[:3],), (20, 58, bar_w, 14), border_radius=4)
            pygame.draw.rect(self.screen, colour, (20, 58, 350, 14), 1, border_radius=4)
            lbl = self.font_xs.render(label, True, colour)
            self.screen.blit(lbl, (380, 55))

        if self.has_shield:
            sh = self.font_xs.render("SHIELD ACTIVE", True, BLUE)
            self.screen.blit(sh, (20, 78))

        # Combo timer bar
        if self.combo_count > 0 and self.combo_timer > 0:
            bar_x, bar_y = 20, 98
            bar_max_w = 280
            remaining = self.combo_timer / COMBO_WINDOW
            pygame.draw.rect(self.screen, (50, 50, 0), (bar_x, bar_y, bar_max_w, 7),
                             border_radius=3)
            pulse = int(190 + 65 * math.sin(pygame.time.get_ticks() / 90))
            fill_c = (pulse, pulse, 0)
            pygame.draw.rect(self.screen, fill_c,
                             (bar_x, bar_y, int(bar_max_w * remaining), 7),
                             border_radius=3)
            pygame.draw.rect(self.screen, YELLOW, (bar_x, bar_y, bar_max_w, 7), 1,
                             border_radius=3)
            lbl = self.font_xs.render("COMBO", True, YELLOW)
            self.screen.blit(lbl, (bar_x + bar_max_w + 8, bar_y - 4))

        # IMPROVEMENT 2: Show next extra life milestone
        if self.next_life_milestone_idx < len(EXTRA_LIFE_MILESTONES):
            next_ms = EXTRA_LIFE_MILESTONES[self.next_life_milestone_idx]
            needed = next_ms - self.score
            if needed > 0:
                life_txt = self.font_xs.render(f"+1 life at {next_ms}", True, DIM_WHITE)
                self.screen.blit(life_txt, (20, 118))

    def _draw_paused(self):
        """Semi-transparent overlay shown when game is paused."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        t = pygame.time.get_ticks() / 1000.0
        pulse = 0.92 + 0.08 * math.sin(t * 4)
        txt = self.font_big.render("PAUSED", True, CYAN)
        tw, th = txt.get_size()
        scaled = pygame.transform.scale(txt, (int(tw * pulse), int(th * pulse)))
        self.screen.blit(scaled, (WIDTH // 2 - scaled.get_width() // 2,
                                   HEIGHT // 2 - scaled.get_height() // 2 - 30))

        hint = self.font_med.render("Press P or ENTER to resume", True, WHITE)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2,
                                 HEIGHT // 2 + 60))

    # IMPROVEMENT 7: Wave summary screen
    def _draw_wave_summary(self):
        d = self.wave_summary_data
        if not d:
            return

        alpha = 220
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        panel_w, panel_h = 700, 400
        panel_x = WIDTH // 2 - panel_w // 2
        panel_y = HEIGHT // 2 - panel_h // 2

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (10, 10, 50, 220), (0, 0, panel_w, panel_h), border_radius=16)
        pygame.draw.rect(panel, (*GOLD, 180), (0, 0, panel_w, panel_h), 2, border_radius=16)
        self.screen.blit(panel, (panel_x, panel_y))

        cx = WIDTH // 2

        title_txt = self.font_big.render(f"WAVE  {d['wave']}  CLEAR!", True, GOLD)
        self.screen.blit(title_txt, (cx - title_txt.get_width() // 2, panel_y + 24))

        row_y = panel_y + 120
        row_gap = 52

        def stat_row(label, value, colour=WHITE):
            nonlocal row_y
            lbl = self.font_med.render(label, True, DIM_WHITE)
            val = self.font_med.render(value, True, colour)
            self.screen.blit(lbl, (cx - 280, row_y))
            self.screen.blit(val, (cx + 160 - val.get_width(), row_y))
            row_y += row_gap

        stat_row("Enemies destroyed:", str(d["kills"]), LIME)
        stat_row("Accuracy:", f"{d['accuracy']:.0f}%",
                 LIME if d['accuracy'] >= 90 else YELLOW if d['accuracy'] >= 60 else RED)
        stat_row("Time:", f"{d['time']:.1f}s", CYAN)

        if d["perfect_bonus"] > 0:
            stat_row("Perfect wave bonus:", f"+{d['perfect_bonus']}", GOLD)
        if d["acc_bonus"] > 0:
            stat_row("Accuracy bonus:", f"+{d['acc_bonus']}", GOLD)

        # Coming up label
        next_wave = d["wave"] + 1
        is_boss = (next_wave % BOSS_WAVE_INTERVAL == 0)
        next_col = RED if is_boss else WHITE
        next_str = f"BOSS WAVE {next_wave}!" if is_boss else f"Next: Wave {next_wave}"
        next_txt = self.font_sm.render(next_str, True, next_col)
        self.screen.blit(next_txt, (cx - next_txt.get_width() // 2, panel_y + panel_h - 72))

        # Skip hint (blinking)
        if int(pygame.time.get_ticks() / 500) % 2:
            skip_txt = self.font_xs.render("SPACE / ENTER to continue", True, DIM_WHITE)
            self.screen.blit(skip_txt, (cx - skip_txt.get_width() // 2, panel_y + panel_h - 36))

    def _draw_gameover(self, offset):
        draw_fn = draw_alien_a if self.alien_frame == 0 else draw_alien_b
        for a in self.aliens:
            draw_fn(self.screen, int(a["x"]) + offset[0], int(a["y"]) + offset[1], a["colour"])

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        go_txt = self.font_big.render("GAME OVER", True, RED)
        self.screen.blit(go_txt, (WIDTH // 2 - go_txt.get_width() // 2, 280))

        score_txt = self.font_med.render(f"Final Score: {self.score}  |  Level: {self.wave}", True, WHITE)
        self.screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 390))

        if self.entering_name:
            prompt = self.font_med.render("NEW HIGH SCORE! Enter initials:", True, GOLD)
            self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 470))

            for i, ch in enumerate(self.name_chars):
                colour = YELLOW if i == self.name_cursor else WHITE
                char_txt = self.font_big.render(ch, True, colour)
                x = WIDTH // 2 - 80 + i * 70
                self.screen.blit(char_txt, (x, 530))
                if i == self.name_cursor:
                    arrow_up = self.font_sm.render("^", True, colour)
                    arrow_dn = self.font_sm.render("v", True, colour)
                    self.screen.blit(arrow_up, (x + 15, 500))
                    self.screen.blit(arrow_dn, (x + 15, 620))

            confirm = self.font_sm.render("Type letters or use Up/Down arrows, then ENTER", True, DIM_WHITE)
            self.screen.blit(confirm, (WIDTH // 2 - confirm.get_width() // 2, 670))
        else:
            restart = self.font_med.render("Press R to return to title", True, WHITE)
            if int(pygame.time.get_ticks() / 500) % 2:
                self.screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, 500))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = Game()
    game.run()
