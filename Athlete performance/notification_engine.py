"""
notification_engine.py — In-app notification system for the Athlete Performance System.

Generates structured notifications from prediction results and agent outputs.
Supports severity levels: CRITICAL, WARNING, CAUTION, INFO, SUCCESS.
Pure Python stdlib only — no external dependencies.
"""

from datetime import datetime

# Severity levels
CRITICAL = "CRITICAL"
WARNING  = "WARNING"
CAUTION  = "CAUTION"
INFO     = "INFO"
SUCCESS  = "SUCCESS"

# Notification categories
CAT_INJURY      = "Injury Risk"
CAT_OVERTRAINING = "Overtraining"
CAT_RECOVERY    = "Recovery"
CAT_NUTRITION   = "Nutrition"
CAT_PERFORMANCE = "Performance"
CAT_WELLNESS    = "Wellness"
CAT_SYSTEM      = "System"

SEVERITY_RANK = {CRITICAL: 4, WARNING: 3, CAUTION: 2, INFO: 1, SUCCESS: 0}

SEVERITY_EMOJI = {
    CRITICAL: "🔴",
    WARNING:  "🟠",
    CAUTION:  "🟡",
    INFO:     "🔵",
    SUCCESS:  "🟢",
}

SEVERITY_COLOR = {
    CRITICAL: ("#fee2e2", "#dc2626"),   # bg, border
    WARNING:  ("#ffedd5", "#c2410c"),
    CAUTION:  ("#fefce8", "#a16207"),
    INFO:     ("#eff6ff", "#2563eb"),
    SUCCESS:  ("#f0fdf4", "#16a34a"),
}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_notification(severity, category, title, message, action=None):
    """Build a single notification dict."""
    return {
        "id":        id(title + _now()),
        "severity":  severity,
        "category":  category,
        "title":     title,
        "message":   message,
        "action":    action or "Review the relevant dashboard tab for details.",
        "timestamp": _now(),
        "read":      False,
    }


# ── Notification generators ──────────────────────────────────────────────────

def generate_from_predictions(pred_result: dict) -> list:
    """Convert prediction engine alerts into notification objects."""
    notifications = []
    for alert in pred_result.get("alerts", []):
        sev = alert["severity"]
        # Map prediction severities to notification severities
        sev_map = {"CRITICAL": CRITICAL, "WARNING": WARNING, "CAUTION": CAUTION, "OK": SUCCESS}
        notifications.append(build_notification(
            severity = sev_map.get(sev, INFO),
            category = alert["category"],
            title    = alert["title"],
            message  = alert["detail"],
            action   = alert["recommendation"],
        ))
    return notifications


def generate_from_agent_outputs(agent_outputs: dict) -> list:
    """
    Parse structured text from agent outputs and extract key notifications.
    Looks for keywords to classify severity automatically.
    """
    notifications = []
    keyword_map = {
        CRITICAL: ["immediately", "stop training", "urgent", "critical", "dangerous", "emergency"],
        WARNING:  ["warning", "high risk", "concerning", "escalat", "overtraining", "overload"],
        CAUTION:  ["caution", "monitor", "watch", "moderate risk", "slightly", "borderline"],
        SUCCESS:  ["excellent", "great", "optimal", "well-recovered", "good progress", "low risk"],
    }

    report_map = {
        "performance_report": CAT_PERFORMANCE,
        "injury_risk_report": CAT_INJURY,
        "recovery_report":    CAT_RECOVERY,
        "nutrition_report":   CAT_NUTRITION,
        "training_plan":      CAT_PERFORMANCE,
    }

    for key, category in report_map.items():
        text = agent_outputs.get(key, "")
        if not text or len(text) < 50:
            continue
        text_lower = text.lower()

        matched_sev = INFO
        for sev, keywords in keyword_map.items():
            if any(kw in text_lower for kw in keywords):
                if SEVERITY_RANK[sev] > SEVERITY_RANK[matched_sev]:
                    matched_sev = sev

        # Extract first meaningful sentence as title (up to 100 chars)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 20]
        title = lines[0][:100] + "…" if lines and len(lines[0]) > 100 else (lines[0] if lines else key.replace("_", " ").title())

        # Summary = first 300 chars
        summary = text[:300].strip() + "…" if len(text) > 300 else text.strip()

        notifications.append(build_notification(
            severity = matched_sev,
            category = category,
            title    = f"Agent Report: {category}",
            message  = summary,
            action   = f"See the 🤖 AI Reports tab for the full {category} analysis.",
        ))

    return notifications


