#!/usr/bin/env python3
"""
Module 2: Schema Integration & Graph Cross-Linking (integrate_moors.py)
=======================================================================
Performs fuzzy name and source page matching between individuals in the Lynn C. Jackson dataset
and Joseph A. Romeo's 'The Moors of Delaware' dataset. Inserts cross-dataset entity matches
and generates connected relationship edges.
"""

import os
import sqlite3
from difflib import SequenceMatcher

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def cross_link_datasets():
    print("=== [Module 2] Starting Cross-Dataset Graph Integration & Entity Matching ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query Jackson dataset individuals vs Moors dataset individuals
    cursor.execute("SELECT person_id, name, source_page FROM persons WHERE dataset_source = 'lynncjackson' OR dataset_source IS NULL")
    jackson_persons = cursor.fetchall()

    cursor.execute("SELECT person_id, name, source_page FROM persons WHERE dataset_source = 'moors_delaware'")
    moors_persons = cursor.fetchall()

    print(f"Comparing {len(jackson_persons)} Jackson individuals against {len(moors_persons)} Moors individuals...")

    matches_found = 0
    rel_edges_added = 0

    for j_id, j_name, j_page in jackson_persons:
        for m_id, m_name, m_page in moors_persons:
            ratio = similarity_ratio(j_name, m_name)
            
            # High confidence threshold match
            if ratio >= 0.75:
                status = "confirmed" if ratio >= 0.90 else "candidate"
                
                cursor.execute("""
                    INSERT INTO entity_matches (person_id_jackson, person_id_moors, confidence_score, match_status)
                    VALUES (?, ?, ?, ?)
                """, (j_id, m_id, round(ratio, 3), status))
                matches_found += 1

                # Create explicit cross-dataset relationship link
                cursor.execute("""
                    INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                    VALUES (?, ?, 'cross_dataset_match', ?)
                """, (j_id, m_id, f"Cross-dataset entity match ({round(ratio*100, 1)}% confidence) between Lynn C. Jackson archive and Moors of Delaware"))
                rel_edges_added += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM entity_matches")
    total_matches = cursor.fetchone()[0]

    conn.close()
    print(f"=== [Module 2] Completed. Generated {total_matches} cross-dataset entity matches ({rel_edges_added} relationship edges). ===")

if __name__ == "__main__":
    cross_link_datasets()
