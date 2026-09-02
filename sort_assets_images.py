#!/usr/bin/env python3
"""
sort_assets_images.py
=====================
Organizes photo assets in preservation_output/assets/images into:
  - people/    : Individual portraits, family photos, ancestor snapshots
  - documents/ : Social Security Applications (SS-5) and church/cemetery documentary listings

Maintains zero-breakage backwards compatibility via relative symlinks at the parent level,
and updates SQLite database records in media_assets and ss_applications.
"""

import os
import shutil
import sqlite3
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
IMAGES_DIR = os.path.join(PRESERVATION_DIR, "assets", "images")
PEOPLE_DIR = os.path.join(IMAGES_DIR, "people")
DOCS_DIR = os.path.join(IMAGES_DIR, "documents")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

def is_document(fname):
    fn_lower = urllib.parse.unquote(fname.lower())
    if fn_lower.startswith("ssa_") or "-ssa" in fn_lower:
        return True, "social_security_application"
    if any(k in fn_lower for k in ["fbranch", "fgrove", "harmony", "jwesley", "manship", "mission"]):
        return True, "church_cemetery_document"
    return False, "person"

def run_sorting():
    print("==================================================================")
    print("STARTING ASSETS/IMAGES REORGANIZATION")
    print("==================================================================")

    os.makedirs(PEOPLE_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    items = sorted(os.listdir(IMAGES_DIR))
    files_to_sort = [f for f in items if os.path.isfile(os.path.join(IMAGES_DIR, f)) and not os.path.islink(os.path.join(IMAGES_DIR, f))]

    print(f"Discovered {len(files_to_sort)} files in {IMAGES_DIR}")

    people_moved = 0
    docs_moved = 0
    moved_mapping = {}

    for fname in files_to_sort:
        src_path = os.path.join(IMAGES_DIR, fname)
        is_doc, reason = is_document(fname)
        target_subdir = "documents" if is_doc else "people"
        target_dir = DOCS_DIR if is_doc else PEOPLE_DIR
        dest_path = os.path.join(target_dir, fname)

        # Move file into subfolder
        shutil.move(src_path, dest_path)

        # Create relative symlink
        rel_link_target = os.path.join(target_subdir, fname)
        try:
            os.symlink(rel_link_target, src_path)
        except OSError:
            pass

        moved_mapping[fname] = target_subdir
        if is_doc:
            docs_moved += 1
        else:
            people_moved += 1

    print(f"\n[Disk Move Complete]")
    print(f"  - Moved to people/   : {people_moved}")
    print(f"  - Moved to documents/: {docs_moved}")
    print(f"  - Total files sorted : {people_moved + docs_moved}")

    # Update SQLite database
    print("\n[Updating Database Records]")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    db_updates_media_assets = 0
    cur.execute("SELECT id, local_path FROM media_assets WHERE local_path LIKE '%assets/images%'")
    for mid, lpath in cur.fetchall():
        if not lpath:
            continue
        fn = os.path.basename(lpath)
        target_sub = moved_mapping.get(fn)
        if target_sub:
            new_path = f"assets/images/{target_sub}/{fn}"
            if new_path != lpath:
                cur.execute("UPDATE media_assets SET local_path = ? WHERE id = ?", (new_path, mid))
                db_updates_media_assets += 1

    db_updates_ssa = 0
    cur.execute("SELECT id, local_image_path FROM ss_applications WHERE local_image_path LIKE '%assets/images%'")
    for sid, lpath in cur.fetchall():
        if not lpath:
            continue
        fn = os.path.basename(lpath)
        target_sub = moved_mapping.get(fn)
        if target_sub:
            new_path = f"assets/images/{target_sub}/{fn}"
            if new_path != lpath:
                cur.execute("UPDATE ss_applications SET local_image_path = ? WHERE id = ?", (new_path, sid))
                db_updates_ssa += 1

    conn.commit()
    conn.close()

    print(f"  - media_assets paths updated   : {db_updates_media_assets}")
    print(f"  - ss_applications paths updated: {db_updates_ssa}")

    print("\n==================================================================")
    print("ASSETS/IMAGES REORGANIZATION COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    run_sorting()
