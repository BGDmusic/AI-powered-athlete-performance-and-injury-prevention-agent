# 🏃 AI-Powered Athlete Performance & Injury Prevention System

A multi-agent AI system built with **CrewAI** and **Streamlit** that analyses athlete training data, monitors injury risk, tracks recovery and wellness, and generates personalised weekly training plans.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                       │
│  (Performance · Injury Risk · Recovery · Plan · AI Reports)│
└──────────────────────────┬─────────────────────────────────┘
                           │
                    crew.py (orchestrator)
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
  │  Performance  │ │ Injury Risk  │ │ Recovery &      │
  │  Analysis     │ │ Monitor      │ │ Wellness Agent  │
  │  Agent        │ │ Agent        │ │                 │
  └───────┬───────┘ └──────┬───────┘ └────────┬────────┘
          └────────────────┼─────────────────-┘
                           ▼
                ┌──────────────────────┐
                │ Training             │
                │ Recommendation Agent │
                └──────────────────────┘
```

## Project Structure

```
Athlete performance/
├── dashboard.py         # Streamlit dashboard (main UI)
├── crew.py              # CrewAI crew orchestrator
├── agents.py            # Agent definitions (4 specialists)
├── tasks.py             # Task definitions with data injection
├── data_generator.py    # Synthetic athlete data generator
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

## Agents

| Agent | Role | Key Inputs |
|---|---|---|
| **Performance Analysis Agent** | Identifies trends, peak periods, weaknesses | Training sessions (90 days) |
| **Injury Risk Monitoring Agent** | Scores injury risk (0–100), flags alerts | Training load, injury history, fitness |
| **Recovery & Wellness Agent** | Wellness score, recovery recommendations | Sleep, HRV, soreness, stress |
| **Training Recommendation Agent** | Personalised 7-day training plan | All 3 agent outputs |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

Or enter the key directly in the dashboard sidebar.

### 3. Run the dashboard

```bash
streamlit run dashboard.py
```

The dashboard opens at `http://localhost:8501`.

### 4. Run the AI crew from the command line (optional)

```bash
python crew.py --athlete_id 1
```

## Dashboard Tabs

| Tab | Description |
|---|---|
| 📊 **Performance** | Performance score trend, intensity, distance, heart rate, speed, fitness radar |
| 🩺 **Injury Risk** | Risk gauge (0–100), risk classification, training load trend, injury history |
| 💤 **Recovery & Wellness** | Wellness gauge, sleep, HRV, stress/soreness trends, recovery method frequency |
| 📋 **Training Plan** | Heuristic-based template weekly plan (no API key needed) |
| 🤖 **AI Reports** | Full CrewAI-generated reports from all 4 agents (requires API key) |

## Data

The `data_generator.py` module generates **synthetic but realistic** athlete data for 10 athletes (IDs 1–10). Each athlete has:
- 90 days of training session records
- 30 days of recovery/wellness records  
- 0–3 historical injury events
- A fitness assessment snapshot
- A static profile (sport, age, weight, height)

## Notes

- **No real athlete data is used.** All data is procedurally generated from a seeded random number generator.
- **AI analysis requires an OpenAI API key.** The dashboard visualisations and template plan work without one.
- The recommended model is `gpt-4o-mini` for speed and cost efficiency; set `OPENAI_MODEL_NAME` in `.env` to change it.
