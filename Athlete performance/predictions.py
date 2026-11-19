"""
predictions.py — Rule-based health & performance prediction engine.
Pure Python stdlib only. No pandas / numpy required.

Analyses the athlete's training, recovery, fitness, and injury data to:
  1. Generate risk predictions (Overtraining, Injury, Burnout, etc.)
  2. Assign severity levels: CRITICAL / WARNING / CAUTION / OK
  3. Produce actionable alert messages
  4. Forecast a 7-day risk trend
"""

from datetime import date, datetime, timedelta
from collections import Counter


# ── Severity constants ───────────────────────────────────────────────────────
CRITICAL = "CRITICAL"
WARNING  = "WARNING"
CAUTION  = "CAUTION"
OK       = "OK"

SEVERITY_ORDER = {OK: 0, CAUTION: 1, WARNING: 2, CRITICAL: 3}


def _avg(lst, key):
    vals = [r[key] for r in lst if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else 0

def _tail(lst, n):
    return lst[-n:] if len(lst) >= n else lst

def _trend(values):
    """Return 'increasing', 'decreasing', or 'stable' for a list of numbers."""
    if len(values) < 3:
        return "stable"
    first_half  = sum(values[:len(values)//2]) / (len(values)//2)
    second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
    diff = second_half - first_half
    if diff > first_half * 0.05:
        return "increasing"
    if diff < -first_half * 0.05:
        return "decreasing"
    return "stable"


# ── Individual prediction checks ─────────────────────────────────────────────

def _check_overtraining(training, fitness):
    """Detect overtraining syndrome risk from load spike + resting HR."""
    alerts = []
    if len(training) < 4:
        return alerts

    last7  = _tail(training, 7)
    last14 = _tail(training, 14)
    all_avg_intensity = _avg(training, "intensity")
    recent_intensity  = _avg(last7, "intensity")
    load_spike_ratio  = recent_intensity / max(all_avg_intensity, 1)

    # Acute:chronic workload ratio
    acute_load  = sum(r["intensity"] * r["duration_min"] for r in last7)
    chronic_load = sum(r["intensity"] * r["duration_min"] for r in last14)
    ac_ratio = (acute_load / 7) / max(chronic_load / 14, 1)

    rhr = fitness.get("resting_heart_rate", 60)

    if ac_ratio > 1.5 or load_spike_ratio > 1.4:
        severity = CRITICAL if ac_ratio > 1.8 else WARNING
        alerts.append({
            "category": "Overtraining Risk",
            "severity": severity,
            "icon": "🔴" if severity == CRITICAL else "🟠",
            "title": "High Acute:Chronic Workload Ratio Detected",
            "detail": (
                f"Your recent training load is **{ac_ratio:.1f}×** your 2-week average. "
                f"Ratios above 1.5 significantly increase soft-tissue injury risk."
            ),
            "recommendation": (
                "Reduce training volume by 30–40% this week. "
                "Include at least 2 full rest days. Monitor for persistent fatigue."
            ),
            "risk_score": min(100, int(ac_ratio * 40)),
        })

    perf_trend = _trend([r["performance_score"] for r in _tail(training, 10)])
    if perf_trend == "decreasing" and recent_intensity >= 6:
        alerts.append({
            "category": "Performance Decline",
            "severity": WARNING,
            "icon": "🟠",
            "title": "Performance Score Declining Despite High Training Load",
            "detail": (
                "Performance scores are trending downward while training intensity remains high. "
                "This is a classic early overtraining indicator."
            ),
            "recommendation": (
                "Consider a deload week. Focus on sleep and nutrition. "
                "Consult a sports coach if the decline persists beyond 2 weeks."
            ),
            "risk_score": 60,
        })

    if rhr > 72:
        alerts.append({
            "category": "Cardiovascular Stress",
            "severity": CAUTION,
            "icon": "🟡",
            "title": "Elevated Resting Heart Rate",
            "detail": (
                f"Resting HR of **{rhr} bpm** is above the optimal range for trained athletes (45–65 bpm). "
                "Elevated RHR can indicate accumulated fatigue or early illness."
            ),
            "recommendation": (
                "Prioritise 8+ hours of sleep. Reduce caffeine intake. "
                "If RHR stays elevated for 3+ days, reduce training intensity."
            ),
            "risk_score": min(100, int((rhr - 55) * 2)),
        })
    return alerts


def _check_injury_risk(training, injuries, fitness):
    """Predict future injury risk from load, history, flexibility, and patterns."""
    alerts = []
    if not training:
        return alerts

    past_count  = len(injuries)
    flexibility = fitness.get("flexibility_score", 7)
    strength    = fitness.get("strength_index", 7)
    last14      = _tail(training, 14)

    # Consecutive high-intensity days
    sorted_sessions = sorted(training, key=lambda r: r["date"])
    consec_hard = 0
    max_consec  = 0
    for s in sorted_sessions[-14:]:
        if s["intensity"] >= 7:
            consec_hard += 1
            max_consec = max(max_consec, consec_hard)
        else:
            consec_hard = 0

    if max_consec >= 4:
        alerts.append({
            "category": "Injury Risk",
            "severity": CRITICAL if max_consec >= 6 else WARNING,
            "icon": "🔴" if max_consec >= 6 else "🟠",
            "title": f"{max_consec} Consecutive High-Intensity Sessions",
            "detail": (
                f"**{max_consec} back-to-back sessions** at intensity ≥7/10 without adequate recovery. "
                "Soft tissue injuries increase dramatically after 3+ consecutive hard days."
            ),
            "recommendation": (
                "Insert a low-intensity or rest day immediately. "
                "No high-intensity work until at least 1 full recovery day is logged."
            ),
            "risk_score": min(100, max_consec * 15),
        })

    if flexibility < 5:
        alerts.append({
            "category": "Injury Risk",
            "severity": WARNING,
            "icon": "🟠",
            "title": "Low Flexibility — Increased Strain Risk",
            "detail": (
                f"Flexibility score of **{flexibility}/10** is below the recommended minimum of 5. "
                "Poor flexibility is a primary risk factor for muscle strains and ligament sprains."
            ),
            "recommendation": (
                "Add 15 minutes of dynamic stretching before each session. "
                "Include yoga or mobility work twice a week."
            ),
            "risk_score": int((5 - flexibility) * 15),
        })

    if past_count >= 2:
        last_injury_types = [inj.get("Injury Type", inj.get("injury_type", "")) for inj in injuries]
        recurrence_types  = [t for t, c in Counter(last_injury_types).items() if c >= 2]
        if recurrence_types:
            alerts.append({
                "category": "Recurrence Risk",
                "severity": WARNING,
                "icon": "🟠",
                "title": f"Recurring Injury Pattern: {', '.join(recurrence_types)}",
                "detail": (
                    f"You have had **{past_count} injuries**, with recurring: "
                    f"**{', '.join(recurrence_types)}**. "
                    "Re-injury probability is 2–8× higher after the first occurrence."
                ),
                "recommendation": (
                    "Schedule a physiotherapy assessment. "
                    "Include targeted strengthening exercises for previously injured areas."
                ),
                "risk_score": min(100, past_count * 20),
            })
        elif past_count >= 3:
            alerts.append({
                "category": "Injury History",
                "severity": CAUTION,
                "icon": "🟡",
                "title": f"High Injury History ({past_count} Recorded Injuries)",
                "detail": (
                    f"**{past_count} past injuries** on record increases baseline re-injury risk."
                ),
                "recommendation": (
                    "Maintain a structured warm-up and cool-down routine. "
                    "Avoid abrupt increases in training load."
                ),
                "risk_score": min(100, past_count * 15),
            })
    return alerts


def _check_recovery(recovery, training):
    """Predict burnout/fatigue from sleep, HRV, stress, and soreness trends."""
    alerts = []
    if len(recovery) < 3:
        return alerts

    last7 = _tail(recovery, 7)

    avg_sleep   = _avg(last7, "sleep_hours")
    avg_quality = _avg(last7, "sleep_quality")
    avg_hrv     = _avg(last7, "hrv")
    avg_stress  = _avg(last7, "stress_level")
    avg_sore    = _avg(last7, "muscle_soreness")
    avg_hydrat  = _avg(last7, "hydration_level")

    hrv_trend    = _trend([r["hrv"]           for r in _tail(recovery, 10)])
    stress_trend = _trend([r["stress_level"]   for r in _tail(recovery, 10)])
    sore_trend   = _trend([r["muscle_soreness"] for r in _tail(recovery, 10)])

    # Sleep deprivation
    if avg_sleep < 6.5:
        alerts.append({
            "category": "Sleep Deprivation",
            "severity": CRITICAL if avg_sleep < 5.5 else WARNING,
            "icon": "🔴" if avg_sleep < 5.5 else "🟠",
            "title": f"Insufficient Sleep — Avg {avg_sleep:.1f} hrs/night",
            "detail": (
                f"Average sleep of **{avg_sleep:.1f} hours** over the past 7 days is critically low. "
                "Athletes require 8–10 hours for full recovery and adaptation."
            ),
            "recommendation": (
                "Target 8–9 hours of sleep per night. "
                "Avoid screens 1 hour before bed. No high-intensity training until sleep improves."
            ),
            "risk_score": min(100, int((7 - avg_sleep) * 25)),
        })
    elif avg_quality < 5:
        alerts.append({
            "category": "Sleep Quality",
            "severity": CAUTION,
            "icon": "🟡",
            "title": f"Poor Sleep Quality — Avg {avg_quality:.1f}/10",
            "detail": (
                f"Sleep quality averaging **{avg_quality:.1f}/10** is impeding recovery. "
                "Poor sleep quality delays muscle repair and hormonal recovery."
            ),
            "recommendation": (
                "Establish a consistent sleep schedule. "
                "Avoid caffeine after 2 PM. Consider magnesium supplementation."
            ),
            "risk_score": int((6 - avg_quality) * 10),
        })

    # HRV decline
    if hrv_trend == "decreasing" and avg_hrv < 45:
        alerts.append({
            "category": "Autonomic Nervous System Fatigue",
            "severity": WARNING,
            "icon": "🟠",
            "title": "HRV Declining — Nervous System Under Stress",
            "detail": (
                f"HRV averaging **{avg_hrv:.0f} ms** and trending downward. "
                "Declining HRV signals accumulated fatigue and reduced readiness."
            ),
            "recommendation": (
                "Reduce training intensity for 3–5 days. "
                "Prioritise breathwork, cold exposure, or meditation to restore HRV."
            ),
            "risk_score": min(100, int((60 - avg_hrv) * 2)),
        })

    # Chronic stress & burnout risk
    if avg_stress >= 7 and stress_trend == "increasing":
        alerts.append({
            "category": "Burnout Risk",
            "severity": CRITICAL if avg_stress >= 8.5 else WARNING,
            "icon": "🔴" if avg_stress >= 8.5 else "🟠",
            "title": f"Rising Stress Levels — Burnout Risk High",
            "detail": (
                f"Stress level averaging **{avg_stress:.1f}/10** and increasing. "
                "Chronic high stress combined with training load leads to burnout syndrome."
            ),
            "recommendation": (
                "Reduce training volume by 50% this week. "
                "Address lifestyle stressors. Consider speaking with a sports psychologist."
            ),
            "risk_score": min(100, int(avg_stress * 11)),
        })

    # Persistent muscle soreness
    if avg_sore >= 7 and sore_trend != "decreasing":
        alerts.append({
            "category": "Muscle Recovery",
            "severity": WARNING,
            "icon": "🟠",
            "title": "Persistent High Muscle Soreness",
            "detail": (
                f"Muscle soreness averaging **{avg_sore:.1f}/10** over 7 days without improvement. "
                "Persistent DOMS indicates incomplete recovery between sessions."
            ),
            "recommendation": (
                "Take 1–2 full rest days. "
                "Use active recovery: ice bath, massage, or gentle swimming."
            ),
            "risk_score": min(100, int(avg_sore * 10)),
        })

    # Dehydration
    if avg_hydrat < 5:
        alerts.append({
            "category": "Hydration",
            "severity": CAUTION,
            "icon": "🟡",
            "title": f"Chronic Under-hydration — Avg {avg_hydrat:.1f}/10",
            "detail": (
                f"Hydration level averaging **{avg_hydrat:.1f}/10**. "
                "Dehydration impairs performance, increases injury risk, and slows recovery."
            ),
            "recommendation": (
                "Drink at least 2–3 litres of water daily. "
                "Increase electrolyte intake during and after training."
            ),
            "risk_score": int((6 - avg_hydrat) * 10),
        })
    return alerts


def _check_performance_plateau(training):
    """Detect performance stagnation over the last 4+ weeks."""
    alerts = []
    if len(training) < 8:
        return alerts

    scores = [r["performance_score"] for r in sorted(training, key=lambda r: r["date"])]
    trend  = _trend(scores[-12:])

    if trend == "stable" and len(scores) >= 10:
        avg_score = sum(scores[-10:]) / 10
        alerts.append({
            "category": "Performance Plateau",
            "severity": CAUTION,
            "icon": "🟡",
            "title": "Performance Plateau Detected",
            "detail": (
                f"Performance score has remained around **{avg_score:.0f}/100** with no significant "
                "improvement over recent sessions. Plateaus indicate the body has adapted to the "
                "current stimulus."
            ),
            "recommendation": (
                "Change your training stimulus: vary intensity zones, add cross-training, "
                "or introduce periodisation (e.g., strength phase)."
            ),
            "risk_score": 35,
        })
    return alerts


def _check_cardiovascular(training):
    """Predict cardiovascular overload from heart rate trends."""
    alerts = []
    if len(training) < 5:
        return alerts

    last7 = _tail(training, 7)
    avg_hr = _avg(last7, "avg_heart_rate")
    hr_trend = _trend([r["avg_heart_rate"] for r in _tail(training, 10)])

    if avg_hr > 175:
        alerts.append({
            "category": "Cardiovascular Overload",
            "severity": CRITICAL if avg_hr > 185 else WARNING,
            "icon": "🔴" if avg_hr > 185 else "🟠",
            "title": f"Dangerously High Training Heart Rate — Avg {avg_hr:.0f} bpm",
            "detail": (
                f"Average training HR of **{avg_hr:.0f} bpm** is in the red zone. "
                "Sustained maximal HR training without recovery raises cardiac stress risk."
            ),
            "recommendation": (
                "Immediately reduce training intensity. "
                "No sessions above 80% max HR until HR normalises. Consult a physician."
            ),
            "risk_score": min(100, int((avg_hr - 155) * 3)),
        })
    elif hr_trend == "increasing" and avg_hr > 160:
        alerts.append({
            "category": "Cardiovascular Stress",
            "severity": CAUTION,
            "icon": "🟡",
            "title": "Training Heart Rate Trending Upward",
            "detail": (
                f"Average HR at {avg_hr:.0f} bpm and rising despite similar training loads. "
                "Rising HR at the same intensity indicates decreasing fitness or fatigue accumulation."
            ),
            "recommendation": (
                "Include 1–2 low-HR aerobic sessions per week (Zone 2: 60–70% max HR). "
                "Reassess training load distribution."
            ),
            "risk_score": 40,
        })
    return alerts


# ── 7-day risk forecast ──────────────────────────────────────────────────────

def _forecast_7day(training, recovery, fitness):
    """
    Project a simple 7-day health risk score (0–100) based on
    current trends using linear extrapolation of recent data.
    """
    today = date.today()
    day_labels = [(today + timedelta(days=i)).strftime("%a %d %b") for i in range(7)]

    # Base risk from current state
    last7_tr  = _tail(training, 7)
    last7_rec = _tail(recovery, 7)

    base_load    = _avg(last7_tr, "intensity") * 10 if last7_tr else 50
    base_sleep   = max(0, (8 - _avg(last7_rec, "sleep_hours")) * 10) if last7_rec else 30
    base_stress  = _avg(last7_rec, "stress_level") * 8 if last7_rec else 40
    base_hrv     = max(0, (60 - _avg(last7_rec, "hrv")) * 1.5) if last7_rec else 20
    base_risk    = min(100, (base_load + base_sleep + base_stress + base_hrv) / 4)

    # Trend direction
    load_trend  = _trend([r["intensity"] for r in _tail(training, 10)]) if len(training) >= 3 else "stable"
    sleep_trend = _trend([r["sleep_hours"] for r in _tail(recovery, 10)]) if len(recovery) >= 3 else "stable"

    direction = 0
    if load_trend  == "increasing":  direction += 3
    if load_trend  == "decreasing":  direction -= 3
    if sleep_trend == "decreasing":  direction += 2
    if sleep_trend == "increasing":  direction -= 2

    forecast_scores = []
    for i in range(7):
        # Apply decay or growth with diminishing effect
        delta = direction * (i + 1) * 0.5
        score = min(100, max(0, base_risk + delta))
        forecast_scores.append(round(score, 1))

    return day_labels, forecast_scores


# ── Main entry point ─────────────────────────────────────────────────────────

def run_predictions(profile, fitness, training, recovery, injuries):
    """
    Run all prediction checks and return a structured result dict:
      {
        "alerts":          list of alert dicts (sorted by severity),
        "overall_risk":    int 0–100,
        "risk_level":      "Low" | "Moderate" | "High" | "Critical",
        "forecast_days":   list[str],
        "forecast_scores": list[float],
        "summary":         str,
      }
    """
    all_alerts = []
    all_alerts += _check_overtraining(training, fitness)
    all_alerts += _check_injury_risk(training, injuries, fitness)
    all_alerts += _check_recovery(recovery, training)
    all_alerts += _check_performance_plateau(training)
    all_alerts += _check_cardiovascular(training)

    # Sort by severity (highest first)
    all_alerts.sort(key=lambda a: SEVERITY_ORDER.get(a["severity"], 0), reverse=True)

    # Overall risk = max individual score, weighted by severity
    if all_alerts:
        overall_risk = min(100, int(
            sum(a["risk_score"] * (SEVERITY_ORDER[a["severity"]] + 1)
                for a in all_alerts)
            / sum(SEVERITY_ORDER[a["severity"]] + 1 for a in all_alerts)
        ))
    else:
        overall_risk = 10  # baseline low risk

    if overall_risk >= 70:
        risk_level = "Critical"
    elif overall_risk >= 45:
        risk_level = "High"
    elif overall_risk >= 25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    critical_count = sum(1 for a in all_alerts if a["severity"] == CRITICAL)
    warning_count  = sum(1 for a in all_alerts if a["severity"] == WARNING)

    if not all_alerts:
        summary = "✅ No significant health risks detected. Keep up the good work!"
    elif critical_count:
        summary = (f"⚠️ **{critical_count} critical alert(s)** require immediate attention. "
                   f"Action is needed now to prevent injury or illness.")
    elif warning_count:
        summary = (f"🟠 **{warning_count} warning(s)** detected. "
                   f"Adjust your training this week to prevent escalation.")
    else:
        summary = "🟡 Minor cautions noted. Monitor trends and follow recommendations."

    forecast_days, forecast_scores = _forecast_7day(training, recovery, fitness)

    return {
        "alerts":          all_alerts,
        "overall_risk":    overall_risk,
        "risk_level":      risk_level,
        "forecast_days":   forecast_days,
        "forecast_scores": forecast_scores,
        "summary":         summary,
    }
