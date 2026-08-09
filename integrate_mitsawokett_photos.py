#!/usr/bin/env python3
"""
Module 2: Database Cataloging & Graph Cross-Linking (integrate_mitsawokett_photos.py)
=====================================================================================
Performs fuzzy name and surname matching between cataloged photos in photo_catalog 
and individual records in the persons database table. Populates person_photos junction table.
"""

import os
import sqlite3
from difflib import SequenceMatcher

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def integrate_photos_with_graph():
    print("=== [Module 2] Starting Photo Catalog Graph Integration & Person Linking ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT photo_id, subject_names, maiden_name, married_surname FROM photo_catalog")
    photos = cursor.fetchall()

    cursor.execute("SELECT person_id, name FROM persons")
    persons = cursor.fetchall()

    print(f"Matching {len(photos)} cataloged photos against {len(persons)} individuals in database...")

    links_created = 0

    for photo_id, subj_names, maiden, married in photos:
        if not subj_names:
            continue

        for p_id, p_name in persons:
            # Test direct subject name similarity
            ratio = similarity_ratio(subj_names, p_name)

            # Test maiden or married surname match if full name similarity is moderate
            if ratio >= 0.70 or (maiden and len(maiden) > 3 and maiden.lower() in p_name.lower()):
                confidence = max(ratio, 0.85)
                cursor.execute("""
                    INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score)
                    VALUES (?, ?, ?)
                """, (p_id, photo_id, round(confidence, 2)))
                links_created += 1

    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM person_photos")
    total_person_photos = cursor.fetchone()[0]

    conn.close()
    print(f"=== Photo Integration Complete! Created {total_person_photos} person-photo junction links in graph. ===")

if __name__ == "__main__":
    integrate_photos_with_graph()
