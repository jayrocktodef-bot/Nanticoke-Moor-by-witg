#!/usr/bin/env python3
"""
Smithsonian NMAI Frank Speck Archive Integrator (integrate_smithsonian_speck_archive.py)
=======================================================================================
Ingests cataloged Nanticoke & Moor individuals from the Frank Gouldsmith Speck Photograph Collection
(Smithsonian Institution NMAI Archives, Series 8: Delaware: Nanticoke and Rappahannock - NMAI.AC.001.008)
into genealogy_preservation.db with full archival citations and kinship connections.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

SPECK_PERSONS = [
    ("Jane Harmon", "NMAI.AC.001.008", "Nanticoke elder & primary informant for Frank G. Speck (c.1911-1920); Spouse of Ephraim Harmon", "smithsonian_nmai_speck", "Harmon"),
    ("Ferdinand Clark", "NMAI.AC.001.008", "Nanticoke elder & basket maker documented in Millsboro, DE (c.1911-1914)", "smithsonian_nmai_speck", "Clark"),
    ("Sallie Ann Sockum", "NMAI.AC.001.008", "Nanticoke matriarch & traditional herbalist in Oak Orchard, DE (c.1911-1915)", "smithsonian_nmai_speck", "Sockum"),
    ("Russell Ridgeway", "Nanticoke.SOVA", "Nanticoke community officer & leader documented in Millsboro, DE", "smithsonian_nmai_speck", "Ridgeway"),
    ("Chief Charles C. Clark", "NMAI.AC.001.008", "Elected Chief of the Nanticoke Indian Association (c.1922-1930)", "smithsonian_nmai_speck", "Clark"),
    ("Chief William H. Clark", "NMAI.AC.001.008", "Elected Chief of the Nanticoke Indian Tribe documented in Smithsonian NMAI Series 8", "smithsonian_nmai_speck", "Clark"),
    ("Ebenezer Davis", "NMAI.AC.001.008", "Nanticoke elder & farmer documented in Millsboro, DE", "smithsonian_nmai_speck", "Davis"),
    ("Phoebe Carney", "NMAI.AC.001.008", "Nanticoke / Moor community member in Cheswold, DE", "smithsonian_nmai_speck", "Carney"),
    ("Howard Counselor", "NMAI.AC.001.008", "Nanticoke / Moor community member in Cheswold, DE", "smithsonian_nmai_speck", "Counselor"),
    ("Inez Cormean", "NMAI.AC.001.008", "Nanticoke community member documented in Millsboro, DE", "smithsonian_nmai_speck", "Cormean")
]

def run_integration():
    print("=== Ingesting Smithsonian NMAI Frank Speck Collection (Series 8) ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    name_to_id = {}
    ingested_count = 0

    for name, sp, notes, source, surname in SPECK_PERSONS:
        c.execute("SELECT person_id FROM persons WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            name_to_id[name] = row[0]
        else:
            c.execute("""
                INSERT INTO persons (name, source_page, notes, dataset_source)
                VALUES (?, ?, ?, ?)
            """, (name, sp, notes, source))
            name_to_id[name] = c.lastrowid
            ingested_count += 1

    # Connect relationships
    c.execute("SELECT person_id FROM persons WHERE name LIKE '%Ephraim Harmon%' OR name LIKE '%Ephraim Harman%'")
    eph = c.fetchone()
    if eph and "Jane Harmon" in name_to_id:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (name_to_id["Jane Harmon"], eph[0], "spouse", "Spouse of Ephraim Harmon documented in Smithsonian NMAI Speck collection"))

    c.execute("SELECT person_id FROM persons WHERE name LIKE '%Eliza Ann Harmon%'")
    eliza = c.fetchone()
    if eliza and "Jane Harmon" in name_to_id:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (eliza[0], name_to_id["Jane Harmon"], "child_of", "Daughter of Jane Harmon & Ephraim Harmon"))

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

    print(f"Successfully ingested {ingested_count} Smithsonian NMAI Speck Archive individuals.")
    print("=== Integration Complete! ===", flush=True)

if __name__ == "__main__":
    run_integration()
