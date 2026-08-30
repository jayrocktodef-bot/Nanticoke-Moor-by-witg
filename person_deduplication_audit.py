#!/usr/bin/env python3
"""
Genealogical Person Deduplication Audit Engine (person_deduplication_audit.py)
=============================================================================
Performs a multi-factor forensic identity audit across all preserved profiles:
1. Surname Canonicalization & Phonetic Grouping (using surname_aliases table).
2. Given Name & Nickname Normalization (e.g., Eliza ↔ Elizabeth, Sally ↔ Sarah).
3. Vital Date Triangulation (Birth & Death exact day/month/year matching vs conflicting years).
4. Family Network Triangulation (Shared spouses, parents, children).
5. Cross-Dataset Provenance Resolution (e.g. lynncjackson vs davis_family_gedcom vs mitsawokett).
"""

import os
import sqlite3
import re
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

NICKNAMES = {
    'william': {'bill', 'billy', 'will', 'willie', 'liam'},
    'elizabeth': {'eliza', 'betty', 'bessie', 'bess', 'beth', 'lizzie', 'liz'},
    'margaret': {'maggie', 'peggy', 'marge', 'margie', 'meta'},
    'sarah': {'sallie', 'sally', 'sadie'},
    'mary': {'polly', 'molly', 'mae', 'may'},
    'james': {'jim', 'jimmy'},
    'john': {'jack', 'johnny'},
    'charles': {'charlie', 'chuck'},
    'robert': {'bob', 'bobby', 'rob'},
    'richard': {'dick', 'rick'},
    'elisha': {'leshia', 'lishia', 'eli'},
    'rebecca': {'becky', 'reba'},
    'catherine': {'kate', 'katie', 'kathy'},
    'edward': {'ed', 'eddie', 'ned'},
    'francis': {'frank', 'frankie'},
    'benjamin': {'ben', 'benny'}
}

NICK_TO_FORMAL = {}
for formal, nicks in NICKNAMES.items():
    NICK_TO_FORMAL[formal] = formal
    for nick in nicks:
        NICK_TO_FORMAL[nick] = formal

def extract_year(text):
    if not text: return None
    m = re.search(r'\b(1[5-9]\d{2}|20\d{2})\b', str(text))
    return int(m.group(1)) if m else None

def extract_exact_date(text):
    if not text: return None
    t = text.lower().strip()
    m = re.search(r'\b(\d{1,2}\s+[a-z]{3,9}\s+1[5-9]\d{2}|\d{1,2}\s+[a-z]{3,9}\s+20\d{2})\b', t)
    if m: return m.group(1)
    m = re.search(r'\b([a-z]{3,9}\s+1[5-9]\d{2}|[a-z]{3,9}\s+20\d{2})\b', t)
    if m: return m.group(1)
    y = extract_year(text)
    return str(y) if y else None

def tokenize_name(name):
    clean = re.sub(r'[\"\'\`\.\,\;\:\(\)\[\]\{\}\-\_\/]', ' ', name.lower())
    return [w for w in clean.split() if w]

