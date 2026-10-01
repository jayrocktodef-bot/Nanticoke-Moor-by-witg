#!/usr/bin/env python3
"""
Genealogical Person Merge & Profile Consolidation Engine (merge_duplicate_persons.py)
===================================================================================
Executes high-confidence person profile deduplication and metadata unioning:
1. Identifies Tier 1 (High Confidence >= 85%) duplicate pairs from person_deduplication_audit.
2. Builds disjoint connected components via Union-Find.
3. Selects the champion profile (most complete name, vital dates, and citations).
4. Safely reassigns all foreign keys across facts, relationships, photos, obituaries, entity_matches, and audit_flags.
5. Deletes dropped duplicate records before updating the champion profile.
6. Merges and enriches person profile attributes (name, vital dates, notes).
7. Prunes merged duplicate IDs and cleans self-referencing relationship edges.
8. Rebuilds static export files for familyarchive.writteninthegenome.blog.
"""

import os
import shutil
import sqlite3
import re
from collections import defaultdict
from datetime import datetime
from person_deduplication_audit import run_deduplication_audit

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
BACKUP_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation_pre_person_merge_backup.db")

class UnionFind:
    def __init__(self):
        self.parent = {}
        
    def find(self, i):
        if i not in self.parent:
            self.parent[i] = i
            return i
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
        
    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

def create_backup():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 1. Creating Pre-Merge Safety Backup...")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        size_mb = os.path.getsize(BACKUP_PATH) / (1024 * 1024)
        print(f"  ✓ Snapshot preserved at: {BACKUP_PATH} ({size_mb:.2f} MB)")
    else:
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

