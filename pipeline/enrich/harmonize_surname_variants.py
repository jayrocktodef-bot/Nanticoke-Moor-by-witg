#!/usr/bin/env python3
"""
Surname Harmonization & Variant Alias Engine (harmonize_surname_variants.py)
=============================================================================
Harmonizes historical Delmarva, Moor, and Nanticoke phonetic surname variants
across all preserved records, photo catalogs, and obituaries in genealogy_preservation.db.

Supported Family Clusters & Phonetic Variants:
- Hansor / Hanzer / Handsor / Handzor / Handszer
- Driggus / Drigger / Driggett / Driggers
- Cuff / Cuffee
- Counselor / Concilor / Concealler / Concealor / Conselah / Conselar
- Seeney / Seany / Seney
- Sockum / Sockey
- Hughes / Hewes
- Sisco / Cisco / Ciscero / Francisco
- Carney / Carny
- Sammons / Sammon
- Ridgeway / Ridgway
- Purnell / Purnel
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

# Canonical Surname Mappings (Canonical -> List of Variants)
CANONICAL_FAMILY_MAP = {
    "Hansor": ["Hansor", "Hanzer", "Handsor", "Handzor", "Handszer"],
    "Driggus": ["Driggus", "Drigger", "Driggett", "Driggers"],
    "Cuff": ["Cuff", "Cuffee"],
    "Counselor": ["Counselor", "Concilor", "Concealler", "Concealor", "Conselah", "Conselar"],
    "Seeney": ["Seeney", "Seany", "Seney"],
    "Sockum": ["Sockum", "Sockey"],
    "Hughes": ["Hughes", "Hewes"],
    "Sisco": ["Sisco", "Cisco", "Ciscero"],
    "Carney": ["Carney", "Carny"],
    "Sammons": ["Sammons", "Sammon"],
    "Ridgeway": ["Ridgeway", "Ridgway"],
    "Purnell": ["Purnell", "Purnel"],
    "Gaines": ["Gaines", "Games/Gaines"],
    "Harmon": ["Harmon", "Harman"]
}

def build_variant_lookup():
    variant_to_canonical = {}
    for canonical, variants in CANONICAL_FAMILY_MAP.items():
        for var in variants:
            variant_to_canonical[var.lower()] = canonical
    return variant_to_canonical

def harmonize_database():
    print("=== Starting Delmarva Surname Harmonization Engine ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # 1. Create surname_aliases reference table
    c.execute("""
        CREATE TABLE IF NOT EXISTS surname_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            variant_name TEXT NOT NULL UNIQUE
        )
    """)
    c.execute("DELETE FROM surname_aliases")

    alias_entries = []
    for canonical, variants in CANONICAL_FAMILY_MAP.items():
        for var in variants:
            alias_entries.append((canonical, var))

    c.executemany("INSERT OR IGNORE INTO surname_aliases (canonical_name, variant_name) VALUES (?, ?)", alias_entries)
    conn.commit()
    print(f"Created surname_aliases reference table with {len(alias_entries)} mapping entries.", flush=True)

    # 2. Harmonize maiden names in photo_catalog
    var_map = build_variant_lookup()
    c.execute("SELECT photo_id, maiden_name, married_surname, title_or_caption FROM photo_catalog")
    photos = c.fetchall()

    photo_updates = 0
    for pid, maiden, married, caption in photos:
        new_maiden = maiden
        new_married = married
        
        if maiden and maiden.lower() in var_map:
            new_maiden = var_map[maiden.lower()]
            
        if married and married.lower() in var_map:
            new_married = var_map[married.lower()]
            
        if new_maiden != maiden or new_married != married:
            c.execute("UPDATE photo_catalog SET maiden_name = ?, married_surname = ? WHERE photo_id = ?",
                      (new_maiden, new_married, pid))
            photo_updates += 1

    conn.commit()
    print(f"Harmonized surname variants across {photo_updates} photo catalog records.", flush=True)

    # 3. Summary stats
    c.execute("""
        SELECT sa.canonical_name, COUNT(pc.photo_id) AS photo_count
        FROM surname_aliases sa
        LEFT JOIN photo_catalog pc ON (LOWER(pc.maiden_name) = LOWER(sa.canonical_name) OR LOWER(pc.maiden_name) = LOWER(sa.variant_name))
        GROUP BY sa.canonical_name
        ORDER BY photo_count DESC
    """)
    print("\nHarmonized Key Family Totals (Photos):", flush=True)
    for canonical, count in c.fetchall():
        variants_str = ", ".join(CANONICAL_FAMILY_MAP.get(canonical, []))
        print(f"  {canonical} ({variants_str}): {count} photos", flush=True)

    conn.close()
    print("=== Surname Harmonization Complete! ===", flush=True)

if __name__ == "__main__":
    harmonize_database()
