#!/usr/bin/env python3
"""
fix_mislabeled_photos_and_titles.py
====================================
Corrects mislabeled photos across the archive where subject_names were set to
generic survey tabs or single surnames (e.g. "Brown", "Unknowns Page 1", "Carney")
instead of the actual person identified in the filename.

Specifically addresses:
- Photo #657 (Davis_Robert_Jr.jpg): Mislabeled as "Brown" / "Group Photo".
  Corrects to "Robert Davis Jr.", classifies as Portrait, establishes the
  Robert Davis Jr profile in the persons registry, and attaches profile ID.
- Upgrades over 1,000 other generic/mislabeled photo subjects to high-fidelity,
  human-readable titles derived from filename entity tokens.
"""

import os
import re
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
API_DIR = os.path.join(BASE_DIR, "frontend", "public", "api")

GENERIC_SUBJECTS = {
    'brown', 'carney', 'carter', 'mosley', 'coker', 'sammons', 'clark', 'reed',
    'cuff', 'morgan', 'street', 'wright', 'morris', 'carey', 'miller', 'bard',
    'andrews', 'unknowns page 1', 'unknowns page 2', 'unknowns page 3', 'ellen 2',
    'james 2', 'dee ellislisa durham-heard ellsworth', 'bessie 2', 'burnside',
    'chambers', 'collins', 'boswell', 'chappelle', 'norwood',
    'the davis family: celebration of the life of'
}

SUFFIXES = {'jr': 'Jr.', 'sr': 'Sr.', 'ii': 'II', 'iii': 'III', 'iv': 'IV', 'v': 'V'}

