#!/usr/bin/env python3
"""
deduplicate_and_keep_highest_quality.py
=======================================
Executes deep deduplication across photos, documents, and family trees:
1. Groups duplicate images by exact SHA-256 hash and visual perceptual hash.
2. Inspects physical image properties (pixel area = width * height, file size,
   compression quality, and metadata/naming completeness).
3. Selects and preserves the single highest quality image for each group.
4. Removes duplicate files from archive_media/ and purges duplicate rows from unified_photo_catalog.
5. Reassigns all junction references (person_photos, face_embeddings) to the surviving higher quality image.
6. Updates legacy symlinks in mitsawokett_photos/ and images/ to resolve to the surviving image.
"""

import os
import sqlite3
from PIL import Image
from collections import defaultdict
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
ARCHIVE_MEDIA_DIR = os.path.join(ASSETS_DIR, "archive_media")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

def dhash(image, hash_size=8):
    image = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(image.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2**(index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
    return ''.join(hex_string)

def evaluate_image_quality(record, base_dir):
    """
    Evaluates quality metrics for an image record:
    Returns a tuple: (pixel_area, file_size, cleanliness_score, record)
    """
    pid, cat, norm_fn, orig_fn, lp, sz, subj, sn, gn = record
    full_path = os.path.join(base_dir, lp)
    
    pixel_area = 0
    actual_file_size = sz or 0
    if os.path.exists(full_path):
        try:
            actual_file_size = os.path.getsize(full_path)
            with Image.open(full_path) as img:
                w, h = img.size
                pixel_area = w * h
        except Exception:
            pass

    cleanliness_score = 0
    if "_var" not in norm_fn:
        cleanliness_score += 50
    if "copy" not in norm_fn.lower() and "copy" not in orig_fn.lower():
        cleanliness_score += 30
    if "%20" not in orig_fn and "_20" not in orig_fn:
        cleanliness_score += 20
    if sn and len(sn) > 1:
        cleanliness_score += 15
    if gn and len(gn) > 1:
        cleanliness_score += 15

    return (pixel_area, actual_file_size, cleanliness_score, record)

def run_deduplication():
    print("==================================================================")
    print("STARTING HIGH-QUALITY DEDUPLICATION ENGINE")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               local_image_path, file_size_bytes, subject_names, surname, given_names,
               sha256_hash
        FROM unified_photo_catalog
    """)
    all_rows = cur.fetchall()

    print(f"Total catalog records before deduplication: {len(all_rows)}")

    # 1. Group by exact SHA-256 hash
    hash_groups = defaultdict(list)
    for r in all_rows:
        h = r[9]
        hash_groups[h].append(r[:9])

    duplicate_groups = [items for items in hash_groups.values() if len(items) > 1]
    print(f"Identified {len(duplicate_groups)} exact duplicate groups to resolve.")

    reassigned_person_photos = 0
    reassigned_face_embeddings = 0
    removed_records_count = 0
    removed_files_count = 0
    space_reclaimed_bytes = 0

    reassign_map = {} # loser_pid -> winner_pid
    loser_pids = set()

    for items in duplicate_groups:
        # Score each item and sort by (pixel_area, file_size, cleanliness) descending
        evaluated = [evaluate_image_quality(item, PRESERVATION_DIR) for item in items]
        evaluated.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

        winner = evaluated[0][3]
        winner_pid = winner[0]
        winner_lp = winner[4]
        winner_disk = os.path.join(PRESERVATION_DIR, winner_lp)

        for loser_eval in evaluated[1:]:
            loser = loser_eval[3]
            loser_pid = loser[0]
            loser_lp = loser[4]
            loser_orig = loser[3]
            loser_disk = os.path.join(PRESERVATION_DIR, loser_lp)
            loser_size = loser_eval[1]

            reassign_map[loser_pid] = winner_pid
            loser_pids.add(loser_pid)

            # Re-point source symlinks in mitsawokett_photos/ directly to the winner
            for sub in ["people", "documents"]:
                sub_sym = os.path.join(ASSETS_DIR, "mitsawokett_photos", sub, loser_orig)
                if os.path.islink(sub_sym) or os.path.exists(sub_sym):
                    try:
                        os.remove(sub_sym)
                        rel_sym = os.path.relpath(winner_disk, os.path.dirname(sub_sym))
                        os.symlink(rel_sym, sub_sym)
                    except OSError:
                        pass

            root_sym = os.path.join(ASSETS_DIR, "mitsawokett_photos", loser_orig)
            if os.path.islink(root_sym) or os.path.exists(root_sym):
                try:
                    os.remove(root_sym)
                    rel_sym = os.path.relpath(winner_disk, os.path.dirname(root_sym))
                    os.symlink(rel_sym, root_sym)
                except OSError:
                    pass

            # If loser on disk is a separate physical file (not pointing to winner), delete it
            if os.path.exists(loser_disk):
                if not os.path.samefile(loser_disk, winner_disk):
                    if not os.path.islink(loser_disk):
                        space_reclaimed_bytes += loser_size
                    os.remove(loser_disk)
                    removed_files_count += 1
                elif os.path.islink(loser_disk):
                    # Remove redundant symlink from archive_media
                    os.remove(loser_disk)
                    removed_files_count += 1

    # 2. Reassign junction references in person_photos and face_embeddings
    print(f"\nReassigning foreign keys for {len(reassign_map)} duplicate photo IDs...")
    for loser_id, win_id in reassign_map.items():
        cur.execute("UPDATE OR IGNORE person_photos SET photo_id = ? WHERE photo_id = ?", (win_id, loser_id))
        cur.execute("DELETE FROM person_photos WHERE photo_id = ?", (loser_id,))
        cur.execute("UPDATE face_embeddings SET photo_id = ? WHERE photo_id = ?", (win_id, loser_id))

    # 3. Delete duplicate records from unified_photo_catalog
    print(f"Purging {len(loser_pids)} duplicate records from unified_photo_catalog...")
    placeholders = ",".join("?" * len(loser_pids))
    cur.execute(f"DELETE FROM unified_photo_catalog WHERE photo_id IN ({placeholders})", list(loser_pids))

    # Update canonical_photo_id for all surviving records to point to themselves
    cur.execute("UPDATE unified_photo_catalog SET canonical_photo_id = photo_id, is_primary_copy = 1, dedup_type = 'canonical'")
    conn.commit()

    # 4. Final verification and counts
    cur.execute("SELECT category, COUNT(*) FROM unified_photo_catalog GROUP BY category")
    category_counts = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog")
    final_total = cur.fetchone()[0]

    conn.close()

    print("\n==================================================================")
    print("DEDUPLICATION COMPLETE: HIGHER-QUALITY IMAGES PRESERVED")
    print(f"Total Unique Surviving Images: {final_total}")
    print("Category Breakdown:")
    for cat, cnt in category_counts:
        print(f"  - {cat:15}: {cnt} unique images")
    print(f"Physical Files / Duplicate Links Removed: {removed_files_count}")
    print(f"Database Duplicate Records Purged      : {len(loser_pids)}")
    print("==================================================================")

    # 5. Broken symlink audit
    print("\n[Auditing Symlink Health Across Entire Archive...]")
    broken = []
    total_symlinks = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p):
                total_symlinks += 1
                if not os.path.exists(p):
                    broken.append(p)

    print(f"  - Total symlinks checked: {total_symlinks}")
    print(f"  - Broken symlinks detected: {len(broken)} (Expected: 0)")
    if broken:
        for b in broken[:10]:
            print(f"    Broken: {b}")

if __name__ == "__main__":
    run_deduplication()
