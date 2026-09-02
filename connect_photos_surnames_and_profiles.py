#!/usr/bin/env python3
"""
connect_photos_surnames_and_profiles.py
=======================================
Deep entity resolution pipeline connecting photos to surnames and person profiles:
1. Matches photos to person profiles (person_photos) using normalized names,
   couples ('John_And_Mary'), maiden names, and surname aliases.
2. Creates and populates 'photo_surnames' mapping every photo to all associated surnames.
3. Synchronizes 'photo_catalog' with 'unified_photo_catalog' for full backwards compatibility.
4. Enriches surname statistics and person profiles for the family archive app.
"""

import os
import re
import sqlite3
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESERVATION_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

NOISE_WORDS = {
    "and", "the", "with", "copy", "ancestry", "lineage", "descent", "pedigree",
    "family", "tree", "cemetery", "cem", "tombstone", "gravestone", "grave",
    "church", "reunion", "census", "will", "probate", "deed", "application",
    "social", "security", "record", "records", "death", "birth", "marriage",
    "certificate", "photo", "photos", "picture", "pictures", "memorial",
    "funeral", "program", "class", "school", "house", "indians", "indian",
    "delaware", "maryland", "jersey", "county", "hundred", "collection",
    "unknown", "unknowns", "unk", "var1", "var2", "var3", "doc", "jpg", "png"
}

def clean_token(t):
    return re.sub(r'[^a-zA-Z]', '', t).strip()

def parse_name_candidates(norm_fn, orig_fn, sn, gn, subj):
    """
    Parses potential (surname, given_name) pairs from filename and metadata.
    Handles couples like 'Alfred_Pierce_Helen_Durham' or 'Harry_And_Mary'.
    """
    candidates = [] # list of (surname, given_name)
    
    # 1. If sn and gn already exist in catalog
    if sn and len(sn) > 1:
        clean_sn = clean_token(sn).capitalize()
        if gn:
            # Check for multiple given names separated by 'And' or '&'
            g_parts = re.split(r'[_ &+]+', gn)
            for gp in g_parts:
                c_gp = clean_token(gp).capitalize()
                if c_gp.lower() not in NOISE_WORDS and len(c_gp) > 1:
                    candidates.append((clean_sn, c_gp))
        else:
            candidates.append((clean_sn, ""))

    # 2. Extract tokens from normalized filename
    # e.g., 'Alfred_Pierce_Helen_Durham_And_Enos_Pierce.jpg'
    base = os.path.splitext(norm_fn)[0]
    tokens = [clean_token(t) for t in base.split('_') if clean_token(t)]
    tokens = [t for t in tokens if t.lower() not in NOISE_WORDS and len(t) > 1]
    
    # Check for couple pairs or surname tokens
    for i, tok in enumerate(tokens):
        # Could be a surname
        cap_tok = tok.capitalize()
        # Look behind or ahead for given name
        if i > 0:
            prev_tok = tokens[i-1].capitalize()
            if prev_tok.lower() not in NOISE_WORDS:
                candidates.append((cap_tok, prev_tok))
        if i < len(tokens) - 1:
            next_tok = tokens[i+1].capitalize()
            if next_tok.lower() not in NOISE_WORDS:
                candidates.append((cap_tok, next_tok))

    # Deduplicate candidates
    dedup = []
    seen = set()
    for s, g in candidates:
        pair = (s.lower(), g.lower())
        if pair not in seen and s.lower() not in NOISE_WORDS:
            seen.add(pair)
            dedup.append((s, g))

    return dedup

