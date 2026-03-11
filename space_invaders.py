"""
space_invaders.py — Entry point.

Run this file to start the game:
    python space_invaders.py
"""
import pygame

pygame.init()
pygame.mixer.set_num_channels(16)
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

from si_game import Game  # noqa: E402 — pygame must be initialised first

if __name__ == "__main__":
    game = Game()
    game.run()
