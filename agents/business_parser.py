# ─────────────────────────────────────────────
#  agents/business_parser.py  –  Business Detail Extraction Agent
# ─────────────────────────────────────────────
"""
Receives raw lead dicts (from maps_agent) and applies initial
parsing / normalisation before the enrichment stage.
"""

import re
from typing import Optional

from utils.helpers import normalize_phone, clean_text, normalize_url
from utils.logger import get_logger

log = get_logger()


class BusinessParserAgent:
    """
    Cleans and normalises the raw fields scraped from Google Maps.
    Works on a list of lead dicts in-place and returns the cleaned list.
    """

    def run(self, leads: list[dict]) -> list[dict]:
        log.info("BusinessParserAgent: parsing %d leads …", len(leads))
        parsed = []
        for lead in leads:
            cleaned = self._parse(lead)
            if cleaned:
                parsed.append(cleaned)
        log.info("BusinessParserAgent: %d leads after parsing.", len(parsed))
        return parsed

    # ── Internal ────────────────────────────────────────────────────────

    def _parse(self, lead: dict) -> Optional[dict]:
        lead = lead.copy()

        # Name is mandatory
        name = clean_text(lead.get("business_name", ""))
        if not name:
            return None
        lead["business_name"] = name

        # Phone normalisation
        lead["phone"] = normalize_phone(lead.get("phone", ""))

        # Website – ensure proper scheme
        website = lead.get("website", "")
        lead["website"] = normalize_url(website) if website else ""

        # Rating – keep only numeric part
        rating = lead.get("rating", "")
        m = re.search(r"[\d.]+", rating)
        lead["rating"] = m.group() if m else ""

        # Reviews – strip non-numeric
        reviews = lead.get("reviews", "")
        m = re.search(r"[\d,]+", reviews)
        lead["reviews"] = m.group().replace(",", "") if m else ""

        # Address
        lead["address"] = clean_text(lead.get("address", ""))

        # Category
        lead["category"] = clean_text(lead.get("category", ""))

        # Opening hours
        lead["opening_hours"] = clean_text(lead.get("opening_hours", ""))

        # Ensure email field exists
        lead.setdefault("email", "")

        return lead