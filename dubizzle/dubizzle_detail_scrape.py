"""
Stage 2: Scrape full listing details from dubizzle.

── Rotating residential proxy mode (fastest, recommended for scaling) ──────
  Set ROTATING_PROXY below to your provider's rotating endpoint, e.g.:
    Webshare:   "http://user:pass@rotating.webshare.io:8080"
    Oxylabs:    "http://user:pass@residential.oxylabs.io:8001"
    BrightData: "http://user:pass@brd.superproxy.io:22225"
  Every Chrome session gets a fresh residential IP → no sleeping, no blocks.
  Estimated time for 500 listings: ~45-60 min.

── Static proxy list mode ──────────────────────────────────────────────────
  Set ROTATING_PROXY = None and populate proxies_working.txt (one per line).
  Each batch of LISTINGS_PER_PROXY uses a different proxy IP.
  Good for a list of 40+ residential proxies.

── Cooldown mode (fallback, no proxies) ────────────────────────────────────
  Slowest — uses the server's own IP with long sleeps between sessions.
"""
import json
import os
import random
import re
import time

from botasaurus.browser import browser, Driver

DEBUG = True  # set True locally to see the browser window; uses 5 listings only

NUM_LISTINGS = 5 if DEBUG else 500
OUT_FILE = "output/dubizzle_listings_full_debug.json" if DEBUG else "output/dubizzle_listings_full.json"
BASE_URL = "https://dubai.dubizzle.com"
LISTINGS_PAGE = f"{BASE_URL}/en/property-for-sale/residential/"
WORKING_PROXIES_FILE = "proxies_working.txt"

# ── Set this to your rotating residential proxy endpoint to eliminate all sleeping ──
# Example: "http://username:password@rotating.webshare.io:8080"
ROTATING_PROXY = None  # <-- plug in your proxy here

# How many listings per Chrome session (each session = one IP from the pool)
LISTINGS_PER_PROXY = 15  # 15 per proxy — safely under dubizzle's ~20/IP limit

# Cooldown settings (used when no proxies file found)
BATCH_SIZE = 8        # conservative — stop well before Cloudflare's detection threshold
BATCH_COOLDOWN = 600  # 10 min cooldown between batches within a session


# ── HTML parsers ───────────────────────────────────────────────────────────────

def clean(text):
    if not text:
        return None
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or None


def field(html, testid):
    m = re.search(
        r'data-testid="' + re.escape(testid) + r'"[^>]*>(.*?)</(?:p|span|div|h[1-6]|a)\b',
        html, re.DOTALL
    )
    return clean(m.group(1)) if m else None


def price_field(html):
    m = re.search(r'data-testid="listing-price".*?<p[^>]*>AED</p>\s*<p[^>]*>([^<]+)</p>',
                  html, re.DOTALL)
    if m:
        return f"AED {clean(m.group(1))}"
    m2 = re.search(r'data-testid="listing-price"[^>]*>(.*?)</div>', html, re.DOTALL)
    return clean(re.sub(r"<[^>]+>", " ", m2.group(1))) if m2 else None


def amenities_list(html):
    start = html.find('data-testid="amenities-title"')
    if start < 0:
        return None
    end = html.find('data-testid="finance-title"', start)
    if end < 0:
        end = start + 6000
    seg = html[start:end]
    found = re.findall(r'data-testid="([^"]+)"[^>]*>[^<]+</span>', seg)
    skip = {"amenities-title", "icon", "read-more"}
    return [a for a in found if a not in skip] or None


def images_list(html):
    imgs = re.findall(r'src="(https://dbz-images\.dubizzle\.com/images/[^"]+)"', html)
    return list(dict.fromkeys(imgs)) or None


