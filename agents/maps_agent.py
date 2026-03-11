"""
Launches a Playwright browser, searches Google Maps for
'{business_type} in {location}', scrolls the results sidebar,
and returns a list of raw business dicts.
"""

import random
import urllib.parse
from typing import Generator

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from config import (
    HEADLESS,
    BROWSER_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    MAPS_BASE_URL,
    SCROLL_DELAY_MIN,
    SCROLL_DELAY_MAX,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
)
from utils.helpers import random_delay, scroll_delay, clean_text
from utils.logger import get_logger

log = get_logger()

SEL_SIDEBAR_FEED  = 'div[role="feed"]'

# Business name  →  <h1 class="DUwDvf ...">
SEL_BIZ_NAME      = 'h1.DUwDvf'

# Category  →  <button class="DkEaL" inside the header block
SEL_CATEGORY      = 'button.DkEaL'

# Phone  →  <button data-item-id="phone:tel:XXXXXXXX">
# real example:  data-item-id="phone:tel:0709216000"
SEL_PHONE         = 'button[data-item-id^="phone:tel:"]'

# Address  →  <button data-item-id="address">
SEL_ADDRESS       = 'button[data-item-id="address"]'

# Website  →  <a data-item-id="authority" href="...">
SEL_WEBSITE_BTN   = 'a[data-item-id="authority"]'

# Rating  →  <span aria-hidden="true">4.5</span> inside div.F7nice
SEL_RATING        = 'div.F7nice span[aria-hidden="true"]'

# Reviews  →  <span role="img" aria-label="428 reviews"> inside div.F7nice
SEL_REVIEWS       = 'div.F7nice span[role="img"][aria-label]'

# Opening hours toggle  →  clickable div inside div.OqCZI
SEL_HOURS_BTN     = 'div.OqCZI div.OMl5r'

# Hours table rendered after clicking the toggle
SEL_HOURS_TABLE   = 'table.eK4R0e'


