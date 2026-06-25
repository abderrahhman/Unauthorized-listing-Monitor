#!/bin/bash
# Sequential community scraper queue.
# Runs one community at a time, waits for completion before starting next.
cd "$(dirname "$0")"
source ../venv/bin/activate
ulimit -u unlimited 2>/dev/null || ulimit -u 65536

run_one() {
    local NAME=$1
    local URL=$2
    local FULL_FILE="output/${NAME}/listings_full.json"
    local URL_FILE="output/${NAME}/listings_urls.json"
    local LOG="output/${NAME}/run.log"

    # Check if already fully done
    if [ -f "$URL_FILE" ] && [ -f "$FULL_FILE" ]; then
        local total=$(python3 -c "import json; print(json.load(open('$URL_FILE'))['count'])" 2>/dev/null || echo 0)
        local done=$(python3 -c "import json; print(len(json.load(open('$FULL_FILE'))))" 2>/dev/null || echo 0)
        if [ "$total" -gt 0 ] && [ "$done" -ge "$total" ]; then
            echo "QUEUE: $NAME already complete ($done/$total) — skipping"
            return
        fi
    fi

    echo "QUEUE: Starting $NAME at $(date)"
    mkdir -p "output/${NAME}"
    xvfb-run -a bash run_community.sh "$NAME" "$URL" 2>&1 | tee -a "$LOG"
    echo "QUEUE: Finished $NAME at $(date)"
    pkill -9 -f "Chrome for Testing" 2>/dev/null
    sleep 5
}

# ── Queue ──────────────────────────────────────────────────────────────────────
# Already running: remraam (wait for it to finish first)
until ! pgrep -f "scrape_community.py remraam" > /dev/null 2>&1; do sleep 30; done
echo "QUEUE: remraam done, starting queue..."

run_one "international_city"      "https://www.bayut.com/to-rent/studio,1,2-bedroom-property/dubai/international-city/"
run_one "the_gardens"             "https://www.bayut.com/to-rent/property/dubai/the-gardens/"
run_one "discovery_gardens"       "https://www.bayut.com/to-rent/property/dubai/discovery-gardens/"
run_one "garden_apartments"       "https://www.bayut.com/to-rent/property/dubai/the-gardens/the-gardens-apartments/"
run_one "city_walk_residences"    "https://www.bayut.com/to-rent/apartments/dubai/al-wasl/city-walk/"
run_one "badrah"                  "https://www.bayut.com/to-rent/townhouses/dubai/dubai-waterfront/badrah/"
run_one "jebel_ali_village_townhouses" "https://www.bayut.com/to-rent/townhouses/dubai/jebel-ali/jebel-ali-village/jebel-ali-village-townhouses/"

# ── Pending (add links as received) ───────────────────────────────────────────
# run_one "ghoroob"             "URL_HERE"
# run_one "ghoroob_square"      "URL_HERE"
# run_one "meydan_heights"      "URL_HERE"
run_one "meydan_residence"    "https://www.bayut.com/to-rent/apartments/dubai/meydan-city/meydan-avenue/residence-1-at-meydan-avenue/"
# run_one "garden_view_apts"    "URL_HERE"
# run_one "bayti_villas"        "URL_HERE"
run_one "nad_al_sheba_villas" "https://www.bayut.com/to-rent/property/dubai/nad-al-sheba/"
# run_one "veneto"              "URL_HERE"
# run_one "garden_view_villas"  "URL_HERE"
# run_one "layan"               "URL_HERE"
# run_one "shorooq"             "URL_HERE"

echo "QUEUE: All done at $(date)"
