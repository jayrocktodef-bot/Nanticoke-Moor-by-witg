import sqlite3
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")

NON_PERSON_PATTERNS = [
    r'\bDescendants\s+of\b',
    r'\bCumberland\b',
    r'\bCo\.\s+N\.J\.\b',
    r'\bAssateague\b',
    r'\bpuzzle\b',
    r'\bROOTS\b',
    r'\bworld\s+of\b',
    r'\bconnection\b',
    r'\bApprenticeship\b',
    r'\bMortar\b',
    r'\bCemetery\b',
    r'\bChurch\b',
    r'\bMeeting\b',
    r'\bTombstones\b',
    r'\bProbate\b',
    r'\bInventory\b',
    r'\bApprentices\b',
    r'\bnamed\s+below\b',
    r'\bm\.\s+', # Marriage notation like m. Prudence
    r'\b\&\b'    # Ampersand concatenated names like Wint Carney & Emma Durham
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

    # Migrate facts & citations
    c.execute("UPDATE OR IGNORE facts SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("DELETE FROM facts WHERE person_id = ?", (source_id,))

    # Migrate audit flags
    c.execute("UPDATE OR IGNORE audit_flags SET person_id = ? WHERE person_id = ?", (target_id, source_id))
    c.execute("UPDATE OR IGNORE audit_flags SET person_id_secondary = ? WHERE person_id_secondary = ?", (target_id, source_id))

    # Delete source record
    c.execute("DELETE FROM persons WHERE person_id = ?", (source_id,))

def run_reconciliation():
    print("=== Running Audit Findings Remediation ===")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Purge Non-Person Sentence Fragments
    c.execute("SELECT person_id, name FROM persons")
    persons = c.fetchall()

    deleted_junk = 0

    for pid, name in persons:
        if not name: continue
        is_junk = False
        for pat in NON_PERSON_PATTERNS:
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
            deleted_junk += 1

    conn.commit()
    print(f"Purged {deleted_junk} non-person phrase/location entries.")

    # 2. Merge Duplicate Names Across Datasets
    c.execute("""
        SELECT name, COUNT(*) as cnt
        FROM persons
        WHERE name IS NOT NULL AND name != ''
        GROUP BY LOWER(name)
        HAVING cnt > 1
    """)
    dup_groups = c.fetchall()

    merged_duplicates = 0

    for name_str, count in dup_groups:
        c.execute("SELECT person_id, birth_info, death_info, dataset_source FROM persons WHERE LOWER(name) = LOWER(?) ORDER BY person_id ASC", (name_str,))
        records = c.fetchall()

        target_id = records[0][0]
        for src_rec in records[1:]:
            src_id = src_rec[0]
            merge_duplicate_person_records(c, src_id, target_id)
            merged_duplicates += 1

    conn.commit()
    print(f"Merged {merged_duplicates} cross-dataset duplicate person records.")

    # 3. Clean up dangling references
    c.execute("""
        DELETE FROM relationships
        WHERE person_a_id NOT IN (SELECT person_id FROM persons)
           OR person_b_id NOT IN (SELECT person_id FROM persons)
    """)
    c.execute("DELETE FROM facts WHERE person_id NOT IN (SELECT person_id FROM persons)")
    conn.commit()
    conn.close()

    print("Reconciliation complete.")

if __name__ == "__main__":
    run_reconciliation()