class MapsScraperAgent:
    """Playwright-based Google Maps scraper."""

    def __init__(self, business_type: str, location: str, max_results: int):
        self.business_type = business_type.strip()
        self.location      = location.strip()
        self.max_results   = max_results
        self.query         = f"{self.business_type} in {self.location}"
        self._search_url   = (
            MAPS_BASE_URL + urllib.parse.quote_plus(self.query)
        )

    def run(self) -> list[dict]:
        """Execute the full scraping pipeline and return collected leads."""
        log.info("Starting Google Maps search: '%s'", self.query)
        results: list[dict] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                user_agent=self._random_ua(),
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()
            page.set_default_timeout(BROWSER_TIMEOUT)

            try:
                self._open_maps(page)
                listing_urls = self._collect_listing_urls(page)
                log.info("Found %d listing URLs to process.", len(listing_urls))

                for i, url in enumerate(listing_urls, 1):
                    if len(results) >= self.max_results:
                        break
                    log.info("[%d/%d] Processing listing …", i, len(listing_urls))
                    lead = self._extract_listing(page, url)
                    if lead:
                        lead["source_query"] = self.query
                        results.append(lead)
                        log.debug("  ✓ %s", lead.get("business_name", "unknown"))
                    random_delay()

            except Exception as exc:
                log.error("MapsScraperAgent error: %s", exc, exc_info=True)
            finally:
                browser.close()

        log.info("Google Maps scraping complete. Collected %d businesses.", len(results))
        return results

    def _open_maps(self, page: Page) -> None:
        """Navigate to Google Maps and handle consent popups."""
        log.info("Opening %s", self._search_url)
        page.goto(self._search_url, wait_until="domcontentloaded",
                  timeout=PAGE_LOAD_TIMEOUT)
        random_delay(2, 4)

        # Accept consent dialog if shown (EU / cookie notice)
        for sel in ['button[aria-label*="Accept"]', 'button[jsname="higCR"]']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    random_delay(1, 2)
                    break
            except Exception:
                pass

    def _collect_listing_urls(self, page: Page) -> list[str]:
        """
        Scroll the results sidebar and collect href links to each business.
        Returns up to self.max_results * 1.2 URLs (buffer for failures).
        """
        target = min(int(self.max_results * 1.3), self.max_results + 50)
        urls: list[str] = []
        seen: set[str] = set()
        stall_count = 0
        max_stalls  = 5

        log.info("Scrolling listings sidebar …")

        while len(urls) < target:
            prev_count = len(urls)

            # Collect all visible listing anchors
            anchors = page.locator(
                'div[role="feed"] a[href*="/maps/place/"]'
            ).all()

            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    if href and href not in seen:
                        seen.add(href)
                        urls.append(href)
                except Exception:
                    pass

            if len(urls) >= target:
                break

            # Check for end-of-results message
            try:
                eol = page.locator('span:has-text("reached the end")').first
                if eol.is_visible(timeout=1000):
                    log.info("Reached end of results.")
                    break
            except Exception:
                pass

            # Scroll the feed
            try:
                feed = page.locator(SEL_SIDEBAR_FEED).first
                feed.evaluate("el => el.scrollBy(0, 600)")
            except Exception:
                page.mouse.wheel(0, 600)

            scroll_delay()

            if len(urls) == prev_count:
                stall_count += 1
                if stall_count >= max_stalls:
                    log.info("No new listings after %d scrolls – stopping.", max_stalls)
                    break
            else:
                stall_count = 0

            log.info("  Collected %d listing URLs …", len(urls))

        return urls[:target]

    def _extract_listing(self, page: Page, url: str) -> dict | None:
        """Navigate to a single listing URL and extract business details."""
        try:
            page.goto(url, wait_until="domcontentloaded",
                      timeout=PAGE_LOAD_TIMEOUT)
            random_delay(1.5, 3)
        except PWTimeout:
            log.warning("Timeout loading listing: %s", url)
            return None
        except Exception as exc:
            log.warning("Error loading listing (%s): %s", url, exc)
            return None

        lead: dict = {
            "business_name": "",
            "category":      "",
            "phone":         "",
            "address":       "",
            "website":       "",
            "rating":        "",
            "reviews":       "",
            "maps_link":     page.url,
            "opening_hours": "",
        }

        lead["business_name"] = self._get_text(page, SEL_BIZ_NAME)

        # <button class="DkEaL">Restaurant</button>
        lead["category"] = self._get_text(page, SEL_CATEGORY)

        # Real DOM: <button data-item-id="phone:tel:0709216000" ...>
        # Number lives after "tel:" in the data-item-id attribute
        try:
            ph_btn = page.locator(SEL_PHONE).first
            if ph_btn.is_visible(timeout=3000):
                raw_id = ph_btn.get_attribute("data-item-id") or ""
                if "tel:" in raw_id:
                    lead["phone"] = raw_id.split("tel:")[-1].strip()
                else:
                    # Fallback: aria-label e.g. "Phone: 0709 216000"
                    aria = ph_btn.get_attribute("aria-label") or ""
                    if ":" in aria:
                        lead["phone"] = aria.split(":", 1)[-1].strip()
        except Exception:
            pass

        # Extra fallback: visible text inside .Io6YTe child div
        if not lead["phone"]:
            try:
                txt_loc = page.locator('button[data-item-id^="phone:tel:"] .Io6YTe').first
                txt = clean_text(txt_loc.inner_text(timeout=2000))
                if txt:
                    lead["phone"] = txt
            except Exception:
                pass

        # Real DOM: <button data-item-id="address" aria-label="Address: 154 James...">
        # Visible text in child div.Io6YTe
        try:
            addr_btn = page.locator(SEL_ADDRESS).first
            if addr_btn.is_visible(timeout=3000):
                addr_inner = addr_btn.locator('.Io6YTe').first
                lead["address"] = clean_text(addr_inner.inner_text(timeout=2000))
                if not lead["address"]:
                    aria = addr_btn.get_attribute("aria-label") or ""
                    for pfx in ("Address:", "Anwani:"):
                        if pfx.lower() in aria.lower():
                            lead["address"] = aria.split(":", 1)[-1].strip()
                            break
        except Exception:
            pass

        # Real DOM: <a data-item-id="authority" href="https://...">
        try:
            web_link = page.locator(SEL_WEBSITE_BTN).first
            if web_link.is_visible(timeout=3000):
                lead["website"] = web_link.get_attribute("href") or ""
        except Exception:
            pass

        # Real DOM: <span aria-hidden="true">4.5</span> inside div.F7nice
        lead["rating"] = self._get_text(page, SEL_RATING)

        # Real DOM: <span role="img" aria-label="428 reviews">(428)</span>
        try:
            import re as _re
            rev_loc = page.locator(SEL_REVIEWS).first
            if rev_loc.is_visible(timeout=2000):
                aria = rev_loc.get_attribute("aria-label") or ""
                nums = _re.findall(r"[\d,]+", aria)
                if nums:
                    lead["reviews"] = nums[0].replace(",", "")
        except Exception:
            pass

        # Real DOM: div.OqCZI > div.OMl5r (clickable toggle row)
        # After clicking, table.eK4R0e appears with the full schedule
        try:
            hrs_btn = page.locator(SEL_HOURS_BTN).first
            if hrs_btn.is_visible(timeout=2000):
                hrs_btn.click()
                random_delay(0.5, 1.2)
                hrs_table = page.locator(SEL_HOURS_TABLE).first
                if hrs_table.is_visible(timeout=3000):
                    lead["opening_hours"] = clean_text(
                        hrs_table.inner_text(timeout=3000)
                    )
        except Exception:
            pass

        # Clean
        for k in lead:
            if isinstance(lead[k], str):
                lead[k] = clean_text(lead[k])

        if not lead["business_name"]:
            return None

        return lead

    @staticmethod
    def _get_text(page: Page, selector: str, timeout: int = 2000) -> str:
        try:
            loc = page.locator(selector).first
            if loc.is_visible(timeout=timeout):
                return clean_text(loc.inner_text(timeout=timeout))
        except Exception:
            pass
        return ""

    @staticmethod
    def _random_ua() -> str:
        """Return a plausible desktop user-agent string."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
            "Gecko/20100101 Firefox/125.0",
        ]
        return random.choice(agents)