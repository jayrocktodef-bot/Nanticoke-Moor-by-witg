#!/usr/bin/env python3
"""
normalize_names_and_clean_junk.py

Normalizes inverted and misordered names in the genealogy database:
1. Merges or updates inverted surname-first records (e.g. 'Carter Irving Edward' -> 'Irving Edward Carter',
   'Cuff Florence' -> 'Florence Cuff', 'Norwood-Green Christina Mae' -> 'Christina Mae Norwood-Green',
   'Counceller Ella Davis' -> 'Ella Davis Counceller', 'McCarty James' -> 'James McCarty', etc.).
2. Normalizes obituary married-name inversions (e.g. 'Dangerfield Phyllis Lorraine Durham' -> 'Phyllis Lorraine Durham Dangerfield').
3. Strips scraper artifact prefixes ('Front --', 'front--', 'Miss ', 'Mrs ', 'Sr. ', 'Jr. ').
4. Strips town suffixes mistakenly appended from obituaries ('Millsboro', 'Lewes', 'Seaford').
5. Safely merges scraper duplicate fragments ('John Wesley the' -> 'John Wesley', 'Sarah Cott the' -> 'Sarah Cott',
   'Obediah Cott the' -> 'Obediah Cott', 'David Holder' -> 'David Holder', etc.) into their primary records.
6. Prunes non-person junk records ('Check it out', 'Sincerely yours', 'High School diploma',
   'Carter kids Davis', 'Bea Davis Memorial Service', 'truly yours', 'Milford Memorial Hospital',
   'She never', 'In Cheswold...', etc.) with cascading foreign keys cleanly removed.
7. Re-parses first_name, middle_name, maiden_name, married_last_name for all modified profiles.
"""

import sqlite3
import re
import sys

DB_PATH = 'preservation_output/genealogy_preservation.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def parse_name_tokens(full_name):
    """
    Standard parser for (first_name, middle_name, maiden_name, married_last_name).
    """
    name = full_name.strip()
    suffix = ""
    for s in [' Jr.', ' Jr', ' Sr.', ' Sr', ' III', ' II', ' IV']:
        if name.endswith(s):
            name = name[:-len(s)].strip()
            suffix = s.strip()
            break

    parts = name.split()
    if not parts:
        return "", "", "", ""
    if len(parts) == 1:
        return parts[0], "", "", parts[0]
    if len(parts) == 2:
        fn = parts[0]
        last = parts[1] + (f" {suffix}" if suffix else "")
        return fn, "", "", last
    if len(parts) == 3:
        fn = parts[0]
        mn = parts[1]
        last = parts[2] + (f" {suffix}" if suffix else "")
        return fn, mn, "", last
    
    # 4+ parts: First Middle1 Middle2 Last
    fn = parts[0]
    mn = " ".join(parts[1:-1])
    last = parts[-1] + (f" {suffix}" if suffix else "")
    return fn, mn, "", last

