import sqlite3
import re

DB_PATH = 'preservation_output/genealogy_preservation.db'
GED_PATH = '/home/jequan/Desktop/Davis Family Tree.ged'

def restore_lineages():
    with open(GED_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Parse individuals from GEDCOM
    indi_blocks = re.findall(r'0 @(I\d+)@ INDI\n(.*?)(?=0 @|\Z)', content, re.DOTALL)
    
    surnames_to_restore = ['carmean', 'ingram', 'turner', 'cordrey']

    restored_persons = 0
    indi_map = {}

    for gid, block in indi_blocks:
        name_match = re.search(r'1 NAME ([^\n]+)', block)
        if not name_match:
            continue
        raw_name = name_match.group(1).replace('/', '').strip()
        
        # Check if name contains target surnames
        if any(s in raw_name.lower() for s in surnames_to_restore):
            # Check birth & death info
            b_match = re.search(r'1 BIRT\n2 DATE ([^\n]+)', block)
            p_match = re.search(r'2 PLAC ([^\n]+)', block)
            birth_info = ""
            if b_match: birth_info += b_match.group(1)
            if p_match: birth_info += " " + p_match.group(1)
            birth_info = birth_info.strip()

            d_match = re.search(r'1 DEAT\n2 DATE ([^\n]+)', block)
            death_info = d_match.group(1).strip() if d_match else ""

            # Check if person already exists in database
            c.execute('SELECT person_id FROM persons WHERE name = ?', (raw_name,))
            existing = c.fetchone()
            
            if existing:
                pid = existing[0]
            else:
                c.execute("""
                    INSERT INTO persons (name, birth_info, death_info, notes, dataset_source)
                    VALUES (?, ?, ?, ?, ?)
                """, (raw_name, birth_info, death_info, "Restored connected Delmarva lineage from GEDCOM", "davis_family_gedcom"))
                pid = c.lastrowid
                restored_persons += 1
                
            indi_map[gid] = pid

    # Parse families and relationships
    fam_blocks = re.findall(r'0 @(F\d+)@ FAM\n(.*?)(?=0 @|\Z)', content, re.DOTALL)
    restored_rels = 0

    for fid, fblock in fam_blocks:
        husb_m = re.search(r'1 HUSB @(I\d+)@', fblock)
        wife_m = re.search(r'1 WIFE @(I\d+)@', fblock)
        chil_ms = re.findall(r'1 CHIL @(I\d+)@', fblock)

        husb_id = indi_map.get(husb_m.group(1)) if husb_m else None
        wife_id = indi_map.get(wife_m.group(1)) if wife_m else None

        if husb_id and wife_id:
            c.execute("""
                INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                VALUES (?, ?, 'spouses', 'Restored GEDCOM family marriage record')
            """, (husb_id, wife_id))
            restored_rels += 1

        if husb_id:
            for cid in chil_ms:
                c_pid = indi_map.get(cid)
                if c_pid:
                    c.execute("""
                        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                        VALUES (?, ?, 'parent_of', 'Restored GEDCOM parent-child record')
                    """, (husb_id, c_pid))
                    restored_rels += 1

        if wife_id:
            for cid in chil_ms:
                c_pid = indi_map.get(cid)
                if c_pid:
                    c.execute("""
                        INSERT OR IGNORE INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
                        VALUES (?, ?, 'parent_of', 'Restored GEDCOM parent-child record')
                    """, (wife_id, c_pid))
                    restored_rels += 1

    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM persons")
    total_p = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    total_r = c.fetchone()[0]

    conn.close()

    print("=========================================================================")
    print("  LINEAGE RESTORATION COMPLETE!")
    print(f"  - Carmean, Ingram, Turner, Cordrey Persons Restored: {restored_persons}")
    print(f"  - Kinship Relationships Restored:                   {restored_rels}")
    print(f"  - Total Preserved Persons:                          {total_p}")
    print(f"  - Total Kinship Ties:                               {total_r}")
    print("=========================================================================")

if __name__ == '__main__':
    restore_lineages()
