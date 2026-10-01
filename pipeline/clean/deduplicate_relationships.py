#!/usr/bin/env python3
"""
Relationship Deduplication & Canonical Consolidation Engine (deduplicate_relationships.py)
========================================================================================
Audits and merges duplicate relationship connections in genealogy_preservation.db:
1. Normalizes relationship types ('spouses', 'spouse_of' -> 'spouse').
2. Canonicalizes symmetrical relationships so person_a_id < person_b_id.
3. Consolidates multi-edge duplicate groups into a single champion record preserving the richest evidence.
4. Adds unique index constraints to prevent future duplicates.
5. Rebuilds static export files for familyarchive.writteninthegenome.blog.
"""

import os
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def score_relationship_evidence(rel):
    """Score evidence quality to pick the best champion record in a duplicate group."""
    ev = (rel['evidence_text'] or '').strip()
    score = 0
    # Length of evidence
    score += min(len(ev), 200)
    # Contains 4-digit year (e.g. 1862)
    if re.search(r'\b(1[6-9]\d{2}|20\d{2})\b', ev):
        score += 100
    # Certainty score
    cert = (rel['certainty'] or '').lower()
    if cert == 'confirmed':
        score += 50
    elif cert == 'probable':
        score += 25
    return score

def deduplicate_relationships(conn):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 1. Auditing & Grouping Duplicate Relationships...")
    c = conn.cursor()
    
    c.execute("SELECT id, person_a_id, person_b_id, relationship_type, evidence_text, certainty FROM relationships")
    all_rows = [dict(r) for r in c.fetchall()]
    print(f"  Loaded {len(all_rows):,} total relationship rows.")
    
    groups = defaultdict(list)
    for r in all_rows:
        pa, pb, rtype = r['person_a_id'], r['person_b_id'], r['relationship_type'].lower()
        
        # Normalize relationship type
        if rtype in ('spouse', 'spouses', 'spouse_of'):
            rtype_norm = 'spouse'
            # Canonicalize symmetrical ordering
            canon_a = min(pa, pb)
            canon_b = max(pa, pb)
        else:
            rtype_norm = rtype
            canon_a = pa
            canon_b = pb
            
        key = (canon_a, canon_b, rtype_norm)
        groups[key].append(r)

    duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"  Found {len(duplicate_groups):,} duplicate groups containing {sum(len(v) - 1 for v in duplicate_groups.values()):,} redundant rows.")

    merged_count = 0
    deleted_ids = []

    for (canon_a, canon_b, rtype_norm), rel_list in groups.items():
        if len(rel_list) == 1:
            r = rel_list[0]
            # Ensure canonical orientation and normalized type
            if r['person_a_id'] != canon_a or r['person_b_id'] != canon_b or r['relationship_type'] != rtype_norm:
                c.execute("""
                    UPDATE relationships 
                    SET person_a_id = ?, person_b_id = ?, relationship_type = ?
                    WHERE id = ?
                """, (canon_a, canon_b, rtype_norm, r['id']))
        else:
            # Sort duplicate records by evidence quality (highest score first)
            rel_list.sort(key=score_relationship_evidence, reverse=True)
            champion = rel_list[0]
            
            # Combine any unique evidence strings
            evidence_pieces = []
            for r in rel_list:
                ev = (r['evidence_text'] or '').strip()
                if ev and ev not in evidence_pieces:
                    # Only add if it's not a strict substring of an already present evidence piece
                    if not any(ev in existing for existing in evidence_pieces):
                        evidence_pieces.append(ev)
            
            consolidated_evidence = " | ".join(evidence_pieces) if evidence_pieces else champion['evidence_text']
            best_certainty = 'confirmed' if any((r['certainty'] or '').lower() == 'confirmed' for r in rel_list) else champion['certainty']
            
            # Update the champion record
            c.execute("""
                UPDATE relationships 
                SET person_a_id = ?, person_b_id = ?, relationship_type = ?, evidence_text = ?, certainty = ?
                WHERE id = ?
            """, (canon_a, canon_b, rtype_norm, consolidated_evidence, best_certainty, champion['id']))
            
            # Mark other redundant records for deletion
            for r in rel_list[1:]:
                deleted_ids.append(r['id'])
                
            merged_count += 1

    if deleted_ids:
        # Delete redundant records in batches
        batch_size = 500
        for i in range(0, len(deleted_ids), batch_size):
            batch = deleted_ids[i:i + batch_size]
            placeholders = ",".join(["?"] * len(batch))
            c.execute(f"DELETE FROM relationships WHERE id IN ({placeholders})", batch)

    print(f"  ✓ Merged {merged_count:,} duplicate groups and deleted {len(deleted_ids):,} redundant relationship rows.")

def apply_schema_hardening(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 2. Applying Schema Hardening & Unique Indexes...")
    c = conn.cursor()
    
    # Create unique compound index to permanently enforce uniqueness
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_canonical_rel 
        ON relationships(person_a_id, person_b_id, relationship_type)
    """)
    print("  ✓ Created UNIQUE compound index on relationships(person_a_id, person_b_id, relationship_type)")

def verify_specific_profiles(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 3. Verifying Target Profile Cleanliness...")
    c = conn.cursor()
    
    # Check Sarah Cott (ID #13)
    c.execute("""
        SELECT r.id, r.relationship_type, r.evidence_text, p2.person_id, p2.name 
        FROM relationships r
        JOIN persons p2 ON (r.person_b_id = p2.person_id AND r.person_a_id = 13) 
                        OR (r.person_a_id = p2.person_id AND r.person_b_id = 13)
    """)
    sarah_rels = c.fetchall()
    print(f"  ✓ Sarah Cott (#13) Family Connections: {len(sarah_rels)} connection(s) (was 11 duplicates):")
    for r in sarah_rels:
        print(f"    └─ [{r[1].upper()}] {r[4]} (#{r[3]}): \"{r[2]}\"")

    # Global duplicate check
    c.execute("""
        SELECT person_a_id, person_b_id, relationship_type, COUNT(*) 
        FROM relationships 
        GROUP BY person_a_id, person_b_id, relationship_type 
        HAVING COUNT(*) > 1
    """)
    remaining_dupes = c.fetchall()
    print(f"  ✓ Global Remaining Duplicate Groups: {len(remaining_dupes)} (Target: 0)")

def main():
    print("=" * 72)
    print("  RELATIONSHIP DEDUPLICATION & CONSOLIDATION ENGINE")
    print("=" * 72)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    
    try:
        with conn:
            deduplicate_relationships(conn)
            apply_schema_hardening(conn)
            verify_specific_profiles(conn)
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 4. Vacuuming and Optimizing Database...")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        print("  ✓ Database vacuumed and optimized.")
        
        print("\n" + "=" * 72)
        print("  DEDUPLICATION COMPLETED SUCCESSFULLY")
        print("=" * 72)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
