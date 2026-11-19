"""
Synthetic athlete data generator — pure Python stdlib only (no pandas/numpy).
Generates realistic training, injury, recovery and wellness data for one athlete.
"""

import random
import math
from datetime import datetime, timedelta

SPORTS = ["Running", "Cycling", "Swimming", "Weightlifting", "Football"]
INJURY_TYPES = ["Hamstring Strain", "Knee Sprain", "Shin Splints",
                "Lower Back Pain", "Ankle Sprain"]
RECOVERY_METHODS = ["Ice Bath", "Massage", "Stretching", "Rest", "Physiotherapy"]
SEVERITY = ["Mild", "Moderate", "Severe"]


def _rng(seed):
    """Return a seeded Random instance."""
    r = random.Random(seed)
    return r


def generate_athlete_profile(athlete_id: int = 1) -> dict:
    r = _rng(athlete_id)
    return {
        "athlete_id": athlete_id,
        "name": f"Athlete_{athlete_id:03d}",
        "age": r.randint(18, 35),
        "sport": r.choice(SPORTS),
        "experience_years": r.randint(1, 15),
        "weight_kg": round(r.uniform(55, 100), 1),
        "height_cm": r.randint(160, 200),
    }


def generate_training_sessions(athlete_id: int = 1, days: int = 90,
                                end_date: datetime = None) -> list:
    """
    Returns a list of dicts, each representing one training session.
    Keys: date, athlete_id, duration_min, intensity, running_distance_km,
          avg_heart_rate, max_speed_kmh, repetitions, performance_score
    """
    r = _rng(athlete_id * 7)
    if end_date is None:
        end_date = datetime.today()

    base_perf = 60 + r.randint(0, 20)
    records = []
    for i in range(days):
        day = end_date - timedelta(days=(days - 1 - i))
        if r.random() < 0.15:          # ~15% rest days
            continue
        intensity = r.randint(4, 9)
        perf = min(100, int(base_perf + i * 0.15 + r.randint(-8, 8)))
        records.append({
            "date": day.strftime("%Y-%m-%d"),
            "athlete_id": athlete_id,
            "duration_min": r.randint(30, 120),
            "intensity": intensity,
            "running_distance_km": round(r.uniform(2, 20), 2),
            "avg_heart_rate": r.randint(120, 184),
            "max_speed_kmh": round(r.uniform(10, 35), 1),
            "repetitions": r.randint(10, 100),
            "performance_score": perf,
        })
    return records


def generate_injury_history(athlete_id: int = 1) -> list:
    r = _rng(athlete_id * 13)
    n = r.randint(0, 3)
    records = []
    for _ in range(n):
        d = datetime.today() - timedelta(days=r.randint(30, 730))
        records.append({
            "athlete_id": athlete_id,
            "injury_type": r.choice(INJURY_TYPES),
            "date": d.strftime("%Y-%m-%d"),
            "recovery_days": r.randint(7, 60),
            "severity": r.choice(SEVERITY),
        })
    return records


def generate_fitness_assessment(athlete_id: int = 1) -> dict:
    r = _rng(athlete_id * 3)
    return {
        "athlete_id": athlete_id,
        "vo2_max": round(r.uniform(35, 75), 1),
        "resting_heart_rate": r.randint(45, 74),
        "flexibility_score": round(r.uniform(4, 10), 1),
        "strength_index": round(r.uniform(4, 10), 1),
        "body_fat_pct": round(r.uniform(8, 25), 1),
        "assessment_date": datetime.today().strftime("%Y-%m-%d"),
    }


def generate_recovery_data(athlete_id: int = 1, days: int = 30,
                            end_date: datetime = None) -> list:
    r = _rng(athlete_id * 17)
    if end_date is None:
        end_date = datetime.today()
    records = []
    for i in range(days):
        day = end_date - timedelta(days=(days - 1 - i))
        records.append({
            "date": day.strftime("%Y-%m-%d"),
            "athlete_id": athlete_id,
            "sleep_hours": round(r.uniform(5, 9), 1),
            "sleep_quality": r.randint(4, 10),
            "recovery_method": r.choice(RECOVERY_METHODS),
            "muscle_soreness": r.randint(1, 9),
            "stress_level": r.randint(1, 9),
            "hydration_level": r.randint(4, 10),
            "hrv": r.randint(30, 99),
        })
    return records


def get_full_athlete_data(athlete_id: int = 1) -> dict:
    return {
        "profile": generate_athlete_profile(athlete_id),
        "training_sessions": generate_training_sessions(athlete_id),
        "injury_history": generate_injury_history(athlete_id),
        "fitness_assessment": generate_fitness_assessment(athlete_id),
        "recovery_data": generate_recovery_data(athlete_id),
    }


if __name__ == "__main__":
    d = get_full_athlete_data(1)
    print("Profile:", d["profile"])
    print("Training sessions:", len(d["training_sessions"]))
    print("Last session:", d["training_sessions"][-1])
    print("Injuries:", d["injury_history"])
    print("Fitness:", d["fitness_assessment"])
    print("Last recovery:", d["recovery_data"][-1])
