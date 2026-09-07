#!/usr/bin/env python3
"""
attach_single_person_photos_and_documents.py
=============================================
Identifies photos and documents associated with a single individual,
and attaches that person's profile ID and name directly to the photo/document
catalog schema (unified_photo_catalog, photo_catalog) and links them in person_photos.

Covers:
1. Existing single-person links in person_photos (sets primary_person_id & primary_person_name)
2. Specific high-value document/photo archives:
   - William Henry Davis Jr (DavisWHJrFuneralPgm, DavisWHJrFuneral13, DavisWHJrRetirement -> person_id 4867)
   - 1930 Census schedules (Augustus Wright, Custis Johnson, Oscar Wright, Phillip Jackson, etc.)
   - Diplomas, single-person obituaries, funeral programs, death certificates, and retirement photos
3. Generalized single-person name matching from filenames and captions against the 3,820 indexed persons.
"""

import os
import re
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
API_DIR = os.path.join(BASE_DIR, "frontend", "public", "api")

NOISE_WORDS = {
    'and', 'with', 'family', 'families', 'reunion', 'group', 'kids', 'babes',
    'children', 'unk', 'unknown', 'unknowns', 'photo', 'photos', 'picture',
    'pictures', 'copy', 'series', 'clan', 'census', 'deed', 'will', 'record',
    'probate', 'tombstone', 'cemetery', 'delaware', 'maryland', 'jersey',
    'county', 'township', 'church', 'school', 'hospital', 'homeplace'
}

SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'esq'}
HONORIFICS = {'dr', 'mr', 'mrs', 'miss', 'ms', 'rev', 'capt', 'col', 'elder', 'deacon'}

