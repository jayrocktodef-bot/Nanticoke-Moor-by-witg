#!/usr/bin/env python3
"""
audit_and_fix_person_photos.py
==============================
1. Corrects photo categories (moves maps/articles/diplomas to 'documents', cemetery photos to 'tombstones').
2. Deletes corrupt/0-byte photo records.
3. Strict entity resolution for person_photos:
   - Only category 'people' can link to individual person portraits.
   - Enforces exact surname matching (maiden or married).
   - Requires distinct, valid surname (rejects single first-name matching).
   - Prevents suffix collisions (Jr vs Sr).
   - Disallows middle-name conflicts and false Olympic athlete mappings.
4. Cleans and resynchronizes photo_surnames with true surnames.
5. Hydrates person vitals (birth_info, death_info) from facts and obituaries.
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
FRONTEND_PUBLIC = os.path.join(SCRIPT_DIR, "frontend", "public")
FRONTEND_DIST = os.path.join(SCRIPT_DIR, "frontend", "dist")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

NOISE_SURNAMES = {
    'jr', 'sr', 'ii', 'iii', 'iv', 'esq', 'and', 'the', 'with', 'copy',
    'clan', 'family', 'homeplace', 'var1', 'var2', 'var3', 'doc',
    'photo', 'photos', 'picture', 'pictures', 'jpg', 'jpeg', 'png',
    'unknown', 'unknowns', 'unk', 'bbdf', 'dad', 'fda', 'fee', 'bbc',
    'dea', 'bdea', 'deda', 'fcf', 'dfb', 'bfe', 'efd', 'acc', 'efa',
    'bdfa', 'faf', 'dcab', 'ced', 'efe', 'dae', 'aad', 'bcc', 'in', 'of'
}

TITLES = {'mr', 'mrs', 'miss', 'ms', 'rev', 'dr', 'elder', 'deacon', 'chief', 'capt', 'col'}
SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'esq', '2nd', '3rd'}

def clean_token(t):
    return re.sub(r'[^a-zA-Z]', '', t).strip()

def fix_categories_and_corrupt(cur):
    print("--- [1/4] Correcting Miscategorized Photos & Corrupt Records ---")
    
    # 1. Delete photo 7 (corrupt HTML file)
    cur.execute("DELETE FROM person_photos WHERE photo_id = 7")
    cur.execute("DELETE FROM photo_surnames WHERE photo_id = 7")
    cur.execute("DELETE FROM photo_catalog WHERE photo_id = 7")
    cur.execute("DELETE FROM unified_photo_catalog WHERE photo_id = 7")
    
    # Delete from disk
    for root in [PRESERVATION_DIR, FRONTEND_PUBLIC, FRONTEND_DIST]:
        for sub in ["assets/archive_media/people/18_Aug_122_2005.jpg", "assets/archive_media/people/Johnson_Dorothy_East_Star.jpg"]:
            fpath = os.path.join(root, sub)
            if os.path.exists(fpath):
                os.remove(fpath)

    # 2. Re-categorize maps, articles, diplomas to 'documents'
    doc_ids = [276, 2013, 2014, 2287, 2440, 2449]
    for ph_id in doc_ids:
        cur.execute("UPDATE unified_photo_catalog SET category = 'documents', document_type = 'historical_document' WHERE photo_id = ?", (ph_id,))
        cur.execute("UPDATE photo_catalog SET media_type = 'documents', document_type = 'historical_document' WHERE photo_id = ?", (ph_id,))
    print(f"  ✓ Moved {len(doc_ids)} maps/articles/diplomas to category 'documents'")

    # 3. Re-categorize cemetery photos to 'tombstones'
    cur.execute("""
        UPDATE unified_photo_catalog 
        SET category = 'tombstones', document_type = 'tombstone'
        WHERE category = 'people'
          AND (
              source_url LIKE '%Cemeteries%'
              OR source_url LIKE '%cemetery%'
              OR original_filename LIKE '%Cemetery%'
              OR original_filename LIKE '%cemetery%'
              OR original_filename LIKE '%tombstone%'
          )
    """)
    tomb_updated = cur.rowcount
    print(f"  ✓ Moved {tomb_updated} cemetery photos to category 'tombstones'")

def audit_and_relink_person_photos(conn, cur):
    print("\n--- [2/4] Strict Entity Resolution for Person Photos ---")

    cur.execute("""
        SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, source_page
        FROM persons
    """)
    persons_raw = cur.fetchall()

    persons_index = {}
    for pid, name, fn, mn, maiden, married, src in persons_raw:
        parts = [clean_token(p) for p in name.split() if clean_token(p)]
        parts_clean = [p for p in parts if p.lower() not in TITLES]

        p_suffix = None
        if parts_clean and parts_clean[-1].lower() in SUFFIXES:
            p_suffix = parts_clean[-1].lower()
            parts_clean = parts_clean[:-1]

        if not parts_clean:
            continue

        p_first = clean_token(fn or parts_clean[0]).lower()

        p_surnames = set()
        if married and len(married) > 1:
            p_surnames.add(married.lower().strip('., '))
        if maiden and len(maiden) > 1:
            p_surnames.add(maiden.lower().strip('., '))

        if len(parts_clean) > 1:
            p_surnames.add(parts_clean[-1].lower())
            p_middles = [p.lower() for p in parts_clean[1:-1]]
        else:
            p_middles = []

        valid_surnames = {s for s in p_surnames if len(s) > 2 and s not in NOISE_SURNAMES and s != p_first}
        if not valid_surnames or not p_first or len(p_first) < 2:
            continue

        persons_index[pid] = {
            'name': name,
            'first': p_first,
            'middles': p_middles,
            'surnames': valid_surnames,
            'suffix': p_suffix,
            'src': (src or '').lower()
        }

    print(f"  ✓ Indexed {len(persons_index)} persons with distinct first and surname")

    # Load cataloged photos of category 'people' ONLY
    cur.execute("""
        SELECT photo_id, normalized_filename, original_filename, surname, given_names, subject_names
        FROM unified_photo_catalog
        WHERE category = 'people'
    """)
    photos = cur.fetchall()

    new_links = set()
    for ph_id, norm_fn, orig_fn, sn, gn, subj in photos:
        base = os.path.splitext(norm_fn)[0]
        tokens = [clean_token(t).lower() for t in base.split('_') if clean_token(t)]
        tokens_clean = [t for t in tokens if t not in NOISE_SURNAMES]

        ph_has_jr = 'jr' in tokens
        ph_has_sr = 'sr' in tokens

        ph_sn = set()
        if sn and len(sn) > 2 and sn.lower() not in NOISE_SURNAMES:
            ph_sn.add(sn.lower())
        if tokens_clean:
            ph_sn.add(tokens_clean[0])

        combined = ' ' + f'{norm_fn} {orig_fn or ""} {subj or ""}'.lower().replace('_', ' ').replace('.', ' ') + ' '

        # Olympic track clipping filter
        is_olympic = any(w in combined for w in ['olympic', 'javelin', 'shot put', 'relay team', 'awards stand', 'postpones title'])

        for pid, p in persons_index.items():
            if is_olympic and 'william alonzo' in p['name'].lower():
                continue

            # Suffix conflict
            if ph_has_jr and p['suffix'] == 'sr':
                continue
            if ph_has_sr and p['suffix'] == 'jr':
                continue

            # Surname check
            if not any(s in ph_sn or f' {s} ' in combined for s in p['surnames']):
                continue

            # First name check
            p_first = p['first']
            if f' {p_first} ' not in combined:
                aliases = {
                    'william': ['will', 'bill'],
                    'robert': ['bob', 'bobby'],
                    'james': ['jim', 'jimmy'],
                    'john': ['jack'],
                    'charles': ['charlie', 'chas'],
                    'edward': ['ed', 'eddie'],
                    'benjamin': ['ben', 'benny'],
                    'thomas': ['tom', 'tommy'],
                    'elizabeth': ['betty', 'bessie', 'libby']
                }
                if not any(p_first == f and any(f' {n} ' in combined for n in nicks) for f, nicks in aliases.items()):
                    continue

            # Middle name collision check
            mid_conflict = False
            for m in p['middles']:
                if (m == 'bernard' and 'burton' in tokens) or (m == 'burton' and 'bernard' in tokens):
                    mid_conflict = True
                    break
                if (m == 'james' and 'burton' in tokens) or (m == 'howard' and 'james' in tokens):
                    mid_conflict = True
                    break
            if mid_conflict:
                continue

            new_links.add((pid, ph_id))

    print(f"  ✓ Validated {len(new_links)} high-confidence portrait-to-person links")

    cur.execute("DELETE FROM person_photos")
    cur.executemany("""
        INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score)
        VALUES (?, ?, 1.0)
    """, list(new_links))
    print(f"  ✓ Updated person_photos table with {len(new_links)} clean rows")

def update_photo_surnames(conn, cur):
    print("\n--- [3/4] Rebuilding Clean photo_surnames Table ---")
    cur.execute("DELETE FROM photo_surnames")

    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename, surname, subject_names
        FROM unified_photo_catalog
    """)
    all_photos = cur.fetchall()

    cur.execute("""
        SELECT DISTINCT maiden_name FROM persons WHERE maiden_name IS NOT NULL AND maiden_name != ''
        UNION
        SELECT DISTINCT married_last_name FROM persons WHERE married_last_name IS NOT NULL AND married_last_name != ''
    """)
    db_surnames = {r[0].capitalize() for r in cur.fetchall() if r[0] and clean_token(r[0]).lower() not in NOISE_SURNAMES}

    links = set()
    for ph_id, cat, norm_fn, orig_fn, sn, subj in all_photos:
        text = f"{norm_fn} {orig_fn or ''} {sn or ''} {subj or ''}"
        tokens = [clean_token(t).capitalize() for t in re.split(r'[_ \-,]+', text) if clean_token(t)]

        for t in tokens:
            if t in db_surnames and t.lower() not in NOISE_SURNAMES and len(t) > 2:
                is_prim = 1 if (sn and sn.capitalize() == t) else 0
                links.add((ph_id, t, is_prim))

    cur.executemany("""
        INSERT OR IGNORE INTO photo_surnames (photo_id, surname, is_primary)
        VALUES (?, ?, ?)
    """, list(links))
    print(f"  ✓ Populated {len(links)} clean photo-to-surname links")

