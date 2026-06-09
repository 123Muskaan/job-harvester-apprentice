"""
Scrape python-developer jobs in Bangalore from Naukri.

Why Playwright?
---------------
A plain `requests.get()` against the Naukri search URL returns only a
Next.js client-rendered shell (or an "Access Denied" page from
Cloudflare/edge protections). The job cards (`.srp-jobtuple-wrapper`)
are rendered in the browser by JavaScript, so they are NOT present in
the initial HTML payload. We therefore drive a real headless Chromium
via Playwright, wait for the cards to render, then parse the rendered
DOM with BeautifulSoup and print each job as a dict.

The full rendered HTML is also written to `page.html` for inspection.
"""

import csv
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://www.naukri.com/python-developer-jobs-in-bangalore"
CARD_SELECTOR = ".srp-jobtuple-wrapper"
TITLE_SELECTOR = "a.title"
COMPANY_SELECTOR = "a.comp-name"
LOCATION_SELECTOR = ".locWdth"

# ---- Headless browser run ---------------------------------------------------
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Send realistic browser-like headers so the page is actually served
    # to us (the unprotected UA got an "Access Denied" page from the edge).
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        viewport={"width": 1366, "height": 900},
        locale="en-US",
    )

    page = context.new_page()
    # Block heavy analytics/tracker requests so they don't slow hydration
    def _block(route):
        url = route.request.url
        if any(x in url for x in ("googletagmanager", "google-analytics", "logs.naukri", "lg.naukri", "nLogger", "ub_v1")):
            return route.abort()
        return route.continue_()
    page.route("**/*", _block)

    response = page.goto(URL, wait_until="networkidle", timeout=90_000)
    print(f"HTTP status: {response.status if response else 'n/a'}")
    print(f"Final URL:   {page.url}")

    # Wait until at least one job card is *attached* to the DOM
    cards_loaded = False
    try:
        page.wait_for_selector(CARD_SELECTOR, state="attached", timeout=30_000)
        cards_loaded = True
    except Exception as e:
        print(f"[warn] Timed out waiting for {CARD_SELECTOR}: {e}")

    # Brief settle to let lazy content finish
    page.wait_for_timeout(2000)

    # Sanity check the title text
    try:
        print(f"Page <title>: {page.title()!r}")
    except Exception:
        pass

    # Snapshot the rendered HTML
    rendered_html = page.content()
    with open("page.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    browser.close()

# ---- Parse with BeautifulSoup ----------------------------------------------
soup = BeautifulSoup(rendered_html, "html.parser")
cards = soup.select(CARD_SELECTOR)
print(f"Found {len(cards)} job card(s) matching {CARD_SELECTOR!r}\n")

if not cards_loaded:
    print(
        "[info] No .srp-jobtuple-wrapper cards were detected. This usually "
        "means the page was served as a Next.js client shell or was blocked. "
        "See page.html for the actual response.",
        file=sys.stderr,
    )

# ---- Extract, print & save to CSV -----------------------------------------
CSV_PATH = "jobs.csv"
CSV_FIELDS = ["Title", "Company", "Location", "Link"]

shown = 0
with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
    writer.writeheader()

    for card in cards:
        title_tag = card.select_one(TITLE_SELECTOR)
        company_tag = card.select_one(COMPANY_SELECTOR)
        location_tag = card.select_one(LOCATION_SELECTOR)

        # Skip cards where the title is missing
        if title_tag is None or not title_tag.get_text(strip=True):
            continue

        job = {
            "Title": title_tag.get_text(strip=True),
            "Company": company_tag.get_text(strip=True) if company_tag else "",
            "Location": location_tag.get_text(strip=True) if location_tag else "",
            "Link": title_tag.get("href", ""),
        }

        # Terminal output (unchanged)
        print({
            "title": job["Title"],
            "company": job["Company"],
            "location": job["Location"],
            "link": job["Link"],
        })

        # Persist to CSV (every extracted job, including empty
        # company/location/link fields, as long as a title is present)
        writer.writerow(job)
        shown += 1

print(f"\nPrinted {shown} job(s). Saved {shown} row(s) to {CSV_PATH!r}.")
