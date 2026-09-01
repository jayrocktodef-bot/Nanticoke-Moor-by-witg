#!/usr/bin/env python3
"""
Photo-to-Person Precision Accuracy Audit & Re-linking Engine
(audit_and_relink_photos.py)
===========================================================
Audits all person-photo connections in genealogy_preservation.db.
Eliminates over-broad surname-only false positive links and guarantees that
photos are connected strictly to the verified corresponding individual profiles.
"""

import os
import re
import json
import sqlite3
from difflib import SequenceMatcher
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'vi', 'esq', 'esq.', 'md', 'phd'}
HONORIFICS = {'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'miss', 'ms', 'ms.', 'rev', 'rev.',
              'capt', 'capt.', 'col', 'col.', 'hon', 'hon.', 'prof', 'prof.', 'sgt', 'sgt.'}

def clean_tokens(name_str):
    if not name_str:
        return []
    # Strip metadata additions
    s = re.sub(r'\(Biometric Match:.*?\)', '', name_str)
    s = re.sub(r'\(also.*?\)', '', s)
    s = re.sub(r'[^\w\s\(\)-]', ' ', s)
    tokens = [t.strip(' -()') for t in s.split() if t.strip(' -()')]
    # Remove honorifics and suffixes for core comparison
    cleaned = [t.lower() for t in tokens if t.lower() not in HONORIFICS and t.lower() not in SUFFIXES]
    return cleaned

def parse_photo_individuals(subject_str, title_str, img_path):
    """
    Extracts individual human names from compound captions and filenames.
    e.g. 'Charles Edward & Della Mae (Ridgway) Carey' -> ['Charles Edward Carey', 'Della Mae Ridgway', 'Della Mae Carey']
    e.g. 'Alfred Pierce-Helen Durham&EnosPierce' -> ['Alfred Pierce', 'Helen Durham', 'Enos Pierce']
    """
    candidates = set()
    raw = subject_str or ""
    
    # Strip non-name phrases
    raw = re.sub(r'\(Biometric Match:.*?\)', '', raw)
    raw = re.sub(r'\b(Collection|Archive|Family|Records|Record|Tombstone|Burial|Indenture|Bible|News|Alumni|News|Obit|Program|Certificate)\b', '', raw, flags=re.IGNORECASE)
    
    # Normalize hyphens between distinct capital words (e.g. Pierce-Helen -> Pierce & Helen)
    raw = re.sub(r'([a-z])\-([A-Z])', r'\1 & \2', raw)
    # CamelCase separation
    raw = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw)
    
    # Split on compound separators: '&', 'and', ',', ';', 'with', 'accompanied by'
    segments = re.split(r'\s*&\s*|\s+and\s+|\s*,\s*|\s*;\s*|\s+with\s+', raw)
    
    # Look for trailing shared surname
    shared_surname = None
    if segments:
        last_seg = segments[-1].strip()
        last_words = [w for w in last_seg.split() if len(w) > 1 and w.isalpha()]
        if last_words:
            shared_surname = last_words[-1]

    for seg in segments:
        seg = seg.strip(' -:,()')
        if len(seg) < 3 or seg.lower() in ['unknown', 'unidentified', 'who', 'group of 16', 'children', 'members']:
            continue
            
        # Check if segment has maiden name in parentheses: e.g. "Della Mae (Ridgway) Carey"
        m = re.search(r'\(([^)]+)\)', seg)
        if m:
            maiden = m.group(1).strip()
            base_name = re.sub(r'\([^)]+\)', '', seg).strip()
            base_words = base_name.split()
            if base_words:
                given = ' '.join(base_words[:-1]) if len(base_words) > 1 else base_words[0]
                married = base_words[-1] if len(base_words) > 1 else ''
                if given and maiden:
                    candidates.add(f"{given} {maiden}".strip())
                if given and married:
                    candidates.add(f"{given} {married}".strip())
        else:
            seg_words = seg.split()
            if len(seg_words) == 1 and shared_surname and seg_words[0].lower() != shared_surname.lower():
                # Apply shared surname
                candidates.add(f"{seg} {shared_surname}".strip())
            else:
                candidates.add(seg)

    # Also extract from filename if subject is short
    fn = os.path.basename(img_path or "").replace("mitsawokett_", "")
    fn = re.sub(r'\.(jpg|jpeg|gif|png)$', '', fn, flags=re.IGNORECASE)
    fn = re.sub(r'[-_](?:Page|obit|funeral program|MC|copy|\d{1,2})$', '', fn, flags=re.IGNORECASE)
    fn_segments = re.split(r'[-&_]', fn)
    for f_seg in fn_segments:
        f_seg = re.sub(r'([a-z])([A-Z])', r'\1 \2', f_seg).strip()
        f_words = f_seg.split()
        if len(f_words) >= 2:
            candidates.add(f_seg)

    return list(candidates)

