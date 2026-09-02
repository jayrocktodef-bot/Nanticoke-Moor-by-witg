#!/usr/bin/env python3
"""
sort_mitsawokett_photos.py
==========================
Organizes all photo assets in preservation_output/assets/mitsawokett_photos
into two structured subdirectories:
  - people/    : Portraits, couples, families, reunions, school classes, church groups
  - documents/ : Primary records, vital certificates, censuses, obituaries, military/pension
                 records, legal indentures, wills/deeds/probate, bible records, lineage charts,
                 news clippings, cemetery tombstones/markers, and site document scans.

Features:
1. Moves each asset into people/ or documents/.
2. Creates relative symlinks at the parent level (mitsawokett_photos/<filename>) pointing
   into people/<filename> or documents/<filename> to preserve zero-breakage backwards compatibility.
3. Updates SQLite database records in genealogy_preservation.db:
   - photo_catalog.local_image_path
   - face_embeddings.image_path
   - media_assets.local_path
4. Synchronizes frontend/public/assets/mitsawokett_photos with the same organized subfolders.
"""

import os
import re
import shutil
import sqlite3
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
PHOTOS_DIR = os.path.join(PRESERVATION_DIR, "assets", "mitsawokett_photos")
PEOPLE_DIR = os.path.join(PHOTOS_DIR, "people")
DOCS_DIR = os.path.join(PHOTOS_DIR, "documents")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")
FRONTEND_PHOTOS_DIR = os.path.join(SCRIPT_DIR, "frontend", "public", "assets", "mitsawokett_photos")

DOC_EXTENSIONS = {".pdf", ".html", ".htm", ".txt", ".svg"}

DOC_TERMS_EXACT = [
    "-dc-", "_dc_", "-mc-", "_mc_", "-bc-", "_bc_",
    "death cert", "death_cert", "death-cert", "death certificate",
    "birth cert", "birth_cert", "birth-cert", "birth certificate",
    "marriage cert", "marriage_cert", "marriage-cert", "marriage certificate", "marriage license", "marriage_bond", "marriage bond",
    "census", "obit", "obituary", "pension", "civil_war", "civil war", "revwar", "enlistment",
    "draft_reg", "draft registration", "wwi registration", "wwi_registration", "wwii registration",
    "tombstone", "headstone", "gravestone", "cemetery", "grave marker", "grave stone", "cemetery_marker", "grave_marker", "grave_stone",
    "bible", "family_record", "family record", "church directory", "directory_18",
    "indenture", "apprentice", "bound_out", "bound out",
    "newspaper", "clipping", "news article", "news_article", "evening news", "councilorpaper",
    "funeral_program", "funeral program", "order_of_service", "order of service", "memorial program", "memorial_program",
    "lineage", "pedigree", "family_tree", "family tree", "descent", "numbered_outlines",
    "probate", "affidavit", "ss-5", "social security", "receipt", "taxassessment", "tax assessment", "tax_assessment",
    "land grant", "deed", "court record", "directory_18", "indexqueenannes", "marylandmarriages",
    "somenewjerseydeaths", "somepennsylvaniadeaths", "somewaynecountybmd", "generalcommunityrefs",
    "referenceworksofinterest", "migrationsfromdelaware"
]

def norm(s):
    s = urllib.parse.unquote(s or "")
    for rep in ["_20", "%20", "_", "-", "&", " ", ".", "'", '"', "(", ")", "[", "]", ",", "+"]:
        s = s.replace(rep, "")
    return s.lower()