def generate_milestone_notifications(training: list, recovery: list, injuries: list) -> list:
    """Generate milestone and progress notifications from raw data."""
    notifications = []

    # First session logged
    if len(training) == 1:
        notifications.append(build_notification(
            SUCCESS, CAT_SYSTEM,
            "🎉 First Training Session Logged!",
            "Great start! Your first training session has been recorded. "
            "Keep logging sessions to unlock performance analytics and predictions.",
            "Log more sessions to see charts in the 📊 Performance tab.",
        ))

    # Every 10 sessions
    if len(training) > 0 and len(training) % 10 == 0:
        notifications.append(build_notification(
            SUCCESS, CAT_PERFORMANCE,
            f"🏆 Milestone: {len(training)} Training Sessions Logged!",
            f"You have now logged {len(training)} training sessions. "
            "Your performance trends are becoming more accurate.",
            "Check your progress in the 📊 Performance tab.",
        ))

    # Injury count warning
    if len(injuries) >= 3:
        notifications.append(build_notification(
            WARNING, CAT_INJURY,
            f"⚠️ {len(injuries)} Injuries on Record — Monitor Carefully",
            f"You have {len(injuries)} recorded injuries. "
            "High injury history increases re-injury probability significantly.",
            "Review the 🩺 Injury Risk tab and consider a physiotherapy consultation.",
        ))

    # Consecutive sessions without recovery log
    if len(training) >= 5 and len(recovery) == 0:
        notifications.append(build_notification(
            CAUTION, CAT_RECOVERY,
            "No Recovery Data Logged Yet",
            "You have logged training sessions but no recovery data. "
            "Recovery tracking is essential for predicting overtraining and injury risk.",
            "Start logging daily recovery in the 💤 Log Recovery tab.",
        ))

    return notifications


def generate_from_sensor(sensor_alerts: list) -> list:
    """
    Convert real-time sensor threshold alerts into notification objects.
    sensor_alerts — list of dicts from sensor_engine.evaluate_thresholds()
    """
    notifications = []
    sev_map = {"CRITICAL": CRITICAL, "WARNING": WARNING, "CAUTION": CAUTION}
    for a in sensor_alerts:
        sev = sev_map.get(a["severity"], CAUTION)
        notifications.append(build_notification(
            severity = sev,
            category = f"🩺 Live Sensor — {a['label']}",
            title    = a["message"],
            message  = (
                f"Real-time reading: **{a['value']} {a['unit']}** "
                f"at {a['timestamp']}. Threshold breached — {a['severity']}."
            ),
            action   = a["action"],
        ))
    return notifications


def get_all_notifications(training, recovery, injuries,
                          pred_result=None, agent_outputs=None,
                          sensor_alerts=None) -> list:
    """
    Collect all notifications from all sources, deduplicate, and sort by severity.
    """
    all_notifs = []
    all_notifs += generate_milestone_notifications(training, recovery, injuries)
    if pred_result:
        all_notifs += generate_from_predictions(pred_result)
    if agent_outputs:
        all_notifs += generate_from_agent_outputs(agent_outputs)
    if sensor_alerts:
        all_notifs += generate_from_sensor(sensor_alerts)

    # Sort: unread + critical first
    all_notifs.sort(key=lambda n: (
        0 if not n["read"] else 1,
        -SEVERITY_RANK.get(n["severity"], 0),
    ))
    return all_notifs


def count_unread(notifications: list) -> dict:
    unread = [n for n in notifications if not n["read"]]
    return {
        "total":    len(unread),
        CRITICAL:   sum(1 for n in unread if n["severity"] == CRITICAL),
        WARNING:    sum(1 for n in unread if n["severity"] == WARNING),
        CAUTION:    sum(1 for n in unread if n["severity"] == CAUTION),
        INFO:       sum(1 for n in unread if n["severity"] == INFO),
        SUCCESS:    sum(1 for n in unread if n["severity"] == SUCCESS),
    }
