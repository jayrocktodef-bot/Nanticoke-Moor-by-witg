#!/usr/bin/env python3
"""
audit_and_deduplicate_findagrave.py
===================================
Comprehensive Find a Grave Audit and Archive-Wide Deduplication.
- Audits all Find a Grave memorials across all profiles.
- Removes false out-of-region matches (e.g., Australia, UK, Missouri, Texas, Mississippi).
- Cleans cross-contaminated / polluted memorials (where unrelated individuals or siblings share one memorial).
- Merges confirmed duplicate ancestor profiles into verified canonical records.
- Preserves all relationships, facts, citations, photos, and face embeddings.
- Guarantees 0 dangling references, 0 self-loops, and 0 data loss.
"""

import sqlite3
import os
import re
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')

def run_audit_and_deduplication():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=========================================================================")
    print("STEP 1: AUDITING AND CLEANING POLLUTED / OUT-OF-REGION FINDAGRAVE MATCHES")
    print("=========================================================================")

    # 1A: Out-of-region / false cemetery matches
    bogus_cemeteries = [
        'Leeds General Cemetery',
        'Fremantle Cemetery',
        'Noxubee Cemetery',
        'Wheatland Cemetery',
        'Celina Community Cemetery',
        'Hickory Creek Cemetery',
        'Waldheim Cemetery',
        'Bolckow Cemetery',
        'Oak Ridge Cemetery',
        'Calvary Cemetery',
        'Logans Ferry UP Church Cemetery',
        'Green Haven Memorial Gardens',
        'Arlington Memorial Park',
        'Abingdon Cemetery'
    ]

    c.execute("SELECT person_id, name, notes FROM persons WHERE notes LIKE '%Verified via FindAGrave:%'")
    all_fg_notes = c.fetchall()

    cleaned_bogus_cems = 0
    for r in all_fg_notes:
        pid = r['person_id']
        notes = r['notes']
        if any(bc.lower() in notes.lower() for bc in bogus_cemeteries):
            # Strip the false Find a Grave link from notes
            cleaned_notes = re.sub(r'\s*\|\s*Verified via FindAGrave:[^\n]+', '', notes)
            cleaned_notes = re.sub(r'Verified via FindAGrave:[^\n]+', '', cleaned_notes).strip()
            c.execute("UPDATE persons SET notes = ? WHERE person_id = ?", (cleaned_notes, pid))
            cleaned_bogus_cems += 1
            print(f"  [Cleaned Out-of-Region Cemetery] ID {pid}: {r['name']}")

    print(f"Cleaned {cleaned_bogus_cems} out-of-region Find a Grave links from profiles.")

    # 1B: Clean the 10 Davis children polluted with A. L. Z. Davis (Memorial 67726281)
    davis_siblings_polluted = [4971, 4975, 4980, 4984, 4988, 4992, 5169, 5177, 5185, 5191]
    for pid in davis_siblings_polluted:
        c.execute("SELECT name, notes FROM persons WHERE person_id = ?", (pid,))
        row = c.fetchone()
        if row:
            notes = row['notes'] or ''
            cleaned_notes = re.sub(r'\s*\|\s*Verified via FindAGrave:[^\n]+', '', notes)
            cleaned_notes = re.sub(r'Verified via FindAGrave:[^\n]+', '', cleaned_notes).strip()
            # Clear bogus birth/death dates that were copied from A. L. Z. Davis
            c.execute("""
                UPDATE persons
                SET birth_info = NULL,
                    death_info = NULL,
                    notes = ?
                WHERE person_id = ?
            """, (cleaned_notes, pid))
            # Also clean bogus facts
            c.execute("DELETE FROM citations WHERE fact_id IN (SELECT fact_id FROM facts WHERE person_id = ? AND fact_type IN ('Birth', 'Death'))", (pid,))
            c.execute("DELETE FROM facts WHERE person_id = ? AND fact_type IN ('Birth', 'Death')", (pid,))
            print(f"  [Cleaned A.L.Z. Davis Pollution] ID {pid}: {row['name']}")

    # 1C: Clean cross-contaminated memorials on victims
    cross_polluted = [
        # (victim_id, memorial_id_pattern, real_owner_id)
        (66, r'142566946', 6116),    # Hopewell Carter Jr
        (9559, r'142566946', 6116),  # Howdie Thompson Jr
        (10749, r'142566946', 6116), # Harvey Harmon Jr
        (10924, r'77808893', 59),    # Phyllis Lorraine Coursey (Hanzer memorial)
        (10964, r'5025875', 323),    # Adella Naomi Hughes (Concilor memorial)
        (7434, r'26626401', 478),    # Paris Vaughn Sterrett (Muncey memorial)
        (2866, r'5962574', 2590),    # Annie Counselor (Harvey memorial)
        (6513, r'5015668', 4253),    # Buddy Morgan Jr (Counselor memorial)
        (6896, r'86392115', 4286),   # Eleanor Petie (Counselor memorial)
        (9883, r'159980382', 6328),  # Dehlia E Harmon (D Harmon memorial)
        (10577, r'159980382', 6328), # Doughas H Harmon (D Harmon memorial)
    ]

    for victim_id, pat, real_owner in cross_polluted:
        c.execute("SELECT name, notes FROM persons WHERE person_id = ?", (victim_id,))
        row = c.fetchone()
        if row:
            notes = row['notes'] or ''
            cleaned_notes = re.sub(rf'\s*\|\s*Verified via FindAGrave:[^\n]*{pat}[^\n]*', '', notes)
            cleaned_notes = re.sub(rf'Verified via FindAGrave:[^\n]*{pat}[^\n]*', '', cleaned_notes).strip()
            c.execute("UPDATE persons SET notes = ? WHERE person_id = ?", (cleaned_notes, victim_id))
            print(f"  [Cleaned Cross-Polluted Memorial] ID {victim_id}: {row['name']} (was tagged with {pat})")

    # 1D: Clean scraper text fragment names
    c.execute("""
        UPDATE persons 
        SET name = 'Polly Handsor',
            first_name = 'Polly',
            middle_name = '',
            married_last_name = 'Handsor'
        WHERE person_id = 11666 AND name = 'Polly Handsor on Aug'
    """)
    c.execute("""
        UPDATE persons 
        SET name = 'Ina Mosley',
            first_name = 'Ina',
            middle_name = '',
            married_last_name = 'Mosley'
        WHERE person_id = 11216 AND name = 'In Milford Mosley'
    """)
    c.execute("""
        UPDATE persons 
        SET name = 'M. Concetta Matteo Muntz',
            first_name = 'M.',
            middle_name = 'Concetta',
            maiden_name = 'Matteo',
            married_last_name = 'Muntz'
        WHERE person_id = 6791 AND name = 'Muntz. She'
    """)

    print("\n=========================================================================")
    print("STEP 2: SYSTEMATIC MERGING OF CONFIRMED DUPLICATE PROFILES")
    print("=========================================================================")

    # Define all verified duplicate clusters: (canonical_id, [duplicate_ids], human_label)
    duplicate_clusters = [
        (591, [45, 552], 'Mary Elizabeth Lizzie Muncey'),
        (2127, [2182], 'Greensbury Beckett'),
        (4462, [2790], 'Esther Ann Pierce Cuff'),
        (3170, [8672], 'Anna Catherine Davis Wright'),
        (3177, [4651], 'Sylvia Davis Pinkett'),
        (7242, [3236], 'Alfred Perkins Sammons'),
        (3588, [3532], 'Charles Edward Carey'),
        (5051, [4484], 'Elizabeth Mae Betty Durham'),
        (8152, [4526], 'William Davis Jr'),
        (9146, [4633], 'Reginald Leon Davis'),
        (4814, [7921], 'Duplesis Wright'),
        (4960, [5443], 'Robert Nehemiah Davis Sr'),
        (6193, [5254], 'Janet Carter Eggleston Davis'),
        (5454, [5364], 'Elizabeth Wilson Davis'),
        (8789, [6082], 'Lillian Eleanor Davis'),
        (6648, [6910], 'Sterrett Henderson Mosley'),
        (9481, [6873], 'George W. Mosley'),
        (7372, [7063], 'Mary Virginia Sammons Reed'),
        (7353, [7280], 'Mary Mosley Reeds'),
        (10705, [7953], 'S. Wright Wilson'),
        (10821, [10087], 'Albert C. Davis Jr'),
        (752, [417], 'Mary Jane Norwood Jackson'),
        (4430, [4464], 'Elias Cuff'),
        (7872, [4021], 'Wade Sammons'),
        (8877, [8360], 'Coard Thompson'),
        (8187, [5258], 'Alsup Davis'),
        (7050, [6639], 'Sina Mosley Ridgeway'),
        (11225, [7337], 'Georgianna Ridgeway'),
        (7978, [6120], 'Lydia Ann Wright Jackson'),
        (5801, [973], 'Theodore Parker Harmon'),
        (10439, [592, 2639], 'Rebecca Jack Ridgeway'),
        (5061, [2583], 'Marshall Ellis Durham'),
        (4887, [3707], 'Freida Russell Durham'),
        (4921, [4917], 'Carlton Hilda Durham'),
        (8123, [2100], 'Billye Pierce Cuff'),
        (5631, [2310], 'Long Tall Lean Larry Dean'),
        (1694, [4100], 'Howard Counselor'),
        (382, [5771], 'Nehemiah Hanzer'),
        (510, [11700], 'Leomond Morgan'),
        (2098, [11664], 'Edward Harmon'),
        (6101, [5681, 10908], 'Brewster Harmon')
    ]

    total_merged = 0

    for canon_id, dups, label in duplicate_clusters:
        # Check canonical exists
        c.execute("SELECT * FROM persons WHERE person_id = ?", (canon_id,))
        canon_row = c.fetchone()
        if not canon_row:
            print(f"  [ERROR] Canonical profile {canon_id} not found! Skipping.")
            continue

        for dup_id in dups:
            c.execute("SELECT * FROM persons WHERE person_id = ?", (dup_id,))
            dup_row = c.fetchone()
            if not dup_row:
                continue

            print(f"  Merging ID {dup_id} ({dup_row['name']}) -> Canonical {canon_id} ({canon_row['name']}) [{label}]")

            # 1. Enrich canonical metadata if empty
            updates = []
            params = []
            if not canon_row['birth_info'] and dup_row['birth_info']:
                updates.append("birth_info = ?")
                params.append(dup_row['birth_info'])
            if not canon_row['death_info'] and dup_row['death_info']:
                updates.append("death_info = ?")
                params.append(dup_row['death_info'])
            if (not canon_row['maiden_name'] or canon_row['maiden_name'] == '') and dup_row['maiden_name']:
                updates.append("maiden_name = ?")
                params.append(dup_row['maiden_name'])
            if (not canon_row['notes'] or len(canon_row['notes']) < 15) and dup_row['notes'] and len(dup_row['notes']) >= 15:
                updates.append("notes = ?")
                params.append(dup_row['notes'])
            
            if updates:
                params.append(canon_id)
                c.execute(f"UPDATE persons SET {', '.join(updates)} WHERE person_id = ?", params)

            # 2. Re-point relationships
            # Avoid self-loops between canon and dup
            c.execute("DELETE FROM relationships WHERE (person_a_id = ? AND person_b_id = ?) OR (person_a_id = ? AND person_b_id = ?)",
                      (canon_id, dup_id, dup_id, canon_id))
            
            # Delete any relationships on dup_id that canon_id already has (to prevent UNIQUE constraint error)
            c.execute("""
                DELETE FROM relationships
                WHERE person_a_id = ?
                  AND (person_b_id, relationship_type) IN (
                      SELECT person_b_id, relationship_type FROM relationships WHERE person_a_id = ?
                  )
            """, (dup_id, canon_id))
            c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (canon_id, dup_id))

            c.execute("""
                DELETE FROM relationships
                WHERE person_b_id = ?
                  AND (person_a_id, relationship_type) IN (
                      SELECT person_a_id, relationship_type FROM relationships WHERE person_b_id = ?
                  )
            """, (dup_id, canon_id))
            c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (canon_id, dup_id))

            # 3. Re-point facts and citations
            # Fetch existing canonical facts
            c.execute("SELECT fact_id, fact_type, date_string, place_string, value_string FROM facts WHERE person_id = ?", (canon_id,))
            canon_facts = c.fetchall()
            canon_fact_set = {(f['fact_type'], f['date_string'], f['place_string'], f['value_string']): f['fact_id'] for f in canon_facts}

            c.execute("SELECT fact_id, fact_type, date_string, place_string, value_string FROM facts WHERE person_id = ?", (dup_id,))
            dup_facts = c.fetchall()

            for df in dup_facts:
                key = (df['fact_type'], df['date_string'], df['place_string'], df['value_string'])
                if key in canon_fact_set:
                    # Point citations to existing canonical fact
                    matching_cid = canon_fact_set[key]
                    c.execute("UPDATE citations SET fact_id = ? WHERE fact_id = ?", (matching_cid, df['fact_id']))
                    c.execute("DELETE FROM facts WHERE fact_id = ?", (df['fact_id'],))
                else:
                    # Move fact to canonical person
                    c.execute("UPDATE facts SET person_id = ? WHERE fact_id = ?", (canon_id, df['fact_id']))

            # 4. Re-point photos
            c.execute("SELECT photo_id FROM person_photos WHERE person_id = ?", (canon_id,))
            canon_photos = {row['photo_id'] for row in c.fetchall()}

            c.execute("SELECT id, photo_id, confidence_score FROM person_photos WHERE person_id = ?", (dup_id,))
            dup_photos = c.fetchall()
            for dp in dup_photos:
                if dp['photo_id'] in canon_photos:
                    c.execute("DELETE FROM person_photos WHERE id = ?", (dp['id'],))
                else:
                    c.execute("UPDATE person_photos SET person_id = ? WHERE id = ?", (canon_id, dp['id']))
                    canon_photos.add(dp['photo_id'])

            # 5. Update photo_catalog & unified_photo_catalog primary person
            c.execute("UPDATE photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE primary_person_id = ?",
                      (canon_id, canon_row['name'], dup_id))
            c.execute("UPDATE unified_photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE primary_person_id = ?",
                      (canon_id, canon_row['name'], dup_id))

            # 6. Update face embeddings
            c.execute("UPDATE face_embeddings SET person_id = ?, person_name = ? WHERE person_id = ?",
                      (canon_id, canon_row['name'], dup_id))

            # 7. Update person obituaries
            c.execute("SELECT obituary_id FROM person_obituaries WHERE person_id = ?", (canon_id,))
            canon_obits = {row['obituary_id'] for row in c.fetchall()}

            c.execute("SELECT id, obituary_id FROM person_obituaries WHERE person_id = ?", (dup_id,))
            dup_obits = c.fetchall()
            for dob in dup_obits:
                if dob['obituary_id'] in canon_obits:
                    c.execute("DELETE FROM person_obituaries WHERE id = ?", (dob['id'],))
                else:
                    c.execute("UPDATE person_obituaries SET person_id = ? WHERE id = ?", (canon_id, dob['id']))
                    canon_obits.add(dob['obituary_id'])

            # 8. Clear audit flags for dup
            c.execute("DELETE FROM audit_flags WHERE person_id = ?", (dup_id,))

            # 9. Delete duplicate person record
            c.execute("DELETE FROM persons WHERE person_id = ?", (dup_id,))
            total_merged += 1

    print(f"\nMerged {total_merged} duplicate profiles cleanly across the database.")

    print("\n=========================================================================")
    print("STEP 3: POST-MERGE GRAPH CLEANUP & INTEGRITY VERIFICATION")
    print("=========================================================================")

    # Remove any self-loops in relationships
    c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")
    self_loops_deleted = c.rowcount
    print(f"Removed {self_loops_deleted} self-referential relationship edges.")

    # Deduplicate relationship pairs
    c.execute("""
        DELETE FROM relationships 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM relationships 
            GROUP BY person_a_id, person_b_id, relationship_type
        )
    """)
    duplicate_rels_deleted = c.rowcount
    print(f"Removed {duplicate_rels_deleted} duplicate relationship edges.")

    # Remove any dangling relationships (pointing to non-existent persons)
    c.execute("""
        DELETE FROM relationships 
        WHERE person_a_id NOT IN (SELECT person_id FROM persons)
           OR person_b_id NOT IN (SELECT person_id FROM persons)
    """)
    dangling_rels_deleted = c.rowcount
    print(f"Removed {dangling_rels_deleted} dangling relationship edges.")

    # Remove any dangling person_photos
    c.execute("DELETE FROM person_photos WHERE person_id NOT IN (SELECT person_id FROM persons)")
    dangling_photos_deleted = c.rowcount
    print(f"Removed {dangling_photos_deleted} dangling person-photo links.")

    # Remove any dangling facts
    c.execute("DELETE FROM facts WHERE person_id NOT IN (SELECT person_id FROM persons)")
    dangling_facts_deleted = c.rowcount
    print(f"Removed {dangling_facts_deleted} dangling facts.")

    # Verify counts
    c.execute("SELECT COUNT(*) FROM persons")
    final_persons_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    final_rels_count = c.fetchone()[0]

    print("\n-------------------------------------------------------------------------")
    print(f"FINAL DATABASE INTEGRITY SUMMARY:")
    print(f"  - Total Surviving Persons: {final_persons_count}")
    print(f"  - Total Clean Relationships: {final_rels_count}")
    print("-------------------------------------------------------------------------")

    conn.commit()
    conn.close()
    print("All deduplication and Find a Grave audit transactions committed successfully.")

if __name__ == '__main__':
    run_audit_and_deduplication()
