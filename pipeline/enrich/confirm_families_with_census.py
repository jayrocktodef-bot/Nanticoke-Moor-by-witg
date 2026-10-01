#!/usr/bin/env python3
"""
confirm_families_with_census.py

Cross-references collected Delaware census schedules (1850-1950) from
frontend/public/ancestry_documents/delaware_census/*.json with the genealogical database:
1. Matches household members (Head, Wife, Children, etc.) against persons in the database.
2. Confirms and creates missing family relationships with certainty='census_confirmed'.
3. Adds primary 'Census' facts and citations for all matched individuals.
4. Safely deduplicates verified identical profiles supported by the census records.
"""

import glob
import json
import os
import re
import sqlite3

DB_PATH = 'preservation_output/genealogy_preservation.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def parse_birth_year(binfo):
    if not binfo:
        return None
    m = re.search(r'\b(1[789]\d\d|20\d\d)\b', str(binfo))
    return int(m.group(1)) if m else None

def build_person_index(c):
    c.execute('SELECT person_id, name, first_name, middle_name, married_last_name, birth_info FROM persons')
    rows = c.fetchall()
    index = []
    for pid, name, fn, mn, last, binfo in rows:
        index.append({
            'id': pid,
            'name': name.strip(),
            'name_lower': name.strip().lower(),
            'fn': (fn or '').strip().lower(),
            'mn': (mn or '').strip().lower(),
            'last': (last or '').strip().lower(),
            'birth_year': parse_birth_year(binfo)
        })
    return index

def get_or_create_census_source(c, year, collection_title, image_file, source_url):
    title = f"{year} US Federal Census - Delaware"
    if collection_title:
        title = collection_title
    c.execute("SELECT source_id FROM sources WHERE title = ?", (title,))
    row = c.fetchone()
    if row:
        return row[0]
    
    url = image_file or source_url or f"delaware_census_{year}"
    c.execute("INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)",
              (title, url, "Delaware Federal Census"))
    return c.lastrowid

