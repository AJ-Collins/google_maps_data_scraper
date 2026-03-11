# ─────────────────────────────────────────────
#  config.py  –  Central configuration
# ─────────────────────────────────────────────

import os

# ── Paths ──────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "leads.db")
CSV_PATH   = os.path.join(BASE_DIR, "leads.csv")
JSON_PATH  = os.path.join(BASE_DIR, "leads.json")
LOG_PATH   = os.path.join(BASE_DIR, "leadgen.log")

# ── Browser ────────────────────────────────────
HEADLESS          = True          # Set False to watch the browser
BROWSER_TIMEOUT   = 60_000        # ms  (60 s)
PAGE_LOAD_TIMEOUT = 30_000        # ms

# ── Scraping delays (seconds) ──────────────────
SCROLL_DELAY_MIN  = 1.5
SCROLL_DELAY_MAX  = 3.5
ACTION_DELAY_MIN  = 2.0
ACTION_DELAY_MAX  = 5.0

# ── Google Maps ────────────────────────────────
MAPS_BASE_URL     = "https://www.google.com/maps/search/"

# ── Website enrichment ─────────────────────────
CONTACT_PATHS     = ["/", "/contact", "/contact-us", "/about", "/about-us"]
REQUEST_TIMEOUT   = 15            # seconds
MAX_WEBSITE_PAGES = 4             # how many sub-pages to crawl per business

# ── Email regex ────────────────────────────────
EMAIL_REGEX = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"

# ── Data cleaning ──────────────────────────────
PHONE_INVALID_PREFIXES = ["000", "1234"]