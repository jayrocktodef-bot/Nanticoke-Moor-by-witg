#!/usr/bin/env python3
"""
comprehensive_photo_audit_and_fix.py

Comprehensive photo filename and entity audit pipeline for the Lynn Jackson & Mitsawokett Archive.
Applies DeepSeek architectural recommendations:
1. Normalizes and parses filenames into clean, dignified human-readable titles.
2. Identifies and corrects scraper bleed-through titles (e.g. 'Margaret 2', 'Ephraim 2', 'Adeline Farmer').
3. Accurately classifies categories and document types (portrait, group_photo, document, family_tree, tombstone).
4. Extracts biographical metadata (birth/death dates, relationships: Sonof, Husb, Wifeof, Uncle).
5. Implements Zero-Hallucination Entity Resolution against the `persons` database to attach `primary_person_id`
   and `primary_person_name` to verified single-subject photographs and records.
6. Synchronizes `unified_photo_catalog`, `photo_catalog`, `person_photos`, and transcription JSONs.
"""

import sqlite3
import re
import os
import json
from collections import defaultdict

DB_PATH = 'preservation_output/genealogy_preservation.db'
TRANSCRIPTIONS_DIR = 'frontend/public/api/transcriptions'

# Known scraper page-level bleed titles where the scraper slapped the page title on every image
BLEED_TITLES = {
    'margaret 2', 'ephraim 2', 'peter 2', 'lillian 2', 'catherine 2', 'adeline farmer',
    'mitsawokett research group members', 'lucille johnson', 'charlotte delores ingram jackson',
    'roland durham', 'geneva mae cuff durham', 'sarah elizabeth mosley durham',
    'alec hanzer', 'elizabeth p. wright harmon', 'hester dean', 'maude loatman',
    'lois ferguson', 'dorcas ann pierce dean', 'mary elizabeth durham', 'marie c. durham',
    'eliza ann harmon', 'loretta gross jordan 1', 'james e hanzer', 'clara jean mosley hall 1',
    'brown', 'carney', 'carter', 'unknowns page 1', 'unknowns page 2',
    'bloomsbury meeting at cheswold firehouse, may 9, 1998'
}

DOC_KEYWORDS = {
    'funeral_pgm': 'funeral_program',
    'funeral_program': 'funeral_program',
    'funeral': 'funeral_record',
    'pgm': 'obituary_program',
    'program': 'obituary_program',
    'memorial': 'memorial_program',
    'diploma': 'diploma',
    'grad': 'graduation_portrait',
    'bible': 'bible_record',
    'deed': 'historical_deed',
    'probate_will': 'last_will_testament',
    'census': 'census_record',
    'draft': 'military_draft_card',
    'deathcertificate': 'death_certificate',
    'birthcertificate': 'birth_certificate',
    'marriagecertificate': 'marriage_certificate',
    'certificate': 'vital_certificate',
    'license': 'marriage_license'
}

def clean_tok(tok):
    """Formats a single token nicely."""
    lower = tok.lower()
    if lower in ['jr', 'jr.']: return 'Jr.'
    if lower in ['sr', 'sr.']: return 'Sr.'
    if lower in ['ii']: return 'II'
    if lower in ['iii']: return 'III'
    if lower in ['iv']: return 'IV'
    if lower in ['cjr']: return 'C. Jr.'
    if lower in ['whjr']: return 'W. H. Jr.'
    if lower in ['unk']: return 'Unknown'
    if lower in ['and']: return '&'
    if len(tok) == 1: return tok.upper() + '.'
    
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', tok)
    return spaced.capitalize() if spaced.isupper() or spaced.islower() else spaced

