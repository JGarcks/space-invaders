# Space Invaders

A neon-themed Space Invaders remake built with Python and Pygame.

## Download & Play (No Python needed)

Pre-built executables are automatically built via GitHub Actions on every push.

| Platform | Download |
|----------|----------|
| Windows | [SpaceInvaders-Windows.exe](../../releases/latest/download/SpaceInvaders-Windows.exe) |
| macOS | [SpaceInvaders-macOS.zip](../../releases/latest/download/SpaceInvaders-macOS.zip) |

> macOS note: If you see "unidentified developer", right-click the app then Open.

## Controls

| Key | Action |
|-----|--------|
| A / Left arrow | Move left |
| D / Right arrow | Move right |
| Space | Shoot |
| P | Pause / Resume |
| Up / Down | Change difficulty (title screen) |
| Left / Right | Cycle ship skin (title screen) |
| ESC | Quit |

## Features

- 3 difficulty modes: Easy, Normal, Hard
- 4 power-ups: Rapid Fire, Spread Shot, Shield, Bomb (screen-clearing nuke)
- Combo multiplier up to 5x with a visible countdown bar
- UFO mystery ship for bonus points (50-300)
- Destructible barriers: 4 bunkers that erode under fire
- Dive-bombing aliens (Galaga-style, from wave 2 onwards)
- Ambient chiptune music (procedurally generated)
- Unlockable ship skins: Cyan, Hot Pink, Gold, Rainbow
- Achievement system: First Blood, Combo Star, UFO Hunter, Nuclear Option, and more
- High score leaderboard (top 5 with initials)
- Neon aesthetic with scanlines, parallax starfield, and screen shake

## Run from Source

```bash
pip install pygame
python space_invaders.py
```

## Build Yourself

```bash
pip install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceInvaders space_invaders.py
```

## Auto-builds

This repo uses GitHub Actions to automatically build executables for Windows and macOS on every push to main. Check the Releases page for the latest downloads.