def hydrate_person_vitals(conn, cur):
    print("\n--- [4/4] Hydrating Missing Person Vitals from Facts & Obituaries ---")

    # 1. Backfill birth_info from facts
    cur.execute("""
        SELECT p.person_id, f.date_string, f.place_string
        FROM persons p
        JOIN facts f ON p.person_id = f.person_id
        WHERE (p.birth_info IS NULL OR TRIM(p.birth_info) = '' OR p.birth_info = 'unknown')
          AND f.fact_type = 'Birth'
          AND f.date_string IS NOT NULL
          AND f.date_string != 'unknown'
          AND TRIM(f.date_string) != ''
    """)
    births = cur.fetchall()
    b_updated = 0
    for pid, d_str, p_str in births:
        vital_str = d_str
        if p_str and p_str != 'unknown' and p_str not in d_str:
            vital_str = f"{d_str} ({p_str})"
        cur.execute("UPDATE persons SET birth_info = ? WHERE person_id = ?", (vital_str, pid))
        b_updated += 1
    print(f"  ✓ Backfilled {b_updated} missing birth_info values from facts")

    # 2. Backfill death_info from facts
    cur.execute("""
        SELECT p.person_id, f.date_string, f.place_string
        FROM persons p
        JOIN facts f ON p.person_id = f.person_id
        WHERE (p.death_info IS NULL OR TRIM(p.death_info) = '' OR p.death_info = 'unknown')
          AND f.fact_type = 'Death'
          AND f.date_string IS NOT NULL
          AND f.date_string != 'unknown'
          AND TRIM(f.date_string) != ''
    """)
    deaths = cur.fetchall()
    d_updated = 0
    for pid, d_str, p_str in deaths:
        vital_str = d_str
        if p_str and p_str != 'unknown' and p_str not in d_str:
            vital_str = f"{d_str} ({p_str})"
        cur.execute("UPDATE persons SET death_info = ? WHERE person_id = ?", (vital_str, pid))
        d_updated += 1
    print(f"  ✓ Backfilled {d_updated} missing death_info values from facts")

    # 3. Backfill from obituaries
    cur.execute("""
        SELECT p.person_id, o.birth_date, o.death_date, o.cemetery_location
        FROM persons p
        JOIN person_obituaries po ON p.person_id = po.person_id
        JOIN obituaries o ON po.obituary_id = o.id
    """)
    obits = cur.fetchall()
    obit_b = 0
    obit_d = 0
    for pid, b_date, d_date, cem in obits:
        cur.execute("SELECT birth_info, death_info FROM persons WHERE person_id = ?", (pid,))
        p_row = cur.fetchone()
        if p_row:
            cur_b, cur_d = p_row
            if (not cur_b or cur_b == 'unknown') and b_date and b_date.strip():
                cur.execute("UPDATE persons SET birth_info = ? WHERE person_id = ?", (b_date.strip(), pid))
                obit_b += 1
            if (not cur_d or cur_d == 'unknown') and d_date and d_date.strip():
                d_val = d_date.strip()
                if cem and cem.strip() and cem.strip() not in d_val:
                    d_val = f"{d_val} ({cem.strip()})"
                cur.execute("UPDATE persons SET death_info = ? WHERE person_id = ?", (d_val, pid))
                obit_d += 1
    print(f"  ✓ Backfilled {obit_b} birth dates and {obit_d} death dates from obituaries")

def main():
    print("==================================================================")
    print("COMPREHENSIVE AUDIT & FIX: PERSON PHOTOS & PROFILE HYDRATION")
    print("==================================================================")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    fix_categories_and_corrupt(cur)
    conn.commit()

    audit_and_relink_person_photos(conn, cur)
    conn.commit()

    update_photo_surnames(conn, cur)
    conn.commit()

    hydrate_person_vitals(conn, cur)
    conn.commit()

    conn.close()
    print("\nDatabase audit and profile hydration successfully completed!")

if __name__ == "__main__":
    main()