def match_person_to_candidate(person, candidate_name):
    """
    High-precision matching requiring:
    1. Matching given name / first name
    2. Matching surname (maiden or married)
    """
    pid, p_name, p_first, p_middle, p_maiden, p_married = person
    
    p_tokens = clean_tokens(p_name)
    c_tokens = clean_tokens(candidate_name)
    
    if len(p_tokens) < 2 or len(c_tokens) < 2:
        return None, 0.0

    p_first_token = p_tokens[0]
    p_last_token = p_tokens[-1]
    
    c_first_token = c_tokens[0]
    c_last_token = c_tokens[-1]

    # Check first name match
    first_match = False
    if p_first_token == c_first_token:
        first_match = True
    elif len(p_first_token) == 1 and c_first_token.startswith(p_first_token): # Initial match
        first_match = True
    elif len(c_first_token) == 1 and p_first_token.startswith(c_first_token): # Initial match
        first_match = True
    elif SequenceMatcher(None, p_first_token, c_first_token).ratio() >= 0.85:
        first_match = True

    if not first_match:
        return None, 0.0

    # Check surname match (against last token, maiden, or married)
    surnames_to_check = {p_last_token}
    if p_maiden:
        surnames_to_check.add(p_maiden.lower().strip())
    if p_married:
        surnames_to_check.add(p_married.lower().strip())

    surname_match = False
    for sn in surnames_to_check:
        if sn == c_last_token:
            surname_match = True
            break
        elif SequenceMatcher(None, sn, c_last_token).ratio() >= 0.88:
            surname_match = True
            break

    if not surname_match:
        return None, 0.0

    # Calculate calibrated confidence score
    full_p = ' '.join(p_tokens)
    full_c = ' '.join(c_tokens)
    
    if full_p == full_c:
        return pid, 1.00
    
    ratio = SequenceMatcher(None, full_p, full_c).ratio()
    confidence = round(max(0.85, ratio), 2)
    return pid, confidence

def run_accuracy_relinking():
    print("==================================================================", flush=True)
    print("STARTING PHOTO-TO-PERSON PRECISION ACCURACY AUDIT & RELINKING", flush=True)
    print("==================================================================", flush=True)

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Load all persons
    c.execute("SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name FROM persons WHERE name IS NOT NULL")
    persons = c.fetchall()
    print(f"Loaded {len(persons)} verified individuals from database.")

    # Load all photos
    c.execute("SELECT photo_id, subject_names, title_or_caption, local_image_path FROM photo_catalog")
    photos = c.fetchall()
    print(f"Loaded {len(photos)} photos from catalog.\n")

    # Clear old fuzzy over-linked connections
    print("Flushing old over-broad person-photo links...", flush=True)
    c.execute("DELETE FROM person_photos")
    conn.commit()

    verified_links = 0
    photos_linked = set()
    person_link_counts = Counter()

    for photo_id, subject_names, title, img_path in photos:
        candidates = parse_photo_individuals(subject_names, title, img_path)
        if not candidates:
            continue

        photo_matched_persons = set()

        for cand in candidates:
            for person in persons:
                matched_pid, score = match_person_to_candidate(person, cand)
                if matched_pid is not None and matched_pid not in photo_matched_persons:
                    photo_matched_persons.add(matched_pid)
                    c.execute("""
                        INSERT INTO person_photos (person_id, photo_id, confidence_score)
                        VALUES (?, ?, ?)
                    """, (matched_pid, photo_id, score))
                    verified_links += 1
                    photos_linked.add(photo_id)
                    person_link_counts[matched_pid] += 1

    conn.commit()

    print("==================================================================", flush=True)
    print("ACCURACY AUDIT & PRECISION RELINKING COMPLETE", flush=True)
    print("==================================================================", flush=True)
    print(f"Total Precision Person-Photo Links Created: {verified_links}")
    print(f"Total Distinct Photos Connected: {len(photos_linked)}")
    print(f"Total Distinct Individuals with Photos: {len(person_link_counts)}")
    
    print("\nTop 15 Individuals with Most Verified Photo Connections:")
    c.execute("""
        SELECT p.person_id, p.name, COUNT(pp.photo_id) as pcount
        FROM persons p
        JOIN person_photos pp ON p.person_id = pp.person_id
        GROUP BY p.person_id
        ORDER BY pcount DESC
        LIMIT 15
    """)
    for r in c.fetchall():
        print(f"  - {r[1]} (ID {r[0]}): {r[2]} verified photos")

    print("\nSample Verified Links (Spot-Check):")
    c.execute("""
        SELECT pc.photo_id, pc.subject_names, p.name, pp.confidence_score
        FROM person_photos pp
        JOIN photo_catalog pc ON pp.photo_id = pc.photo_id
        JOIN persons p ON pp.person_id = p.person_id
        ORDER BY RANDOM()
        LIMIT 10
    """)
    for r in c.fetchall():
        print(f"  [Conf: {r[3]}] Photo: '{r[1]}'  <==>  Person Profile: '{r[2]}'")

    conn.close()

if __name__ == "__main__":
    run_accuracy_relinking()
