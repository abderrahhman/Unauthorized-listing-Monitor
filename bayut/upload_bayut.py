import os
"""
Uploads bayut_stage_2.json to Supabase bayut_listings table.
Run on the server: python3 upload_bayut.py
Requires: pip install requests
"""
import json
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY", "")
INPUT_FILE = "output/bayut_stage_2.json"
TABLE = "bayut_listings"
BATCH_SIZE = 50

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


def transform(raw):
    price = raw.get("price") or {}
    return {
        "url":                   raw.get("url"),
        "reference_number":      raw.get("reference_number"),
        "external_id":           raw.get("external_id"),
        "title":                 raw.get("title"),
        "price_amount":          price.get("amount"),
        "price_currency":        price.get("currency"),
        "purpose":               raw.get("purpose"),
        "property_type":         raw.get("type"),
        "beds":                  raw.get("beds"),
        "baths":                 raw.get("baths"),
        "is_studio":             raw.get("is_studio"),
        "area_sqm":              raw.get("area_sqm"),
        "area_sqft":             raw.get("area_sqft"),
        "furnishing":            raw.get("furnishing"),
        "completion_status":     raw.get("completion_status"),
        "description":           raw.get("description"),
        "location":              raw.get("location"),
        "location_hierarchy":    raw.get("location_hierarchy"),
        "lat":                   (raw.get("coordinates") or {}).get("lat"),
        "lng":                   (raw.get("coordinates") or {}).get("lng"),
        "sale_type":             raw.get("sale_type"),
        "added_on":              raw.get("added_on"),
        "updated_on":            raw.get("updated_on"),
        "trucheck_on":           raw.get("trucheck_on"),
        "handover_date":         raw.get("handover_date"),
        "is_verified":           raw.get("is_verified"),
        "verification_status":   raw.get("verification_status"),
        "permit_number":         raw.get("permit_number"),
        "dld_property_sk":       raw.get("dld_property_sk"),
        "cover_photo":           raw.get("cover_photo"),
        "photo_count":           raw.get("photo_count"),
        "video_count":           raw.get("video_count"),
        "panorama_count":        raw.get("panorama_count"),
        # JSONB columns
        "contact_methods":       raw.get("contact_methods"),
        "amenities":             raw.get("amenities"),
        "offplan_details":       raw.get("offplan_details"),
        "validated_information": raw.get("validated_information"),
        "building_information":  raw.get("building_information"),
        "project_information":   raw.get("project_information"),
        "regulatory_information":raw.get("regulatory_information"),
        "similar_transactions":  raw.get("similar_transactions"),
        "project":               raw.get("project"),
        "agency":                raw.get("agency"),
        "agent":                 raw.get("agent"),
        "payment_plan_summary":  raw.get("payment_plan_summary"),
        "payment_plan_detailed": raw.get("payment_plan_detailed"),
        "photos":                raw.get("photos"),
        "videos":                raw.get("videos"),
        "panoramas":             raw.get("panoramas"),
        "floor_plans":           raw.get("floor_plans"),
    }


def upload_batch(rows, batch_num, total_batches):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    resp = requests.post(url, headers=HEADERS, json=rows, timeout=30)
    if resp.status_code in (200, 201):
        print(f"  Batch {batch_num}/{total_batches}: OK ({len(rows)} rows)", flush=True)
        return True
    else:
        print(f"  Batch {batch_num}/{total_batches}: ERROR {resp.status_code} — {resp.text[:200]}", flush=True)
        return False


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        raw_listings = json.load(f)

    print(f"Loaded {len(raw_listings)} listings from {INPUT_FILE}", flush=True)
    rows = [transform(r) for r in raw_listings]

    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    total_batches = len(batches)
    print(f"Uploading in {total_batches} batches of {BATCH_SIZE}...\n", flush=True)

    success = 0
    for i, batch in enumerate(batches, 1):
        ok = upload_batch(batch, i, total_batches)
        if ok:
            success += len(batch)
        time.sleep(0.3)  # be gentle on the API

    print(f"\nDone: {success}/{len(rows)} rows uploaded to {TABLE}", flush=True)


if __name__ == "__main__":
    main()
