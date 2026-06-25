import os
"""
Uploads listings_full.json to Supabase bayut_dubai_rentals table.
"""
import json
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY", "")
INPUT_FILE = "output/listings_full.json"
TABLE = "bayut_dubai_rentals"
BATCH_SIZE = 50

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def transform(r):
    return {
        "url":                   r.get("url"),
        "reference_number":      r.get("reference_number"),
        "external_id":           r.get("external_id"),
        "title":                 r.get("title"),
        "price":                 r.get("price"),
        "purpose":               r.get("purpose"),
        "type":                  r.get("type"),
        "beds":                  r.get("beds"),
        "baths":                 r.get("baths"),
        "is_studio":             r.get("is_studio"),
        "area_sqm":              r.get("area_sqm"),
        "area_sqft":             r.get("area_sqft"),
        "furnishing":            r.get("furnishing"),
        "completion_status":     r.get("completion_status"),
        "description":           r.get("description"),
        "location":              r.get("location"),
        "location_hierarchy":    r.get("location_hierarchy"),
        "coordinates":           r.get("coordinates"),
        "added_on":              r.get("added_on"),
        "updated_on":            r.get("updated_on"),
        "trucheck_on":           r.get("trucheck_on"),
        "handover_date":         r.get("handover_date"),
        "is_verified":           r.get("is_verified"),
        "verification_status":   r.get("verification_status"),
        "permit_number":         r.get("permit_number"),
        "dld_property_sk":       r.get("dld_property_sk"),
        "contact_methods":       r.get("contact_methods"),
        "amenities":             r.get("amenities"),
        "validated_information": r.get("validated_information"),
        "building_information":  r.get("building_information"),
        "project_information":   r.get("project_information"),
        "regulatory_information":r.get("regulatory_information"),
        "similar_transactions":  r.get("similar_transactions"),
        "project":               r.get("project"),
        "agency":                r.get("agency"),
        "agent":                 r.get("agent"),
        "payment_plan_summary":  r.get("payment_plan_summary"),
        "payment_plan_detailed": r.get("payment_plan_detailed"),
        "cover_photo":           r.get("cover_photo"),
        "photo_count":           r.get("photo_count"),
        "photos":                r.get("photos"),
        "video_count":           r.get("video_count"),
        "videos":                r.get("videos"),
        "panorama_count":        r.get("panorama_count"),
        "panoramas":             r.get("panoramas"),
        "floor_plans":           r.get("floor_plans"),
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
    print(f"Uploading {len(rows)} rows in {len(batches)} batches...\n", flush=True)

    success = 0
    for i, batch in enumerate(batches, 1):
        if upload_batch(batch, i, len(batches)):
            success += len(batch)
        time.sleep(0.3)

    print(f"\nDone: {success}/{len(rows)} rows uploaded to {TABLE}", flush=True)


if __name__ == "__main__":
    main()