def score_profile_completeness(p, c):
    """Calculates profile completeness score to select the champion record."""
    pid = p['person_id']
    score = 0
    name = (p['name'] or '').strip()
    score += len(name) * 2
    
    # Has middle name
    if (p['middle_name'] or '').strip():
        score += 20
    # Has full birth date
    b_info = (p['birth_info'] or '').strip()
    if re.search(r'\d{1,2}\s+[a-z]{3,9}\s+\d{4}', b_info, re.I):
        score += 30
    elif re.search(r'\d{4}', b_info):
        score += 15
        
    # Has full death date
    d_info = (p['death_info'] or '').strip()
    if re.search(r'\d{1,2}\s+[a-z]{3,9}\s+\d{4}', d_info, re.I):
        score += 30
    elif re.search(r'\d{4}', d_info):
        score += 15
        
    # Count attached facts, photos, obituaries, relationships
    c.execute("SELECT COUNT(*) FROM facts WHERE person_id = ?", (pid,))
    score += c.fetchone()[0] * 10
    
    c.execute("SELECT COUNT(*) FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
    score += c.fetchone()[0] * 15
    
    c.execute("SELECT COUNT(*) FROM person_photos WHERE person_id = ?", (pid,))
    score += c.fetchone()[0] * 20
    
    c.execute("SELECT COUNT(*) FROM person_obituaries WHERE person_id = ?", (pid,))
    score += c.fetchone()[0] * 20
    
    return score

def merge_duplicate_components(conn, tier1_candidates):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 2. Grouping Connected Components via Disjoint Sets...")
    uf = UnionFind()
    for cand in tier1_candidates:
        p1_id = cand['p1']['person_id']
        p2_id = cand['p2']['person_id']
        uf.union(p1_id, p2_id)
        
    # Group by component root
    components = defaultdict(set)
    for cand in tier1_candidates:
        p1_id = cand['p1']['person_id']
        p2_id = cand['p2']['person_id']
        root = uf.find(p1_id)
        components[root].add(p1_id)
        components[root].add(p2_id)
        
    print(f"  ✓ Grouped {len(tier1_candidates):,} pairs into {len(components):,} unique duplicate clusters.")
    
    c = conn.cursor()
    
    # Temporarily drop unique index on relationships during batch foreign key realignment
    c.execute("DROP INDEX IF EXISTS idx_unique_canonical_rel")
    
    merged_clusters = 0
    total_profiles_removed = 0
    
    for root, member_ids in components.items():
        placeholders = ",".join(["?"] * len(member_ids))
        c.execute(f"SELECT * FROM persons WHERE person_id IN ({placeholders})", list(member_ids))
        member_rows = [dict(r) for r in c.fetchall()]
        
        if len(member_rows) < 2:
            continue
            
        # Select champion record
        member_rows.sort(key=lambda p: score_profile_completeness(p, c), reverse=True)
        champion = member_rows[0]
        drop_profiles = member_rows[1:]
        
        keep_id = champion['person_id']
        drop_ids = [dp['person_id'] for dp in drop_profiles]
        
        # 1. Consolidate Name & Metadata
        best_name = champion['name']
        for dp in drop_profiles:
            if len(dp['name']) > len(best_name) and not re.search(r'[,;:\(\)\[\]\{\}\/\\=0-9]', dp['name']):
                best_name = dp['name']
                
        best_fn = champion['first_name'] or next((dp['first_name'] for dp in drop_profiles if dp['first_name']), '')
        best_mn = champion['middle_name'] or next((dp['middle_name'] for dp in drop_profiles if dp['middle_name']), '')
        best_mn_last = champion['maiden_name'] or next((dp['maiden_name'] for dp in drop_profiles if dp['maiden_name']), '')
        best_mrd_last = champion['married_last_name'] or next((dp['married_last_name'] for dp in drop_profiles if dp['married_last_name']), '')
        
        # Consolidate Dates (choose most specific)
        best_birth = champion['birth_info']
        for dp in drop_profiles:
            b = (dp['birth_info'] or '').strip()
            if b and b != 'unknown':
                if not best_birth or best_birth == 'unknown' or (len(b) > len(best_birth) and re.search(r'\d{1,2}\s+[a-z]{3,9}', b, re.I)):
                    best_birth = b
                    
        best_death = champion['death_info']
        for dp in drop_profiles:
            d = (dp['death_info'] or '').strip()
            if d and d != 'unknown':
                if not best_death or best_death == 'unknown' or (len(d) > len(best_death) and re.search(r'\d{1,2}\s+[a-z]{3,9}', d, re.I)):
                    best_death = d
                    
        # Consolidate Notes
        note_pieces = [champion['notes']] if champion['notes'] else []
        for dp in drop_profiles:
            if dp['notes'] and dp['notes'] not in note_pieces:
                note_pieces.append(dp['notes'])
        combined_notes = " | ".join([n.strip(" |") for n in note_pieces if n])
        
        # 2. Reassign All Foreign Keys Across All Referencing Tables
        for drop_id in drop_ids:
            # Facts
            c.execute("UPDATE facts SET person_id = ? WHERE person_id = ?", (keep_id, drop_id))
            
            # Relationships
            c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (keep_id, drop_id))
            c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (keep_id, drop_id))
            
            # Photos
            c.execute("""
                INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score)
                SELECT ?, photo_id, confidence_score FROM person_photos WHERE person_id = ?
            """, (keep_id, drop_id))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (drop_id,))
            
            # Obituaries
            c.execute("""
                INSERT OR IGNORE INTO person_obituaries (person_id, obituary_id, role, confidence_score)
                SELECT ?, obituary_id, role, confidence_score FROM person_obituaries WHERE person_id = ?
            """, (keep_id, drop_id))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (drop_id,))
            
            # Entity matches
            c.execute("UPDATE entity_matches SET person_id_jackson = ? WHERE person_id_jackson = ?", (keep_id, drop_id))
            c.execute("UPDATE entity_matches SET person_id_moors = ? WHERE person_id_moors = ?", (keep_id, drop_id))
            
            # Audit flags
            c.execute("UPDATE audit_flags SET person_id = ? WHERE person_id = ?", (keep_id, drop_id))
            c.execute("UPDATE audit_flags SET person_id_secondary = ? WHERE person_id_secondary = ?", (keep_id, drop_id))
            
            # Delete dropped person profile FIRST so name unique constraint is freed
            c.execute("DELETE FROM persons WHERE person_id = ?", (drop_id,))
            total_profiles_removed += 1
            
        # 3. Update Champion Profile
        c.execute("SELECT person_id FROM persons WHERE name = ? AND person_id != ?", (best_name, keep_id))
        existing = c.fetchone()
        final_name = best_name if not existing else champion['name']
        
        c.execute("""
            UPDATE persons 
            SET name = ?, first_name = ?, middle_name = ?, maiden_name = ?, 
                married_last_name = ?, birth_info = ?, death_info = ?, notes = ?
            WHERE person_id = ?
        """, (final_name, best_fn, best_mn, best_mn_last, best_mrd_last, best_birth, best_death, combined_notes, keep_id))
        
        # Self-referencing relationship protection
        c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")
        
        merged_clusters += 1
        
    print(f"  ✓ Successfully consolidated {merged_clusters:,} clusters and retired {total_profiles_removed:,} duplicate profiles.")
    return merged_clusters, total_profiles_removed