def check_is_document(fname, unquoted, db_entry=None):
    ext = os.path.splitext(fname)[1].lower()
    if ext in DOC_EXTENSIONS:
        return True, f"extension_{ext}"

    for term in DOC_TERMS_EXACT:
        if term in unquoted:
            return True, f"keyword_{term}"

    # Specific regex patterns
    if re.search(r'(?:will[0-9]|wills[0-9]|_will_|_will\.|will of|probate|last will)', unquoted):
        return True, "regex_will"

    if re.search(r'(?:^|[-_ \(\[])graves?(?:[-_ \.\)\]]|$)', unquoted):
        return True, "regex_grave"

    if re.search(r'(?:^|[-_ \(\[])maps?(?:[-_ \.\)\]]|$)', unquoted):
        return True, "regex_map"

    if re.search(r'(?:marker|monument|stone_by|civil_war_marker|_stone\.|\.stone)', unquoted):
        return True, "regex_stone_monument"

    if re.search(r'porter\s*-\s*\d+', unquoted) or re.search(r'babcock\d*\s*-\s*\d+', unquoted) or "babcock1899" in unquoted:
        return True, "academic_report_page"

    if any(k in unquoted for k in ["weslager", "speck_report", "heite_report"]):
        return True, "academic_report_page"

    if re.search(r'[-_]land\d*', unquoted):
        return True, "land_plat"

    # Database catalog record match
    if db_entry:
        dtype = db_entry[2]
        if dtype in ["bible_record", "funeral_program", "legal_indenture", "military_record", "newspaper_clipping", "obituary", "vital_certificate", "tombstone"]:
            return True, f"db_type_{dtype}"

    # Web assets / site icons / non-person media
    if any(k in unquoted for k in ["_wbgs", "_wbg", "running_man", "container", "league_fallback", "email.fw", "featherbar", "indianrodmotif", "ind-footer", "mediafeed", "reuters", "huffpost", "the_independent", "stacker_642", "people.png", "gemini.png", "dims_thumbnail"]):
        return True, "web_asset_non_person"

    # Standalone building/church/house photos (without human subjects)
    if any(k in unquoted for k in ["forestgrovechurch", "forestgrovesdachurch", "immanuelunionchurch", "israelumchurchsign", "carneyjohnhouse."]):
        return True, "building_no_person"

    return False, "person"

