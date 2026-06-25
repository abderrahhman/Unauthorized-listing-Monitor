"""
Stage 2: Scrape full property details from each listing URL.
Reads output/listings_urls.json, visits each URL, extracts all fields
from window.state (same structure as bayut sell listings).
Auto-resumes: skips already-scraped URLs.
Output: output/listings_full.json
"""
import json
import os
import re
from datetime import datetime, timezone

from botasaurus.browser import browser, Driver

IN_FILE = "output/listings_urls.json"
OUT_FILE = "output/listings_full.json"
BATCH_SIZE = 8


def strip_tags(s):
    if s is None:
        return None
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip() or None


def ts_to_date(ts):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def extract_window_state(html):
    s = html.find("window.state =")
    if s < 0:
        return None
    s = html.find("{", s)
    depth = 0
    instr = False
    esc = False
    for j in range(s, len(html)):
        ch = html[j]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            instr = not instr
            continue
        if instr:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[s:j + 1])
    return None


def _snake(label):
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def section_pairs(html, heading, length=3500):
    i = html.find(">" + heading + "<")
    if i < 0:
        return None
    seg = html[i:i + length]
    ul = re.search(r"<ul[^>]*>(.*?)</ul>", seg, re.DOTALL)
    if not ul:
        return None
    out = {}
    for li in re.findall(r"<li[^>]*>(.*?)</li>", ul.group(1), re.DOTALL):
        lab = re.search(r'class="a39496d5">([^<]+)</span>', li)
        val = re.search(r'aria-label="[^"]*"[^>]*>(.*?)</span>', li, re.DOTALL)
        if lab and val:
            out[_snake(strip_tags(lab.group(1)))] = strip_tags(val.group(1))
    return out or None


def similar_transactions(html):
    j = html.find("Similar Property Transactions")
    if j < 0:
        return None
    seg = html[j:j + 4000]
    rows = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.DOTALL):
        cells = [strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)]
        cells = [c for c in cells if c]
        if len(cells) >= 3:
            rows.append({"date": cells[0], "area_sqft": cells[1], "price": cells[2]})
    return rows or None


def regulatory_info(html):
    if "Regulatory Information" not in html:
        return None
    start = html.find("Regulatory Information")
    seg = html[start:start + 6000]
    vals = re.findall(r'class="_677f9d24"[^>]*>(.*?)</span>', seg, re.DOTALL)
    vals = [strip_tags(v) for v in vals]
    keys = ["permit_number", "zone_name", "registered_agency", "rera", "brn"]
    return {k: (vals[i] if i < len(vals) else None) for i, k in enumerate(keys)}


