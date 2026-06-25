"""
Scrapes all rental listings for a specific Bayut community.

Usage:
    python3 scrape_community.py <community_name> <base_url>

Example:
    python3 scrape_community.py bluewaters_residences \
        https://www.bayut.com/to-rent/property/dubai/bluewaters-island/bluewaters-residences/

Stage 1: Collects all listing URLs from paginated search results.
Stage 2: Scrapes full details from each listing URL (window.state).
Output:  output/<community_name>/listings_urls.json
         output/<community_name>/listings_full.json
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

from botasaurus.browser import browser, Driver

EXTRACT_LINKS_JS = """
return Array.from(document.querySelectorAll('article')).map(card => {
    const priceEl = card.querySelector('span[aria-label="Price"]');
    if (!priceEl) return null;
    const linkEl  = card.querySelector('a[aria-label="Listing link"]');
    const titleEl = card.querySelector('h2[aria-label="Title"]');
    const locEl   = card.querySelector('[aria-label="Location"]');
    const curEl   = card.querySelector('span[aria-label="Currency"]');
    const price   = curEl
        ? curEl.textContent.trim() + ' ' + priceEl.textContent.trim()
        : priceEl.textContent.trim();
    return {
        link:     linkEl ? linkEl.href : null,
        title:    titleEl ? titleEl.textContent.trim() : (linkEl ? linkEl.title : null),
        location: locEl   ? locEl.textContent.trim()   : null,
        price
    };
}).filter(x => x && x.link);
"""


# ── Stage 1: URL collection ────────────────────────────────────────────────────

def urls_file(community):
    return f"output/{community}/listings_urls.json"

def full_file(community):
    return f"output/{community}/listings_full.json"

def load_url_progress(community):
    path = urls_file(community)
    if not os.path.exists(path):
        return [], set(), 1
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    listings = data.get("listings", [])
    seen = {l["link"] for l in listings if l.get("link")}
    return listings, seen, data.get("next_page", 1)

def save_url_progress(community, listings, next_page):
    os.makedirs(f"output/{community}", exist_ok=True)
    with open(urls_file(community), "w", encoding="utf-8") as f:
        json.dump({"count": len(listings), "next_page": next_page, "listings": listings},
                  f, ensure_ascii=False, indent=2)


@browser(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_page(driver: Driver, data):
    page_num, url = data["page"], data["url"]
    print(f"[PAGE {page_num}] {url}", flush=True)
    try:
        driver.get(url)
        driver.sleep(6)
    except Exception as e:
        print(f"[PAGE {page_num}] Load failed: {e}", flush=True)
        return []
    try:
        cards = driver.run_js(EXTRACT_LINKS_JS)
        print(f"[PAGE {page_num}] Got {len(cards)} listings", flush=True)
        return cards if isinstance(cards, list) else []
    except Exception as e:
        print(f"[PAGE {page_num}] JS failed: {e}", flush=True)
        return []


def collect_urls(community, base_url):
    all_listings, seen, start_page = load_url_progress(community)
    print(f"\n=== Stage 1: Collecting URLs for '{community}' ===", flush=True)
    print(f"Resuming from page {start_page}, {len(all_listings)} already saved", flush=True)

    consecutive_empty = 0
    page = start_page

    while True:
        # Bayut search pages paginate with /page-N/ suffix
        url = base_url if page == 1 else base_url.rstrip("/") + f"/page-{page}/"
        results = scrape_page({"page": page, "url": url})

        page_cards = []
        for r in results:
            if isinstance(r, list):
                page_cards.extend(r)
            elif isinstance(r, dict):
                page_cards.append(r)

        new_on_page = 0
        for item in page_cards:
            link = item.get("link")
            if link and link not in seen:
                seen.add(link)
                all_listings.append(item)
                new_on_page += 1

        print(f"Page {page}: +{new_on_page} new (total {len(all_listings)})", flush=True)
        save_url_progress(community, all_listings, page + 1)

        if new_on_page == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print("2 empty pages in a row — done collecting.", flush=True)
                break
        else:
            consecutive_empty = 0
        page += 1

    print(f"Collected {len(all_listings)} URLs → {urls_file(community)}", flush=True)
    return all_listings


# ── Stage 2: Detail scraping ───────────────────────────────────────────────────

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
    depth, instr, esc = 0, False, False
    for j in range(s, len(html)):
        ch = html[j]
        if esc: esc = False; continue
        if ch == "\\": esc = True; continue
        if ch == '"': instr = not instr; continue
        if instr: continue
        if ch == "{": depth += 1
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

def regulatory_info(html):
    if "Regulatory Information" not in html:
        return None
    start = html.find("Regulatory Information")
    seg = html[start:start + 6000]
    vals = [strip_tags(v) for v in re.findall(r'class="_677f9d24"[^>]*>(.*?)</span>', seg, re.DOTALL)]
    keys = ["permit_number", "zone_name", "registered_agency", "rera", "brn"]
    return {k: (vals[i] if i < len(vals) else None) for i, k in enumerate(keys)}

def similar_transactions(html):
    j = html.find("Similar Property Transactions")
    if j < 0:
        return None
    seg = html[j:j + 4000]
    rows = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.DOTALL):
        cells = [strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL) if strip_tags(c)]
        if len(cells) >= 3:
            rows.append({"date": cells[0], "area_sqft": cells[1], "price": cells[2]})
    return rows or None

def parse_listing(html, url):
    state = extract_window_state(html) or {}
    p = (state.get("property") or {}).get("data") or {}
    cat = p.get("category") or []
    prop_type = cat[-1]["name"] if cat and isinstance(cat[-1], dict) else None
    area_sqm = p.get("area")
    area_sqft = round(area_sqm * 10.7639, 0) if area_sqm else None
    photos = [f"https://images.bayut.com/thumbnails/{ph['id']}-800x600.webp"
              for ph in p.get("photos", []) if ph.get("id")]
    agency = p.get("agency") or {}
    rera_license = next((l.get("number") for l in agency.get("licenses", [])
                         if l.get("authority") == "RERA"), None)
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
        "amenities": [a["text"] for grp in p.get("amenities", [])
                      for a in grp.get("amenities", [])],
        "validated_information": section_pairs(html, "Validated Information"),
        "building_information": section_pairs(html, "Building Information"),
        "project_information": section_pairs(html, "Project Information"),
        "regulatory_information": regulatory_info(html),
        "similar_transactions": similar_transactions(html),
        "project": {"name": proj.get("title"), "external_id": proj.get("externalID"),
                    "status": proj.get("state"), "completion_status": proj.get("completionStatus"),
                    "handover_date": ts_to_date((proj.get("completionDetails") or {}).get("completionDate"))},
        "agency": {"name": agency.get("name"), "rera_license": rera_license,
                   "location": agency.get("location"), "is_verified": agency.get("isVerified")},
        "agent": {"name": p.get("contactName"), "phone": p.get("primaryPhoneNumber"),
                  "mobile": p.get("mobilePhoneNumber"),
                  "whatsapp": (p.get("phoneNumber") or {}).get("whatsapp")},
        "payment_plan_summary": p.get("paymentPlanSummaries"),
        "payment_plan_detailed": p.get("paymentPlans"),
        "cover_photo": (f"https://images.bayut.com/thumbnails/{p['coverPhotoID']}-800x600.webp"
                        if p.get("coverPhotoID") else None),
        "photo_count": p.get("photoCount"),
        "photos": photos,
        "video_count": p.get("videoCount"),
        "videos": p.get("videos"),
        "panorama_count": p.get("panoramaCount"),
        "panoramas": p.get("panoramas"),
        "floor_plans": p.get("floorPlans"),
    }

def load_done(community):
    path = full_file(community)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    return {it["url"]: it for it in items}

def save_done(community, done):
    os.makedirs(f"output/{community}", exist_ok=True)
    with open(full_file(community), "w", encoding="utf-8") as f:
        json.dump(list(done.values()), f, ensure_ascii=False, indent=2)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@browser(parallel=1, add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_detail(driver: Driver, listing):
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
                raise RuntimeError("empty page")
            print(f"OK: {parsed.get('title', '')[:60]}", flush=True)
            return parsed
        except Exception as e:
            print(f"attempt {attempt} failed ({url[-50:]}): {type(e).__name__}", flush=True)
            driver.sleep(3)
    return None


def scrape_details(community):
    with open(urls_file(community), encoding="utf-8") as f:
        listings = json.load(f)["listings"]
    total = len(listings)
    done = load_done(community)
    print(f"\n=== Stage 2: Scraping details for '{community}' ===", flush=True)
    print(f"Already done: {len(done)}/{total}", flush=True)

    pending = [l for l in listings if l["link"] not in done]
    if not pending:
        print("All done!", flush=True)
        return

    consecutive_empty = 0
    for batch in chunks(pending, 8):
        results = scrape_detail(batch)
        gained = 0
        for r in results:
            if r:
                done[r["url"]] = r
                gained += 1
        save_done(community, done)
        print(f"Progress: {len(done)}/{total} (+{gained})", flush=True)
        if gained == 0:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print("3 empty batches — aborting for restart.", flush=True)
                break
        else:
            consecutive_empty = 0

    print(f"DONE: {len(done)}/{total} saved to {full_file(community)}", flush=True)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scrape_community.py <community_name> <base_url>")
        sys.exit(1)

    community_name = sys.argv[1]
    base_url = sys.argv[2]

    os.makedirs(f"output/{community_name}", exist_ok=True)
    collect_urls(community_name, base_url)
    scrape_details(community_name)
