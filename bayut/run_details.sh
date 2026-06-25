#!/bin/bash
# Relaunch the detail scraper until all 25 listings are collected. Each run
# resumes from output/listings_full.json and aborts cleanly if Chrome dies;
# this loop restarts it with a fresh browser.
cd "$(dirname "$0")"
ulimit -u unlimited 2>/dev/null || ulimit -u 65536
TARGET=500
for i in $(seq 1 40); do
  count=$(python -c "import json,os;print(len(json.load(open('output/listings_full.json'))) if os.path.exists('output/listings_full.json') else 0)" 2>/dev/null || echo 0)
  if [ "$count" -ge "$TARGET" ]; then
    echo "RUN_LOOP: reached $count, done."
    break
  fi
  echo "RUN_LOOP: attempt $i, current count=$count"
  pkill -9 -f "Chrome for Testing" 2>/dev/null
  sleep 2
  echo "" | python -u detail_scrape.py >> details.log 2>&1
done
