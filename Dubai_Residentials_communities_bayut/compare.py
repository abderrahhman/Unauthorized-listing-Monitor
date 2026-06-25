"""
Compares each unit in dubai_residentials_full against bayut_community_rentals.

Scoring (max 100):
  - Beds exact match:  40 pts
  - Baths exact match: 20 pts
  - Size within ±20%:  up to 20 pts (linear, 20=exact, 0=at boundary)
  - Price within ±20%: up to 20 pts (linear, 20=exact, 0=at boundary)

Only listings with matching beds are returned (score >= 40).
Output: output/comparison_results.json
"""
import json
import os
import time
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wqaqbqsmyldzqjgdojsg.supabase.co")
KEY = os.getenv("SUPABASE_KEY", "")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# Community name mapping: dubai_residentials_full → bayut_community_rentals
COMMUNITY_MAP = {
    "Al Khail Gate":          "Al Khail Gate",
    "Bluewaters":             "Bluewaters Residences",
    "Citywalk":               "City Walk Residences",
    "Discovery Gardens":      "Discovery Gardens",
    "Dubai Wharf":            "Dubai Wharf",
    "Gardens Apartments":     "Garden Apartments",
    "International City":     "International City",
    "Manazel Al Khor":        "Manazel Al Khor",
    "Meydan Residence 1":     "Meydan Residence",
    "The Gardens":            "The Gardens",
}


def fetch_all(table, select="*"):
    rows = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select={select}&limit=1000&offset={offset}",
            headers=H, timeout=30
        )
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break
    return rows


def scaled_score(val_a, val_b, max_pts=20, tolerance=0.20):
    """Linear score: max_pts at exact match, 0 at tolerance boundary, 0 beyond."""
    if not val_a or not val_b or val_a <= 0 or val_b <= 0:
        return 0
    diff_pct = abs(val_a - val_b) / val_a
    if diff_pct > tolerance:
        return 0
    return round(max_pts * (1 - diff_pct / tolerance), 1)


def score_pair(dr, bayut):
    breakdown = {"beds": 0, "baths": 0, "size": 0, "price": 0}

    dr_beds  = dr.get("beds")
    dr_baths = dr.get("baths")
    dr_sqft  = dr.get("size_sqft")
    dr_price = dr.get("price_aed")

    b_beds  = bayut.get("beds")
    b_baths = bayut.get("baths")
    b_sqft  = bayut.get("area_sqft")
    b_price = (bayut.get("price") or {}).get("amount")

    if dr_beds is None or b_beds is None or dr_beds != b_beds:
        return 0, breakdown
    breakdown["beds"] = 40

    if dr_baths is not None and b_baths is not None and dr_baths == b_baths:
        breakdown["baths"] = 20

    breakdown["size"]  = scaled_score(dr_sqft, b_sqft)
    breakdown["price"] = scaled_score(dr_price, b_price)

    total = sum(breakdown.values())
    return round(total, 1), breakdown


def main():
    print("Fetching dubai_residentials_full...", flush=True)
    dr_rows = fetch_all("dubai_residentials_full")
    print(f"  {len(dr_rows)} rows", flush=True)

    print("Fetching bayut_community_rentals...", flush=True)
    bayut_rows = fetch_all("bayut_community_rentals")
    print(f"  {len(bayut_rows)} rows", flush=True)

    # Group bayut by community for fast lookup
    bayut_by_community = {}
    for b in bayut_rows:
        c = b.get("community")
        bayut_by_community.setdefault(c, []).append(b)

    results = []
    skipped_no_map = 0
    skipped_no_bayut = 0

    for dr in dr_rows:
        dr_community = dr.get("community")
        bayut_community = COMMUNITY_MAP.get(dr_community)

        if not bayut_community:
            skipped_no_map += 1
            continue

        candidates = bayut_by_community.get(bayut_community, [])
        if not candidates:
            skipped_no_bayut += 1
            continue

        matches = []
        for b in candidates:
            score, breakdown = score_pair(dr, b)
            if score < 40:  # beds must match
                continue
            matches.append({
                "score": score,
                "score_breakdown": breakdown,
                "bayut_url":   b.get("url"),
                "bayut_title": b.get("title"),
                "bayut_beds":  b.get("beds"),
                "bayut_baths": b.get("baths"),
                "bayut_sqft":  b.get("area_sqft"),
                "bayut_price": (b.get("price") or {}).get("amount"),
                "bayut_location": b.get("location"),
                "bayut_furnishing": b.get("furnishing"),
                "bayut_reference": b.get("reference_number"),
            })

        matches.sort(key=lambda x: x["score"], reverse=True)

        results.append({
            "dr_unit": {
                "property_id":  dr.get("property_id"),
                "unit_id":      dr.get("unit_id"),
                "community":    dr_community,
                "apartment_type": dr.get("apartment_type"),
                "beds":         dr.get("beds"),
                "baths":        dr.get("baths"),
                "size_sqft":    dr.get("size_sqft"),
                "price_aed":    dr.get("price_aed"),
                "url":          dr.get("url"),
                "location":     dr.get("location"),
            },
            "match_count": len(matches),
            "matches": matches,
        })

    os.makedirs("output", exist_ok=True)
    with open("output/comparison_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total_matches = sum(r["match_count"] for r in results)
    print(f"\nDone.")
    print(f"  DR units processed:  {len(results)}")
    print(f"  Skipped (no map):    {skipped_no_map}")
    print(f"  Skipped (no bayut):  {skipped_no_bayut}")
    print(f"  Total bayut matches: {total_matches}")
    print(f"  Output: output/comparison_results.json")


if __name__ == "__main__":
    main()
