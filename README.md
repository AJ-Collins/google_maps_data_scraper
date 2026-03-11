# google_maps_data_scraper
# 🔍 Lead Generation AI Agent System

A professional, multi-stage automation pipeline that collects B2B leads from
Google Maps, enriches them with email addresses scraped from business websites,
and exports structured data to SQLite / CSV / JSON.

---

## Architecture

```
User Input Agent
      ↓
Google Maps Scraper Agent    (Playwright)
      ↓
Business Detail Parser       (normalise fields)
      ↓
Website Enrichment Agent     (requests + BeautifulSoup)
      ↓
Email Extraction Agent       (regex + mailto links)
      ↓
Data Cleaning Agent          (dedup, validate)
      ↓
Storage & Export Agent       (SQLite → CSV + JSON)
```

---

## Project Structure

```
leadgen_ai_agent/
├── main.py              ← CLI entry point & pipeline orchestrator
├── config.py            ← All tuneable settings
├── requirements.txt
│
├── agents/
│   ├── maps_agent.py        Google Maps scraper (Playwright)
│   ├── business_parser.py   Raw field normalisation
│   ├── website_agent.py     Website crawler (requests)
│   ├── email_agent.py       Email extractor (regex)
│   └── cleaner_agent.py     Dedup & validation
│
├── storage/
│   ├── database.py          SQLite helpers
│   └── exporter.py          CSV / JSON export
│
└── utils/
    ├── logger.py            Logging (console + file)
    └── helpers.py           Shared utilities
```

---

## Installation

```bash
# 1. Clone / unzip the project
cd leadgen_ai_agent

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium
```

---

## Usage

```bash
python main.py
```

You will be prompted for:

```
Business type : insurance companies
Location      : Nairobi Kenya
Max leads     : 200
```

### Example inputs

| Business type       | Location          |
|---------------------|-------------------|
| insurance companies | Nairobi Kenya     |
| restaurants         | Westlands Nairobi |
| law firms           | Mombasa Kenya     |
| hotels              | Karen Nairobi     |
| dentists            | Kisumu Kenya      |

---

## Output files

| File         | Description                          |
|--------------|--------------------------------------|
| `leads.db`   | SQLite database (table: business_leads) |
| `leads.csv`  | CRM-ready CSV export                 |
| `leads.json` | JSON export                          |
| `leadgen.log`| Full debug log                       |

### CSV / DB columns

```
id, business_name, category, phone, email, website,
address, rating, reviews, maps_link, opening_hours,
source_query, scraped_at
```

---

## Configuration (`config.py`)

| Setting             | Default  | Description                        |
|---------------------|----------|------------------------------------|
| `HEADLESS`          | `True`   | Run browser invisibly              |
| `ACTION_DELAY_MIN`  | `2.0`    | Min delay between actions (secs)   |
| `ACTION_DELAY_MAX`  | `5.0`    | Max delay between actions (secs)   |
| `MAX_WEBSITE_PAGES` | `4`      | Sub-pages to crawl per business    |
| `REQUEST_TIMEOUT`   | `15`     | HTTP request timeout (secs)        |

To watch the browser while scraping, set `HEADLESS = False` in `config.py`.

---

## Anti-blocking techniques

- Random delays between all actions
- Rotating user-agent strings
- Respectful scroll speed on the Maps sidebar
- Session-based HTTP requests with realistic headers
- SSL verification graceful fallback

---

## Tips for large-scale collection

- Run in batches of 200–500 per query to avoid Maps rate limits
- Use different location modifiers: `"Westlands Nairobi"`, `"CBD Nairobi"`, etc.
- Combine multiple business-type queries for the same area
- The `INSERT OR IGNORE` dedup in SQLite prevents re-inserting duplicates
  across multiple runs, so re-running with the same query is safe

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `playwright install` fails | Run `pip install playwright` first |
| Google Maps shows CAPTCHA | Set `HEADLESS = False`, solve manually once |
| No emails extracted | Many sites use contact forms; check `leads.csv` — website field still populated |
| SSL errors on websites | Already handled with `verify=False` fallback |