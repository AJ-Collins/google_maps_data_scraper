import json

import pandas as pd

from config import CSV_PATH, JSON_PATH
from storage.database import fetch_all_leads
from utils.logger import get_logger

log = get_logger()


def export_csv(path: str = CSV_PATH) -> str:
    """Export all leads to CSV and return the file path."""
    leads = fetch_all_leads()
    if not leads:
        log.warning("No leads to export to CSV.")
        return ""
    df = pd.DataFrame(leads)
    # CRM-friendly column order
    ordered_cols = [
        "id", "business_name", "category", "phone", "email",
        "website", "address", "rating", "reviews",
        "maps_link", "opening_hours", "source_query", "scraped_at",
    ]
    # keep only columns that exist
    cols = [c for c in ordered_cols if c in df.columns]
    df = df[cols]
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info("Exported %d leads → %s", len(df), path)
    return path


def export_json(path: str = JSON_PATH) -> str:
    """Export all leads to JSON and return the file path."""
    leads = fetch_all_leads()
    if not leads:
        log.warning("No leads to export to JSON.")
        return ""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    log.info("Exported %d leads → %s", len(leads), path)
    return path