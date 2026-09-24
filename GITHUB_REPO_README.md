# Bellabeat Fitness Analytics Dashboard

Interactive Streamlit dashboard analyzing Fitbit fitness-tracker data (33 users, Apr–May 2016) for the Bellabeat case study.

## Live app
Deployed on Streamlit Community Cloud from this repo (`app.py` as the entry point).

## Files
- `app.py` — the Streamlit dashboard (4 tabs: Overview, By User, Sleep & Weight, Run SQL)
- `fitness.db` — pre-built SQLite database (`daily_activity`, `user_summary`, `sleep_log`, `weight_log` tables)
- `requirements.txt` — Python dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data source
FitBit Fitness Tracker Data (public domain, CC0), Kaggle — 33 users, April 12 – May 12, 2016.
