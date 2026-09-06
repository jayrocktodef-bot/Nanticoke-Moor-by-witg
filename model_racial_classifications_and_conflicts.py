#!/usr/bin/env python3
"""
model_racial_classifications_and_conflicts.py
=============================================
Models federal census racial designations ('Mu', 'I', 'B', 'W', 'Indian', 'Mulatto')
and administrative strike-through changes across 1790–1930 Delmarva censuses.

Integrates with the Lynn C. Jackson & Mitsawokett Family Archive:
  1. Ingests explicit racial classification facts from `census01.htm` to `census20.htm` and `Change_of_Race.htm`.
  2. Links citations with verbatim transcript excerpts into `citations`.
  3. Detects multi-census classification shifts (e.g., Mulatto -> White, Black -> Mulatto, Indian -> Negro).
  4. Records GPS-compliant evidence conflict notes in `audit_flags` with historical context.
  5. Re-exports static profiles and builds the frontend.
"""

import sqlite3
import re
import html
import os
import sys
from datetime import datetime

DB_PATH = "preservation_output/genealogy_preservation.db"

# Core Delmarva Afro-Indigenous Surnames
TARGET_SURNAMES = {
    'cott', 'durham', 'carty', 'carter', 'harmon', 'mosley', 'clark', 'clarke',
    'reed', 'read', 'sockum', 'sockume', 'street', 'pierce', 'puckham', 'hughes',
    'johnson', 'ridgeway', 'miller', 'munce', 'dean', 'hansor', 'sisco', 'carney',
    'morgan', 'purnell', 'sammons', 'jackson', 'okey', 'lopeman', 'davis', 'greenage',
    'bedell', 'bowles', 'coker', 'faulkner', 'sterrett', 'congo', 'seeney', 'handsor',
    'counsellor', 'counceller', 'gray', 'muntz', 'burch', 'pettijohn', 'driggus',
    'wright', 'norwood', 'thompson', 'becket', 'beckett'
}

