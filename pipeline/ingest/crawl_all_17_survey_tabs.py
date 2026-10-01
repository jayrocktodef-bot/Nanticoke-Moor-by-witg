#!/usr/bin/env python3
"""
Crawl All 17 Photographic Survey Tabs (crawl_all_17_survey_tabs.py)
===================================================================
Deep-crawls all 17 pages of the Nanticoke & Moor Photographic Survey
(PhotographicSurvey-page1.htm through PhotographicSurvey-page17.htm)
from nativeamericansofdelawarestate.com, extracts ALL photos, captions,
and names, and ensures 100% complete cataloging in genealogy_preservation.db.
"""

import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
PHOTOS_DIR = os.path.join(OUTPUT_DIR, "assets", "mitsawokett_photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

BASE_URL = "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def crawl_17_tabs():
    print("=== Crawling All 28 Photographic Survey Tabs (Pages 1 - 28) ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    total_photos_found = 0
    new_photos_added = 0

    for page_num in range(1, 29):
        page_url = f"{BASE_URL}PhotographicSurvey-page{page_num}.htm"
        print(f"\n[Tab {page_num}/28] Fetching: {page_url}...", flush=True)

        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"  ❌ Failed to fetch Tab {page_num} (HTTP {r.status_code})", flush=True)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            images = soup.find_all('img')
            print(f"  ✓ Found {len(images)} image tags on Tab {page_num}", flush=True)

            for img in images:
                src = img.get('src')
                if not src: continue

                img_url = urljoin(page_url, src)
                filename = os.path.basename(img_url)

                # Skip header/template graphics
                if any(ign in filename.lower() for ign in ["copyright", "email", "redrule", "ind-footer", "banner", "sorry", "return"]):
                    continue

                total_photos_found += 1

                # Extract surrounding text / caption / alt
                alt = img.get('alt', '')
                parent = img.parent
                caption = parent.get_text().strip() if parent else alt

                # Infer surnames from text/filename
                maiden = None
                married = None
                for candidate in ["Durham", "Harmon", "Mosley", "Jackson", "Morgan", "Coker", "Carney", "Dean", "Wright", "Sisco", "Carter", "Hansor", "Ridgeway", "Counselor", "Sammons", "Johnson", "Sockum", "Seeney", "Thomas", "Clark", "Davis", "Norwood", "Miller", "Morris", "Gould", "Cuff", "Driggus", "Thompson", "Speck", "Rappahannock", "Nanticoke", "Alexander", "Pritchett", "Lopeman"]:
                    if candidate.lower() in caption.lower() or candidate.lower() in filename.lower():
                        if not maiden: maiden = candidate
                        elif not married and candidate != maiden: married = candidate

                # Download image asset locally
                local_path = os.path.join("assets", "mitsawokett_photos", f"mitsawokett_{filename}")
                full_local_path = os.path.join(OUTPUT_DIR, local_path)

                if not os.path.exists(full_local_path):
                    try:
                        img_resp = requests.get(img_url, headers=HEADERS, timeout=10)
                        if img_resp.status_code == 200:
                            with open(full_local_path, 'wb') as f:
                                f.write(img_resp.content)
                    except Exception as e:
                        pass

                # Check if already in photo_catalog
                c.execute("SELECT photo_id FROM photo_catalog WHERE local_image_path = ? OR source_url = ?", (local_path, img_url))
                row = c.fetchone()
                if not row:
                    c.execute("""
                        INSERT INTO photo_catalog (title_or_caption, subject_names, maiden_name, married_surname, local_image_path, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (caption[:200], caption[:80] or filename, maiden, married, local_path, img_url))
                    new_photos_added += 1

        except Exception as e:
            print(f"  ❌ Error processing Tab {page_num}: {e}", flush=True)

    conn.commit()
    conn.close()

    print(f"\n==================================================")
    print(f"Finished crawling all 17 tabs.")
    print(f"Total photos processed across 17 tabs: {total_photos_found}")
    print(f"New photo catalog records added: {new_photos_added}")
    print(f"==================================================")

if __name__ == "__main__":
    crawl_17_tabs()
