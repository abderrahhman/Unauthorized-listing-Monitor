"""
1. Downloads proxy lists from public GitHub sources (HTTP + SOCKS5).
2. Tests each against httpbin.org/ip to filter alive proxies (fast).
3. Saves working proxies to proxies_working.txt (protocol://ip:port, one per line).

Why not test against dubizzle directly:
  Dubizzle sits behind Cloudflare and always returns a JS challenge to plain
  requests (no browser).  Chrome solves the challenge automatically; requests
  never does.  Testing reachability via httpbin.org is sufficient — fresh proxy
  IPs will pass Cloudflare when used inside Chrome.

Usage:  python3 proxy_manager.py
"""
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

WORKING_PROXIES_FILE = "proxies_working.txt"
CHECK_URL = "https://httpbin.org/ip"
REQUEST_TIMEOUT = 8
MAX_WORKERS = 80
TARGET = 60
MAX_TEST = 5000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

SOURCES = [
    ("http",   "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("http",   "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"),
    ("http",   "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("http",   "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"),
    ("http",   "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"),
    ("http",   "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"),
    ("socks5", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt"),
    ("socks5", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"),
    ("socks5", "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt"),
]


def fetch_source(proto, url):
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        r.raise_for_status()
        lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
        return [f"{proto}://{ln}" for ln in lines if ":" in ln]
    except Exception as e:
        print(f"  WARNING: could not fetch {url.split('/')[-1]}: {e}", flush=True)
        return []


def collect_raw_proxies():
    print("Fetching proxy lists...", flush=True)
    all_proxies = []
    for proto, url in SOURCES:
        batch = fetch_source(proto, url)
        print(f"  {proto:6s} {len(batch):5d}  {url.split('/')[-1]}", flush=True)
        all_proxies.extend(batch)
    all_proxies = list(set(all_proxies))
    random.shuffle(all_proxies)
    print(f"Total unique: {len(all_proxies)}", flush=True)
    return all_proxies


def test_proxy(proxy_url):
    """Returns proxy_url if it can reach httpbin.org/ip within timeout."""
    try:
        resp = requests.get(
            CHECK_URL,
            proxies={"http": proxy_url, "https": proxy_url},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200 and "origin" in resp.text:
            return proxy_url
        return None
    except Exception:
        return None


def find_working_proxies(raw_proxies):
    pool = raw_proxies[:MAX_TEST]
    working = []
    tested = 0

    print(f"\nTesting up to {len(pool)} proxies against httpbin.org ({MAX_WORKERS} concurrent)...", flush=True)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(test_proxy, p): p for p in pool}
        for fut in as_completed(futures):
            tested += 1
            result = fut.result()
            if result:
                working.append(result)
                print(f"  ALIVE [{len(working)}/{TARGET}]: {result}", flush=True)
            if len(working) >= TARGET:
                for f in futures:
                    f.cancel()
                break
            if tested % 100 == 0:
                print(f"  ... {tested} tested, {len(working)} alive so far", flush=True)

    print(f"\nTested {tested} proxies, found {len(working)} alive.", flush=True)
    return working


def main():
    raw = collect_raw_proxies()
    if not raw:
        print("ERROR: no proxies fetched.", flush=True)
        return

    working = find_working_proxies(raw)

    with open(WORKING_PROXIES_FILE, "w") as f:
        f.write("\n".join(working) + "\n")

    print(f"\nDone: {len(working)} proxies saved to {WORKING_PROXIES_FILE}", flush=True)
    print("These proxies are alive. Chrome will handle Cloudflare's JS challenge when scraping.", flush=True)


if __name__ == "__main__":
    main()
