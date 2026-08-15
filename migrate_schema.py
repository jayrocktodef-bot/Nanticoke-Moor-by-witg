import sqlite3
import re

DB_PATH = 'preservation_output/genealogy_preservation.db'

def add_columns_if_not_exist(cursor, table, columns):
    cursor.execute(f"PRAGMA table_info({table})")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    for col_name, col_type in columns.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to {table}")

def parse_name(full_name):
    # Default values
    first = ""
    middle = ""
    maiden = ""
    last = ""
    
    # 1. Extract maiden name if in parentheses
    maiden_match = re.search(r'\((.*?)\)', full_name)
    if maiden_match:
        maiden = maiden_match.group(1).strip()
        full_name = full_name.replace(f"({maiden_match.group(1)})", "").strip()
        
    # Clean up excess spaces
    full_name = re.sub(r'\s+', ' ', full_name).strip()
    
    # 2. Split remaining parts
    parts = full_name.split()
    
    if len(parts) == 1:
        first = parts[0]
    elif len(parts) == 2:
        first = parts[0]
        last = parts[1]
    elif len(parts) >= 3:
        first = parts[0]
        last = parts[-1]
        middle = " ".join(parts[1:-1])
        
    return first, middle, maiden, last

def determine_evidence_level(notes):
    if not notes:
        return 1
    notes_lower = notes.lower()
    
    if 'dna' in notes_lower or 'genomic' in notes_lower:
        return 4
    if 'probate' in notes_lower or 'deed' in notes_lower or 'primary source' in notes_lower:
        return 3
    if 'findagrave' in notes_lower or 'census' in notes_lower or 'index' in notes_lower:
        return 2
        
    return 1

def migrate():
    print("Starting database migration...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Add new columns
    add_columns_if_not_exist(c, 'persons', {
        'first_name': 'TEXT',
        'middle_name': 'TEXT',
        'maiden_name': 'TEXT',
        'married_last_name': 'TEXT',
        'evidence_level': 'INTEGER DEFAULT 1'
    })
    
    add_columns_if_not_exist(c, 'relationships', {
        'certainty': "TEXT DEFAULT 'confirmed'"
    })
    
    # Fetch all persons and update structured names and evidence level
    c.execute("SELECT person_id, name, notes FROM persons")
    persons = c.fetchall()
    
    print(f"Migrating {len(persons)} person records...")
    
    for person_id, full_name, notes in persons:
        first, middle, maiden, last = parse_name(full_name)
        evidence = determine_evidence_level(notes)
        
        c.execute('''
            UPDATE persons 
            SET first_name = ?, middle_name = ?, maiden_name = ?, married_last_name = ?, evidence_level = ?
            WHERE person_id = ?
        ''', (first, middle, maiden, last, evidence, person_id))
        
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
