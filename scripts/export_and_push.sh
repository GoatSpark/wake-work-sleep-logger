#!/usr/bin/env bash
# Regenerate docs/data.json from the live DB and push it to GitHub if it
# changed. Run on a timer (see wake-work-sleep-logger-export.timer) - not
# meant to be run manually except for debugging.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

source venv/bin/activate
python export_stats.py
deactivate

if git diff --quiet -- docs/data.json && git diff --cached --quiet -- docs/data.json; then
    echo "No change to docs/data.json, nothing to push."
    exit 0
fi

git add docs/data.json
git commit -m "Update stats data ($(date '+%Y-%m-%d %H:%M %Z'))"
git push origin HEAD:main
