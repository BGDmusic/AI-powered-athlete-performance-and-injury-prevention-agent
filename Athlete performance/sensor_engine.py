"""
sensor_engine.py — Wearable Sensor Data Layer
AI-Powered Athlete Performance & Injury Prevention System

Simulates a BLE/ANT+ wearable device streaming live biometric data.
In a real deployment, replace _simulate_reading() with calls to your
device SDK (e.g. Polar H10, Garmin Connect IQ, Apple HealthKit, etc.)

Sensor metrics (all updated every READ_INTERVAL seconds):
  heart_rate      — bpm (60–200)
  spo2            — % blood oxygen (90–100)
  hrv_ms          — HRV in milliseconds (20–120)
  skin_temp_c     — °C (35–39)
  steps           — cumulative steps this session
  cadence_rpm     — steps or pedal strokes per minute
  calories_burned — kcal estimate (cumulative)
  speed_kmh       — GPS/accelerometer speed
  distance_m      — GPS distance covered (metres)

Thresholds used for real-time alert generation:
  CRITICAL — act immediately
  WARNING  — act soon
  CAUTION  — monitor
"""

import math
import time
import random
from datetime import datetime

# ── Sensor read interval (seconds) ───────────────────────────────────────────
READ_INTERVAL = 3   # simulate a reading every 3 s

# ── Physiological thresholds ─────────────────────────────────────────────────
THRESHOLDS = {
    # metric          : (caution_lo, warning_lo, critical_lo,
    #                    caution_hi, warning_hi, critical_hi)
    "heart_rate"      : (None,  None,  None,  165, 180, 195),
    "spo2"            : (96,    94,    91,    None,None,None),   # low is bad
    "hrv_ms"          : (40,    30,    20,    None,None,None),   # low is bad
    "skin_temp_c"     : (None,  None,  None,  37.5,38.0,38.5),
    "speed_kmh"       : (None,  None,  None,  None,None,None),  # informational only
    "cadence_rpm"     : (None,  None,  None,  None,None,None),
    "calories_burned" : (None,  None,  None,  None,None,None),
}

METRIC_LABELS = {
    "heart_rate":      "Heart Rate",
    "spo2":            "SpO₂",
    "hrv_ms":          "HRV",
    "skin_temp_c":     "Skin Temp",
    "steps":           "Steps",
    "cadence_rpm":     "Cadence",
    "calories_burned": "Calories",
    "speed_kmh":       "Speed",
    "distance_m":      "Distance",
}

METRIC_UNITS = {
    "heart_rate":      "bpm",
    "spo2":            "%",
    "hrv_ms":          "ms",
    "skin_temp_c":     "°C",
    "steps":           "steps",
    "cadence_rpm":     "rpm",
    "calories_burned": "kcal",
    "speed_kmh":       "km/h",
    "distance_m":      "m",
}


# ── Simulation state (persists across calls in a process) ─────────────────────
_sim_state = {
    "t":               0,
    "steps":           0,
    "distance_m":      0.0,
    "calories_burned": 0.0,
    "last_hr":         70,
    "last_hrv":        65,
    "last_temp":       36.5,
    "session_phase":   "warmup",   # warmup → active → peak → cooldown
    "phase_elapsed":   0,
}


