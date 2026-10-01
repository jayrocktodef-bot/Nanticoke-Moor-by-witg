#!/usr/bin/env python3
"""
Integrate Change of Race Records (integrate_change_of_race_records.py)
====================================================================
Ingests historical Indian leaders and Nanticoke community members documented in the 
Delaware Change of Race historical record (nativeamericansofdelawarestate.com/Change_of_Race.htm)
into genealogy_preservation.db with full legal & census citations.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

COR_PERSONS = [
    ("Wassason", "Change_of_Race.htm", "Indian leader documented in 1736 land conveyance of 600-acre Indian Lands reservation in Millsboro, DE", "mitsawokett_delaware"),
    ("Weatomotonies", "Change_of_Race.htm", "Nanticoke 'Indian Queen' documented in 1743 land conveyance of Queen's Swamp in Sussex Co, DE", "mitsawokett_delaware"),
    ("Augustus Wright", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("David H. Clark", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 3); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Luther B. Norwood", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Oscar W. Wright", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Gardner R. Street", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Wilson Harmon", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Custis Johnson", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 7); race struck through from 'In' to 'Neg'", "mitsawokett_delaware"),
    ("Phillip Jackson", "Change_of_Race.htm", "Delaware Nanticoke Tribe member enumerated in 1930 Sussex Co Census (District 3); race struck through from 'In' to 'Neg'", "mitsawokett_delaware")
]

def run_integration():
    print("=== Ingesting Delaware Change of Race Historical Records ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    name_to_id = {}
    ingested_count = 0

    for name, sp, notes, dataset in COR_PERSONS:
        c.execute("SELECT person_id FROM persons WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            name_to_id[name] = row[0]
        else:
            c.execute("""
                INSERT INTO persons (name, source_page, notes, dataset_source)
                VALUES (?, ?, ?, ?)
            """, (name, sp, notes, dataset))
            name_to_id[name] = c.lastrowid
            ingested_count += 1

    # Link relationships
    if "Wassason" in name_to_id and "Weatomotonies" in name_to_id:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (name_to_id["Wassason"], name_to_id["Weatomotonies"], "kinship", "Co-signatories of 1736-1743 Indian River Indian reservation land conveyances"))

    # Link cataloged photos matching these surnames
    for name, pid in name_to_id.items():
        surname = name.split()[-1]
        c.execute("""
            SELECT photo_id FROM photo_catalog 
            WHERE maiden_name = ? OR married_surname = ? OR subject_names LIKE ?
            LIMIT 5
        """, (surname, surname, f"%{surname}%"))
        for (photo_id,) in c.fetchall():
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (?, ?)", (pid, photo_id))

    conn.commit()
    conn.close()

    print(f"Successfully ingested {ingested_count} Change of Race historical individuals.")
    print("=== Integration Complete! ===", flush=True)

if __name__ == "__main__":
    run_integration()