def clean_token(t):
    return re.sub(r'[^a-zA-Z]', '', t).strip().lower()

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Ensure columns exist
    for tbl in ['unified_photo_catalog', 'photo_catalog']:
        c.execute(f"PRAGMA table_info({tbl})")
        cols = [r[1] for r in c.fetchall()]
        if 'primary_person_id' not in cols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN primary_person_id INTEGER REFERENCES persons(person_id)")
        if 'primary_person_name' not in cols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN primary_person_name TEXT")
    conn.commit()

    # 2. Index all persons
    c.execute("""
        SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, birth_info, death_info
        FROM persons
    """)
    all_persons = c.fetchall()
    persons_by_id = {p[0]: p for p in all_persons}

    persons_index = {}
    persons_by_first_last = {}
    for p in all_persons:
        pid, name, fn, mn, maiden, married, birth, death = p
        clean = re.sub(r'[^a-zA-Z\s]', ' ', name)
        words = [clean_token(w) for w in clean.split() if clean_token(w)]
        words_no_title = [w for w in words if w not in HONORIFICS]
        
        suffix = words_no_title[-1] if (words_no_title and words_no_title[-1] in SUFFIXES) else None
        core_words = words_no_title[:-1] if suffix else words_no_title

        if len(core_words) >= 2:
            first = core_words[0]
            last = core_words[-1]
            middles = core_words[1:-1]
            
            surnames = {last}
            if married and len(married) > 1:
                surnames.add(clean_token(married))
            if maiden and len(maiden) > 1:
                surnames.add(clean_token(maiden))

            persons_index[pid] = {
                'id': pid,
                'name': name,
                'first': first,
                'middles': middles,
                'surnames': surnames,
                'suffix': suffix,
                'birth': birth or '',
                'death': death or ''
            }
            for s in surnames:
                persons_by_first_last.setdefault((first, s), []).append(pid)

    print(f"Loaded and indexed {len(all_persons)} persons.")

    # 3. Populate existing single-person links from person_photos
    c.execute("""
        SELECT pp.photo_id, pp.person_id
        FROM person_photos pp
        GROUP BY pp.photo_id
        HAVING COUNT(DISTINCT pp.person_id) = 1
    """)
    existing_single = c.fetchall()
    print(f"Setting primary person for {len(existing_single)} already-linked single-person photos...")
    for ph_id, pid in existing_single:
        p_name = persons_by_id[pid][1]
        c.execute("UPDATE unified_photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (pid, p_name, ph_id))
        c.execute("UPDATE photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (pid, p_name, ph_id))
    conn.commit()

    # 4. Specific high-confidence mappings for known unlinked archives
    specific_mappings = {
        # William Henry Davis Jr (photo_id 2807: funeral pgm, 2806: funeral 13, 679: retirement)
        2807: 4867, # Davis_Whjr_Funeral_Pgm.jpg
        2806: 4867, # Davis_Whjr_Funeral_13.jpg
        679:  4867, # Davis_Whjr_Retirement.jpg
        
        # 1930 Census X-Indian records
        2634: 11266, # Augustus Wright
        2636: 1709,  # Custis Johnson
        2637: 1708,  # Elwood Wright
        2640: 1706,  # Oscar Wright
        2641: 1710,  # Phillip Jackson
        2643: 1707,  # Walter B Wright
        2644: 1705,  # Warren Wright
        2645: 1711,  # Wilson Harmon
        
        # Specific single-person diplomas and articles
        2449: 4619,  # Williams_Hazel_Diploma -> Hazel Williams
        2013: 4181,  # Pierce_William_Sojourner_Article_1 -> William Sojourner Pierce
        2014: 4181,  # Pierce_William_Sojourner_Article_2 -> William Sojourner Pierce
    }

    # Verify and apply specific mappings
    for ph_id, pid in specific_mappings.items():
        if pid in persons_by_id:
            p_name = persons_by_id[pid][1]
            c.execute("UPDATE unified_photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (pid, p_name, ph_id))
            c.execute("UPDATE photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (pid, p_name, ph_id))
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, ?, 1.0)", (pid, ph_id))
            print(f"  [Explicit Match] Photo #{ph_id} -> {p_name} (#{pid})")
    conn.commit()

    # 5. Entity resolution for remaining unlinked single-person photos & documents
    c.execute("""
        SELECT photo_id, category, normalized_filename, original_filename, subject_names, surname
        FROM unified_photo_catalog
        WHERE primary_person_id IS NULL
    """)
    unmatched_rows = c.fetchall()
    print(f"Evaluating {len(unmatched_rows)} remaining unlinked/unassigned catalog items...")

    auto_matched = 0
    for ph_id, cat, norm, orig, subj, cat_sn in unmatched_rows:
        base = os.path.splitext(norm)[0]
        base_clean = base.replace('-', '_').replace(' ', '_')
        
        # Multi-person exclusion check
        has_multi = bool(re.search(r'(\b|_)(and|with|family|families|reunion|group|kids|babes|children|unk|unknowns?)(_|\b)', base_clean, re.I))
        if has_multi:
            continue

        raw_tokens = [clean_token(t) for t in base_clean.split('_') if clean_token(t)]
        tokens = [t for t in raw_tokens if t not in NOISE_WORDS and not t.isdigit() and len(t) > 1]
        
        if len(tokens) < 2:
            continue

        ph_suffix = tokens[-1] if (tokens and tokens[-1] in SUFFIXES) else None
        c_tokens = tokens[:-1] if ph_suffix else tokens

        matched_pid = None

        # Pattern A: <Surname>_<First> (e.g. Davis_Wilson, Carey_Charles, Miller_Debrix)
        cand_a = persons_by_first_last.get((c_tokens[1], c_tokens[0])) if len(c_tokens) >= 2 else None
        if cand_a and len(cand_a) == 1:
            pid = cand_a[0]
            p_info = persons_index[pid]
            if not ph_suffix or p_info['suffix'] == ph_suffix:
                matched_pid = pid

        # Pattern B: <Surname>_<First> with middle (e.g. Carney_Ernest_Clarence)
        if not matched_pid and len(c_tokens) >= 3:
            cand_b = persons_by_first_last.get((c_tokens[1], c_tokens[0]))
            if cand_b and len(cand_b) == 1:
                pid = cand_b[0]
                p_info = persons_index[pid]
                if not ph_suffix or p_info['suffix'] == ph_suffix:
                    matched_pid = pid

        # Pattern C: <First>_<Surname> (e.g. Wilson_Davis, Charles_Burden)
        if not matched_pid and len(c_tokens) >= 2:
            cand_c = persons_by_first_last.get((c_tokens[0], c_tokens[-1]))
            if cand_c and len(cand_c) == 1:
                pid = cand_c[0]
                p_info = persons_index[pid]
                if not ph_suffix or p_info['suffix'] == ph_suffix:
                    matched_pid = pid

        # Pattern D: Check subject_names if it contains a single human name
        if not matched_pid and subj and len(subj) > 3:
            subj_clean = re.sub(r'[^a-zA-Z\s]', ' ', subj)
            subj_tokens = [clean_token(w) for w in subj_clean.split() if clean_token(w)]
            subj_tokens = [w for w in subj_tokens if w not in HONORIFICS and w not in NOISE_WORDS]
            if len(subj_tokens) == 2:
                # Try First Last
                cand_d = persons_by_first_last.get((subj_tokens[0], subj_tokens[1]))
                if cand_d and len(cand_d) == 1:
                    matched_pid = cand_d[0]
                # Try Last First
                if not matched_pid:
                    cand_d2 = persons_by_first_last.get((subj_tokens[1], subj_tokens[0]))
                    if cand_d2 and len(cand_d2) == 1:
                        matched_pid = cand_d2[0]

        if matched_pid:
            p_name = persons_by_id[matched_pid][1]
            c.execute("UPDATE unified_photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (matched_pid, p_name, ph_id))
            c.execute("UPDATE photo_catalog SET primary_person_id = ?, primary_person_name = ? WHERE photo_id = ?", (matched_pid, p_name, ph_id))
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, ?, 1.0)", (matched_pid, ph_id))
            auto_matched += 1

    conn.commit()
    print(f"Auto-matched and attached {auto_matched} additional single-person photos and documents!")

    # 6. Verify total single-person photos now attached
    c.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE primary_person_id IS NOT NULL")
    total_attached = c.fetchone()[0]
    print(f"Total catalog items with direct profile ID attached: {total_attached}")

    # 7. Update transcription JSON files for documents
    transcriptions_dir = os.path.join(API_DIR, "transcriptions")
    if os.path.exists(transcriptions_dir):
        c.execute("""
            SELECT photo_id, primary_person_id, primary_person_name, subject_names, normalized_filename
            FROM unified_photo_catalog
            WHERE primary_person_id IS NOT NULL
        """)
        attached_items = c.fetchall()
        updated_json_count = 0

        for ph_id, pid, pname, subj, norm in attached_items:
            json_file = os.path.join(transcriptions_dir, f"{ph_id}.json")
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    data["person_id"] = pid
                    data["person_name"] = pname

                    # Check if line already present
                    person_line = f"PRIMARY SUBJECT / PERSON: {pname} (Profile #{pid})"
                    lines = data.get("lines", [])
                    if lines and not any("PRIMARY SUBJECT / PERSON" in l for l in lines):
                        # Insert right after date
                        insert_idx = min(4, len(lines))
                        lines.insert(insert_idx, person_line)
                        data["lines"] = lines
                        data["full_text"] = "\n".join(lines)

                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    updated_json_count += 1
                except Exception as e:
                    print(f"Error updating {json_file}: {e}")

        print(f"Updated {updated_json_count} transcription JSON files with person_id and person_name.")

    conn.close()
    print("Done attaching single person profile IDs!")

if __name__ == "__main__":
    main()
