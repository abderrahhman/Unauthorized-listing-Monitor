#!/bin/bash
cd "$(dirname "$0")"
source ../venv/bin/activate
ulimit -u unlimited 2>/dev/null || ulimit -u 65536
TARGET=118
for i in $(seq 1 30); do
  count=$(python3 -c "import json,os; f='output/listings_full.json'; print(len(json.load(open(f)))) if os.path.exists(f) else print(0)" 2>/dev/null || echo 0)
  if [ "$count" -ge "$TARGET" ]; then
    echo "RUN_LOOP: reached $count — done."
    break
  fi
  echo "RUN_LOOP: attempt $i, count=$count"
  pkill -9 -f "Chrome for Testing" 2>/dev/null
  sleep 3
  python3 -u dubai_residentials_detail.py >> output/details.log 2>&1
done
