#!/usr/bin/env python3
"""
Module 2: Cross-Year CDX Snapshot Fallback (cdx_fallback.py)
============================================================
Scans SQLite database and preserved HTML pages for unresolved relative links.
For missing pages, issues a targeted CDX API query across all historical capture years (1998-present)
to recover the closest snapshot with HTTP status 200, cleans the HTML, and saves to database.
"""

import os
import re
import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup, Comment

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
ROOT_DOMAIN = "http://www.lynncjackson.com/family/"
WAYBACK_BASE = "https://web.archive.org/web/"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 GenealogyCDXFallback/1.0"})

def clean_wayback_html(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    wm_selectors = [
        "#wm-ipp-base", "#wm-ipp", "#donato", "#wm-share",
        "iframe[src*='archive.org']", "script[src*='archive.org']",
        "link[href*='archive.org']", "div[id^='wm-']"
    ]
    for sel in wm_selectors:
        for el in soup.select(sel):
            el.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment) and "WAYBACK" in text):
        comment.extract()

    return soup

def find_unresolved_links():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return set()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, clean_html FROM pages")
    rows = cursor.fetchall()
    
    known_pages = {row[0] for row in rows}
    unresolved = set()

    for filename, clean_html in rows:
        if not clean_html:
            continue
        soup = BeautifulSoup(clean_html, "html.parser")
        for tag in soup.find_all(["a", "frame", "iframe", "area"]):
            href = tag.get("href") or tag.get("src")
            if not href:
                continue

            parsed = urllib.parse.urlparse(href)
            path = parsed.path

            if not path or path.startswith("http") or path.startswith("mailto:") or path.startswith("#"):
                continue

            rel_target = path.split("/family/", 1)[-1].lstrip("/") if "/family/" in path else path.lstrip("/")
            
            # Skip media or external files
            ext = os.path.splitext(rel_target)[1].lower()
            if ext in [".jpg", ".jpeg", ".gif", ".png", ".pdf", ".css", ".js"]:
                continue

            if rel_target and rel_target not in known_pages:
                unresolved.add(rel_target)

    conn.close()
    return unresolved

def recover_missing_page(rel_path: str):
    target_orig_url = urllib.parse.urljoin(ROOT_DOMAIN, rel_path)
    cdx_query_url = f"http://web.archive.org/cdx/search/cdx?url={target_orig_url}&output=json"
    print(f"Querying CDX fallback for: {rel_path}...")

    try:
        res = session.get(cdx_query_url, timeout=20)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"  [CDX Error] Failed to query CDX for {rel_path}: {e}")
        return None

    if not data or len(data) < 2:
        print(f"  [CDX] No capture history found for {rel_path}")
        return None

    header = data[0]
    idx_timestamp = header.index("timestamp") if "timestamp" in header else 1
    idx_status = header.index("statuscode") if "statuscode" in header else 4

    # Select the latest status 200 capture
    valid_captures = [row for row in data[1:] if row[idx_status] == "200"]
    if not valid_captures:
        print(f"  [CDX] No 200 OK captures found for {rel_path}")
        return None

    latest_capture = sorted(valid_captures, key=lambda x: x[idx_timestamp])[-1]
    timestamp = latest_capture[idx_timestamp]
    wayback_url = f"{WAYBACK_BASE}{timestamp}/{target_orig_url}"

    print(f"  [CDX Found] Recovering snapshot {timestamp} ({wayback_url})")

    try:
        r = session.get(wayback_url, timeout=30)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        soup = clean_wayback_html(r.text)
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else rel_path
        text_content = soup.get_text(separator="\n", strip=True)

        return {
            "filename": rel_path,
            "title": title,
            "clean_html": str(soup),
            "text_content": text_content,
            "wayback_url": wayback_url,
            "timestamp": timestamp
        }
    except Exception as e:
        print(f"  [Recovery Error] Could not fetch page from {wayback_url}: {e}")
        return None

def run_cdx_fallback():
    print("=== [Module 2] Starting Cross-Year CDX Snapshot Fallback ===")
    unresolved_links = find_unresolved_links()
    print(f"Found {len(unresolved_links)} unresolved internal page link(s).")

    if not unresolved_links:
        print("=== [Module 2] Completed. No broken internal links found. ===")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    recovered_count = 0

    for rel_path in unresolved_links:
        page_data = recover_missing_page(rel_path)
        if page_data:
            cursor.execute("""
                INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                page_data["filename"],
                page_data["title"],
                page_data["clean_html"],
                page_data["text_content"],
                page_data["wayback_url"],
                page_data["timestamp"]
            ))
            recovered_count += 1

    conn.commit()
    conn.close()
    print(f"=== [Module 2] Completed. Successfully recovered {recovered_count} missing subpages across CDX history. ===")

if __name__ == "__main__":
    run_cdx_fallback()