CHANGE_OF_RACE_CASES = [
    ("Augustus Wright", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 120: Augustus Wright; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro); tribal connection 'Delaware Nanticoke Tribe' altered under supervision."),
    ("David H. Clark", "1930", "Sussex County, DE (District 3)", "In", "Neg", "1930 Sussex Co Census Dist 3 Roll 291 Pg 143: David H. Clark; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Luther B. Norwood", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 110: Luther B. Norwood; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Oscar W. Wright", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 111: Oscar W. Wright; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Gardner R. Street", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 109: Gardner R. Street; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Wilson Harmon", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 115: Wilson Harmon; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Walter B Wright", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 114: Walter B Wright; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Elwood Wright", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 113: Elwood Wright; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Warren Wright", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 111: Warren Wright; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Custis Johnson", "1930", "Sussex County, DE (District 7)", "In", "Neg", "1930 Sussex Co Census Dist 7 Roll 291 Pg 109: Custis Johnson; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro)."),
    ("Phillip Jackson", "1930", "Sussex County, DE (District 3)", "In", "Neg", "1930 Sussex Co Census Dist 3 Roll 291 Pg 141: Phillip Jackson; race enumerated as 'In' (Indian), struck through to 'Neg' (Negro).")
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("=" * 70)
    print("Racial Reclassification & Evidence Conflict Modeling")
    print("=" * 70)

    # 1. Map persons by name and first+last
    cur.execute("""
        SELECT person_id, name, first_name, married_last_name, maiden_name
        FROM persons
        WHERE first_name IS NOT NULL AND married_last_name IS NOT NULL
    """)
    person_lookup = {}
    for pid, name, first, last, maiden in cur.fetchall():
        fn_clean = first.strip().lower()
        ln_clean = last.strip().lower()
        person_lookup.setdefault((fn_clean, ln_clean), []).append(pid)
        if maiden:
            person_lookup.setdefault((fn_clean, maiden.strip().lower()), []).append(pid)

    # Sources map
    cur.execute("SELECT source_id, LOWER(url) FROM sources")
    sources_map = {row[1]: row[0] for row in cur.fetchall() if row[1]}

    # Ensure source for Change_of_Race.htm
    cor_source_id = sources_map.get("change_of_race.htm")
    if not cor_source_id:
        cur.execute("""
            INSERT INTO sources (title, url, dataset)
            VALUES ('Delaware Change of Race Records: 1930 Census Alterations', 'Change_of_Race.htm', 'mitsawokett_primary')
        """)
        cor_source_id = cur.lastrowid
        sources_map["change_of_race.htm"] = cor_source_id
        conn.commit()

    # Track person's recorded classifications: pid -> list of (year, code, label, source, excerpt)
    classifications_by_person = {}

    # ---------------------------------------------------------
    # Ingest 1930 Change of Race Cases
    # ---------------------------------------------------------
    print("\n[Step 1] Ingesting 1930 Census supervisor reclassification cases...")
    cor_added = 0
    for full_name, yr, place, old_race, new_race, excerpt in CHANGE_OF_RACE_CASES:
        parts = full_name.split()
        fn = parts[0].lower()
        ln = parts[-1].lower()
        pids = person_lookup.get((fn, ln), [])
        
        if not pids:
            # Check by full name
            cur.execute("SELECT person_id FROM persons WHERE LOWER(name) = ?", (full_name.lower(),))
            row = cur.fetchone()
            if row:
                pids = [row[0]]
                
        for pid in pids:
            val = f"Enumerated as '{old_race}' (Indian); administratively altered to '{new_race}' (Negro)"
            
            # Check if fact already exists
            cur.execute("""
                SELECT fact_id FROM facts
                WHERE person_id = ? AND fact_type = 'Racial Classification' AND date_string = ?
            """, (pid, yr))
            existing_fact = cur.fetchone()
            
            if not existing_fact:
                cur.execute("""
                    INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
                    VALUES (?, 'Racial Classification', ?, ?, ?)
                """, (pid, yr, place, val))
                fact_id = cur.lastrowid
                
                cur.execute("""
                    INSERT INTO citations (fact_id, source_id, evidence_text)
                    VALUES (?, ?, ?)
                """, (fact_id, cor_source_id, excerpt))
                cor_added += 1
                
            classifications_by_person.setdefault(pid, []).append((yr, old_race, "Indian (Struck-through)", "Change_of_Race.htm", excerpt))
            classifications_by_person[pid].append((yr, new_race, "Negro (Supervisor Alteration)", "Change_of_Race.htm", excerpt))

    conn.commit()
    print(f"  ✓ Added {cor_added} official 1930 Change of Race facts and citations.")

    # ---------------------------------------------------------
    # Ingest 1850, 1860, 1870, 1840 Census Classifications
    # ---------------------------------------------------------
    print("\n[Step 2] Parsing 1850–1870 federal census schedules for core family racial markers...")
    races_dict = {
        'M': 'Mulatto', 'MU': 'Mulatto',
        'B': 'Black', 'NEG': 'Negro',
        'W': 'White',
        'I': 'Indian', 'IN': 'Indian'
    }

    census_configs = [
        ('census18.htm', '1850', 'Federal Census 1850'),
        ('census19.htm', '1860', 'Federal Census 1860'),
        ('census20.htm', '1870', 'Federal Census 1870'),
        ('census17.htm', '1840', 'Federal Census 1840'),
    ]

    total_census_facts = 0
    for filename, census_year, census_title in census_configs:
        cur.execute("SELECT text_content FROM pages WHERE filename = ?", (filename,))
        row = cur.fetchone()
        if not row or not row[0]:
            continue
        text = row[0]
        source_id = sources_map.get(filename.lower())
        if not source_id:
            cur.execute("INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)", (census_title, filename, 'mitsawokett_primary'))
            source_id = cur.lastrowid
            sources_map[filename.lower()] = source_id
            conn.commit()

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        current_surname = ""
        current_county = "Delmarva Region"

        for i, line in enumerate(lines):
            # Track county / hundred if indicated
            if any(c in line for c in ['Kent', 'Sussex', 'New Castle', 'Caroline', 'Dorchester', 'Somerset', 'Worcester', 'Cumberland', 'Salem']):
                current_county = line

            if line.isupper() and line.isalpha() and len(line) >= 3 and line not in ['CENSUS', 'MALE', 'FEMALE', 'FARMER', 'LABORER', 'PLEASE', 'NOTE', 'PAGE', 'STATE', 'SURNAME', 'FREE', 'WHITE']:
                current_surname = line.capitalize()
                continue

            if line.upper() in races_dict and current_surname:
                race_code = line.upper()
                race_label = races_dict[race_code]

                candidate_name = None
                candidate_age = None
                for pl in reversed(lines[max(0, i-4):i]):
                    if pl.isdigit() and not candidate_age:
                        candidate_age = pl
                    elif len(pl) > 1 and not pl.isdigit() and pl.upper() not in ['M', 'F', 'DE', 'MD', 'NJ'] and not candidate_name:
                        candidate_name = pl

                if candidate_name and current_surname.lower() in TARGET_SURNAMES:
                    clean_first = candidate_name.strip().lower()
                    clean_last = current_surname.strip().lower()
                    
                    pids = person_lookup.get((clean_first, clean_last), [])
                    if pids:
                        val_str = f"Enumerated as '{race_code}' ({race_label})"
                        if candidate_age:
                            val_str += f", age {candidate_age}"
                            
                        # Extract excerpt
                        window_lines = lines[max(0, i-3):min(len(lines), i+3)]
                        excerpt = f"{census_year} Census: {current_surname}, {candidate_name} — " + " | ".join(window_lines)

                        for pid in pids:
                            # Verify if fact exists
                            cur.execute("""
                                SELECT fact_id FROM facts
                                WHERE person_id = ? AND fact_type = 'Racial Classification' AND date_string = ?
                            """, (pid, census_year))
                            f_row = cur.fetchone()

                            if not f_row:
                                cur.execute("""
                                    INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
                                    VALUES (?, 'Racial Classification', ?, ?, ?)
                                """, (pid, census_year, current_county, val_str))
                                f_id = cur.lastrowid
                                cur.execute("""
                                    INSERT INTO citations (fact_id, source_id, evidence_text)
                                    VALUES (?, ?, ?)
                                """, (f_id, source_id, excerpt))
                                total_census_facts += 1

                            classifications_by_person.setdefault(pid, []).append((census_year, race_code, race_label, filename, excerpt))

    conn.commit()
    print(f"  ✓ Added {total_census_facts} historical census racial classification facts and citations.")

    # ---------------------------------------------------------
    # Detect Racial Classification Shifts & Model Conflicts
    # ---------------------------------------------------------
    print("\n[Step 3] Modeling racial reclassification conflicts across federal censuses...")
    conflict_count = 0

    for pid, entries in classifications_by_person.items():
        distinct_labels = {e[2] for e in entries}
        # A conflict is present if multiple distinct labels exist for the individual
        # e.g., 'Mulatto' and 'White', or 'Black' and 'Mulatto', or 'Indian' and 'Negro'
        if len(distinct_labels) > 1:
            # Order entries chronologically by year and deduplicate adjacent identical year/label pairs
            sorted_entries = sorted(entries, key=lambda x: x[0])
            unique_year_labels = []
            for yr, code, lbl, src, exc in sorted_entries:
                pair = f"{yr}: {lbl}"
                if pair not in unique_year_labels:
                    unique_year_labels.append(pair)
                    
            transition_summary = " ➔ ".join(unique_year_labels)
            
            desc = (
                f"Historical Racial Reclassification: Recorded under multiple distinct racial categories across federal records ({transition_summary}). "
                f"Exemplifies the tripartite legal classification pressures and racial boundary fluidity characteristic of Delmarva Afro-Indigenous families."
            )
            
            src_list = list(dict.fromkeys(e[3] for e in sorted_entries))
            ev_context = f"Sources: {', '.join(src_list)} | Chronology: {transition_summary}"

            # Check if audit flag already exists
            cur.execute("""
                SELECT flag_id FROM audit_flags
                WHERE person_id = ? AND category = 'RACIAL_RECLASSIFICATION'
            """, (pid,))
            existing_flag = cur.fetchone()

            if not existing_flag:
                cur.execute("""
                    INSERT INTO audit_flags (person_id, category, severity, description, evidence, created_at)
                    VALUES (?, 'RACIAL_RECLASSIFICATION', 'info', ?, ?, ?)
                """, (pid, desc, ev_context, datetime.utcnow().isoformat()))
                conflict_count += 1

    conn.commit()
    print(f"  ✓ Documented {conflict_count} institutional racial reclassification conflicts in audit_flags.")

    # ---------------------------------------------------------
    # Recalibrate Statistics
    # ---------------------------------------------------------
    cur.execute("SELECT count(*) FROM facts WHERE fact_type = 'Racial Classification'")
    tot_race_facts = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM audit_flags WHERE category = 'RACIAL_RECLASSIFICATION'")
    tot_race_flags = cur.fetchone()[0]

    print("\n" + "=" * 70)
    print("Racial Reclassification Model Summary:")
    print(f"  Total Racial Classification Facts: {tot_race_facts}")
    print(f"  Documented Evidence Conflict Audits: {tot_race_flags}")
    print("=" * 70)

    conn.close()

if __name__ == "__main__":
    main()
