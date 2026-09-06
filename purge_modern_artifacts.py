#!/usr/bin/env python3
"""
purge_modern_artifacts.py
=========================
Permanently purges modern web template artifacts, scraped celebrity/stock photos,
and non-family graphics from SQLite database and filesystem.
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
FRONTEND_PUBLIC = os.path.join(SCRIPT_DIR, "frontend", "public")
FRONTEND_DIST = os.path.join(SCRIPT_DIR, "frontend", "dist")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)

KNOWN_JUNK_PIDS = [
    1, 2, 3, 4, 5, 14, 15, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 53,
    2589, 2590, 2591, 2592, 2593, 2594, 2595, 2596, 2599, 2600, 2601, 2602, 2603
]

def purge_artifacts():
    print("==================================================================")
    print("PURGING MODERN SCRAPED ARTIFACTS & CELEBRITY/STOCK PHOTOS")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Find all UUID or known junk photos
    all_photos = cur.execute("""
        SELECT photo_id, category, original_filename, normalized_filename, local_image_path
        FROM unified_photo_catalog
    """).fetchall()

    target_pids = set(KNOWN_JUNK_PIDS)
    for pid, cat, orig, norm, loc in all_photos:
        if UUID_PATTERN.search(orig or '') or UUID_PATTERN.search(loc or '') or UUID_PATTERN.search(norm or ''):
            target_pids.add(pid)

    print(f"Identified {len(target_pids)} modern artifact photo records to purge.")

    # 2. Get file paths before deleting from DB
    placeholders = ",".join("?" * len(target_pids))
    records = cur.execute(f"""
        SELECT photo_id, category, original_filename, normalized_filename, local_image_path
        FROM unified_photo_catalog
        WHERE photo_id IN ({placeholders})
    """, list(target_pids)).fetchall()

    files_removed = 0
    for pid, cat, orig, norm, loc in records:
        print(f"  - Purging Photo [{pid}]: {norm} (Orig: {orig})")
        # Candidate file locations
        candidates = [
            os.path.join(PRESERVATION_DIR, loc),
            os.path.join(PRESERVATION_DIR, "assets", loc),
            os.path.join(FRONTEND_PUBLIC, loc),
            os.path.join(FRONTEND_DIST, loc),
            os.path.join(PRESERVATION_DIR, "assets", "archive_media", cat, norm),
            os.path.join(FRONTEND_PUBLIC, "assets", "archive_media", cat, norm),
            os.path.join(FRONTEND_DIST, "assets", "archive_media", cat, norm),
            os.path.join(PRESERVATION_DIR, "assets", "mitsawokett_photos", "people", orig),
            os.path.join(PRESERVATION_DIR, "assets", "mitsawokett_photos", "documents", orig),
        ]
        for cpath in set(candidates):
            if os.path.islink(cpath) or os.path.exists(cpath):
                try:
                    os.remove(cpath)
                    files_removed += 1
                except Exception as e:
                    print(f"    Failed removing {cpath}: {e}")

    # 3. Delete from DB tables
    cur.execute(f"DELETE FROM person_photos WHERE photo_id IN ({placeholders})", list(target_pids))
    pp_del = cur.rowcount
    cur.execute(f"DELETE FROM photo_surnames WHERE photo_id IN ({placeholders})", list(target_pids))
    ps_del = cur.rowcount
    cur.execute(f"DELETE FROM photo_catalog WHERE photo_id IN ({placeholders})", list(target_pids))
    pc_del = cur.rowcount
    cur.execute(f"DELETE FROM unified_photo_catalog WHERE photo_id IN ({placeholders})", list(target_pids))
    upc_del = cur.rowcount

    conn.commit()
    conn.close()

    print(f"✓ Removed {files_removed} files from disk.")
    print(f"✓ Deleted from unified_photo_catalog: {upc_del} rows")
    print(f"✓ Deleted from photo_catalog: {pc_del} rows")
    print(f"✓ Deleted from photo_surnames: {ps_del} rows")
    print(f"✓ Deleted from person_photos: {pp_del} rows")
    print("Modern artifact purge complete!\n")

if __name__ == "__main__":
    purge_artifacts()