def _simulate_reading(intensity: int = 6) -> dict:
    """
    Produce one realistic sensor reading based on training intensity (1–10).
    Uses sine waves + noise to mimic wearable variability.
    """
    s = _sim_state
    s["t"] += READ_INTERVAL
    s["phase_elapsed"] += READ_INTERVAL

    # Phase transitions
    if s["session_phase"] == "warmup"   and s["phase_elapsed"] > 120:
        s["session_phase"] = "active";  s["phase_elapsed"] = 0
    elif s["session_phase"] == "active" and s["phase_elapsed"] > 600:
        s["session_phase"] = "peak";    s["phase_elapsed"] = 0
    elif s["session_phase"] == "peak"   and s["phase_elapsed"] > 300:
        s["session_phase"] = "cooldown";s["phase_elapsed"] = 0

    phase_hr_offset = {"warmup": 0, "active": 20, "peak": 40, "cooldown": -15}
    base_hr = 60 + (intensity * 9) + phase_hr_offset.get(s["session_phase"], 0)

    # Smooth HR with noise
    target_hr = base_hr + 10 * math.sin(s["t"] / 40)
    s["last_hr"] = round(s["last_hr"] * 0.85 + target_hr * 0.15
                         + random.gauss(0, 1.5), 1)
    hr = max(50, min(220, s["last_hr"]))

    # HRV inversely related to HR + noise
    target_hrv = max(15, 90 - (hr - 60) * 0.7)
    s["last_hrv"] = round(s["last_hrv"] * 0.80 + target_hrv * 0.20
                          + random.gauss(0, 2), 1)
    hrv = max(10, min(130, s["last_hrv"]))

    # SpO2 — dips slightly under extreme effort
    spo2 = round(99 - max(0, (hr - 150) * 0.05) + random.gauss(0, 0.3), 1)
    spo2 = max(88, min(100, spo2))

    # Skin temperature
    temp_rise = (intensity / 10) * 1.8
    s["last_temp"] = round(s["last_temp"] * 0.95 + (36.5 + temp_rise) * 0.05
                           + random.gauss(0, 0.05), 2)
    skin_temp = max(35.0, min(39.5, s["last_temp"]))

    # Speed & cadence
    speed = round(max(0, (intensity * 1.5) + math.sin(s["t"] / 20) * 1.2
                       + random.gauss(0, 0.4)), 1)
    cadence = round(max(0, 60 + intensity * 8 + random.gauss(0, 3)))

    # Cumulative metrics
    dt_hrs = READ_INTERVAL / 3600
    s["distance_m"]      += speed * 1000 * dt_hrs
    s["steps"]           += cadence * (READ_INTERVAL / 60)
    s["calories_burned"] += (0.0175 * intensity * 2.0 * dt_hrs * 60)

    return {
        "timestamp":       datetime.now().strftime("%H:%M:%S"),
        "heart_rate":      round(hr),
        "spo2":            round(spo2, 1),
        "hrv_ms":          round(hrv, 1),
        "skin_temp_c":     round(skin_temp, 2),
        "speed_kmh":       speed,
        "cadence_rpm":     cadence,
        "steps":           int(s["steps"]),
        "distance_m":      round(s["distance_m"]),
        "calories_burned": round(s["calories_burned"], 1),
        "session_phase":   s["session_phase"],
        "intensity":       intensity,
    }


def reset_simulation():
    """Reset simulation state (call at start of new session)."""
    global _sim_state
    _sim_state = {
        "t": 0, "steps": 0, "distance_m": 0.0, "calories_burned": 0.0,
        "last_hr": 70, "last_hrv": 65, "last_temp": 36.5,
        "session_phase": "warmup", "phase_elapsed": 0,
    }


def get_live_reading(intensity: int = 6, real_data: dict = None) -> dict:
    """
    Public API — returns one sensor reading.
    Pass real_data dict to inject actual wearable values instead of simulating.
    Expected real_data keys (all optional): heart_rate, spo2, hrv_ms,
      skin_temp_c, speed_kmh, cadence_rpm, steps, distance_m, calories_burned
    """
    if real_data:
        reading = _simulate_reading(intensity)   # fills in any missing fields
        reading.update(real_data)                 # override with actual values
        reading["timestamp"] = datetime.now().strftime("%H:%M:%S")
        return reading
    return _simulate_reading(intensity)


def evaluate_thresholds(reading: dict) -> list:
    """
    Compare a sensor reading against physiological thresholds.
    Returns a list of alert dicts:
      { metric, label, value, unit, severity, message, action }
    """
    alerts = []
    for metric, (clo, wlo, crit_lo, chi, whi, crit_hi) in THRESHOLDS.items():
        val = reading.get(metric)
        if val is None:
            continue
        label = METRIC_LABELS.get(metric, metric)
        unit  = METRIC_UNITS.get(metric, "")

        # Check HIGH thresholds
        if crit_hi is not None and val >= crit_hi:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "CRITICAL", f"{label} is dangerously high at {val} {unit}.",
                f"Stop training immediately. Rest and seek medical attention if {label} does not recover within 2 minutes."))
        elif whi is not None and val >= whi:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "WARNING", f"{label} is very high at {val} {unit}.",
                f"Slow down immediately and shift to low-intensity activity. Monitor closely."))
        elif chi is not None and val >= chi:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "CAUTION", f"{label} elevated at {val} {unit}.",
                f"Ease off intensity. Take a short walk/rest and check again in 60 seconds."))

        # Check LOW thresholds
        if crit_lo is not None and val <= crit_lo:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "CRITICAL", f"{label} critically low at {val} {unit}.",
                f"Stop training immediately. Low {label} requires urgent attention."))
        elif wlo is not None and val <= wlo:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "WARNING", f"{label} very low at {val} {unit}.",
                f"Reduce intensity. Rest for 2–3 minutes and re-evaluate."))
        elif clo is not None and val <= clo:
            alerts.append(_make_threshold_alert(metric, label, val, unit,
                "CAUTION", f"{label} lower than normal at {val} {unit}.",
                f"Monitor {label} closely over the next few minutes."))

    return alerts


def _make_threshold_alert(metric, label, value, unit, severity, message, action):
    return {
        "metric":    metric,
        "label":     label,
        "value":     value,
        "unit":      unit,
        "severity":  severity,
        "message":   message,
        "action":    action,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
