"""
Stage 2: Scrape full property details from each listing URL.
Reads output/listings.json, visits each URL, extracts all available fields.
Auto-resumes: skips already-scraped URLs.
Output: output/listings_full.json
"""
import json
import os
import re

from botasaurus.browser import browser, Driver

BASE_URL = "https://dubairesidential.ae"
IN_FILE = "output/listings.json"
OUT_FILE = "output/listings_full.json"
BATCH_SIZE = 10


# ── Parsers ────────────────────────────────────────────────────────────────────

def attr(html, name):
    m = re.search(rf'data-{re.escape(name)}="([^"]+)"', html)
    return m.group(1) if m else None


def clean(text):
    if not text:
        return None
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def parse_price(html):
    v = attr(html, "desiredrent")
    return int(v) if v and v.isdigit() else None


def parse_beds(html):
    v = attr(html, "bed-room")
    return int(v) if v and v.isdigit() else None


def parse_feature_number(html, icon_class):
    """Extract number from property-detail__features after a given icon class."""
    m = re.search(
        rf'{re.escape(icon_class)}[^<]*</span><span[^>]*property-detail__features__number[^>]*>([\d, Sqft]+)</span>',
        html, re.DOTALL
    )
    return clean(m.group(1)) if m else None


def parse_sqft(html):
    v = parse_feature_number(html, "icon-acreage")
    if not v:
        m = re.search(r'<span[^>]*property-detail__features__number[^>]*>([\d,]+ Sqft)</span>', html)
        v = m.group(1) if m else None
    if v:
        digits = re.sub(r'[^\d]', '', v)
        return int(digits) if digits else None
    return None


def parse_baths(html):
    v = parse_feature_number(html, "icon-shower")
    if v and re.match(r'^\d+$', v.strip()):
        return int(v.strip())
    # fallback
    m = re.search(r'icon-shower[^<]*</span><span[^>]*>([\d]+)</span>', html)
    return int(m.group(1)) if m else None


def parse_type(html):
    return attr(html, "rental-type")


def parse_apartment_type(html):
    return attr(html, "apartment-type")


def parse_community(html):
    return attr(html, "community-name") or attr(html, "community")


def parse_location(html):
    """Extracts 'Al Khail Gate | Al Quoz | Dubai' from the category list."""
    cats = re.findall(r'class="property-detail__category">([^<]+)</li>', html)
    loc = [c.strip() for c in cats if "|" in c]
    return loc[0] if loc else None


def parse_categories(html):
    cats = re.findall(r'class="property-detail__category">([^<]+)</li>', html)
    return [c.strip() for c in cats] if cats else None


def parse_lat_lng(html):
    lat = attr(html, "lat")
    lng = attr(html, "long")
    if lat and lng:
        try:
            return {"lat": float(lat), "lng": float(lng)}
        except ValueError:
            pass
    return None


def parse_availability(html):
    return attr(html, "availability-start-date") or attr(html, "website-date")


def parse_property_id(html):
    return attr(html, "property-id")


def parse_unique_id(html):
    return attr(html, "unique-id")


def parse_description(html):
    m = re.search(r'class="property-detail__desc"[^>]*>(.*?)</div>', html, re.DOTALL)
    return clean(m.group(1)) if m else None


def parse_key_features(html):
    start = html.find('property-detail__key-features')
    if start < 0:
        return None
    seg = html[start:start + 3000]
    items = re.findall(r'class="features__item__text">([^<]+)</span>', seg)
    return [clean(i) for i in items if clean(i)] or None


def parse_special_offers(html):
    start = html.find('offers__')
    if start < 0:
        return None
    seg = html[start:start + 2000]
    items = re.findall(r'class="features__item__text">([^<]+)</span>', seg)
    cleaned = [clean(i) for i in items if clean(i)]
    # skip the T&Cs line
    return [o for o in cleaned if not o.startswith("*T")] or None


def parse_amenities(html):
    """Community amenities from facilities__name spans."""
    items = re.findall(r'class="facilities__name">([^<]+)</span>', html)
    return list(dict.fromkeys(clean(i) for i in items if clean(i))) or None


def parse_photos(html):
    imgs = re.findall(r'src="([^"]*/-/media/dpam/rented-properties/[^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I)
    full = [BASE_URL + i if i.startswith("/") else i for i in imgs]
    return list(dict.fromkeys(full)) or None


def parse_listing(html, listing_meta):
    return {
        "url":              listing_meta.get("url"),
        "community":        parse_community(html) or listing_meta.get("community"),
        "community_slug":   listing_meta.get("community_slug"),
        "bedroom_type":     listing_meta.get("bedroom_type"),
        "property_id":      parse_property_id(html),
        "unit_id":          parse_unique_id(html) or listing_meta.get("unit_id"),
        "apartment_type":   parse_apartment_type(html),
        "rental_type":      parse_type(html),
        "location":         parse_location(html),
        "categories":       parse_categories(html),
        "price_aed":        parse_price(html),
        "beds":             parse_beds(html),
        "baths":            parse_baths(html),
        "size_sqft":        parse_sqft(html),
        "coordinates":      parse_lat_lng(html),
        "availability_date":parse_availability(html),
        "description":      parse_description(html),
        "key_features":     parse_key_features(html),
        "special_offers":   parse_special_offers(html),
        "amenities":        parse_amenities(html),
        "photos":           parse_photos(html),
    }


# ── Persistence ────────────────────────────────────────────────────────────────

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


# ── Scraper ────────────────────────────────────────────────────────────────────

@browser(parallel=2, headless=True, add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_detail(driver: Driver, listing):
    url = listing["url"]
    for attempt in range(1, 4):
        try:
            driver.get(url)
            driver.sleep(3)
            for frac in (0.3, 0.6, 1.0):
                driver.run_js(f"window.scrollTo(0, document.body.scrollHeight*{frac});")
                driver.sleep(1)
            parsed = parse_listing(driver.page_html, listing)
            if not parsed.get("price_aed") and not parsed.get("description"):
                raise RuntimeError("page appears empty")
            print(
                f"  OK: {parsed.get('community')} | {parsed.get('unit_id')} | "
                f"AED {parsed.get('price_aed')} | {parsed.get('size_sqft')} sqft | "
                f"{parsed.get('beds')}bed/{parsed.get('baths')}bath",
                flush=True
            )
            return parsed
        except Exception as e:
            print(f"  attempt {attempt} failed ({url[-50:]}): {type(e).__name__}", flush=True)
            driver.sleep(3)
    return None


def main():
    with open(IN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    listings = data["listings"]
    total = len(listings)

    done = load_done()
    print(f"Already scraped: {len(done)}/{total}", flush=True)

    pending = [l for l in listings if l["url"] not in done]
    if not pending:
        print("All done!", flush=True)
        return

    consecutive_empty = 0

    for batch in chunks(pending, BATCH_SIZE):
        print(f"\nScraping batch of {len(batch)}...", flush=True)
        results = scrape_detail(batch)
        gained = 0
        for r in results:
            if r:
                done[r["url"]] = r
                gained += 1
        save_all(done)
        print(f"Batch done: +{gained} | total {len(done)}/{total}", flush=True)

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
