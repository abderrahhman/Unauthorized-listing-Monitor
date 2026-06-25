#!/bin/bash
# Run scraper for one community with restart loop.
# Usage: bash run_community.sh <community_name> <base_url>
#
# Example:
#   bash run_community.sh bluewaters_residences \
#       https://www.bayut.com/to-rent/property/dubai/bluewaters-island/bluewaters-residences/

cd "$(dirname "$0")"
source ../venv/bin/activate
ulimit -u unlimited 2>/dev/null || ulimit -u 65536

COMMUNITY=$1
BASE_URL=$2

if [ -z "$COMMUNITY" ] || [ -z "$BASE_URL" ]; then
    echo "Usage: bash run_community.sh <community_name> <base_url>"
    exit 1
fi

TOTAL_FILE="output/${COMMUNITY}/listings_urls.json"
FULL_FILE="output/${COMMUNITY}/listings_full.json"
LOG="output/${COMMUNITY}/run.log"

mkdir -p "output/${COMMUNITY}"

echo "=== $(date) Starting: $COMMUNITY ===" | tee -a "$LOG"

for i in $(seq 1 40); do
    total=$(python3 -c "import json,os; f='$TOTAL_FILE'; print(json.load(open(f))['count']) if os.path.exists(f) else print(0)" 2>/dev/null || echo 0)
    count=$(python3 -c "import json,os; f='$FULL_FILE'; print(len(json.load(open(f)))) if os.path.exists(f) else print(0)" 2>/dev/null || echo 0)

    if [ "$total" -gt 0 ] && [ "$count" -ge "$total" ]; then
        echo "RUN_LOOP: $COMMUNITY complete — $count/$total" | tee -a "$LOG"
        break
    fi

    echo "RUN_LOOP attempt $i: $count/$total" | tee -a "$LOG"
    pkill -9 -f "Chrome for Testing" 2>/dev/null
    sleep 2
    python3 -u scrape_community.py "$COMMUNITY" "$BASE_URL" >> "$LOG" 2>&1
done

echo "=== $(date) Done: $COMMUNITY ===" | tee -a "$LOG"
