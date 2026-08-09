#!/usr/bin/env python3
"""
Module 1: Mitsawokett Photo Index & Detail Scraper (scrape_mitsawokett_photos.py)
==================================================================================
Crawls photo index pages, group photo sections, and unidentified photo pages across
Mitsawokett Photo Archive (nativeamericansofdelawarestate.com/Mitsawokett Photos/).
Downloads high-res photos to /assets/mitsawokett_photos/ and extracts metadata.
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
MITSAWOKETT_PHOTOS_DIR = os.path.join(OUTPUT_DIR, "assets", "mitsawokett_photos")

os.makedirs(MITSAWOKETT_PHOTOS_DIR, exist_ok=True)

TARGET_INDEXES = [
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexA-C.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexD.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexE-L.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexM.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexN-R.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexS-Z.htm"
]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 MitsawokettPhotoScraper/1.0"})

def init_photo_schema(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS photo_catalog (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_or_caption TEXT,
            subject_names TEXT,
            maiden_name TEXT,
            married_surname TEXT,
            location TEXT,
            approximate_year TEXT,
            local_image_path TEXT,
            source_url TEXT,
            dataset_source TEXT DEFAULT 'mitsawokett'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS person_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            photo_id INTEGER,
            confidence_score REAL DEFAULT 1.0,
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            FOREIGN KEY(photo_id) REFERENCES photo_catalog(photo_id)
        )
    """)
    conn.commit()

def parse_maiden_and_married_names(text: str):
    """
    Extract maiden name and married surname from patterns like 'Sarah Archer (Seeney)' or 'Lethia Coker (Carter)'
    """
    maiden = ""
    married = ""

    match = re.search(r"^([^\(]+)\s*\(([^\)]+)\)", text)
    if match:
        full_primary = match.group(1).strip()
        married = match.group(2).strip()
        words = full_primary.split()
        maiden = words[-1] if len(words) > 1 else full_primary
    else:
        words = text.split()
        maiden = words[-1] if words else ""

    return maiden, married

def scrape_mitsawokett_photos():
    print("=== Starting Mitsawokett Photo Archive Scraper ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_photo_schema(conn)
    cursor = conn.cursor()

    detail_links = set()

    for idx_url in TARGET_INDEXES:
        print(f"[Photo Index] Crawling: {idx_url}")
        try:
            r = session.get(idx_url, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception as e:
            print(f"Failed to fetch index {idx_url}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href")
            text = a.get_text(strip=True)
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue

            full_url = urllib.parse.urljoin(idx_url, href)

            # Target photo detail pages or direct image links
            if "Mitsawokett%20Photos/" in full_url or full_url.endswith((".htm", ".html", ".jpg", ".png")):
                detail_links.add((text, full_url))

    print(f"Discovered {len(detail_links)} photo detail and media links.")

    photos_downloaded = 0
    catalog_entries = 0

    for subject_text, page_url in detail_links:
        # Check if direct image or detail HTML page
        ext = os.path.splitext(urllib.parse.urlparse(page_url).path)[1].lower()
        maiden_name, married_surname = parse_maiden_and_married_names(subject_text)

        if ext in [".jpg", ".png", ".jpeg", ".gif"]:
            img_url = page_url
            caption = subject_text
        else:
            try:
                r = session.get(page_url, timeout=15)
                if r.status_code != 200:
                    continue
                r.encoding = r.apparent_encoding or "utf-8"
                detail_soup = BeautifulSoup(r.text, "html.parser")
                img_tag = detail_soup.find("img")
                if not img_tag or not img_tag.get("src"):
                    continue
                img_url = urllib.parse.urljoin(page_url, img_tag.get("src"))
                caption = detail_soup.get_text(separator=" ", strip=True)[:300]
            except Exception:
                continue

        orig_filename = os.path.basename(urllib.parse.urlparse(img_url).path)
        local_filename = f"mitsawokett_{orig_filename}"
        local_file_path = os.path.join(MITSAWOKETT_PHOTOS_DIR, local_filename)
        rel_db_path = f"assets/mitsawokett_photos/{local_filename}"

        # Download raw high-res photo asset
        if not os.path.exists(local_file_path):
            try:
                img_res = session.get(img_url, timeout=20)
                if img_res.status_code == 200:
                    with open(local_file_path, "wb") as f:
                        f.write(img_res.content)
                    photos_downloaded += 1
                    print(f"  [Photo Downloaded] {local_filename}")
            except Exception as e:
                print(f"  [Download Error] {img_url}: {e}")

        # Extract approximate year if present (e.g., c. 1921 or 1895)
        year_match = re.search(r"\b(18\d\d|19\d\d|20\d\d)\b", caption)
        approx_year = year_match.group(1) if year_match else ""

        # Catalog photo in photo_catalog table
        cursor.execute("""
            INSERT OR REPLACE INTO photo_catalog 
            (title_or_caption, subject_names, maiden_name, married_surname, location, approximate_year, local_image_path, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (caption, subject_text, maiden_name, married_surname, "Delaware / Delmarva", approx_year, rel_db_path, page_url))

        # Save to media_assets table as portrait photo
        cursor.execute("""
            INSERT OR REPLACE INTO media_assets (original_filename, local_path, caption, associated_page, wayback_url)
            VALUES (?, ?, ?, 'Mitsawokett_Photos', ?)
        """, (orig_filename, rel_db_path, f"Mitsawokett Photo: {subject_text}", page_url))

        catalog_entries += 1

    conn.commit()
    conn.close()
    print(f"=== Mitsawokett Photo Scraper Complete! Cataloged {catalog_entries} photos and downloaded {photos_downloaded} new high-res image assets. ===")

if __name__ == "__main__":
    scrape_mitsawokett_photos()
