#!/usr/bin/env python3
"""
remove_web_assets.py
====================
Permanently removes scraped website template graphics, copyright banners,
navigation buttons, telemetry pixels, news logos, and divider graphics
from the unified archive and SQLite database.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
FRONTEND_ASSETS = os.path.join(SCRIPT_DIR, "frontend", "public", "assets")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

WEB_ASSET_PIDS = [
    13, 535, 536, 537, 2352, 2597, 2598, 2605, 2608, 2611, 2612, 2835, 2902,
    2977, 3043, 3106, 3180, 3184, 3185, 3191, 3192, 3193, 3195, 3216, 3220
]

def run_purge():
    print("==================================================================")
    print("PURGING SCRAPED WEB TEMPLATE ASSETS & BANNERS")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    placeholders = ",".join("?" * len(WEB_ASSET_PIDS))
    cur.execute(f"""
        SELECT photo_id, category, normalized_filename, original_filename, local_image_path
        FROM unified_photo_catalog
        WHERE photo_id IN ({placeholders})
    """, WEB_ASSET_PIDS)
    records = cur.fetchall()

    print(f"Identified {len(records)} web asset records to remove from archive.")

    files_removed = 0
    symlinks_removed = 0

    for pid, cat, norm_fn, orig_fn, lp in records:
        print(f"  - Purging: [{pid}] {norm_fn:40} | Orig: {orig_fn}")

        # 1. Path in archive_media
        archive_path = os.path.join(PRESERVATION_DIR, lp)
        if os.path.exists(archive_path) or os.path.islink(archive_path):
            if os.path.islink(archive_path):
                os.remove(archive_path)
                symlinks_removed += 1
            else:
                os.remove(archive_path)
                files_removed += 1

        # 2. Source symlinks in mitsawokett_photos subfolder
        for sub in ["documents", "people"]:
            src_sub_path = os.path.join(ASSETS_DIR, "mitsawokett_photos", sub, orig_fn)
            if os.path.islink(src_sub_path) or os.path.exists(src_sub_path):
                os.remove(src_sub_path)
                symlinks_removed += 1

        # 3. Source symlinks in mitsawokett_photos root
        src_root_path = os.path.join(ASSETS_DIR, "mitsawokett_photos", orig_fn)
        if os.path.islink(src_root_path) or os.path.exists(src_root_path):
            os.remove(src_root_path)
            symlinks_removed += 1

        # 4. Frontend public assets if present
        if os.path.exists(FRONTEND_ASSETS):
            for root, dirs, files in os.walk(FRONTEND_ASSETS):
                for f in [norm_fn, orig_fn]:
                    fp = os.path.join(root, f)
                    if os.path.islink(fp) or os.path.exists(fp):
                        try:
                            os.remove(fp)
                            symlinks_removed += 1
                        except OSError:
                            pass

    # 5. Purge from database
    cur.execute(f"DELETE FROM unified_photo_catalog WHERE photo_id IN ({placeholders})", WEB_ASSET_PIDS)
    cur.execute(f"UPDATE unified_photo_catalog SET canonical_photo_id = photo_id WHERE canonical_photo_id IN ({placeholders})", WEB_ASSET_PIDS)
    
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog")
    remaining_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE is_primary_copy = 1")
    canonical_count = cur.fetchone()[0]

    conn.close()

    print("\n[Purge Summary]")
    print(f"  - Physical files deleted : {files_removed}")
    print(f"  - Symlinks removed       : {symlinks_removed}")
    print(f"  - Catalog records purged : {len(records)}")
    print(f"  - Total catalog records  : {remaining_count}")
    print(f"  - Primary canonical photos: {canonical_count}")

    # Symlink verification
    print("\n[Running Broken Symlink Audit...]")
    broken = []
    total_links = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.islink(fp):
                total_links += 1
                if not os.path.exists(fp):
                    broken.append(fp)

    print(f"  - Total symlinks checked: {total_links}")
    print(f"  - Broken symlinks detected: {len(broken)} (Expected: 0)")
    if broken:
        for b in broken[:10]:
            print(f"    Broken: {b}")

    print("\n==================================================================")
    print("WEB ASSETS PURGE COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    run_purge()
