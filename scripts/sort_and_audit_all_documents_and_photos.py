#!/usr/bin/env python3
"""
sort_and_audit_all_documents_and_photos.py

Comprehensive Audit & Sorting Pipeline:
1. Re-categorizes all media across unified_photo_catalog and photo_catalog into their true archival categories:
   - 'people': Portraits, group photos, graduation portraits, family snapshots.
   - 'documents': Primary source records (census, wills, deeds, vitals, marriages, bibles, church records, obituaries, maps).
   - 'tombstones': Cemetery memorials, grave markers, tombstones.
   - 'family_trees': Lineage charts, ancestry diagrams, pedigree trees (*ancestry.jpg).
2. Physically migrates and syncs files into preservation_output/assets/archive_media/{category}/.
3. Ingests any unindexed census and archival records into catalogs.
4. Enforces the Person Photo Invariant:
   - Sets transcription = NULL (no spurious OCR text on portraits).
   - Normalizes names (surname NOT first).
   - Retains source, name, birth/death dates, and primary person linkages.
5. Transcribes all documents and tombstones lacking text using the ONNX PP-OCRv4 engine.
6. Updates document_records for full primary source provenance.
"""

import os
import sys
import sqlite3
import shutil
import re
import json
import time
import hashlib
import numpy as np
import cv2

BASE_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper'
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')
MEDIA_BASE = os.path.join(BASE_DIR, 'preservation_output', 'assets', 'archive_media')
CENSUS_DIR = os.path.join(BASE_DIR, 'preservation_output', 'ancestry_documents', 'delaware_census')
PUCKHAM_DIR = os.path.join(BASE_DIR, 'preservation_output', 'scraped_media', 'puckham_collection')

# Import ONNX OCR engine from our upgraded pipeline
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from onnx_archive_pipeline import PPOCRTextEngine, SCRFDFaceDetector

CATEGORIES = ['people', 'documents', 'tombstones', 'family_trees']

# Known Surnames for name normalization
SURNAMES = {
    'harmon', 'johnson', 'clark', 'davis', 'street', 'mosley', 'moseley', 'norwood',
    'wright', 'ridgeway', 'drain', 'draine', 'jackson', 'carney', 'cuff', 'durham',
    'greenage', 'grinage', 'seeney', 'miller', 'burton', 'sammons', 'sockum',
    'perkins', 'morris', 'hansley', 'hanzer', 'puckham', 'bookram', 'pierce',
    'hitchens', 'sterrett', 'morgan', 'conner', 'hall', 'reed', 'cott', 'dean',
    'butler', 'felts', 'newton', 'munce', 'muntz', 'pettijohn', 'turner', 'swain',
    'bedell', 'bowles', 'duffy', 'moore', 'ellis', 'kearney', 'steward'
}


