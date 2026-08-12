import sqlite3
import re
from html import unescape
import sys
sys.path.insert(0, '.')
from archive_naming_rules import get_clean_surname

CORE_SURNAMES = {
    'harmon', 'durham', 'sockum', 'ridgeway', 'carney', 'davis', 'counselor',
    'mosley', 'muncey', 'thompson', 'wright', 'johnson', 'jackson', 'morris',
    'clark', 'sammons', 'moore', 'dean', 'carmean', 'coker', 'pierce', 'street',
    'wilson', 'green', 'hanzer', 'ingram', 'turner', 'cordrey', 'cork', 'loatman',
    'francisco', 'bantum', 'copes', 'puckham', 'pinder', 'kinyon', 'bookram',
    'butcher', 'reed', 'miller', 'oakley', 'norwood', 'hitchens', 'handsor',
    'goldsborough', 'cottman', 'conaway', 'cremeen', 'dickerson', 'thomas'
}

SUFFIXES = {'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v', 'esq', 'esq.'}

def normalize_person_name(name):
    """
    Converts surname-first inverted names to standard First Name Middle Surname format.
    Example: "Hanzer Bishop James E" -> "Bishop James E. Hanzer"
    Example: "Durham Benjamin Robert Jr" -> "Benjamin Robert Durham Jr."
    Example: "Carney Charlotte H. Saunders" -> "Charlotte H. Saunders Carney"
    """
    if not name:
        return name
        
    raw = unescape(name).strip()
    words = raw.split()
    if len(words) < 2:
        return raw

    first_word_clean = words[0].strip('.,;:\"\'()').lower()
    
    if first_word_clean in CORE_SURNAMES:
        rest = list(words[1:])
        
        suffix_part = ""
        if rest and rest[-1].strip('.,;:\"\'()').lower() in SUFFIXES:
            suf = rest.pop().strip('.,;')
            if suf.lower() in ('jr', 'sr'):
                suf = suf.capitalize() + '.'
            elif suf.lower() in ('ii', 'iii', 'iv', 'v'):
                suf = suf.upper()
            suffix_part = " " + suf

        if rest:
            surname_proper = words[0].strip('.,;:\"\'()').capitalize()
            new_given = " ".join(rest)
            
            if rest[-1].strip('.,;:\"\'()').lower() == first_word_clean:
                rest.pop()
                new_given = " ".join(rest)
                
            normalized = f"{new_given} {surname_proper}{suffix_part}".strip()
            return normalized

    return raw

def merge_duplicate_person(conn, target_pid, duplicate_pid):
    """
    Merges duplicate_pid into target_pid cleanly across all relational tables.
    """
    c = conn.cursor()
    # Update relationships
    c.execute('UPDATE OR IGNORE relationships SET person_a_id = ? WHERE person_a_id = ?', (target_pid, duplicate_pid))
    c.execute('UPDATE OR IGNORE relationships SET person_b_id = ? WHERE person_b_id = ?', (target_pid, duplicate_pid))
    c.execute('DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?', (duplicate_pid, duplicate_pid))

    # Update person_photos
    c.execute('UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?', (target_pid, duplicate_pid))
    c.execute('DELETE FROM person_photos WHERE person_id = ?', (duplicate_pid,))

    # Update person_obituaries
    c.execute('UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?', (target_pid, duplicate_pid))
    c.execute('DELETE FROM person_obituaries WHERE person_id = ?', (duplicate_pid,))

    # Delete duplicate person record
    c.execute('DELETE FROM persons WHERE person_id = ?', (duplicate_pid,))

def run_name_normalization():
    conn = sqlite3.connect('preservation_output/genealogy_preservation.db')
    c = conn.cursor()

    c.execute('SELECT person_id, name FROM persons ORDER BY person_id ASC')
    persons = c.fetchall()

    name_map = {}
    normalized_count = 0
    merged_count = 0

    for pid, orig_name in persons:
        name_map[orig_name] = pid

    for pid, orig_name in persons:
        # Check if person still exists (might have been merged)
        c.execute('SELECT person_id FROM persons WHERE person_id = ?', (pid,))
        if not c.fetchone():
            continue

        norm_name = normalize_person_name(orig_name)
        if norm_name != orig_name:
            # Check if normalized name conflicts with existing person
            c.execute('SELECT person_id FROM persons WHERE name = ?', (norm_name,))
            existing = c.fetchone()
            
            if existing and existing[0] != pid:
                target_pid = existing[0]
                merge_duplicate_person(conn, target_pid, pid)
                merged_count += 1
            else:
                c.execute('UPDATE persons SET name = ? WHERE person_id = ?', (norm_name, pid))
                normalized_count += 1

    # Also normalize deceased names in obituaries table
    c.execute('SELECT id, deceased_name FROM obituaries')
    obits = c.fetchall()
    obit_norm_count = 0
    for oid, dname in obits:
        norm_d = normalize_person_name(dname)
        if norm_d != dname:
            obit_norm_count += 1
            c.execute('UPDATE obituaries SET deceased_name = ? WHERE id = ?', (norm_d, oid))

    conn.commit()
    print(f'===========================================================')
    print(f'  NAME NORMALIZATION ENGINE COMPLETE!')
    print(f'  - Person Profiles Normalized:  {normalized_count}')
    print(f'  - Duplicate Profiles Merged:    {merged_count}')
    print(f'  - Obituary Deceased Normalized: {obit_norm_count}')
    print(f'===========================================================')
    conn.close()

if __name__ == '__main__':
    run_name_normalization()
