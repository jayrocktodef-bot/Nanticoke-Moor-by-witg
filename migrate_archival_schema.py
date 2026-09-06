#!/usr/bin/env python3
"""
migrate_archival_schema.py
==========================
Migrates database schema to integrate the new Archival Cataloging & Preservation Engine schema:
- asset_type: 'photograph' | 'monument' | 'document' | 'composite_ephemera' | 'disqualified'
- subtype: specific physical/documentary subtype
- confidence_score: REAL (0.0 - 1.0)
- contains_face: BOOLEAN (0 or 1)
- face_context: 'primary_subject' | 'document_embedded' | 'none'
- routing_target: 'photos' | 'obituaries' | 'documents' | 'monuments' | 'quarantine'
- transcription: TEXT (verbatim transcription / OCR)
- dates_mentioned: TEXT (JSON array string, e.g. '["1964"]')
- flag_for_human_review: BOOLEAN (DEFAULT 0)
"""

import os
import json
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

NEW_COLUMNS = {
    "asset_type": "TEXT",
    "subtype": "TEXT",
    "confidence_score": "REAL DEFAULT 1.0",
    "contains_face": "INTEGER DEFAULT 0",
    "face_context": "TEXT DEFAULT 'none'",
    "routing_target": "TEXT",
    "transcription": "TEXT",
    "dates_mentioned": "TEXT",
    "flag_for_human_review": "INTEGER DEFAULT 0"
}

def add_columns_if_missing(cur, table, columns):
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    added = 0
    for col_name, col_def in columns.items():
        if col_name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
            added += 1
            print(f"  ✓ Added column `{col_name}` to `{table}`")
    if added == 0:
        print(f"  - All columns already present in `{table}`")

def backfill_catalog_metadata(cur):
    print("\nBackfilling archival classification metadata from existing records...")

    # 1. Backfill unified_photo_catalog
    cur.execute("""
        SELECT photo_id, category, document_type, normalized_filename, original_filename,
                approximate_year, subject_names
        FROM unified_photo_catalog
    """)
    rows = cur.fetchall()

    updated = 0
    for pid, cat, doc_type, norm_fn, orig_fn, approx_yr, subj in rows:
        combined = f"{norm_fn} {orig_fn or ''} {subj or ''}".lower()

        # Extract 4-digit years
        years = sorted(list(set(re.findall(r'\b(1[789]\d\d|20[012]\d)\b', combined))))
        if approx_yr and approx_yr.isdigit() and approx_yr not in years:
            years.append(approx_yr)
        dates_json = json.dumps(years) if years else "[]"

        # Defaults
        asset_type = "photograph"
        subtype = "candid_snapshot"
        contains_face = 1
        face_context = "primary_subject"
        routing_target = "photos"
        flag_review = 0

        # Category logic
        if cat == "tombstones" or "tombstone" in combined or "headstone" in combined or "cemetery" in combined:
            asset_type = "monument"
            subtype = "headstone"
            contains_face = 0
            face_context = "none"
            routing_target = "monuments"

        elif cat == "documents" or "census" in combined or "deed" in combined or "will" in combined or "certificate" in combined or "ssa" in combined:
            asset_type = "document"
            contains_face = 0
            face_context = "none"
            routing_target = "documents"

            if "census" in combined:
                subtype = "census_page"
            elif "death" in combined and "cert" in combined:
                subtype = "death_certificate"
            elif "marriage" in combined:
                subtype = "marriage_record"
            elif "birth" in combined and "cert" in combined:
                subtype = "birth_record"
            elif "ssa" in combined or "social" in combined:
                subtype = "ss_application"
            elif "deed" in combined or "land" in combined:
                subtype = "land_deed"
            elif "will" in combined or "probate" in combined:
                subtype = "probate_will"
            else:
                subtype = doc_type or "legal_record"

        elif cat == "family_trees" or "ancestry" in combined or "lineage" in combined or "descent" in combined or "tree" in combined:
            asset_type = "document"
            subtype = "lineage_chart"
            contains_face = 0
            face_context = "none"
            routing_target = "documents"

        elif "program" in combined or "obit" in combined or "funeral" in combined:
            asset_type = "composite_ephemera"
            subtype = "funeral_program" if "program" in combined else "obituary_clipping"
            contains_face = 1
            face_context = "document_embedded"
            routing_target = "obituaries"

        elif cat == "people":
            asset_type = "photograph"
            contains_face = 1
            face_context = "primary_subject"
            routing_target = "photos"

            if "group" in combined or "and" in norm_fn.lower() or "family" in combined or "&" in norm_fn:
                subtype = "family_group"
            elif "school" in combined or "class" in combined:
                subtype = "school_class_photo"
            elif "speck" in combined or "smithsonian" in combined:
                subtype = "field_study_photo"
            else:
                subtype = "studio_portrait"

        cur.execute("""
            UPDATE unified_photo_catalog
            SET asset_type = ?,
                subtype = ?,
                confidence_score = 1.0,
                contains_face = ?,
                face_context = ?,
                routing_target = ?,
                dates_mentioned = ?,
                flag_for_human_review = ?
            WHERE photo_id = ?
        """, (asset_type, subtype, contains_face, face_context, routing_target, dates_json, flag_review, pid))
        updated += 1

    print(f"  ✓ Backfilled {updated} records in `unified_photo_catalog`")

    # 2. Sync into photo_catalog
    cur.execute("""
        UPDATE photo_catalog
        SET media_type = (SELECT u.asset_type FROM unified_photo_catalog u WHERE u.photo_id = photo_catalog.photo_id),
            document_type = (SELECT u.subtype FROM unified_photo_catalog u WHERE u.photo_id = photo_catalog.photo_id)
        WHERE photo_id IN (SELECT photo_id FROM unified_photo_catalog)
    """)
    print("  ✓ Synchronized media_type and document_type in `photo_catalog`")

def main():
    print("==================================================================")
    print("MIGRATING SCHEMA: ARCHIVAL CATALOGING & PRESERVATION ENGINE")
    print("==================================================================")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n[Step 1] Adding New Archival Columns to `unified_photo_catalog`...")
    add_columns_if_missing(cur, "unified_photo_catalog", NEW_COLUMNS)

    print("\n[Step 2] Adding Archival Columns to `photo_catalog`...")
    add_columns_if_missing(cur, "photo_catalog", {
        "asset_type": "TEXT",
        "subtype": "TEXT",
        "confidence_score": "REAL DEFAULT 1.0",
        "contains_face": "INTEGER DEFAULT 0",
        "face_context": "TEXT DEFAULT 'none'",
        "routing_target": "TEXT",
        "dates_mentioned": "TEXT",
        "flag_for_human_review": "INTEGER DEFAULT 0"
    })

    conn.commit()

    print("\n[Step 3] Backfilling and Classifying Existing Holdings...")
    backfill_catalog_metadata(cur)
    conn.commit()

    conn.close()
    print("\nArchival schema migration successfully applied to database!")

if __name__ == "__main__":
    main()
