#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  main.py  –  Lead Generation AI Agent System
#              Pipeline Orchestrator & CLI
# ─────────────────────────────────────────────
"""
Usage:
    python main.py

Follow the prompts to enter:
  - Business type  (e.g. insurance companies)
  - Location       (e.g. Nairobi Kenya)
  - Max results    (e.g. 100)

The pipeline will:
  1. Scrape Google Maps
  2. Parse / normalise business details
  3. Crawl each business website
  4. Extract emails
  5. Clean & deduplicate
  6. Store in SQLite
  7. Export to CSV + JSON
"""

import sys
import textwrap
from datetime import datetime

# ── Bootstrap sys.path so sub-packages resolve ────────────────────────────────
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.maps_agent       import MapsScraperAgent
from agents.business_parser  import BusinessParserAgent
from agents.website_agent    import WebsiteEnrichmentAgent
from agents.email_agent      import EmailExtractionAgent
from agents.cleaner_agent    import DataCleaningAgent
from storage.database        import init_db, bulk_insert_leads, count_leads
from storage.exporter        import export_csv, export_json
from utils.logger            import get_logger

log = get_logger()


# ══════════════════════════════════════════════
#  User Input Agent
# ══════════════════════════════════════════════

def collect_user_input() -> tuple[str, str, int]:
    """Interactive CLI prompts; returns (business_type, location, max_leads)."""
    print("\n" + "═" * 55)
    print("   🔍  Lead Generation AI Agent System")
    print("═" * 55)
    print(textwrap.dedent("""
    Examples:
      Business type : insurance companies | restaurants
                      law firms | hotels | dentists
      Location      : Nairobi Kenya | Mombasa Kenya
                      Westlands Nairobi | Karen Nairobi
    """))

    while True:
        btype = input("  Business type : ").strip()
        if btype:
            break
        print("  ⚠  Business type cannot be empty.")

    while True:
        location = input("  Location      : ").strip()
        if location:
            break
        print("  ⚠  Location cannot be empty.")

    while True:
        raw = input("  Max leads     : ").strip()
        try:
            max_leads = int(raw)
            if max_leads > 0:
                break
            print("  ⚠  Please enter a positive number.")
        except ValueError:
            print("  ⚠  Please enter a valid integer.")

    print("═" * 55 + "\n")
    return btype, location, max_leads


# ══════════════════════════════════════════════
#  Pipeline Orchestrator
# ══════════════════════════════════════════════

def run_pipeline(business_type: str, location: str, max_leads: int) -> None:
    start = datetime.now()
    log.info("Pipeline started at %s", start.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("Query: '%s in %s'  |  Max leads: %d", business_type, location, max_leads)

    # ── 1. Initialise database ──────────────────────────────────────────
    log.info("Initialising database …")
    init_db()

    # ── 2. Google Maps Scraper Agent ────────────────────────────────────
    maps_agent = MapsScraperAgent(business_type, location, max_leads)
    raw_leads  = maps_agent.run()

    if not raw_leads:
        log.warning("No leads collected from Google Maps. Exiting.")
        print("\n⚠  No leads were collected. Check your query or network.")
        return

    # ── 3. Business Detail Parser ───────────────────────────────────────
    parser_agent = BusinessParserAgent()
    parsed_leads = parser_agent.run(raw_leads)

    # ── 4. Website Enrichment Agent ─────────────────────────────────────
    website_agent   = WebsiteEnrichmentAgent()
    enriched_leads  = website_agent.run(parsed_leads)

    # ── 5. Email Extraction Agent ───────────────────────────────────────
    email_agent  = EmailExtractionAgent()
    email_leads  = email_agent.run(enriched_leads)

    # ── 6. Data Cleaning Agent ──────────────────────────────────────────
    cleaner_agent = DataCleaningAgent()
    clean_leads   = cleaner_agent.run(email_leads)

    # ── 7. Storage & Export Agent ───────────────────────────────────────
    log.info("Saving leads to database …")
    inserted = bulk_insert_leads(clean_leads)
    total_in_db = count_leads()

    log.info("Exporting CSV …")
    csv_path = export_csv()

    log.info("Exporting JSON …")
    json_path = export_json()

    # ── Summary ─────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    emails_found = sum(1 for l in clean_leads if l.get("email"))

    print("\n" + "═" * 55)
    print("   ✅  Lead generation completed!")
    print("═" * 55)
    print(f"   Businesses collected : {len(raw_leads)}")
    print(f"   After cleaning       : {len(clean_leads)}")
    print(f"   Emails extracted     : {emails_found}")
    print(f"   New rows inserted    : {inserted}")
    print(f"   Total in database    : {total_in_db}")
    print(f"   Time elapsed         : {elapsed}s")
    print(f"   Database             : leads.db")
    if csv_path:
        print(f"   CSV export           : leads.csv")
    if json_path:
        print(f"   JSON export          : leads.json")
    print("═" * 55 + "\n")

    log.info("Pipeline finished. %d leads stored.", total_in_db)


# ══════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════

if __name__ == "__main__":
    try:
        btype, location, max_leads = collect_user_input()
        run_pipeline(btype, location, max_leads)
    except KeyboardInterrupt:
        print("\n\n⚠  Interrupted by user. Partial results may be saved.")
        sys.exit(0)
    except Exception as exc:
        log.critical("Unhandled exception: %s", exc, exc_info=True)
        print(f"\n❌  Fatal error: {exc}")
        sys.exit(1)