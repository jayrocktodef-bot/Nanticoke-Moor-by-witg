#!/usr/bin/env python3
"""
reconcile_and_hydrate_genealogy.py
===================================
1. Prunes spurious child_of edges on documented spouses.
2. Deduplicates relationship edges.
3. Fixes chronologically impossible birth/death dates caused by bogus modern FindAGrave matches.
4. Hydrates missing birth and death dates from source pages and records with citations.
5. Resolves multi-parent (>2 parents) anomalies using chronological validation and evidence strength.
"""

import os
import re
import sqlite3
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")

def extract_year(text):
    if not text:
        return None
    m = re.findall(r'\b(1[6789]\d\d|20[012]\d)\b', str(text))
    return int(m[0]) if m else None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("=== STEP 1: PRUNING ERRONEOUS CHILD_OF EDGES ON SPOUSES ===")
    c.execute("""
        SELECT r2.id, r2.person_a_id, r2.person_b_id, p1.name as n1, p2.name as n2, r1.evidence_text
        FROM relationships r1
        JOIN relationships r2 ON (
            (r1.person_a_id = r2.person_a_id AND r1.person_b_id = r2.person_b_id) OR
            (r1.person_a_id = r2.person_b_id AND r1.person_b_id = r2.person_a_id)
        )
        JOIN persons p1 ON r2.person_a_id = p1.person_id
        JOIN persons p2 ON r2.person_b_id = p2.person_id
        WHERE r1.relationship_type = 'spouse' AND r2.relationship_type = 'child_of'
    """)
    spouse_child_conflicts = c.fetchall()
    for row in spouse_child_conflicts:
        print(f"  Removing bogus child_of #{row['id']} between spouses {row['n1']} ({row['person_a_id']}) and {row['n2']} ({row['person_b_id']})")
        c.execute("DELETE FROM relationships WHERE id = ?", (row['id'],))

    print(f"Pruned {len(spouse_child_conflicts)} spurious child_of edges on spouses.\n")

    print("=== STEP 2: DEDUPLICATING RELATIONSHIP EDGES ===")
    # Remove duplicate inverse edges (e.g. 1681 child_of 8679 and 8679 parent_of 1681)
    c.execute("""
        SELECT r2.id, r1.person_a_id, r1.person_b_id
        FROM relationships r1
        JOIN relationships r2 ON r1.person_a_id = r2.person_b_id 
                             AND r1.person_b_id = r2.person_a_id
                             AND r1.relationship_type = 'child_of'
                             AND r2.relationship_type = 'parent_of'
    """)
    inverse_dupes = c.fetchall()
    for row in inverse_dupes:
        print(f"  Removing redundant parent_of #{row['id']} (child_of already exists)")
        c.execute("DELETE FROM relationships WHERE id = ?", (row['id'],))

    # Remove duplicate cross_dataset_match
    c.execute("""
        SELECT r2.id
        FROM relationships r1
        JOIN relationships r2 ON r1.id < r2.id
                             AND r1.person_a_id = r2.person_a_id 
                             AND r1.person_b_id = r2.person_b_id
                             AND r1.relationship_type = r2.relationship_type
    """)
    exact_dupes = c.fetchall()
    for row in exact_dupes:
        print(f"  Removing duplicate relationship #{row['id']}")
        c.execute("DELETE FROM relationships WHERE id = ?", (row['id'],))

    print(f"Deduplicated {len(inverse_dupes) + len(exact_dupes)} edges.\n")

    print("=== STEP 3: RECONCILING CORRUPTED FINDAGRAVE DATES ===")
    # Specifically fix John Puckham (#1696)
    c.execute("""
        UPDATE persons 
        SET birth_info = 'abt 1660', 
            death_info = 'aft 1683',
            notes = 'Nanticoke Indian born c. 1660 in Somerset Co, MD (Puckamee village); Baptized Jan 25, 1682/3'
        WHERE person_id = 1696
    """)
    # Update facts for John Puckham
    c.execute("UPDATE facts SET date_string = 'abt 1660', value_string = 'Nanticoke Indian born c. 1660 in Somerset Co, MD (Puckamee village)' WHERE person_id = 1696 AND fact_type = 'Birth'")
    c.execute("UPDATE facts SET date_string = 'aft 1683', value_string = 'Living after Jan 25, 1682/3 baptism' WHERE person_id = 1696 AND fact_type = 'Death'")

    # Detect other parents whose FindAGrave dates are impossibly modern compared to their children
    c.execute("SELECT person_id, name, birth_info, death_info, notes FROM persons")
    all_persons = {r['person_id']: dict(r) for r in c.fetchall()}
    for pid, p in all_persons.items():
        p['by'] = extract_year(p['birth_info'])
        p['dy'] = extract_year(p['death_info'])

    c.execute("SELECT person_a_id, person_b_id FROM relationships WHERE relationship_type = 'child_of'")
    child_edges = c.fetchall()

    corrupted_parents = {}
    for r in child_edges:
        ca = all_persons.get(r['person_a_id'])
        pb = all_persons.get(r['person_b_id'])
        if not ca or not pb:
            continue
        if ca['by'] and pb['by'] and (pb['by'] - ca['by'] > 15):
            corrupted_parents.setdefault(r['person_b_id'], []).append(ca)

    fixed_parents_count = 0
    for pb_id, children in corrupted_parents.items():
        parent = all_persons[pb_id]
        if 'findagrave' in (parent['notes'] or '').lower():
            # Oldest child birth year
            child_years = [c['by'] for c in children if c['by']]
            if child_years:
                min_child_year = min(child_years)
                est_birth_year = min_child_year - 25
                print(f"  Resetting corrupted FindAGrave dates for {parent['name']} (#{pb_id}): was b.{parent['by']}, d.{parent['dy']}. Oldest child born {min_child_year}. Estimated birth ~{est_birth_year}")
                
                # Clean notes to remove the erroneous FindAGrave link
                clean_notes = re.sub(r'\|?\s*Verified via FindAGrave[^\n\|]*', '', parent['notes'] or '').strip()
                c.execute("""
                    UPDATE persons 
                    SET birth_info = ?, death_info = 'unknown', notes = ?
                    WHERE person_id = ?
                """, (f"abt {est_birth_year}", clean_notes, pb_id))
                
                # Update birth fact
                c.execute("UPDATE facts SET date_string = ? WHERE person_id = ? AND fact_type = 'Birth'", (f"abt {est_birth_year}", pb_id))
                c.execute("UPDATE facts SET date_string = 'unknown' WHERE person_id = ? AND fact_type = 'Death'", (pb_id,))
                
                # Log audit flag
                c.execute("""
                    INSERT INTO audit_flags (category, severity, person_id, description, evidence, auto_resolved, created_at)
                    VALUES ('CHRONOLOGY_RECONCILED', 'info', ?, ?, ?, 1, datetime('now'))
                """, (pb_id, f"Corrected impossible modern FindAGrave dates to estimated ~{est_birth_year}", f"Children born starting {min_child_year}"))
                fixed_parents_count += 1

    print(f"Reconciled {fixed_parents_count} parents with corrupted modern FindAGrave dates.\n")

    print("=== STEP 4: HYDRATING MISSING BIRTH/DEATH DATES FROM SOURCE PAGES ===")
    c.execute("SELECT filename, text_content FROM pages WHERE text_content IS NOT NULL")
    pages = {row['filename'].lower(): row['text_content'] for row in c.fetchall()}

    c.execute("SELECT person_id, name, source_page, notes, birth_info, death_info FROM persons")
    persons_to_hydrate = c.fetchall()

    MONTH_REGEX = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

    hydrated_births = 0
    hydrated_deaths = 0

    for p in persons_to_hydrate:
        pid = p['person_id']
        name = p['name']
        b = p['birth_info']
        d = p['death_info']
        notes = p['notes'] or ''
        sp = p['source_page'] or ''

        linked_pages = []
        if sp and sp.lower() in pages:
            linked_pages.append(sp.lower())
        for m in re.findall(r'Linked to ([a-zA-Z0-9_\-\.]+\.htm)', notes):
            if m.lower() in pages and m.lower() not in linked_pages:
                linked_pages.append(m.lower())

        if not linked_pages:
            continue

        name_parts = [part for part in name.split() if len(part) > 1 and part.lower() not in ['front--', 'children:', 'widow', 'jr', 'sr']]
        if len(name_parts) < 2:
            continue
        first_last_pattern = re.escape(name_parts[0]) + r'(?:\s+[A-Za-z\.\"]+){0,2}\s+' + re.escape(name_parts[-1])

        new_b = None
        new_d = None
        source_doc = None
        evidence_snippet = None

        for lp in linked_pages:
            txt = pages[lp]
            for match in re.finditer(first_last_pattern, txt, re.IGNORECASE):
                start = max(0, match.start() - 60)
                end = min(len(txt), match.end() + 250)
                snippet = txt[start:end]

                if (not b or b.lower() == 'unknown') and not new_b:
                    m_b = re.search(r'(?:was\s+)?born(?:\s+in\s+[^,\.\n]+)?\s+on\s+([0-9]{1,2}\s+' + MONTH_REGEX + r',?\s+[0-9]{4}|' + MONTH_REGEX + r'\s+[0-9]{1,2},?\s+[0-9]{4})', snippet, re.IGNORECASE)
                    if not m_b:
                        m_b = re.search(r'(?:was\s+)?born(?:\s+in\s+[^,\.\n]+)?\s+(?:about|abt\.?|c\.\s*)?(' + MONTH_REGEX + r'\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{1,2}\s+' + MONTH_REGEX + r',?\s+[0-9]{4})', snippet, re.IGNORECASE)
                    if not m_b:
                        m_b = re.search(r'\((?:ca?\.?\s*)?([0-9]{4})\s*[-–]\s*([0-9]{4}|\s*)\)', snippet)
                        if m_b:
                            new_b = m_b.group(1).strip()
                            source_doc = lp
                            evidence_snippet = snippet
                    elif m_b:
                        new_b = m_b.group(1).replace('\n', ' ').strip()
                        source_doc = lp
                        evidence_snippet = snippet

                if (not d or d.lower() == 'unknown') and not new_d:
                    m_d = re.search(r'(?:died|departed this life)(?:\s+in\s+[^,\.\n]+)?\s+on\s+([0-9]{1,2}\s+' + MONTH_REGEX + r',?\s+[0-9]{4}|' + MONTH_REGEX + r'\s+[0-9]{1,2},?\s+[0-9]{4})', snippet, re.IGNORECASE)
                    if not m_d:
                        m_d = re.search(r'(?:died|departed this life)(?:\s+in\s+[^,\.\n]+)?\s+(?:about|abt\.?|c\.\s*)?(' + MONTH_REGEX + r'\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{1,2}\s+' + MONTH_REGEX + r',?\s+[0-9]{4})', snippet, re.IGNORECASE)
                    if not m_d:
                        m_d = re.search(r'\((?:ca?\.?\s*)?[0-9]{4}\s*[-–]\s*([0-9]{4})\)', snippet)
                        if m_d:
                            new_d = m_d.group(1).strip()
                            source_doc = lp
                            evidence_snippet = snippet
                    elif m_d:
                        new_d = m_d.group(1).replace('\n', ' ').strip()
                        source_doc = lp
                        evidence_snippet = snippet

        if new_b:
            c.execute("UPDATE persons SET birth_info = ? WHERE person_id = ?", (new_b, pid))
            # Insert or update birth fact
            c.execute("SELECT fact_id FROM facts WHERE person_id = ? AND fact_type = 'Birth'", (pid,))
            f_row = c.fetchone()
            if f_row:
                c.execute("UPDATE facts SET date_string = ?, value_string = ? WHERE fact_id = ?", (new_b, f"Born {new_b}", f_row['fact_id']))
                fact_id = f_row['fact_id']
            else:
                c.execute("INSERT INTO facts (person_id, fact_type, date_string, value_string) VALUES (?, 'Birth', ?, ?)",
                          (pid, new_b, f"Born {new_b}"))
                fact_id = c.lastrowid
            # Add citation
            c.execute("INSERT INTO citations (fact_id, evidence_text) VALUES (?, ?)", (fact_id, f"Documented in {source_doc}: {evidence_snippet[:200]}"))
            hydrated_births += 1

        if new_d:
            c.execute("UPDATE persons SET death_info = ? WHERE person_id = ?", (new_d, pid))
            # Insert or update death fact
            c.execute("SELECT fact_id FROM facts WHERE person_id = ? AND fact_type = 'Death'", (pid,))
            f_row = c.fetchone()
            if f_row:
                c.execute("UPDATE facts SET date_string = ?, value_string = ? WHERE fact_id = ?", (new_d, f"Died {new_d}", f_row['fact_id']))
                fact_id = f_row['fact_id']
            else:
                c.execute("INSERT INTO facts (person_id, fact_type, date_string, value_string) VALUES (?, 'Death', ?, ?)",
                          (pid, new_d, f"Died {new_d}"))
                fact_id = c.lastrowid
            c.execute("INSERT INTO citations (fact_id, evidence_text) VALUES (?, ?)", (fact_id, f"Documented in {source_doc}: {evidence_snippet[:200]}"))
            hydrated_deaths += 1

    print(f"Hydrated {hydrated_births} birth dates and {hydrated_deaths} death dates from primary source pages with citations.\n")

    print("=== STEP 5: RESOLVING MULTI-PARENT (>2 PARENTS) ANOMALIES ===")
    c.execute("""
        SELECT person_a_id as child_id, person_b_id as parent_id, r.id as rel_id, r.evidence_text
        FROM relationships r
        WHERE r.relationship_type = 'child_of'
    """)
    all_child_edges = c.fetchall()
    
    # Reload updated persons
    c.execute("SELECT person_id, name, birth_info, death_info, notes FROM persons")
    updated_persons = {r['person_id']: dict(r) for r in c.fetchall()}
    for pid, p in updated_persons.items():
        p['by'] = extract_year(p['birth_info'])
        p['dy'] = extract_year(p['death_info'])

    child_to_parents = {}
    for r in all_child_edges:
        child_to_parents.setdefault(r['child_id'], []).append(r)

    multi_parent_resolved = 0
    for child_id, parent_edges in child_to_parents.items():
        if len(parent_edges) <= 2:
            continue

        child = updated_persons.get(child_id)
        if not child:
            continue

        c_by = child['by']
        valid_edges = []
        invalid_edges = []

        for edge in parent_edges:
            parent = updated_persons.get(edge['parent_id'])
            if not parent:
                continue
            p_by = parent['by']
            p_dy = parent['dy']

            # Chronological check: Parent must be born BEFORE child (at least ~12 yrs), and parent cannot die before child birth
            is_impossible = False
            if c_by and p_by and p_by > c_by - 12:
                is_impossible = True
            if c_by and p_dy and p_dy < c_by - 1:
                is_impossible = True

            if is_impossible:
                invalid_edges.append(edge)
            else:
                valid_edges.append(edge)

        # If we have impossible parent edges, delete them
        for edge in invalid_edges:
            p_name = updated_persons[edge['parent_id']]['name']
            print(f"  Pruning chronologically impossible parent edge #{edge['rel_id']}: Parent {p_name} (#{edge['parent_id']}) for Child {child['name']} (#{child_id})")
            c.execute("DELETE FROM relationships WHERE id = ?", (edge['rel_id'],))
            multi_parent_resolved += 1

        # If still > 2 valid parents, keep the top 2 with strongest evidence
        if len(valid_edges) > 2:
            # Check if any pair are known spouses
            c.execute("""
                SELECT person_a_id, person_b_id FROM relationships WHERE relationship_type = 'spouse'
            """)
            couples = set()
            for row in c.fetchall():
                couples.add((row['person_a_id'], row['person_b_id']))
                couples.add((row['person_b_id'], row['person_a_id']))

            # Find couple among parents
            best_pair = None
            for i in range(len(valid_edges)):
                for j in range(i + 1, len(valid_edges)):
                    p1 = valid_edges[i]['parent_id']
                    p2 = valid_edges[j]['parent_id']
                    if (p1, p2) in couples:
                        best_pair = (valid_edges[i], valid_edges[j])
                        break
                if best_pair:
                    break

            if best_pair:
                keep_ids = {best_pair[0]['rel_id'], best_pair[1]['rel_id']}
                for edge in valid_edges:
                    if edge['rel_id'] not in keep_ids:
                        p_name = updated_persons[edge['parent_id']]['name']
                        print(f"  Pruning redundant 3rd+ parent edge #{edge['rel_id']}: Parent {p_name} (#{edge['parent_id']}) for Child {child['name']} (#{child_id}) (Retaining confirmed spouse parents)")
                        c.execute("DELETE FROM relationships WHERE id = ?", (edge['rel_id'],))
                        multi_parent_resolved += 1

    print(f"Resolved multi-parent anomalies, pruned {multi_parent_resolved} contradictory edges.\n")

    conn.commit()
    conn.close()
    print("Database reconciliation and hydration complete!")

if __name__ == "__main__":
    main()