def parse_listing(html, url):
    return {
        "url": url,
        "title": field(html, "listing-title"),
        "price": price_field(html),
        "type": field(html, "Type"),
        "purpose": field(html, "Purpose"),
        "beds": field(html, "bed_space"),
        "baths": field(html, "bath"),
        "size_sqft": field(html, "sqft"),
        "location": field(html, "location-information"),
        "furnishing": field(html, "Furnishing"),
        "completion_status": field(html, "Completion Status"),
        "handover": field(html, "Handover"),
        "developer": field(html, "Developer"),
        "project_name": field(html, "Project Name"),
        "description": field(html, "description"),
        "posted_on": field(html, "posted-on"),
        "updated": field(html, "Updated"),
        "payment_plan": field(html, "Payment Plan"),
        "validated_information": {
            "ownership": field(html, "Ownership"),
            "balcony_size": field(html, "Balcony Size"),
            "parking_availability": field(html, "Parking Availability"),
            "usage": field(html, "Usage"),
        },
        "building_information": {
            "building_name": field(html, "Building Name"),
            "floors": field(html, "Floors"),
            "retail_centres": field(html, "Retail Centres"),
            "swimming_pools": field(html, "Swimming Pools"),
            "parking_spaces": field(html, "Parking Spaces"),
            "building_area": field(html, "Building Area"),
            "elevators": field(html, "Elevators"),
        },
        "regulatory_information": {
            "permit_number": field(html, "Permit Number"),
            "zone_name": field(html, "Zone Name"),
            "registered_agency": field(html, "Registered Agency"),
            "rera": field(html, "RERA"),
            "reference_id": field(html, "Reference ID"),
            "brn_dld": field(html, "BRN (DLD)"),
        },
        "agent": {
            "name": field(html, "agent-name"),
        },
        "amenities": amenities_list(html),
        "photos": images_list(html),
    }


# ── persistence ────────────────────────────────────────────────────────────────

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


# ── proxy-rotation mode ────────────────────────────────────────────────────────

def load_proxies():
    """
    Returns a proxy list. If ROTATING_PROXY is set, returns it repeated so
    the rotation loop always has something to cycle through — each new Chrome
    session will get a fresh IP from the provider's pool automatically.
    """
    if ROTATING_PROXY:
        return [ROTATING_PROXY] * 500  # rotating endpoint handles IP diversity
    if not os.path.exists(WORKING_PROXIES_FILE):
        return []
    with open(WORKING_PROXIES_FILE) as f:
        return [ln.strip() for ln in f if ln.strip()]


