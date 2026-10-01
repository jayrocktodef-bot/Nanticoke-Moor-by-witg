import sqlite3
import re
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")

JUNK_REGEX_PATTERNS = [
    r'^CC:\s*',
    r'^Date:\s*',
    r'^Subject:\s*',
    r'departed\s+this\s+life',
    r'until\s+her\s+death',
    r'sp\s+var\s+=',
    r'children\s+included:',
    r'each\s+person\s+by\s+row:',
    r'leader\s+is\s+',
    r'@.*\.net',
    r'@.*\.com',
    r'^\d+\.\s+', # Leading numbers like "1. Pauline C. Pierce"
]

def merge_duplicate_person_records(c, source_id, target_id):
    # Migrate relationships
    c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (target_id, source_id))
    c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (target_id, source_id))
    c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

    # Migrate photos
    c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("DELETE FROM person_photos WHERE person_id = ?", (source_id,))

    # Migrate obituaries
    c.execute("UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (source_id,))

    # Migrate facts
    c.execute("UPDATE OR IGNORE facts SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("DELETE FROM facts WHERE person_id = ?", (source_id,))

    # Migrate audit flags
    c.execute("UPDATE OR IGNORE audit_flags SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("UPDATE OR IGNORE audit_flags SET person_id_secondary = ? WHERE person_id_secondary = ?", (target_id, source_id))

    # Delete source record
    c.execute("DELETE FROM persons WHERE person_id = ?", (source_id,))

def run_deep_cleanup():
    print("=== Running Deep Audit Clean & Normalized Cross-Dataset Merge ===")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Purge Sentence Fragments and Email Headers
    c.execute("SELECT person_id, name FROM persons")
    all_p = c.fetchall()

    purged_junk = 0
    for p in all_p:
        pid = p['person_id']
        name = p['name']
        if not name: continue
        is_junk = False
        for pat in JUNK_REGEX_PATTERNS:
            if re.search(pat, name, re.IGNORECASE):
                is_junk = True
                break

        if is_junk:
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
            c.execute("DELETE FROM facts WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            purged_junk += 1

    conn.commit()
    print(f"Purged {purged_junk} text/email fragment entries.")

    # 2. Clean Obituary Title Quotes / Leading Numbers
    c.execute("SELECT id, deceased_name FROM obituaries")
    obits = c.fetchall()
    for ob in obits:
        oid = ob['id']
        dname = ob['deceased_name']
        if not dname: continue
        clean_d = re.sub(r'^\d+\.\s*', '', dname).strip() # Remove "1. Pauline" -> "Pauline"
        clean_d = re.sub(r'^["\']|["\']$', '', clean_d).strip() # Remove surrounding quotes
        if clean_d != dname:
            c.execute("UPDATE obituaries SET deceased_name = ? WHERE id = ?", (clean_d, oid))
    conn.commit()

    # 3. Normalized Merge of Duplicate Names
    c.execute("SELECT person_id, name FROM persons WHERE name IS NOT NULL AND name != ''")
    persons_all = c.fetchall()

    name_map = defaultdict(list)
    for p in persons_all:
        clean_name = re.sub(r'[\s\.\'-]+', '', p['name'].lower())
        if len(clean_name) > 3 and clean_name not in ['unknown', 'baby', 'infant']:
            name_map[clean_name].append(p['person_id'])

    total_merged = 0
    for key, pids in name_map.items():
        if len(pids) > 1:
            target_id = pids[0]
            for src_id in pids[1:]:
                merge_duplicate_person_records(c, src_id, target_id)
                total_merged += 1

    conn.commit()
    print(f"Successfully merged {total_merged} cross-dataset duplicate individual profiles.")

    # 4. Clean up dangling references
    c.execute("""
        DELETE FROM relationships
        WHERE person_a_id NOT IN (SELECT person_id FROM persons)
           OR person_b_id NOT IN (SELECT person_id FROM persons)
    """)
    c.execute("DELETE FROM facts WHERE person_id NOT IN (SELECT person_id FROM persons)")
    conn.commit()

    conn.close()
    print("Deep Audit Clean Complete.")

if __name__ == "__main__":
    run_deep_cleanup()
