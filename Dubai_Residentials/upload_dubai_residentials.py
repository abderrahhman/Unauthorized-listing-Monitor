import os
"""
Uploads listings_full.json to Supabase Dubai_Residentials_full table.
"""
import json
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY", "")
INPUT_FILE = "output/listings_full.json"
TABLE = "dubai_residentials_full"
BATCH_SIZE = 50

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def transform(r):
    coords = r.get("coordinates") or {}
    return {
        "url":              r.get("url"),
        "community":        r.get("community"),
        "community_slug":   r.get("community_slug"),
        "bedroom_type":     r.get("bedroom_type"),
        "property_id":      r.get("property_id"),
        "unit_id":          r.get("unit_id"),
        "apartment_type":   r.get("apartment_type"),
        "rental_type":      r.get("rental_type"),
        "location":         r.get("location"),
        "price_aed":        r.get("price_aed"),
        "beds":             r.get("beds"),
        "baths":            r.get("baths"),
        "size_sqft":        r.get("size_sqft"),
        "lat":              coords.get("lat"),
        "lng":              coords.get("lng"),
        "availability_date":r.get("availability_date"),
        "description":      r.get("description"),
        # JSONB columns
        "categories":       r.get("categories"),
        "key_features":     r.get("key_features"),
        "special_offers":   r.get("special_offers"),
        "amenities":        r.get("amenities"),
        "photos":           r.get("photos"),
    }


def upload_batch(rows, batch_num, total):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{TABLE}",
        headers=HEADERS,
        json=rows,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print(f"  Batch {batch_num}/{total}: OK ({len(rows)} rows)", flush=True)
        return True
    print(f"  Batch {batch_num}/{total}: ERROR {resp.status_code} — {resp.text[:200]}", flush=True)
    return False


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"Loaded {len(raw)} listings from {INPUT_FILE}", flush=True)
    rows = [transform(r) for r in raw]

    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    print(f"Uploading in {len(batches)} batches...\n", flush=True)

    success = 0
    for i, batch in enumerate(batches, 1):
        if upload_batch(batch, i, len(batches)):
            success += len(batch)
        time.sleep(0.3)

    print(f"\nDone: {success}/{len(rows)} rows uploaded to {TABLE}", flush=True)


if __name__ == "__main__":
    main()
