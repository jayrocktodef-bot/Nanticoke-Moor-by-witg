#!/usr/bin/env python3
"""
Integrate Native American Roots Frank Speck Data (integrate_native_american_roots_speck.py)
========================================================================================
Ingests documented Nanticoke lineage data from Native American Roots (nativeamericanroots.wordpress.com/tag/frank-speck)
including the John Puckham (b.1660) & Elias Bookram (b.1790) Nanticoke family tree, connecting Puckham / Bookram / Bookrum variants.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

SURNAME_ALIASES = [
    ("Puckham", "Bookram"),
    ("Puckham", "Bookrum"),
    ("Puckham", "Buckram"),
    ("Puckham", "Pookum"),
    ("Puckham", "Puckins"),
    ("Puckham", "Puckram")
]

PERSONS = [
    ("John Puckham (b.1660)", "Puckham.htm", "Nanticoke Indian born c. 1660 in Somerset Co, MD (Puckamee village); Baptized Jan 25, 1682/3", "native_american_roots_speck"),
    ("Joan Johnson", "Puckham.htm", "Wife of John Puckham, married Feb 25, 1682/3 in Somerset Co, MD", "native_american_roots_speck"),
    ("Chief George Puckham (c.1742)", "Winnesoccum.htm", "Nanticoke Chief signatory of the 1742 Winnasoccum Peace Treaty in Maryland", "native_american_roots_speck"),
    ("Elias Puckham / Bookram (b.1790)", "census.htm", "Nanticoke descendant born c. 1790; relocated from MD to Granville Co, NC; recorded as Elias Puckham (1814), Elias Puckins (1820), Elias Puckram (1824), Elisha Buckram (1830), Elias Bookram (1840)", "native_american_roots_speck"),
    ("Chashe Scott", "census.htm", "Second spouse of Elias Bookram, married June 24, 1824 in Granville Co, NC", "native_american_roots_speck")
]

def run_integration():
    print("=== Integrating Native American Roots Frank Speck Nanticoke Data ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # 1. Ingest Surname Aliases
    for canon, var in SURNAME_ALIASES:
        c.execute("""
            INSERT OR IGNORE INTO surname_aliases (canonical_name, variant_name)
            VALUES (?, ?)
        """, (canon, var))

    # 2. Ingest Persons
    pid_map = {}
    for name, sp, notes, dataset in PERSONS:
        c.execute("SELECT person_id FROM persons WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            pid_map[name] = row[0]
        else:
            c.execute("""
                INSERT INTO persons (name, source_page, notes, dataset_source)
                VALUES (?, ?, ?, ?)
            """, (name, sp, notes, dataset))
            pid_map[name] = c.lastrowid

    # 3. Establish Relationships
    if "John Puckham (b.1660)" in pid_map and "Joan Johnson" in pid_map:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (pid_map["John Puckham (b.1660)"], pid_map["Joan Johnson"], "spouse", "Married 25 Feb 1682/3 in Somerset Co, MD; minister John Huett"))

    if "John Puckham (b.1660)" in pid_map and "Chief George Puckham (c.1742)" in pid_map:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (pid_map["Chief George Puckham (c.1742)"], pid_map["John Puckham (b.1660)"], "child_of", "Grandson of John Puckham (b.1660); Nanticoke Chief 1742"))

    if "Chief George Puckham (c.1742)" in pid_map and "Elias Puckham / Bookram (b.1790)" in pid_map:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (pid_map["Elias Puckham / Bookram (b.1790)"], pid_map["Chief George Puckham (c.1742)"], "child_of", "Descendant of Chief George Puckham & Nanticoke Puckamee village lineage"))

    if "Elias Puckham / Bookram (b.1790)" in pid_map and "Chashe Scott" in pid_map:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (pid_map["Elias Puckham / Bookram (b.1790)"], pid_map["Chashe Scott"], "spouse", "Married 24 Jun 1824 in Granville Co, NC"))

    conn.commit()
    conn.close()
    print("=== Native American Roots Integration Complete! ===", flush=True)

if __name__ == "__main__":
    run_integration()
