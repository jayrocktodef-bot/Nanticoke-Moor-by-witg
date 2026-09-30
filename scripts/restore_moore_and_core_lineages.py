#!/usr/bin/env python3
"""
Restore Moore & Core Lineages Engine (scripts/restore_moore_and_core_lineages.py)
================================================================================
1. Ingests all 89 Moore individuals from Davis Family Tree.ged into genealogy_preservation.db.
2. Establishes family kinship relationships (spouses, parents, children) connecting Moore to Jackson, Green, Reed, Davis.
3. Re-ingests Elias Bookram (b. 1790) as child of Chief George Puckham and spouse of Chashe Scott.
4. Adds Oakley / Okie / Okey aliases to surname_aliases table.
"""

import os
import re
import sqlite3

BASE_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper'
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')
GED_PATH = '/home/jequan/Desktop/Davis Family Tree.ged'

def run():
    print("=== Restoring Moore and Core Lineages ===", flush=True)
    if not os.path.exists(GED_PATH):
        print(f"Error: GEDCOM not found at {GED_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Step 1: Parse GEDCOM
    with open(GED_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    indi_blocks = re.findall(r'0 @(I\d+)@ INDI\n(.*?)(?=0 @|\Z)', content, re.DOTALL)
    print(f"Loaded {len(indi_blocks)} individuals from GEDCOM.")

    # Build map of existing persons in database
    c.execute("SELECT person_id, name FROM persons")
    name_to_pid = {r[1].lower(): r[0] for r in c.fetchall()}

    indi_map = {}
    restored_moore = 0

    for gid, block in indi_blocks:
        name_m = re.search(r'1 NAME ([^\n]+)', block)
        if not name_m:
            continue
        raw_name = name_m.group(1).replace('/', '').strip()
        
        # Check if Moore
        if re.search(r'\bmoore\b', raw_name, re.IGNORECASE):
            b_m = re.search(r'1 BIRT\n2 DATE ([^\n]+)', block)
            p_m = re.search(r'2 PLAC ([^\n]+)', block)
            birth_info = ""
            if b_m: birth_info += b_m.group(1)
            if p_m: birth_info += " " + p_m.group(1)
            birth_info = birth_info.strip()

            d_m = re.search(r'1 DEAT\n2 DATE ([^\n]+)', block)
            dp_m = re.search(r'1 DEAT.*?\n2 PLAC ([^\n]+)', block, re.DOTALL)
            death_info = ""
            if d_m: death_info += d_m.group(1)
            if dp_m and "2 PLAC" in block:
                plac_match = re.search(r'1 DEAT[^\n]*\n(?:[^\n]*\n)*?2 PLAC ([^\n]+)', block)
                if plac_match:
                    death_info += " " + plac_match.group(1)
            death_info = death_info.strip()

            # Clean name for first/last
            parts = raw_name.split()
            first_name = parts[0] if parts else ""
            middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else ""
            married_last = parts[-1] if len(parts) > 1 else "Moore"

            # Check if person already exists
            existing_pid = name_to_pid.get(raw_name.lower())
            if existing_pid:
                pid = existing_pid
            else:
                c.execute("""
                    INSERT INTO persons (name, first_name, middle_name, married_last_name, birth_info, death_info, notes, dataset_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (raw_name, first_name, middle_name, married_last, birth_info, death_info, "Preserved Delmarva Moore lineage from Davis Family Tree GEDCOM", "davis_family_gedcom"))
                pid = c.lastrowid
                name_to_pid[raw_name.lower()] = pid
                restored_moore += 1

            indi_map[gid] = pid
        else:
            # Check if this person is already in DB so we can link them to Moores
            existing_pid = name_to_pid.get(raw_name.lower())
            if existing_pid:
                indi_map[gid] = existing_pid

    print(f"Restored {restored_moore} Moore individuals to database.")

    # Step 2: Establish relationships
    fam_blocks = re.findall(r'0 @(F\d+)@ FAM\n(.*?)(?=0 @|\Z)', content, re.DOTALL)
    restored_rels = 0

    for fid, fblock in fam_blocks:
        husb_m = re.search(r'1 HUSB @(I\d+)@', fblock)
        wife_m = re.search(r'1 WIFE @(I\d+)@', fblock)
        chil_ms = re.findall(r'1 CHIL @(I\d+)@', fblock)

        husb_id = indi_map.get(husb_m.group(1)) if husb_m else None
        wife_id = indi_map.get(wife_m.group(1)) if wife_m else None

        # Only insert relationship if at least one person is in indi_map (and especially Moore)
        if husb_id and wife_id:
            c.execute("""
                INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                VALUES (?, ?, 'spouses', 'Davis Family Tree GEDCOM family marriage record')
            """, (husb_id, wife_id))
            restored_rels += 1

        if husb_id:
            for cid in chil_ms:
                c_pid = indi_map.get(cid)
                if c_pid:
                    c.execute("""
                        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                        VALUES (?, ?, 'parent_of', 'Davis Family Tree GEDCOM parent-child record')
                    """, (husb_id, c_pid))
                    restored_rels += 1

        if wife_id:
            for cid in chil_ms:
                c_pid = indi_map.get(cid)
                if c_pid:
                    c.execute("""
                        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                        VALUES (?, ?, 'parent_of', 'Davis Family Tree GEDCOM parent-child record')
                    """, (wife_id, c_pid))
                    restored_rels += 1

    print(f"Restored {restored_rels} kinship ties involving Moore and connected families.")

    # Step 3: Re-ingest Elias Bookram (Puckham)
    print("\nStep 3: Re-ingesting Elias Bookram...")
    c.execute("SELECT person_id FROM persons WHERE name = 'Elias Bookram' OR name = 'Elias Puckham / Bookram'")
    existing_elias = c.fetchone()
    if not existing_elias:
        c.execute("""
            INSERT INTO persons (name, first_name, married_last_name, birth_info, source_page, notes, dataset_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "Elias Bookram",
            "Elias",
            "Bookram",
            "c. 1790",
            "census.htm",
            "Nanticoke descendant born c. 1790 in MD; relocated to Granville Co, NC; recorded as Elias Puckham (1814), Elias Puckins (1820), Elias Puckram (1824), Elisha Buckram (1830), Elias Bookram (1840). Variant of Puckham.",
            "native_american_roots_speck"
        ))
        elias_id = c.lastrowid
        print(f"  Ingested Elias Bookram (ID #{elias_id})")
    else:
        elias_id = existing_elias[0]
        print(f"  Elias Bookram already present (ID #{elias_id})")

    # Connect Elias Bookram to Chief George Puckham (#1698) and Chashe Scott (#1700)
    c.execute("SELECT person_id FROM persons WHERE name LIKE 'George Puckham%'")
    gp_row = c.fetchone()
    if gp_row:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, 'child_of', 'Descendant of Chief George Puckham & Nanticoke Puckamee village lineage')
        """, (elias_id, gp_row[0]))

    c.execute("SELECT person_id FROM persons WHERE name LIKE 'Chashe Scott%'")
    cs_row = c.fetchone()
    if cs_row:
        c.execute("""
            INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
            VALUES (?, ?, 'spouses', 'Married 24 Jun 1824 in Granville Co, NC')
        """, (elias_id, cs_row[0]))
    print("  Linked Elias Bookram to parent Chief George Puckham and spouse Chashe Scott.")

    # Step 4: Ensure surname_aliases has Oakley/Okie/Okey and Moore/Moor
    print("\nStep 4: Ensuring surname_aliases are populated...")
    aliases_to_add = [
        ("Oakley", "Oakley"),
        ("Oakley", "Okie"),
        ("Oakley", "Okey"),
        ("Oakley", "Oakey"),
        ("Puckham", "Bookram"),
        ("Puckham", "Bookrum"),
        ("Puckham", "Buckram"),
        ("Moore", "Moore"),
        ("Moore", "Moor"),
        ("Driggus", "Driggus"),
        ("Driggus", "Driggers"),
        ("Driggus", "Drigger"),
        ("Carmean", "Cremeen"),
        ("Seeney", "Seeney"),
        ("Seeney", "Seany"),
        ("Seeney", "Seney"),
        ("Cuff", "Cuff"),
        ("Cuff", "Cuffee"),
        ("Gould", "Gould"),
        ("Gould", "Gold"),
        ("Sisco", "Sisco"),
        ("Sisco", "Cisco"),
        ("Beckett", "Beckett"),
        ("Beckett", "Becket"),
        ("Morgan", "Morgan"),
        ("Carty", "Carty"),
        ("Coursey", "Coursey"),
        ("Greenage", "Greenage")
    ]
    for canon, var in aliases_to_add:
        c.execute("""
            INSERT OR IGNORE INTO surname_aliases (canonical_name, variant_name)
            VALUES (?, ?)
        """, (canon, var))
    print(f"  Added/verified {len(aliases_to_add)} aliases.")

    conn.commit()

    c.execute("SELECT COUNT(*) FROM persons")
    total_p = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    total_r = c.fetchone()[0]

    conn.close()
    print(f"\nCompleted: Database now has {total_p} persons and {total_r} kinship ties.")

if __name__ == '__main__':
    run()