def parse_filename_metadata(filename, known_surnames):
    """
    Parses a normalized filename into structured components using dynamic surnames.
    """
    raw_base = re.sub(r'\.(jpg|png|gif|jpeg)$', '', filename, flags=re.I)
    raw_base = re.sub(r'^mitsawokett_', '', raw_base, flags=re.I)

    # 1. Check tombstones / cemeteries BEFORE stripping leading digits
    if re.search(r'^\d{1,2}_[A-Za-z]{3}_', raw_base) or re.search(r'(_cem|_tombstone|_grave|_burying|_ame_cem)', raw_base, re.I):
        title = raw_base.replace('_', ' ')
        title = re.sub(r'\bCem\b', 'Cemetery', title, flags=re.I)
        title = re.sub(r'\bAme\b', 'A.M.E.', title, flags=re.I)
        return {
            'category': 'tombstones',
            'document_type': 'tombstone',
            'subtype': 'cemetery_memorial',
            'is_group': False,
            'is_single_person': False,
            'candidate_name': None,
            'title': title.strip(),
            'birth_year': None,
            'death_year': None,
            'relationships': []
        }

    # Strip leading counter if present (e.g. 8_Terry...)
    base = re.sub(r'^\d+_', '', raw_base)

    # Special compound patterns in Delmarva filenames:
    base = re.sub(r'Jryoung', '_Jr_Young', base, flags=re.I)
    base = re.sub(r'Whjr', '_William_Henry_Jr', base, flags=re.I)
    base = re.sub(r'Edithyoungteenager', 'Edith_Young_Teenager', base, flags=re.I)
    base = re.sub(r'Rnsr', 'R._N._Sr.', base, flags=re.I)

    # 2. Check family trees
    if re.search(r'(_ancestry|_tree|_pedigree|_lineage|_descendants)', base, re.I):
        clean_name_part = re.sub(r'(_ancestry|_tree|_pedigree|_lineage|_descendants).*$', '', base, flags=re.I)
        tokens = [clean_tok(t) for t in clean_name_part.split('_') if t]
        
        if len(tokens) >= 2 and tokens[0] in known_surnames:
            formatted_name = ' '.join(tokens[1:] + [tokens[0]])
        else:
            formatted_name = ' '.join(tokens)
            
        title = f"{formatted_name} Lineage Pedigree"
        return {
            'category': 'family_trees',
            'document_type': 'family_tree',
            'subtype': 'ancestor_pedigree_chart',
            'is_group': False,
            'is_single_person': False,
            'candidate_name': formatted_name,
            'title': title,
            'birth_year': None,
            'death_year': None,
            'relationships': []
        }

    # 3. Check documents & funeral programs (avoiding William matching will)
    test_base = re.sub(r'\b(william|williams|willie|willard|willis)\b', '', base, flags=re.I)
    is_doc = False
    doc_subtype = 'historical_document'
    doc_match = re.search(r'_(funeral_pgm|funeral_program|funeral|memorial|pgm|program|diploma|grad|bible|deed|probate_will|census|draft|deathcertificate|birthcertificate|marriagecertificate|certificate|license|obit_obituary|obituary|obit|socialsecurity_application|socialsecurity)(?:_|\.|$)', test_base, re.I)
    if doc_match:
        is_doc = True
        doc_key = doc_match.group(1).lower()
        doc_subtype = DOC_KEYWORDS.get(doc_key, 'historical_document')
    elif re.search(r'_(probate|testament)(?:_|\.|$)', test_base, re.I):
        is_doc = True
        doc_subtype = 'last_will_testament'
    elif re.search(r'_(?:last_will|probate_will)(?:_|\.|$)', base, re.I):
        is_doc = True
        doc_subtype = 'last_will_testament'

    # 4. Extract dates like B_1898_D_1977 or Wborn_1899
    base = re.sub(r'([A-Z])born_(\d{4})', r'\1_B_\2', base)
    birth_year = None
    death_year = None
    b_match = re.search(r'(?:^|_)B_?(\d{4})(?:_|$)', base, re.I)
    if b_match: birth_year = b_match.group(1)
    d_match = re.search(r'(?:^|_)D_?(\d{4})(?:_|$)', base, re.I)
    if d_match: death_year = d_match.group(1)

    # 5. Extract relationships (for single person media)
    relationships = []
    if not re.search(r'_and_(?:wife|husband|daughter|son)', base, re.I):
        if re.search(r'(?:^|_)Husb(?:of)?_([A-Za-z_]+)', base, re.I):
            m = re.search(r'(?:^|_)Husb(?:of)?_([A-Za-z_]+)', base, re.I)
            spouse = m.group(1)
            spouse = re.split(r'_(?:Sonof|Dtrof|Daughterof|B_|D_)', spouse, flags=re.I)[0]
            spouse_toks = []
            for t in spouse.split('_'):
                m2 = re.match(r'^([A-Z])([A-Z][a-z]+)$', t)
                if m2:
                    spouse_toks.extend([m2.group(1) + '.', m2.group(2)])
                else:
                    spouse_toks.append(t)
            relationships.append(f"Husband of {' '.join(spouse_toks)}")
        if re.search(r'(?:^|_)Wife(?:of)?_([A-Za-z_]+)', base, re.I):
            m = re.search(r'(?:^|_)Wife(?:of)?_([A-Za-z_]+)', base, re.I)
            spouse = m.group(1)
            spouse = re.split(r'_(?:Sonof|Dtrof|Daughterof|B_|D_)', spouse, flags=re.I)[0]
            spouse_toks = []
            for t in spouse.split('_'):
                m2 = re.match(r'^([A-Z])([A-Z][a-z]+)$', t)
                if m2:
                    spouse_toks.extend([m2.group(1) + '.', m2.group(2)])
                else:
                    spouse_toks.append(t)
            relationships.append(f"Wife of {' '.join(spouse_toks)}")

    if re.search(r'(?:^|_)Sonof_([A-Za-z_]+)', base, re.I):
        m = re.search(r'(?:^|_)Sonof_([A-Za-z_]+)', base, re.I)
        parents = m.group(1).replace('_And_', ' & ').replace('_', ' ')
        relationships.append(f"Son of {parents}")
    if re.search(r'(?:^|_)(?:Dtr|Daughter)(?:of)?_([A-Za-z_]+)', base, re.I):
        m = re.search(r'(?:^|_)(?:Dtr|Daughter)(?:of)?_([A-Za-z_]+)', base, re.I)
        parents = m.group(1).replace('_And_', ' & ').replace('_', ' ')
        relationships.append(f"Daughter of {parents}")

    # 6. Check if group / multi-person / school (ignoring parents like Sonof_A_And_B)
    core_for_group = re.sub(r'_(?:Sonof|Dtrof|Daughterof).*$', '', base, flags=re.I)
    base_lower = core_for_group.lower()
    is_school = bool(re.search(r'\bschool\b', base_lower))
    is_group = is_school or bool(re.search(r'(_and_|_family|_cfamily|_kids|_group|_reunion|_collection|_band|_club|_team|_sisters|_brothers|_babes|_children|_gathering|_couple|\band\b|\bfamily\b|\bkids\b)', base_lower))
    
    # 7. Strip doc keywords, dates, and relationships to isolate person tokens
    clean_base = base
    clean_base = re.sub(r'_(B_\d{4}.*|D_\d{4}.*|Husb.*|Wife.*|Sonof.*|Dtr.*|Daughter.*)', '', clean_base, flags=re.I)
    clean_base = re.sub(r'_(funeral_\d+|funeral_pgm|funeral_program|funeral|memorial|pgm|program|obit_obituary_\d+|obit_obituary|obituary_\d+|obituary|obit_\d+|obit|socialsecurity_application|socialsecurity|grad_\d+|grad|diploma|bible|deed|probate_will|last_will|probate|census|draft|cert|certificate|deathcertificate|birthcertificate|marriagecertificate|license|copy|photo|\d+)$', '', clean_base, flags=re.I)
    
    raw_tokens = [t for t in clean_base.split('_') if t]

    # Check embedded nickname/relation (Uncle, Aunt, Grandma, Grandpa, Mom)
    nickname = None
    tokens = []
    i = 0
    while i < len(raw_tokens):
        tok = raw_tokens[i]
        if tok in ['Uncle', 'Aunt', 'Grandma', 'Grandpa', 'Mom']:
            if i + 1 < len(raw_tokens):
                nickname = f"{tok} {raw_tokens[i+1]}"
                i += 2
                continue
            else:
                nickname = tok
        else:
            tokens.append(tok)
        i += 1

    # Check suffix and descriptors
    DESCRIPTORS = {'Young', 'Retirement', 'Elder', 'Child', 'Baby', 'Teenager', 'Wedding', 'Army', 'Military', 'Soldier'}
    SUFFIXES = {'Jr.', 'Sr.', 'II', 'III', 'IV'}
    
    clean_tokens = []
    for t in tokens:
        m = re.match(r'^([A-Z])([A-Z][a-z]+)$', t)
        if m:
            clean_tokens.extend([m.group(1) + '.', m.group(2)])
        else:
            clean_tokens.append(clean_tok(t))

    dedup_tokens = []
    for t in clean_tokens:
        if not dedup_tokens or t != dedup_tokens[-1]:
            dedup_tokens.append(t)
    clean_tokens = dedup_tokens

    desc_tokens = []
    suffix = None
    name_tokens = []
    for t in clean_tokens:
        if t in DESCRIPTORS:
            desc_tokens.append(t)
        elif t in SUFFIXES:
            suffix = t
        else:
            name_tokens.append(t)

    candidate_name = None
    formatted_title = None

    if not is_group and len(name_tokens) >= 1:
        if len(name_tokens) >= 2 and name_tokens[0] in known_surnames:
            candidate_name = ' '.join(name_tokens[1:] + [name_tokens[0]])
        else:
            candidate_name = ' '.join(name_tokens)

        if suffix:
            candidate_name = f"{candidate_name} {suffix}"
        if nickname:
            candidate_name = f"{candidate_name} ({nickname})"

    # Build formatted title
    if is_school:
        formatted_title = raw_base.replace('_', ' ')
    elif is_group:
        group_title = base.replace('_And_', ' & ').replace('_', ' ')
        group_title = re.sub(r'\s+', ' ', group_title).strip()
        formatted_title = group_title
    elif is_doc:
        if "obituary" in doc_subtype or "obit" in doc_subtype:
            doc_label = "Obituary"
        elif "social_security" in doc_subtype:
            doc_label = "Social Security Application"
        elif "funeral" in doc_subtype:
            doc_label = "Funeral Program"
        elif "birth" in doc_subtype:
            doc_label = "Birth Certificate"
        elif "death" in doc_subtype:
            doc_label = "Death Certificate"
        elif "marriage" in doc_subtype:
            doc_label = "Marriage Certificate"
        else:
            doc_label = "Historical Document"
        formatted_title = f"{candidate_name} ({doc_label})" if candidate_name else base.replace('_', ' ')
    else:
        formatted_title = candidate_name if candidate_name else base.replace('_', ' ')
        if desc_tokens and formatted_title:
            formatted_title = f"{formatted_title} ({' '.join(desc_tokens)})"

    # Append date and relationship annotations to title if available
    extra_annotations = []
    if birth_year and death_year:
        extra_annotations.append(f"({birth_year}–{death_year})")
    elif birth_year:
        extra_annotations.append(f"(b. {birth_year})")
    elif death_year:
        extra_annotations.append(f"(d. {death_year})")

    if relationships:
        extra_annotations.append(", ".join(relationships))

    if extra_annotations and candidate_name:
        formatted_title = f"{candidate_name} {' '.join(extra_annotations)}"

    # Determine final category and document type
    category = 'documents' if is_doc else ('people' if not is_group else 'people')
    document_type = doc_subtype if is_doc else ('group_photo' if is_group else 'portrait')

    return {
        'category': category,
        'document_type': document_type,
        'subtype': 'studio_portrait' if document_type == 'portrait' else ('group_portrait' if is_group else doc_subtype),
        'is_group': is_group,
        'is_single_person': not is_group and not is_doc,
        'candidate_name': candidate_name,
        'title': formatted_title,
        'birth_year': birth_year,
        'death_year': death_year,
        'relationships': relationships
    }

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("=" * 80)
    print("STARTING COMPREHENSIVE PHOTO & DOCUMENT AUDIT AND ENTITY RESOLUTION")
    print("=" * 80)

    # 1. Load all persons and extract dynamic surnames
    c.execute("""
        SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, birth_info, death_info 
        FROM persons
    """)
    all_persons = c.fetchall()

    known_surnames = set()
    by_full_name = defaultdict(list)
    by_first_last = defaultdict(list)

    for p in all_persons:
        pid, name, fn, mn, maiden, married, binfo, dinfo = p
        
        for raw in [married, maiden]:
            if raw:
                cl = re.sub(r'[^a-zA-Z]', '', raw).strip().title()
                if len(cl) >= 2: known_surnames.add(cl)
        tokens = [re.sub(r'[^a-zA-Z]', '', t).strip().title() for t in name.split()]
        tokens = [t for t in tokens if len(t) >= 2]
        if len(tokens) >= 2:
            known_surnames.add(tokens[-1])

        clean = re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()
        by_full_name[clean].append(p)
        toks = clean.split()
        if len(toks) >= 2:
            by_first_last[(toks[0], toks[-1])].append(p)
        if married:
            m_last = re.sub(r'[^a-z0-9]', '', married.lower())
            if toks:
                by_first_last[(toks[0], m_last)].append(p)
        if maiden:
            m_maiden = re.sub(r'[^a-z0-9]', '', maiden.lower())
            if toks:
                by_first_last[(toks[0], m_maiden)].append(p)

    print(f"Loaded {len(all_persons)} persons and {len(known_surnames)} dynamic Delmarva surnames into memory.")

    # 2. Fetch all photos
    c.execute("""
        SELECT photo_id, normalized_filename, subject_names, category, document_type, primary_person_id, primary_person_name 
        FROM unified_photo_catalog
    """)
    photos = c.fetchall()
    print(f"Evaluating {len(photos)} photos across archive...")

    titles_fixed = 0
    categories_fixed = 0
    persons_linked = 0
    join_links_added = 0
    fixed_transcriptions = 0

    audit_records = []

    for photo in photos:
        pid, filename, current_subj, current_cat, current_dt, current_ppid, current_ppname = photo

        parsed = parse_filename_metadata(filename, known_surnames)
        new_title = parsed['title']
        new_cat = parsed['category']
        new_dt = parsed['document_type']
        new_subtype = parsed['subtype']
        candidate_name = parsed['candidate_name']
        birth_year = parsed['birth_year']
        death_year = parsed['death_year']

        # Determine if subject title needs fixing
        curr_clean = (current_subj or '').strip()
        curr_lower = curr_clean.lower()

        # Check if scraper bleed or complete disconnect from filename
        fn_tokens = [t.lower() for t in re.sub(r'[^a-z0-9_]', '', filename).split('_') 
                     if len(t) > 2 and t.lower() not in ['and', 'family', 'collection', 'photo', 'ancestry', 'tree', 'tombstone', 'cem', 'funeral', 'pgm', 'program', 'jpg', 'png']]
        overlap = any(tok in curr_lower for tok in fn_tokens) if fn_tokens else True

        # Check if current title is reversed "Surname First" like "Andrews Jonathan"
        is_reversed_raw = False
        parts = curr_clean.split()
        if len(parts) >= 2 and parts[0] in known_surnames and new_title != curr_clean:
            is_reversed_raw = True

        # Check for first-name contradiction (e.g. filename says Harry E. Davis, but scraper put Ethel G. Clark Davis)
        first_name_mismatch = False
        subj_words = [t.lower() for t in re.sub(r'[^a-zA-Z ]', '', curr_clean).split() if t]
        if subj_words and fn_tokens:
            subj_first = subj_words[0]
            if (subj_first not in fn_tokens and 
                subj_first not in ['the', 'bloomsbury', 'unknown', 'group', 'collection', 'family', 'reunion', 'mitsawokett', 'delaware', 'draft', 'peter', 'catherine', 'margaret', 'ephraim', 'lillian']):
                # If filename contains a distinct given name, this is a clear scraper mismatch!
                first_name_mismatch = True

        needs_title_update = False
        if curr_lower in BLEED_TITLES:
            needs_title_update = True
        elif first_name_mismatch:
            needs_title_update = True
        elif not overlap and len(fn_tokens) >= 1:
            needs_title_update = True
        elif is_reversed_raw:
            needs_title_update = True
        elif not curr_clean or curr_clean.endswith('.jpg') or curr_clean.endswith('.png'):
            needs_title_update = True
        elif curr_clean == filename:
            needs_title_update = True
        elif "(last will testament)" in curr_lower or "(historical document)" in curr_lower:
            needs_title_update = True

        final_title = new_title if needs_title_update else current_subj

        # Determine entity matching
        matched_person_id = current_ppid
        matched_person_name = current_ppname

        # If not linked yet, attempt Zero-Hallucination match
        if matched_person_id is None and candidate_name and (parsed['is_single_person'] or parsed['category'] == 'documents'):
            match_cand = re.sub(r'\(.*?\)', '', candidate_name).strip()
            cand_clean = re.sub(r'[^a-z0-9 ]', '', match_cand.lower()).strip()
            
            # Match 1: Full name match
            if cand_clean in by_full_name:
                matches = by_full_name[cand_clean]
                if len(matches) == 1:
                    matched_person_id = matches[0][0]
                    matched_person_name = matches[0][1]
                elif len(matches) > 1 and (birth_year or death_year):
                    for m in matches:
                        m_binfo = str(m[6] or '')
                        m_dinfo = str(m[7] or '')
                        if (birth_year and birth_year in m_binfo) or (death_year and death_year in m_dinfo):
                            matched_person_id = m[0]
                            matched_person_name = m[1]
                            break

            # Match 2: (First, Last) match
            if matched_person_id is None:
                cand_tokens = cand_clean.split()
                if len(cand_tokens) >= 2:
                    fl_key = (cand_tokens[0], cand_tokens[-1])
                    if fl_key in by_first_last:
                        fl_matches = by_first_last[fl_key]
                        if len(fl_matches) == 1:
                            matched_person_id = fl_matches[0][0]
                            matched_person_name = fl_matches[0][1]
                        elif len(fl_matches) > 1 and (birth_year or death_year):
                            for m in fl_matches:
                                m_binfo = str(m[6] or '')
                                m_dinfo = str(m[7] or '')
                                if (birth_year and birth_year in m_binfo) or (death_year and death_year in m_dinfo):
                                    matched_person_id = m[0]
                                    matched_person_name = m[1]
                                    break

        # Check if updates occurred
        title_changed = (final_title != current_subj)
        cat_changed = (new_cat != current_cat or new_dt != current_dt)
        person_linked = (matched_person_id != current_ppid and matched_person_id is not None)

        if title_changed: titles_fixed += 1
        if cat_changed: categories_fixed += 1
        if person_linked: persons_linked += 1

        if title_changed or cat_changed or person_linked:
            # Update unified_photo_catalog
            c.execute("""
                UPDATE unified_photo_catalog
                SET subject_names = ?, category = ?, document_type = ?, subtype = ?,
                    primary_person_id = ?, primary_person_name = ?
                WHERE photo_id = ?
            """, (final_title, new_cat, new_dt, new_subtype, matched_person_id, matched_person_name, pid))

            # Update photo_catalog
            c.execute("""
                UPDATE photo_catalog
                SET subject_names = ?, document_type = ?, subtype = ?,
                    primary_person_id = ?, primary_person_name = ?
                WHERE photo_id = ?
            """, (final_title, new_dt, new_subtype, matched_person_id, matched_person_name, pid))

            # Ensure join table person_photos has this link
            if matched_person_id:
                c.execute("SELECT COUNT(*) FROM person_photos WHERE person_id = ? AND photo_id = ?", (matched_person_id, pid))
                if c.fetchone()[0] == 0:
                    c.execute("INSERT INTO person_photos (person_id, photo_id) VALUES (?, ?)", (matched_person_id, pid))
                    join_links_added += 1

            # Update transcription JSON if exists
            json_path = os.path.join(TRANSCRIPTIONS_DIR, f"{pid}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as jf:
                        tj = json.load(jf)
                    tj['subject_names'] = final_title
                    tj['document_type'] = new_dt
                    tj['category'] = new_cat
                    tj['primary_person_id'] = matched_person_id
                    tj['primary_person_name'] = matched_person_name
                    with open(json_path, 'w', encoding='utf-8') as jf:
                        json.dump(tj, jf, indent=2)
                    fixed_transcriptions += 1
                except Exception as ex:
                    pass

            audit_records.append({
                'photo_id': pid,
                'filename': filename,
                'old_title': current_subj,
                'new_title': final_title,
                'old_cat': current_cat,
                'new_cat': new_cat,
                'old_dt': current_dt,
                'new_dt': new_dt,
                'linked_person_id': matched_person_id,
                'linked_person_name': matched_person_name
            })

    conn.commit()

    print("\n" + "=" * 80)
    print("AUDIT & RESOLUTION EXECUTION RESULTS:")
    print(f"  - Subject Titles Repaired:       {titles_fixed}")
    print(f"  - Categories/Types Reclassified: {categories_fixed}")
    print(f"  - New Single-Person Links:       {persons_linked}")
    print(f"  - Join Table Links Added:        {join_links_added}")
    print(f"  - Transcription JSONs Updated:   {fixed_transcriptions}")
    print("=" * 80)

    # Print sample of dramatic repairs
    print("\nSample of Audited & Repaired Records:")
    for r in audit_records[:40]:
        link_str = f" -> Linked to #{r['linked_person_id']} ({r['linked_person_name']})" if r['linked_person_id'] else ""
        print(f"[{r['photo_id']}] {r['filename']}: \"{r['old_title']}\" -> \"{r['new_title']}\" [{r['new_cat']}/{r['new_dt']}]{link_str}")

    conn.close()

if __name__ == '__main__':
    main()
