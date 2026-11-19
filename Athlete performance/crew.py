"""
crew.py — Assembles and runs the 5-agent Athlete Performance CrewAI crew.

Accepts either:
  - athlete_id (int) → loads auto-generated data from data_generator.py
  - athlete_data     (dict) → uses caller-supplied data (user-entered from dashboard)

Usage:
    python crew.py                           # auto-generated data, athlete 1
    python crew.py --athlete_id 3            # auto-generated data, athlete 3
"""

import argparse
from crewai import Crew, Process

from agents import (
    build_performance_agent,
    build_injury_risk_agent,
    build_recovery_agent,
    build_nutrition_agent,
    build_training_recommendation_agent,
)
from tasks import (
    build_performance_task,
    build_injury_risk_task,
    build_recovery_task,
    build_nutrition_task,
    build_training_recommendation_task,
)


def _get_task_output(task_outputs, idx: int) -> str:
    """Safely extract raw text from a CrewAI task output."""
    try:
        return str(task_outputs[idx].raw) if task_outputs else ""
    except (IndexError, AttributeError):
        return ""


def run_crew(athlete_id: int = 1, athlete_data: dict = None) -> dict:
    """
    Build agents, tasks, assemble the crew, and run the analysis pipeline.

    Parameters
    ----------
    athlete_id   : used only when athlete_data is None (loads synthetic data)
    athlete_data : dict with keys: profile, fitness / fitness_assessment,
                   training_sessions, recovery_data, injury_history

    Returns
    -------
    dict with keys:
        performance_report, injury_risk_report, recovery_report,
        nutrition_report, training_plan, athlete_data
    """
    # ── Load data ────────────────────────────────────────────────────────
    if athlete_data is None:
        from data_generator import get_full_athlete_data
        raw = get_full_athlete_data(athlete_id)
        # Normalise data_generator output to dashboard key names
        data = {
            "profile":          raw["profile"],
            "fitness":          raw["fitness_assessment"],
            "fitness_assessment": raw["fitness_assessment"],
            "training_sessions": raw["training_sessions"],
            "recovery_data":    raw["recovery_data"],
            "injury_history":   raw["injury_history"],
        }
    else:
        # Normalise user-supplied data
        fitness = athlete_data.get("fitness") or athlete_data.get("fitness_assessment", {})
        data = {
            "profile":           athlete_data.get("profile", {}),
            "fitness":           fitness,
            "fitness_assessment": fitness,
            "training_sessions": athlete_data.get("training_sessions", []),
            "recovery_data":     athlete_data.get("recovery_data", []),
            "injury_history":    athlete_data.get("injury_history", []),
        }

    profile = data["profile"]
    print(f"\n🏃 Athlete: {profile.get('name', 'Unknown')} | "
          f"Sport: {profile.get('sport', '?')} | "
          f"Age: {profile.get('age', '?')}\n")

    # ── Build agents ─────────────────────────────────────────────────────
    perf_agent     = build_performance_agent()
    injury_agent   = build_injury_risk_agent()
    recovery_agent = build_recovery_agent()
    nutrition_agent = build_nutrition_agent()
    recommend_agent = build_training_recommendation_agent()

    # ── Build tasks ──────────────────────────────────────────────────────
    perf_task      = build_performance_task(perf_agent, data)
    injury_task    = build_injury_risk_task(injury_agent, data)
    recovery_task  = build_recovery_task(recovery_agent, data)
    nutrition_task = build_nutrition_task(nutrition_agent, data)
    recommend_task = build_training_recommendation_task(
        recommend_agent,
        data,
        context_tasks=[perf_task, injury_task, recovery_task, nutrition_task],
    )

    # ── Assemble and run crew ─────────────────────────────────────────────
    crew = Crew(
        agents=[perf_agent, injury_agent, recovery_agent, nutrition_agent, recommend_agent],
        tasks=[perf_task, injury_task, recovery_task, nutrition_task, recommend_task],
        process=Process.sequential,
        verbose=True,
    )

    print("🤖 5-Agent crew assembled. Starting analysis...\n")
    result = crew.kickoff()

    task_outputs = getattr(result, "tasks_output", [])

    return {
        "performance_report": _get_task_output(task_outputs, 0) or str(result),
        "injury_risk_report": _get_task_output(task_outputs, 1) or str(result),
        "recovery_report":    _get_task_output(task_outputs, 2) or str(result),
        "nutrition_report":   _get_task_output(task_outputs, 3) or str(result),
        "training_plan":      _get_task_output(task_outputs, 4) or str(result),
        "athlete_data":       data,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the 5-Agent Athlete Performance Crew")
    parser.add_argument("--athlete_id", type=int, default=1)
    args = parser.parse_args()

    outputs = run_crew(athlete_id=args.athlete_id)
    sep = "=" * 70
    for key, label in [
        ("performance_report", "PERFORMANCE ANALYSIS"),
        ("injury_risk_report", "INJURY RISK ASSESSMENT"),
        ("recovery_report",    "RECOVERY & WELLNESS"),
        ("nutrition_report",   "NUTRITION & HYDRATION"),
        ("training_plan",      "7-DAY TRAINING PLAN"),
    ]:
        print(f"\n{sep}\n{label}\n{sep}")
        print(outputs[key])
