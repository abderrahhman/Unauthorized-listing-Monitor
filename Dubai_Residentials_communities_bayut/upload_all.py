"""
Uploads all completed community listings to Supabase bayut_community_rentals table.
Adds a 'community' field to each row identifying the source community.
"""
import json
import os
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY", "")
TABLE = "bayut_community_rentals"
BATCH_SIZE = 50

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# folder_name → display name
COMMUNITIES = {
    "bluewaters_residences": "Bluewaters Residences",
    "al_khail_gate":         "Al Khail Gate",
    "dubai_wharf":           "Dubai Wharf",
    "manazel_al_khor":       "Manazel Al Khor",
    "remraam":               "Remraam",
    "the_gardens":           "The Gardens",
    "international_city":    "International City",
    "discovery_gardens":     "Discovery Gardens",
    "garden_apartments":     "Garden Apartments",
    "city_walk_residences":  "City Walk Residences",
    "badrah":                "Badrah",
    "meydan_residence":      "Meydan Residence",
    "bayti_homes":           "Bayti Homes",
}


def transform(r, community_name):
    return {
        "community":             community_name,
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


def upload_batch(rows, label):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{TABLE}",
        headers=HEADERS,
        json=rows,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        return True
    print(f"  ERROR {resp.status_code}: {resp.text[:200]}", flush=True)
    return False


def upload_community(folder, display_name):
    path = f"output/{folder}/listings_full.json"
    if not os.path.exists(path):
        print(f"  SKIP {display_name} — no file at {path}", flush=True)
        return 0

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    rows = [transform(r, display_name) for r in raw]
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    success = 0
    for batch in batches:
        if upload_batch(batch, display_name):
            success += len(batch)
        time.sleep(0.2)

    print(f"  {display_name}: {success}/{len(rows)} uploaded", flush=True)
    return success


def main():
    total_success = 0
    total_rows = 0

    for folder, display_name in COMMUNITIES.items():
        print(f"\n[{display_name}]", flush=True)
        n = upload_community(folder, display_name)
        total_success += n
        total_rows += n

    print(f"\n=== Done: {total_success} total rows uploaded to {TABLE} ===", flush=True)


if __name__ == "__main__":
    main()
