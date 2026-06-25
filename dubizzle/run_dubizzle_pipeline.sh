#!/bin/bash
# Full pipeline: run stage 1 (dubizzle.py) until 500 listings are collected,
# then launch the detail scraper loop.
cd "$(dirname "$0")"
TARGET=500
LOG=output/dubizzle_pipeline.log

echo "PIPELINE: starting stage 1" | tee -a "$LOG"
echo "" | python3 -u dubizzle.py >> output/dubizzle.log 2>&1

while true; do
  count=$(python3 -c "import json,os;d=json.load(open('output/dubizzle_listings.json')) if os.path.exists('output/dubizzle_listings.json') else {};print(d.get('count',0))" 2>/dev/null || echo 0)
  echo "PIPELINE: stage 1 count=$count" | tee -a "$LOG"
  if [ "$count" -ge "$TARGET" ]; then
    echo "PIPELINE: stage 1 done. Starting stage 2." | tee -a "$LOG"
    break
  fi
  echo "PIPELINE: stage 1 incomplete, restarting..." | tee -a "$LOG"
  pkill -9 -f "Chrome for Testing" 2>/dev/null
  sleep 3
  echo "" | python3 -u dubizzle.py >> output/dubizzle.log 2>&1
done

bash run_dubizzle_details.sh >> output/dubizzle_details.log 2>&1
echo "PIPELINE: all done." | tee -a "$LOG"
