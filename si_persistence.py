"""
si_persistence.py — JSON-backed highscore and achievement persistence.

Isolated here so the Game class doesn't need to know about file paths or
JSON serialisation.  All functions are pure (no module-level side-effects).
"""
from __future__ import annotations

import json

from si_constants import HIGHSCORE_FILE, ACHIEVEMENT_FILE


def load_json(path: str, default: dict) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_highscores() -> dict:
    data = load_json(HIGHSCORE_FILE, {"scores": [], "total_score": 0})
    if "total_score" not in data:
        data["total_score"] = 0
    return data


def save_highscore(name: str, score: int) -> dict:
    data = load_highscores()
    data["scores"].append({"name": name, "score": score})
    data["scores"].sort(key=lambda x: x["score"], reverse=True)
    data["scores"] = data["scores"][:5]
    data["total_score"] = data.get("total_score", 0) + score
    save_json(HIGHSCORE_FILE, data)
    return data


def load_achievements() -> dict:
    return load_json(ACHIEVEMENT_FILE, {"earned": []})


def save_achievement(name: str) -> bool:
    data = load_achievements()
    if name not in data["earned"]:
        data["earned"].append(name)
        save_json(ACHIEVEMENT_FILE, data)
        return True
    return False
