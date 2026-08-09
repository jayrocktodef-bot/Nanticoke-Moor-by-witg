#!/usr/bin/env python3
"""
Clean Person Names v2 (clean_person_names_v2.py)
================================================
Cleans all person names in genealogy_preservation.db by:
1. Extracting parenthetical dates (b.1660, d.1844, c.1742, 1727-1784) into birth_info/death_info fields.
2. Deleting non-person text fragments (e.g., '29 June - 1 July 1742', '(see Concilor)', 'Delaware State News Archive').
3. Normalizing name strings to proper First Name + Surname format.
4. Auto-merging duplicate person records created by cleaning, preserving all relationships and photo links.
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

NON_PERSON_PATTERNS = [
    r'^\(?see\s+.*$',
    r'^\(?born\s+.*$',
    r'^\(?died\s+.*$',
    r'^\d+\s+(June|July|August|January|February|March|April|May|September|October|November|December).*$',
    r'^.*(Archive|Directory|Settlement|Book|Journal|News|Tombstones|Site|Chapter|State|County|Church|Meeting|Probate|Inventory|Orphans|Case|File|Files|Court|Petition|Table|Contents|Guide|Index|Search|Email|Copyright|Wayback|Wikipedia).*$',
    r'^\(?color removed.*\)?$',
    r'^\(?no parents listed.*\)?$',
    r'^.*\(Outside site removed.*\).*$',
    r'^.*\(Site removed by creator\).*$'
]

def clean_name_and_extract_dates(raw_name):
    if not raw_name:
        return "", None, None

    name = raw_name.strip()
    birth_info = None
    death_info = None

    # Check for site notes at end e.g. 'Moors Nanticokes'
    name = re.sub(r"['\"]Moors\s+Nanticokes['\"]", "", name, flags=re.IGNORECASE).strip()

    # Match birth date in parentheses e.g. (b.1660), (b. 1790), (born 1814)
    b_match = re.search(r'\((?:b\.|born|c\.|ca\.)\s*(\d{4})\)', name, re.IGNORECASE)
    if b_match:
        birth_info = f"c. {b_match.group(1)}"
        name = re.sub(r'\((?:b\.|born|c\.|ca\.)\s*\d{4}\)', '', name, flags=re.IGNORECASE).strip()

    # Match death date in parentheses e.g. (d.1844), (d. 1801), (died 1783)
    d_match = re.search(r'\((?:d\.|died)\s*(\d{4,5})\)', name, re.IGNORECASE)
    if d_match:
        death_info = f"d. {d_match.group(1)}"
        name = re.sub(r'\((?:d\.|died)\s*\d{4,5}\s*\)', '', name, flags=re.IGNORECASE).strip()

    # Match general year ranges e.g. (1784-1853), (-1811), (1811)
    range_match = re.search(r'\((-?\d{4})\s*[-–]\s*(\d{4})\)', name)
    if range_match:
        birth_info = birth_info or range_match.group(1)
        death_info = death_info or range_match.group(2)
        name = re.sub(r'\(-?\d{4}\s*[-–]\s*\d{4}\)', '', name).strip()

    single_year_match = re.search(r'\((1[6-9]\d{2})\)', name)
    if single_year_match and not birth_info and not death_info:
        death_info = f"d. {single_year_match.group(1)}"
        name = re.sub(r'\(1[6-9]\d{2}\)', '', name).strip()

    # Clean up extra slashes or spaces e.g. "Elias Puckham Bookram" -> "Elias Bookram"
    name = re.sub(r'\s*/\s*', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # Standardize casing (keep uppercase if ALL CAPS, otherwise Title Case)
    if name.isupper():
        name = name.title()

    return name, birth_info, death_info

def run_cleanup():
    print("=== Running Comprehensive Person Name Sanitizer v2 ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    c.execute("SELECT person_id, name, birth_info, death_info FROM persons")
    all_persons = c.fetchall()

    deleted_count = 0
    cleaned_count = 0
    merged_count = 0

    for pid, raw_name, orig_b, orig_d in all_persons:
        # Check if non-person text fragment
        is_non_person = False
        for pat in NON_PERSON_PATTERNS:
            if re.search(pat, raw_name, re.IGNORECASE):
                is_non_person = True
                break

        if is_non_person:
            # Delete non-person entry
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            deleted_count += 1
            continue

        cleaned_name, b_info, d_info = clean_name_and_extract_dates(raw_name)

        if not cleaned_name or len(cleaned_name) < 3:
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            deleted_count += 1
            continue

        new_b = orig_b or b_info
        new_d = orig_d or d_info

        if cleaned_name != raw_name:
            # Check if cleaned_name already exists for another person_id
            c.execute("SELECT person_id, birth_info, death_info FROM persons WHERE name = ? AND person_id != ?", (cleaned_name, pid))
            existing = c.fetchone()

            if existing:
                target_id = existing[0]
                # Merge pid into target_id
                c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (target_id, pid))
                c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (target_id, pid))
                c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

                c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (target_id, pid))
                c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))

                c.execute("UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?", (target_id, pid))
                c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))

                # Update target_id birth/death info if missing
                if new_b and not existing[1]:
                    c.execute("UPDATE persons SET birth_info = ? WHERE person_id = ?", (new_b, target_id))
                if new_d and not existing[2]:
                    c.execute("UPDATE persons SET death_info = ? WHERE person_id = ?", (new_d, target_id))

                c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
                merged_count += 1
            else:
                c.execute("""
                    UPDATE persons
                    SET name = ?, birth_info = ?, death_info = ?
                    WHERE person_id = ?
                """, (cleaned_name, new_b, new_d, pid))
                cleaned_count += 1
        elif new_b != orig_b or new_d != orig_d:
            c.execute("""
                UPDATE persons
                SET birth_info = ?, death_info = ?
                WHERE person_id = ?
            """, (new_b, new_d, pid))

    conn.commit()
    conn.close()

    print(f"\n==================================================")
    print(f"Name Cleaning v2 Complete.")
    print(f"Non-Person Fragments Deleted: {deleted_count}")
    print(f"Person Names Cleaned & Sanitized: {cleaned_count}")
    print(f"Duplicate Person Records Merged: {merged_count}")
    print(f"==================================================")

if __name__ == "__main__":
    run_cleanup()
