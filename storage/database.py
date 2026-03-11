import sqlite3
from datetime import datetime
from typing import Optional

from config import DB_PATH
from utils.logger import get_logger

log = get_logger()


# Schema

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS business_leads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name   TEXT,
    category        TEXT,
    phone           TEXT,
    email           TEXT,
    website         TEXT,
    address         TEXT,
    rating          TEXT,
    reviews         TEXT,
    maps_link       TEXT,
    opening_hours   TEXT,
    source_query    TEXT,
    scraped_at      TEXT
);
"""

CREATE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_name_phone
    ON business_leads (business_name, phone);
"""


# Connection helper

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the database and table if they don't exist."""
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_INDEX_SQL)
        conn.commit()
    log.debug("Database initialised at %s", DB_PATH)


# Write

def insert_lead(lead: dict) -> bool:
    """
    Insert a single lead dict.
    Returns True if inserted, False if duplicate/error.
    """
    sql = """
    INSERT OR IGNORE INTO business_leads
        (business_name, category, phone, email, website,
         address, rating, reviews, maps_link, opening_hours,
         source_query, scraped_at)
    VALUES
        (:business_name, :category, :phone, :email, :website,
         :address, :rating, :reviews, :maps_link, :opening_hours,
         :source_query, :scraped_at)
    """
    lead.setdefault("scraped_at", datetime.utcnow().isoformat())
    try:
        with get_connection() as conn:
            cursor = conn.execute(sql, lead)
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as exc:
        log.error("DB insert error: %s | lead=%s", exc, lead.get("business_name"))
        return False


def bulk_insert_leads(leads: list[dict]) -> int:
    """Insert many leads; returns count of newly inserted rows."""
    inserted = 0
    for lead in leads:
        if insert_lead(lead):
            inserted += 1
    return inserted


# Read

def fetch_all_leads() -> list[dict]:
    """Return all leads as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM business_leads").fetchall()
    return [dict(row) for row in rows]


def count_leads() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM business_leads").fetchone()
    return row[0]