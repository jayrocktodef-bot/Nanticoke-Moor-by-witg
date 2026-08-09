#!/usr/bin/env python3
"""
Photo Deduplication Engine (deduplicate_photos.py)
===================================================
Deduplicates photo_catalog entries in genealogy_preservation.db while reassigning
all person_photos junction links to surviving canonical photo records.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

IGNORED_SITE_ASSETS = [
    "Copyright (C) 1998-2002.jpg", "email.jpg", "ind-footer.gif", "redrule.gif",
    "sorry.jpg", "banner.jpg", "return.gif"
]

def score_photo_entry(row):
    """Score metadata completeness of a photo catalog row to pick canonical entry."""
    pid, caption, subjects, maiden, married, year, path, url = row
    score = 0
    if subjects and subjects.lower() not in ["unknown", "who"]: score += 10
    if maiden and maiden.lower() not in ["unknown", "who"]: score += 15
    if married and married.lower() not in ["unknown", "who"]: score += 10
    if year: score += 5
    if caption and len(caption) > 30: score += 5
    if url and "PhotographicSurvey" in url: score += 2
    return score

def run_photo_deduplication():
    print("=== Running Photo Deduplication Engine ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # 1. Clean out site icon / template image entries
    for asset in IGNORED_SITE_ASSETS:
        c.execute("SELECT photo_id FROM photo_catalog WHERE local_image_path LIKE ?", (f"%{asset}%",))
        bad_ids = [r[0] for r in c.fetchall()]
        if bad_ids:
            placeholders = ",".join("?" * len(bad_ids))
            c.execute(f"DELETE FROM person_photos WHERE photo_id IN ({placeholders})", bad_ids)
            c.execute(f"DELETE FROM photo_catalog WHERE photo_id IN ({placeholders})", bad_ids)
            print(f"Removed {len(bad_ids)} template site asset entries ({asset}).", flush=True)

    conn.commit()

    # 2. Find groups of duplicate photos by local_image_path
    c.execute("""
        SELECT photo_id, title_or_caption, subject_names, maiden_name, 
               married_surname, approximate_year, local_image_path, source_url
        FROM photo_catalog
        WHERE local_image_path IS NOT NULL AND local_image_path != ''
    """)
    all_photos = c.fetchall()

    path_groups = {}
    for p in all_photos:
        path = p[6]
        if path not in path_groups:
            path_groups[path] = []
        path_groups[path].append(p)

    merged_count = 0
    deleted_photos_count = 0

    for path, entries in path_groups.items():
        if len(entries) > 1:
            # Sort by completeness score descending
            entries.sort(key=score_photo_entry, reverse=True)
            canonical = entries[0]
            canonical_id = canonical[0]

            duplicate_ids = [e[0] for e in entries[1:]]

            # Reassign person_photos junction links
            for dup_id in duplicate_ids:
                c.execute("UPDATE OR IGNORE person_photos SET photo_id = ? WHERE photo_id = ?", (canonical_id, dup_id))
                c.execute("DELETE FROM person_photos WHERE photo_id = ?", (dup_id,))
                c.execute("DELETE FROM photo_catalog WHERE photo_id = ?", (dup_id,))
                deleted_photos_count += 1
            
            merged_count += 1

    conn.commit()

    # Summary Stats
    c.execute("SELECT COUNT(*) FROM photo_catalog")
    remaining_photos = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM person_photos")
    remaining_links = c.fetchone()[0]

    conn.close()

    print(f"Successfully deduplicated {merged_count} photo groups.")
    print(f"Deleted {deleted_photos_count} duplicate photo records.")
    print(f"Remaining Unique Preserved Photos in Catalog: {remaining_photos}")
    print(f"Remaining Active Person-Photo Junction Links: {remaining_links}")
    print("=== Photo Deduplication Complete! ===", flush=True)

if __name__ == "__main__":
    run_photo_deduplication()
