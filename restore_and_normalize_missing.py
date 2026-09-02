#!/usr/bin/env python3
"""
restore_and_normalize_missing.py
================================
Restores the 39 files from git HEAD that were skipped during the previous partial run,
normalizes their filenames into archive_media/{people,documents}, updates database records,
and re-establishes valid symlinks.
"""

import os
import subprocess
import sqlite3
import hashlib
import urllib.parse
from merge_and_normalize_archive import normalize_filename
from sort_mitsawokett_photos import check_is_document

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
ARCHIVE_MEDIA_DIR = os.path.join(ASSETS_DIR, "archive_media")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

def compute_sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def run_restoration():
    print("==================================================================")
    print("RESTORING SKIPPED FILES FROM GIT HEAD & NORMALIZING")
    print("==================================================================")

    # Find broken symlinks
    broken_links = []
    unique_filenames = set()
    for root, dirs, files in os.walk(ASSETS_DIR):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p) and not os.path.exists(p):
                broken_links.append(p)
                unique_filenames.add(f)

    print(f"Discovered {len(broken_links)} broken symlinks representing {len(unique_filenames)} unique files.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT filename, title FROM pages")
    page_titles = dict(cur.fetchall())

    cur.execute("SELECT local_image_path, subject_names, maiden_name, married_surname, approximate_year, document_type, source_url FROM photo_catalog")
    meta_by_filename = {os.path.basename(r[0]): r for r in cur.fetchall() if r[0]}

    restored_count = 0
    records_to_insert = []

    for fname in sorted(unique_filenames):
        git_rel = f"preservation_output/assets/mitsawokett_photos/{fname}"
        res = subprocess.run(
            ["git", "show", f"HEAD:{git_rel}"],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if res.returncode != 0:
            print(f"  [WARN] Failed to read {fname} from git HEAD")
            continue

        file_bytes = res.stdout
        h = compute_sha256_bytes(file_bytes)
        sz = len(file_bytes)

        is_doc, _ = check_is_document(fname, urllib.parse.unquote(fname))
        cat = "documents" if is_doc else "people"
        dest_dir = os.path.join(ARCHIVE_MEDIA_DIR, cat)
        os.makedirs(dest_dir, exist_ok=True)

        meta = meta_by_filename.get(fname)
        meta_subj = meta[1] if meta else None
        norm_name = normalize_filename(cat, fname, page_titles, meta_subj)

        dest_file_path = os.path.join(dest_dir, norm_name)
        # Handle collision if needed
        cand_name = norm_name
        col_idx = 1
        name_no_ext, ext = os.path.splitext(norm_name)
        while os.path.exists(dest_file_path):
            cand_name = f"{name_no_ext}_var{col_idx}{ext}"
            dest_file_path = os.path.join(dest_dir, cand_name)
            col_idx += 1

        with open(dest_file_path, "wb") as f:
            f.write(file_bytes)

        rel_new_path = f"assets/archive_media/{cat}/{cand_name}"

        # Update symlinks
        # 1. in mitsawokett_photos/{people,documents}/<fname>
        src_sub_path = os.path.join(ASSETS_DIR, "mitsawokett_photos", cat, fname)
        if os.path.islink(src_sub_path) or os.path.exists(src_sub_path):
            try:
                os.remove(src_sub_path)
                rel_sym = os.path.relpath(dest_file_path, os.path.dirname(src_sub_path))
                os.symlink(rel_sym, src_sub_path)
            except OSError:
                pass

        # 2. in mitsawokett_photos/<fname>
        src_root_path = os.path.join(ASSETS_DIR, "mitsawokett_photos", fname)
        if os.path.islink(src_root_path) or os.path.exists(src_root_path):
            try:
                os.remove(src_root_path)
                rel_sym = os.path.relpath(dest_file_path, os.path.dirname(src_root_path))
                os.symlink(rel_sym, src_root_path)
            except OSError:
                pass

        # Database record
        surname = ""
        given_names = ""
        if cat == "people":
            name_tokens = name_no_ext.split("_")
            if len(name_tokens) >= 2:
                surname = name_tokens[0]
                given_names = " ".join(name_tokens[1:])
            elif len(name_tokens) == 1:
                surname = name_tokens[0]

        approx_year = meta[4] if meta else None
        doc_type = meta[5] if meta else ("portrait" if cat == "people" else "document")
        source_url = meta[6] if meta else None
        subject_names = meta[1] if meta else name_no_ext.replace("_", " ")

        # Check if hash already exists in unified_photo_catalog for deduplication
        cur.execute("SELECT photo_id, canonical_photo_id FROM unified_photo_catalog WHERE sha256_hash = ? AND is_primary_copy = 1", (h,))
        existing = cur.fetchone()
        if existing:
            can_id = existing[1] or existing[0]
            is_prim = 0
            dedup_t = "exact_sha256_dup"
            cid = f"cluster_{h[:12]}"
        else:
            can_id = None
            is_prim = 1
            dedup_t = "canonical"
            cid = None

        cur.execute("""
            INSERT INTO unified_photo_catalog (
                category, normalized_filename, original_filename, local_image_path,
                sha256_hash, file_size_bytes, mime_type, subject_names, surname,
                given_names, approximate_year, document_type, dataset_source,
                source_url, duplicate_cluster_id, is_primary_copy, canonical_photo_id, dedup_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cat, cand_name, fname, rel_new_path, h, sz,
            "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext.lstrip('.')}",
            subject_names, surname, given_names, approx_year, doc_type, "mitsawokett",
            source_url, cid, is_prim, can_id, dedup_t
        ))
        
        # If this was primary, set its canonical_photo_id to itself
        if is_prim:
            inserted_id = cur.lastrowid
            cur.execute("UPDATE unified_photo_catalog SET canonical_photo_id = ? WHERE photo_id = ?", (inserted_id, inserted_id))

        restored_count += 1
        print(f"  ✓ Restored & Normalized: {fname:45} -> {cand_name}")

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog")
    total_recs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE is_primary_copy = 1")
    total_canon = cur.fetchone()[0]
    conn.close()

    print(f"\nSuccessfully restored and normalized {restored_count} files.")
    print(f"Total catalog records: {total_recs}")
    print(f"Total primary canonical photos: {total_canon}")

    # Audit symlinks
    broken_after = []
    total_symlinks = 0
    for root, dirs, files in os.walk(ASSETS_DIR):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p):
                total_symlinks += 1
                if not os.path.exists(p):
                    broken_after.append(p)

    print(f"\nFinal Broken Symlink Audit:")
    print(f"  - Total symlinks checked: {total_symlinks}")
    print(f"  - Broken symlinks: {len(broken_after)} (Expected: 0)")

if __name__ == "__main__":
    run_restoration()
