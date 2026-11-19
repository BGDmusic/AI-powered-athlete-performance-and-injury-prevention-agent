"""
dashboard.py — AI-Powered Athlete Performance & Injury Prevention System
Version 4.0 — 5 specialist agents, manual data entry, predictions, notifications, dark theme.

Run with:
    py -m streamlit run dashboard.py --server.headless true --browser.gatherUsageStats false
"""

import os
from datetime import date, datetime
from collections import Counter
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Athlete AI Performance System",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
section[data-testid="stSidebar"] { background:#1a1d27; }
div[data-testid="stForm"] { background:#1a1d27; border:1px solid #2d3748;
                             border-radius:8px; padding:16px 20px 8px; }
.agent-badge { display:inline-block; padding:2px 8px; border-radius:12px;
               font-size:11px; font-weight:600; margin-right:4px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────
SPORTS = ["Running","Cycling","Swimming","Weightlifting","Football",
          "Basketball","Tennis","Cricket","Athletics","Other"]
INJURY_TYPES = ["Hamstring Strain","Knee Sprain","Shin Splints","Lower Back Pain",
                "Ankle Sprain","Shoulder Injury","Stress Fracture","Muscle Pull",
                "Ligament Tear","Other"]
SEVERITY_OPTS = ["Mild","Moderate","Severe"]
RECOVERY_METHODS = ["Ice Bath","Massage","Stretching","Rest",
                    "Physiotherapy","Yoga","Foam Rolling","Hydrotherapy"]

AGENTS = [
    {"id":"perf",     "name":"Performance Analyst",       "icon":"📊", "color":"#3b82d4"},
    {"id":"injury",   "name":"Injury Risk Specialist",    "icon":"🩺", "color":"#ef4444"},
    {"id":"recovery", "name":"Recovery & Wellness Coach", "icon":"💤", "color":"#8b5cf6"},
    {"id":"nutrition","name":"Sports Nutritionist",       "icon":"🥗", "color":"#10b981"},
    {"id":"plan",     "name":"Periodisation Coach",       "icon":"📋", "color":"#f59e0b"},
]

# ── Pure-Python helpers ──────────────────────────────────────────────────────
def _avg(lst, key):
    vals = [r[key] for r in lst if r.get(key) is not None]
    return round(sum(vals)/len(vals), 2) if vals else 0

def _tail(lst, n):
    return lst[-n:] if len(lst) >= n else lst

def _col(lst, key):
    return [r[key] for r in lst]

def _html_table(rows):
    if not rows:
        return "<p style='color:#9ca3af'><em>No records yet.</em></p>"
    headers = list(rows[0].keys())
    th = "".join(
        f'<th style="background:#1e2130;border:1px solid #2d3748;'
        f'padding:7px 12px;text-align:left;font-size:12px;white-space:nowrap;color:#e5e7eb">{h}</th>'
        for h in headers)
    body = ""
    for i, row in enumerate(rows):
        bg = "#161922" if i%2==0 else "#1a1d27"
        tds = "".join(
            f'<td style="border:1px solid #2d3748;padding:5px 12px;font-size:12px;color:#e5e7eb">'
            f'{row.get(h,"")}</td>' for h in headers)
        body += f'<tr style="background:{bg}">{tds}</tr>'
    return (
        '<div style="overflow-x:auto;margin-top:6px">'
        '<table style="border-collapse:collapse;width:100%">'
        f"<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>")

def _alert_card(sev, category, title, message, action):
    colors = {
        "CRITICAL": ("#2d1515","#dc2626","🔴"),
        "WARNING":  ("#2d1f0a","#f97316","🟠"),
        "CAUTION":  ("#262208","#eab308","🟡"),
        "INFO":     ("#0f1f35","#3b82f6","🔵"),
        "SUCCESS":  ("#0d2318","#16a34a","🟢"),
    }
    bg, border, icon = colors.get(sev, ("#1a1d27","#9ca3af","⚪"))
    return st.markdown(
        f'<div style="background:{bg};border-left:5px solid {border};'
        f'border-radius:6px;padding:12px 16px;margin-bottom:10px">'
        f'<div style="font-weight:700;color:{border};margin-bottom:4px">'
        f'{icon} [{sev}] {category} — {title}</div>'
        f'<div style="color:#d1d5db;font-size:0.9rem;margin-bottom:6px">{message}</div>'
        f'<div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:6px 10px;'
        f'font-size:0.85rem;color:#e5e7eb"><strong>✅ Action:</strong> {action}</div>'
        f'</div>', unsafe_allow_html=True)

# ── Session-state defaults ───────────────────────────────────────────────────
def _init():
    defaults = {
        "data_source":           "manual",
        "athlete_id":            "",          # ID of currently loaded athlete (empty = unsaved)
        "sensor_notif_log":      [],          # persistent log of all sensor threshold breaches this session
        "profile":  {"name":"","sport":SPORTS[0],"age":25,"experience_years":1,
                     "weight_kg":70.0,"height_cm":175},
        "fitness":  {"vo2_max":50.0,"resting_heart_rate":60,"flexibility_score":6.0,
                     "strength_index":6.0,"body_fat_pct":15.0,"assessment_date":str(date.today())},
        "training_sessions": [],
        "recovery_data":     [],
        "injury_history":    [],
        "ai_results":        {},
        "notifications":     [],
        "pred_result":       None,
        # Sensor state
        "sensor_active":     False,
        "sensor_intensity":  6,
        "sensor_history":    [],
        "sensor_alerts":     [],
        "sensor_reading":    None,
        "sensor_real_data":  {},
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

def _load_athlete_into_state(athlete_id: str):
    """Load a saved athlete's data from disk into session state."""
    from athlete_store import load_athlete
    data = load_athlete(athlete_id)
    if not data:
        return False
    st.session_state["athlete_id"]         = data["id"]
    st.session_state["profile"]            = data["profile"]
    st.session_state["fitness"]            = data["fitness"]
    st.session_state["training_sessions"]  = data["training_sessions"]
    st.session_state["recovery_data"]      = data["recovery_data"]
    st.session_state["injury_history"]     = data["injury_history"]
    st.session_state["ai_results"]         = data.get("ai_results", {})
    # Reset transient state
    st.session_state["pred_result"]        = None
    st.session_state["notifications"]      = []
    return True

def _new_athlete():
    """Clear session state to start a fresh athlete."""
    st.session_state["athlete_id"]         = ""
    st.session_state["profile"]            = {"name":"","sport":SPORTS[0],"age":25,
                                              "experience_years":1,"weight_kg":70.0,"height_cm":175}
    st.session_state["fitness"]            = {"vo2_max":50.0,"resting_heart_rate":60,
                                              "flexibility_score":6.0,"strength_index":6.0,
                                              "body_fat_pct":15.0,"assessment_date":str(date.today())}
    st.session_state["training_sessions"]  = []
    st.session_state["recovery_data"]      = []
    st.session_state["injury_history"]     = []
    st.session_state["ai_results"]         = {}
    st.session_state["pred_result"]        = None
    st.session_state["notifications"]      = []

def get_active_data():
    """Return (profile, fitness, training, recovery, injuries) from session state."""
    return (st.session_state["profile"],
            st.session_state["fitness"],
            st.session_state["training_sessions"],
            st.session_state["recovery_data"],
            st.session_state["injury_history"])

profile, fitness, training, recovery, injuries = get_active_data()
last14_tr = _tail(training, 14)
last7_rec = _tail(recovery, 7)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Controls")
    st.divider()

    # ── Athlete Roster ────────────────────────────────────────────────
    from athlete_store import list_athletes, save_athlete, delete_athlete
    st.markdown("**👥 Athlete Roster**")

    roster = list_athletes()
    current_id = st.session_state.get("athlete_id", "")

    if roster:
        roster_labels = {a["id"]: f"{a['name']} ({a['sport']})" for a in roster}
        roster_ids    = [a["id"] for a in roster]
        # Find index of current athlete; default to 0
        sel_idx = roster_ids.index(current_id) if current_id in roster_ids else 0
        chosen_id = st.selectbox(
            "Select athlete",
            options=roster_ids,
            index=sel_idx,
            format_func=lambda aid: roster_labels.get(aid, aid),
            key="roster_select",
        )
        # Load athlete when selection changes
        if chosen_id != current_id:
            _load_athlete_into_state(chosen_id)
            st.rerun()
    else:
        st.caption("No saved athletes yet.")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("➕ New", use_container_width=True):
            _new_athlete()
            st.rerun()
    with btn_col2:
        # Save current athlete
        _cur_name = st.session_state["profile"].get("name","").strip()
        if st.button("💾 Save", use_container_width=True, disabled=not _cur_name):
            _saved_id = save_athlete(
                athlete_id       = st.session_state["athlete_id"],
                profile          = st.session_state["profile"],
                fitness          = st.session_state["fitness"],
                training_sessions= st.session_state["training_sessions"],
                recovery_data    = st.session_state["recovery_data"],
                injury_history   = st.session_state["injury_history"],
                ai_results       = st.session_state.get("ai_results", {}),
            )
            st.session_state["athlete_id"] = _saved_id
            st.success(f"✅ Saved {_cur_name}")
            st.rerun()

    # Delete button (only shown when an athlete is loaded)
    if current_id:
        _del_name = st.session_state["profile"].get("name", current_id)
        if st.button(f"🗑️ Delete {_del_name}", use_container_width=True):
            delete_athlete(current_id)
            _new_athlete()
            st.rerun()

    if not _cur_name:
        st.caption("⚠️ Save is disabled until you set a name in 👤 Profile.")

    # Show last-saved time if available
    if current_id and roster:
        _meta = next((a for a in roster if a["id"] == current_id), None)
        if _meta:
            st.caption(f"Last saved: {_meta['saved_at']}")

    st.divider()

    # ── Sensor Controls ──
    st.markdown("**📡 Wearable Sensor**")
    sens_col1, sens_col2 = st.columns(2)
    with sens_col1:
        if st.button("▶ Start" if not st.session_state["sensor_active"] else "⏹ Stop",
                     use_container_width=True):
            if not st.session_state["sensor_active"]:
                from sensor_engine import reset_simulation
                reset_simulation()
                st.session_state["sensor_history"] = []
                st.session_state["sensor_alerts"]  = []
            st.session_state["sensor_active"] = not st.session_state["sensor_active"]
            st.rerun()
    with sens_col2:
        sensor_status_color = "#16a34a" if st.session_state["sensor_active"] else "#6b7280"
        sensor_status_text  = "🟢 LIVE" if st.session_state["sensor_active"] else "⚪ OFF"
        st.markdown(
            f'<div style="text-align:center;padding:6px 0;font-weight:700;'
            f'color:{sensor_status_color};font-size:0.9rem">{sensor_status_text}</div>',
            unsafe_allow_html=True)

    st.session_state["sensor_intensity"] = st.slider(
        "Training Intensity", 1, 10,
        value=st.session_state["sensor_intensity"], key="sb_intensity")

    # Tick sensor if active
    if st.session_state["sensor_active"]:
        from sensor_engine import get_live_reading, evaluate_thresholds
        reading = get_live_reading(
            intensity=st.session_state["sensor_intensity"],
            real_data=st.session_state.get("sensor_real_data") or None,
        )
        st.session_state["sensor_reading"] = reading
        # Keep rolling 60-point history
        hist = st.session_state["sensor_history"]
        hist.append(reading)
        if len(hist) > 60:
            hist.pop(0)
        st.session_state["sensor_history"] = hist
        # Evaluate thresholds
        sa = evaluate_thresholds(reading)
        st.session_state["sensor_alerts"] = sa

        # ── Persist new alerts into the notification log ──────────────
        if sa:
            _athlete_name = st.session_state["profile"].get("name","") or "Athlete"
            _notif_log = st.session_state.get("sensor_notif_log", [])
            for _a in sa:
                # Avoid duplicate entries within the same second
                _dup = any(
                    n["metric"] == _a["metric"] and n["timestamp"] == _a["timestamp"]
                    for n in _notif_log
                )
                if not _dup:
                    _notif_log.append({**_a, "athlete": _athlete_name})
            # Keep last 200 sensor notifications
            if len(_notif_log) > 200:
                _notif_log = _notif_log[-200:]
            st.session_state["sensor_notif_log"] = _notif_log

            # Prominent sidebar alert banner for CRITICAL / WARNING
            _top = max(sa, key=lambda x: {"CRITICAL":3,"WARNING":2,"CAUTION":1}.get(x["severity"],0))
            _sev_bg  = {"CRITICAL":"#2d1515","WARNING":"#2d1f0a","CAUTION":"#262208"}.get(_top["severity"],"#1a1d27")
            _sev_bdr = {"CRITICAL":"#dc2626","WARNING":"#f97316","CAUTION":"#eab308"}.get(_top["severity"],"#9ca3af")
            _sev_ico = {"CRITICAL":"🔴","WARNING":"🟠","CAUTION":"🟡"}.get(_top["severity"],"⚪")
            st.markdown(
                f'<div style="background:{_sev_bg};border-left:4px solid {_sev_bdr};'
                f'border-radius:6px;padding:8px 10px;margin-top:4px">'
                f'<div style="font-weight:700;color:{_sev_bdr};font-size:0.8rem">'
                f'{_sev_ico} {_top["severity"]}: {_top["label"]}</div>'
                f'<div style="color:#d1d5db;font-size:0.75rem">{_top["message"]}</div>'
                f'</div>',
                unsafe_allow_html=True)

    st.divider()
    # Notification badge
    from notification_engine import get_all_notifications, count_unread
    notifs = get_all_notifications(training, recovery, injuries,
                                   pred_result=st.session_state.get("pred_result"),
                                   agent_outputs=st.session_state.get("ai_results"),
                                   sensor_alerts=st.session_state.get("sensor_alerts"))
    st.session_state["notifications"] = notifs
    uc = count_unread(notifs)
    if uc["total"]:
        st.markdown(f"**🔔 {uc['total']} unread alerts** &nbsp;"
                    f"🔴{uc.get('CRITICAL',0)} 🟠{uc.get('WARNING',0)} "
                    f"🟡{uc.get('CAUTION',0)}")
    else:
        st.markdown("**🔔 No new alerts**")

    st.divider()
    # Auto-save on AI run
    run_ai = st.button("🤖 Run 5-Agent AI Analysis", type="primary", use_container_width=True)
    if run_ai and st.session_state["profile"].get("name","").strip():
        save_athlete(
            athlete_id        = st.session_state["athlete_id"],
            profile           = st.session_state["profile"],
            fitness           = st.session_state["fitness"],
            training_sessions = st.session_state["training_sessions"],
            recovery_data     = st.session_state["recovery_data"],
            injury_history    = st.session_state["injury_history"],
        )
    st.divider()
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...",
                                  help="Required for AI analysis tab.")
    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input
    st.divider()
    # Agent legend
    st.markdown("**🤖 Active Agents**")
    for ag in AGENTS:
        st.markdown(
            f'<span class="agent-badge" style="background:{ag["color"]}22;'
            f'color:{ag["color"]};border:1px solid {ag["color"]}44">'
            f'{ag["icon"]} {ag["name"]}</span>', unsafe_allow_html=True)
    st.divider()
    st.caption("v4.0 · AI Athlete Performance System")

# ── Refresh active data after sidebar changes ────────────────────────────────
profile, fitness, training, recovery, injuries = get_active_data()
last14_tr = _tail(training, 14)
last7_rec = _tail(recovery, 7)

# ── Run predictions on every load ────────────────────────────────────────────
from predictions import run_predictions
pred_result = run_predictions(profile, fitness, training, recovery, injuries)
st.session_state["pred_result"] = pred_result

# ── Header ───────────────────────────────────────────────────────────────────
aname = profile.get("name","") or "My Athlete"
st.title(f"🏃 {aname} · AI Performance Dashboard")
st.caption(
    f"Sport: **{profile.get('sport','—')}** | "
    f"Age: **{profile.get('age','—')}** | "
    f"Experience: **{profile.get('experience_years','—')} yrs** | "
    f"Weight: **{profile.get('weight_kg','—')} kg** | "
    f"Height: **{profile.get('height_cm','—')} cm**"
)
st.divider()

# ── KPI strip ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Training Sessions",   len(training))
k2.metric("Latest Perf Score",   f"{training[-1]['performance_score']}/100" if training else "—")
k3.metric("Avg HR (14d)",         f"{round(_avg(last14_tr,'avg_heart_rate'))} bpm" if last14_tr else "—")
k4.metric("Avg Sleep (7d)",       f"{round(_avg(last7_rec,'sleep_hours'),1)} hrs" if last7_rec else "—")
k5.metric("Injuries Logged",      len(injuries))
k6.metric("Overall Risk",
          f"{pred_result['overall_risk']}/100 ({pred_result['risk_level']})"
          if training or recovery else "—")
st.divider()

# ── Tabs ─────────────────────────────────────────────────────────────────────
(tab_prof, tab_train, tab_rec_log, tab_perf,
 tab_inj, tab_well, tab_pred, tab_plan, tab_notif, tab_ai, tab_sensor, tab_roster) = st.tabs([
    "👤 Profile",
    "🏋️ Log Training",
    "💤 Log Recovery",
    "📊 Performance",
    "🩺 Injury Risk",
    "🌿 Wellness",
    "🔮 Predictions",
    "📋 Training Plan",
    "🔔 Notifications",
    "🤖 AI Reports",
    "📡 Live Sensor",
    "👥 All Athletes",
])


# ════════════════════════════════════════════════════════════════════════
# TAB — PROFILE
# ════════════════════════════════════════════════════════════════════════
with tab_prof:
    st.subheader("👤 Athlete Profile")
    p = st.session_state["profile"]
    fi = st.session_state["fitness"]
    with st.form("form_profile"):
        st.markdown("#### 🧍 Personal Details")
        c1,c2,c3 = st.columns(3)
        with c1:
            inp_name  = st.text_input("Full Name", value=p.get("name",""))
            inp_sport = st.selectbox("Sport", SPORTS,
                                     index=SPORTS.index(p["sport"]) if p["sport"] in SPORTS else 0)
        with c2:
            inp_age = st.number_input("Age", 10, 60, value=int(p["age"]))
            inp_exp = st.number_input("Experience (yrs)", 0, 40, value=int(p["experience_years"]))
        with c3:
            inp_wt  = st.number_input("Weight (kg)", 30.0, 200.0, value=float(p["weight_kg"]), step=0.5)
            inp_ht  = st.number_input("Height (cm)", 100, 250, value=int(p["height_cm"]))

        st.markdown("#### 🏋️ Fitness Assessment")
        f1,f2,f3 = st.columns(3)
        with f1:
            inp_vo2 = st.number_input("VO₂ Max (ml/kg/min)", 20.0, 90.0, value=float(fi["vo2_max"]), step=0.5)
            inp_rhr = st.number_input("Resting HR (bpm)", 30, 100, value=int(fi["resting_heart_rate"]))
        with f2:
            inp_flex = st.slider("Flexibility (1–10)", 1.0, 10.0, value=float(fi["flexibility_score"]), step=0.5)
            inp_str  = st.slider("Strength Index (1–10)", 1.0, 10.0, value=float(fi["strength_index"]), step=0.5)
        with f3:
            inp_bf   = st.number_input("Body Fat (%)", 3.0, 50.0, value=float(fi["body_fat_pct"]), step=0.5)
            inp_ad   = st.date_input("Assessment Date", value=date.fromisoformat(fi["assessment_date"]))
        save_p = st.form_submit_button("💾 Save Profile & Fitness", type="primary", use_container_width=True)

    if save_p:
        st.session_state["profile"].update({"name":inp_name,"sport":inp_sport,"age":inp_age,
                                             "experience_years":inp_exp,"weight_kg":inp_wt,"height_cm":inp_ht})
        st.session_state["fitness"].update({"vo2_max":inp_vo2,"resting_heart_rate":inp_rhr,
                                             "flexibility_score":inp_flex,"strength_index":inp_str,
                                             "body_fat_pct":inp_bf,"assessment_date":str(inp_ad)})
        if inp_name.strip():
            from athlete_store import save_athlete as _sa
            _sid = _sa(st.session_state["athlete_id"], st.session_state["profile"],
                       st.session_state["fitness"], st.session_state["training_sessions"],
                       st.session_state["recovery_data"], st.session_state["injury_history"],
                       st.session_state.get("ai_results",{}))
            st.session_state["athlete_id"] = _sid
        st.success(f"✅ Profile saved for **{inp_name}**!")
        st.rerun()

    st.divider()
    st.markdown("#### 🩹 Injury History")
    inj_list = st.session_state["injury_history"]
    if inj_list: st.markdown(_html_table(inj_list), unsafe_allow_html=True)
    else:        st.info("No injuries recorded yet.")

    with st.form("form_injury"):
        ic1,ic2,ic3,ic4 = st.columns(4)
        with ic1: inj_type = st.selectbox("Injury Type", INJURY_TYPES)
        with ic2: inj_date = st.date_input("Date", value=date.today())
        with ic3: inj_sev  = st.selectbox("Severity", SEVERITY_OPTS)
        with ic4: inj_days = st.number_input("Recovery Days", 1, 365, value=14)
        add_inj = st.form_submit_button("➕ Add Injury", use_container_width=True)
    if add_inj:
        st.session_state["injury_history"].append(
            {"Injury Type":inj_type,"Date":str(inj_date),"Severity":inj_sev,"Recovery Days":inj_days})
        if st.session_state["profile"].get("name","").strip():
            from athlete_store import save_athlete as _sa
            _sid = _sa(st.session_state["athlete_id"], st.session_state["profile"],
                       st.session_state["fitness"], st.session_state["training_sessions"],
                       st.session_state["recovery_data"], st.session_state["injury_history"],
                       st.session_state.get("ai_results",{}))
            st.session_state["athlete_id"] = _sid
        st.success(f"✅ Injury added: {inj_type}")
        st.rerun()
    if inj_list and st.button("🗑️ Clear All Injuries"):
        st.session_state["injury_history"] = []
        st.rerun()


# ════════════════════════════════════════════════════════════════════════
# TAB — LOG TRAINING
# ════════════════════════════════════════════════════════════════════════
with tab_train:
    st.subheader("🏋️ Log Training Session")
    with st.form("form_training"):
        c1,c2,c3 = st.columns(3)
        with c1:
            td    = st.date_input("Session Date", value=date.today())
            tdur  = st.number_input("Duration (min)", 5, 300, value=60)
        with c2:
            tint  = st.slider("Intensity (1–10)", 1, 10, value=6)
            tdist = st.number_input("Distance (km)", 0.0, 100.0, value=5.0, step=0.1)
        with c3:
            thr   = st.number_input("Avg HR (bpm)", 60, 220, value=145)
            tspd  = st.number_input("Max Speed (km/h)", 0.0, 60.0, value=12.0, step=0.5)
        c4,c5 = st.columns(2)
        with c4: treps = st.number_input("Repetitions", 0, 500, value=20)
        with c5: tperf = st.slider("Performance Score (0–100)", 0, 100, value=70)
        tnotes = st.text_area("Notes", placeholder="e.g. felt strong…")
        log_t  = st.form_submit_button("✅ Log Session", type="primary", use_container_width=True)

    if log_t:
        st.session_state["training_sessions"].append({
            "Date":str(td),"Duration (min)":tdur,"Intensity":tint,"Distance (km)":tdist,
            "Avg HR (bpm)":thr,"Max Speed (km/h)":tspd,"Reps":treps,"Perf Score":tperf,"Notes":tnotes,
            "date":str(td),"duration_min":tdur,"intensity":tint,"running_distance_km":tdist,
            "avg_heart_rate":thr,"max_speed_kmh":tspd,"repetitions":treps,"performance_score":tperf,
        })
        if st.session_state["profile"].get("name","").strip():
            from athlete_store import save_athlete as _sa
            _sid = _sa(st.session_state["athlete_id"], st.session_state["profile"],
                       st.session_state["fitness"], st.session_state["training_sessions"],
                       st.session_state["recovery_data"], st.session_state["injury_history"],
                       st.session_state.get("ai_results",{}))
            st.session_state["athlete_id"] = _sid
        st.success(f"✅ Session logged for {td}!"); st.rerun()

    t_list = st.session_state["training_sessions"]
    st.markdown(f"#### Training Log ({len(t_list)} sessions)")
    if t_list:
        show = ["Date","Duration (min)","Intensity","Distance (km)",
                "Avg HR (bpm)","Max Speed (km/h)","Reps","Perf Score","Notes"]
        st.markdown(_html_table([{c:r.get(c,"") for c in show} for r in
                                 sorted(t_list, key=lambda r:r["date"], reverse=True)]),
                    unsafe_allow_html=True)
        if st.button("🗑️ Clear All Sessions"): st.session_state["training_sessions"]=[]; st.rerun()
    else:
        st.info("No sessions yet.")


# ════════════════════════════════════════════════════════════════════════
# TAB — LOG RECOVERY
# ════════════════════════════════════════════════════════════════════════
with tab_rec_log:
    st.subheader("💤 Log Recovery & Wellness")
    with st.form("form_recovery"):
        rc1,rc2,rc3 = st.columns(3)
        with rc1:
            rd    = st.date_input("Date", value=date.today())
            rslp  = st.number_input("Sleep Hours", 0.0, 14.0, value=7.5, step=0.5)
            rqlty = st.slider("Sleep Quality (1–10)", 1, 10, value=7)
        with rc2:
            rhrv  = st.number_input("HRV (ms)", 10, 200, value=55)
            rsore = st.slider("Muscle Soreness (1–10)", 1, 10, value=4)
            rstrs = st.slider("Stress Level (1–10)", 1, 10, value=4)
        with rc3:
            rhydr = st.slider("Hydration (1–10)", 1, 10, value=7)
            rmeth = st.selectbox("Recovery Method", RECOVERY_METHODS)
        rnotes = st.text_area("Notes", placeholder="e.g. good rest day…")
        log_r  = st.form_submit_button("✅ Log Recovery", type="primary", use_container_width=True)

    if log_r:
        st.session_state["recovery_data"].append({
            "Date":str(rd),"Sleep (hrs)":rslp,"Sleep Quality":rqlty,"HRV (ms)":rhrv,
            "Soreness":rsore,"Stress":rstrs,"Hydration":rhydr,"Method":rmeth,"Notes":rnotes,
            "date":str(rd),"sleep_hours":rslp,"sleep_quality":rqlty,"hrv":rhrv,
            "muscle_soreness":rsore,"stress_level":rstrs,"hydration_level":rhydr,"recovery_method":rmeth,
        })
        if st.session_state["profile"].get("name","").strip():
            from athlete_store import save_athlete as _sa
            _sid = _sa(st.session_state["athlete_id"], st.session_state["profile"],
                       st.session_state["fitness"], st.session_state["training_sessions"],
                       st.session_state["recovery_data"], st.session_state["injury_history"],
                       st.session_state.get("ai_results",{}))
            st.session_state["athlete_id"] = _sid
        st.success(f"✅ Recovery logged for {rd}!"); st.rerun()

    r_list = st.session_state["recovery_data"]
    st.markdown(f"#### Recovery Log ({len(r_list)} entries)")
    if r_list:
        show_r = ["Date","Sleep (hrs)","Sleep Quality","HRV (ms)","Soreness","Stress","Hydration","Method","Notes"]
        st.markdown(_html_table([{c:r.get(c,"") for c in show_r} for r in
                                 sorted(r_list, key=lambda r:r["date"], reverse=True)]),
                    unsafe_allow_html=True)
        if st.button("🗑️ Clear All Recovery"): st.session_state["recovery_data"]=[]; st.rerun()
    else:
        st.info("No recovery entries yet.")


# ════════════════════════════════════════════════════════════════════════
# TAB — PERFORMANCE
# ════════════════════════════════════════════════════════════════════════
with tab_perf:
    st.subheader("📊 Performance Analytics")
    if not training:
        st.info("No training data yet. Log your sessions in the 🏋️ Log Training tab.")
    else:
        dates = _col(training,"date")
        perf  = _col(training,"performance_score")
        avg_p = sum(perf)/len(perf)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=perf, mode="lines+markers",
                                 name="Performance Score",
                                 line=dict(color="#3b82d4",width=2), marker=dict(size=5)))
        fig.add_hline(y=avg_p, line_dash="dash", line_color="#7c5cd8",
                      annotation_text=f"Avg {avg_p:.1f}")
        fig.update_layout(title="Performance Score Over Time",
                          xaxis_title="Date", yaxis_title="Score (0–100)",
                          height=300, margin=dict(t=40,b=20),
                          paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                          font=dict(color="#e5e7eb"))
        st.plotly_chart(fig, use_container_width=True)

        c1,c2 = st.columns(2)
        with c1:
            fig2 = make_subplots(specs=[[{"secondary_y":True}]])
            fig2.add_trace(go.Bar(x=dates, y=_col(training,"duration_min"),
                                  name="Duration (min)", marker_color="#bfdbfe"), secondary_y=False)
            fig2.add_trace(go.Scatter(x=dates, y=_col(training,"intensity"),
                                      name="Intensity", line=dict(color="#3b82d4",width=2)), secondary_y=True)
            fig2.update_layout(title="Duration & Intensity", height=280,
                               margin=dict(t=40,b=20),
                               legend=dict(orientation="h",yanchor="bottom",y=1.02),
                               paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                               font=dict(color="#e5e7eb"))
            fig2.update_yaxes(title_text="Duration (min)", secondary_y=False)
            fig2.update_yaxes(title_text="Intensity (1–10)", secondary_y=True)
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            fig3 = go.Figure(go.Scatter(x=dates, y=_col(training,"running_distance_km"),
                                        fill="tozeroy", line=dict(color="#7c5cd8",width=2)))
            fig3.update_layout(title="Running Distance (km)", height=280, margin=dict(t=40,b=20),
                               paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                               font=dict(color="#e5e7eb"))
            st.plotly_chart(fig3, use_container_width=True)

        c3,c4 = st.columns(2)
        with c3:
            fig4 = go.Figure(go.Scatter(x=dates, y=_col(training,"avg_heart_rate"),
                                        mode="lines", line=dict(color="#ef4444",width=2)))
            fig4.update_layout(title="Avg Heart Rate (bpm)", height=260, margin=dict(t=40,b=20),
                               paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                               font=dict(color="#e5e7eb"))
            st.plotly_chart(fig4, use_container_width=True)
        with c4:
            fig5 = go.Figure(go.Scatter(x=dates, y=_col(training,"max_speed_kmh"),
                                        mode="lines", line=dict(color="#f59e0b",width=2)))
            fig5.update_layout(title="Max Speed (km/h)", height=260, margin=dict(t=40,b=20),
                               paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                               font=dict(color="#e5e7eb"))
            st.plotly_chart(fig5, use_container_width=True)

        # Fitness radar
        st.subheader("Fitness Snapshot")
        vo2_n = round(min(10, fitness["vo2_max"]/75*10), 1)
        rhr_n = round(min(10, max(0,(75-fitness["resting_heart_rate"])/30*10)), 1)
        bf_n  = round(min(10, max(0,(25-fitness["body_fat_pct"])/17*10)), 1)
        cats = ["VO2 Max","Flexibility","Strength","Resting HR","Body Fat"]
        vals = [vo2_n, fitness["flexibility_score"], fitness["strength_index"], rhr_n, bf_n]
        fig6 = go.Figure(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]],
                                          fill="toself", fillcolor="rgba(59,130,212,0.2)",
                                          line=dict(color="#3b82d4")))
        fig6.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,10])),
                           height=320, margin=dict(t=40,b=20),
                           paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                           font=dict(color="#e5e7eb"))
        st.plotly_chart(fig6, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — INJURY RISK
# ════════════════════════════════════════════════════════════════════════
with tab_inj:
    st.subheader("🩺 Injury Risk Assessment")
    if not training:
        st.info("Log training sessions to enable injury risk analysis.")
    else:
        last14 = _tail(training, 14)
        avg_all = _avg(training,"intensity")
        avg_14d = _avg(last14,"intensity")
        load_spike = avg_14d / max(avg_all,1)
        past_inj   = len(injuries)
        rhr        = fitness["resting_heart_rate"]

        risk_score = max(0, min(100, int(
            (load_spike-1)*30 + past_inj*10 +
            max(0,rhr-60)*0.5 + (10-fitness["flexibility_score"])*2)))

        if risk_score<30:    rc,rcol,ri = "Low","#16a34a","🟢"
        elif risk_score<60:  rc,rcol,ri = "Medium","#d97706","🟡"
        elif risk_score<80:  rc,rcol,ri = "High","#c2410c","🟠"
        else:                rc,rcol,ri = "Critical","#dc2626","🔴"

        c1,c2,c3 = st.columns([1,1,2])
        with c1:
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=risk_score, title={"text":"Risk Score"},
                gauge={"axis":{"range":[0,100]},"bar":{"color":rcol},
                       "steps":[{"range":[0,30],"color":"#dcfce7"},
                                 {"range":[30,60],"color":"#fef9c3"},
                                 {"range":[60,80],"color":"#ffedd5"},
                                 {"range":[80,100],"color":"#fee2e2"}]}))
            fig_g.update_layout(height=280, margin=dict(t=20,b=20,l=20,r=20),
                                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_g, use_container_width=True)
        with c2:
            st.markdown(f"### {ri} {rc} Risk")
            st.markdown(f"**Score:** {risk_score}/100")
            st.markdown(f"**Injuries on record:** {past_inj}")
            st.markdown(f"**Avg intensity (14d):** {avg_14d:.1f}/10")
            st.markdown(f"**Flexibility:** {fitness['flexibility_score']}/10")
            st.markdown(f"**Resting HR:** {rhr} bpm")
            st.markdown(f"**Load spike ratio:** {load_spike:.2f}×")
        with c3:
            if injuries:
                st.markdown("#### Injury History")
                st.markdown(_html_table(injuries), unsafe_allow_html=True)
            else:
                st.info("No injury history. ✅")

        # Training load chart
        st.subheader("Training Load Trend")
        loads = [r["intensity"]*r["duration_min"] for r in training]
        rolling = []
        for i in range(len(loads)):
            w = loads[max(0,i-6):i+1]
            rolling.append(sum(w)/len(w))
        fig_l = go.Figure()
        fig_l.add_trace(go.Bar(x=_col(training,"date"), y=loads,
                               name="Daily Load", marker_color="#bfdbfe"))
        fig_l.add_trace(go.Scatter(x=_col(training,"date"), y=rolling,
                                   mode="lines", name="7-Day Avg",
                                   line=dict(color="#dc2626",width=2)))
        fig_l.update_layout(title="Daily Load (Intensity×Duration) + 7-Day Rolling Avg",
                            height=280, margin=dict(t=40,b=20),
                            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                            font=dict(color="#e5e7eb"))
        st.plotly_chart(fig_l, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — WELLNESS
# ════════════════════════════════════════════════════════════════════════
with tab_well:
    st.subheader("🌿 Recovery & Wellness")
    if not recovery:
        st.info("No recovery data yet.")
    else:
        last7 = _tail(recovery,7)
        ws = round(min(10.0,
            _avg(last7,"sleep_quality")*0.25 + _avg(last7,"hydration_level")*0.15 +
            (10-_avg(last7,"muscle_soreness"))*0.20 + (10-_avg(last7,"stress_level"))*0.20 +
            (_avg(last7,"hrv")/100*10)*0.20), 1)

        wc1,wc2 = st.columns([1,3])
        with wc1:
            fig_w = go.Figure(go.Indicator(
                mode="gauge+number", value=ws, title={"text":"Wellness"},
                gauge={"axis":{"range":[0,10]},"bar":{"color":"#3b82d4"},
                       "steps":[{"range":[0,4],"color":"#fee2e2"},
                                 {"range":[4,7],"color":"#fef9c3"},
                                 {"range":[7,10],"color":"#dcfce7"}]}))
            fig_w.update_layout(height=240, margin=dict(t=20,b=20,l=20,r=20),
                                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_w, use_container_width=True)
        with wc2:
            kc1,kc2,kc3,kc4 = st.columns(4)
            kc1.metric("Avg Sleep", f"{round(_avg(last7,'sleep_hours'),1)} hrs")
            kc2.metric("Sleep Quality", f"{round(_avg(last7,'sleep_quality'),1)}/10")
            kc3.metric("Avg HRV", f"{round(_avg(last7,'hrv'))} ms")
            kc4.metric("Avg Soreness", f"{round(_avg(last7,'muscle_soreness'),1)}/10")

        rdates = _col(recovery,"date")
        fig_sl = make_subplots(specs=[[{"secondary_y":True}]])
        fig_sl.add_trace(go.Bar(x=rdates, y=_col(recovery,"sleep_hours"),
                                name="Sleep (hrs)", marker_color="#bfdbfe"), secondary_y=False)
        fig_sl.add_trace(go.Scatter(x=rdates, y=_col(recovery,"sleep_quality"),
                                    name="Sleep Quality", line=dict(color="#7c5cd8",width=2)), secondary_y=True)
        fig_sl.update_layout(title="Sleep Hours & Quality", height=260, margin=dict(t=40,b=20),
                             paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                             font=dict(color="#e5e7eb"))
        fig_sl.update_yaxes(title_text="Hours", secondary_y=False)
        fig_sl.update_yaxes(title_text="Quality (1–10)", secondary_y=True)
        st.plotly_chart(fig_sl, use_container_width=True)

        c3,c4 = st.columns(2)
        with c3:
            fig_hrv = go.Figure(go.Scatter(x=rdates, y=_col(recovery,"hrv"),
                                           mode="lines+markers", line=dict(color="#16a34a",width=2)))
            fig_hrv.update_layout(title="HRV (ms)", height=260, margin=dict(t=40,b=20),
                                  paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                  font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_hrv, use_container_width=True)
        with c4:
            fig_ss = go.Figure()
            fig_ss.add_trace(go.Scatter(x=rdates, y=_col(recovery,"stress_level"),
                                        name="Stress", line=dict(color="#ef4444",width=2)))
            fig_ss.add_trace(go.Scatter(x=rdates, y=_col(recovery,"muscle_soreness"),
                                        name="Soreness", line=dict(color="#f59e0b",width=2)))
            fig_ss.update_layout(title="Stress & Soreness (1–10)", height=260, margin=dict(t=40,b=20),
                                 paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                 font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_ss, use_container_width=True)

        st.subheader("Recovery Methods Used")
        cnt = Counter(_col(recovery,"recovery_method"))
        fig_m = go.Figure(go.Bar(x=list(cnt.keys()), y=list(cnt.values()),
                                  marker_color="#3b82d4",
                                  text=list(cnt.values()), textposition="auto"))
        fig_m.update_layout(title="Recovery Method Frequency", height=260, margin=dict(t=40,b=20),
                            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                            font=dict(color="#e5e7eb"))
        st.plotly_chart(fig_m, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — PREDICTIONS
# ════════════════════════════════════════════════════════════════════════
with tab_pred:
    st.subheader("🔮 Health Predictions & Risk Forecast")
    from predictions import CRITICAL as PC, WARNING as PW, CAUTION as PCau, OK as POK

    if not training and not recovery:
        st.info("Log training or recovery data to see predictions.")
    else:
        alerts        = pred_result["alerts"]
        overall_risk  = pred_result["overall_risk"]
        risk_level    = pred_result["risk_level"]
        fc_days       = pred_result["forecast_days"]
        fc_scores     = pred_result["forecast_scores"]
        summary       = pred_result["summary"]

        LVLC = {"Low":("#0d2318","#16a34a"),"Moderate":("#262208","#eab308"),
                "High":("#2d1f0a","#f97316"),"Critical":("#2d1515","#dc2626")}
        bg,tc = LVLC.get(risk_level,("#1a1d27","#9ca3af"))
        st.markdown(
            f'<div style="background:{bg};border-left:5px solid {tc};border-radius:6px;'
            f'padding:14px 18px;margin-bottom:12px">'
            f'<span style="font-size:1.1rem;font-weight:700;color:{tc}">'
            f'Overall Risk: {risk_level} ({overall_risk}/100)</span><br>'
            f'<span style="color:#d1d5db;font-size:0.95rem">{summary}</span></div>',
            unsafe_allow_html=True)

        gk1,gk2,gk3,gk4 = st.columns(4)
        gk1.metric("🔴 Critical", sum(1 for a in alerts if a["severity"]==PC))
        gk2.metric("🟠 Warnings", sum(1 for a in alerts if a["severity"]==PW))
        gk3.metric("🟡 Cautions", sum(1 for a in alerts if a["severity"]==PCau))
        gk4.metric("✅ Healthy",  sum(1 for a in alerts if a["severity"]==POK))
        st.divider()

        # 7-day forecast chart
        st.markdown("#### 📈 7-Day Risk Forecast")
        fc_colors = ["#dc2626" if s>=70 else "#f97316" if s>=45 else
                     "#eab308" if s>=25 else "#16a34a" for s in fc_scores]
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=fc_days, y=fc_scores,
                                     mode="lines+markers+text",
                                     line=dict(color="#3b82d4",width=3),
                                     marker=dict(size=10,color=fc_colors,
                                                 line=dict(color="white",width=2)),
                                     text=[f"{s:.0f}" for s in fc_scores],
                                     textposition="top center", name="Predicted Risk"))
        fig_fc.add_hrect(y0=0, y1=25, fillcolor="#dcfce7", opacity=0.2, line_width=0,
                          annotation_text="Low",      annotation_position="left")
        fig_fc.add_hrect(y0=25,y1=45, fillcolor="#fef9c3", opacity=0.2, line_width=0,
                          annotation_text="Moderate", annotation_position="left")
        fig_fc.add_hrect(y0=45,y1=70, fillcolor="#ffedd5", opacity=0.2, line_width=0,
                          annotation_text="High",     annotation_position="left")
        fig_fc.add_hrect(y0=70,y1=100,fillcolor="#fee2e2", opacity=0.2, line_width=0,
                          annotation_text="Critical", annotation_position="left")
        fig_fc.update_layout(title="Projected Health Risk — Next 7 Days",
                             yaxis=dict(range=[0,100]), height=320, margin=dict(t=50,b=30),
                             paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                             font=dict(color="#e5e7eb"))
        st.plotly_chart(fig_fc, use_container_width=True)
        st.divider()

        # Alert cards
        st.markdown("#### 🚨 Active Alerts & Recommendations")
        if not alerts:
            st.success("✅ No active health alerts. All metrics look healthy!")
        else:
            for a in alerts:
                _alert_card(a["severity"], a["category"], a["title"],
                            a["detail"], a["recommendation"])

        # Risk breakdown
        if alerts:
            st.divider()
            st.markdown("#### 📊 Risk Score by Category")
            fig_bar = go.Figure(go.Bar(
                x=[a["category"] for a in alerts],
                y=[a["risk_score"] for a in alerts],
                marker_color=["#dc2626" if a["severity"]==PC else
                              "#f97316" if a["severity"]==PW else
                              "#eab308" if a["severity"]==PCau else "#16a34a"
                              for a in alerts],
                text=[a["risk_score"] for a in alerts], textposition="auto"))
            fig_bar.update_layout(yaxis=dict(range=[0,100]), height=300,
                                  margin=dict(t=40,b=20),
                                  paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                  font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_bar, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — TRAINING PLAN
# ════════════════════════════════════════════════════════════════════════
with tab_plan:
    st.subheader("📋 Weekly Training Plan")
    st.info("Auto-generated heuristic plan based on your data. Use 🤖 AI Reports for a full AI-generated plan.")
    if not training:
        st.warning("Log training sessions to generate a plan.")
    else:
        avg_int = _avg(_tail(training,14),"intensity")
        if avg_int>=7:   focus,ints = "Recovery & Consolidation",[5,7,4,7,6,4,3]
        elif avg_int>=5: focus,ints = "Progressive Overload",    [6,8,5,8,7,5,3]
        else:            focus,ints = "Foundation Building",     [5,6,4,6,5,4,3]

        sport = profile.get("sport","Sport")
        days  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        types = ["Aerobic Base","High-Intensity Intervals","Strength & Conditioning",
                 "Sport-Specific Skills","Tempo / Moderate Cardio","Active Recovery","Full Rest"]
        durs  = [60,45,50,60,50,30,0]
        notes = [f"{sport} aerobic endurance","Sprint intervals 6×400m@90%",
                 "Core + compound lifts",f"{sport}-specific drills",
                 "70–75% max HR","Foam rolling, yoga, light swim","Complete rest"]
        plan  = [{"Day":days[i],"Session":types[i],"Intensity":ints[i],
                  "Duration (min)":durs[i],"Notes":notes[i]} for i in range(7)]

        st.markdown(f"**Weekly Focus:** {focus} &nbsp;·&nbsp; **Avg 14d Intensity:** {avg_int:.1f}/10")
        st.markdown(_html_table(plan), unsafe_allow_html=True)

        active = [r for r in plan if r["Duration (min)"]>0]
        fig_p = go.Figure(go.Bar(
            x=[r["Day"] for r in active], y=[r["Duration (min)"] for r in active],
            marker_color=[f"rgba(59,130,212,{r['Intensity']/10})" for r in active],
            text=[f"Int {r['Intensity']}" for r in active], textposition="auto"))
        fig_p.update_layout(title="Weekly Session Load", height=280, margin=dict(t=40,b=20),
                            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                            font=dict(color="#e5e7eb"))
        st.plotly_chart(fig_p, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — NOTIFICATIONS
# ════════════════════════════════════════════════════════════════════════
with tab_notif:
    st.subheader("🔔 Notifications & Alerts")

    from notification_engine import (get_all_notifications, count_unread,
                                      CRITICAL as NC, WARNING as NW,
                                      CAUTION as NCau, INFO as NI, SUCCESS as NS,
                                      SEVERITY_COLOR)

    notifs = get_all_notifications(training, recovery, injuries,
                                   pred_result=pred_result,
                                   agent_outputs=st.session_state.get("ai_results"))
    uc2 = count_unread(notifs)

    # Summary banner
    if uc2["total"]:
        st.markdown(
            f'<div style="background:#262208;border-left:5px solid #eab308;'
            f'border-radius:6px;padding:12px 16px;margin-bottom:12px;color:#e5e7eb">'
            f'<strong>🔔 {uc2["total"]} unread notification(s)</strong> — '
            f'🔴 {uc2.get(NC,0)} Critical &nbsp; '
            f'🟠 {uc2.get(NW,0)} Warnings &nbsp; '
            f'🟡 {uc2.get(NCau,0)} Cautions &nbsp; '
            f'🔵 {uc2.get(NI,0)} Info</div>',
            unsafe_allow_html=True)
    else:
        st.success("✅ All caught up — no unread notifications!")

    st.divider()

    # Filter
    sev_filter = st.multiselect("Filter by Severity",
                                [NC, NW, NCau, NI, NS],
                                default=[NC, NW, NCau, NI, NS])

    shown = [n for n in notifs if n["severity"] in sev_filter]
    st.markdown(f"**Showing {len(shown)} notification(s)**")
    st.divider()

    if not shown:
        st.info("No notifications match the selected filter.")
    else:
        DARK_NOTIF_COLORS = {
            "CRITICAL": ("#2d1515","#dc2626"),
            "WARNING":  ("#2d1f0a","#f97316"),
            "CAUTION":  ("#262208","#eab308"),
            "INFO":     ("#0f1f35","#3b82f6"),
            "SUCCESS":  ("#0d2318","#16a34a"),
        }
        for n in shown:
            bg_c, border_c = DARK_NOTIF_COLORS.get(n["severity"], ("#1a1d27","#9ca3af"))
            emoji = {"CRITICAL":"🔴","WARNING":"🟠","CAUTION":"🟡",
                     "INFO":"🔵","SUCCESS":"🟢"}.get(n["severity"],"⚪")
            read_badge = "" if n["read"] else ' <span style="font-size:10px;background:#3b82d4;color:white;border-radius:8px;padding:1px 6px">NEW</span>'
            st.markdown(
                f'<div style="background:{bg_c};border-left:5px solid {border_c};'
                f'border-radius:6px;padding:12px 16px;margin-bottom:10px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-weight:700;color:{border_c};font-size:0.95rem">'
                f'{emoji} [{n["severity"]}] {n["category"]}{read_badge}</span>'
                f'<span style="font-size:11px;color:#9ca3af">{n["timestamp"]}</span></div>'
                f'<div style="font-weight:600;margin:4px 0;color:#e5e7eb">{n["title"]}</div>'
                f'<div style="font-size:0.88rem;color:#d1d5db;margin-bottom:6px">{n["message"]}</div>'
                f'<div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:6px 10px;'
                f'font-size:0.85rem;color:#e5e7eb"><strong>✅ Action:</strong> {n["action"]}</div>'
                f'</div>', unsafe_allow_html=True)

    st.divider()
    # Notification summary table
    if notifs:
        st.markdown("#### 📋 Notification Summary Table")
        tbl = [{"Time":n["timestamp"],"Severity":n["severity"],"Category":n["category"],
                "Title":n["title"][:60]+"…" if len(n["title"])>60 else n["title"],
                "Status":"Unread" if not n["read"] else "Read"}
               for n in notifs]
        st.markdown(_html_table(tbl), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — AI REPORTS (5 Agents)
# ════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 5-Agent AI Analysis")

    # Agent grid legend
    st.markdown("**Active Agents in this Analysis:**")
    ag_cols = st.columns(5)
    for i, ag in enumerate(AGENTS):
        with ag_cols[i]:
            st.markdown(
                f'<div style="background:{ag["color"]}11;border:1px solid {ag["color"]}44;'
                f'border-radius:8px;padding:10px;text-align:center">'
                f'<div style="font-size:1.5rem">{ag["icon"]}</div>'
                f'<div style="font-size:0.8rem;font-weight:600;color:{ag["color"]}">'
                f'{ag["name"]}</div></div>', unsafe_allow_html=True)
    st.divider()

    if run_ai:
        api_key = os.environ.get("OPENAI_API_KEY","")
        if not api_key or api_key=="your_openai_api_key_here":
            st.error("No OpenAI API key found. Enter your key in the sidebar.")
        elif not training:
            st.warning("Log at least one training session first.")
        else:
            with st.spinner("🤖 All 5 agents are running… this may take 2–4 minutes."):
                try:
                    from crew import run_crew
                    user_data = {
                        "profile":           profile,
                        "fitness":           fitness,
                        "fitness_assessment":fitness,
                        "training_sessions": training,
                        "recovery_data":     recovery,
                        "injury_history":    injuries,
                    }
                    results = run_crew(athlete_data=user_data)
                    st.session_state["ai_results"] = results
                    st.success("✅ All 5 agents completed their analysis!")
                except Exception as e:
                    st.error(f"AI analysis failed: {e}")

    results = st.session_state.get("ai_results", {})
    if results:
        report_meta = [
            ("performance_report", "📊 Performance Analyst",    AGENTS[0]["color"]),
            ("injury_risk_report", "🩺 Injury Risk Specialist",  AGENTS[1]["color"]),
            ("recovery_report",    "💤 Recovery & Wellness Coach",AGENTS[2]["color"]),
            ("nutrition_report",   "🥗 Sports Nutritionist",     AGENTS[3]["color"]),
            ("training_plan",      "📋 Periodisation Coach",     AGENTS[4]["color"]),
        ]
        # Show in 2+2+1 layout
        for i in range(0, len(report_meta), 2):
            cols = st.columns(2)
            for j, (key, label, color) in enumerate(report_meta[i:i+2]):
                with cols[j]:
                    st.markdown(
                        f'<div style="border-left:4px solid {color};'
                        f'padding:4px 8px;margin-bottom:4px;font-weight:600;'
                        f'color:{color}">{label}</div>', unsafe_allow_html=True)
                    with st.expander("View Full Report", expanded=(i==0 and j==0)):
                        st.markdown(results.get(key, "No output."))
    else:
        st.info(
            "Click **🤖 Run 5-Agent AI Analysis** in the sidebar.\n\n"
            "What each agent produces:\n"
            "- 📊 **Performance Analyst** — trends, weaknesses, coaching insights\n"
            "- 🩺 **Injury Risk Specialist** — risk score 0–100, top risk factors, preventions\n"
            "- 💤 **Recovery Coach** — wellness score, HRV trend, readiness verdict\n"
            "- 🥗 **Sports Nutritionist** — macros, hydration protocol, meal plan\n"
            "- 📋 **Periodisation Coach** — integrated 7-day training programme"
        )


# ════════════════════════════════════════════════════════════════════════
# TAB — LIVE SENSOR
# ════════════════════════════════════════════════════════════════════════
with tab_sensor:
    st.subheader("📡 Live Wearable Sensor — Real-Time Biometrics")

    from sensor_engine import (get_live_reading, evaluate_thresholds,
                                reset_simulation, METRIC_LABELS, METRIC_UNITS,
                                THRESHOLDS)

    # ── Status banner ──────────────────────────────────────────────────
    is_active = st.session_state["sensor_active"]
    reading   = st.session_state.get("sensor_reading")
    history   = st.session_state.get("sensor_history", [])
    sal       = st.session_state.get("sensor_alerts", [])

    if not is_active:
        st.markdown(
            '<div style="background:#1a1d27;border:2px dashed #2d3748;border-radius:10px;'
            'padding:24px;text-align:center;color:#9ca3af;margin-bottom:16px">'
            '<div style="font-size:2rem">📡</div>'
            '<div style="font-size:1.1rem;font-weight:600;margin:8px 0">Sensor Offline</div>'
            '<div>Press <strong>▶ Start</strong> in the sidebar to begin live streaming.</div>'
            '<div style="font-size:0.85rem;margin-top:8px;color:#6b7280">'
            'Simulates a BLE/ANT+ wearable. Connect a real device by entering '
            'readings in the <strong>Real Device Input</strong> form below.</div>'
            '</div>',
            unsafe_allow_html=True)
    else:
        # Auto-refresh every 3 s using st.empty() placeholder + rerun
        st.markdown(
            '<div style="background:#0d2318;border-left:4px solid #16a34a;'
            'border-radius:6px;padding:10px 16px;margin-bottom:12px;color:#e5e7eb">'
            '🟢 <strong>SENSOR LIVE</strong> — streaming every 3 seconds. '
            'Switch to this tab to see real-time data. Use ⏹ Stop in the sidebar to pause.</div>',
            unsafe_allow_html=True)
        # Trigger rerun to tick the sensor
        import time as _time
        _time.sleep(3)
        st.rerun()

    # ── Live KPI gauges ────────────────────────────────────────────────
    if reading:
        phase = reading.get("session_phase","—").upper()
        phase_color = {"WARMUP":"#3b82d4","ACTIVE":"#f59e0b","PEAK":"#ef4444","COOLDOWN":"#16a34a"}.get(phase,"#9ca3af")
        st.markdown(
            f'<div style="background:#1a1d27;border-radius:8px;padding:10px 16px;'
            f'margin-bottom:12px;display:flex;gap:12px;align-items:center">'
            f'<span style="font-size:0.85rem;color:#9ca3af">Session Phase:</span>'
            f'<span style="background:{phase_color}22;color:{phase_color};border:1px solid {phase_color}44;'
            f'border-radius:12px;padding:2px 10px;font-weight:700;font-size:0.85rem">{phase}</span>'
            f'<span style="font-size:0.85rem;color:#9ca3af;margin-left:auto">Last update: {reading["timestamp"]}</span>'
            f'</div>', unsafe_allow_html=True)

        # 4 primary KPI gauges
        def _gauge(fig_id, label, value, unit, color, min_v, max_v, thresholds_hi=None, height=200):
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": f"{label}<br><span style='font-size:0.75rem;color:#9ca3af'>{unit}</span>",
                       "font": {"color": "#e5e7eb", "size": 13}},
                number={"font": {"color": color, "size": 24}, "suffix": f" {unit}"},
                gauge={
                    "axis": {"range": [min_v, max_v], "tickcolor": "#4b5563"},
                    "bar":  {"color": color},
                    "bgcolor": "#0f1117",
                    "bordercolor": "#2d3748",
                    "steps": (thresholds_hi or []),
                }
            ))
            fig.update_layout(
                height=height, margin=dict(t=30, b=10, l=10, r=10),
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                font=dict(color="#e5e7eb"))
            return fig

        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.plotly_chart(_gauge("hr", "Heart Rate", reading["heart_rate"], "bpm",
                "#ef4444", 40, 220,
                [{"range":[40,120],"color":"#0d2318"},
                 {"range":[120,165],"color":"#1a2d1a"},
                 {"range":[165,180],"color":"#2d1f0a"},
                 {"range":[180,220],"color":"#2d1515"}]), use_container_width=True)
        with g2:
            st.plotly_chart(_gauge("spo2", "SpO₂", reading["spo2"], "%",
                "#3b82d4", 85, 100,
                [{"range":[85,91],"color":"#2d1515"},
                 {"range":[91,94],"color":"#2d1f0a"},
                 {"range":[94,96],"color":"#262208"},
                 {"range":[96,100],"color":"#0d2318"}]), use_container_width=True)
        with g3:
            st.plotly_chart(_gauge("hrv", "HRV", reading["hrv_ms"], "ms",
                "#8b5cf6", 10, 120,
                [{"range":[10,20],"color":"#2d1515"},
                 {"range":[20,30],"color":"#2d1f0a"},
                 {"range":[30,40],"color":"#262208"},
                 {"range":[40,120],"color":"#0d2318"}]), use_container_width=True)
        with g4:
            st.plotly_chart(_gauge("temp", "Skin Temp", reading["skin_temp_c"], "°C",
                "#10b981", 35, 40,
                [{"range":[35,37.5],"color":"#0d2318"},
                 {"range":[37.5,38.0],"color":"#262208"},
                 {"range":[38.0,38.5],"color":"#2d1f0a"},
                 {"range":[38.5,40],"color":"#2d1515"}]), use_container_width=True)

        # Secondary metrics row
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("⚡ Speed",    f"{reading['speed_kmh']} km/h")
        m2.metric("🦶 Cadence",  f"{reading['cadence_rpm']} rpm")
        m3.metric("👟 Steps",    f"{reading['steps']:,}")
        m4.metric("📏 Distance", f"{reading['distance_m']:,} m")
        m5.metric("🔥 Calories", f"{reading['calories_burned']} kcal")

    # ── Live HR & HRV chart (rolling history) ──────────────────────────
    if len(history) >= 2:
        st.markdown("#### 📈 Live Trend (Last 60 Readings)")
        times = [r["timestamp"] for r in history]
        hrc1, hrc2 = st.columns(2)
        with hrc1:
            fig_hr_live = go.Figure()
            fig_hr_live.add_trace(go.Scatter(
                x=times, y=[r["heart_rate"] for r in history],
                mode="lines", name="Heart Rate",
                line=dict(color="#ef4444", width=2),
                fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"))
            # Threshold bands
            fig_hr_live.add_hline(y=180, line_dash="dash", line_color="#f97316",
                                  annotation_text="Warning 180", annotation_font_color="#f97316")
            fig_hr_live.add_hline(y=195, line_dash="dot", line_color="#dc2626",
                                  annotation_text="Critical 195", annotation_font_color="#dc2626")
            fig_hr_live.update_layout(title="Heart Rate (bpm)", height=240,
                                      margin=dict(t=40,b=20),
                                      paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                      font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_hr_live, use_container_width=True)
        with hrc2:
            fig_hrv_live = go.Figure()
            fig_hrv_live.add_trace(go.Scatter(
                x=times, y=[r["hrv_ms"] for r in history],
                mode="lines", name="HRV",
                line=dict(color="#8b5cf6", width=2),
                fill="tozeroy", fillcolor="rgba(139,92,246,0.1)"))
            fig_hrv_live.add_hline(y=30, line_dash="dash", line_color="#f97316",
                                   annotation_text="Warning 30ms", annotation_font_color="#f97316")
            fig_hrv_live.add_hline(y=20, line_dash="dot", line_color="#dc2626",
                                   annotation_text="Critical 20ms", annotation_font_color="#dc2626")
            fig_hrv_live.update_layout(title="HRV (ms)", height=240,
                                       margin=dict(t=40,b=20),
                                       paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                       font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_hrv_live, use_container_width=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            fig_spo2_live = go.Figure(go.Scatter(
                x=times, y=[r["spo2"] for r in history],
                mode="lines", line=dict(color="#3b82d4", width=2),
                fill="tozeroy", fillcolor="rgba(59,130,212,0.1)"))
            fig_spo2_live.add_hline(y=94, line_dash="dash", line_color="#f97316",
                                    annotation_text="Warning 94%", annotation_font_color="#f97316")
            fig_spo2_live.add_hline(y=91, line_dash="dot", line_color="#dc2626",
                                    annotation_text="Critical 91%", annotation_font_color="#dc2626")
            fig_spo2_live.update_layout(title="SpO₂ (%)", height=220,
                                        yaxis=dict(range=[85,101]),
                                        margin=dict(t=40,b=20),
                                        paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                        font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_spo2_live, use_container_width=True)
        with sc2:
            fig_spd_live = go.Figure(go.Scatter(
                x=times, y=[r["speed_kmh"] for r in history],
                mode="lines", line=dict(color="#10b981", width=2),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.1)"))
            fig_spd_live.update_layout(title="Speed (km/h)", height=220,
                                       margin=dict(t=40,b=20),
                                       paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                       font=dict(color="#e5e7eb"))
            st.plotly_chart(fig_spd_live, use_container_width=True)

    # ── Real-time threshold alerts ─────────────────────────────────────
    # ── Live threshold notification banner ─────────────────────────────
    DARK_SEV_MAP = {
        "CRITICAL": ("#2d1515","#dc2626","🔴"),
        "WARNING":  ("#2d1f0a","#f97316","🟠"),
        "CAUTION":  ("#262208","#eab308","🟡"),
    }
    _athlete_disp = st.session_state["profile"].get("name","") or "Athlete"

    st.markdown("#### 🚨 Live Risk Notifications")

    if not sal:
        st.markdown(
            '<div style="background:#0d2318;border-left:4px solid #16a34a;'
            'border-radius:6px;padding:12px 16px;color:#e5e7eb">'
            f'✅ <strong>{_athlete_disp} — All metrics within safe thresholds.</strong></div>',
            unsafe_allow_html=True)
    else:
        # Sort: CRITICAL first
        _sorted_sal = sorted(sal, key=lambda x: {"CRITICAL":0,"WARNING":1,"CAUTION":2}.get(x["severity"],3))
        for a in _sorted_sal:
            bg_c, bdr_c, ico = DARK_SEV_MAP.get(a["severity"], ("#1a1d27","#9ca3af","⚪"))
            st.markdown(
                f'<div style="background:{bg_c};border-left:5px solid {bdr_c};'
                f'border-radius:6px;padding:12px 16px;margin-bottom:8px">'
                f'<div style="font-weight:700;color:{bdr_c};font-size:0.95rem">'
                f'{ico} [{a["severity"]}] {_athlete_disp} — {a["label"]} is {a["value"]} {a["unit"]}</div>'
                f'<div style="color:#d1d5db;font-size:0.9rem;margin:6px 0">{a["message"]}</div>'
                f'<div style="background:rgba(255,255,255,0.05);border-radius:4px;padding:6px 10px;'
                f'font-size:0.85rem;color:#e5e7eb">✅ <strong>Action:</strong> {a["action"]}</div>'
                f'<div style="font-size:0.75rem;color:#6b7280;margin-top:4px">Detected @ {a["timestamp"]}</div>'
                f'</div>', unsafe_allow_html=True)

    # ── Session notification history ────────────────────────────────────
    st.divider()
    st.markdown("#### 📋 Sensor Notification History (This Session)")
    _notif_log = st.session_state.get("sensor_notif_log", [])
    if not _notif_log:
        st.caption("No threshold breaches recorded yet this session.")
    else:
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("🔴 Critical", sum(1 for n in _notif_log if n["severity"]=="CRITICAL"))
        sc2.metric("🟠 Warnings", sum(1 for n in _notif_log if n["severity"]=="WARNING"))
        sc3.metric("🟡 Cautions", sum(1 for n in _notif_log if n["severity"]=="CAUTION"))

        # Show last 20 in reverse-chronological order
        _recent = list(reversed(_notif_log))[:20]
        log_rows = [{
            "Time":     n["timestamp"],
            "Athlete":  n.get("athlete","—"),
            "Severity": n["severity"],
            "Metric":   n["label"],
            "Value":    f"{n['value']} {n['unit']}",
            "Alert":    n["message"][:60] + ("…" if len(n["message"])>60 else ""),
        } for n in _recent]
        st.markdown(_html_table(log_rows), unsafe_allow_html=True)

        if st.button("🗑️ Clear Notification History", key="clr_notif_hist"):
            st.session_state["sensor_notif_log"] = []
            st.rerun()

    # ── Auto-log to session: append latest reading to recovery/training ─
    st.divider()
    st.markdown("#### 💾 Auto-Log Sensor Reading to Session")
    st.caption("Save the latest sensor snapshot as a recovery or training entry for analysis across all tabs.")
    if reading:
        log_col1, log_col2 = st.columns(2)
        with log_col1:
            if st.button("📥 Save as Recovery Entry", use_container_width=True):
                st.session_state["recovery_data"].append({
                    "Date": str(date.today()), "Sleep (hrs)": 0.0,
                    "Sleep Quality": 0, "HRV (ms)": reading["hrv_ms"],
                    "Soreness": 0, "Stress": 0,
                    "Hydration": 0, "Method": "Sensor", "Notes": f"Auto-logged from sensor @ {reading['timestamp']}",
                    "date": str(date.today()), "sleep_hours": 0.0, "sleep_quality": 0,
                    "hrv": reading["hrv_ms"], "muscle_soreness": 0, "stress_level": 0,
                    "hydration_level": 0, "recovery_method": "Sensor",
                })
                st.success("✅ Saved as recovery entry!")
        with log_col2:
            if st.button("📥 Save as Training Entry", use_container_width=True):
                st.session_state["training_sessions"].append({
                    "Date": str(date.today()),
                    "Duration (min)": 0,
                    "Intensity": reading["intensity"],
                    "Distance (km)": round(reading["distance_m"] / 1000, 2),
                    "Avg HR (bpm)": reading["heart_rate"],
                    "Max Speed (km/h)": reading["speed_kmh"],
                    "Reps": 0, "Perf Score": 0,
                    "Notes": f"Auto-logged from sensor @ {reading['timestamp']}",
                    "date": str(date.today()),
                    "duration_min": 0,
                    "intensity": reading["intensity"],
                    "running_distance_km": round(reading["distance_m"] / 1000, 2),
                    "avg_heart_rate": reading["heart_rate"],
                    "max_speed_kmh": reading["speed_kmh"],
                    "repetitions": 0, "performance_score": 0,
                })
                st.success("✅ Saved as training entry!")
    else:
        st.info("Start the sensor to get a live reading first.")

    # ── Real Device Input form ─────────────────────────────────────────
    st.divider()
    st.markdown("#### 🔌 Real Device Input")
    st.caption("If you have an actual wearable, enter live readings here. These override the simulated values.")
    # Sentinel values = the field's min_value → means "not provided"
    _HR_MIN, _SPO2_MIN, _HRV_MIN = 40, 80, 5
    _TEMP_MIN, _SPD_MIN, _CAD_MIN = 34.0, 0.0, 0
    _STEPS_MIN, _CAL_MIN = 0, 0.0

    with st.form("form_real_sensor"):
        rs1, rs2, rs3, rs4 = st.columns(4)
        with rs1:
            inp_hr   = st.number_input("Heart Rate (bpm)", min_value=_HR_MIN,   max_value=220,    value=_HR_MIN,   step=1)
            inp_spo2 = st.number_input("SpO₂ (%)",         min_value=_SPO2_MIN, max_value=100,    value=_SPO2_MIN, step=1)
        with rs2:
            inp_hrv  = st.number_input("HRV (ms)",          min_value=_HRV_MIN,  max_value=200,    value=_HRV_MIN,  step=1)
            inp_temp = st.number_input("Skin Temp (°C)",    min_value=_TEMP_MIN, max_value=40.0,   value=_TEMP_MIN, step=0.1)
        with rs3:
            inp_spd  = st.number_input("Speed (km/h)",      min_value=_SPD_MIN,  max_value=60.0,   value=_SPD_MIN,  step=0.1)
            inp_cad  = st.number_input("Cadence (rpm)",     min_value=_CAD_MIN,  max_value=300,    value=_CAD_MIN,  step=1)
        with rs4:
            inp_steps = st.number_input("Steps",            min_value=_STEPS_MIN,max_value=100000, value=_STEPS_MIN,step=1)
            inp_cal   = st.number_input("Calories (kcal)",  min_value=_CAL_MIN,  max_value=5000.0, value=_CAL_MIN,  step=1.0)
        apply_real = st.form_submit_button("📡 Apply Real Device Values", use_container_width=True, type="primary")

    if apply_real:
        real = {}
        # Only include fields the user actually changed away from the sentinel/minimum
        if inp_hr   > _HR_MIN:    real["heart_rate"]      = inp_hr
        if inp_spo2 > _SPO2_MIN:  real["spo2"]            = inp_spo2
        if inp_hrv  > _HRV_MIN:   real["hrv_ms"]          = inp_hrv
        if inp_temp > _TEMP_MIN:  real["skin_temp_c"]      = inp_temp
        if inp_spd  > _SPD_MIN:   real["speed_kmh"]        = inp_spd
        if inp_cad  > _CAD_MIN:   real["cadence_rpm"]      = inp_cad
        if inp_steps > _STEPS_MIN: real["steps"]           = inp_steps
        if inp_cal  > _CAL_MIN:   real["calories_burned"]  = inp_cal
        st.session_state["sensor_real_data"] = real
        # Immediately evaluate thresholds on real data
        from sensor_engine import evaluate_thresholds as _eval_thr
        sa2 = _eval_thr(real)
        st.session_state["sensor_alerts"] = sa2
        st.success(f"✅ {len(real)} real values applied. {len(sa2)} threshold alert(s) generated.")
        st.rerun()

    # ── Threshold reference table ──────────────────────────────────────
    st.divider()
    st.markdown("#### 📋 Threshold Reference")
    thr_rows = []
    for metric, (clo, wlo, crit_lo, chi, whi, crit_hi) in THRESHOLDS.items():
        label = METRIC_LABELS.get(metric, metric)
        unit  = METRIC_UNITS.get(metric, "")
        def _fmt(v): return f"{v} {unit}" if v is not None else "—"
        thr_rows.append({
            "Metric":      label,
            "Unit":        unit,
            "🟡 Caution Low":  _fmt(clo),
            "🟠 Warning Low":  _fmt(wlo),
            "🔴 Critical Low": _fmt(crit_lo),
            "🟡 Caution High": _fmt(chi),
            "🟠 Warning High": _fmt(whi),
            "🔴 Critical High":_fmt(crit_hi),
        })
    st.markdown(_html_table(thr_rows), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# TAB — ALL ATHLETES ROSTER
# ════════════════════════════════════════════════════════════════════════
with tab_roster:
    st.subheader("👥 All Athletes — Roster & Records")
    from athlete_store import list_athletes, load_athlete, save_athlete, delete_athlete

    all_athletes = list_athletes()

    if not all_athletes:
        st.markdown(
            '<div style="background:#1a1d27;border:2px dashed #2d3748;border-radius:10px;'
            'padding:32px;text-align:center;color:#9ca3af">'
            '<div style="font-size:2rem">👥</div>'
            '<div style="font-size:1.1rem;font-weight:600;margin:8px 0">No athletes saved yet</div>'
            '<div>Fill in the <strong>👤 Profile</strong> tab, then press '
            '<strong>💾 Save</strong> in the sidebar to add an athlete.</div>'
            '</div>',
            unsafe_allow_html=True)
    else:
        # ── Summary KPI strip ──────────────────────────────────────────
        rk1, rk2, rk3 = st.columns(3)
        rk1.metric("Total Athletes Saved", len(all_athletes))

        # Athlete with most sessions
        most_sessions = max(all_athletes,
            key=lambda a: len(load_athlete(a["id"]).get("training_sessions", [])))
        most_sessions_data = load_athlete(most_sessions["id"])
        rk2.metric("Most Active", most_sessions["name"],
                   f"{len(most_sessions_data.get('training_sessions',[]))} sessions")

        # Average age
        ages = []
        for a in all_athletes:
            d = load_athlete(a["id"])
            if d:
                ages.append(d.get("profile",{}).get("age", 0))
        rk3.metric("Avg Age", f"{round(sum(ages)/len(ages))} yrs" if ages else "—")

        st.divider()

        # ── Athlete cards grid ─────────────────────────────────────────
        st.markdown("#### 🏃 Athlete Cards")
        cols_per_row = 3
        for row_start in range(0, len(all_athletes), cols_per_row):
            row_athletes = all_athletes[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, meta in zip(cols, row_athletes):
                with col:
                    data = load_athlete(meta["id"])
                    if not data:
                        continue
                    p  = data.get("profile", {})
                    fi = data.get("fitness", {})
                    tr = data.get("training_sessions", [])
                    rc = data.get("recovery_data", [])
                    inj = data.get("injury_history", [])

                    # Risk colour
                    from predictions import run_predictions as _rp
                    _pr = _rp(p, fi, tr, rc, inj)
                    risk_level = _pr["risk_level"]
                    risk_score = _pr["overall_risk"]
                    risk_color = {"Low":"#16a34a","Moderate":"#eab308",
                                  "High":"#f97316","Critical":"#dc2626"}.get(risk_level,"#9ca3af")

                    is_current = (meta["id"] == st.session_state.get("athlete_id",""))
                    border_style = f"border:2px solid #3b82d4" if is_current else "border:1px solid #2d3748"

                    st.markdown(
                        f'<div style="background:#1a1d27;{border_style};border-radius:10px;'
                        f'padding:16px;margin-bottom:8px">'
                        f'<div style="font-size:1.1rem;font-weight:700;color:#e5e7eb;margin-bottom:6px">'
                        f'{"⭐ " if is_current else ""}{p.get("name","—")}</div>'
                        f'<div style="font-size:0.82rem;color:#9ca3af;margin-bottom:8px">'
                        f'{p.get("sport","—")} · Age {p.get("age","—")} · '
                        f'{p.get("experience_years","—")} yrs exp</div>'
                        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:0.82rem">'
                        f'<span style="color:#9ca3af">Sessions:</span>'
                        f'<span style="color:#e5e7eb;font-weight:600">{len(tr)}</span>'
                        f'<span style="color:#9ca3af">Recovery:</span>'
                        f'<span style="color:#e5e7eb;font-weight:600">{len(rc)}</span>'
                        f'<span style="color:#9ca3af">Injuries:</span>'
                        f'<span style="color:#e5e7eb;font-weight:600">{len(inj)}</span>'
                        f'<span style="color:#9ca3af">VO₂ Max:</span>'
                        f'<span style="color:#e5e7eb;font-weight:600">{fi.get("vo2_max","—")}</span>'
                        f'<span style="color:#9ca3af">Risk:</span>'
                        f'<span style="color:{risk_color};font-weight:700">'
                        f'{risk_level} ({risk_score})</span>'
                        f'</div>'
                        f'<div style="font-size:0.75rem;color:#6b7280;margin-top:8px">'
                        f'Saved: {meta["saved_at"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True)

                    # Load / Delete buttons per card
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if not is_current:
                            if st.button(f"📂 Load", key=f"load_{meta['id']}",
                                         use_container_width=True):
                                _load_athlete_into_state(meta["id"])
                                st.rerun()
                        else:
                            st.markdown(
                                '<div style="text-align:center;color:#3b82d4;'
                                'font-size:0.8rem;padding:4px 0">✅ Active</div>',
                                unsafe_allow_html=True)
                    with bc2:
                        if st.button(f"🗑️", key=f"del_{meta['id']}",
                                     use_container_width=True,
                                     help=f"Delete {meta['name']}"):
                            delete_athlete(meta["id"])
                            if is_current:
                                _new_athlete()
                            st.rerun()

        # ── Full roster comparison table ───────────────────────────────
        st.divider()
        st.markdown("#### 📊 Comparison Table")
        tbl_rows = []
        for meta in all_athletes:
            data = load_athlete(meta["id"])
            if not data:
                continue
            p  = data.get("profile", {})
            fi = data.get("fitness", {})
            tr = data.get("training_sessions", [])
            rc = data.get("recovery_data", [])
            inj= data.get("injury_history", [])
            from predictions import run_predictions as _rp2
            _pr2 = _rp2(p, fi, tr, rc, inj)
            avg_perf = round(sum(s.get("performance_score",0) for s in tr)/len(tr),1) if tr else "—"
            avg_hrv  = round(sum(r.get("hrv",0) for r in rc)/len(rc),1) if rc else "—"
            tbl_rows.append({
                "Name":          p.get("name","—"),
                "Sport":         p.get("sport","—"),
                "Age":           p.get("age","—"),
                "Sessions":      len(tr),
                "Avg Perf":      avg_perf,
                "Avg HRV (ms)":  avg_hrv,
                "Injuries":      len(inj),
                "VO₂ Max":       fi.get("vo2_max","—"),
                "Risk Level":    _pr2["risk_level"],
                "Risk Score":    _pr2["overall_risk"],
                "Last Saved":    meta["saved_at"],
            })
        st.markdown(_html_table(tbl_rows), unsafe_allow_html=True)

        # ── Export all athletes ────────────────────────────────────────
        st.divider()
        st.markdown("#### 📥 Export All Athletes")

        # Collect full data once
        all_data = []
        for meta in all_athletes:
            d = load_athlete(meta["id"])
            if d:
                all_data.append(d)

        ex_col1, ex_col2 = st.columns(2)

        # ── JSON download ──────────────────────────────────────────────
        with ex_col1:
            import json as _json
            export_str = _json.dumps(all_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="⬇️ Download All Athletes (JSON)",
                data=export_str,
                file_name="all_athletes.json",
                mime="application/json",
                use_container_width=True,
            )

        # ── Excel download ─────────────────────────────────────────────
        with ex_col2:
            import io as _io
            import openpyxl as _xl
            from openpyxl.styles import (Font as _Font, PatternFill as _Fill,
                                          Alignment as _Align, Border as _Border,
                                          Side as _Side)

            def _build_excel(athletes_data: list) -> bytes:
                wb = _xl.Workbook()

                # ── Colour palette ──
                HDR_FILL   = _Fill(fill_type="solid", fgColor="1E2130")
                ALT_FILL   = _Fill(fill_type="solid", fgColor="161922")
                ALT2_FILL  = _Fill(fill_type="solid", fgColor="1A1D27")
                HDR_FONT   = _Font(bold=True, color="E5E7EB", size=10)
                BODY_FONT  = _Font(color="E5E7EB", size=9)
                TITLE_FONT = _Font(bold=True, color="3B82D4", size=12)
                THIN_SIDE  = _Side(border_style="thin", color="2D3748")
                THIN_BORDER= _Border(left=THIN_SIDE, right=THIN_SIDE,
                                     top=THIN_SIDE, bottom=THIN_SIDE)
                CENTER     = _Align(horizontal="center", vertical="center")
                LEFT       = _Align(horizontal="left",   vertical="center", wrap_text=True)

                def _style_hdr(cell):
                    cell.fill   = HDR_FILL
                    cell.font   = HDR_FONT
                    cell.border = THIN_BORDER
                    cell.alignment = CENTER

                def _style_cell(cell, row_i):
                    cell.fill   = ALT_FILL if row_i % 2 == 0 else ALT2_FILL
                    cell.font   = BODY_FONT
                    cell.border = THIN_BORDER
                    cell.alignment = LEFT

                # ════════════════════════════════════════════════════
                # Sheet 1 — Roster Overview
                # ════════════════════════════════════════════════════
                ws = wb.active
                ws.title = "Roster Overview"
                ws.sheet_properties.tabColor = "3B82D4"

                # Title row
                ws.merge_cells("A1:L1")
                ws["A1"].value     = "🏃 Athlete Performance System — All Athletes Export"
                ws["A1"].font      = TITLE_FONT
                ws["A1"].alignment = CENTER
                ws["A1"].fill      = _Fill(fill_type="solid", fgColor="0F1117")
                ws.row_dimensions[1].height = 24

                overview_hdrs = [
                    "Name","Sport","Age","Experience (yrs)","Weight (kg)","Height (cm)",
                    "VO₂ Max","Resting HR","Flexibility","Strength","Body Fat %",
                    "Sessions","Recovery Entries","Injuries","Risk Level","Risk Score","Saved At"
                ]
                for ci, h in enumerate(overview_hdrs, 1):
                    c = ws.cell(row=2, column=ci, value=h)
                    _style_hdr(c)
                    ws.column_dimensions[c.column_letter].width = max(12, len(h) + 2)

                for ri, d in enumerate(athletes_data, 3):
                    p   = d.get("profile", {})
                    fi  = d.get("fitness", {})
                    tr  = d.get("training_sessions", [])
                    rc  = d.get("recovery_data", [])
                    inj = d.get("injury_history", [])
                    from predictions import run_predictions as _rp3
                    _pr3 = _rp3(p, fi, tr, rc, inj)
                    row_vals = [
                        p.get("name",""), p.get("sport",""), p.get("age",""),
                        p.get("experience_years",""), p.get("weight_kg",""), p.get("height_cm",""),
                        fi.get("vo2_max",""), fi.get("resting_heart_rate",""),
                        fi.get("flexibility_score",""), fi.get("strength_index",""),
                        fi.get("body_fat_pct",""),
                        len(tr), len(rc), len(inj),
                        _pr3["risk_level"], _pr3["overall_risk"], d.get("saved_at",""),
                    ]
                    for ci, val in enumerate(row_vals, 1):
                        c = ws.cell(row=ri, column=ci, value=val)
                        _style_cell(c, ri)
                ws.freeze_panes = "A3"

                # ════════════════════════════════════════════════════
                # One sheet per athlete: Training + Recovery + Injuries
                # ════════════════════════════════════════════════════
                for d in athletes_data:
                    p   = d.get("profile", {})
                    name = (p.get("name","") or d.get("id","Athlete"))[:28]  # sheet name max 31 chars
                    # sanitise sheet name
                    safe_name = "".join(c for c in name if c not in r'\/*?:[]-')[:28]

                    ws2 = wb.create_sheet(title=safe_name or "Athlete")
                    ws2.sheet_properties.tabColor = "8B5CF6"

                    # Athlete header block
                    fi  = d.get("fitness", {})
                    tr  = d.get("training_sessions", [])
                    rc  = d.get("recovery_data", [])
                    inj = d.get("injury_history", [])

                    info_rows = [
                        ("Name", p.get("name","")), ("Sport", p.get("sport","")),
                        ("Age", p.get("age","")),   ("Experience", f"{p.get('experience_years','')} yrs"),
                        ("Weight", f"{p.get('weight_kg','')} kg"), ("Height", f"{p.get('height_cm','')} cm"),
                        ("VO₂ Max", f"{fi.get('vo2_max','')} ml/kg/min"),
                        ("Resting HR", f"{fi.get('resting_heart_rate','')} bpm"),
                        ("Flexibility", f"{fi.get('flexibility_score','')}/10"),
                        ("Strength", f"{fi.get('strength_index','')}/10"),
                        ("Body Fat", f"{fi.get('body_fat_pct','')} %"),
                        ("Saved At", d.get("saved_at","")),
                    ]
                    for ri2, (k, v) in enumerate(info_rows, 1):
                        ws2.cell(ri2, 1, k).font   = _Font(bold=True, color="9CA3AF", size=9)
                        ws2.cell(ri2, 2, v).font   = _Font(color="E5E7EB", size=9)
                    ws2.column_dimensions["A"].width = 18
                    ws2.column_dimensions["B"].width = 22

                    cur_row = len(info_rows) + 2

                    # Training sessions sub-table
                    ws2.cell(cur_row, 1, "── Training Sessions ──").font = _Font(bold=True, color="3B82D4", size=10)
                    cur_row += 1
                    t_hdrs = ["Date","Duration (min)","Intensity","Distance (km)",
                              "Avg HR (bpm)","Max Speed (km/h)","Reps","Perf Score","Notes"]
                    for ci, h in enumerate(t_hdrs, 1):
                        _style_hdr(ws2.cell(cur_row, ci, h))
                        ws2.column_dimensions[ws2.cell(cur_row, ci).column_letter].width = max(10, len(h)+2)
                    cur_row += 1
                    for ri2, s in enumerate(tr):
                        vals = [s.get("date",""),s.get("duration_min",""),s.get("intensity",""),
                                s.get("running_distance_km",""),s.get("avg_heart_rate",""),
                                s.get("max_speed_kmh",""),s.get("repetitions",""),
                                s.get("performance_score",""),s.get("Notes","")]
                        for ci, v in enumerate(vals, 1):
                            _style_cell(ws2.cell(cur_row, ci, v), ri2)
                        cur_row += 1

                    cur_row += 1  # blank row

                    # Recovery data sub-table
                    ws2.cell(cur_row, 1, "── Recovery Data ──").font = _Font(bold=True, color="8B5CF6", size=10)
                    cur_row += 1
                    r_hdrs = ["Date","Sleep (hrs)","Sleep Quality","HRV (ms)",
                              "Soreness","Stress","Hydration","Method","Notes"]
                    for ci, h in enumerate(r_hdrs, 1):
                        _style_hdr(ws2.cell(cur_row, ci, h))
                    cur_row += 1
                    for ri2, r in enumerate(rc):
                        vals = [r.get("date",""),r.get("sleep_hours",""),r.get("sleep_quality",""),
                                r.get("hrv",""),r.get("muscle_soreness",""),r.get("stress_level",""),
                                r.get("hydration_level",""),r.get("recovery_method",""),r.get("Notes","")]
                        for ci, v in enumerate(vals, 1):
                            _style_cell(ws2.cell(cur_row, ci, v), ri2)
                        cur_row += 1

                    cur_row += 1

                    # Injury history sub-table
                    ws2.cell(cur_row, 1, "── Injury History ──").font = _Font(bold=True, color="EF4444", size=10)
                    cur_row += 1
                    inj_hdrs = ["Injury Type","Date","Severity","Recovery Days"]
                    for ci, h in enumerate(inj_hdrs, 1):
                        _style_hdr(ws2.cell(cur_row, ci, h))
                    cur_row += 1
                    for ri2, inj_rec in enumerate(inj):
                        vals = [inj_rec.get("Injury Type",""),inj_rec.get("Date",""),
                                inj_rec.get("Severity",""),inj_rec.get("Recovery Days","")]
                        for ci, v in enumerate(vals, 1):
                            _style_cell(ws2.cell(cur_row, ci, v), ri2)
                        cur_row += 1

                # Save to bytes buffer
                buf = _io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                return buf.getvalue()

            xlsx_bytes = _build_excel(all_data)
            st.download_button(
                label="⬇️ Download All Athletes (Excel)",
                data=xlsx_bytes,
                file_name="all_athletes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
