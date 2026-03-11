@echo off
REM Push all local commits to GitHub.
REM Double-click this file from the SpaceInvaders folder, or run it in a terminal.

cd /d "%~dp0"

git push

echo.
echo Done! Check https://github.com/JGarcks/space-invaders
pause