def run_deduplication_audit():
    print("=" * 72)
    print("  GENEALOGICAL PERSON DEDUPLICATION AUDIT")
    print("=" * 72)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT variant_name, canonical_name FROM surname_aliases")
    surname_map = {r['variant_name'].lower(): r['canonical_name'].lower() for r in c.fetchall()}
    
    c.execute("""
        SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, 
               birth_info, death_info, dataset_source, source_page, notes 
        FROM persons
    """)
    persons = [dict(p) for p in c.fetchall()]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(persons):,} total person profiles.")
    
    # Pre-map family relationships
    c.execute("SELECT person_a_id, person_b_id, relationship_type FROM relationships")
    rel_map = defaultdict(lambda: {'spouses': set(), 'parents': set(), 'children': set()})
    for r in c.fetchall():
        pa, pb, rt = r[0], r[1], r[2].lower()
        if rt == 'spouse':
            rel_map[pa]['spouses'].add(pb)
            rel_map[pb]['spouses'].add(pa)
        elif rt == 'child_of':
            rel_map[pa]['parents'].add(pb)
            rel_map[pb]['children'].add(pa)
        elif rt == 'parent_of':
            rel_map[pa]['children'].add(pb)
            rel_map[pb]['parents'].add(pa)

    # Bucket persons by canonical surname
    surname_buckets = defaultdict(list)
    for p in persons:
        tokens = tokenize_name(p['name'])
        if not tokens: continue
        
        # Primary surname token
        ln = tokens[-1]
        cln = surname_map.get(ln, ln)
        p['tokens'] = tokens
        p['fn'] = tokens[0]
        p['ln'] = ln
        p['cln'] = cln
        p['by'] = extract_year(p['birth_info'])
        p['dy'] = extract_year(p['death_info'])
        p['bd'] = extract_exact_date(p['birth_info'])
        p['dd'] = extract_exact_date(p['death_info'])
        surname_buckets[cln].append(p)

    candidate_pairs = []
    
    for cln, plist in surname_buckets.items():
        if len(plist) < 2: continue
        
        for i in range(len(plist)):
            p1 = plist[i]
            t1 = p1['tokens']
            fn1 = p1['fn']
            formal1 = NICK_TO_FORMAL.get(fn1, fn1)
            
            for j in range(i + 1, len(plist)):
                p2 = plist[j]
                t2 = p2['tokens']
                fn2 = p2['fn']
                formal2 = NICK_TO_FORMAL.get(fn2, fn2)
                
                confidence = 0
                reasons = []
                
                # Check given name match or nickname match
                name_sim = SequenceMatcher(None, ' '.join(t1), ' '.join(t2)).ratio()
                
                if fn1 == fn2:
                    confidence += 30
                    reasons.append(f"Matching given name '{fn1}'")
                    # Check middle initial expansion: e.g. ['noah', 'harmon'] vs ['noah', 'c', 'harmon']
                    if (len(t1) == 2 and len(t2) == 3 and t2[0] == fn1 and t2[-1] == p1['ln']) or \
                       (len(t2) == 2 and len(t1) == 3 and t1[0] == fn2 and t1[-1] == p2['ln']):
                        confidence += 25
                        reasons.append(f"Middle initial expansion ('{p1['name']}' ↔ '{p2['name']}')")
                elif formal1 == formal2:
                    confidence += 25
                    reasons.append(f"Nickname equivalence ({fn1} ↔ {fn2})")
                elif name_sim >= 0.85:
                    confidence += 20
                    reasons.append(f"High name similarity ({name_sim:.0%})")
                else:
                    continue
                    
                # Vital Dates Compatibility Check
                by1, by2 = p1['by'], p2['by']
                dy1, dy2 = p1['dy'], p2['dy']
                bd1, bd2 = p1['bd'], p2['bd']
                dd1, dd2 = p1['dd'], p2['dd']
                
                date_evidence = False
                
                if by1 and by2:
                    if by1 == by2:
                        confidence += 35
                        reasons.append(f"Exact birth year ({by1})")
                        date_evidence = True
                        if bd1 and bd2 and bd1 == bd2:
                            confidence += 15
                            reasons.append(f"Exact birth date match ('{bd1}')")
                    elif abs(by1 - by2) <= 1:
                        confidence += 20
                        reasons.append(f"Compatible birth year ({by1} vs {by2})")
                        date_evidence = True
                    else:
                        # Conflicting birth years
                        confidence -= 60
                        reasons.append(f"Conflicting birth years ({by1} vs {by2})")
                        
                if dy1 and dy2:
                    if dy1 == dy2:
                        confidence += 35
                        reasons.append(f"Exact death year ({dy1})")
                        date_evidence = True
                        if dd1 and dd2 and dd1 == dd2:
                            confidence += 15
                            reasons.append(f"Exact death date match ('{dd1}')")
                    elif abs(dy1 - dy2) <= 1:
                        confidence += 20
                        reasons.append(f"Compatible death year ({dy1} vs {dy2})")
                        date_evidence = True
                    else:
                        # Conflicting death years
                        confidence -= 60
                        reasons.append(f"Conflicting death years ({dy1} vs {dy2})")

                # Family network corroboration
                rels1 = rel_map[p1['person_id']]
                rels2 = rel_map[p2['person_id']]
                shared_spouses = rels1['spouses'].intersection(rels2['spouses'])
                shared_parents = rels1['parents'].intersection(rels2['parents'])
                shared_children = rels1['children'].intersection(rels2['children'])
                
                if shared_spouses:
                    confidence += 35
                    reasons.append(f"Shared spouse(s): {shared_spouses}")
                if shared_parents:
                    confidence += 35
                    reasons.append(f"Shared parent(s): {shared_parents}")
                if shared_children:
                    confidence += 25
                    reasons.append(f"Shared child(ren): {shared_children}")

                # Cross-dataset provenance bonus
                if p1['dataset_source'] != p2['dataset_source'] and date_evidence:
                    confidence += 10
                    reasons.append(f"Cross-dataset match ({p1['dataset_source']} ↔ {p2['dataset_source']})")
                    
                if confidence >= 60:
                    tier = "Tier 1: High Confidence (≥ 85%)" if confidence >= 85 else \
                           "Tier 2: Medium Confidence (70-84%)" if confidence >= 70 else \
                           "Tier 3: Review Candidate (60-69%)"
                    candidate_pairs.append({
                        'p1': p1,
                        'p2': p2,
                        'confidence': confidence,
                        'tier': tier,
                        'reasons': reasons
                    })

    candidate_pairs.sort(key=lambda x: x['confidence'], reverse=True)
    
    tier_counts = defaultdict(int)
    for c_pair in candidate_pairs:
        tier_counts[c_pair['tier']] += 1
        
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Audit Scan Completed:")
    print(f"  Total Duplicate Candidate Pairs Found: {len(candidate_pairs):,}")
    for t in sorted(tier_counts.keys()):
        print(f"  • {t}: {tier_counts[t]:,} candidate pairs")
        
    conn.close()
    return candidate_pairs

if __name__ == "__main__":
    run_deduplication_audit()
