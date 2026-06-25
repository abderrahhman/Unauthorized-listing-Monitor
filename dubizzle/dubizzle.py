import json
import os
import re

from botasaurus.browser import browser, Driver

MAX_LISTINGS = 25
PROGRESS_FILE = "output/dubizzle_listings.json"
BASE_URL = "https://dubai.dubizzle.com"


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return [], set(), 1
    with open(PROGRESS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    listings = data.get("listings", [])
    seen = {l["link"] for l in listings if l.get("link")}
    next_page = data.get("next_page", 1)
    return listings, seen, next_page


def save_progress(listings, next_page):
    os.makedirs("output", exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"count": len(listings), "next_page": next_page,
                   "listings": listings}, f, ensure_ascii=False, indent=2)


def clean(text):
    if not text:
        return None
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def inner_text(html, testid):
    """Extract inner text of the element with a given data-testid (from raw HTML)."""
    m = re.search(
        r'data-testid="' + re.escape(testid) + r'"[^>]*>(.*?)</(?:p|span|div|h[1-6]|a)\b',
        html, re.DOTALL
    )
    return clean(m.group(1)) if m else None


def parse_page_html(html, seen_links, max_listings, current_count):
    """Parse all listing cards from page HTML using regex — no WebDriver round trips."""
    listings = []

    # Each listing card is: <a data-testid="listing-N" ... href="...">...</a>
    # Split HTML into per-card chunks by finding each listing-N anchor's start
    card_starts = [m.start() for m in re.finditer(r'<a\s[^>]*data-testid="listing-\d+"', html)]

    for idx, start in enumerate(card_starts):
        # Card ends at the next listing card start (or a generous window)
        end = card_starts[idx + 1] if idx + 1 < len(card_starts) else start + 8000
        card_html = html[start:end]

        # Extract href
        href_m = re.search(r'href="([^"]+)"', card_html)
        if not href_m:
            continue
        href = href_m.group(1)
        if "/property-for-sale/residential/" not in href:
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        if href in seen_links:
            continue

        # Skip if no price (project/promo cards have no listing-price)
        price = inner_text(card_html, "listing-price")
        if not price:
            continue

        seen_links.add(href)
        listings.append({
            "title": inner_text(card_html, "subheading-text"),
            "price": f"AED {price}",
            "type": inner_text(card_html, "category-text"),
            "beds": inner_text(card_html, "listing-bedrooms"),
            "baths": inner_text(card_html, "listing-bathrooms"),
            "size_sqft": inner_text(card_html, "listing-size"),
            "location": inner_text(card_html, "listing-location"),
            "link": href,
        })

        if current_count + len(listings) >= max_listings:
            break

    return listings


@browser(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"])
def dubizzle_scrape(driver: Driver, data):

    def scrape_page(page, listings, seen_links):
        url = f"{BASE_URL}/en/property-for-sale/residential/?page={page}"
        driver.get(url)
        driver.sleep(6)
        html = driver.page_html
        new_listings = parse_page_html(html, seen_links, MAX_LISTINGS, len(listings))
        listings.extend(new_listings)
        return len(new_listings)

    listings, seen_links, page = load_progress()
    if listings:
        print(f"Resuming from page {page} with {len(listings)} listings", flush=True)

    consecutive_failures = 0
    while len(listings) < MAX_LISTINGS:
        new_on_page = None
        for attempt in range(1, 4):
            try:
                new_on_page = scrape_page(page, listings, seen_links)
                break
            except Exception as e:
                print(f"page {page} attempt {attempt} failed: {type(e).__name__}; retrying",
                      flush=True)
                driver.sleep(5)

        if new_on_page is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print("3 pages failed in a row, browser likely dead. Aborting.", flush=True)
                break
            print(f"page {page} failed 3x, skipping it", flush=True)
            page += 1
            save_progress(listings, page)
            continue

        consecutive_failures = 0
        print(f"page {page}: +{new_on_page} new (total {len(listings)})", flush=True)

        if new_on_page == 0:
            print("No more listings found, stopping.", flush=True)
            save_progress(listings, page)
            break

        page += 1
        save_progress(listings, page)

    return {"count": len(listings), "listings": listings}


dubizzle_scrape()
