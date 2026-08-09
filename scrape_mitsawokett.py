#!/usr/bin/env python3
"""
Module: Mitsawokett Family Histories Crawler (scrape_mitsawokett.py)
===================================================================
Crawls and parses the 'Native Americans of Delaware State' (Mitsawokett) 
17th Century Native American Community Family History Reports database:
https://nativeamericansofdelawarestate.com/FamilyHistories/Index.html
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
IMAGES_DIR = os.path.join(OUTPUT_DIR, "assets", "images")

INDEX_URL = "https://nativeamericansofdelawarestate.com/FamilyHistories/Index.html"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 MitsawokettPreservation/1.0"})

def init_mitsawokett_schema(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mitsawokett_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patriarch_name TEXT,
            surname TEXT,
            report_url TEXT UNIQUE,
            title TEXT,
            summary_text TEXT,
            clean_html TEXT
        )
    """)
    conn.commit()

def crawl_mitsawokett():
    print("=== Starting Mitsawokett (Native Americans of Delaware State) Crawler ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_mitsawokett_schema(conn)
    cursor = conn.cursor()

    try:
        r = session.get(INDEX_URL, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
    except Exception as e:
        print(f"Failed to fetch Mitsawokett index: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a")

    report_urls = set()
    for a in links:
        href = a.get("href")
        if not href:
            continue
        full_url = urllib.parse.urljoin(INDEX_URL, href)
        if "nativeamericansofdelawarestate.com/FamilyHistories/" in full_url and full_url != INDEX_URL:
            report_urls.add(full_url)

    print(f"Found {len(report_urls)} unique Family History Report links on Mitsawokett.")

    pages_saved = 0
    persons_saved = 0

    for rep_url in sorted(list(report_urls)):
        try:
            resp = session.get(rep_url, timeout=15)
            if resp.status_code != 200:
                continue
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception as e:
            print(f"  [Error] Could not fetch {rep_url}: {e}")
            continue

        rep_soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove navigation wrappers / template comments
        title_el = rep_soup.find("title")
        title = title_el.get_text(strip=True) if title_el else "Mitsawokett Family History"

        text_content = rep_soup.get_text(separator="\n", strip=True)
        rel_filename = f"mitsawokett_{os.path.basename(urllib.parse.urlparse(rep_url).path) or 'report.htm'}"

        # 1. Save to pages table
        cursor.execute("""
            INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rel_filename, title, str(rep_soup), text_content, rep_url, "2026-LIVE"))

        # 2. Extract Patriarch / Family Report Metadata
        path_parts = urllib.parse.urlparse(rep_url).path.split("/")
        folder_name = path_parts[-2] if len(path_parts) >= 2 else "Unknown"
        surname = folder_name.split("_")[0] if "_" in folder_name else folder_name

        cursor.execute("""
            INSERT OR REPLACE INTO mitsawokett_reports (patriarch_name, surname, report_url, title, summary_text, clean_html)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (folder_name, surname, rep_url, title, text_content[:500], str(rep_soup)))

        # 3. Extract Individuals and Add to persons Table
        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        for line in lines:
            if any(kw in line.lower() for kw in ["born", "died", "married", "b.", "d.", "m.", "son of", "daughter of"]):
                words = line.split()
                name_cand = " ".join(words[:4])
                if len(name_cand) > 3:
                    cursor.execute("""
                        INSERT OR IGNORE INTO persons (name, source_page, notes, dataset_source)
                        VALUES (?, ?, ?, 'mitsawokett_delaware')
                    """, (name_cand, rel_filename, f"Mitsawokett 17th C. Delaware Native Community: {line[:100]}"))
                    persons_saved += 1

        pages_saved += 1
        print(f"  [Preserved] {title[:60]} ({rel_filename})")

    conn.commit()

    # Re-run Cross-Dataset Entity Match Engine
    print("\n--- Cross-Linking Mitsawokett with Existing Lineage Graph ---")
    try:
        import integrate_moors
        integrate_moors.cross_link_datasets()
    except Exception as e:
        print(f"Error cross-linking: {e}")

    conn.close()
    print(f"=== Mitsawokett Preservation Complete! Saved {pages_saved} family history reports and {persons_saved} individuals. ===")

if __name__ == "__main__":
    crawl_mitsawokett()
