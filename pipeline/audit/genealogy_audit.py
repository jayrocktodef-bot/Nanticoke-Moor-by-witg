import sqlite3
import re
from datetime import datetime

DB_PATH = 'preservation_output/genealogy_preservation.db'

def extract_year(date_string):
    if not date_string:
        return None
    match = re.search(r'\b(1[6-9]\d{2}|20\d{2})\b', date_string)
    if match:
        return int(match.group(1))
    return None

def clear_old_audits(cursor):
    cursor.execute("DELETE FROM audit_flags")

def run_audits():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Starting automated genealogy audits...")
    clear_old_audits(c)
    
    c.execute("SELECT person_id, name, first_name, married_last_name, birth_info, death_info FROM persons")
    persons = c.fetchall()
    
    time_travel_flags = 0
    extreme_lifespan_flags = 0
    duplicate_flags = 0
    
    # 1. Date Sanity Checks (Time-Travel & Extreme Lifespan)
    parsed_persons = []
    for p in persons:
        pid, name, first, last, b_info, d_info = p
        b_year = extract_year(b_info)
        d_year = extract_year(d_info)
        
        parsed_persons.append({
            'id': pid, 'name': name, 'first': first, 'last': last,
            'b_year': b_year, 'd_year': d_year
        })
        
        if b_year and d_year:
            # Time Travel Check
            if d_year < b_year:
                c.execute('''
                    INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                    VALUES ('Logic Error', 'critical', ?, 'Death year before birth year', ?)
                ''', (pid, f"Born: {b_year}, Died: {d_year}"))
                time_travel_flags += 1
            
            # Extreme Lifespan Check
            lifespan = d_year - b_year
            if lifespan > 115:
                c.execute('''
                    INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                    VALUES ('Data Outlier', 'warning', ?, 'Extreme lifespan (>115 years)', ?)
                ''', (pid, f"Lifespan: {lifespan} years (Born {b_year}, Died {d_year})"))
                extreme_lifespan_flags += 1

    # 2. Duplicate Detection
    # Look for matching first name, last name, and birth year
    seen = {}
    for p in parsed_persons:
        if p['first'] and p['last'] and p['b_year']:
            key = f"{p['first'].lower()}|{p['last'].lower()}|{p['b_year']}"
            if key in seen:
                # Potential Duplicate Found
                duplicate_id = seen[key]
                c.execute('''
                    INSERT INTO audit_flags (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('Duplicate Candidate', 'warning', ?, ?, 'Potential duplicate profile (matching name and birth year)', ?)
                ''', (p['id'], duplicate_id, f"Key: {key}"))
                duplicate_flags += 1
            else:
                seen[key] = p['id']

    conn.commit()
    conn.close()
    
    print("\n--- AUDIT COMPLETE ---")
    print(f"Time-Travel Errors: {time_travel_flags}")
    print(f"Extreme Lifespans:  {extreme_lifespan_flags}")
    print(f"Potential Duplicates: {duplicate_flags}")
    
if __name__ == "__main__":
    run_audits()
