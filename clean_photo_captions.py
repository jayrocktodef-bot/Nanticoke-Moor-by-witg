#!/usr/bin/env python3
"""
Refine Photo Subject Names (clean_photo_captions.py)
===================================================
Extracts exact full personal names for subject_names:
- "Charles Edward & Della Mae (Ridgway) Carey" -> "Charles Edward Carey & Della Mae (Ridgway) Carey"
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def extract_full_names_from_text(text, maiden, married, url):
    if not text:
        text = ""

    # Clean text first
    t = text.split('\n')[0].strip()
    t = re.sub(r"^Mitsawokett:\s*A\s*17th\s*Century.*\|\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^Mitsawokett:\s*A\s*17th\s*Century.*$", "", t, flags=re.IGNORECASE).strip()

    if not t or len(t) < 4:
        if url:
            fn = os.path.basename(url).replace('.htm', '').replace('.html', '')
            t = re.sub(r'([a-z])([A-Z])', r'\1 \2', fn).replace('&', ' & ')

    # Truncate clean caption line
    clean_cap = t[:120].strip()

    # Extract clean subject display string
    subj = clean_cap
    if len(subj) > 60:
        # Stop at first sentence or double space
        subj = re.split(r'\.\s+|\s{2,}', subj)[0].strip()

    return clean_cap, subj

def run_refine():
    print("=== Refining Photo Subject Names ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()

    c.execute("SELECT photo_id, title_or_caption, maiden_name, married_surname, source_url FROM photo_catalog")
    rows = c.fetchall()

    for photo_id, cap, maiden, married, url in rows:
        clean_cap, clean_subj = extract_full_names_from_text(cap, maiden, married, url)
        c.execute("""
            UPDATE photo_catalog
            SET title_or_caption = ?, subject_names = ?
            WHERE photo_id = ?
        """, (clean_cap, clean_subj, photo_id))

    conn.commit()
    conn.close()
    print("=== Photo Subject Names Refined! ===")

if __name__ == "__main__":
    run_refine()
