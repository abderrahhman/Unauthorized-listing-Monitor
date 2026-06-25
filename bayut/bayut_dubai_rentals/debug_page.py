import re
from botasaurus.browser import browser, Driver

@browser(add_arguments=["--no-sandbox", "--disable-dev-shm-usage"], output=None)
def check(driver, data):
    driver.get("https://www.bayut.com/companies/dubai-residential-assets-102918/")
    driver.sleep(8)
    html = driver.page_html

    # Find all pagination-related links/buttons
    pag = re.findall(r'href="([^"]*(?:page|Page)[^"]*)"', html)
    print("pagination hrefs:", pag[:20])

    # Find next page button
    next_links = re.findall(r'aria-label="[Nn]ext[^"]*"[^>]*href="([^"]+)"', html)
    print("next links:", next_links[:5])

    # Find any link with page in href
    all_hrefs = re.findall(r'href="(/[^"]{0,100})"', html)
    page_hrefs = [h for h in all_hrefs if "page" in h.lower()]
    print("hrefs with 'page':", page_hrefs[:10])

    # Check for ?page= query param style
    query_pages = re.findall(r'[?&]page=(\d+)', html)
    print("?page= params found:", query_pages[:10])

    # Check the URL after loading (may have redirected)
    print("current url:", driver.current_url)

    # Check for any JS fetch/API calls to get listings
    api_calls = re.findall(r'"(https://[^"]*bayut[^"]*api[^"]*)"', html)
    print("api urls:", api_calls[:5])

    # Try page 2 with query param
    driver.get("https://www.bayut.com/companies/dubai-residential-assets-102918/?page=2")
    driver.sleep(6)
    cards2 = driver.select_all("article")
    print(f"articles with ?page=2: {len(cards2)}")

    return None

check()