def normalize_person_name(raw_name):
    """Normalize names where surname is placed first or formatted with underscores/commas."""
    if not raw_name:
        return raw_name, None, None

    clean = re.sub(r'\.(?:jpg|jpeg|png|gif)$', '', raw_name, flags=re.I)
    clean = clean.replace('_', ' ').replace('-', ' ').strip()

    ignore_words = {'&', ' and ', 'family', 'portraits', 'group', 'survey', 'overview', 'historical', 'community', 'son of', 'wife of', 'father of', 'monument', 'stone'}
    has_ignore = any(w in clean.lower() for w in ignore_words)
    
    if ',' in clean and not has_ignore and clean.count(',') == 1:
        parts = [p.strip() for p in clean.split(',', 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            if len(parts[0].split()) <= 2:
                norm = f"{parts[1]} {parts[0]}"
                return norm, parts[0], parts[1]

    tokens = clean.split()
    if len(tokens) >= 2 and not has_ignore:
        first_token = tokens[0].lower()
        if first_token in SURNAMES:
            surname = tokens[0]
            remainder = tokens[1:]

            year = None
            if remainder and re.match(r'^(?:1[789]\d\d|20\d\d)$', remainder[-1]):
                year = remainder.pop()

            suffix = None
            if remainder and remainder[-1].lower() in ('sr', 'jr', 'ii', 'iii', 'iv', 'sr.', 'jr.'):
                suffix = remainder.pop()
                if not suffix.endswith('.'):
                    suffix += '.'

            given = ' '.join(remainder)
            given = given.replace(' And ', ' & ')
            norm = f"{given} {surname}"

            if suffix:
                norm = f"{norm} {suffix}"
            if year:
                norm = f"{norm} ({year})"

            return norm, surname, given

    return clean, None, None


def determine_category_and_typology(nfn, ofn, current_cat, current_dtype):
    """Determine true archival category, document type, asset type, and subtype."""
    fn = (nfn or '').lower()
    orig = (ofn or '').lower()

    # 1. Family Trees (pedigree charts, *ancestry.jpg)
    if 'ancestry.jpg' in fn or (('tree' in fn or 'pedigree' in fn or 'lineage' in fn) and 'street' not in fn and 'wood' not in fn and 'doc' not in fn):
        return 'family_trees', 'family_tree', 'diagram', 'pedigree_chart', 'family_trees'

    # 2. Tombstones / Monuments
    tombstone_patterns = [
        r'\b(?:tombstone|headstone|grave|cem|cemetery|monument|marker)\b',
        r'24_jul_\d+_2005',
        r'10_sep_.*cem',
        r'israel_cem',
        r'zadock_muntz_stone',
        r'civil_war_marker'
    ]
    if any(re.search(pat, fn) or re.search(pat, orig) for pat in tombstone_patterns):
        if not re.search(r'\b(?:records|deed|will|census|probate)\b', fn):
            return 'tombstones', 'tombstone', 'monument', 'cemetery_memorial', 'monuments'

    # 3. Documents
    doc_patterns = [
        (r'\b(?:census)\b', 'census_record', 'document', 'federal_census'),
        (r'\b(?:will|probate|testament|estate)\b', 'last_will_testament', 'document', 'probate_will'),
        (r'\b(?:deed|patent|plat|indenture|indent)\b', 'land_deed', 'document', 'land_deed'),
        (r'\b(?:deathcert|death_certificate)\b', 'death_certificate', 'document', 'death_certificate'),
        (r'\b(?:birthcert|birth_certificate)\b', 'birth_certificate', 'document', 'birth_certificate'),
        (r'\b(?:marriage|marriage_certificate|marriagebond)\b', 'marriage_certificate', 'document', 'marriage_bond'),
        (r'\b(?:births|deaths|marriages|grinagebirths|grinagedeaths)\b', 'vital_certificate', 'document', 'vital_register'),
        (r'\b(?:bible)\b', 'bible_record', 'document', 'family_bible'),
        (r'\b(?:ss_application|ss-5|application)\b', 'ss_application', 'document', 'ss_application'),
        (r'\b(?:military|pension|enlistment)\b', 'military_pension', 'document', 'military_record'),
        (r'\b(?:obit|obituary|death_announcement|funeral|memorial_program)\b', 'obituary_program', 'document', 'obituary'),
        (r'\b(?:fork_branch_records|church_directory|directory_1887)\b', 'church_record', 'document', 'church_register'),
        (r'survey_22[0-6]\.jpg', 'historical_document', 'document', 'survey_monograph'),
        (r'\b(?:map|plaque|medal|tax_list)\b', 'historical_document', 'document', 'historical_artifact')
    ]
    for pat, dt, at, st in doc_patterns:
        if re.search(pat, fn) or re.search(pat, orig):
            return 'documents', dt, at, st, 'documents'

    # 4. People (Portraits, group photos, graduation portraits, survey portraits 227-248)
    if 'grad' in fn or current_dtype in ('portrait', 'graduation_portrait', 'group_photo') or 'survey_2' in fn or current_cat == 'people':
        dt = 'portrait' if 'group' not in fn and current_dtype != 'group_photo' else 'group_photo'
        st = 'graduation_portrait' if 'grad' in fn else ('group_portrait' if dt == 'group_photo' else 'historical_portrait')
        return 'people', dt, 'photograph', st, 'photos'

    # Fallback to current values
    return current_cat or 'documents', current_dtype or 'historical_document', 'document', 'historical_document', 'documents'


def find_file_on_disk(filename):
    """Finds the actual file path across known media directories."""
    candidates = [
        os.path.join(MEDIA_BASE, 'people', filename),
        os.path.join(MEDIA_BASE, 'documents', filename),
        os.path.join(MEDIA_BASE, 'family_trees', filename),
        os.path.join(MEDIA_BASE, 'tombstones', filename),
        os.path.join(PUCKHAM_DIR, filename),
        os.path.join(CENSUS_DIR, filename),
        os.path.join(BASE_DIR, 'assets', 'archive_media', 'people', filename),
        os.path.join(BASE_DIR, 'assets', 'archive_media', 'documents', filename),
        os.path.join(BASE_DIR, 'assets', 'archive_media', 'family_trees', filename),
        os.path.join(BASE_DIR, 'assets', 'archive_media', 'tombstones', filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def run_pipeline():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure directories exist
    for cat in CATEGORIES:
        os.makedirs(os.path.join(MEDIA_BASE, cat), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, 'frontend', 'public', 'assets', 'archive_media', cat), exist_ok=True)

    print("=================================================================")
    print("STEP 1: Re-categorizing and Sorting All Cataloged Assets")
    print("=================================================================")

    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               document_type, asset_type, subtype, local_image_path,
               subject_names, primary_person_id, primary_person_name
        FROM unified_photo_catalog
    """)
    records = cur.fetchall()

    recategorized_count = 0
    relocated_files_count = 0

    for r in records:
        pid, old_cat, nfn, ofn, old_dt, old_at, old_st, old_path, subj, p_id, p_name = r
        new_cat, new_dt, new_at, new_st, new_target = determine_category_and_typology(nfn, ofn, old_cat, old_dt)

        # Expected canonical path
        expected_db_path = f"assets/archive_media/{new_cat}/{nfn}"
        target_disk_path = os.path.join(MEDIA_BASE, new_cat, nfn)
        frontend_target_path = os.path.join(BASE_DIR, 'frontend', 'public', 'assets', 'archive_media', new_cat, nfn)

        # Physical file check & relocation
        current_disk_file = find_file_on_disk(nfn)
        if current_disk_file:
            if os.path.abspath(current_disk_file) != os.path.abspath(target_disk_path):
                shutil.copy2(current_disk_file, target_disk_path)
                shutil.copy2(current_disk_file, frontend_target_path)
                relocated_files_count += 1
            elif not os.path.exists(frontend_target_path):
                shutil.copy2(target_disk_path, frontend_target_path)

        # Database record update
        if (new_cat != old_cat or new_dt != old_dt or old_path != expected_db_path or
            new_at != old_at or new_st != old_st):
            cur.execute("""
                UPDATE unified_photo_catalog
                SET category = ?, document_type = ?, asset_type = ?, subtype = ?,
                    routing_target = ?, local_image_path = ?
                WHERE photo_id = ?
            """, (new_cat, new_dt, new_at, new_st, new_target, expected_db_path, pid))

            cur.execute("""
                UPDATE photo_catalog
                SET media_type = ?, document_type = ?, asset_type = ?, subtype = ?,
                    routing_target = ?, local_image_path = ?
                WHERE photo_id = ?
            """, (new_target, new_dt, new_at, new_st, new_target, expected_db_path, pid))
            recategorized_count += 1

    conn.commit()
    print(f"  ✓ Processed {len(records)} media items.")
    print(f"  ✓ Re-categorized & updated: {recategorized_count} assets.")
    print(f"  ✓ Physically relocated to correct directory: {relocated_files_count} files.")

    print("\n=================================================================")
    print("STEP 2: Indexing Any Remaining Unindexed Census Documents")
    print("=================================================================")
    import glob
    census_jpgs = glob.glob(os.path.join(CENSUS_DIR, '*.jpg'))
    newly_indexed_census = 0

    for cpath in census_jpgs:
        base = os.path.basename(cpath)
        cur.execute("SELECT photo_id FROM unified_photo_catalog WHERE normalized_filename = ? OR original_filename = ?", (base, base))
        if not cur.fetchone():
            target_path = os.path.join(MEDIA_BASE, 'documents', base)
            frontend_target = os.path.join(BASE_DIR, 'frontend', 'public', 'assets', 'archive_media', 'documents', base)
            shutil.copy2(cpath, target_path)
            shutil.copy2(cpath, frontend_target)

            file_size = os.path.getsize(target_path)
            with open(target_path, 'rb') as f:
                sha256 = hashlib.sha256(f.read()).hexdigest()
            title = f"Sussex County Delaware Federal Census Record ({base})"
            db_rel_path = f"assets/archive_media/documents/{base}"

            cur.execute("""
                INSERT INTO unified_photo_catalog (
                    category, normalized_filename, original_filename, local_image_path,
                    file_size_bytes, sha256_hash, mime_type, subject_names, approximate_year,
                    document_type, dataset_source, asset_type, subtype, routing_target,
                    contains_face, is_primary_copy
                ) VALUES (
                    'documents', ?, ?, ?, ?, ?, 'image/jpeg', ?, 'Historical Census',
                    'census_record', 'Delaware Federal Census Records', 'document', 'federal_census', 'documents',
                    0, 1
                )
            """, (base, base, db_rel_path, file_size, sha256, title))
            new_pid = cur.lastrowid

            cur.execute("""
                INSERT INTO photo_catalog (
                    photo_id, title_or_caption, subject_names, approximate_year,
                    local_image_path, dataset_source, media_type, document_type,
                    asset_type, subtype, routing_target, contains_face
                ) VALUES (
                    ?, ?, ?, 'Historical Census', ?, 'Delaware Federal Census Records',
                    'documents', 'census_record', 'document', 'federal_census', 'documents', 0
                )
            """, (new_pid, title, title, db_rel_path))

            cur.execute("""
                INSERT OR IGNORE INTO document_records (
                    photo_id, doc_typology, title, record_date, notes
                ) VALUES (
                    ?, 'census_record', ?, 'Historical Census', 'Sussex County Delaware Federal Census schedule page'
                )
            """, (new_pid, title))
            newly_indexed_census += 1

    conn.commit()
    print(f"  ✓ Newly indexed census documents: {newly_indexed_census}")

    print("\n=================================================================")
    print("STEP 3: Enforcing Person Photo Invariant (Clean Source, Name, Dates, NO OCR Dumps)")
    print("=================================================================")

    # Load person lookup for name, birth, death dates
    cur.execute("""
        SELECT person_id, name, first_name, maiden_name, married_last_name, birth_info, death_info
        FROM persons
    """)
    person_lookup = {}
    for p in cur.fetchall():
        pid, nm, fn, mn, mln, b, d = p
        person_lookup[pid] = {
            "name": nm, "first": fn, "maiden": mn, "surname": mln, "birth": b, "death": d
        }
        clean_k = re.sub(r'[^a-zA-Z0-9 ]', '', (nm or '').lower()).strip()
        person_lookup[clean_k] = pid

    cur.execute("""
        SELECT photo_id, normalized_filename, subject_names, primary_person_id, primary_person_name
        FROM unified_photo_catalog
        WHERE category = 'people'
    """)
    people_photos = cur.fetchall()

    cleaned_people_count = 0
    renamed_people_count = 0

    for r in people_photos:
        pid, nfn, subj, primary_pid, primary_pname = r

        # 1. Clear text transcriptions from all person photos
        cur.execute("UPDATE unified_photo_catalog SET transcription = NULL WHERE photo_id = ? AND transcription IS NOT NULL", (pid,))
        cur.execute("UPDATE photo_catalog SET transcript = NULL WHERE photo_id = ? AND transcript IS NOT NULL", (pid,))
        cleaned_people_count += 1

        # 2. Normalize surname-first in subject_names
        if subj and not nfn.startswith('Survey_'):
            norm_subj, sname, gname = normalize_person_name(subj)
            if sname and gname and norm_subj != subj:
                cur.execute("UPDATE unified_photo_catalog SET subject_names = ?, surname = ?, given_names = ? WHERE photo_id = ?",
                            (norm_subj, sname, gname, pid))
                cur.execute("UPDATE photo_catalog SET subject_names = ?, married_surname = ? WHERE photo_id = ?",
                            (norm_subj, sname, pid))
                renamed_people_count += 1

    conn.commit()
    print(f"  ✓ Ensured 0 OCR dumps across {cleaned_people_count} person photos.")
    print(f"  ✓ Normalized {renamed_people_count} person names from surname-first format.")

    print("\n=================================================================")
    print("STEP 4: Auditing & Transcribing Documents and Tombstones via ONNX PP-OCRv4")
    print("=================================================================")

    # Initialize ONNX OCR engine
    print("  ... Initializing ONNX PP-OCRv4 text detection and recognition engines ...")
    ocr_engine = PPOCRTextEngine()

    cur.execute("""
        SELECT photo_id, category, normalized_filename, local_image_path, document_type, subject_names
        FROM unified_photo_catalog
        WHERE (category = 'documents' OR category = 'tombstones')
          AND (transcription IS NULL OR TRIM(transcription) = '')
    """)
    untranscribed = cur.fetchall()
    print(f"  ✓ Found {len(untranscribed)} documents/tombstones requiring direct text transcription.")

    transcribed_count = 0
    t0 = time.time()

    for idx, row in enumerate(untranscribed):
        pid, cat, nfn, rel_path, dtype, title = row
        img_path = find_file_on_disk(nfn)
        if not img_path:
            continue

        try:
            img_bgr = cv2.imread(img_path)
            if img_bgr is None:
                continue

            results = ocr_engine.transcribe_image(img_bgr)
            if results:
                # Combine detected lines
                lines = [f"{r['text']} (conf: {r['confidence']})" for r in results]
                raw_text = "\n".join([r['text'] for r in results])
                avg_conf = float(np.mean([r['confidence'] for r in results]))

                # Save directly into DB
                cur.execute("UPDATE unified_photo_catalog SET transcription = ?, confidence_score = ? WHERE photo_id = ?", (raw_text, avg_conf, pid))
                cur.execute("UPDATE photo_catalog SET transcript = ?, transcription_confidence = ? WHERE photo_id = ?", (raw_text, avg_conf, pid))

                # Insert or update document_records
                cur.execute("""
                    INSERT OR REPLACE INTO document_records (
                        photo_id, doc_typology, title, record_date, notes
                    ) VALUES (
                        ?, ?, ?, 'Preserved Record', ?
                    )
                """, (pid, dtype or 'historical_document', title or nfn, raw_text[:500]))

                transcribed_count += 1
                if transcribed_count % 10 == 0:
                    conn.commit()
                    print(f"    -> Transcribed {transcribed_count}/{len(untranscribed)} documents (elapsed: {time.time()-t0:.1f}s)", flush=True)

        except Exception as e:
            continue

    conn.commit()
    print(f"  ✓ Direct ONNX OCR Transcription completed for {transcribed_count} primary documents and tombstones.", flush=True)

    print("\n=================================================================")
    print("STEP 5: Auditing Database & Generating Verified Statistics")
    print("=================================================================")

    cur.execute("SELECT category, COUNT(*) FROM unified_photo_catalog GROUP BY category")
    cat_dist = cur.fetchall()
    print("  Final Verified Category Distribution in Unified Catalog:")
    for cat, count in cat_dist:
        print(f"    - {cat:15}: {count:5} assets")

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE category = 'people' AND transcription IS NOT NULL")
    people_with_ocr = cur.fetchone()[0]
    print(f"  - People photos with OCR text dumps (must be 0): {people_with_ocr}")

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE category = 'documents' AND transcription IS NOT NULL")
    docs_with_trans = cur.fetchone()[0]
    print(f"  - Documents with direct text transcription:       {docs_with_trans}")

    cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE category = 'tombstones' AND transcription IS NOT NULL")
    tombs_with_trans = cur.fetchone()[0]
    print(f"  - Tombstones with direct stone transcription:     {tombs_with_trans}")

    conn.close()
    print("\n✓ Pipeline execution finished successfully.")


if __name__ == '__main__':
    run_pipeline()
