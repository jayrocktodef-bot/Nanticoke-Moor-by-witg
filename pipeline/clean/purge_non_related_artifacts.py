#!/usr/bin/env python3
"""
Purge Non-Related & Accidentally Ingested Artifacts
===================================================
Systematically purges non-related scraping artifacts from the Lynn Jackson
genealogical preservation archive:
1. Purges non-genealogical pages (.gif binary, banner/bbar iframes, parked domain ad pages, directory listings).
2. Purges website section title graphics, watermark slices, and ghost records from photo catalogs.
3. Purges orphaned web button and banner references from media_assets.
4. Corrects corrupted grammatical sentence fragment pseudo-entities in persons table.
5. Deletes 0-byte legacy database placeholder.
6. Rebuilds SQLite FTS5 search index.
7. Refreshes canonical immutable DB snapshot and asserts OAIS RFC 8493 BagIt fixity.
"""

import os
import sys
import glob
import sqlite3
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PRESERVATION_DIR = os.path.join(PROJECT_ROOT, "preservation_output")
ASSETS_DIR = os.path.join(PRESERVATION_DIR, "assets")
FRONTEND_PUBLIC = os.path.join(PROJECT_ROOT, "frontend", "public")
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")
CANONICAL_DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation_canonical.db")

PURGE_PAGE_IDS = [1, 5, 6, 19, 153, 312, 337]

WEB_GRAPHICS_PIDS = [733, 861, 1526, 1870, 1925, 2607, 3372]
GHOST_PHOTO_PIDS = [2912, 2913, 3143, 3374, 3375, 3376, 3377, 3378, 3379, 3380]
ALL_PURGE_PIDS = WEB_GRAPHICS_PIDS + GHOST_PHOTO_PIDS

ORPHAN_MEDIA_IDS = [204, 704, 773, 1482, 2105, 2260]