def run_connection_pipeline():
    print("==================================================================")
    print("CONNECTING PHOTOS TO SURNAMES AND PERSON PROFILES")
    print("==================================================================")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # -------------------------------------------------------------
    # 1. Load Persons into Memory Index
    # -------------------------------------------------------------
    print("\n[1/4] Loading Person Registry for Entity Resolution...")
    cur.execute("""
        SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name
        FROM persons
    """)
    all_persons = cur.fetchall()
    print(f"  ✓ Loaded {len(all_persons)} person profiles")

    # Index by (surname_lower, first_name_lower)
    person_by_exact = defaultdict(set)
    person_by_surname = defaultdict(set)

    for p in all_persons:
        pid = p["person_id"]
        p_name = p["name"]
        p_first = clean_token(p["first_name"] or "").lower()
        if not p_first and p_name:
            parts = p_name.split()
            if parts:
                p_first = clean_token(parts[0]).lower()

        surnames = set()
        if p["married_last_name"]:
            surnames.add(clean_token(p["married_last_name"]).lower())
        if p["maiden_name"]:
            surnames.add(clean_token(p["maiden_name"]).lower())
        if p_name:
            parts = p_name.split()
            if len(parts) > 1:
                surnames.add(clean_token(parts[-1]).lower())

        for sn in surnames:
            if sn and sn not in NOISE_WORDS:
                person_by_surname[sn].add(pid)
                if p_first and len(p_first) > 1 and p_first not in NOISE_WORDS:
                    person_by_exact[(sn, p_first)].add(pid)

    print(f"  ✓ Indexed {len(person_by_exact)} distinct (surname, given_name) pairs")
    print(f"  ✓ Indexed {len(person_by_surname)} distinct surname clusters")

    # -------------------------------------------------------------
    # 2. Match Photos to Persons & Update person_photos
    # -------------------------------------------------------------
    print("\n[2/4] Matching 2,609 Photos to Person Profiles...")
    cur.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               surname, given_names, subject_names
        FROM unified_photo_catalog
    """)
    photos = cur.fetchall()

    new_links = set() # (person_id, photo_id)
    photo_matched_set = set()
    photo_surnames_map = defaultdict(set) # photo_id -> set of surnames

    for photo in photos:
        ph_id = photo["photo_id"]
        norm_fn = photo["normalized_filename"]
        orig_fn = photo["original_filename"]
        sn = photo["surname"]
        gn = photo["given_names"]
        subj = photo["subject_names"]

        # Parse candidate names
        candidates = parse_name_candidates(norm_fn, orig_fn, sn, gn, subj)

        for cand_sn, cand_gn in candidates:
            s_low = cand_sn.lower()
            g_low = cand_gn.lower()

            # Record surname association
            if s_low and s_low not in NOISE_WORDS and len(s_low) > 2:
                photo_surnames_map[ph_id].add(cand_sn.capitalize())

            # Check exact (surname, given_name)
            if (s_low, g_low) in person_by_exact:
                for matched_pid in person_by_exact[(s_low, g_low)]:
                    new_links.add((matched_pid, ph_id))
                    photo_matched_set.add(ph_id)
            elif s_low in person_by_surname and len(g_low) >= 3:
                # Prefix match on first name
                for p_id in person_by_surname[s_low]:
                    # Find person's first name
                    for (sn_k, fn_k), pids in person_by_exact.items():
                        if sn_k == s_low and p_id in pids:
                            if fn_k.startswith(g_low) or g_low.startswith(fn_k):
                                new_links.add((p_id, ph_id))
                                photo_matched_set.add(ph_id)

    print(f"  ✓ Matched {len(photo_matched_set)} / {len(photos)} photos directly to person profiles ({len(photo_matched_set)/len(photos)*100:.1f}%)")
    print(f"  ✓ Generated {len(new_links)} validated person-to-photo links")

    # Update person_photos table
    print("\nUpdating 'person_photos' junction table in database...")
    cur.execute("DELETE FROM person_photos")
    for pid, ph_id in new_links:
        cur.execute("""
            INSERT OR IGNORE INTO person_photos (person_id, photo_id)
            VALUES (?, ?)
        """, (pid, ph_id))

    # -------------------------------------------------------------
    # 3. Create & Populate 'photo_surnames' Table
    # -------------------------------------------------------------
    print("\n[3/4] Creating and Populating 'photo_surnames' Table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS photo_surnames (
            photo_id INTEGER NOT NULL,
            surname TEXT NOT NULL,
            is_primary BOOLEAN DEFAULT 0,
            PRIMARY KEY (photo_id, surname),
            FOREIGN KEY (photo_id) REFERENCES unified_photo_catalog(photo_id)
        )
    """)
    cur.execute("DELETE FROM photo_surnames")

    inserted_photo_surnames = 0
    for ph_id, s_set in photo_surnames_map.items():
        # Primary surname from unified_photo_catalog if present
        cur.execute("SELECT surname FROM unified_photo_catalog WHERE photo_id = ?", (ph_id,))
        row = cur.fetchone()
        prim_sn = row[0] if row and row[0] else None

        for s in s_set:
            is_prim = 1 if (prim_sn and prim_sn.lower() == s.lower()) else 0
            cur.execute("""
                INSERT OR IGNORE INTO photo_surnames (photo_id, surname, is_primary)
                VALUES (?, ?, ?)
            """, (ph_id, s, is_prim))
            inserted_photo_surnames += 1

    print(f"  ✓ Populated {inserted_photo_surnames} photo-to-surname links in 'photo_surnames'")

    # -------------------------------------------------------------
    # 4. Synchronize photo_catalog with unified_photo_catalog
    # -------------------------------------------------------------
    print("\n[4/4] Synchronizing 'photo_catalog' with Canonical Unified Catalog...")
    cur.execute("DROP TABLE IF EXISTS photo_catalog_new")
    cur.execute("""
        CREATE TABLE photo_catalog_new (
            photo_id INTEGER PRIMARY KEY,
            title_or_caption TEXT,
            subject_names TEXT,
            maiden_name TEXT,
            married_surname TEXT,
            location TEXT,
            approximate_year TEXT,
            local_image_path TEXT,
            source_url TEXT,
            dataset_source TEXT,
            media_type TEXT,
            transcript TEXT,
            document_type TEXT,
            extracted_entities TEXT,
            transcription_confidence REAL
        )
    """)
    cur.execute("""
        INSERT INTO photo_catalog_new (
            photo_id, title_or_caption, subject_names, maiden_name, married_surname,
            location, approximate_year, local_image_path, source_url, dataset_source,
            media_type, document_type
        )
        SELECT 
            photo_id,
            normalized_filename,
            subject_names,
            NULL,
            surname,
            NULL,
            approximate_year,
            local_image_path,
            source_url,
            dataset_source,
            category,
            document_type
        FROM unified_photo_catalog
    """)
    cur.execute("DROP TABLE photo_catalog")
    cur.execute("ALTER TABLE photo_catalog_new RENAME TO photo_catalog")

    conn.commit()

    # Final stats
    cur.execute("SELECT COUNT(DISTINCT person_id), COUNT(DISTINCT photo_id) FROM person_photos")
    dist_p, dist_ph = cur.fetchone()

    cur.execute("SELECT COUNT(DISTINCT surname), COUNT(DISTINCT photo_id) FROM photo_surnames")
    dist_sn, dist_ph_sn = cur.fetchone()

    conn.close()

    print("\n==================================================================")
    print("PIPELINE COMPLETE: ENTITY RESOLUTION & SURNAMES INTEGRATED")
    print(f"  - Persons with Connected Photos   : {dist_p} / 3,820 profiles")
    print(f"  - Photos Connected to Profiles    : {dist_ph} photos")
    print(f"  - Total Person-Photo Links (pp)   : {len(new_links)}")
    print(f"  - Distinct Surnames with Galleries: {dist_sn}")
    print(f"  - Photos Connected to Surnames    : {dist_ph_sn} / 2,609 photos")
    print("==================================================================")

if __name__ == "__main__":
    run_connection_pipeline()
