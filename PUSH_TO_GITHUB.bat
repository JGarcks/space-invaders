@echo off
REM Run this from your SpaceInvaders folder to commit and push the refactor.
REM Double-click it, or paste the commands into a Command Prompt.

cd /d "%~dp0"

git add si_constants.py si_audio.py si_entities.py si_persistence.py si_game.py space_invaders.py DESIGN_ROADMAP.md tests\test_logic.py tests\__init__.py

git commit -m "Refactor: modular architecture, typed dataclasses, enums, unit tests

- Split 2863-line monolith into si_constants, si_audio, si_entities,
  si_persistence, si_game modules
- Alien/Bullet/EnemyBullet converted from plain dicts to @dataclass
- All game states use GameState enum (no more magic strings)
- SoundManager: lazy synthesis via __getattr__ (zero startup cost)
- All sounds routed through self.sfx instead of module-level globals
- Full type hints throughout
- 26 pure-logic unit tests in tests/test_logic.py (no pygame needed)"

git push

echo.
echo Done! Check https://github.com/JGarcks/space-invaders for the new build.
pause
