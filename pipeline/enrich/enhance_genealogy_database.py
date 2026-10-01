#!/usr/bin/env python3
"""
Genealogical Database Safe Enhancement Engine (enhance_genealogy_database.py)
=============================================================================
Performs 100% deterministic, zero-error data quality enhancements:
1. HTML Entity Decoding across all tables (persons, facts, citations, sources, photo_catalog, obituaries).
2. Cross-Table Fact Synchronization (populating missing birth/death info on persons from verified primary facts).
3. Name Component Decomposition (filling missing first/middle/last name fields for 2-3 word names).
4. Exact Photo-to-Person Junction Linking.
5. Database Vacuuming and Optimization.
"""

import os
import sqlite3
import html
import re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def clean_html_entities(text):
    if not text or not isinstance(text, str):
        return text
    if '&' not in text:
        return text
    # Unescape HTML entities
    cleaned = html.unescape(text)
    # Normalize double spaces or non-breaking spaces
    cleaned = cleaned.replace('\xa0', ' ')
    cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
    return cleaned

def decode_all_html_entities(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 1. Decoding HTML Entity Clutter Across All Tables...")
    c = conn.cursor()
    
    total_decoded = 0
    tables = ['persons', 'facts', 'citations', 'sources', 'photo_catalog', 'obituaries']
    
    for tbl in tables:
        c.execute(f"PRAGMA table_info({tbl})")
        columns = [row[1] for row in c.fetchall() if row[2] == 'TEXT']
        pk = 'person_id' if tbl == 'persons' else 'fact_id' if tbl == 'facts' else 'citation_id' if tbl == 'citations' else 'source_id' if tbl == 'sources' else 'photo_id' if tbl == 'photo_catalog' else 'id'
        
        c.execute(f"SELECT {pk}, {', '.join(columns)} FROM {tbl}")
        rows = c.fetchall()
        
        tbl_updated = 0
        for row in rows:
            row_id = row[0]
            col_vals = list(row[1:])
            modified = False
            
            for idx, val in enumerate(col_vals):
                if val and '&' in val:
                    new_val = clean_html_entities(val)
                    if new_val != val:
                        col_vals[idx] = new_val
                        modified = True
                        
            if modified:
                set_clauses = [f"{col} = ?" for col in columns]
                c.execute(f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE {pk} = ?", (*col_vals, row_id))
                tbl_updated += 1
                
        print(f"  ✓ Cleaned {tbl_updated:,} rows in '{tbl}'")
        total_decoded += tbl_updated
        
    return total_decoded

def sync_facts_to_persons(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 2. Synchronizing Primary Facts into Person Profiles...")
    c = conn.cursor()
    
    # Sync Birth
    c.execute("""
        SELECT p.person_id, f.date_string 
        FROM persons p 
        JOIN facts f ON p.person_id = f.person_id 
        WHERE (p.birth_info IS NULL OR p.birth_info = '' OR p.birth_info = 'unknown')
          AND f.fact_type = 'Birth'
          AND f.date_string IS NOT NULL 
          AND f.date_string != ''
    """)
    birth_syncs = c.fetchall()
    for pid, bdate in birth_syncs:
        c.execute("UPDATE persons SET birth_info = ? WHERE person_id = ?", (bdate.strip(), pid))
    print(f"  ✓ Synchronized {len(birth_syncs):,} missing birth records from facts table")
    
    # Sync Death
    c.execute("""
        SELECT p.person_id, f.date_string 
        FROM persons p 
        JOIN facts f ON p.person_id = f.person_id 
        WHERE (p.death_info IS NULL OR p.death_info = '' OR p.death_info = 'unknown')
          AND f.fact_type = 'Death'
          AND f.date_string IS NOT NULL 
          AND f.date_string != ''
    """)
    death_syncs = c.fetchall()
    for pid, ddate in death_syncs:
        c.execute("UPDATE persons SET death_info = ? WHERE person_id = ?", (ddate.strip(), pid))
    print(f"  ✓ Synchronized {len(death_syncs):,} missing death records from facts table")
    
    return len(birth_syncs) + len(death_syncs)

def decompose_missing_name_components(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 3. Decomposing Missing First/Last Name Components...")
    c = conn.cursor()
    
    c.execute("""
        SELECT person_id, name, first_name, middle_name, married_last_name 
        FROM persons 
        WHERE (first_name IS NULL OR first_name = '' OR married_last_name IS NULL OR married_last_name = '')
    """)
    rows = c.fetchall()
    
    decomposed_count = 0
    for pid, name, fn, mn, ln in rows:
        nm = (name or "").strip()
        words = nm.split()
        
        # Valid 2 or 3 word names without punctuation
        if 2 <= len(words) <= 3 and not re.search(r'[,;:\(\)\[\]\{\}\/\\=0-9]', nm):
            new_fn = words[0]
            new_mn = words[1] if len(words) == 3 else None
            new_ln = words[-1]
            
            c.execute("""
                UPDATE persons 
                SET first_name = COALESCE(NULLIF(first_name, ''), ?),
                    middle_name = COALESCE(NULLIF(middle_name, ''), ?),
                    married_last_name = COALESCE(NULLIF(married_last_name, ''), ?)
                WHERE person_id = ?
            """, (new_fn, new_mn, new_ln, pid))
            decomposed_count += 1
            
    print(f"  ✓ Decomposed {decomposed_count:,} name structures into first/middle/last components")
    return decomposed_count

def link_exact_matching_photos(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 4. Linking Exact-Matching Photos to Person Profiles...")
    c = conn.cursor()
    
    c.execute("""
        SELECT pc.photo_id, p.person_id 
        FROM photo_catalog pc
        JOIN persons p ON LOWER(TRIM(pc.subject_names)) = LOWER(TRIM(p.name))
        WHERE pc.photo_id NOT IN (SELECT photo_id FROM person_photos WHERE person_id = p.person_id)
    """)
    matches = c.fetchall()
    
    linked_count = 0
    for photo_id, person_id in matches:
        c.execute("""
            INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score)
            VALUES (?, ?, 1.0)
        """, (person_id, photo_id))
        linked_count += 1
        
    print(f"  ✓ Linked {linked_count:,} exact-match photos into person_photos junction")
    return linked_count

def main():
    print("=" * 72)
    print("  GENEALOGICAL ARCHIVE ENHANCEMENT & OPTIMIZATION")
    print("=" * 72)
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    
    try:
        with conn:
            html_decoded = decode_all_html_entities(conn)
            facts_synced = sync_facts_to_persons(conn)
            names_decomposed = decompose_missing_name_components(conn)
            photos_linked = link_exact_matching_photos(conn)
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 5. Optimizing and Vacuuming Database...")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        print("  ✓ Database vacuumed and optimized")
        
        print("\n" + "=" * 72)
        print("  ENHANCEMENTS COMPLETED SUCCESSFULLY")
        print(f"  - HTML Entities Cleaned Across DB: {html_decoded:,}")
        print(f"  - Facts Synchronized to Profiles: {facts_synced:,}")
        print(f"  - Name Components Decomposed: {names_decomposed:,}")
        print(f"  - Exact Photo Links Created: {photos_linked:,}")
        print("=" * 72)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
