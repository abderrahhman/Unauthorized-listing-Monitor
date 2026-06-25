"""
Collect all listing URLs from Bayut company page:
  https://www.bayut.com/companies/dubai-residential-assets-102918/
Uses a single JS call per page to extract all cards (fast, no per-element CDP round trips).
Output: output/listings_urls.json
"""
import json
import os

from botasaurus.browser import browser, Driver

COMPANY_URL = "https://www.bayut.com/companies/dubai-residential-assets-102918/"
OUT_FILE = "output/listings_urls.json"

EXTRACT_JS = """
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
    let link = linkEl ? linkEl.href : null;
    return { link, price,
             title:    titleEl ? titleEl.textContent.trim() : (linkEl ? linkEl.title : null),
             location: locEl   ? locEl.textContent.trim()   : null };
}).filter(x => x && x.link);
"""


def load_progress():
    if not os.path.exists(OUT_FILE):
        return [], set(), 1
    with open(OUT_FILE, encoding="utf-8") as f:
        data = json.load(f)
    listings = data.get("listings", [])
    seen = {l["link"] for l in listings if l.get("link")}
    next_page = data.get("next_page", 1)
    return listings, seen, next_page


def save_progress(listings, next_page):
    os.makedirs("output", exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"count": len(listings), "next_page": next_page, "listings": listings},
                  f, ensure_ascii=False, indent=2)


@browser(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def scrape_page(driver: Driver, data):
    page_num, url = data["page"], data["url"]
    print(f"[PAGE {page_num}] Loading: {url}", flush=True)
    try:
        driver.get(url)
        driver.sleep(6)
    except Exception as e:
        print(f"[PAGE {page_num}] Load failed: {e}", flush=True)
        return []

    try:
        cards = driver.run_js(EXTRACT_JS)
        print(f"[PAGE {page_num}] Extracted {len(cards)} listings via JS", flush=True)
        return cards if isinstance(cards, list) else []
    except Exception as e:
        print(f"[PAGE {page_num}] JS extraction failed: {e}", flush=True)
        return []


def main():
    os.makedirs("output", exist_ok=True)

    all_listings, seen, start_page = load_progress()
    print(f"Resuming from page {start_page}, already have {len(all_listings)} listings", flush=True)

    consecutive_empty = 0
    page = start_page

    while True:
        url = COMPANY_URL if page == 1 else f"{COMPANY_URL}?page={page}"
        results = scrape_page({"page": page, "url": url})

        # flatten botasaurus result wrapper
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
        save_progress(all_listings, page + 1)

        if new_on_page == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print("2 consecutive empty pages — done.", flush=True)
                break
        else:
            consecutive_empty = 0

        page += 1

    print(f"\nTotal: {len(all_listings)} URLs → {OUT_FILE}", flush=True)


if __name__ == "__main__":
    main()