def run_sorting():
    print("==================================================================")
    print("STARTING MITSAWOKETT PHOTO ARCHIVE REORGANIZATION")
    print("==================================================================")

    os.makedirs(PEOPLE_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT local_image_path, media_type, document_type, title_or_caption, source_url FROM photo_catalog")
    catalog_rows = cur.fetchall()

    db_by_exact = {}
    db_by_norm = {}
    for r in catalog_rows:
        p = r[0]
        fn = os.path.basename(p)
        db_by_exact[fn] = r
        db_by_norm[norm(fn)] = r

    # Scan all files directly in PHOTOS_DIR (skip subdirectories)
    items = sorted(os.listdir(PHOTOS_DIR))
    files_to_sort = [f for f in items if os.path.isfile(os.path.join(PHOTOS_DIR, f)) and not os.path.islink(os.path.join(PHOTOS_DIR, f))]

    print(f"Discovered {len(files_to_sort)} files in {PHOTOS_DIR}")

    people_moved = 0
    docs_moved = 0
    moved_mapping = {} # filename -> ('people' or 'documents')

    for fname in files_to_sort:
        src_path = os.path.join(PHOTOS_DIR, fname)
        unquoted = urllib.parse.unquote(fname.lower()).replace("_20", " ").replace("%20", " ")
        db_entry = db_by_exact.get(fname) or db_by_norm.get(norm(fname))

        is_doc, reason = check_is_document(fname, unquoted, db_entry)
        target_subdir = "documents" if is_doc else "people"
        target_dir = DOCS_DIR if is_doc else PEOPLE_DIR
        dest_path = os.path.join(target_dir, fname)

        # Move file into subfolder
        shutil.move(src_path, dest_path)

        # Create relative symlink at the root level for zero breakage
        rel_link_target = os.path.join(target_subdir, fname)
        try:
            os.symlink(rel_link_target, src_path)
        except OSError as e:
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

    # Update database records
    print("\n[Updating Database Records]")
    db_updates_photo_catalog = 0
    db_updates_face_embeddings = 0
    db_updates_media_assets = 0

    # 1. photo_catalog
    cur.execute("SELECT photo_id, local_image_path FROM photo_catalog")
    for pid, img_path in cur.fetchall():
        if not img_path:
            continue
        fn = os.path.basename(img_path)
        # Check if this filename was moved or corresponds to a moved file
        target_sub = moved_mapping.get(fn)
        if not target_sub:
            # Check normalized match
            for m_fn, m_sub in moved_mapping.items():
                if norm(m_fn) == norm(fn):
                    target_sub = m_sub
                    break

        if target_sub:
            new_path = f"assets/mitsawokett_photos/{target_sub}/{fn}"
            if new_path != img_path:
                cur.execute("UPDATE photo_catalog SET local_image_path = ? WHERE photo_id = ?", (new_path, pid))
                db_updates_photo_catalog += 1

    # 2. face_embeddings
    cur.execute("SELECT id, image_path FROM face_embeddings")
    for eid, img_path in cur.fetchall():
        if not img_path:
            continue
        fn = os.path.basename(img_path)
        target_sub = moved_mapping.get(fn)
        if not target_sub:
            for m_fn, m_sub in moved_mapping.items():
                if norm(m_fn) == norm(fn):
                    target_sub = m_sub
                    break

        if target_sub:
            new_path = f"assets/mitsawokett_photos/{target_sub}/{fn}"
            if new_path != img_path:
                cur.execute("UPDATE face_embeddings SET image_path = ? WHERE id = ?", (new_path, eid))
                db_updates_face_embeddings += 1

    # 3. media_assets
    cur.execute("SELECT id, local_path FROM media_assets WHERE local_path LIKE '%mitsawokett_photos%'")
    for mid, l_path in cur.fetchall():
        if not l_path:
            continue
        fn = os.path.basename(l_path)
        target_sub = moved_mapping.get(fn)
        if not target_sub:
            for m_fn, m_sub in moved_mapping.items():
                if norm(m_fn) == norm(fn):
                    target_sub = m_sub
                    break

        if target_sub:
            new_path = f"assets/mitsawokett_photos/{target_sub}/{fn}"
            if new_path != l_path:
                cur.execute("UPDATE media_assets SET local_path = ? WHERE id = ?", (new_path, mid))
                db_updates_media_assets += 1

    conn.commit()
    conn.close()

    print(f"  - photo_catalog paths updated  : {db_updates_photo_catalog}")
    print(f"  - face_embeddings paths updated: {db_updates_face_embeddings}")
    print(f"  - media_assets paths updated   : {db_updates_media_assets}")

    # Synchronize frontend/public/assets/mitsawokett_photos if it exists
    if os.path.exists(FRONTEND_PHOTOS_DIR):
        print("\n[Synchronizing Frontend Public Assets]")
        frontend_people = os.path.join(FRONTEND_PHOTOS_DIR, "people")
        frontend_docs = os.path.join(FRONTEND_PHOTOS_DIR, "documents")
        os.makedirs(frontend_people, exist_ok=True)
        os.makedirs(frontend_docs, exist_ok=True)

        frontend_files = [f for f in os.listdir(FRONTEND_PHOTOS_DIR) if os.path.isfile(os.path.join(FRONTEND_PHOTOS_DIR, f)) and not os.path.islink(os.path.join(FRONTEND_PHOTOS_DIR, f))]
        f_moved = 0
        for f in frontend_files:
            sub = moved_mapping.get(f)
            if not sub:
                for m_fn, m_sub in moved_mapping.items():
                    if norm(m_fn) == norm(f):
                        sub = m_sub
                        break
            if not sub:
                unq = urllib.parse.unquote(f.lower()).replace("_20", " ").replace("%20", " ")
                is_doc, _ = check_is_document(f, unq)
                sub = "documents" if is_doc else "people"

            dest_dir = frontend_docs if sub == "documents" else frontend_people
            src = os.path.join(FRONTEND_PHOTOS_DIR, f)
            dest = os.path.join(dest_dir, f)
            shutil.move(src, dest)
            try:
                os.symlink(os.path.join(sub, f), src)
            except OSError:
                pass
            f_moved += 1
        print(f"  - Frontend assets organized into people/ and documents/: {f_moved}")

    print("\n==================================================================")
    print("REORGANIZATION AND DATABASE SYNCHRONIZATION COMPLETE")
    print("==================================================================")

if __name__ == "__main__":
    run_sorting()
