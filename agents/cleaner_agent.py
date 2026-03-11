"""
Deduplicates leads, removes invalid entries, and normalises
remaining records before they are persisted to the database.
"""

import re
from typing import Optional

from config import PHONE_INVALID_PREFIXES
from utils.helpers import normalize_phone, clean_text
from utils.logger import get_logger

log = get_logger()

INVALID_EMAIL_PATTERN = re.compile(
    r"@(example|test|domain|localhost|yourdomain)\.",
    re.IGNORECASE,
)


class DataCleaningAgent:
    """
    Runs deduplication and validation on the full lead list.
    Returns a clean, ready-to-store list.
    """

    def run(self, leads: list[dict]) -> list[dict]:
        log.info("DataCleaningAgent: cleaning %d leads …", len(leads))
        before = len(leads)

        # Step 1 – basic field cleaning
        leads = [self._clean_lead(l) for l in leads]
        leads = [l for l in leads if l is not None]

        # Step 2 – deduplicate by (business_name + phone) or (business_name + website)
        leads = self._deduplicate(leads)

        after = len(leads)
        log.info(
            "DataCleaningAgent: %d → %d leads (removed %d duplicates/invalids).",
            before, after, before - after,
        )
        return leads

    def _clean_lead(self, lead: dict) -> Optional[dict]:
        lead = lead.copy()

        # Mandatory: business name
        name = clean_text(lead.get("business_name", ""))
        if not name or len(name) < 2:
            return None
        lead["business_name"] = name

        # Phone
        phone = normalize_phone(lead.get("phone", ""))
        if phone:
            # Drop obviously fake numbers
            for pfx in PHONE_INVALID_PREFIXES:
                if phone.lstrip("+").startswith(pfx):
                    phone = ""
                    break
        lead["phone"] = phone

        # Email validation
        email = lead.get("email", "")
        if email:
            valid_emails = []
            for e in email.split(";"):
                e = e.strip().lower()
                if e and "@" in e and not INVALID_EMAIL_PATTERN.search(e):
                    valid_emails.append(e)
            lead["email"] = "; ".join(valid_emails)

        # Clamp rating to 0-5
        try:
            r = float(lead.get("rating", "") or 0)
            lead["rating"] = str(round(min(max(r, 0), 5), 1)) if r else ""
        except ValueError:
            lead["rating"] = ""

        return lead

    @staticmethod
    def _deduplicate(leads: list[dict]) -> list[dict]:
        seen_keys: set[str] = set()
        unique: list[dict] = []

        for lead in leads:
            name    = (lead.get("business_name") or "").lower().strip()
            phone   = (lead.get("phone") or "").strip()
            website = (lead.get("website") or "").lower().strip().rstrip("/")

            # Build composite dedup keys
            key_np = f"{name}|{phone}"           if phone   else None
            key_nw = f"{name}|{website}"         if website else None
            key_n  = name                         # fallback: name only

            # Check any matching key
            if key_np and key_np in seen_keys:
                continue
            if key_nw and key_nw in seen_keys:
                continue
            if not key_np and not key_nw and key_n in seen_keys:
                continue

            # Register keys
            if key_np: seen_keys.add(key_np)
            if key_nw: seen_keys.add(key_nw)
            if not key_np and not key_nw: seen_keys.add(key_n)

            unique.append(lead)

        return unique