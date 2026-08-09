#!/usr/bin/env python3
"""
Catalog Thompson Family (catalog_thompson_family.py)
=====================================================
Catalog Thompson family members and kinship relationships from Mitsawokett photo detail records.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

THOMPSON_PERSONS = [
    ("John Asbury Thompson", "ThompsonAsbury.htm", "Mitsawokett Photo Detail - John Asbury Thompson", "mitsawokett_photos"),
    ("Snowden Asher Thompson", "ThompsonAsher.htm", "Son of John W. Thompson & Sarah Ann (Harmon) Thompson", "mitsawokett_photos"),
    ("Bartholomew Thompson", "ThompsonBartholomew.htm", "Son of John W. Thompson & Sarah Ann (Harmon) Thompson", "mitsawokett_photos"),
    ("John W. Thompson", "ThompsonJohn&Sarah.htm", "Spouse of Sarah Ann Harmon; Father of Snowden Asher & Bartholomew Thompson", "mitsawokett_photos"),
    ("Sarah Ann Harmon", "ThompsonJohn&Sarah.htm", "Spouse of John W. Thompson; Mother of Snowden Asher & Bartholomew Thompson", "mitsawokett_photos"),
]

def catalog_thompson():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    name_to_id = {}
    for name, page, notes, source in THOMPSON_PERSONS:
        c.execute("SELECT person_id FROM persons WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            name_to_id[name] = row[0]
        else:
            c.execute("""
                INSERT INTO persons (name, source_page, notes, dataset_source)
                VALUES (?, ?, ?, ?)
            """, (name, page, notes, source))
            name_to_id[name] = c.lastrowid

    print(f"Cataloged Thompson person IDs: {name_to_id}")

    # Relationships
    rels = [
        (name_to_id["John W. Thompson"], name_to_id["Sarah Ann Harmon"], "spouse", "Spouse of Sarah Ann Harmon in Thompson family records"),
        (name_to_id["Snowden Asher Thompson"], name_to_id["John W. Thompson"], "child_of", "Son of John W. Thompson"),
        (name_to_id["Snowden Asher Thompson"], name_to_id["Sarah Ann Harmon"], "child_of", "Son of Sarah Ann (Harmon) Thompson"),
        (name_to_id["Bartholomew Thompson"], name_to_id["John W. Thompson"], "child_of", "Son of John W. Thompson"),
        (name_to_id["Bartholomew Thompson"], name_to_id["Sarah Ann Harmon"], "child_of", "Son of Sarah Ann (Harmon) Thompson"),
    ]

    for p_a, p_b, r_type, evidence in rels:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, ?, ?)
        """, (p_a, p_b, r_type, evidence))

    # Link photo_catalog items for Thompson
    for name, pid in name_to_id.items():
        c.execute("""
            SELECT photo_id FROM photo_catalog 
            WHERE subject_names LIKE ? OR maiden_name LIKE ? OR married_surname LIKE ?
        """, (f"%{name.split()[0]}%", "%Thompson%", "%Thompson%"))
        photos = c.fetchall()
        for (photo_id,) in photos:
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (?, ?)", (pid, photo_id))

    conn.commit()
    conn.close()
    print("=== Successfully Cataloged Thompson Family Lineage ===")

if __name__ == "__main__":
    catalog_thompson()
