import json
import os

from botasaurus.browser import browser, Driver

# How many listings to collect in total
MAX_LISTINGS = 500

# Write progress here after every page so it's observable / resumable
PROGRESS_FILE = "output/bayut_listings.json"


def load_progress():
    """Resume from a previous run if progress was saved."""
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


@browser(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"])
def bayut_scrape(driver: Driver, data):
    def text_of(card, selector):
        el = card.select(selector)
        return el.text if el else None

    def scrape_page(page, listings, seen_links):
        """Extract listings from one page. Returns count of new listings."""
        driver.get(f"https://www.bayut.com/for-sale/property/uae/page-{page}/")
        # Give the JS-rendered listing cards time to appear
        driver.sleep(6)

        # Listing cards are <article aria-label="Listing">. Botasaurus' selector
        # engine mishandles the tag+attribute combo, so grab every <article>
        # and skip the ones that aren't priced listings (promo/project cards).
        new_on_page = 0
        for card in driver.select_all('article'):
            price = text_of(card, 'span[aria-label="Price"]')
            if not price:
                continue

            link_el = card.select('a[aria-label="Listing link"]')
            link = link_el.get_attribute("href") if link_el else None
            if link and link.startswith("/"):
                link = "https://www.bayut.com" + link

            # Skip duplicates (sponsored listings can repeat across pages)
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)

            currency = text_of(card, 'span[aria-label="Currency"]')
            if currency:
                price = f"{currency} {price}"

            # Standard cards have an <h2 aria-label="Title">; compact cards
            # don't -> fall back to the listing link's `title` attribute.
            title = text_of(card, 'h2[aria-label="Title"]')
            if not title and link_el:
                title = link_el.get_attribute("title")

            # Location is a <div> on standard cards but a <span> on compact
            # ones, so match on the attribute alone (tag-agnostic).
            location = text_of(card, '[aria-label="Location"]')

            listings.append({
                "title": title,
                "price": price,
                "location": location,
                "link": link,
            })
            new_on_page += 1

            if len(listings) >= MAX_LISTINGS:
                break

        return new_on_page

    listings, seen_links, page = load_progress()
    if listings:
        print(f"Resuming from page {page} with {len(listings)} listings", flush=True)

    # Paginate until we have MAX_LISTINGS (or run out of pages)
    consecutive_failures = 0
    while len(listings) < MAX_LISTINGS:
        # Retry a page a few times before giving up (transient CDP timeouts)
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
            # If several pages fail in a row the browser has likely died -> abort
            # so we don't spin through dead pages forever.
            if consecutive_failures >= 3:
                print("3 pages failed in a row, browser likely dead. Aborting.", flush=True)
                break
            print(f"page {page} failed 3x, skipping it", flush=True)
            page += 1
            save_progress(listings, page)
            continue

        consecutive_failures = 0

        print(f"page {page}: +{new_on_page} new (total {len(listings)})", flush=True)

        # No new listings found -> reached the end of the results
        if new_on_page == 0:
            print("No more listings found, stopping.", flush=True)
            save_progress(listings, page)
            break

        page += 1
        save_progress(listings, page)

    # Saved automatically to output/bayut_scrape.json
    return {
        "count": len(listings),
        "listings": listings,
    }


# Initiate the web scraping task
bayut_scrape()
