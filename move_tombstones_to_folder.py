#!/usr/bin/env python3
"""
move_tombstones_to_folder.py
============================
Moves all tombstone photos, grave markers, headstones, and cemetery maps
from documents/ and people/ into a dedicated 'tombstones/' subfolder:
  preservation_output/assets/archive_media/tombstones/

Updates SQLite schema and paths in genealogy_preservation.db, and verifies
complete archive integrity.
"""

import os
import shutil
import sqlite3
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
ARCHIVE_MEDIA_DIR = os.path.join(ASSETS_DIR, "archive_media")
TOMBSTONES_DIR = os.path.join(ARCHIVE_MEDIA_DIR, "tombstones")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

def is_tombstone(norm_fn, orig_fn, dtype):
    name_check = f"{norm_fn.lower()} {orig_fn.lower()}"
    if dtype == "tombstone":
        return True, "dtype_tombstone"
    if any(k in name_check for k in ["tombstone", "headstone", "gravestone", "cemetery", "grave marker", "grave stone"]):
        return True, "keyword_tombstone"
    if re.search(r'\bcem\b', name_check) or "_cem_" in name_check or "-cem-" in name_check:
        return True, "cemetery_abbrev"
    if re.search(r'\bgraves?\b', name_check) or "_grave" in name_check:
        return True, "grave"
    return False, None

def run_move():
    print("==================================================================")
    print("MOVING TOMBSTONES TO DEDICATED FOLDER")
    print("==================================================================")

    os.makedirs(TOMBSTONES_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Update table schema check constraint to allow 'tombstones'
    print("Updating unified_photo_catalog table schema to include 'tombstones'...")
    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unified_photo_catalog_new (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT CHECK(category IN ('people', 'documents', 'family_trees', 'tombstones')),
            normalized_filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            local_image_path TEXT NOT NULL,
            sha256_hash TEXT NOT NULL,
            file_size_bytes INTEGER,
            mime_type TEXT,
            subject_names TEXT,
            surname TEXT,
            given_names TEXT,
            approximate_year TEXT,
            document_type TEXT,
            dataset_source TEXT,
            source_url TEXT,
            duplicate_cluster_id TEXT,
            is_primary_copy INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            canonical_photo_id INTEGER,
            dedup_type TEXT DEFAULT 'canonical'
        )
    """)
    cur.execute("INSERT INTO unified_photo_catalog_new SELECT * FROM unified_photo_catalog")
    cur.execute("DROP TABLE unified_photo_catalog")
    cur.execute("ALTER TABLE unified_photo_catalog_new RENAME TO unified_photo_catalog")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_unified_hash ON unified_photo_catalog (sha256_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_unified_category ON unified_photo_catalog (category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_unified_names ON unified_photo_catalog (surname, given_names)")
    cur.execute("PRAGMA foreign_keys=ON")
    conn.commit()

    # 2. Identify all tombstone records
    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               document_type, local_image_path
        FROM unified_photo_catalog
    """)
    all_photos = cur.fetchall()

    tombstone_records = []
    for pid, cat, norm_fn, orig_fn, dtype, lp in all_photos:
        is_tomb, reason = is_tombstone(norm_fn, orig_fn, dtype)
        if is_tomb:
            tombstone_records.append((pid, cat, norm_fn, orig_fn, dtype, lp, reason))

    print(f"Identified {len(tombstone_records)} tombstones to move.")

    moved_count = 0
    db_updated = 0

    for pid, old_cat, norm_fn, orig_fn, dtype, lp, reason in tombstone_records:
        src_path = os.path.join(PRESERVATION_DIR, lp)
        dest_path = os.path.join(TOMBSTONES_DIR, norm_fn)
        new_rel_path = f"assets/archive_media/tombstones/{norm_fn}"

        # Move physical file
        if os.path.exists(src_path) and not os.path.islink(src_path):
            shutil.move(src_path, dest_path)
            moved_count += 1
        elif os.path.islink(src_path):
            target = os.readlink(src_path)
            os.remove(src_path)
            # Make sure dest has the actual file
            abs_target = os.path.normpath(os.path.join(os.path.dirname(src_path), target))
            if os.path.exists(abs_target):
                shutil.copy2(abs_target, dest_path)
            moved_count += 1
        elif os.path.exists(dest_path):
            # Already at dest
            moved_count += 1

        # Update database catalog
        cur.execute("""
            UPDATE unified_photo_catalog
            SET category = 'tombstones', document_type = 'tombstone', local_image_path = ?
            WHERE photo_id = ?
        """, (new_rel_path, pid))

        # Update photo_catalog if referenced
        cur.execute("""
            UPDATE photo_catalog
            SET local_image_path = ?
            WHERE local_image_path = ?
        """, (new_rel_path, lp))

        db_updated += 1

    conn.commit()

    # Category breakdown
    cur.execute("SELECT category, COUNT(*) FROM unified_photo_catalog GROUP BY category")
    cat_summary = cur.fetchall()

    conn.close()

    print(f"\n[Movement Summary]")
    print(f"  - Files moved into tombstones/        : {moved_count}")
    print(f"  - Database records updated to tombstones: {db_updated}")
    print(f"\nNew Archive Category Breakdown:")
    for c, cnt in cat_summary:
        print(f"  - {c:15}: {cnt}")

    # Verify disk files
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT photo_id, local_image_path FROM unified_photo_catalog WHERE category = 'tombstones'")
    missing = [lp for _, lp in cur.fetchall() if not os.path.exists(os.path.join(PRESERVATION_DIR, lp))]
    conn.close()

    print(f"  - Tombstones missing from disk       : {len(missing)} (Expected: 0)")

    print("\n==================================================================")
    print("TOMBSTONES MOVEMENT COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    run_move()
