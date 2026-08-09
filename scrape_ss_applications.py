#!/usr/bin/env python3
"""
Module: Social Security Applications Preservation (scrape_ss_applications.py)
=============================================================================
Scrapes and preserves Social Security Application records and primary document images 
contributed by Lishia Durham Heard from Mitsawokett:
https://nativeamericansofdelawarestate.com/SocialSecurityApplications.htm
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

SSA_INDEX_URL = "https://nativeamericansofdelawarestate.com/SocialSecurityApplications.htm"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 SSAPreservation/1.0"})

def init_ssa_schema(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ss_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surname TEXT,
            given_names TEXT,
            maiden_or_full_name TEXT,
            image_url TEXT UNIQUE,
            local_image_path TEXT,
            source_page TEXT
        )
    """)
    conn.commit()

def scrape_ss_applications():
    print("=== Starting Social Security Applications Preservation ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_ssa_schema(conn)
    cursor = conn.cursor()

    try:
        r = session.get(SSA_INDEX_URL, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
    except Exception as e:
        print(f"Failed to fetch SSA index page: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.find_all("tr")

    records_count = 0
    images_downloaded = 0

    # Save index page to pages table
    cursor.execute("""
        INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("SocialSecurityApplications.htm", "Mitsawokett Social Security Applications", str(soup), soup.get_text(separator="\n", strip=True), SSA_INDEX_URL, "2026-LIVE"))

    for row in rows:
        a_tag = row.find("a")
        if not a_tag or not a_tag.get("href"):
            continue

        img_href = a_tag.get("href")
        if not img_href.endswith((".jpg", ".png", ".jpeg")):
            continue

        row_text = row.get_text(separator=" ", strip=True)
        if "," in row_text:
            parts = row_text.split(",", 1)
            surname_col = parts[0].strip()
            given_names = parts[1].strip()
        else:
            surname_col = row_text
            given_names = row_text

        full_person_name = f"{surname_col}, {given_names}"



        full_img_url = urllib.parse.urljoin(SSA_INDEX_URL, img_href)

        orig_filename = os.path.basename(urllib.parse.urlparse(full_img_url).path)
        local_filename = f"ssa_{orig_filename}"
        local_file_path = os.path.join(IMAGES_DIR, local_filename)
        rel_db_path = f"assets/images/{local_filename}"

        # Download primary Social Security Application scan
        if not os.path.exists(local_file_path):
            try:
                img_res = session.get(full_img_url, timeout=20)
                if img_res.status_code == 200:
                    with open(local_file_path, "wb") as f:
                        f.write(img_res.content)
                    images_downloaded += 1
                    print(f"  [Downloaded SSA Scan] {local_filename}")
            except Exception as e:
                print(f"  [Error Downloading Scan] {full_img_url}: {e}")

        # Save to ss_applications table
        cursor.execute("""
            INSERT OR REPLACE INTO ss_applications (surname, given_names, maiden_or_full_name, image_url, local_image_path, source_page)
            VALUES (?, ?, ?, ?, ?, 'SocialSecurityApplications.htm')
        """, (surname_col, given_names, full_person_name, full_img_url, rel_db_path))


        # Save to media_assets table as primary historical document
        cursor.execute("""
            INSERT OR REPLACE INTO media_assets (original_filename, local_path, caption, associated_page, wayback_url)
            VALUES (?, ?, ?, 'SocialSecurityApplications.htm', ?)
        """, (orig_filename, rel_db_path, f"Social Security Application: {full_person_name}", full_img_url))

        # Add person to persons database table
        cursor.execute("""
            INSERT OR IGNORE INTO persons (name, source_page, notes, dataset_source)
            VALUES (?, 'SocialSecurityApplications.htm', ?, 'mitsawokett_ssa')
        """, (full_person_name, f"Social Security Application record: {full_person_name}"))

        records_count += 1


    conn.commit()
    conn.close()
    print(f"=== SSA Preservation Complete! Cataloged {records_count} application records and downloaded {images_downloaded} primary document scans. ===")

if __name__ == "__main__":
    scrape_ss_applications()
