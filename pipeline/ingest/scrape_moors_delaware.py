#!/usr/bin/env python3
"""
Module: Moors of Delaware Crawler & Parser (scrape_moors_delaware.py)
=====================================================================
Crawls and parses Joseph A. Romeo's 'The Moors of Delaware' genealogical database
from Wayback captures into genealogy_preservation.db.
"""

import os
import re
import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

WAYBACK_BASE = "https://web.archive.org/web/20180826150754/"
MOORS_ROOT = "http://www.moors-delaware.com/GenDat/"
CDX_QUERY = "http://web.archive.org/cdx/search/cdx?url=moors-delaware.com/*&output=json"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 MoorsScraper/1.0"})

def init_moors_db(conn):
    c = conn.cursor()
    # Add dataset_source column to persons if not present
    try:
        c.execute("ALTER TABLE persons ADD COLUMN dataset_source TEXT DEFAULT 'lynncjackson'")
    except sqlite3.OperationalError:
        pass # Column already exists

    c.execute("""
        CREATE TABLE IF NOT EXISTS entity_matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id_jackson INTEGER,
            person_id_moors INTEGER,
            confidence_score REAL,
            match_status TEXT DEFAULT 'candidate',
            FOREIGN KEY(person_id_jackson) REFERENCES persons(person_id),
            FOREIGN KEY(person_id_moors) REFERENCES persons(person_id)
        )
    """)
    conn.commit()

def fetch_moors_cdx_urls():
    print("[Moors] Fetching CDX URLs for moors-delaware.com...")
    try:
        r = session.get(CDX_QUERY, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[Moors CDX Error] {e}")
        return []

    if len(data) < 2:
        return []

    captures = {}
    for row in data[1:]:
        if row[4] == "200":
            url = row[2]
            timestamp = row[1]
            if url not in captures or timestamp > captures[url][0]:
                captures[url] = (timestamp, url)

    return list(captures.values())

def scrape_moors_database():
    print("=== [Module] Starting Moors of Delaware Preservation & Parser ===")
    conn = sqlite3.connect(DB_PATH)
    init_moors_db(conn)
    cursor = conn.cursor()

    cdx_items = fetch_moors_cdx_urls()
    print(f"[Moors] Discovered {len(cdx_items)} unique CDX capture paths.")

    # High-priority Moor/Nanticoke Surnames
    target_surnames = ["Argo", "Counselor", "Durham", "Harmon", "Jackson", "Mosley", "Munce", "Ridgeway", "Seeney", "Sockum", "Carney", "Cott", "Carter"]
    
    records_saved = 0
    persons_saved = 0

    # Seed list of known Moors pages if CDX is restricted
    seed_urls = [
        ("20180826150754", "http://moors-delaware.com/GenDat/moors.aspx"),
        ("20180826150754", "http://moors-delaware.com/GenDat/default.htm"),
        ("20180826150754", "http://moors-delaware.com/GenDat/surnames.htm")
    ]

    work_queue = seed_urls + cdx_items[:50]

    processed_urls = set()

    for timestamp, orig_url in work_queue:
        if orig_url in processed_urls:
            continue
        processed_urls.add(orig_url)

        wayback_url = f"https://web.archive.org/web/{timestamp}/{orig_url}"
        try:
            r = session.get(wayback_url, timeout=15)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        
        # Clean wayback headers
        for el in soup.select("#wm-ipp-base, #wm-ipp, iframe[src*='archive.org']"):
            el.decompose()

        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else "Moors of Delaware Record"
        page_text = soup.get_text(separator="\n", strip=True)

        # Save HTML to pages table
        rel_filename = f"moors_{os.path.basename(urllib.parse.urlparse(orig_url).path) or 'moors.htm'}"
        cursor.execute("""
            INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rel_filename, title, str(soup), page_text, wayback_url, timestamp))
        records_saved += 1

        # Extract Moors Individuals & Communities
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        for line in lines:
            for surname in target_surnames:
                if surname.lower() in line.lower() and len(line) < 120:
                    cursor.execute("""
                        INSERT OR IGNORE INTO persons (name, source_page, notes, dataset_source)
                        VALUES (?, ?, ?, 'moors_delaware')
                    """, (line[:80], rel_filename, f"Moor/Nanticoke lineage record - {surname} cluster"))
                    persons_saved += 1
                    break

    conn.commit()
    conn.close()
    print(f"=== [Moors] Completed. Preserved {records_saved} Moors pages and {persons_saved} individuals. ===")

if __name__ == "__main__":
    scrape_moors_database()
