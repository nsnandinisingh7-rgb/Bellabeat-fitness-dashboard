"""
Bellabeat / Fitbit Fitness Analytics Dashboard
------------------------------------------------
A Streamlit app that reads from fitness.db (built by clean_and_load.py)
and lets you explore the smart-device usage data with live SQL queries,
KPI cards and charts.

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday",
                  "Friday", "Saturday", "Sunday"]

st.set_page_config(
    page_title="Bellabeat Fitness Analytics",
    page_icon="\U0001F3C3",
    layout="wide",
)


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    daily = pd.read_sql("SELECT * FROM daily_activity", conn)
    users = pd.read_sql("SELECT * FROM user_summary", conn)
    conn.close()
    daily["ActivityDate"] = pd.to_datetime(daily["ActivityDate"])
    daily["Weekday"] = pd.Categorical(daily["Weekday"], categories=WEEKDAY_ORDER, ordered=True)
    return daily, users


@st.cache_data
def run_sql(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()


if not os.path.exists(DB_PATH):
    st.error(
        "fitness.db not found. Run `python clean_and_load.py --raw_dir <folder with csvs> "
        "--out fitness.db` first, in the same folder as this app."
    )
    st.stop()

daily, users = load_data()

# ---------------------------------------------------------------- Sidebar --
st.sidebar.title("Filters")
all_ids = sorted(daily["Id"].unique().tolist())
selected_ids = st.sidebar.multiselect("User ID(s)", all_ids, default=all_ids)
date_min, date_max = daily["ActivityDate"].min(), daily["ActivityDate"].max()
date_range = st.sidebar.date_input(
    "Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max
)

filtered = daily[daily["Id"].isin(selected_ids)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["ActivityDate"] >= start) & (filtered["ActivityDate"] <= end)]

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: Fitbit fitness tracker export, 33 users, Apr\u2013May 2016 "
    "(public Kaggle dataset used in the Bellabeat case study)."
)

# ------------------------------------------------------------------ Title --
st.title("\U0001F3C3 Bellabeat Fitness Analytics Dashboard")
st.caption("Smart-device usage patterns to inform Bellabeat's marketing strategy.")

if filtered.empty:
    st.warning("No data for the current filter selection.")
    st.stop()

# --------------------------------------------------------------- KPI row --
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Avg. Daily Steps", f"{filtered['TotalSteps'].mean():,.0f}")
c2.metric("Avg. Daily Calories", f"{filtered['Calories'].mean():,.0f}")
c3.metric("Avg. Sedentary Hours", f"{filtered['SedentaryMinutes'].mean()/60:.1f} hrs")
c4.metric(
    "% Days \u2265 10,000 Steps",
    f"{100 * filtered['MeetsStepGoal'].mean():.1f}%",
)
if filtered["HasSleepData"].any():
    c5.metric("Avg. Hours Asleep", f"{filtered.loc[filtered['HasSleepData'], 'MinutesAsleep'].mean()/60:.1f} hrs")
else:
    c5.metric("Avg. Hours Asleep", "no data")

st.markdown("---")

tab_overview, tab_users, tab_sleep_weight, tab_sql = st.tabs(
    ["\U0001F4CA Overview", "\U0001F465 By User", "\U0001F634 Sleep & Weight", "\U0001F5C3\uFE0F Run SQL"]
)

# --------------------------------------------------------------- Overview --
with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        wk = (
            filtered.groupby("Weekday", observed=True)["TotalSteps"]
            .mean()
            .reindex(WEEKDAY_ORDER)
            .reset_index()
        )
        fig = px.bar(wk, x="Weekday", y="TotalSteps", title="Average Steps by Weekday")
        fig.add_hline(y=10000, line_dash="dash", line_color="red",
                      annotation_text="10,000-step benchmark")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        wk_c = (
            filtered.groupby("Weekday", observed=True)["Calories"]
            .mean()
            .reindex(WEEKDAY_ORDER)
            .reset_index()
        )
        fig2 = px.bar(wk_c, x="Weekday", y="Calories", title="Average Calories Burned by Weekday",
                       color_discrete_sequence=["#FF7F0E"])
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        activity_cols = ["VeryActiveMinutes", "FairlyActiveMinutes", "LightlyActiveMinutes", "SedentaryMinutes"]
        avg_minutes = filtered[activity_cols].mean().reset_index()
        avg_minutes.columns = ["Activity Type", "Avg Minutes"]
        fig3 = px.pie(avg_minutes, names="Activity Type", values="Avg Minutes",
                       title="Share of the Day by Activity Intensity")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        fig4 = px.scatter(
            filtered, x="TotalSteps", y="Calories", color="Weekday",
            title="Steps vs. Calories Burned", opacity=0.6,
            trendline="ols",
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Activity-Level Segments")
    seg = filtered["ActivityLevel"].value_counts().reindex(
        ["Sedentary (<5k)", "Low Active (5-7.5k)", "Somewhat Active (7.5-10k)",
         "Active (10-12.5k)", "Highly Active (12.5k+)"]
    ).reset_index()
    seg.columns = ["Activity Level", "Days"]
    fig5 = px.bar(seg, x="Activity Level", y="Days", title="Days Logged, by Step-Count Band")
    st.plotly_chart(fig5, use_container_width=True)

# ------------------------------------------------------------------- Users --
with tab_users:
    st.subheader("Per-User Summary")
    u = users[users["Id"].isin(selected_ids)].sort_values("avg_steps", ascending=False)
    st.dataframe(
        u.rename(columns={
            "days_logged": "Days Logged",
            "avg_steps": "Avg Steps",
            "avg_calories": "Avg Calories",
            "avg_sedentary_minutes": "Avg Sedentary (min)",
            "avg_active_minutes": "Avg Active (min)",
            "pct_days_meeting_step_goal": "% Days \u2265 10k Steps",
        }).round(1),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Most Sedentary Users (avg. sedentary minutes/day)")
    top_sed = u.sort_values("avg_sedentary_minutes", ascending=False).head(10)
    fig6 = px.bar(top_sed, x="Id", y="avg_sedentary_minutes",
                   title="Top 10 Most Sedentary Users")
    fig6.update_xaxes(type="category")
    st.plotly_chart(fig6, use_container_width=True)

# ------------------------------------------------------------- Sleep & Weight --
with tab_sleep_weight:
    sleep_rows = filtered[filtered["HasSleepData"]]
    weight_rows = filtered[filtered["HasWeightData"]]

    st.subheader("Sleep")
    if sleep_rows.empty:
        st.info("No sleep data logged for the current filter selection.")
    else:
        n_users_sleep = sleep_rows["Id"].nunique()
        st.caption(
            f"{len(sleep_rows)} nights logged across {n_users_sleep} user(s) "
            f"(sleep tracking is sparse in this dataset - many users never log it)."
        )
        s1, s2, s3 = st.columns(3)
        s1.metric("Avg. Hours Asleep", f"{sleep_rows['MinutesAsleep'].mean()/60:.1f} hrs")
        s2.metric("Avg. Hours in Bed", f"{sleep_rows['MinutesInBed'].mean()/60:.1f} hrs")
        efficiency = 100 * sleep_rows["MinutesAsleep"].sum() / sleep_rows["MinutesInBed"].sum()
        s3.metric("Sleep Efficiency", f"{efficiency:.0f}%", help="Minutes asleep \u00f7 minutes in bed")

        col1, col2 = st.columns(2)
        with col1:
            wk_sleep = (
                sleep_rows.groupby("Weekday", observed=True)["MinutesAsleep"]
                .mean()
                .reindex(WEEKDAY_ORDER)
                .reset_index()
            )
            fig = px.bar(wk_sleep, x="Weekday", y="MinutesAsleep",
                         title="Average Minutes Asleep by Weekday")
            fig.add_hline(y=480, line_dash="dash", line_color="red",
                          annotation_text="8-hour recommendation")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig2 = px.scatter(
                sleep_rows, x="TotalSteps", y="MinutesAsleep", color="Weekday",
                title="Daily Steps vs. Minutes Asleep That Night", opacity=0.6,
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Sleep efficiency by user")
        eff_by_user = (
            sleep_rows.groupby("Id")
            .apply(lambda g: 100 * g["MinutesAsleep"].sum() / g["MinutesInBed"].sum(), include_groups=False)
            .reset_index(name="SleepEfficiencyPct")
            .sort_values("SleepEfficiencyPct")
        )
        fig3 = px.bar(eff_by_user, x="Id", y="SleepEfficiencyPct",
                       title="Sleep Efficiency by User (% of time in bed spent asleep)")
        fig3.update_xaxes(type="category")
        fig3.add_hline(y=85, line_dash="dash", line_color="green",
                       annotation_text="typical healthy benchmark (~85%)")
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("Weight")
    if weight_rows.empty:
        st.info("No weight data logged for the current filter selection.")
    else:
        n_users_weight = weight_rows["Id"].nunique()
        st.caption(
            f"Only {n_users_weight} user(s) in this dataset logged weight at all "
            f"({len(weight_rows)} entries total) - treat this section as directional, not representative."
        )
        w1, w2 = st.columns(2)
        w1.metric("Avg. Weight (logged users)", f"{weight_rows['WeightKg'].mean():.1f} kg")
        manual_pct = 100 * weight_rows["IsManualReport"].astype(bool).mean()
        w2.metric("% Manually Entered", f"{manual_pct:.0f}%")

        fig4 = px.line(
            weight_rows.sort_values("ActivityDate"),
            x="ActivityDate", y="WeightKg", color="Id",
            title="Weight Over Time, by User", markers=True,
        )
        fig4.update_layout(legend_title_text="User ID")
        st.plotly_chart(fig4, use_container_width=True)

# --------------------------------------------------------------------- SQL --
with tab_sql:
    st.subheader("Query the data directly")
    st.caption(
        "Tables available: `daily_activity` (one row per user per day, includes "
        "merged sleep & weight columns), `user_summary` (one row per user), "
        "`sleep_log` (sleep-only, native grain), `weight_log` (weight-only, native grain)."
    )

    presets = {
        "-- write your own --": "",
        "Weekday averages": (
            "SELECT Weekday, ROUND(AVG(TotalSteps),0) AS avg_steps, "
            "ROUND(AVG(Calories),0) AS avg_calories, "
            "ROUND(AVG(SedentaryMinutes),0) AS avg_sedentary_minutes\n"
            "FROM daily_activity GROUP BY Weekday;"
        ),
        "% of days hitting 10k steps": (
            "SELECT ROUND(100.0 * SUM(MeetsStepGoal) / COUNT(*), 1) AS pct_days_hitting_10k\n"
            "FROM daily_activity;"
        ),
        "Most sedentary users": (
            "SELECT Id, ROUND(AVG(SedentaryMinutes),0) AS avg_sedentary_minutes\n"
            "FROM daily_activity GROUP BY Id ORDER BY avg_sedentary_minutes DESC LIMIT 10;"
        ),
        "Weekend vs weekday": (
            "SELECT CASE WHEN Weekday IN ('Saturday','Sunday') THEN 'Weekend' ELSE 'Weekday' END AS day_type,\n"
            "       ROUND(AVG(TotalSteps),0) AS avg_steps, ROUND(AVG(Calories),0) AS avg_calories\n"
            "FROM daily_activity GROUP BY day_type;"
        ),
        "Sleep efficiency by user": (
            "SELECT Id, COUNT(*) AS nights_logged, ROUND(AVG(MinutesAsleep),0) AS avg_minutes_asleep,\n"
            "       ROUND(100.0 * AVG(MinutesAsleep) / AVG(MinutesInBed), 1) AS sleep_efficiency_pct\n"
            "FROM sleep_log GROUP BY Id ORDER BY sleep_efficiency_pct;"
        ),
        "Steps vs. sleep by activity level": (
            "SELECT ActivityLevel, ROUND(AVG(MinutesAsleep),0) AS avg_minutes_asleep, COUNT(*) AS n\n"
            "FROM daily_activity WHERE HasSleepData = 1 GROUP BY ActivityLevel;"
        ),
        "Weight trend per user": (
            "SELECT Id, COUNT(*) AS weigh_ins, MIN(ActivityDate) AS first_weigh_in,\n"
            "       MAX(ActivityDate) AS last_weigh_in, ROUND(MIN(WeightKg),1) AS first_weight_kg,\n"
            "       ROUND(MAX(WeightKg),1) AS last_weight_kg\n"
            "FROM weight_log GROUP BY Id ORDER BY weigh_ins DESC;"
        ),
    }
    choice = st.selectbox("Preset queries", list(presets.keys()))
    query = st.text_area("SQL query", value=presets[choice] or "SELECT * FROM daily_activity LIMIT 20;", height=140)

    if st.button("Run query", type="primary"):
        try:
            result = run_sql(query)
            st.dataframe(result, use_container_width=True)
            st.caption(f"{len(result)} row(s) returned.")
        except Exception as e:
            st.error(f"Query failed: {e}")

st.markdown("---")
with st.expander("\U0001F4CB Key takeaways & recommendations"):
    st.markdown(
        """
- **Most users fall short of the 10,000-step benchmark** on a given day — only
  about a third of logged days hit that mark.
- **Sedentary time dominates the day.** Even active users log well over 15
  hours of sedentary time on many days, and some days show a full 24 hours
  sedentary — a sign the tracker likely wasn't worn.
- **Weekday vs. weekend behavior is similar** in this dataset, unlike many
  fitness-app populations — engagement doesn't clearly spike or dip on
  weekends.
- **Recommendation:** Bellabeat's app could nudge users with mid-day
  movement reminders on low-activity days, and surface a simple
  "time since last activity" signal instead of only end-of-day summaries.
        """
    )
