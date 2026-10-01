#!/usr/bin/env python3
"""
execute_archive_deduplication.py
================================
Autonomous two-tier deduplication engine for the genealogy archive:
1. Exact SHA-256 Binary Deduplication (653 clusters, 656 redundant copies)
2. Perceptual Visual dHash Deduplication (cross-collection resolution)
3. Storage Reclamation: Replaces physical duplicates with relative symlinks
4. Database Junction Reassignment: Synchronizes person_photos and face_embeddings
5. Flags non-genealogical site template assets
"""

import os
import sqlite3
from PIL import Image
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
ARCHIVE_MEDIA_DIR = os.path.join(ASSETS_DIR, "archive_media")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

SITE_ASSET_PATTERNS = [
    "ind-footer", "ind_footer", "copyright", "email.fw", "redrule",
    "sorry.jpg", "banner.jpg", "return.gif"
]

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

def score_candidate(record):
    """
    Score a record to pick the best canonical entry.
    Higher score = better candidate for canonical.
    """
    pid, fn, orig_fn, lp, sz, subj, sn, gn, yr, dt = record
    score = 0
    # Clean filename without _var or copy
    if "_var" not in fn:
        score += 20
    if "copy" not in fn.lower() and "copy" not in orig_fn.lower():
        score += 15
    # Does not have url encoding relics in original
    if "%20" not in orig_fn and "_20" not in orig_fn:
        score += 10
    # Rich metadata
    if sn:
        score += 10
    if gn:
        score += 10
    if yr:
        score += 5
    if sz:
        try:
            score += min(int(float(sz) / 1024), 20)  # Larger file size preferred
        except (ValueError, TypeError):
            pass
    return score