def deduplicate_post_merge_relationships(conn):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 3. Consolidating Newly Formed Duplicate Relationships...")
    c = conn.cursor()
    
    c.execute("SELECT id, person_a_id, person_b_id, relationship_type, evidence_text, certainty FROM relationships")
    all_rows = [dict(r) for r in c.fetchall()]
    
    groups = defaultdict(list)
    for r in all_rows:
        pa, pb, rtype = r['person_a_id'], r['person_b_id'], r['relationship_type'].lower()
        if rtype in ('spouse', 'spouses', 'spouse_of'):
            key = (min(pa, pb), max(pa, pb), 'spouse')
        else:
            key = (pa, pb, rtype)
        groups[key].append(r)
        
    deleted_ids = []
    for (ca, cb, rtype), rlist in groups.items():
        if len(rlist) > 1:
            # Sort by evidence length and confirmed status
            rlist.sort(key=lambda x: (1 if (x['certainty'] or '').lower() == 'confirmed' else 0, len(x['evidence_text'] or '')), reverse=True)
            champion = rlist[0]
            
            c.execute("""
                UPDATE relationships 
                SET person_a_id = ?, person_b_id = ?, relationship_type = ?, evidence_text = ?, certainty = ?
                WHERE id = ?
            """, (ca, cb, rtype, champion['evidence_text'], champion['certainty'], champion['id']))
            
            for extra in rlist[1:]:
                deleted_ids.append(extra['id'])
        else:
            r = rlist[0]
            if r['person_a_id'] != ca or r['person_b_id'] != cb or r['relationship_type'] != rtype:
                c.execute("""
                    UPDATE relationships 
                    SET person_a_id = ?, person_b_id = ?, relationship_type = ?
                    WHERE id = ?
                """, (ca, cb, rtype, r['id']))
                
    if deleted_ids:
        batch_size = 500
        for i in range(0, len(deleted_ids), batch_size):
            batch = deleted_ids[i:i + batch_size]
            placeholders = ",".join(["?"] * len(batch))
            c.execute(f"DELETE FROM relationships WHERE id IN ({placeholders})", batch)
            
    print(f"  ✓ Cleaned {len(deleted_ids):,} post-merge duplicate relationships.")
    
    # Re-apply UNIQUE compound index
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_canonical_rel 
        ON relationships(person_a_id, person_b_id, relationship_type)
    """)
    print("  ✓ Re-enforced UNIQUE compound index on relationships(person_a_id, person_b_id, relationship_type)")

def main():
    print("=" * 72)
    print("  GENEALOGICAL PERSON PROFILE MERGE & CONSOLIDATION")
    print("=" * 72)
    
    create_backup()
    
    # Run audit to fetch Tier 1 candidates
    candidates = run_deduplication_audit()
    tier1 = [c for c in candidates if "Tier 1" in c['tier']]
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Identified {len(tier1):,} Tier 1 High-Confidence Candidate Pairs for Merge.")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    
    try:
        with conn:
            clusters, profiles_removed = merge_duplicate_components(conn, tier1)
            deduplicate_post_merge_relationships(conn)
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 4. Optimizing & Vacuuming Database...")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        print("  ✓ Database vacuumed and optimized.")
        
        # Verify final person count
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM persons")
        final_persons = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM relationships")
        final_rels = c.fetchone()[0]
        
        print("\n" + "=" * 72)
        print("  PERSON MERGE & CONSOLIDATION SUMMARY")
        print(f"  - Duplicate Clusters Merged:   {clusters:,}")
        print(f"  - Duplicate Profiles Retired: {profiles_removed:,}")
        print(f"  - Active Verified Persons:    {final_persons:,}")
        print(f"  - Active Canonical Ties:      {final_rels:,}")
        print("=" * 72)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