def parse_listing(html, url):
    state = extract_window_state(html) or {}
    p = (state.get("property") or {}).get("data") or {}

    cat = p.get("category") or []
    prop_type = cat[-1]["name"] if cat and isinstance(cat[-1], dict) else None

    area_sqm = p.get("area")
    area_sqft = round(area_sqm * 10.7639, 0) if area_sqm else None

    photos = [
        f"https://images.bayut.com/thumbnails/{ph['id']}-800x600.webp"
        for ph in p.get("photos", []) if ph.get("id")
    ]

    agency = p.get("agency") or {}
    rera_license = None
    for lic in agency.get("licenses", []):
        if lic.get("authority") == "RERA":
            rera_license = lic.get("number")

    proj = p.get("project") or {}
    comp = p.get("completionDetails") or {}
    verif = p.get("verification") or {}

    return {
        "url": url,
        "reference_number": p.get("referenceNumber"),
        "external_id": p.get("externalID"),
        "title": p.get("title"),
        "price": {"amount": p.get("price"), "currency": "AED"},
        "purpose": p.get("purpose"),
        "type": prop_type,
        "beds": p.get("rooms"),
        "baths": p.get("baths"),
        "is_studio": p.get("isStudio"),
        "area_sqm": round(area_sqm, 2) if area_sqm else None,
        "area_sqft": area_sqft,
        "furnishing": p.get("furnishingStatus"),
        "completion_status": p.get("completionStatus"),
        "description": strip_tags(p.get("description")),
        "location": (p.get("labels") or {}).get("locationHierarchy"),
        "location_hierarchy": (p.get("labels") or {}).get("locationNames"),
        "coordinates": p.get("geography"),
        "added_on": ts_to_date(p.get("createdAt")),
        "updated_on": ts_to_date(p.get("updatedAt")),
        "trucheck_on": ts_to_date(verif.get("trucheckedAt")),
        "handover_date": ts_to_date(comp.get("completionDate")),
        "is_verified": p.get("isVerified"),
        "verification_status": verif.get("status"),
        "permit_number": p.get("permitNumber"),
        "dld_property_sk": (p.get("extraFields") or {}).get("dldPropertySK"),
        "contact_methods": p.get("contactMethodAvailability"),
        "amenities": [
            a["text"]
            for grp in p.get("amenities", [])
            for a in grp.get("amenities", [])
        ],
        "validated_information": section_pairs(html, "Validated Information"),
        "building_information": section_pairs(html, "Building Information"),
        "project_information": section_pairs(html, "Project Information"),
        "regulatory_information": regulatory_info(html),
        "similar_transactions": similar_transactions(html),
        "project": {
            "name": proj.get("title"),
            "external_id": proj.get("externalID"),
            "status": proj.get("state"),
            "completion_status": proj.get("completionStatus"),
            "handover_date": ts_to_date((proj.get("completionDetails") or {}).get("completionDate")),
        },
        "agency": {
            "name": agency.get("name"),
            "rera_license": rera_license,
            "location": agency.get("location"),
            "is_verified": agency.get("isVerified"),
        },
        "agent": {
            "name": p.get("contactName"),
            "phone": p.get("primaryPhoneNumber"),
            "mobile": p.get("mobilePhoneNumber"),
            "whatsapp": (p.get("phoneNumber") or {}).get("whatsapp"),
        },
        "payment_plan_summary": p.get("paymentPlanSummaries"),
        "payment_plan_detailed": p.get("paymentPlans"),
        "cover_photo": (
            f"https://images.bayut.com/thumbnails/{p['coverPhotoID']}-800x600.webp"
            if p.get("coverPhotoID") else None
        ),
        "photo_count": p.get("photoCount"),
        "photos": photos,
        "video_count": p.get("videoCount"),
        "videos": p.get("videos"),
        "panorama_count": p.get("panoramaCount"),
        "panoramas": p.get("panoramas"),
        "floor_plans": p.get("floorPlans"),
    }


def load_done():
    if not os.path.exists(OUT_FILE):
        return {}
    with open(OUT_FILE, encoding="utf-8") as f:
        items = json.load(f)
    return {it["url"]: it for it in items}


def save_all(done):
    os.makedirs("output", exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done.values()), f, ensure_ascii=False, indent=2)


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@browser(parallel=1, add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_one(driver: Driver, listing):
    url = listing["link"]
    for attempt in range(1, 3):
        try:
            driver.get(url)
            driver.sleep(3)
            for frac in (0.3, 0.6, 1.0):
                driver.run_js(f"window.scrollTo(0, document.body.scrollHeight*{frac});")
                driver.sleep(1.5)
            driver.sleep(1)
            parsed = parse_listing(driver.page_html, url)
            if not parsed.get("reference_number") and not parsed.get("title"):
                raise RuntimeError("empty page (window.state missing)")
            print(f"OK: {parsed.get('title', '')[:60]}", flush=True)
            return parsed
        except Exception as e:
            print(f"attempt {attempt} failed ({url[-50:]}): {type(e).__name__}", flush=True)
            driver.sleep(3)
    return None


def main():
    if not os.path.exists(IN_FILE):
        print(f"ERROR: {IN_FILE} not found. Run collect_urls.py first.", flush=True)
        return

    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    listings = data.get("listings", [])
    total = len(listings)
    print(f"Loaded {total} URLs from {IN_FILE}", flush=True)

    done = load_done()
    print(f"Already scraped: {len(done)}/{total}", flush=True)

    pending = [l for l in listings if l["link"] not in done]
    if not pending:
        print(f"All done! {len(done)} listings in {OUT_FILE}", flush=True)
        return

    consecutive_empty = 0

    for batch in chunks(pending, BATCH_SIZE):
        print(f"\nScraping batch of {len(batch)}...", flush=True)
        results = scrape_one(batch)
        gained = 0
        for r in results:
            if r:
                done[r["url"]] = r
                gained += 1
        save_all(done)
        print(f"Progress: {len(done)}/{total} (+{gained} this batch)", flush=True)

        if gained == 0:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print("3 empty batches — aborting for restart.", flush=True)
                break
        else:
            consecutive_empty = 0

    print(f"\nDONE: {len(done)}/{total} listings saved to {OUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