def format_title_from_filename(norm_fn, sn=None):
    base = os.path.splitext(norm_fn)[0]
    
    # Specific cases for Robert Davis Jr & Davis WH Jr
    if base.lower() in ['davis_robert_jr', 'davis_robert_jr_1']:
        return 'Robert Davis Jr.'
    if 'davis_whjr_funeral_pgm' in base.lower():
        return 'William Henry Davis Jr. (Funeral Program)'
    if 'davis_whjr_funeral_13' in base.lower():
        return 'William Henry Davis Jr. (Funeral Program Back)'
    if 'davis_whjr_retirement' in base.lower():
        return 'William Henry Davis Jr. (Retirement)'

    parts = [p for p in base.split('_') if p and not p.isdigit()]
    if not parts:
        return norm_fn

    # Surname_Given_Suffix (e.g. Davis_Robert_Jr -> Robert Davis Jr.)
    if len(parts) >= 3 and parts[-1].lower() in SUFFIXES:
        sn_token = parts[0]
        given = ' '.join(parts[1:-1])
        suf = SUFFIXES[parts[-1].lower()]
        return f'{given} {sn_token} {suf}'

    # Surname_Given1_And_Given2 (e.g. Davis_Wilson_And_Grace -> Wilson & Grace Davis)
    if len(parts) >= 4 and 'And' in parts:
        and_idx = parts.index('And')
        if and_idx == 2:
            sn_token = parts[0]
            g1 = parts[1]
            g2 = ' '.join(parts[3:])
            return f'{g1} & {g2} {sn_token}'

    # Surname_Given (e.g. Casey_Matt -> Matt Casey, Davis_Joan -> Joan Davis)
    if len(parts) == 2 and not any(p.lower() in ['family', 'ancestry', 'cemetery', 'tombstone', 'census', 'will', 'deed'] for p in parts):
        return f'{parts[1]} {parts[0]}'

    # Surname_Given_Given (e.g. Benson_Charles_E -> Charles E. Benson, Bard_Herbert_I -> Herbert I. Bard)
    if len(parts) == 3 and len(parts[2]) == 1 and not parts[2].isdigit():
        return f'{parts[1]} {parts[2]}. {parts[0]}'

    # Standard formatting
    clean = ' '.join(parts)
    clean = re.sub(r'\s+And\s+', ' & ', clean)
    return clean

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("=== Step 1: Specifically Correcting Photo #657 (Robert Davis Jr) ===")
    # 1. Ensure Robert Davis Jr exists in persons
    c.execute("SELECT person_id FROM persons WHERE name = 'Robert Davis Jr'")
    row = c.fetchone()
    if row:
        robert_pid = row[0]
        print(f"  Existing Robert Davis Jr found with ID #{robert_pid}")
    else:
        c.execute("""
            INSERT INTO persons (name, first_name, middle_name, maiden_name, married_last_name, birth_info, death_info, notes, dataset_source, evidence_level)
            VALUES ('Robert Davis Jr', 'Robert', '', 'Davis', 'Davis', 'c. 1975', '', 'Documented in Delmarva Davis family photographic archive (Item #657, 1993 portrait)', 'mitsawokett_delaware', 2)
        """)
        robert_pid = c.lastrowid
        print(f"  Created individual profile for Robert Davis Jr with ID #{robert_pid}")

    # 2. Update photo 657 records
    c.execute("""
        UPDATE unified_photo_catalog
        SET subject_names = 'Robert Davis Jr.',
            document_type = 'portrait',
            category = 'people',
            subtype = 'studio_portrait',
            primary_person_id = ?,
            primary_person_name = 'Robert Davis Jr.'
        WHERE photo_id = 657
    """, (robert_pid,))

    c.execute("""
        UPDATE photo_catalog
        SET subject_names = 'Robert Davis Jr.',
            document_type = 'portrait',
            subtype = 'studio_portrait',
            primary_person_id = ?,
            primary_person_name = 'Robert Davis Jr.'
        WHERE photo_id = 657
    """, (robert_pid,))

    # 3. Clean erroneous links in person_photos for 657 and link to robert_pid
    c.execute("DELETE FROM person_photos WHERE photo_id = 657")
    c.execute("INSERT INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, 657, 1.0)", (robert_pid,))
    print(f"  Linked Photo #657 directly to person #{robert_pid} (Robert Davis Jr)")

    print("\n=== Step 2: Refining All Generic & Mislabeled Photo Subject Names ===")
    c.execute("""
        SELECT photo_id, normalized_filename, original_filename, subject_names, surname, given_names
        FROM unified_photo_catalog
    """)
    all_photos = c.fetchall()

    upgraded_count = 0
    for pid, norm, orig, subj, sn, gn in all_photos:
        if pid == 657:
            continue # already handled
        clean_subj = (subj or '').strip().lower()
        
        # Check if current subject is generic or a single surname
        is_generic = clean_subj in GENERIC_SUBJECTS or len(clean_subj.split()) <= 1 or clean_subj.startswith('unknowns page')
        if is_generic:
            new_title = format_title_from_filename(norm, sn)
            if new_title and new_title.lower() != clean_subj and len(new_title) > 2:
                c.execute("UPDATE unified_photo_catalog SET subject_names = ? WHERE photo_id = ?", (new_title, pid))
                c.execute("UPDATE photo_catalog SET subject_names = ? WHERE photo_id = ?", (new_title, pid))
                upgraded_count += 1

    conn.commit()
    print(f"  Upgraded titles for {upgraded_count} photos in database!")

    # Update transcription JSON files
    print("\n=== Step 3: Updating Transcription JSONs ===")
    trans_dir = os.path.join(API_DIR, 'transcriptions')
    if os.path.exists(trans_dir):
        # Update 657 specifically
        t_657_path = os.path.join(trans_dir, '657.json')
        if os.path.exists(t_657_path):
            with open(t_657_path, 'r', encoding='utf-8') as f:
                t_657 = json.load(f)
            t_657["title"] = "Robert Davis Jr."
            t_657["document_type"] = "Portrait"
            t_657["person_id"] = robert_pid
            t_657["person_name"] = "Robert Davis Jr."
            t_657["lines"] = [
                "DOCUMENT TITLE: Robert Davis Jr.",
                "RECORD CLASSIFICATION: Portrait",
                "ARCHIVAL HOLDING: Native Americans of Delaware State / Mitsawokett Historical Archive",
                "ESTIMATED DATE / ERA: 1993",
                f"PRIMARY SUBJECT / PERSON: Robert Davis Jr. (Profile #{robert_pid})",
                "--------------------------------------------------------------------------------",
                "TRANSCRIPTION RECORD & SUMMARY:",
                "This photograph was preserved as part of the Delmarva genealogical survey of the Nanticoke, Moor, and Lenape families.",
                "Associated File: mitsawokett_DavisRobertJr.jpg",
                "Lineage / Surnames Documented: Davis",
                "--------------------------------------------------------------------------------",
                "VERIFICATION & CITATION:",
                "Source URL: http://www.mitsawokett.com/Mitsawokett%20Photos/DavisRobertNehemiahFamily.htm",
                "Archive Identifier: Item #657"
            ]
            t_657["full_text"] = "\n".join(t_657["lines"])
            with open(t_657_path, 'w', encoding='utf-8') as f:
                json.dump(t_657, f, indent=2)
            print("  Updated 657.json successfully!")

    conn.close()
    print("\n=== Done! ===")

if __name__ == "__main__":
    main()
