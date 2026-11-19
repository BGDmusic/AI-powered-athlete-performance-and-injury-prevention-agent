"""
tasks.py — CrewAI task definitions for the 5-agent Athlete Performance System.

Each task receives athlete data (user-entered OR auto-generated) injected into
the task description at build time. The final training recommendation task
receives the first four tasks as context.
"""

from crewai import Task, Agent


# ── Formatting helpers ───────────────────────────────────────────────────────

def _fmt_training(sessions: list) -> str:
    if not sessions:
        return "No training sessions recorded."
    last = sessions[-14:] if len(sessions) >= 14 else sessions

    def avg(key):
        vals = [r[key] for r in last if r.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0

    # Consecutive high-intensity days
    sorted_s = sorted(sessions, key=lambda r: r.get("date", ""))
    consec = max_consec = 0
    for s in sorted_s[-14:]:
        if s.get("intensity", 0) >= 7:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    # Acute:Chronic ratio
    acute  = sum(r.get("intensity", 0) * r.get("duration_min", 0) for r in sessions[-7:])
    chronic = sum(r.get("intensity", 0) * r.get("duration_min", 0) for r in sessions[-14:])
    ac_ratio = round((acute / 7) / max(chronic / 14, 1), 2)

    rows = "\n".join(
        f"  {r.get('date','?')} | Int:{r.get('intensity','?')} | "
        f"Dur:{r.get('duration_min','?')}min | "
        f"Dist:{r.get('running_distance_km','?')}km | "
        f"HR:{r.get('avg_heart_rate','?')}bpm | "
        f"Spd:{r.get('max_speed_kmh','?')}km/h | "
        f"Perf:{r.get('performance_score','?')}/100"
        for r in last
    )
    return (
        f"Total sessions: {len(sessions)} | "
        f"Avg intensity: {avg('intensity')}/10 | "
        f"Avg HR: {avg('avg_heart_rate')}bpm | "
        f"Avg perf score: {avg('performance_score')}/100 | "
        f"Acute:Chronic ratio: {ac_ratio} | "
        f"Max consecutive hard sessions: {max_consec}\n"
        f"Recent sessions (last {len(last)}):\n{rows}"
    )


def _fmt_injuries(injuries: list) -> str:
    if not injuries:
        return "No injury history on record."
    rows = []
    for inj in injuries:
        t = inj.get("Injury Type") or inj.get("injury_type", "Unknown")
        d = inj.get("Date") or inj.get("date", "?")
        s = inj.get("Severity") or inj.get("severity", "?")
        r = inj.get("Recovery Days") or inj.get("recovery_days", "?")
        rows.append(f"  {t} | Date:{d} | Severity:{s} | Recovery:{r} days")
    return f"{len(injuries)} recorded injuries:\n" + "\n".join(rows)


def _fmt_fitness(f: dict) -> str:
    return (
        f"VO2 max:{f.get('vo2_max','?')} ml/kg/min | "
        f"Resting HR:{f.get('resting_heart_rate','?')} bpm | "
        f"Flexibility:{f.get('flexibility_score','?')}/10 | "
        f"Strength index:{f.get('strength_index','?')}/10 | "
        f"Body fat:{f.get('body_fat_pct','?')}%"
    )


def _fmt_recovery(records: list) -> str:
    if not records:
        return "No recovery data recorded."
    last = records[-7:] if len(records) >= 7 else records

    def avg(key):
        vals = [r[key] for r in last if r.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0

    rows = "\n".join(
        f"  {r.get('date','?')} | Sleep:{r.get('sleep_hours','?')}h "
        f"(Q:{r.get('sleep_quality','?')}/10) | HRV:{r.get('hrv','?')}ms | "
        f"Soreness:{r.get('muscle_soreness','?')}/10 | "
        f"Stress:{r.get('stress_level','?')}/10 | "
        f"Hydration:{r.get('hydration_level','?')}/10"
        for r in last
    )
    return (
        f"Last 7 days avg — Sleep:{avg('sleep_hours')}h | "
        f"HRV:{avg('hrv')}ms | Soreness:{avg('muscle_soreness')}/10 | "
        f"Stress:{avg('stress_level')}/10 | Hydration:{avg('hydration_level')}/10\n"
        f"Daily records:\n{rows}"
    )


# ── Task builders ────────────────────────────────────────────────────────────

def build_performance_task(agent: Agent, athlete_data: dict) -> Task:
    p = athlete_data["profile"]
    desc = f"""
Athlete: {p.get('name','Unknown')} | Age:{p.get('age','?')} | Sport:{p.get('sport','?')} | 
Experience:{p.get('experience_years','?')} yrs | Weight:{p.get('weight_kg','?')}kg | Height:{p.get('height_cm','?')}cm

Fitness: {_fmt_fitness(athlete_data.get('fitness_assessment', athlete_data.get('fitness', {})))}

Training Data:
{_fmt_training(athlete_data.get('training_sessions', []))}

Injury History:
{_fmt_injuries(athlete_data.get('injury_history', []))}

TASKS:
1. Identify the performance trend over the last 4 weeks (improving/declining/plateau).
2. Pinpoint peak performance periods and what drove them.
3. Identify the top 3 specific weaknesses in training metrics with data evidence.
4. Rate overall performance 1–10 with a brief justification.
5. Provide 3 actionable coaching insights the athlete can apply this week.
"""
    return Task(
        description=desc,
        expected_output=(
            "Structured performance report: trend analysis, peak period highlights, "
            "top 3 weaknesses with data, overall rating (1–10) with justification, "
            "3 coaching insights."
        ),
        agent=agent,
    )


def build_injury_risk_task(agent: Agent, athlete_data: dict) -> Task:
    p = athlete_data["profile"]
    desc = f"""
Athlete: {p.get('name','Unknown')} | Age:{p.get('age','?')} | Sport:{p.get('sport','?')}

Fitness Assessment:
{_fmt_fitness(athlete_data.get('fitness_assessment', athlete_data.get('fitness', {})))}

Training Load:
{_fmt_training(athlete_data.get('training_sessions', []))}

Previous Injury History:
{_fmt_injuries(athlete_data.get('injury_history', []))}

Recovery Data (recent):
{_fmt_recovery(athlete_data.get('recovery_data', []))}

TASKS:
1. Calculate a composite injury risk score (0–100). Higher = higher risk.
2. Classify overall risk: Low (<30) / Medium (30–60) / High (60–80) / Critical (>80).
3. List the top 3 specific injury risk factors with data evidence.
4. Identify any RECURRING injury patterns from history that elevate re-injury risk.
5. Provide 3 immediate preventative interventions the athlete must start today.
6. Flag any single metric that is URGENT and requires immediate action.
"""
    return Task(
        description=desc,
        expected_output=(
            "Injury risk report: numeric score (0–100), classification (Low/Medium/High/Critical), "
            "top 3 risk factors with evidence, recurrence patterns, "
            "3 preventative interventions, urgent flags."
        ),
        agent=agent,
    )


def build_recovery_task(agent: Agent, athlete_data: dict) -> Task:
    p = athlete_data["profile"]
    desc = f"""
Athlete: {p.get('name','Unknown')} | Age:{p.get('age','?')} | Sport:{p.get('sport','?')}

Recovery & Wellness Data:
{_fmt_recovery(athlete_data.get('recovery_data', []))}

Recent Training Load (for context):
{_fmt_training(athlete_data.get('training_sessions', []))}

TASKS:
1. Assign an overall wellness score (1–10) with justification.
2. Identify the single most critical recovery deficit (sleep/HRV/hydration/stress/soreness).
3. Assess HRV trend (improving/stable/declining) and what it means for readiness.
4. Provide 3 specific, actionable recovery recommendations for the next 7 days.
5. State clearly: Is the athlete READY or NOT READY for high-intensity training this week? Why?
"""
    return Task(
        description=desc,
        expected_output=(
            "Wellness report: overall score (1–10) with justification, critical deficit identified, "
            "HRV trend assessment, 3 recovery recommendations, training-readiness verdict."
        ),
        agent=agent,
    )


def build_nutrition_task(agent: Agent, athlete_data: dict) -> Task:
    p  = athlete_data["profile"]
    fi = athlete_data.get("fitness_assessment", athlete_data.get("fitness", {}))
    desc = f"""
Athlete: {p.get('name','Unknown')} | Age:{p.get('age','?')} | Sport:{p.get('sport','?')} | 
Weight:{p.get('weight_kg','?')}kg | Height:{p.get('height_cm','?')}cm

Body Composition & Fitness:
{_fmt_fitness(fi)}

Recent Training Load (to estimate caloric needs):
{_fmt_training(athlete_data.get('training_sessions', []))}

Recovery/Hydration patterns:
{_fmt_recovery(athlete_data.get('recovery_data', []))}

TASKS:
1. Estimate daily caloric requirement based on training load and body weight.
2. Provide macro-nutrient targets: carbohydrates (g), protein (g), fats (g) per day.
3. Design a simple hydration protocol: litres/day at rest and during training.
4. Recommend 2 evidence-based supplements with dosage and timing.
5. Provide a brief pre-training meal and post-training meal outline.
"""
    return Task(
        description=desc,
        expected_output=(
            "Nutrition report: estimated daily calories, macro targets (carbs/protein/fat in grams), "
            "hydration protocol, 2 supplement recommendations with dosage, "
            "pre-training and post-training meal outlines."
        ),
        agent=agent,
    )


def build_training_recommendation_task(
    agent: Agent,
    athlete_data: dict,
    context_tasks: list,
) -> Task:
    p = athlete_data["profile"]
    desc = f"""
Athlete: {p.get('name','Unknown')} | Age:{p.get('age','?')} | Sport:{p.get('sport','?')} | 
Experience:{p.get('experience_years','?')} yrs | Weight:{p.get('weight_kg','?')}kg

You have been provided with specialist reports from:
- Performance Analyst (training trends, weaknesses, coaching insights)
- Injury Risk Specialist (risk score, top risk factors, preventative actions)
- Recovery & Wellness Specialist (wellness score, recovery deficit, readiness verdict)
- Sports Nutritionist (caloric needs, macros, hydration, supplements, meal plan)

Using ALL FOUR specialist reports, design a complete 7-day training programme.

REQUIREMENTS:
1. Day-by-day: session type, specific exercises/drills, duration, intensity (1–10), volume.
2. Integrate at least 1 dedicated recovery/rest day.
3. Address the top 3 performance weaknesses identified.
4. Respect the injury risk classification — no exercises that aggravate flagged risk areas.
5. Align training load with the wellness/readiness score.
6. Integrate nutrition timing from the dietitian's report (pre/post session fuelling).
7. Set 3 measurable performance targets for the week.
8. Include a 2-sentence rationale explaining how the plan balances all four reports.
"""
    return Task(
        description=desc,
        expected_output=(
            "7-day training programme: day-by-day sessions with type, exercises, duration, "
            "intensity, volume; 3 measurable weekly targets; nutrition integration notes; "
            "rationale connecting performance, injury, recovery, and nutrition findings."
        ),
        agent=agent,
        context=context_tasks,
    )
