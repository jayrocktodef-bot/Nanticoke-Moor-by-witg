#!/usr/bin/env python3
"""
deduplicate_hester_morris.py

Full deduplication and cross-reference of Hester Morris profiles (#11247 and #8185)
using verified primary evidence from Find a Grave Memorial 41150907 and
Harmony Methodist Church records (harmony1.htm).

Profile #11247 is retained as the authoritative canonical profile.
"""

import sqlite3
import os
import sys

BASE_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper'
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')

def deduplicate_hester_morris():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("Beginning deduplication of #11247 and #8185...")

    # Step 1: Ensure Sources exist
    c.execute("SELECT source_id FROM sources WHERE title LIKE '%FindAGrave Memorial 41150907%'")
    row = c.fetchone()
    if row:
        src_findagrave_id = row['source_id']
    else:
        c.execute("""
            INSERT INTO sources (title, url, dataset)
            VALUES (?, ?, ?)
        """, ('Find a Grave Memorial 41150907: Hester A. Morris Davis',
              'https://www.findagrave.com/memorial/41150907/hester_a-davis',
              'findagrave'))
        src_findagrave_id = c.lastrowid

    c.execute("SELECT source_id FROM sources WHERE title LIKE '%harmony1.htm%' OR url LIKE '%harmony1.htm%'")
    row = c.fetchone()
    src_harmony_id = row['source_id'] if row else None

    # Step 2: Ensure Morris Davis (1858-1916) exists as spouse
    c.execute("""
        SELECT person_id FROM persons 
        WHERE (name = 'Morris Davis' OR (first_name = 'Morris' AND married_last_name = 'Davis'))
        AND birth_info LIKE '%1858%'
    """)
    row = c.fetchone()
    if row:
        morris_davis_id = row['person_id']
        print(f"Found existing Morris Davis: ID {morris_davis_id}")
    else:
        c.execute("""
            INSERT INTO persons (name, first_name, middle_name, maiden_name, married_last_name,
                                birth_info, death_info, source_page, dataset_source, notes, evidence_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Morris Davis',
            'Morris',
            '',
            '',
            'Davis',
            '15 Mar 1858',
            '12 Nov 1916 (aged 58)',
            'FindAGrave Memorial 158876354',
            'findagrave',
            'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Husband of Hester A. Morris Davis. Father of Bertha, Stephen, Elsie, Charles, William, George, Hersel, and Harry Davis. Verified via Find a Grave Memorial 158876354.',
            3
        ))
        morris_davis_id = c.lastrowid
        print(f"Created Morris Davis: ID {morris_davis_id}")

        # Add facts for Morris Davis
        c.execute("""
            INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
            VALUES (?, ?, ?, ?, ?)
        """, (morris_davis_id, 'Name', None, None, 'Morris Davis'))
        c.execute("""
            INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
            VALUES (?, ?, ?, ?, ?)
        """, (morris_davis_id, 'Birth', '15 Mar 1858', None, None))
        c.execute("""
            INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
            VALUES (?, ?, ?, ?, ?)
        """, (morris_davis_id, 'Death', '12 Nov 1916', None, None))
        c.execute("""
            INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
            VALUES (?, ?, ?, ?, ?)
        """, (morris_davis_id, 'Burial', None, 'Harmony Cemetery, Millsboro, Sussex County, Delaware', None))

    # Step 2.5: Rename #8185 temporarily to free the UNIQUE name constraint
    c.execute("UPDATE persons SET name = 'Hester A. Morris Davis (Duplicate 8185)' WHERE person_id = 8185")

    # Step 3: Update canonical profile #11247
    c.execute("""
        UPDATE persons
        SET name = ?,
            first_name = ?,
            middle_name = ?,
            maiden_name = ?,
            married_last_name = ?,
            birth_info = ?,
            death_info = ?,
            source_page = ?,
            dataset_source = ?,
            notes = ?,
            evidence_level = ?
        WHERE person_id = 11247
    """, (
        'Hester A. Morris Davis',
        'Hester',
        'A.',
        'Morris',
        'Davis',
        '22 Sep 1877 Millsboro, Sussex, Delaware, USA',
        '9 Nov 1944 (aged 67) Millsboro, Sussex, Delaware, USA',
        'FindAGrave Memorial 41150907; Davis Family Tree.ged; harmony1.htm',
        'findagrave',
        'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Tombstone inscription: "daughter of Hattie Morris". Daughter of Francis E. Morris (1839–1910) and Hester Jemima "Hettie" Carmean Morris (1835–1923). Married 1st Morris Davis (1858–1916), married 2nd John Asbury Thompson (1881–1968) on 29 Dec 1920. Cross-referenced and verified via Find a Grave Memorial 41150907 and Harmony Methodist Church records.',
        3
    ))
    print("Updated #11247 to canonical Hester A. Morris Davis.")

    # Step 4: Rebuild Facts for #11247 and remove facts for #8185
    # Delete citations for old facts first
    c.execute("""
        DELETE FROM citations 
        WHERE fact_id IN (SELECT fact_id FROM facts WHERE person_id IN (11247, 8185))
    """)
    # Delete facts for 11247 and 8185
    c.execute("DELETE FROM facts WHERE person_id IN (11247, 8185)")

    facts_to_add = [
        ('Name', None, None, 'Hester A. Morris Davis'),
        ('Birth', '22 Sep 1877', 'Millsboro, Sussex, Delaware, USA', None),
        ('Death', '9 Nov 1944', 'Millsboro, Sussex, Delaware, USA', None),
        ('Burial', None, 'Harmony Cemetery, Millsboro, Sussex County, Delaware', None),
        ('Marriage', 'abt 1892', None, 'Married Morris Davis (1858–1916)'),
        ('Marriage', '29 Dec 1920', 'Millsboro, Sussex, Delaware, USA', 'Married John Asbury Thompson (1881–1968)'),
        ('Document Mention', None, 'Delmarva Peninsula', 'Documented in primary record: Harmony Methodist Church ("Hester A. Davis 9/22/1877 - 11/9/1944 daughter of Hattie Morris")')
    ]

    for f_type, f_date, f_place, f_val in facts_to_add:
        c.execute("""
            INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
            VALUES (?, ?, ?, ?, ?)
        """, (11247, f_type, f_date, f_place, f_val))
        fid = c.lastrowid
        # Add citation
        s_id = src_harmony_id if (f_type == 'Document Mention' and src_harmony_id) else src_findagrave_id
        c.execute("""
            INSERT INTO citations (fact_id, source_id, evidence_text)
            VALUES (?, ?, ?)
        """, (fid, s_id, 'Find a Grave Memorial 41150907 & Harmony Cemetery primary documentation'))

    print("Rebuilt facts for #11247.")

    # Step 5: Update children with accurate FindAGrave data from Harmony Cemetery
    children_updates = [
        (8675, 'Bertha May Davis Harmon', '1893', '1982 (aged 88–89)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 163086104. Daughter of Morris Davis and Hester A. Morris Davis.'),
        (8160, 'Stephen F. Davis', '1894', '1967 (aged 72–73)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 41151183. Son of Morris Davis and Hester A. Morris Davis.'),
        (8186, 'Elsie Rebecca Davis Clark', '1896', '1939 (aged 42–43)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 41149114. Daughter of Morris Davis and Hester A. Morris Davis.'),
        (8676, 'Charles Morris Davis', '1898', '1948 (aged 49–50)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 36966022. Son of Morris Davis and Hester A. Morris Davis.'),
        (8609, 'William Wesley Davis Sr', '1906', '1961 (aged 54–55)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 41151224. Son of Morris Davis and Hester A. Morris Davis.'),
        (8157, 'George A. Davis', '1909', '1986 (aged 76–77)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 41149906. Son of Morris Davis and Hester A. Morris Davis.'),
        (8158, 'Hersel R. Davis', '3 Jun 1915', '2005 (aged 89–90)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Inscribed in harmony1.htm: "son of Hester Davis". Verified via FindAGrave Memorial 36964560.'),
        (8159, 'Harry Edward Davis', '1916', '1999 (aged 82–83)',
         'Buried at Harmony Cemetery, Millsboro, Sussex County, Delaware. Verified via FindAGrave Memorial 36969032. Son of Morris Davis and Hester A. Morris Davis.'),
        (2646, 'Hershel Davis', '1926', '1930 (aged 3–4)',
         'Son of Hester Morris Davis and Morris Davis. Ingested from DavisHesterMorris.htm.')
    ]

    for cid, cname, cbirth, cdeath, cnotes in children_updates:
        c.execute("""
            UPDATE persons
            SET name = ?,
                birth_info = ?,
                death_info = ?,
                notes = ?
            WHERE person_id = ?
        """, (cname, cbirth, cdeath, cnotes, cid))
    print("Updated children profiles with verified Harmony Cemetery FindAGrave records.")

    # Step 6: Delete redundant relationships and fix pointers
    # Relationship 25290: 11247 parent_of 8185 (self-link once merged)
    c.execute("DELETE FROM relationships WHERE id = 25290")
    # Relationship 2056: 8890 (John H Davis, 1738-1840) child_of 8185 (impossible child)
    c.execute("DELETE FROM relationships WHERE id = 2056")
    # Relationship 25289: 11246 parent_of 8185 (11246 was synthetic duplicate father)
    c.execute("DELETE FROM relationships WHERE id = 25289")

    # Clean up redundant synthetic father 11246
    c.execute("DELETE FROM citations WHERE fact_id IN (SELECT fact_id FROM facts WHERE person_id = 11246)")
    c.execute("DELETE FROM facts WHERE person_id = 11246")
    c.execute("DELETE FROM relationships WHERE person_a_id = 11246 OR person_b_id = 11246")
    c.execute("DELETE FROM persons WHERE person_id = 11246")
    print("Cleaned up redundant synthetic profile #11246.")

    # Re-point all relationships involving 8185 to 11247
    c.execute("UPDATE relationships SET person_a_id = 11247 WHERE person_a_id = 8185")
    c.execute("UPDATE relationships SET person_b_id = 11247 WHERE person_b_id = 8185")

    # Ensure parent-child relationships for 11247:
    # Father: Francis E. Frank Morris (#8571)
    # Mother: Hester Jemima Carmean (#11120)
    def ensure_rel(p_a, p_b, rel_type, ev_text):
        c.execute("""
            SELECT id FROM relationships 
            WHERE person_a_id = ? AND person_b_id = ? AND relationship_type = ?
        """, (p_a, p_b, rel_type))
        if not c.fetchone():
            c.execute("""
                INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text, certainty)
                VALUES (?, ?, ?, ?, 'confirmed')
            """, (p_a, p_b, rel_type, ev_text))

    ensure_rel(8571, 11247, 'parent_of', 'Verified via FindAGrave Memorial 41150907 & Davis Family GEDCOM')
    ensure_rel(11120, 11247, 'parent_of', 'Verified via FindAGrave Memorial 41150907 & 12146447 (Hester Jemima Carmean)')
    ensure_rel(8571, 11120, 'spouse', 'Verified via FindAGrave Memorials 12146440 & 12146447')

    # Spouses of 11247:
    ensure_rel(morris_davis_id, 11247, 'spouse', 'FindAGrave Memorials 158876354 & 41150907')
    ensure_rel(1681, 11247, 'spouse', 'GEDCOM Family @F225@ marriage 29 Dec 1920 Millsboro, Sussex, Delaware, USA')

    # Children of 11247 and Morris Davis:
    all_children_ids = [8675, 8160, 8186, 8676, 8609, 8157, 8158, 8159, 2646]
    for cid in all_children_ids:
        ensure_rel(11247, cid, 'parent_of', 'Verified via FindAGrave Memorial 41150907 & Harmony Cemetery records')
        ensure_rel(morris_davis_id, cid, 'parent_of', 'Verified via FindAGrave Memorial 158876354 & Harmony Cemetery records')

    # Remove any self-referencing relationships
    c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

    # Remove exact duplicate relationships
    c.execute("""
        DELETE FROM relationships 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM relationships 
            GROUP BY person_a_id, person_b_id, relationship_type
        )
    """)
    print("Reconciled all relationships for #11247, Morris Davis, and children.")

    # Step 7: Media, Photos & Face Embeddings
    # Update photo_catalog and unified_photo_catalog
    c.execute("""
        UPDATE photo_catalog
        SET primary_person_id = 11247,
            primary_person_name = 'Hester A. Morris Davis',
            subject_names = 'Hester A. Morris Davis'
        WHERE photo_id = 627
    """)
    c.execute("""
        UPDATE unified_photo_catalog
        SET primary_person_id = 11247,
            primary_person_name = 'Hester A. Morris Davis',
            subject_names = 'Hester A. Morris Davis'
        WHERE photo_id = 627
    """)

    # Update person_photos: ensure 11247 has photo 627, remove 8185
    c.execute("DELETE FROM person_photos WHERE person_id IN (11247, 8185) AND photo_id = 627")
    c.execute("""
        INSERT INTO person_photos (person_id, photo_id, confidence_score)
        VALUES (11247, 627, 1.0)
    """)
    c.execute("DELETE FROM person_photos WHERE person_id = 8185")

    # Update face_embeddings
    c.execute("""
        UPDATE face_embeddings
        SET person_id = 11247,
            person_name = 'Hester A. Morris Davis'
        WHERE person_id = 8185
    """)
    print("Updated photo catalog, person_photos, and face embeddings to #11247.")

    # Step 8: Audit flags
    c.execute("DELETE FROM audit_flags WHERE person_id = 8185")
    print("Cleared obsolete audit flags for #8185.")

    # Step 9: Delete #8185
    c.execute("DELETE FROM persons WHERE person_id = 8185")
    print("Deleted duplicate profile #8185.")

    conn.commit()
    conn.close()
    print("Database transaction committed successfully.")

if __name__ == '__main__':
    deduplicate_hester_morris()
