"""
Scans the raw web text collected by the WebsiteEnrichmentAgent
and populates the 'email' field on each lead dict.
"""

from utils.helpers import extract_emails_from_text
from utils.logger import get_logger

log = get_logger()

# Domains that are almost certainly not real business emails
JUNK_DOMAINS = {
    "example.com", "test.com", "domain.com", "yourdomain.com",
    "email.com", "sentry.io", "wixpress.com", "wordpress.com",
    "gmail.com",   # personal – only skip if business email also found
}

# Prefixes that usually indicate a real business contact
PRIORITY_PREFIXES = ["info", "contact", "sales", "support", "hello",
                     "enquiries", "enquiry", "admin", "office"]


class EmailExtractionAgent:
    """
    Extracts emails from the 'raw_web_text' field of each lead,
    picks the best one (or joins multiple), and writes to 'email'.
    """

    def run(self, leads: list[dict]) -> list[dict]:
        log.info("EmailExtractionAgent: extracting emails from %d leads …", len(leads))
        found_count = 0
        for lead in leads:
            text = lead.pop("raw_web_text", "")  # consume temp field
            if not text:
                continue
            emails = self._extract_best_emails(text, lead.get("website", ""))
            if emails:
                lead["email"] = "; ".join(emails)
                found_count += 1
        log.info("EmailExtractionAgent: extracted emails for %d leads.", found_count)
        return leads

    def _extract_best_emails(self, text: str, website: str) -> list[str]:
        all_emails = extract_emails_from_text(text)
        if not all_emails:
            return []

        # Infer the business domain from website URL
        biz_domain = ""
        if website:
            try:
                from urllib.parse import urlparse
                biz_domain = urlparse(website).netloc.lstrip("www.")
            except Exception:
                pass

        # Separate domain-matched vs others
        domain_matched = [e for e in all_emails
                          if biz_domain and e.endswith(biz_domain)]
        others         = [e for e in all_emails if e not in domain_matched]

        # Filter junk from others
        others = [e for e in others
                  if e.split("@")[-1] not in JUNK_DOMAINS]

        # Prefer domain-matched; fall back to others
        pool = domain_matched if domain_matched else others
        if not pool:
            return []

        # Within the pool, sort by priority prefix
        def priority(email: str) -> int:
            prefix = email.split("@")[0].lower()
            for i, p in enumerate(PRIORITY_PREFIXES):
                if prefix.startswith(p):
                    return i
            return len(PRIORITY_PREFIXES)

        pool.sort(key=priority)

        # Return top 3 unique emails
        seen: set[str] = set()
        result: list[str] = []
        for e in pool:
            if e not in seen:
                seen.add(e)
                result.append(e)
            if len(result) == 3:
                break
        return result