def make_scraper(proxy=None):
    """Return a browser function bound to the given proxy (or no proxy)."""
    kwargs = dict(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"])
    if DEBUG:
        kwargs["headless"] = False
    if proxy:
        kwargs["proxy"] = proxy

    @browser(**kwargs)
    def _scrape(driver: Driver, listing):
        url = listing["link"]
        for attempt in range(1, 4):
            try:
                driver.get(url, bypass_cloudflare=True)
                driver.sleep(random.uniform(3, 5))
                for frac in (0.3, 0.6, 1.0):
                    driver.run_js(f"window.scrollTo(0, document.body.scrollHeight*{frac});")
                    driver.sleep(random.uniform(1, 2))
                driver.sleep(random.uniform(1, 2))
                parsed = parse_listing(driver.page_html, url)
                if not parsed.get("title") and not parsed.get("price"):
                    raise RuntimeError("page blocked or empty")
                return parsed
            except Exception as e:
                print(f"  attempt {attempt} failed: {type(e).__name__}", flush=True)
                driver.sleep(4)
        return None

    return _scrape


def run_with_proxies(listings, done, proxies):
    """Rotate a fresh proxy every LISTINGS_PER_PROXY listings — no cooldown needed."""
    pending = [l for l in listings if l["link"] not in done]
    print(
        f"Proxy-rotation mode | "
        f"{len(done)}/{NUM_LISTINGS} done | "
        f"{len(pending)} pending | "
        f"{len(proxies)} proxies",
        flush=True
    )

    for batch_idx, batch in enumerate(chunks(pending, LISTINGS_PER_PROXY)):
        proxy = proxies[batch_idx % len(proxies)]
        print(f"\nBatch {batch_idx + 1}: {len(batch)} listings via {proxy}", flush=True)

        scraper = make_scraper(proxy)
        results = scraper(batch)

        gained = 0
        for r in results:
            if r:
                done[r["url"]] = r
                gained += 1
                print(
                    f"  OK [{len(done)}/{NUM_LISTINGS}]: {(r.get('title') or '')[:50]}",
                    flush=True
                )
        save_all(done)
        print(f"  Batch {batch_idx + 1} done: +{gained} | total {len(done)}/{NUM_LISTINGS}", flush=True)

    print(f"\nDONE (proxy mode): {len(done)}/{NUM_LISTINGS} listings in {OUT_FILE}", flush=True)


# ── fallback cooldown mode ─────────────────────────────────────────────────────

def cooldown(driver, seconds):
    print(f"COOLDOWN: idling {seconds}s...", flush=True)
    driver.get(LISTINGS_PAGE, bypass_cloudflare=True)
    chunks_count = max(1, seconds // 30)
    per_chunk = seconds / chunks_count
    for _ in range(chunks_count):
        time.sleep(per_chunk)
        driver.run_js("window.scrollTo(0, Math.random()*document.body.scrollHeight);")
    print("COOLDOWN: resuming.", flush=True)


@browser(headless=not DEBUG, add_arguments=["--no-sandbox", "--disable-dev-shm-usage"])
def scrape_with_cooldowns(driver: Driver, data):
    with open("output/dubizzle_listings.json", encoding="utf-8") as f:
        listings = json.load(f)["listings"][:NUM_LISTINGS]

    done = load_done()
    print(f"Cooldown mode | already have {len(done)}/{NUM_LISTINGS}", flush=True)

    print("Warming up session...", flush=True)
    driver.get(LISTINGS_PAGE, bypass_cloudflare=True)
    driver.sleep(random.uniform(3, 5))

    batch_count = 0
    consecutive_fails = 0
    consecutive_batch_fails = 0
    last_batch_start = 0

    for i, listing in enumerate(listings):
        url = listing["link"]
        if url in done:
            continue

        if batch_count > 0 and batch_count % BATCH_SIZE == 0:
            # Check if the last batch made zero progress (IP blocked)
            if batch_count == last_batch_start:
                consecutive_batch_fails += 1
                if consecutive_batch_fails >= 2:
                    print("2 batches with zero new listings — IP likely blocked. Aborting for restart.", flush=True)
                    break
            else:
                consecutive_batch_fails = 0
            last_batch_start = batch_count
            cooldown(driver, BATCH_COOLDOWN)
            batch_count = 0

        result = None
        for attempt in range(1, 4):
            try:
                driver.get(url, bypass_cloudflare=True)
                driver.sleep(random.uniform(4, 7))
                for frac in (0.3, 0.6, 1.0):
                    driver.run_js(f"window.scrollTo(0, document.body.scrollHeight*{frac});")
                    driver.sleep(random.uniform(1.5, 3))
                driver.sleep(random.uniform(2, 4))

                parsed = parse_listing(driver.page_html, url)
                if not parsed.get("title") and not parsed.get("price"):
                    wait = 60 + attempt * 30
                    print(f"[{i+1}] attempt {attempt} blocked; cooling {wait}s", flush=True)
                    cooldown(driver, wait)
                    continue

                result = parsed
                break
            except Exception as e:
                print(f"[{i+1}] attempt {attempt} error: {type(e).__name__}", flush=True)
                driver.sleep(5)

        if result is None:
            consecutive_fails += 1
            if consecutive_fails >= 3:
                print("3 consecutive failures — IP blocked. Aborting for 30-min restart.", flush=True)
                break
            continue

        consecutive_fails = 0
        batch_count += 1
        done[url] = result
        save_all(done)
        print(
            f"[{i+1}/{NUM_LISTINGS}] OK: {(result.get('title') or '')[:50]} | {result.get('price')}",
            flush=True
        )

        if i + 1 < len(listings):
            driver.sleep(random.uniform(8, 15))

    print(f"DONE (cooldown mode): {len(done)}/{NUM_LISTINGS} in {OUT_FILE}", flush=True)
    return {"count": len(done)}


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    proxies = load_proxies()

    with open("output/dubizzle_listings.json", encoding="utf-8") as f:
        listings = json.load(f)["listings"][:NUM_LISTINGS]

    done = load_done()

    if proxies:
        run_with_proxies(listings, done, proxies)
    else:
        print(
            "No proxies_working.txt found — running in cooldown mode.\n"
            "Run proxy_manager.py first for faster proxy-rotation mode.",
            flush=True
        )
        scrape_with_cooldowns()


if __name__ == "__main__":
    main()
