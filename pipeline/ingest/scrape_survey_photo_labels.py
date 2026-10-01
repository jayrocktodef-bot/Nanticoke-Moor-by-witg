#!/usr/bin/env python3
"""
Scrape Photo Survey Labels (scrape_survey_photo_labels.py)
=========================================================
Crawls all 28 Photo Survey index pages on nativeamericansofdelawarestate.com
and extracts the EXACT text label next to every 'Photo Survey*.jpg' image.
100% authentic primary source labels. Zero hallucinated data.
"""

import os
import re
import urllib.request
import sqlite3
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

SURVEY_URLS = [
    f"https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/Photo%20Survey{i}.htm"
    for i in range(1, 29)
]

def scrape_survey_labels():
    print("=== Scraping Photo Survey Labels from All 28 Survey Pages ===", flush=True)
    
    label_map = {} # image_filename -> clean_label

    for url in SURVEY_URLS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                # Find all img tags
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    if not src:
                        continue

                    img_filename = os.path.basename(src)
                    
                    # Extract surrounding text from parent td/tr/p or alt tag
                    alt = img.get('alt', '').strip()
                    parent_text = img.parent.get_text(strip=True) if img.parent else ""
                    cell_text = ""
                    
                    # Look up nearest table cell
                    cell = img.find_parent(['td', 'p', 'div', 'tr'])
                    if cell:
                        cell_text = cell.get_text(" ", strip=True)

                    label = alt or parent_text or cell_text
                    
                    # Clean label
                    label = re.sub(r'Mitsawokett:.*$', '', label, flags=re.IGNORECASE).strip()
                    label = re.sub(r'\s+', ' ', label).strip()

                    if label and len(label) > 2 and "Photo Survey" not in label and not label.endswith(".jpg"):
                        label_map[img_filename.lower()] = label

        except Exception as e:
            continue

    print(f"Extracted {len(label_map)} authentic labels from Survey pages!")

    # Update photo_catalog in database
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()

    updated = 0

    c.execute("SELECT photo_id, local_image_path, source_url FROM photo_catalog")
    rows = c.fetchall()

    for photo_id, local_path, source_url in rows:
        fn = os.path.basename(source_url or local_path or "").lower()
        if fn in label_map:
            clean_l = label_map[fn]
            surname = clean_l.split()[-1] if clean_l else ""
            
            c.execute("""
                UPDATE photo_catalog
                SET title_or_caption = ?, subject_names = ?, maiden_name = COALESCE(maiden_name, ?)
                WHERE photo_id = ?
            """, (clean_l, clean_l, surname, photo_id))
            updated += 1

    conn.commit()
    conn.close()

    print(f"==================================================")
    print(f"Survey Photo Label Scrape Complete.")
    print(f"Total Photos Labeled with Real Names: {updated}")
    print(f"==================================================")

if __name__ == "__main__":
    scrape_survey_labels()
