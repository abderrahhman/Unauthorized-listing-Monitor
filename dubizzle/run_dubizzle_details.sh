#!/bin/bash
# Restart loop for dubizzle detail scraper until all 500 listings are collected.
# Uses proxy-rotation mode if proxies_working.txt exists (fast, no cooldowns).
# Falls back to cooldown mode if no proxy file found.
cd "$(dirname "$0")"
ulimit -u unlimited 2>/dev/null || ulimit -u 65536
TARGET=500
for i in $(seq 1 60); do
  count=$(python3 -c "import json,os;print(len(json.load(open('output/dubizzle_listings_full.json'))) if os.path.exists('output/dubizzle_listings_full.json') else 0)" 2>/dev/null || echo 0)
  if [ "$count" -ge "$TARGET" ]; then
    echo "RUN_LOOP: reached $count, done."
    break
  fi
  echo "RUN_LOOP: attempt $i, current count=$count"
  pkill -9 -f "Chrome for Testing" 2>/dev/null
  sleep 5
  python3 -u dubizzle_detail_scrape.py >> output/dubizzle_details.log 2>&1
done
