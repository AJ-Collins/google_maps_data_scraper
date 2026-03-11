"""
For each lead that has a website URL, fetches homepage + contact pages
and hands the raw HTML to the EmailAgent for extraction.
"""

import random
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import CONTACT_PATHS, REQUEST_TIMEOUT, MAX_WEBSITE_PAGES
from utils.helpers import safe_urljoin, get_base_url, random_delay
from utils.logger import get_logger

log = get_logger()

# User-agent pool
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class WebsiteEnrichmentAgent:
    """
    Visits each business website and returns combined page text
    so the email agent can extract contacts.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept-Language": "en-US,en;q=0.9"})

    def run(self, leads: list[dict]) -> list[dict]:
        """
        Enriches each lead dict with a 'raw_web_text' key containing
        the combined text of all crawled pages.
        """
        log.info("WebsiteEnrichmentAgent: enriching %d leads …", len(leads))
        enriched = 0
        for lead in leads:
            website = lead.get("website", "")
            if not website:
                lead["raw_web_text"] = ""
                continue
            text = self._crawl_website(website)
            lead["raw_web_text"] = text
            if text:
                enriched += 1
            random_delay(1, 2.5)   # polite crawl
        log.info("WebsiteEnrichmentAgent: fetched content for %d websites.", enriched)
        return leads

    def _crawl_website(self, base_url: str) -> str:
        """Fetch homepage + contact sub-pages; return combined text."""
        root = get_base_url(base_url)
        if not root:
            return ""

        combined_texts: list[str] = []
        fetched = 0

        for path in CONTACT_PATHS:
            if fetched >= MAX_WEBSITE_PAGES:
                break
            url = safe_urljoin(root, path) if path != "/" else root
            html = self._get_html(url)
            if html:
                combined_texts.append(self._html_to_text(html))
                fetched += 1

        return "\n".join(combined_texts)

    def _get_html(self, url: str) -> Optional[str]:
        try:
            self.session.headers["User-Agent"] = random.choice(UA_POOL)
            resp = self.session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False,    # some sites have self-signed certs
            )
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "")
            if "html" not in ct and "text" not in ct:
                return None
            return resp.text
        except requests.exceptions.SSLError:
            # Retry without SSL verification already set above
            return None
        except Exception as exc:
            log.debug("WebsiteAgent: could not fetch %s – %s", url, exc)
            return None

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Extract visible text + mailto hrefs from HTML."""
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # Extract mailto links explicitly (often not in visible text)
        mailto_emails = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if href.startswith("mailto:"):
                mailto_emails.append(href.replace("mailto:", "").split("?")[0])

        text = soup.get_text(separator=" ")
        if mailto_emails:
            text += " " + " ".join(mailto_emails)
        return text