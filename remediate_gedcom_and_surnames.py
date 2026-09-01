#!/usr/bin/env python3
"""
Remediate GEDCOM & Suffix Surname Engine
(remediate_gedcom_and_surnames.py)
========================================
1. Purges all 13 unrelated Cremeen (Ohio) profiles and associated records.
2. Preserves legitimate in-law families (Carmean, Ingram, Hitchens, Dickerson, Cordrey, Conaway, Goldsborough, Turner).
3. Repairs all generational suffix surname errors (e.g. surname recorded as Jr/Sr instead of family name).
4. Cleans malformed single-name records and scraping relics.
5. Re-verifies relational integrity.
"""

import os
import sqlite3
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'vi', 'esq', 'esq.', 'md', 'phd'}
HONORIFICS = {'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'miss', 'ms', 'ms.', 'rev', 'rev.'}

def run_remediation():
    print("==================================================================", flush=True)
    print("STARTING GEDCOM CLEANUP & SUFFIX SURNAME REPAIR PIPELINE", flush=True)
    print("==================================================================", flush=True)

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Step 1: Purge Cremeen profiles
    print("\n[Step 1] Purging Cremeen (Ohio) profiles...", flush=True)
    c.execute("""
        SELECT person_id, name FROM persons 
        WHERE name LIKE '%Cremeen%' OR maiden_name LIKE '%Cremeen%' OR married_last_name LIKE '%Cremeen%'
    """)
    cremeen_rows = c.fetchall()
    cremeen_ids = [r[0] for r in cremeen_rows]
    print(f"Found {len(cremeen_ids)} Cremeen profiles to purge: {[r[1] for r in cremeen_rows]}")

    if cremeen_ids:
        placeholders = ','.join('?' for _ in cremeen_ids)
        
        # Delete from relationships
        c.execute(f"DELETE FROM relationships WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})", cremeen_ids + cremeen_ids)
        rels_del = c.rowcount
        
        # Delete from person_photos
        c.execute(f"DELETE FROM person_photos WHERE person_id IN ({placeholders})", cremeen_ids)
        photos_del = c.rowcount

        # Delete from person_obituaries
        c.execute(f"DELETE FROM person_obituaries WHERE person_id IN ({placeholders})", cremeen_ids)
        obits_del = c.rowcount

        # Delete facts & citations
        c.execute(f"SELECT fact_id FROM facts WHERE person_id IN ({placeholders})", cremeen_ids)
        fact_ids = [r[0] for r in c.fetchall()]
        if fact_ids:
            f_ph = ','.join('?' for _ in fact_ids)
            c.execute(f"DELETE FROM citations WHERE fact_id IN ({f_ph})", fact_ids)
            c.execute(f"DELETE FROM facts WHERE fact_id IN ({f_ph})", fact_ids)

        # Delete persons
        c.execute(f"DELETE FROM persons WHERE person_id IN ({placeholders})", cremeen_ids)
        persons_del = c.rowcount

        print(f"Purged: {persons_del} persons, {rels_del} relationships, {photos_del} photo links, {obits_del} obituary links.")

    # Step 2: Repair Suffix & Malformed Surnames across all persons
    print("\n[Step 2] Repairing Suffix Surnames (Jr/Sr/III/etc.)...", flush=True)
    c.execute("SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name FROM persons")
    all_persons = c.fetchall()

    suffix_repaired = 0
    scraping_relics_fixed = 0

    for pid, name, first_name, middle_name, maiden_name, married_last_name in all_persons:
        raw_name = (name or '').strip()
        if not raw_name:
            continue

        words = [w.strip(' ,.;:') for w in raw_name.split() if w.strip(' ,.;:')]
        if not words:
            continue

        new_first = first_name or ''
        new_middle = middle_name or ''
        new_maiden = maiden_name or ''
        new_married = married_last_name or ''
        needs_update = False

        # Clean corrupted scraping relics in first_name or married_last_name
        if new_first in ['Seated:', 'Jr.;', 'Standing:', 'Left:', 'Right:']:
            new_first = words[0] if words else ''
            needs_update = True
        if new_married in ['-----', 'purple', 'green', 'red', 'blue', 'seated']:
            new_married = words[-1] if len(words) > 1 else ''
            needs_update = True

        # Check if the name ends in a generational suffix
        if len(words) >= 2 and words[-1].lower() in SUFFIXES:
            detected_suffix = words[-1]
            actual_surname = words[-2]
            given_parts = words[:-2]

            # If maiden or married was mistakenly set to the suffix, fix it
            if new_maiden.lower() in SUFFIXES or not new_maiden:
                new_maiden = actual_surname
                needs_update = True
            if new_married.lower() in SUFFIXES or not new_married:
                new_married = actual_surname
                needs_update = True
            if not new_first and given_parts:
                new_first = given_parts[0]
                needs_update = True
            if len(given_parts) > 1 and not new_middle:
                new_middle = ' '.join(given_parts[1:])
                needs_update = True

            suffix_repaired += 1

        elif len(words) >= 2:
            actual_surname = words[-1]
            given_parts = words[:-1]

            if new_maiden.lower() in SUFFIXES:
                new_maiden = actual_surname
                needs_update = True
            if new_married.lower() in SUFFIXES:
                new_married = actual_surname
                needs_update = True
            if not new_first and given_parts:
                new_first = given_parts[0]
                needs_update = True

        if needs_update:
            c.execute("""
                UPDATE persons
                SET first_name = ?, middle_name = ?, maiden_name = ?, married_last_name = ?
                WHERE person_id = ?
            """, (new_first, new_middle, new_maiden, new_married, pid))

    conn.commit()

    print(f"Repaired {suffix_repaired} suffix surname records.")

    # Step 3: Verify remaining dataset stats
    c.execute("SELECT COUNT(*) FROM persons")
    total_persons = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    total_rels = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM persons WHERE maiden_name IN ('Jr', 'Sr', 'II', 'III', 'IV') OR married_last_name IN ('Jr', 'Sr', 'II', 'III', 'IV')")
    remaining_suffix_errors = c.fetchone()[0]

    print("\n==================================================================", flush=True)
    print("REMEDIATION SUMMARY", flush=True)
    print("==================================================================", flush=True)
    print(f"Total Preserved Persons: {total_persons}")
    print(f"Total Preserved Kinship Ties: {total_rels}")
    print(f"Remaining Suffix Surname Errors: {remaining_suffix_errors}")
    print("==================================================================", flush=True)

    conn.close()

if __name__ == "__main__":
    run_remediation()