def merge_persons(primary_id, duplicate_id, c):
    """
    Safely merges duplicate_id into primary_id across all foreign key tables.
    Handles unique constraints gracefully by deleting duplicate edges before updating.
    """
    print(f"Merging duplicate #{duplicate_id} into primary #{primary_id}...")

    # 1. Update relationships
    # If primary already has an edge to person_b with the same relationship_type, delete duplicate's edge
    c.execute("""
        DELETE FROM relationships
        WHERE person_a_id = ?
          AND EXISTS (
              SELECT 1 FROM relationships r2
              WHERE r2.person_a_id = ?
                AND r2.person_b_id = relationships.person_b_id
                AND r2.relationship_type = relationships.relationship_type
          )
    """, (duplicate_id, primary_id))

    # If primary already has an edge from person_a with the same relationship_type, delete duplicate's edge
    c.execute("""
        DELETE FROM relationships
        WHERE person_b_id = ?
          AND EXISTS (
              SELECT 1 FROM relationships r2
              WHERE r2.person_b_id = ?
                AND r2.person_a_id = relationships.person_a_id
                AND r2.relationship_type = relationships.relationship_type
          )
    """, (duplicate_id, primary_id))

    # Now safely update the remaining relationships
    c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (primary_id, duplicate_id))
    # Remove self-loops
    c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

    # 2. Update person_photos
    c.execute("""
        DELETE FROM person_photos
        WHERE person_id = ?
          AND photo_id IN (
              SELECT photo_id FROM person_photos WHERE person_id = ?
          )
    """, (duplicate_id, primary_id))
    c.execute("UPDATE person_photos SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))

    # 3. Update person_obituaries
    c.execute("""
        DELETE FROM person_obituaries
        WHERE person_id = ?
          AND obituary_id IN (
              SELECT obituary_id FROM person_obituaries WHERE person_id = ?
          )
    """, (duplicate_id, primary_id))
    c.execute("UPDATE person_obituaries SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))

    # 4. Update facts and citations
    c.execute("UPDATE facts SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))

    # 5. Update audit_flags
    c.execute("UPDATE audit_flags SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE audit_flags SET person_id_secondary = ? WHERE person_id_secondary = ?", (primary_id, duplicate_id))

    # 6. Update face_embeddings, entity_matches, photo_catalog
    c.execute("UPDATE face_embeddings SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE entity_matches SET person_id_moors = ? WHERE person_id_moors = ?", (primary_id, duplicate_id))
    c.execute("UPDATE entity_matches SET person_id_jackson = ? WHERE person_id_jackson = ?", (primary_id, duplicate_id))
    c.execute("UPDATE unified_photo_catalog SET primary_person_id = ? WHERE primary_person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE photo_catalog SET primary_person_id = ? WHERE primary_person_id = ?", (primary_id, duplicate_id))

    # 7. Merge birth_info, death_info, notes if missing on primary
    c.execute("SELECT birth_info, death_info, notes FROM persons WHERE person_id = ?", (duplicate_id,))
    dup_row = c.fetchone()
    c.execute("SELECT birth_info, death_info, notes FROM persons WHERE person_id = ?", (primary_id,))
    pri_row = c.fetchone()

    if dup_row and pri_row:
        dup_b, dup_d, dup_n = dup_row
        pri_b, pri_d, pri_n = pri_row
        new_b = pri_b or dup_b or ""
        new_d = pri_d or dup_d or ""
        new_n = pri_n or ""
        if dup_n and dup_n not in new_n:
            new_n = f"{new_n} | Merged from duplicate #{duplicate_id}: {dup_n}".strip(" |")
        c.execute("UPDATE persons SET birth_info = ?, death_info = ?, notes = ? WHERE person_id = ?",
                  (new_b, new_d, new_n, primary_id))

    # 7. Delete duplicate record from persons
    c.execute("DELETE FROM persons WHERE person_id = ?", (duplicate_id,))

def set_or_merge_name(pid, new_name, c):
    """
    Updates person pid to new_name, or if new_name is already held by another person,
    merges pid into that person.
    """
    # Check if another person already has this name
    c.execute("SELECT person_id, name FROM persons WHERE name = ? AND person_id != ?", (new_name, pid))
    existing = c.fetchone()
    if existing:
        other_pid, other_name = existing
        merge_persons(other_pid, pid, c)
        return "merged"
    else:
        fn, mn, maiden, married = parse_name_tokens(new_name)
        c.execute("""
            UPDATE persons
            SET name = ?, first_name = ?, middle_name = ?, married_last_name = ?
            WHERE person_id = ?
        """, (new_name, fn, mn, married, pid))
        return "updated"

def main():
    conn = get_db()
    c = conn.cursor()

    print("=== Step 1: Explicit Name Corrections & Inversion Normalizations ===")

    # Explicit mapping for verified individual corrections
    EXPLICIT_NAME_MAP = {
        # Surnames at start inverted:
        10915: "Irving Edward Carter",
        10918: "Charles Glendon Coker Sr.",
        10919: 'Ellsworth "Buddy" Coombs',
        10921: "Elijah Counceller",
        10922: "Ella Davis Counceller",
        10923: "Charles Willis Coursey",
        10924: "Phyllis Lorraine Coursey",
        10925: "Florence Cuff",
        10927: "Phyllis Lorraine Durham Dangerfield",
        10928: "Lular Shuler Dantzler",
        10929: "Lucinda Durham Davenport",
        10931: "Ralph Elwood Dean Sr.",
        10932: "Ellen Irene Johnson Doddato",
        10933: "David Gerald Downes",
        10936: "Harriett Cuff Edwards",
        10937: "Theresa Deborah Tilghman Fontaine",
        10938: "Timothy Leroy Fontaine",
        10940: "Mary V. Frazier",
        10941: "Valerie Goldsboro",
        10943: "Thelma Davine Loatman Gonzalez",
        10944: "Albert Gould",
        10945: "Caroline Pierce Gould",
        10947: "Abijah Gould IV",
        10948: 'Edward "Duckie" Gourley',
        10962: "Barbara Mosley Holmes",
        10963: "Julia A. Winrow Hubbard",
        10965: "Phyllis Sharon Mosley Hunter",
        10966: "Luella Durham Huntsinger",
        10969: "Elwood Johnson Jr.",
        10970: "Christine E. Mosley Jones",
        10971: "George Thomas Jones",
        10972: "Lloyd Emerson Lawson",
        10973: "Virginia C. Pierce Lee",
        10975: "Gail Street McCall",
        10977: "Edna E. Beals Morgan",
        10980: "Gertrude Webster Nelson",
        10981: "Catherine Elizabeth Morgan Norris",
        10982: "Charles Verdelle Norris",
        10983: "Christina Mae Norwood-Green",
        10984: "Laura C. Gould Pearce",
        10985: "Margaret Elizabeth Perkins",
        10986: "Ruth Baker Perkins",
        10993: "Carolyn Louise Pleasanton",
        10994: "Stacey Ridgway-Miller",
        10996: "Eugene V. Robinson",
        10998: "Ella Mae Bailey Scott",
        10999: "Edison Emerson Steward",
        11000: "Shirley Still",
        11001: "William Clement Still",
        11004: "Earl Paul Street Sr.",
        11005: "Theressa Corney Swift",
        11007: "Channing Richard Tucker",
        11008: "Ruth E. Pierce Valentine",
        11009: "Mary Elizabeth Jackson Ward",
        11010: "Millie L Draine Warren",
        11011: "Catherine Nellie Mosley Watson",
        11012: "Janet Morris Watson",
        11013: "Ord Victor Winrow",

        # General inverted / misordered names
        2073: "James McCarty",
        4433: "Thomas Cuff",
        7530: "Thomas Carter",
        2619: "Hazel Ella Sammons Morgan",
        3357: "Brittany Bernice Hovington Morgan",
        5168: "Brian Mott Morgan",

        # Prefix stripping
        4556: "Elaine Davis",
        6344: "David Holder",
        20: "Maria Reed",
        6203: "Maude Jackson",
        7206: "Blanche Hughes Hickerson",

        # Suffix town stripping
        11187: "Jacob W. Draine",
        11190: "Lincoln Harmon Sr.",
        11191: "Eunice E. Harmon",
        11197: "Matilda J. Harmon",
        11202: "Philip Harrison Jackson",
        11204: "William Arthur Jackson",
        11212: "Edgar C. Morris",
        11229: "Bertha Mae Streett",
        11231: "Burton C. Street",
        11240: "George H. Webb",

        # Trailing scraper junk stripping
        11390: "Robert B. Morris",
        11574: "John Morgan",
        11796: "Ida Patience Johnson",
        11636: "Mary Vincent",
        70: "Elmira",
        372: "Mary Vincent",
        411: "John",
        11627: "Mamie",
        11650: "Sarah Hewes",
        11815: "Larry Kellam",
        11768: "James Sockum",
        11769: "Levin Sockum",
        11642: "Samuel Hansor",

        # Specific column realignments
        5177: "Betty Davis Terry",
        5191: "Elaine Davis Blackwell",
        5265: "William Henry Davis Jr."
    }

    updated_count = 0
    merged_count = 0
    for pid, new_name in EXPLICIT_NAME_MAP.items():
        res = set_or_merge_name(pid, new_name, c)
        if res == "updated":
            updated_count += 1
        elif res == "merged":
            merged_count += 1

    print(f"Explicit map processed: {updated_count} updated, {merged_count} merged.")

    print("\n=== Step 2: Merge Known Trailing Fragment Duplicates ===")
    KNOWN_FRAGMENT_MERGES = [
        (11476, 7),     # 'Lopeman the' -> 'John Lopeman'
        (11478, 8),     # 'John Wesley the' -> 'John Wesley'
        (11480, 13),    # 'Sarah Cott the' -> 'Sarah Cott'
        (11482, 14),    # 'Obediah Cott the' -> 'Obediah Cott'
        (11688, 315),   # 'Edward Morgan and' -> 'Edward Morgan'
        (11709, 286),   # 'Peregrine Cork and' -> 'Peregrine Cork'
        (11810, 2247),  # 'Robert Miller and' -> 'Robert Miller'
        (11818, 31),    # 'James McCarty and' -> 'James McCarty'
    ]

    for dup_id, pri_id in KNOWN_FRAGMENT_MERGES:
        c.execute("SELECT person_id FROM persons WHERE person_id = ?", (dup_id,))
        if c.fetchone():
            merge_persons(pri_id, dup_id, c)

    print("\n=== Step 3: Prune Non-Person Junk Records ===")
    JUNK_PERSON_IDS = [
        201,   # 'Check it out'
        4239,  # 'Sincerely yours'
        4482,  # 'High School diploma'
        4572,  # 'Carter kids Davis'
        4789,  # 'Bea Davis Memorial Service'
        7792,  # 'truly yours'
        11220, # 'Milford Memorial Hospital'
        11497, # 'She never'
        11587, # 'possibly the'
        11181, # 'In Cheswold Del Carney'
        11199, # 'In Cheswold Hughes'
        11215, # 'In Cheswold Morris'
        11748, # 'as the'
        11749, # 'William and'
        11491, # 'Seeney an'
        7604,  # 'Miss or Mrs. Regua'
        6363   # 'Widow of Stanley Monts'
    ]

    for j_id in JUNK_PERSON_IDS:
        c.execute("SELECT name FROM persons WHERE person_id = ?", (j_id,))
        row = c.fetchone()
        if not row:
            continue
        name_str = row[0]

        # Cascade cleanup: child tables first
        c.execute("DELETE FROM citations WHERE fact_id IN (SELECT fact_id FROM facts WHERE person_id = ?)", (j_id,))
        c.execute("DELETE FROM facts WHERE person_id = ?", (j_id,))
        c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (j_id, j_id))
        c.execute("DELETE FROM person_photos WHERE person_id = ?", (j_id,))
        c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (j_id,))
        c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (j_id, j_id))
        c.execute("DELETE FROM face_embeddings WHERE person_id = ?", (j_id,))
        c.execute("DELETE FROM entity_matches WHERE person_id_moors = ? OR person_id_jackson = ?", (j_id, j_id))
        c.execute("UPDATE unified_photo_catalog SET primary_person_id = NULL WHERE primary_person_id = ?", (j_id,))
        c.execute("UPDATE photo_catalog SET primary_person_id = NULL WHERE primary_person_id = ?", (j_id,))
        c.execute("DELETE FROM persons WHERE person_id = ?", (j_id,))
        print(f"Pruned junk person #{j_id} ({name_str}) and cleaned linked records.")

    conn.commit()
    conn.close()
    print("\nAll name normalizations, duplicate merges, and junk prunings complete!")

if __name__ == '__main__':
    main()