def merge_persons(primary_id, duplicate_id, c):
    """
    Safely merges duplicate_id into primary_id across all foreign key tables.
    """
    if primary_id == duplicate_id:
        return

    # 1. Update relationships
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

    c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (primary_id, duplicate_id))
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

    # 4. Update facts
    c.execute("UPDATE facts SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))

    # 5. Update audit_flags
    c.execute("UPDATE audit_flags SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE audit_flags SET person_id_secondary = ? WHERE person_id_secondary = ?", (primary_id, duplicate_id))

    # 6. Update other tables
    c.execute("UPDATE face_embeddings SET person_id = ? WHERE person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE entity_matches SET person_id_moors = ? WHERE person_id_moors = ?", (primary_id, duplicate_id))
    c.execute("UPDATE entity_matches SET person_id_jackson = ? WHERE person_id_jackson = ?", (primary_id, duplicate_id))
    c.execute("UPDATE unified_photo_catalog SET primary_person_id = ? WHERE primary_person_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE photo_catalog SET primary_person_id = ? WHERE primary_person_id = ?", (primary_id, duplicate_id))

    # 7. Merge birth_info, death_info, notes
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
            new_n = f"{new_n} | Merged duplicate #{duplicate_id}: {dup_n}".strip(" |")
        c.execute("UPDATE persons SET birth_info = ?, death_info = ?, notes = ? WHERE person_id = ?",
                  (new_b, new_d, new_n, primary_id))

    c.execute("DELETE FROM persons WHERE person_id = ?", (duplicate_id,))

def main():
    conn = get_db()
    c = conn.cursor()

    print("=== Step 1: Processing Delaware Census Records ===")
    files = sorted(glob.glob('frontend/public/ancestry_documents/delaware_census/*.json'))
    print(f"Found {len(files)} census JSON schedules.")

    person_index = build_person_index(c)

    confirmed_spouse_edges = 0
    confirmed_child_edges = 0
    facts_added = 0
    matched_individuals = set()

    for fn in files:
        with open(fn) as f:
            data = json.load(f)

        hh = data.get('household', [])
        if len(hh) <= 2:
            continue

        raw_year = data.get('census_year', '')
        try:
            census_year = int(re.search(r'\b(1[789]\d\d|20\d\d)\b', str(raw_year)).group(1))
        except Exception:
            continue

        fields = data.get('fields', {})
        home_loc = fields.get(f'Home in {census_year}', fields.get('Residence', 'Delaware, USA'))
        collection_title = data.get('collection_title', f"{census_year} United States Federal Census")
        image_file = data.get('image_file', '')
        source_url = data.get('source_url', '')

        source_id = get_or_create_census_source(c, census_year, collection_title, image_file, source_url)

        # Parse household members
        members = []
        member_names = []
        for row in hh[2:]:
            if len(row) >= 3:
                name = row[0].strip()
                age_str = row[1].strip()
                rel = row[2].strip()
                member_names.append(f"{name} ({rel}, age {age_str})")

                try:
                    age = int(re.search(r'\d+', age_str).group())
                    est_by = census_year - age
                except Exception:
                    age = None
                    est_by = None

                # Disambiguate / Match
                matched_id = None
                exact = [p for p in person_index if p['name_lower'] == name.lower()]
                if len(exact) == 1:
                    matched_id = exact[0]['id']
                elif len(exact) > 1 and est_by:
                    close = [p for p in exact if p['birth_year'] and abs(p['birth_year'] - est_by) <= 5]
                    if close:
                        matched_id = close[0]['id']
                    else:
                        matched_id = exact[0]['id']
                elif not exact and est_by:
                    parts = name.split()
                    if len(parts) >= 2:
                        cfn, clast = parts[0].lower(), parts[-1].lower()
                        fuzzy = [p for p in person_index if p['fn'] == cfn and p['last'] == clast and p['birth_year'] and abs(p['birth_year'] - est_by) <= 4]
                        if len(fuzzy) == 1:
                            matched_id = fuzzy[0]['id']

                members.append({
                    'name': name,
                    'age': age_str,
                    'rel': rel,
                    'est_by': est_by,
                    'person_id': matched_id
                })
                if matched_id:
                    matched_individuals.add(matched_id)

        hh_summary = ", ".join(member_names)

        # 1. Attach Census Facts and Citations for matched members
        for m in members:
            pid = m['person_id']
            if not pid:
                continue

            # Check if this Census fact already exists
            c.execute("""
                SELECT fact_id FROM facts
                WHERE person_id = ? AND fact_type = 'Census' AND date_string = ?
            """, (pid, str(census_year)))
            existing_fact = c.fetchone()

            fact_val = f"{census_year} US Federal Census: {m['rel']}, age {m['age']}. Household: {hh_summary}"
            if not existing_fact:
                c.execute("""
                    INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
                    VALUES (?, 'Census', ?, ?, ?)
                """, (pid, str(census_year), home_loc, fact_val))
                fact_id = c.lastrowid
                facts_added += 1

                # Add citation
                ev_text = f"{collection_title}, Delaware, {home_loc}. Dwelling record #{data.get('record_id', '')}"
                c.execute("""
                    INSERT INTO citations (fact_id, source_id, evidence_text)
                    VALUES (?, ?, ?)
                """, (fact_id, source_id, ev_text))

        # 2. Confirm Family Relationships
        heads = [m for m in members if 'head' in m['rel'].lower() and m['person_id']]
        wives = [m for m in members if 'wife' in m['rel'].lower() and m['person_id']]
        children = [m for m in members if ('son' in m['rel'].lower() or 'daughter' in m['rel'].lower()) and m['person_id']]

        head_id = heads[0]['person_id'] if heads else None
        wife_id = wives[0]['person_id'] if wives else None

        # Confirm Head <-> Wife (Spouse)
        if head_id and wife_id:
            c.execute("""
                SELECT id FROM relationships
                WHERE ((person_a_id = ? AND person_b_id = ?) OR (person_a_id = ? AND person_b_id = ?))
                  AND relationship_type = 'spouse'
            """, (head_id, wife_id, wife_id, head_id))
            r_row = c.fetchone()
            ev_desc = f"Confirmed in {census_year} US Federal Census household ({home_loc})"
            if r_row:
                c.execute("""
                    UPDATE relationships
                    SET certainty = 'census_confirmed', evidence_text = ?
                    WHERE id = ?
                """, (ev_desc, r_row[0]))
            else:
                c.execute("""
                    INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text, certainty)
                    VALUES (?, ?, 'spouse', ?, 'census_confirmed')
                """, (head_id, wife_id, ev_desc))
            confirmed_spouse_edges += 1

        # Confirm Parent -> Child edges
        parent_ids = [pid for pid in [head_id, wife_id] if pid]
        for ch in children:
            ch_id = ch['person_id']
            for par_id in parent_ids:
                c.execute("""
                    SELECT id FROM relationships
                    WHERE person_a_id = ? AND person_b_id = ? AND relationship_type = 'child_of'
                """, (ch_id, par_id))
                r_row = c.fetchone()
                ev_desc = f"Confirmed in {census_year} US Federal Census as {ch['rel']} of household head ({home_loc})"
                if r_row:
                    c.execute("""
                        UPDATE relationships
                        SET certainty = 'census_confirmed', evidence_text = ?
                        WHERE id = ?
                    """, (ev_desc, r_row[0]))
                else:
                    c.execute("""
                        INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text, certainty)
                        VALUES (?, ?, 'child_of', ?, 'census_confirmed')
                    """, (ch_id, par_id, ev_desc))
                confirmed_child_edges += 1

    conn.commit()
    print(f"Matched {len(matched_individuals)} distinct individuals across census households.")
    print(f"Confirmed {confirmed_spouse_edges} spouse relationships with primary census evidence.")
    print(f"Confirmed {confirmed_child_edges} parent-child relationships with primary census evidence.")
    print(f"Created {facts_added} new primary Census facts and citations.")

    print("\n=== Step 2: Deduplicating Verified Cross-Record Profiles ===")
    VERIFIED_PROFILE_MERGES = [
        # (duplicate_id, canonical_primary_id, reason)
        (471, 119, "Francis L. Jackson duplicate of Francis Lawrence Jackson"),
        (10726, 439, "William E Jackson (1931) duplicate of William Jackson (1931)"),
        (1056, 974, "Robert Harmon duplicate of Robert K Harmon (b. 8 Jan 1859 Northwest Fork)"),
        (1045, 1039, "John W Harmon duplicate of John Wesley Harmon (b. 1820)"),
        (11206, 4121, "Anna E. Johnson (b. 14 Dec 1889) duplicate of Anna Clark Johnson"),
        (6492, 4219, "Harry N. Morgan Sr duplicate of Harry Morgan Sr"),
        (3899, 75, "Sarah Catherine Ridgeway Carter (b. 1807) duplicate of Sarah Carter (b. 1807)")
    ]

    dedup_count = 0
    for dup_id, pri_id, reason in VERIFIED_PROFILE_MERGES:
        c.execute("SELECT person_id, name FROM persons WHERE person_id = ?", (dup_id,))
        dup_row = c.fetchone()
        c.execute("SELECT person_id, name FROM persons WHERE person_id = ?", (pri_id,))
        pri_row = c.fetchone()
        if dup_row and pri_row:
            print(f"Deduplicating: #{dup_id} ({dup_row[1]}) into #{pri_id} ({pri_row[1]}) - {reason}")
            merge_persons(pri_id, dup_id, c)
            dedup_count += 1

    conn.commit()
    conn.close()
    print(f"\nDeduplication complete: merged {dedup_count} verified duplicate profiles.")

if __name__ == '__main__':
    main()
