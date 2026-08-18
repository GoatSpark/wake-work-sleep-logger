"""
Export logged events to docs/data.json for the GitHub Pages dashboard.

Run periodically (see scripts/export_and_push.sh + the systemd timer) - this
script only writes the JSON file, it does not touch git. Format is one row
per day with each category's earliest HH:MM that day (or omitted if no event
was logged for that category that day), plus a wall-clock minutes value the
page uses directly for chart math instead of re-parsing "HH:MM" client-side.
"""

import json
import os

os.environ.setdefault("WWSL_BOT_ALLOW_LIVE_DB", "1")

from config import Config
from database import CATEGORIES, SessionLocal
from stats import build_days_table, time_of_day_minutes

DATA_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data.json")


def build_export() -> dict:
    db = SessionLocal()
    try:
        by_date = build_days_table(db)
    finally:
        db.close()

    days = []
    for day in sorted(by_date.keys()):
        row = {"date": day.isoformat()}
        for category, timestamp in by_date[day].items():
            row[category] = time_of_day_minutes(timestamp)
        days.append(row)

    return {
        "generated_at": Config.now().isoformat(),
        "timezone": str(Config.TIMEZONE),
        "categories": list(CATEGORIES),
        "days": days,
    }


def main():
    export = build_export()
    os.makedirs(os.path.dirname(DATA_JSON_PATH), exist_ok=True)
    with open(DATA_JSON_PATH, "w") as f:
        json.dump(export, f, indent=2)
    print(f"Wrote {len(export['days'])} day(s) to {DATA_JSON_PATH}")


if __name__ == "__main__":
    main()
