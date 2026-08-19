import sqlite3
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")

KEY_SURNAMES = set([
    'Bantum', 'Bookram', 'Butcher', 'Carmean', 'Carney', 'Clark', 'Coker', 'Conaway',
    'Copes', 'Cordrey', 'Cork', 'Cottman', 'Counselor', 'Cremeen', 'Davis', 'Dean',
    'Dickerson', 'Durham', 'Francisco', 'Goldsborough', 'Green', 'Handsor', 'Hanzer',
    'Harmon', 'Hitchens', 'Hughes', 'Ingram', 'Jackson', 'Johnson', 'Kinyon', 'Loatman',
    'Miller', 'Moore', 'Morris', 'Mosley', 'Muncey', 'Norwood', 'Oakley', 'Pierce',
    'Pinder', 'Puckham', 'Reed', 'Ridgeway', 'Sammons', 'Sockum', 'Street', 'Thomas',
    'Thompson', 'Turner', 'Wilson', 'Wright'
])

SUFFIXES = set(['Sr.', 'Jr.', 'I', 'II', 'III', 'IV', 'Sr', 'Jr', 'Esq.', 'Esq'])

JUNK_PHRASES = [
    'was the', 'his wife', 'was born', 'residence', 'on feb', 'who was', 
    'later thomas', 'rev war', 'revolutionary war', 'in the', 'who died in',
    'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh'
]

def sanitize_surnames_as_first_names():
    print("=== Sanitizing Surnames Used as First Names ===")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT person_id, name, dataset_source FROM persons")
    all_persons = c.fetchall()

    deleted_count = 0
    reformatted_count = 0

    for pid, name, ds in all_persons:
        if not name:
            continue
            
        lower_name = name.lower()
        
        # 1. Delete Junk Phrase fragments
        if any(jp in lower_name for jp in JUNK_PHRASES):
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
            c.execute("DELETE FROM facts WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            deleted_count += 1
            continue

        words = [w.strip(',') for w in name.split()]
        if not words:
            continue

        first_word = words[0]
        
        # 2. Check if the first word is a known surname
        if first_word in KEY_SURNAMES:
            non_surname_words = [w for w in words if w not in KEY_SURNAMES and w not in SUFFIXES and w.lower() not in ['and', '&', 'family', 'descendants', 'kids', 'dau', 'sisters']]
            
            # Case A: Pure combination of surnames or family header placeholders -> Delete
            if len(words) >= 2 and len(non_surname_words) == 0:
                c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
                c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
                c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
                c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
                c.execute("DELETE FROM facts WHERE person_id = ?", (pid,))
                c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
                deleted_count += 1
                continue

            # Case B: Surname + Suffix (e.g., 'Mosley Sr.') -> Keep as is (or clean)
            if len(words) >= 2 and all(w in SUFFIXES for w in words[1:]):
                # Valid surname with suffix, keep format
                continue

            # Case C: Surname + Real Given Names (e.g. 'Hughes Adella Naomi') -> Reformat to 'Adella Naomi Hughes'
            if len(words) >= 2 and len(non_surname_words) > 0:
                given_part = ' '.join([w for w in words[1:] if w not in SUFFIXES])
                suffix_part = ' '.join([w for w in words[1:] if w in SUFFIXES])
                
                new_name = f"{given_part} {first_word}"
                if suffix_part:
                    new_name += f" {suffix_part}"

                new_name = new_name.strip()

                # Check if new_name already exists for another person
                c.execute("SELECT person_id FROM persons WHERE name = ? AND person_id != ?", (new_name, pid))
                existing = c.fetchone()

                if existing:
                    target_id = existing[0]
                    # Merge pid into target_id
                    c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (target_id, pid))
                    c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (target_id, pid))
                    c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

                    c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (target_id, pid))
                    c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))

                    c.execute("UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?", (target_id, pid))
                    c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))

                    c.execute("UPDATE OR IGNORE facts SET person_id = ? WHERE person_id = ?", (target_id, pid))
                    c.execute("DELETE FROM facts WHERE person_id = ?", (pid,))

                    c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
                    deleted_count += 1
                else:
                    c.execute("UPDATE persons SET name = ? WHERE person_id = ?", (new_name, pid))
                    c.execute("UPDATE facts SET value_string = ? WHERE person_id = ? AND fact_type = 'Name'", (new_name, pid))
                    reformatted_count += 1

    conn.commit()
    conn.close()

    print(f"Sanitization Complete.")
    print(f"-> Deleted {deleted_count} non-person surname combinations / phrase placeholders.")
    print(f"-> Reformatted {reformatted_count} Last-Name-First person names.")

if __name__ == "__main__":
    sanitize_surnames_as_first_names()
