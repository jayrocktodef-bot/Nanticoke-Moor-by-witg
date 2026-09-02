#!/usr/bin/env python3
"""
separate_family_trees.py
========================
Separates all family trees, pedigree charts, lineage diagrams, and descent trees
from people/ and documents/ into a dedicated 'family_trees/' subfolder:
  preservation_output/assets/archive_media/family_trees/

Updates SQLite schema and paths in genealogy_preservation.db, and preserves
complete backwards compatibility via relative symlinks.
"""

import os
import shutil
import sqlite3
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
ARCHIVE_MEDIA_DIR = os.path.join(ASSETS_DIR, "archive_media")
TREES_DIR = os.path.join(ARCHIVE_MEDIA_DIR, "family_trees")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

def is_family_tree(orig_fn, norm_fn):
    orig_clean = urllib.parse.unquote(orig_fn).lower()
    norm_clean = norm_fn.lower()
    
    if "ancestry" in orig_clean or "ancestry" in norm_clean:
        return True, "ancestry_pedigree_chart"
    if "lineage" in orig_clean or "lineage" in norm_clean:
        return True, "lineage_chart"
    if "descent" in orig_clean or "descent" in norm_clean:
        return True, "descent_tree"
    if "pedigree" in orig_clean or "pedigree" in norm_clean:
        return True, "pedigree_chart"
    if any(k in orig_clean or k in norm_clean for k in ["family tree", "familytree", "family_tree"]):
        return True, "family_tree"
    return False, None

def run_separation():
    print("==================================================================")
    print("SEPARATING FAMILY TREES INTO DEDICATED FOLDER")
    print("==================================================================")

    os.makedirs(TREES_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Update table schema check constraint to allow 'family_trees'
    print("Updating unified_photo_catalog table schema to include 'family_trees'...")
    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unified_photo_catalog_new (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT CHECK(category IN ('people', 'documents', 'family_trees')),
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

    # 2. Identify all family tree records
    cur.execute("SELECT photo_id, category, normalized_filename, original_filename, local_image_path FROM unified_photo_catalog")
    all_photos = cur.fetchall()

    tree_records = []
    for pid, cat, norm_fn, orig_fn, lp in all_photos:
        is_tree, reason = is_family_tree(orig_fn, norm_fn)
        if is_tree:
            tree_records.append((pid, cat, norm_fn, orig_fn, lp, reason))

    print(f"Identified {len(tree_records)} family trees to separate.")

    moved_count = 0
    db_updated = 0

    for pid, old_cat, norm_fn, orig_fn, lp, reason in tree_records:
        src_path = os.path.join(PRESERVATION_DIR, lp)
        dest_path = os.path.join(TREES_DIR, norm_fn)
        new_rel_path = f"assets/archive_media/family_trees/{norm_fn}"

        # If file exists at src_path
        if os.path.exists(src_path) or os.path.islink(src_path):
            # If it's a symlink (e.g. from deduplication)
            if os.path.islink(src_path):
                target = os.readlink(src_path)
                os.remove(src_path)
                # If target was relative to src_path dir, calculate target relative to dest_path
                # Best to resolve absolute target then make relative to dest_path
                abs_target = os.path.normpath(os.path.join(os.path.dirname(src_path), target))
                rel_target = os.path.relpath(abs_target, os.path.dirname(dest_path))
                os.symlink(rel_target, dest_path)
            else:
                shutil.move(src_path, dest_path)

            # Leave a backwards-compatibility relative symlink at old path
            rel_backlink = os.path.relpath(dest_path, os.path.dirname(src_path))
            try:
                os.symlink(rel_backlink, src_path)
            except OSError:
                pass

            moved_count += 1

        # Re-point source symlinks in mitsawokett_photos/ to the new destination
        for sub in ["people", "documents"]:
            sub_sym = os.path.join(ASSETS_DIR, "mitsawokett_photos", sub, orig_fn)
            if os.path.islink(sub_sym) or os.path.exists(sub_sym):
                try:
                    os.remove(sub_sym)
                    rel_sym = os.path.relpath(dest_path, os.path.dirname(sub_sym))
                    os.symlink(rel_sym, sub_sym)
                except OSError:
                    pass

        root_sym = os.path.join(ASSETS_DIR, "mitsawokett_photos", orig_fn)
        if os.path.islink(root_sym) or os.path.exists(root_sym):
            try:
                os.remove(root_sym)
                rel_sym = os.path.relpath(dest_path, os.path.dirname(root_sym))
                os.symlink(rel_sym, root_sym)
            except OSError:
                pass

        # Update Database
        cur.execute("""
            UPDATE unified_photo_catalog
            SET category = 'family_trees', document_type = 'family_tree', local_image_path = ?
            WHERE photo_id = ?
        """, (new_rel_path, pid))
        db_updated += 1

    conn.commit()

    # Category breakdown
    cur.execute("SELECT category, COUNT(*) FROM unified_photo_catalog GROUP BY category")
    cat_summary = cur.fetchall()

    conn.close()

    print(f"\n[Separation Summary]")
    print(f"  - Files moved/symlinked into family_trees/ : {moved_count}")
    print(f"  - Database records updated to family_trees : {db_updated}")
    print(f"\nNew Archive Category Breakdown:")
    for c, cnt in cat_summary:
        print(f"  - {c:15}: {cnt}")

    # Audit symlinks
    print("\n[Verifying Symlink Integrity Across Archive...]")
    broken = []
    total_symlinks = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.islink(fp):
                total_symlinks += 1
                if not os.path.exists(fp):
                    broken.append(fp)

    print(f"  - Total symlinks checked : {total_symlinks}")
    print(f"  - Broken symlinks detected: {len(broken)} (Expected: 0)")
    if broken:
        for b in broken[:10]:
            print(f"    Broken: {b}")

    print("\n==================================================================")
    print("FAMILY TREES SEPARATION COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    run_separation()
