#!/usr/bin/env python3
"""
Name Sanitization, Cleaning, & Flip-Flop Normalizer Engine (clean_person_names.py)
===================================================================================
1. Removes 'who', 'whose', 'who was', 'who died', 'who married' and sentence clause fragments from names.
2. Identifies and flips surname-first names (e.g., "Durham Enoch" -> "Enoch Durham").
3. Removes non-person sentence fragments ingested from raw HTML.
"""

import os
import sqlite3
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

KNOWN_SURNAMES = {
    "Durham", "Carney", "Harmon", "Jackson", "Morgan", "Coker", 
    "Dean", "Wright", "Sisco", "Carter", "Hansor", "Ridgeway", 
    "Sammons", "Seeney", "Clark", "Davis", "Norwood", "Counselor", 
    "Concilor", "Cuff", "Thompson", "Purnell", "Gould", "Cott", "Carty"
}

KNOWN_FIRST_NAMES = {
    "Enoch", "Sarah", "Thomas", "William", "John", "Ann", "Anne", "Mary", 
    "Charles", "James", "Elizabeth", "Robert", "George", "Alexander", 
    "David", "Henry", "Joseph", "Samuel", "Rachel", "Hannah", "Hester", 
    "Lydia", "Martha", "Rebecca", "Benjamin", "Daniel", "Edward", "Frank",
    "Grace", "Ida", "Lola", "Mabel", "Nelson", "Oscar", "Peter", "Ruth",
    "Walter", "Asbury", "Asher", "Bartholomew", "Snowden", "Clinton", "Eloise"
}

GARBAGE_FRAGMENTS = [
    "state Delaware was", "Sample was", "It is said that the", "but we know she had at least one child",
    "this child was Howard HARDCASTLE and indeed", "no proof that he was the", "He was the same minister who",
    "Letters of Administration on the estate of John Morgan deceased were granted to Joseph Stafford of Talbot County in the state of Maryland who",
    "We know she could not have been Hester Concilor who was still", "do have some SAMMONS who have",
    "most of whom", "most of whom are", "who had been", "who is believed to have been the", "who married",
    "who was the", "who were", "and who was possibly the", "the Jesse Dean who died prior to", "the Jesse who married",
    "the elder John Sisco who died in", "wheelwright who", "who (who died between", "Sisco Mailing List"
]

def clean_name_string(raw_name):
    if not raw_name:
        return ""

    name = raw_name.strip()

    # 1. Check exact garbage fragments
    if name in GARBAGE_FRAGMENTS or len(name) > 80:
        return ""

    # 2. Strip leading prefix noise
    name = re.sub(r'^(Living next door with|he married|is he the|and|the)\s+', '', name, flags=re.I)

    # 3. Strip trailing 'who ...' relative clauses
    name = re.sub(r'\s+who(\s+was|\s+died|\s+married|\s+were|\s+is|\s+had|\s+may\s+have\s+been.*)?.*$', '', name, flags=re.I)
    name = re.sub(r'\s+whose(\s+family.*)?.*$', '', name, flags=re.I)
    name = re.sub(r'\s+whom.*$', '', name, flags=re.I)

    # Clean punctuation
    name = re.sub(r'[^\w\s\-\.\'\(\)]', '', name).strip()

    # 4. Fix flip-flopped surname-first names (e.g. "Durham Enoch" -> "Enoch Durham")
    parts = name.split()
    if len(parts) == 2:
        surname_candidate, first_candidate = parts[0], parts[1]
        if surname_candidate in KNOWN_SURNAMES and first_candidate in KNOWN_FIRST_NAMES:
            name = f"{first_candidate} {surname_candidate}"

    return name

def run_cleaning():
    print("=== Running Name Sanitization & Flip-Flop Normalizer Engine ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # 1. Clean Persons table
    c.execute("SELECT person_id, name FROM persons")
    persons = c.fetchall()

    cleaned_persons_count = 0
    deleted_garbage_count = 0

    for pid, orig_name in persons:
        cleaned = clean_name_string(orig_name)
        if not cleaned:
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            deleted_garbage_count += 1
        elif cleaned != orig_name:
            # Check if cleaned name already exists under another person_id
            c.execute("SELECT person_id FROM persons WHERE name = ? AND person_id != ?", (cleaned, pid))
            existing = c.fetchone()
            if existing:
                keep_id = existing[0]
                remove_id = pid
                # Merge relationships & photos
                c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (keep_id, remove_id))
                c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (keep_id, remove_id))
                c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")
                c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (keep_id, remove_id))
                c.execute("DELETE FROM person_photos WHERE person_id = ?", (remove_id,))
                c.execute("UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?", (keep_id, remove_id))
                c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (remove_id,))
                c.execute("DELETE FROM persons WHERE person_id = ?", (remove_id,))
                cleaned_persons_count += 1
            else:
                c.execute("UPDATE persons SET name = ? WHERE person_id = ?", (cleaned, pid))
                cleaned_persons_count += 1

    conn.commit()
    print(f"Cleaned {cleaned_persons_count} person names and removed {deleted_garbage_count} non-person sentence fragments.", flush=True)

    # 2. Clean Photo Catalog subject_names
    c.execute("SELECT photo_id, subject_names FROM photo_catalog WHERE subject_names LIKE '%who%' OR subject_names LIKE '%Who%'")
    photos = c.fetchall()

    cleaned_photos = 0
    for pid, orig_sub in photos:
        cleaned = clean_name_string(orig_sub)
        if cleaned != orig_sub:
            c.execute("UPDATE photo_catalog SET subject_names = ? WHERE photo_id = ?", (cleaned, pid))
            cleaned_photos += 1

    conn.commit()
    print(f"Cleaned {cleaned_photos} photo subject name entries in photo catalog.", flush=True)

    # 3. Clean Obituaries deceased_name
    c.execute("SELECT id, deceased_name FROM obituaries WHERE deceased_name LIKE '%who%' OR deceased_name LIKE '%Who%'")
    obits = c.fetchall()

    cleaned_obits = 0
    for oid, orig_name in obits:
        cleaned = clean_name_string(orig_name)
        if cleaned != orig_name:
            c.execute("UPDATE obituaries SET deceased_name = ? WHERE id = ?", (cleaned, oid))
            cleaned_obits += 1

    conn.commit()
    conn.close()
    print("=== Name Cleaning & Flip-Flop Normalization Complete! ===", flush=True)

if __name__ == "__main__":
    run_cleaning()
