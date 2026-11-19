"""
athlete_store.py — Persistent JSON storage for all athlete profiles.

Each athlete is stored as:
    athletes/<athlete_id>.json

The JSON file contains:
    {
        "id":               str,
        "profile":          dict,
        "fitness":          dict,
        "training_sessions": list,
        "recovery_data":    list,
        "injury_history":   list,
        "ai_results":       dict,
        "saved_at":         str (ISO datetime),
    }

All functions are pure Python stdlib — no external dependencies.
"""

import os
import json
from datetime import datetime

_STORE_DIR = os.path.join(os.path.dirname(__file__), "athletes")


def _ensure_dir():
    os.makedirs(_STORE_DIR, exist_ok=True)


def _path(athlete_id: str) -> str:
    return os.path.join(_STORE_DIR, f"{athlete_id}.json")


def _safe_id(name: str) -> str:
    """Convert a display name to a safe filename-compatible ID."""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name.strip())
    return safe.lower() or "athlete"


# ── Public API ───────────────────────────────────────────────────────────────

def list_athletes() -> list:
    """
    Return a list of dicts: [{"id": str, "name": str, "sport": str, "saved_at": str}, ...]
    sorted alphabetically by name.
    """
    _ensure_dir()
    athletes = []
    for fname in os.listdir(_STORE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(_STORE_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            athletes.append({
                "id":       data.get("id", fname[:-5]),
                "name":     data.get("profile", {}).get("name", "Unknown"),
                "sport":    data.get("profile", {}).get("sport", "—"),
                "saved_at": data.get("saved_at", "—"),
            })
        except Exception:
            pass
    return sorted(athletes, key=lambda a: a["name"].lower())


def save_athlete(athlete_id: str, profile: dict, fitness: dict,
                 training_sessions: list, recovery_data: list,
                 injury_history: list, ai_results: dict = None) -> str:
    """
    Persist all data for one athlete. Returns the athlete_id used.
    If athlete_id is empty, derives one from profile["name"].
    """
    _ensure_dir()
    if not athlete_id:
        base = _safe_id(profile.get("name", "athlete"))
        # Ensure uniqueness
        existing_ids = {a["id"] for a in list_athletes()}
        athlete_id = base
        counter = 2
        while athlete_id in existing_ids:
            athlete_id = f"{base}_{counter}"
            counter += 1

    data = {
        "id":                athlete_id,
        "profile":           profile,
        "fitness":           fitness,
        "training_sessions": training_sessions,
        "recovery_data":     recovery_data,
        "injury_history":    injury_history,
        "ai_results":        ai_results or {},
        "saved_at":          datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    with open(_path(athlete_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return athlete_id


def load_athlete(athlete_id: str) -> dict:
    """
    Load all data for one athlete. Returns the full data dict,
    or None if not found.
    """
    p = _path(athlete_id)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_athlete(athlete_id: str) -> bool:
    """Delete an athlete file. Returns True if deleted, False if not found."""
    p = _path(athlete_id)
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


def athlete_exists(athlete_id: str) -> bool:
    return os.path.exists(_path(athlete_id))
