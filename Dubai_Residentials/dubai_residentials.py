"""
Stage 1: Collect all listing cards from dubairesidential.ae/en/rented-properties.
Clicks "Load More" until all 118 listings are visible, then parses every card.
Output: output/listings.json

Card structure (confirmed from HTML):
  <div class="property-list" data-gallery-listing="">
    <a class="property-card" href="...?apartmentid=...">
      ...
      <span class="property-card__price"><span><span class="iconew-dhiram"></span> 66,000</span></span>
      <div class="property-card__address">Al Khail Gate | Al Quoz | Dubai</div>
      <span class="icon-acreage ..."></span><span class="property-card__features__number">1172 Sqft</span>
      <span class="icon-bed ..."></span><span class="property-card__features__number">2</span>
      <span class="icon-shower ..."></span><span class="property-card__features__number">2</span>
      <div class="property-card__description">...</div>
      data-desiredrent="66000" data-bed-room="2" data-apartment-type="2Bed-T1"
      data-unique-id="..." data-availability-start-date="..." data-property-id="..."
"""
import json
import os
import re
from urllib.parse import urlparse, parse_qs

from botasaurus.browser import browser, Driver

BASE_URL = "https://dubairesidential.ae"
LISTINGS_URL = f"{BASE_URL}/en/rented-properties"
OUT_FILE = "output/listings.json"


# ── Load More helpers ──────────────────────────────────────────────────────────

def count_listing_links(driver):
    return driver.run_js(
        "return document.querySelectorAll('a.property-card').length;"
    )


def load_more_visible(driver):
    return driver.run_js("""
        const btn = document.querySelector('button.btn-load-more');
        return btn ? (btn.offsetParent !== null && !btn.disabled) : false;
    """)


def click_load_more(driver):
    return driver.run_js("""
        const btn = document.querySelector('button.btn-load-more');
        if (btn && btn.offsetParent !== null && !btn.disabled) {
            btn.click(); return true;
        }
        return false;
    """)


# ── Card parsers ───────────────────────────────────────────────────────────────

def da(card, name):
    """Extract a data-* attribute value from card HTML."""
    m = re.search(rf'data-{re.escape(name)}="([^"]+)"', card)
    return m.group(1) if m else None


def parse_card(card_html):
    # URL
    url_m = re.search(r'href="(https://dubairesidential\.ae/en/rented-properties/[^"]+)"', card_html)
    if not url_m:
        return None
    url = url_m.group(1)

    # URL-derived fields
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    community_slug = parts[2] if len(parts) > 2 else None
    bedroom_slug   = parts[3] if len(parts) > 3 else None

    # Price: data-desiredrent="66000"
    rent_raw = da(card_html, "desiredrent")
    price_aed = int(rent_raw) if rent_raw and rent_raw.isdigit() else None

    # Also try the display span: <span class="iconew-dhiram"></span> 66,000
    if not price_aed:
        pm = re.search(r'iconew-dhiram[^<]*</span>\s*([\d,]+)', card_html)
        if pm:
            price_aed = int(pm.group(1).replace(",", ""))

    # Size: after icon-acreage
    sqft_m = re.search(
        r'icon-acreage[^<]*</span>\s*<span[^>]*property-card__features__number[^>]*>([\d,]+)\s*Sqft',
        card_html
    )
    size_sqft = int(sqft_m.group(1).replace(",", "")) if sqft_m else None

    # Beds: after icon-bed
    beds_m = re.search(
        r'icon-bed[^<]*</span>\s*<span[^>]*property-card__features__number[^>]*>(\d+)',
        card_html
    )
    beds = int(beds_m.group(1)) if beds_m else None

    # Baths: after icon-shower
    baths_m = re.search(
        r'icon-shower[^<]*</span>\s*<span[^>]*property-card__features__number[^>]*>(\d+)',
        card_html
    )
    baths = int(baths_m.group(1)) if baths_m else None

    # Location
    loc_m = re.search(r'class="property-card__address">([^<]+)</div>', card_html)
    location = loc_m.group(1).strip() if loc_m else None

    # Description
    desc_m = re.search(r'class="property-card__description"[^>]*>([^<]+)</div>', card_html)
    description = desc_m.group(1).strip() if desc_m else None

    # Thumbnails
    imgs = re.findall(r'src="(/-/media/dpam/rented-properties/[^"]+\.(?:jpg|jpeg|png|webp))"', card_html, re.I)
    thumbnails = list(dict.fromkeys(BASE_URL + i for i in imgs))

    return {
        "url":                  url,
        "community":            da(card_html, "community") or (community_slug.replace("-", " ").title() if community_slug else None),
        "community_slug":       community_slug,
        "bedroom_type":         bedroom_slug,
        "property_id":          da(card_html, "property-id"),
        "unit_id":              da(card_html, "unique-id"),
        "apartment_type":       da(card_html, "apartment-type"),
        "rental_type":          da(card_html, "rental-type"),
        "price_aed":            price_aed,
        "beds":                 beds if beds is not None else (int(da(card_html, "bed-room")) if da(card_html, "bed-room") and da(card_html, "bed-room").isdigit() else None),
        "baths":                baths,
        "size_sqft":            size_sqft,
        "location":             location,
        "availability_date":    da(card_html, "availability-start-date"),
        "description":          description,
        "thumbnail_images":     thumbnails,
    }


def parse_all_cards(html):
    # All cards are <a class="property-card"> elements inside a single wrapper div
    cards = html.split('<a class="property-card"')
    listings = []
    for card in cards[1:]:  # skip everything before the first card
        parsed = parse_card('<a class="property-card"' + card)
        if parsed:
            listings.append(parsed)
    return listings


# ── Scraper ────────────────────────────────────────────────────────────────────

@browser(headless=False, add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_listing_urls(driver: Driver, data):
    print("Loading listings page...", flush=True)
    driver.get(LISTINGS_URL)
    driver.sleep(5)

    prev_count = 0
    for attempt in range(40):
        count = count_listing_links(driver)
        print(f"  Visible cards: {count}", flush=True)

        if not load_more_visible(driver):
            print("  Load More gone — all loaded.", flush=True)
            break

        if count == prev_count and attempt > 0:
            print("  No change — done.", flush=True)
            break

        prev_count = count
        click_load_more(driver)
        driver.sleep(3)

    html = driver.page_html
    listings = parse_all_cards(html)
    print(f"\nParsed {len(listings)} listing cards.", flush=True)
    return listings


def main():
    os.makedirs("output", exist_ok=True)
    results = scrape_listing_urls()

    listings = []
    for r in results:
        if isinstance(r, list):
            listings.extend(r)
        elif r:
            listings.append(r)

    out = {"count": len(listings), "listings": listings}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(listings)} listings to {OUT_FILE}", flush=True)
    if listings:
        sample = listings[0]
        print(f"\nSample: {sample.get('community')} | AED {sample.get('price_aed')} | "
              f"{sample.get('size_sqft')} sqft | {sample.get('beds')}bed/{sample.get('baths')}bath", flush=True)


if __name__ == "__main__":
    main()
