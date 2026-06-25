#!/bin/bash
# Restart loop for detail scraper only (use after collect_urls.py has run)
cd "$(dirname "$0")"
source ../../venv/bin/activate
ulimit -u unlimited 2>/dev/null || ulimit -u 65536

TOTAL=$(python3 -c "import json,os; f='output/listings_urls.json'; print(json.load(open(f))['count']) if os.path.exists(f) else print(0)" 2>/dev/null || echo 0)
echo "Target: $TOTAL listings"

for i in $(seq 1 40); do
  count=$(python3 -c "import json,os; f='output/listings_full.json'; print(len(json.load(open(f)))) if os.path.exists(f) else print(0)" 2>/dev/null || echo 0)
  if [ "$count" -ge "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    echo "RUN_LOOP: reached $count/$TOTAL — done."
    break
  fi
  echo "RUN_LOOP: attempt $i, count=$count/$TOTAL"
  pkill -9 -f "Chrome for Testing" 2>/dev/null
  sleep 3
  python3 -u detail_scrape.py >> output/details.log 2>&1
done