def purge_pages(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("Step 1: Purging Non-Genealogical Pages...")
    q = ",".join("?" * len(PURGE_PAGE_IDS))
    pages = cur.execute(f"SELECT id, filename, title FROM pages WHERE id IN ({q})", PURGE_PAGE_IDS).fetchall()
    
    filenames = []
    for pid, fn, title in pages:
        print(f"  - Purging Page [{pid}]: {fn} ({title})")
        filenames.append(fn)

    # Delete from pages table
    cur.execute(f"DELETE FROM pages WHERE id IN ({q})", PURGE_PAGE_IDS)
    print(f"    ✓ Deleted {cur.rowcount} rows from pages.")

    # Delete corresponding source records
    if filenames:
        fn_q = ",".join("?" * len(filenames))
        cur.execute(f"DELETE FROM sources WHERE url IN ({fn_q})", filenames)
        print(f"    ✓ Deleted {cur.rowcount} matching sources.")

    # Remove corresponding JSON files if present
    for fn in filenames:
        for folder in ["records", "transcriptions"]:
            for base in [FRONTEND_PUBLIC, FRONTEND_DIST]:
                target_json = os.path.join(base, "api", folder, f"{fn}.json")
                if os.path.exists(target_json):
                    try:
                        os.remove(target_json)
                        print(f"    ✓ Removed {target_json}")
                    except Exception as e:
                        print(f"    Failed removing {target_json}: {e}")


def purge_photos(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\nStep 2: Purging Web Title Graphics & Ghost Records from Photo Catalog...")
    q = ",".join("?" * len(ALL_PURGE_PIDS))
    photos = cur.execute(f"""
        SELECT photo_id, category, normalized_filename, original_filename, local_image_path
        FROM unified_photo_catalog
        WHERE photo_id IN ({q})
    """, ALL_PURGE_PIDS).fetchall()

    files_removed = 0
    for pid, cat, norm_fn, orig_fn, lp in photos:
        print(f"  - Purging Photo [{pid}]: {norm_fn} (Orig: {orig_fn})")
        candidates = [
            os.path.join(PRESERVATION_DIR, lp) if lp else "",
            os.path.join(ASSETS_DIR, "archive_media", cat, norm_fn) if cat and norm_fn else "",
            os.path.join(FRONTEND_PUBLIC, "assets", "archive_media", cat, norm_fn) if cat and norm_fn else "",
            os.path.join(FRONTEND_DIST, "assets", "archive_media", cat, norm_fn) if cat and norm_fn else "",
            os.path.join(ASSETS_DIR, "mitsawokett_photos", orig_fn) if orig_fn else "",
            os.path.join(ASSETS_DIR, "mitsawokett_photos", "people", orig_fn) if orig_fn else "",
            os.path.join(ASSETS_DIR, "mitsawokett_photos", "documents", orig_fn) if orig_fn else "",
        ]
        for cpath in set(candidates):
            if cpath and (os.path.exists(cpath) or os.path.islink(cpath)):
                try:
                    os.remove(cpath)
                    files_removed += 1
                except Exception as e:
                    print(f"    Failed removing {cpath}: {e}")

    # Delete DB records
    cur.execute(f"DELETE FROM person_photos WHERE photo_id IN ({q})", ALL_PURGE_PIDS)
    pp_cnt = cur.rowcount
    cur.execute(f"DELETE FROM photo_surnames WHERE photo_id IN ({q})", ALL_PURGE_PIDS)
    ps_cnt = cur.rowcount
    cur.execute(f"DELETE FROM photo_catalog WHERE photo_id IN ({q})", ALL_PURGE_PIDS)
    pc_cnt = cur.rowcount
    cur.execute(f"DELETE FROM face_embeddings WHERE photo_id IN ({q})", ALL_PURGE_PIDS)
    fe_cnt = cur.rowcount
    cur.execute(f"DELETE FROM unified_photo_catalog WHERE photo_id IN ({q})", ALL_PURGE_PIDS)
    upc_cnt = cur.rowcount
    cur.execute(f"UPDATE unified_photo_catalog SET canonical_photo_id = photo_id WHERE canonical_photo_id IN ({q})", ALL_PURGE_PIDS)

    print(f"    ✓ Deleted {files_removed} physical image files/symlinks.")
    print(f"    ✓ Deleted from unified_photo_catalog: {upc_cnt} rows.")
    print(f"    ✓ Deleted from photo_catalog: {pc_cnt} rows.")
    print(f"    ✓ Deleted from photo_surnames: {ps_cnt} rows.")
    print(f"    ✓ Deleted from person_photos: {pp_cnt} rows.")
    print(f"    ✓ Deleted from face_embeddings: {fe_cnt} rows.")


def purge_media_assets(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\nStep 3: Purging Orphaned Web Buttons & Banners from media_assets...")
    q = ",".join("?" * len(ORPHAN_MEDIA_IDS))
    cur.execute(f"DELETE FROM media_assets WHERE id IN ({q})", ORPHAN_MEDIA_IDS)
    print(f"    ✓ Deleted {cur.rowcount} orphaned rows from media_assets.")


def reconcile_corrupted_persons(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\nStep 4: Reconciling Corrupted Grammatical Pseudo-Entity (Person 3087)...")
    cur.execute("""
        UPDATE persons
        SET name = 'Aaron Bass Jr.',
            first_name = 'Aaron',
            middle_name = 'Jr.',
            maiden_name = '',
            married_last_name = 'Bass',
            birth_info = NULL,
            death_info = NULL,
            notes = 'Mentioned in Bass family records (BassKLorraine.htm)'
        WHERE person_id = 3087
    """)
    print("    ✓ Person 3087 sanitized to 'Aaron Bass Jr.' (removed corrupted surname 'went' and bogus memorial).")


def cleanup_filesystem():
    print("\nStep 5: Cleaning up Filesystem Residuals...")
    dead_db = os.path.join(PRESERVATION_DIR, "genealogy.db")
    if os.path.exists(dead_db):
        os.remove(dead_db)
        print(f"    ✓ Removed 0-byte legacy database {dead_db}")


def rebuild_fts(conn: sqlite3.Connection):
    cur = conn.cursor()
    print("\nStep 6: Rebuilding SQLite FTS5 Corpus...")
    cur.execute("DROP TABLE IF EXISTS fts_genealogy_corpus")
    cur.execute("""
        CREATE VIRTUAL TABLE fts_genealogy_corpus USING fts5(
            doc_type UNINDEXED,
            source_id UNINDEXED,
            title,
            full_text,
            metadata,
            tokenize = 'porter unicode61'
        )
    """)

    cur.execute("""
        SELECT id, deceased_name, full_text, surviving_kin, birth_date, death_date, cemetery_location
        FROM obituaries
    """)
    for oid, dname, ftext, kin, bdate, ddate, cem in cur.fetchall():
        meta = f"Born: {bdate or ''} | Died: {ddate or ''} | Cemetery: {cem or ''} | Kin: {kin or ''}"
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('obituary', ?, ?, ?, ?)
        """, (str(oid), dname or "", ftext or "", meta))

    cur.execute("SELECT filename, title, text_content FROM pages")
    for fn, title, ctext in cur.fetchall():
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('page', ?, ?, ?, ?)
        """, (fn, title or fn, ctext or "", f"Filename: {fn}"))

    cur.execute("SELECT id, surname, given_names, maiden_or_full_name FROM ss_applications")
    for sid, sname, gnames, mname in cur.fetchall():
        full_n = f"{gnames or ''} {sname or ''}".strip()
        meta = f"Surname: {sname or ''} | Given: {gnames or ''} | Maiden/Full: {mname or ''}"
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('ss_application', ?, ?, ?, ?)
        """, (str(sid), full_n, f"Social Security Application for {full_n}. Name: {mname or full_n}.", meta))

    conn.commit()
    print("    ✓ FTS5 table rebuilt.")


def refresh_canonical_snapshot(conn: sqlite3.Connection):
    print("\nStep 7: Refreshing Canonical Database Snapshot...")
    if os.path.exists(CANONICAL_DB_PATH):
        os.remove(CANONICAL_DB_PATH)
    cur = conn.cursor()
    cur.execute(f"VACUUM INTO '{CANONICAL_DB_PATH}'")
    print(f"    ✓ Created canonical snapshot at {CANONICAL_DB_PATH}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        purge_pages(conn)
        purge_photos(conn)
        purge_media_assets(conn)
        reconcile_corrupted_persons(conn)
        cleanup_filesystem()
        rebuild_fts(conn)
        refresh_canonical_snapshot(conn)
        conn.commit()
    finally:
        conn.close()

    print("\nStep 8: Re-exporting Static Vercel API & Generating Production Build...")
    export_script = os.path.join(PROJECT_ROOT, "export_static_build_for_vercel.py")
    subprocess.run([sys.executable, export_script], cwd=PROJECT_ROOT, check=True)

    print("\nStep 9: Regenerating BagIt Package...")
    bagit_script = os.path.join(PROJECT_ROOT, "scripts", "generate_bagit_package.py")
    subprocess.run([sys.executable, bagit_script], cwd=PROJECT_ROOT, check=True)

    print("\nStep 10: Verifying BagIt Fixity...")
    verify_script = os.path.join(PROJECT_ROOT, "scripts", "verify_bagit_fixity.py")
    subprocess.run([sys.executable, verify_script], cwd=PROJECT_ROOT, check=True)

    print("\nNon-related artifact purge and fixity verification complete.")

if __name__ == "__main__":
    main()