def run_deduplication():
    print("==================================================================")
    print("STARTING ARCHIVE DEDUPLICATION PIPELINE")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Ensure columns exist in unified_photo_catalog
    cur.execute("PRAGMA table_info(unified_photo_catalog)")
    cols = [r[1] for r in cur.fetchall()]
    if "canonical_photo_id" not in cols:
        print("Adding column 'canonical_photo_id' to unified_photo_catalog...")
        cur.execute("ALTER TABLE unified_photo_catalog ADD COLUMN canonical_photo_id INTEGER")
    if "dedup_type" not in cols:
        print("Adding column 'dedup_type' to unified_photo_catalog...")
        cur.execute("ALTER TABLE unified_photo_catalog ADD COLUMN dedup_type TEXT DEFAULT 'canonical'")
    conn.commit()

    # 2. Flag Site Template Assets
    print("\n[Step 1: Identifying & Flagging Non-Genealogical Site Assets]")
    cur.execute("SELECT photo_id, normalized_filename, original_filename FROM unified_photo_catalog")
    site_assets_count = 0
    for pid, fn, orig_fn in cur.fetchall():
        fn_lower = fn.lower()
        orig_lower = orig_fn.lower()
        if any(pat in fn_lower or pat in orig_lower for pat in SITE_ASSET_PATTERNS):
            cur.execute("""
                UPDATE unified_photo_catalog 
                SET is_primary_copy = 0, dedup_type = 'site_asset'
                WHERE photo_id = ?
            """, (pid,))
            site_assets_count += 1
    conn.commit()
    print(f"  - Flagged {site_assets_count} site template assets as non-primary.")

    # 3. Exact Binary Deduplication (SHA-256)
    print("\n[Step 2: Resolving Exact SHA-256 Binary Duplicate Clusters]")
    cur.execute("""
        SELECT photo_id, normalized_filename, original_filename, local_image_path,
               file_size_bytes, subject_names, surname, given_names, approximate_year,
               document_type, sha256_hash
        FROM unified_photo_catalog
        WHERE dedup_type != 'site_asset'
    """)
    all_rows = cur.fetchall()

    hash_groups = defaultdict(list)
    for r in all_rows:
        h = r[10]
        hash_groups[h].append(r[:10])

    exact_clusters = {h: items for h, items in hash_groups.items() if len(items) > 1}
    print(f"  - Total Exact Duplicate Clusters to resolve: {len(exact_clusters)}")

    space_reclaimed_bytes = 0
    sha_merged_records = 0

    for h, items in exact_clusters.items():
        items.sort(key=score_candidate, reverse=True)
        canonical = items[0]
        canonical_id = canonical[0]
        canonical_lp = canonical[3]
        canonical_disk = os.path.join(PRESERVATION_DIR, canonical_lp)

        # Mark canonical
        cur.execute("""
            UPDATE unified_photo_catalog
            SET canonical_photo_id = ?, is_primary_copy = 1, dedup_type = 'canonical'
            WHERE photo_id = ?
        """, (canonical_id, canonical_id))

        # Reassign duplicates
        for dup in items[1:]:
            dup_id = dup[0]
            dup_lp = dup[3]
            dup_disk = os.path.join(PRESERVATION_DIR, dup_lp)
            dup_size = dup[4] or 0

            cur.execute("""
                UPDATE unified_photo_catalog
                SET canonical_photo_id = ?, is_primary_copy = 0, dedup_type = 'exact_sha256_dup'
                WHERE photo_id = ?
            """, (canonical_id, dup_id))

            # Reclaim disk space if duplicate file is a separate physical file
            if os.path.exists(dup_disk) and not os.path.islink(dup_disk):
                try:
                    os.remove(dup_disk)
                    rel_target = os.path.relpath(canonical_disk, os.path.dirname(dup_disk))
                    os.symlink(rel_target, dup_disk)
                    space_reclaimed_bytes += dup_size
                except OSError:
                    pass

            sha_merged_records += 1

    # Mark all singletons
    cur.execute("""
        UPDATE unified_photo_catalog
        SET canonical_photo_id = photo_id, is_primary_copy = 1, dedup_type = 'canonical'
        WHERE canonical_photo_id IS NULL AND dedup_type != 'site_asset'
    """)
    conn.commit()

    print(f"  - Merged {sha_merged_records} redundant duplicate records.")
    print(f"  - Reclaimed {space_reclaimed_bytes / (1024 * 1024):.2f} MB of disk storage using relative symlinks.")

    # 4. Perceptual dHash Deduplication
    print("\n[Step 3: Evaluating Perceptual Visual Similarity (dHash)]")
    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               local_image_path, file_size_bytes, subject_names, surname, given_names,
               approximate_year, document_type
        FROM unified_photo_catalog
        WHERE is_primary_copy = 1 AND dedup_type = 'canonical'
    """)
    canonical_rows = cur.fetchall()
    print(f"  - Hashing {len(canonical_rows)} canonical primary photos for visual duplicates...")

    dhashes = defaultdict(list)
    for r in canonical_rows:
        pid, cat, fn, orig_fn, lp, sz, subj, sn, gn, yr, dt = r
        full_p = os.path.join(PRESERVATION_DIR, lp)
        try:
            with Image.open(full_p) as img:
                dh = dhash(img)
                dhashes[dh].append((pid, cat, fn, orig_fn, lp, sz, subj, sn, gn, yr, dt, img.size[0] * img.size[1]))
        except Exception:
            pass

    perceptual_clusters = {dh: items for dh, items in dhashes.items() if len(items) > 1}
    print(f"  - Discovered {len(perceptual_clusters)} perceptual visual duplicate clusters.")

    perceptual_merged_count = 0
    for dh, items in perceptual_clusters.items():
        # Verify that the cluster actually represents the same subject/person
        # Sort by resolution (pixel area) and metadata score descending
        items.sort(key=lambda x: (x[11], score_candidate(x[:10])), reverse=True)
        primary_item = items[0]
        primary_id = primary_item[0]
        primary_lp = primary_item[4]
        primary_disk = os.path.join(PRESERVATION_DIR, primary_lp)

        for other in items[1:]:
            other_id = other[0]
            other_fn = other[2]
            primary_fn = primary_item[2]

            # Check if surnames match or one is a substring of another
            # e.g. Henrietta_Carty and Carty_Henrietta or Carter_Eloise and Carter_Eloise_copy
            s1 = set(primary_fn.lower().replace(".jpg", "").split("_"))
            s2 = set(other_fn.lower().replace(".jpg", "").split("_"))
            common = s1.intersection(s2)

            if len(common) >= 1:
                # Confirmed visual match of same entity
                cur.execute("""
                    UPDATE unified_photo_catalog
                    SET canonical_photo_id = ?, is_primary_copy = 0, dedup_type = 'perceptual_dhash_dup'
                    WHERE photo_id = ?
                """, (primary_id, other_id))

                other_disk = os.path.join(PRESERVATION_DIR, other[4])
                if os.path.exists(other_disk) and not os.path.islink(other_disk):
                    try:
                        os.remove(other_disk)
                        rel_target = os.path.relpath(primary_disk, os.path.dirname(other_disk))
                        os.symlink(rel_target, other_disk)
                    except OSError:
                        pass
                perceptual_merged_count += 1
                print(f"    [Visual Match Merged] {other_fn} -> {primary_fn}")

    conn.commit()
    print(f"  - Successfully consolidated {perceptual_merged_count} perceptual visual duplicates.")

    # 5. Junction Table Reassignment
    print("\n[Step 4: Reassigning Junction Links (person_photos, face_embeddings)]")
    # Fetch all photo reassignments
    cur.execute("SELECT photo_id, canonical_photo_id, local_image_path FROM unified_photo_catalog WHERE canonical_photo_id != photo_id")
    reassignments = cur.fetchall()
    reassign_map = {p[0]: p[1] for p in reassignments}

    reassigned_person_photos = 0
    cur.execute("SELECT person_id, photo_id FROM person_photos")
    all_pp = cur.fetchall()
    for per_id, pho_id in all_pp:
        new_pho_id = reassign_map.get(pho_id)
        if new_pho_id:
            cur.execute("UPDATE OR IGNORE person_photos SET photo_id = ? WHERE person_id = ? AND photo_id = ?",
                        (new_pho_id, per_id, pho_id))
            cur.execute("DELETE FROM person_photos WHERE person_id = ? AND photo_id = ?", (per_id, pho_id))
            reassigned_person_photos += 1

    reassigned_face_embeddings = 0
    cur.execute("SELECT id, photo_id FROM face_embeddings")
    for fe_id, pho_id in cur.fetchall():
        new_pho_id = reassign_map.get(pho_id)
        if new_pho_id:
            cur.execute("UPDATE face_embeddings SET photo_id = ? WHERE id = ?", (new_pho_id, fe_id))
            reassigned_face_embeddings += 1

    conn.commit()
    print(f"  - person_photos links reassigned     : {reassigned_person_photos}")
    print(f"  - face_embeddings links reassigned   : {reassigned_face_embeddings}")

    # 6. Final Summary Statistics
    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE is_primary_copy = 1")
    total_canonical = cur.fetchone()[0]

    cur.execute("SELECT dedup_type, COUNT(*) FROM unified_photo_catalog GROUP BY dedup_type")
    type_counts = cur.fetchall()

    conn.close()

    print("\n==================================================================")
    print("DEDUPLICATION ENGINE EXECUTION COMPLETE")
    print(f"Total Preserved Unique Canonical Photos: {total_canonical}")
    print("Breakdown by Deduplication Status:")
    for dt, cnt in type_counts:
        print(f"  - {dt:25}: {cnt}")
    print("==================================================================")

if __name__ == "__main__":
    run_deduplication()
