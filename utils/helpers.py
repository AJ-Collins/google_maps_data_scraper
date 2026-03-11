import random
import re
import time
from urllib.parse import urljoin, urlparse

from config import (
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
    SCROLL_DELAY_MIN,
    SCROLL_DELAY_MAX,
    EMAIL_REGEX,
)


def random_delay(min_s: float = ACTION_DELAY_MIN,
                 max_s: float = ACTION_DELAY_MAX) -> None:
    """Sleep for a random duration to mimic human behaviour."""
    time.sleep(random.uniform(min_s, max_s))


def scroll_delay() -> None:
    random_delay(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX)



def safe_urljoin(base: str, path: str) -> str:
    """Safely join a base URL and a relative path."""
    try:
        return urljoin(base, path)
    except Exception:
        return ""


def normalize_url(url: str) -> str:
    """Ensure the URL has a scheme."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def get_base_url(url: str) -> str:
    """Return scheme + netloc  e.g. https://example.com"""
    try:
        p = urlparse(normalize_url(url))
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return ""


def extract_emails_from_text(text: str) -> list[str]:
    """Return a de-duplicated list of emails found in *text*."""
    emails = re.findall(EMAIL_REGEX, text)
    # filter obvious false positives (image filenames, etc.)
    cleaned = []
    for e in emails:
        e = e.lower().strip(".")
        ext = e.rsplit(".", 1)[-1]
        if len(ext) > 5:          # very long TLD → skip
            continue
        if any(bad in e for bad in ["@2x", ".png", ".jpg", ".gif", ".svg"]):
            continue
        cleaned.append(e)
    return list(dict.fromkeys(cleaned))   # deduplicate while preserving order


def normalize_phone(phone: str) -> str:
    """Strip non-numeric characters, keep leading +."""
    if not phone:
        return ""
    phone = phone.strip()
    normalized = re.sub(r"[^\d+]", "", phone)
    return normalized

def clean_text(text: str) -> str:
    """Strip excessive whitespace."""
    if not text:
        return ""
    return " ".join(text.split()).strip()