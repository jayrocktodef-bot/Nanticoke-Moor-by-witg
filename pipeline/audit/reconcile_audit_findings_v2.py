#!/usr/bin/env python3
"""
reconcile_audit_findings_v2.py
Remediate remaining database audit anomalies:
1. Merge compound records (#582, #594, #2271) into individual persons and establish marital links.
2. Clean compound names (#2312, #2421, #5043).
3. Clean obituary titles and ages (#47, #138, #139, #174, #210).
4. Link explicit family relationships from notes and families_and_people.
"""

import sqlite3
import re
import os

DB_PATH = 'preservation_output/genealogy_preservation.db'

def remediate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("=== Step 1: Merging Compound Couple Records ===")
    
    # 1. Clarence Jackson & Ellen Perkins Jackson (#582 -> #765 & #6156)
    c.execute("SELECT photo_id FROM person_photos WHERE person_id = 582")
    photos_582 = [r[0] for r in c.fetchall()]
    for ph in photos_582:
        c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (765, ?)", (ph,))
        c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (6156, ?)", (ph,))
    
    c.execute("""
        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
        VALUES (765, 6156, 'spouse', 'Verified married couple Clarence Jackson & Ellen Perkins Jackson from photo.htm')
    """)
    c.execute("DELETE FROM person_photos WHERE person_id = 582")
    c.execute("DELETE FROM persons WHERE person_id = 582")
    print("Merged #582 into #765 (Clarence Jackson) & #6156 (Ellen Perkins Jackson)")

    # 2. Frederick Seeney & Hester Dean Seeney (#594 -> #7356 & #7401)
    c.execute("SELECT photo_id FROM person_photos WHERE person_id = 594")
    photos_594 = [r[0] for r in c.fetchall()]
    for ph in photos_594:
        c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (7356, ?)", (ph,))
        c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (7401, ?)", (ph,))
    
    c.execute("""
        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
        VALUES (7356, 7401, 'spouse', 'Verified married couple Frederick Seeney & Hester Dean Seeney from SeeneyFrederick&HesterFamily.htm')
    """)
    # Update FindAGrave and facts for Frederick Seeney if missing
    c.execute("""
        UPDATE persons 
        SET birth_info = COALESCE(NULLIF(birth_info, ''), '1880'),
            death_info = COALESCE(NULLIF(death_info, ''), '13 Jan 1889 (aged 8–9)'),
            notes = notes || ' | Verified via FindAGrave: https://www.findagrave.com/memorial/270319060/frederick-seeney'
        WHERE person_id = 7356 AND notes NOT LIKE '%270319060%'
    """)
    c.execute("DELETE FROM person_photos WHERE person_id = 594")
    c.execute("DELETE FROM persons WHERE person_id = 594")
    print("Merged #594 into #7356 (Frederick Seeney) & #7401 (Hester Dean Seeney)")

    # 3. John B Hodge & Fanny Jackson (#2271 -> #2266 & #2268)
    c.execute("""
        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
        VALUES (2266, 2268, 'associated', 'Documented together in Probate.htm record')
    """)
    c.execute("DELETE FROM person_photos WHERE person_id = 2271")
    c.execute("DELETE FROM persons WHERE person_id = 2271")
    print("Merged #2271 into #2266 (John B Hodge) & #2268 (Fanny Jackson)")

    print("\n=== Step 2: Cleaning Compound Names ===")
    # #2312 -> S. Rebecca Durham Thomas
    c.execute("""
        UPDATE persons 
        SET name = 'Rebecca Durham Thomas',
            notes = notes || ' | Documented in Probate.htm with S. Butcher'
        WHERE person_id = 2312
    """)
    print("Cleaned #2312 -> Rebecca Durham Thomas")

    # #2421 -> Harman Clark
    c.execute("""
        UPDATE persons 
        SET name = 'Harman Clark',
            notes = notes || ' | Documented with Mary Perkins & Sarah Clark in Probate.htm'
        WHERE person_id = 2421
    """)
    print("Cleaned #2421 -> Harman Clark")

    # #5043 -> Geoffrey A. Garfield Mosley
    c.execute("""
        UPDATE persons 
        SET name = 'Geoffrey A. Garfield Mosley'
        WHERE person_id = 5043
    """)
    print("Cleaned #5043 -> Geoffrey A. Garfield Mosley")

    print("\n=== Step 3: Cleaning Obituary Titles & Ages ===")
    # Obit #47: Buena "Boni" Durham, 92 -> Buena (Boni) Durham, age 92
    c.execute("""
        UPDATE obituaries 
        SET deceased_name = 'Buena (Boni) Durham',
            age = '92'
        WHERE id = 47
    """)

    # Obit #174: Milton "Nick" Carney, 71 -> Milton (Nick) Carney, age 71
    c.execute("""
        UPDATE obituaries 
        SET deceased_name = 'Milton (Nick) Carney',
            age = '71'
        WHERE id = 174
    """)

    # Obit #138 & #139: Theressa Corney "Bonnie" Swift
    c.execute("""
        UPDATE obituaries 
        SET deceased_name = 'Theressa Corney (Bonnie) Swift',
            age = '75'
        WHERE id = 139
    """)
    c.execute("DELETE FROM obituaries WHERE id = 138")

    # Obit #210: Ethelda "Ted" Street Dean
    c.execute("""
        UPDATE obituaries 
        SET deceased_name = 'Ethelda (Ted) Street Dean',
            maiden_name = 'Street'
        WHERE id = 210
    """)
    print("Cleaned obituaries #47, #139, #174, #210 and removed duplicate #138.")

    print("\n=== Step 4: Extracting Lineage Relationships from Notes ===")
    
    # 1. Robert B. Morris (#1479) & Julia Clark
    c.execute("SELECT person_id FROM persons WHERE name LIKE 'Julia Clark%'")
    jc_rows = c.fetchall()
    if jc_rows:
        jc_id = jc_rows[0][0]
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (1479, ?, 'spouse', 'Verified married couple Robert B. Morris & Julia Clark from Mitsawokett 17th C. Community')
        """, (jc_id,))
        print(f"Linked Robert B. Morris (#1479) to Julia Clark (#{jc_id})")

    # 2. John Asbury Thompson (#1681), Bartholomew Thompson (#1683), Snowden Asher Thompson (#1682)
    c.execute("SELECT person_id FROM persons WHERE name LIKE 'John W%Thompson%'")
    jwt_rows = c.fetchall()
    c.execute("SELECT person_id FROM persons WHERE name LIKE 'Sarah Ann%Thompson%' OR name LIKE 'Sarah Ann Harmon%'")
    sat_rows = c.fetchall()

    jwt_id = jwt_rows[0][0] if jwt_rows else None
    sat_id = sat_rows[0][0] if sat_rows else None

    if jwt_id and sat_id:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, 'spouse', 'Documented parents of Asbury, Bartholomew, and Asher Thompson')
        """, (jwt_id, sat_id))

    for child_id in [1681, 1682, 1683]:
        if jwt_id:
            c.execute("""
                INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                VALUES (?, ?, 'parent_of', 'Buried at Indian Mission Cemetery; son of John W. Thompson')
            """, (jwt_id, child_id))
        if sat_id:
            c.execute("""
                INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                VALUES (?, ?, 'parent_of', 'Buried at Indian Mission Cemetery; son of Sarah Ann Harmon Thompson')
            """, (sat_id, child_id))
    print("Linked Thompson brothers (#1681, #1682, #1683) to documented parents")

    # 3. Jane Harmon (#1686) & Ephraim Harmon
    c.execute("SELECT person_id FROM persons WHERE name LIKE 'Ephraim Harmon%'")
    eh_rows = c.fetchall()
    if eh_rows:
        eh_id = eh_rows[0][0]
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (1686, ?, 'spouse', 'Frank G. Speck Nanticoke informant; spouse of Ephraim Harmon')
        """, (eh_id,))
        print(f"Linked Jane Harmon (#1686) to Ephraim Harmon (#{eh_id})")

    # 4. Ferdinand Chief Sea Gull Clark (#1687) & Chief William Russell Wyniaco Clark
    c.execute("SELECT person_id FROM persons WHERE name LIKE '%Russell%Clark%' OR name LIKE '%Wyniaco%'")
    rc_rows = c.fetchall()
    if rc_rows:
        rc_id = rc_rows[0][0]
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, 1687, 'parent_of', 'Chief William Russell Wyniaco Clark father of Chief Sea Gull Clark')
        """, (rc_id,))
        print(f"Linked Chief Sea Gull Clark (#1687) to father #{rc_id}")

    conn.commit()

    c.execute("SELECT COUNT(*) FROM persons")
    print(f"Total persons in DB: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM relationships")
    print(f"Total relationships in DB: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM obituaries")
    print(f"Total obituaries in DB: {c.fetchone()[0]}")

    conn.close()
    print("Remediation completed successfully!")

if __name__ == '__main__':
    remediate()
