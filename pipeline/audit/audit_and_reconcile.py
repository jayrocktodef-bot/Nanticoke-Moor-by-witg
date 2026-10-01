#!/usr/bin/env python3
"""
Genealogical Audit & Conflict Resolution Engine (audit_and_reconcile.py)
========================================================================
Analyzes genealogy_preservation.db to identify, log, and resolve discrepancies
across all merged datasets (lynncjackson.com, moors-delaware.com,
nativeamericansofdelawarestate.com).

Zero-speculation policy: all reconciliations are based on verified primary
source data, not inferred or guessed relationships.

Audit Categories:
  1. Impossible Lifespans & Anachronistic Dates
  2. Duplicate Person Detection (exact + fuzzy)
  3. Non-Person Entity Cleanup
  4. Circular / Contradictory Relationships
  5. Orphaned Media & Dangling References
  6. Cross-Dataset Merge Candidates
  7. Parent-Child Age Gap Violations
"""

import os
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

# ─── Configuration ────────────────────────────────────────────────────────
MIN_MOTHER_AGE = 12
MAX_MOTHER_AGE = 55
MIN_FATHER_AGE = 13
MAX_FATHER_AGE = 75
MAX_LIFESPAN_YEARS = 115
EARLIEST_PLAUSIBLE_BIRTH = 1600
FUZZY_MATCH_THRESHOLD = 0.82  # High confidence for auto-merge candidates
FUZZY_REVIEW_THRESHOLD = 0.70  # Lower threshold for manual review

# Non-person indicators: fragments that should never be person records
NON_PERSON_PATTERNS = [
    r"^(see\s+)?family\s+(history|report|bible)",
    r"^(census|bible|probate|marriage|obituary|orphans\s+court)\s+records?",
    r"^\d{4}\s+(census|de\s+federal)",
    r"^(kent|sussex|new\s+castle)\s+county",
    r"^(his|her|the)\s+(will|family|son|daughter)",
    r"^(he|she)\s+(was|is)\s+the",
    r"^(linked\s+to|see\s+also|index|contents?)",
    r"^(j\s*-\s*p|a\s*-\s*c|d\s*-\s*f|g\s*-\s*i|s\s*-\s*z|e\s*-\s*l|m|n\s*-\s*r)$",
    r"^cott\s+family",
    r"^the\s+(durham|lecount|ridgeway|coker|carty|jackson|carter|munce)\s+family",
]

NON_PERSON_COMPILED = [re.compile(p, re.IGNORECASE) for p in NON_PERSON_PATTERNS]


# ─── Schema ───────────────────────────────────────────────────────────────
def init_audit_schema(conn):
    """Create the audit_flags table for storing all findings."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_flags (
            flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('critical','warning','info')),
            person_id INTEGER,
            person_id_secondary INTEGER,
            description TEXT NOT NULL,
            evidence TEXT,
            resolution TEXT,
            resolved_at TEXT,
            auto_resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            FOREIGN KEY(person_id_secondary) REFERENCES persons(person_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_flags(category)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_flags(severity)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_person ON audit_flags(person_id)
    """)
    conn.commit()


def clear_previous_audit(conn):
    """Wipe all unresolved flags from previous audit runs (preserve resolved ones)."""
    conn.execute("DELETE FROM audit_flags WHERE auto_resolved = 0 AND resolved_at IS NULL")
    conn.commit()


# ─── Date Extraction Helpers ──────────────────────────────────────────────
def extract_year(text):
    """Extract the first plausible 4-digit year from free text."""
    if not text:
        return None
    # Match years like 1702, 1850, 1999
    matches = re.findall(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', str(text))
    if matches:
        return int(matches[0])
    # Try "abt", "ca.", "c " prefixed
    matches = re.findall(r'(?:abt?|ca?\.?\s*)(\d{4})', str(text), re.IGNORECASE)
    if matches:
        return int(matches[0])
    return None


def extract_birth_year(person_row):
    """Try birth_info first, then scan notes for birth indicators."""
    pid, name, birth_info, death_info, notes, source = person_row

    year = extract_year(birth_info)
    if year:
        return year

    if notes:
        # Look for "born <year>" or "(born <year>)" patterns
        m = re.search(r'born\s+(?:abt?\.?\s*|ca?\.?\s*|about\s+|bef(?:ore)?\s+)?(\d{4})', str(notes), re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def extract_death_year(person_row):
    """Try death_info first, then scan notes for death indicators."""
    pid, name, birth_info, death_info, notes, source = person_row

    year = extract_year(death_info)
    if year:
        return year

    if notes:
        m = re.search(r'(?:died|death|d\.)\s*(?:abt?\.?\s*|ca?\.?\s*|about\s+)?(\d{4})', str(notes), re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


# ─── Audit Module 1: Lifespan & Date Anomalies ───────────────────────────
def audit_lifespans(conn):
    """Flag impossible lifespans and anachronistic dates."""
    print("  [Audit 1] Scanning lifespans and date anomalies...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT person_id, name, birth_info, death_info, notes, dataset_source
        FROM persons
    """)
    persons = cursor.fetchall()

    flag_count = 0
    for person in persons:
        pid, name, birth_info, death_info, notes, source = person
        birth_year = extract_birth_year(person)
        death_year = extract_death_year(person)

        # Rule 1: Death before birth
        if birth_year and death_year and death_year < birth_year:
            conn.execute("""
                INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                VALUES ('lifespan', 'critical', ?, ?, ?)
            """, (pid,
                  f"Death year ({death_year}) precedes birth year ({birth_year})",
                  f"birth_info='{birth_info}', death_info='{death_info}', notes='{(notes or '')[:200]}'"))
            flag_count += 1

        # Rule 2: Born before 1600
        if birth_year and birth_year < EARLIEST_PLAUSIBLE_BIRTH:
            conn.execute("""
                INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                VALUES ('lifespan', 'warning', ?, ?, ?)
            """, (pid,
                  f"Birth year ({birth_year}) before {EARLIEST_PLAUSIBLE_BIRTH} — possibly erroneous",
                  f"name='{name}', notes='{(notes or '')[:200]}'"))
            flag_count += 1

        # Rule 3: Lifespan exceeds maximum
        if birth_year and death_year:
            lifespan = death_year - birth_year
            if lifespan > MAX_LIFESPAN_YEARS:
                conn.execute("""
                    INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                    VALUES ('lifespan', 'warning', ?, ?, ?)
                """, (pid,
                      f"Lifespan of {lifespan} years exceeds {MAX_LIFESPAN_YEARS}-year maximum",
                      f"born={birth_year}, died={death_year}"))
                flag_count += 1

    conn.commit()
    print(f"    → {flag_count} lifespan flags raised")
    return flag_count


# ─── Audit Module 2: Non-Person Entity Detection ─────────────────────────
def audit_non_person_entities(conn):
    """Identify records that are clearly not people (labels, categories, fragments)."""
    print("  [Audit 2] Scanning for non-person entities...")
    cursor = conn.cursor()
    cursor.execute("SELECT person_id, name, dataset_source FROM persons")
    persons = cursor.fetchall()

    flag_count = 0
    auto_cleaned = 0

    for pid, name, source in persons:
        is_non_person = False
        reason = ""

        # Check against compiled non-person patterns
        for pattern in NON_PERSON_COMPILED:
            if pattern.search(name.strip()):
                is_non_person = True
                reason = f"Matches non-person pattern: {pattern.pattern}"
                break

        # Very short names (less than 3 chars) are likely fragments
        if not is_non_person and len(name.strip()) < 3:
            is_non_person = True
            reason = f"Name too short ({len(name.strip())} chars) — likely a data fragment"

        # Names that are all uppercase single words without any letter variation
        if not is_non_person and name.strip().isupper() and len(name.split()) == 1 and len(name) > 2:
            # Single uppercase words like "BORN" or "DIED" aren't people
            if name.strip().upper() in ("BORN", "DIED", "MARRIED", "SEE", "INDEX", "CONTENTS",
                                        "FAMILY", "RECORDS", "CENSUS", "BIBLE", "NOTE", "NOTES"):
                is_non_person = True
                reason = f"Single keyword '{name.strip()}' is not a person name"

        if is_non_person:
            # Check if this person has any relationships before flagging
            cursor.execute("""
                SELECT COUNT(*) FROM relationships
                WHERE person_a_id = ? OR person_b_id = ?
            """, (pid, pid))
            rel_count = cursor.fetchone()[0]

            severity = 'info' if rel_count > 0 else 'warning'

            conn.execute("""
                INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                VALUES ('non_person', ?, ?, ?, ?)
            """, (severity, pid,
                  f"Non-person entity detected: '{name}'",
                  f"reason={reason}, relationships={rel_count}, source={source}"))
            flag_count += 1

    conn.commit()
    print(f"    → {flag_count} non-person entity flags raised")
    return flag_count


# ─── Audit Module 3: Duplicate Detection ─────────────────────────────────
def normalize_name(name):
    """Normalize a name for comparison: lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r'[.,;:()\[\]"\'!?]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name


def audit_duplicates(conn):
    """Identify exact and fuzzy duplicate person records."""
    print("  [Audit 3] Scanning for duplicate persons...")
    cursor = conn.cursor()
    cursor.execute("SELECT person_id, name, dataset_source, notes FROM persons")
    persons = cursor.fetchall()

    # Phase 1: Exact duplicates (after normalization)
    norm_map = defaultdict(list)
    for pid, name, source, notes in persons:
        nname = normalize_name(name)
        if len(nname) >= 3:  # Skip tiny fragments
            norm_map[nname].append((pid, name, source))

    exact_flag_count = 0
    for nname, entries in norm_map.items():
        if len(entries) > 1:
            # Group by dataset source
            primary = entries[0]
            for duplicate in entries[1:]:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('duplicate_exact', 'warning', ?, ?, ?, ?)
                """, (primary[0], duplicate[0],
                      f"Exact name match after normalization: '{primary[1]}' ↔ '{duplicate[1]}'",
                      f"primary_source={primary[2]}, dup_source={duplicate[2]}, normalized='{nname}'"))
                exact_flag_count += 1

    # Phase 2: Fuzzy duplicates (across datasets, higher threshold)
    fuzzy_flag_count = 0
    already_flagged = set()

    # Only compare across different datasets for fuzzy matching
    by_source = defaultdict(list)
    for pid, name, source, notes in persons:
        nname = normalize_name(name)
        if len(nname) >= 5:  # Need enough chars for meaningful fuzzy match
            by_source[source].append((pid, name, nname))

    sources = list(by_source.keys())
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            src_a, src_b = sources[i], sources[j]
            for pid_a, name_a, nnorm_a in by_source[src_a]:
                for pid_b, name_b, nnorm_b in by_source[src_b]:
                    pair_key = (min(pid_a, pid_b), max(pid_a, pid_b))
                    if pair_key in already_flagged:
                        continue

                    # Skip if already an exact match
                    if nnorm_a == nnorm_b:
                        continue

                    score = SequenceMatcher(None, nnorm_a, nnorm_b).ratio()
                    if score >= FUZZY_REVIEW_THRESHOLD:
                        already_flagged.add(pair_key)
                        severity = 'warning' if score >= FUZZY_MATCH_THRESHOLD else 'info'
                        conn.execute("""
                            INSERT INTO audit_flags
                            (category, severity, person_id, person_id_secondary, description, evidence)
                            VALUES ('duplicate_fuzzy', ?, ?, ?, ?, ?)
                        """, (severity, pid_a, pid_b,
                              f"Fuzzy name match ({score:.0%}): '{name_a}' ↔ '{name_b}'",
                              f"source_a={src_a}, source_b={src_b}, score={score:.4f}"))
                        fuzzy_flag_count += 1

    conn.commit()
    total = exact_flag_count + fuzzy_flag_count
    print(f"    → {exact_flag_count} exact + {fuzzy_flag_count} fuzzy = {total} duplicate flags raised")
    return total


# ─── Audit Module 4: Circular & Contradictory Relationships ──────────────
def audit_circular_relationships(conn):
    """Detect impossible relationship loops and contradictions."""
    print("  [Audit 4] Scanning for circular/contradictory relationships...")
    cursor = conn.cursor()

    flag_count = 0

    # 4a: Self-referencing relationships
    cursor.execute("""
        SELECT id, person_a_id, person_b_id, relationship_type
        FROM relationships WHERE person_a_id = person_b_id
    """)
    for rel_id, pa, pb, rtype in cursor.fetchall():
        conn.execute("""
            INSERT INTO audit_flags (category, severity, person_id, description, evidence)
            VALUES ('circular', 'critical', ?, ?, ?)
        """, (pa,
              f"Self-referencing relationship: person {pa} is '{rtype}' of themselves",
              f"relationship_id={rel_id}"))
        flag_count += 1

    # 4b: Bidirectional parent-child (A is parent of B AND B is parent of A)
    cursor.execute("""
        SELECT r1.id, r1.person_a_id, r1.person_b_id, r1.relationship_type,
               r2.id, r2.relationship_type
        FROM relationships r1
        JOIN relationships r2
          ON r1.person_a_id = r2.person_b_id
         AND r1.person_b_id = r2.person_a_id
        WHERE r1.id < r2.id
          AND r1.relationship_type IN ('parent_of', 'child_of')
          AND r2.relationship_type IN ('parent_of', 'child_of')
    """)
    for r1_id, pa, pb, rtype1, r2_id, rtype2 in cursor.fetchall():
        # parent_of/child_of is expected complementary, but parent_of/parent_of is circular
        if rtype1 == rtype2:
            conn.execute("""
                INSERT INTO audit_flags
                (category, severity, person_id, person_id_secondary, description, evidence)
                VALUES ('circular', 'critical', ?, ?, ?, ?)
            """, (pa, pb,
                  f"Mutual {rtype1} relationship: {pa} ↔ {pb}",
                  f"rel_ids={r1_id},{r2_id}"))
            flag_count += 1

    # 4c: Person is both spouse and parent/child of the same person
    cursor.execute("""
        SELECT r1.person_a_id, r1.person_b_id, r1.relationship_type, r2.relationship_type
        FROM relationships r1
        JOIN relationships r2
          ON ((r1.person_a_id = r2.person_a_id AND r1.person_b_id = r2.person_b_id)
              OR (r1.person_a_id = r2.person_b_id AND r1.person_b_id = r2.person_a_id))
        WHERE r1.id < r2.id
          AND r1.relationship_type = 'spouse'
          AND r2.relationship_type IN ('parent_of', 'child_of')
    """)
    for pa, pb, rtype1, rtype2 in cursor.fetchall():
        conn.execute("""
            INSERT INTO audit_flags
            (category, severity, person_id, person_id_secondary, description, evidence)
            VALUES ('contradictory', 'critical', ?, ?, ?, ?)
        """, (pa, pb,
              f"Contradictory relationship: persons {pa} & {pb} are both 'spouse' and '{rtype2}'",
              f"Likely data merge error"))
        flag_count += 1

    # 4d: Multi-generational cycle detection (A→B→C→...→A via parent_of)
    cursor.execute("""
        SELECT person_a_id, person_b_id FROM relationships
        WHERE relationship_type IN ('parent_of', 'child_of')
    """)
    parent_graph = defaultdict(set)
    for pa, pb in cursor.fetchall():
        parent_graph[pa].add(pb)

    def detect_cycle(start, graph, max_depth=10):
        """BFS-based cycle detection with depth limit."""
        visited = set()
        queue = [(start, 0)]
        while queue:
            node, depth = queue.pop(0)
            if depth > max_depth:
                continue
            if node == start and depth > 0:
                return True
            if node in visited:
                continue
            visited.add(node)
            for neighbor in graph.get(node, []):
                queue.append((neighbor, depth + 1))
        return False

    checked_nodes = set()
    for node in parent_graph:
        if node not in checked_nodes:
            if detect_cycle(node, parent_graph):
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, description, evidence)
                    VALUES ('circular', 'critical', ?, ?, ?)
                """, (node,
                      f"Multi-generational cycle detected starting from person {node}",
                      "Parent-child chain loops back to origin"))
                flag_count += 1
            checked_nodes.add(node)

    conn.commit()
    print(f"    → {flag_count} circular/contradictory flags raised")
    return flag_count


# ─── Audit Module 5: Parent-Child Age Gaps ───────────────────────────────
def audit_parent_child_gaps(conn):
    """Flag implausible parent-child age differences."""
    print("  [Audit 5] Scanning parent-child age gaps...")
    cursor = conn.cursor()

    # Get all parent_of relationships
    cursor.execute("""
        SELECT r.id, r.person_a_id, r.person_b_id,
               pa.name, pa.birth_info, pa.death_info, pa.notes, pa.dataset_source,
               pb.name, pb.birth_info, pb.death_info, pb.notes, pb.dataset_source
        FROM relationships r
        JOIN persons pa ON r.person_a_id = pa.person_id
        JOIN persons pb ON r.person_b_id = pb.person_id
        WHERE r.relationship_type = 'parent_of'
    """)

    flag_count = 0
    for row in cursor.fetchall():
        rel_id = row[0]
        parent_row = (row[1], row[3], row[4], row[5], row[6], row[7])
        child_row = (row[2], row[8], row[9], row[10], row[11], row[12])

        parent_birth = extract_birth_year(parent_row)
        child_birth = extract_birth_year(child_row)

        if parent_birth and child_birth:
            gap = child_birth - parent_birth

            if gap < 0:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('age_gap', 'critical', ?, ?, ?, ?)
                """, (row[1], row[2],
                      f"Parent '{row[3]}' born AFTER child '{row[8]}' (gap: {gap} years)",
                      f"parent_birth={parent_birth}, child_birth={child_birth}"))
                flag_count += 1
            elif gap < MIN_MOTHER_AGE:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('age_gap', 'warning', ?, ?, ?, ?)
                """, (row[1], row[2],
                      f"Parent '{row[3]}' only {gap} years older than child '{row[8]}'",
                      f"parent_birth={parent_birth}, child_birth={child_birth}, min_expected={MIN_MOTHER_AGE}"))
                flag_count += 1
            elif gap > MAX_FATHER_AGE:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('age_gap', 'warning', ?, ?, ?, ?)
                """, (row[1], row[2],
                      f"Parent '{row[3]}' was {gap} years old at child '{row[8]}'s birth",
                      f"parent_birth={parent_birth}, child_birth={child_birth}, max_expected={MAX_FATHER_AGE}"))
                flag_count += 1

    # Also check child_of relationships (reversed direction)
    cursor.execute("""
        SELECT r.id, r.person_a_id, r.person_b_id,
               pa.name, pa.birth_info, pa.death_info, pa.notes, pa.dataset_source,
               pb.name, pb.birth_info, pb.death_info, pb.notes, pb.dataset_source
        FROM relationships r
        JOIN persons pa ON r.person_a_id = pa.person_id
        JOIN persons pb ON r.person_b_id = pb.person_id
        WHERE r.relationship_type = 'child_of'
    """)

    for row in cursor.fetchall():
        # In child_of: person_a is the child, person_b is the parent
        child_row = (row[1], row[3], row[4], row[5], row[6], row[7])
        parent_row = (row[2], row[8], row[9], row[10], row[11], row[12])

        parent_birth = extract_birth_year(parent_row)
        child_birth = extract_birth_year(child_row)

        if parent_birth and child_birth:
            gap = child_birth - parent_birth

            if gap < 0:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('age_gap', 'critical', ?, ?, ?, ?)
                """, (row[2], row[1],
                      f"Parent '{row[8]}' born AFTER child '{row[3]}' (gap: {gap} years)",
                      f"parent_birth={parent_birth}, child_birth={child_birth}"))
                flag_count += 1
            elif gap < MIN_MOTHER_AGE:
                conn.execute("""
                    INSERT INTO audit_flags
                    (category, severity, person_id, person_id_secondary, description, evidence)
                    VALUES ('age_gap', 'warning', ?, ?, ?, ?)
                """, (row[2], row[1],
                      f"Parent '{row[8]}' only {gap} years older than child '{row[3]}'",
                      f"parent_birth={parent_birth}, child_birth={child_birth}"))
                flag_count += 1

    conn.commit()
    print(f"    → {flag_count} parent-child age gap flags raised")
    return flag_count


# ─── Audit Module 6: Orphaned Media & Dangling References ────────────────
def audit_orphaned_records(conn):
    """Find dangling FK references, orphaned photos, and broken links."""
    print("  [Audit 6] Scanning for orphaned media and dangling references...")
    cursor = conn.cursor()
    flag_count = 0

    # 6a: Relationships pointing to non-existent persons
    cursor.execute("""
        SELECT r.id, r.person_a_id, r.person_b_id, r.relationship_type
        FROM relationships r
        LEFT JOIN persons pa ON r.person_a_id = pa.person_id
        LEFT JOIN persons pb ON r.person_b_id = pb.person_id
        WHERE pa.person_id IS NULL OR pb.person_id IS NULL
    """)
    for rel_id, pa, pb, rtype in cursor.fetchall():
        conn.execute("""
            INSERT INTO audit_flags (category, severity, description, evidence)
            VALUES ('orphaned', 'warning', ?, ?)
        """, (f"Relationship {rel_id} references non-existent person(s)",
              f"person_a={pa}, person_b={pb}, type={rtype}"))
        flag_count += 1

    # 6b: person_photos pointing to non-existent persons or photos
    cursor.execute("""
        SELECT pp.id, pp.person_id, pp.photo_id
        FROM person_photos pp
        LEFT JOIN persons p ON pp.person_id = p.person_id
        LEFT JOIN photo_catalog pc ON pp.photo_id = pc.photo_id
        WHERE p.person_id IS NULL OR pc.photo_id IS NULL
    """)
    for ppid, pid, phid in cursor.fetchall():
        conn.execute("""
            INSERT INTO audit_flags (category, severity, person_id, description, evidence)
            VALUES ('orphaned', 'info', ?, ?, ?)
        """, (pid,
              f"Person-photo link {ppid} references missing person or photo",
              f"person_id={pid}, photo_id={phid}"))
        flag_count += 1

    # 6c: entity_matches pointing to non-existent persons
    cursor.execute("""
        SELECT em.match_id, em.person_id_jackson, em.person_id_moors
        FROM entity_matches em
        LEFT JOIN persons pa ON em.person_id_jackson = pa.person_id
        LEFT JOIN persons pb ON em.person_id_moors = pb.person_id
        WHERE pa.person_id IS NULL OR pb.person_id IS NULL
    """)
    for mid, pj, pm in cursor.fetchall():
        conn.execute("""
            INSERT INTO audit_flags (category, severity, description, evidence)
            VALUES ('orphaned', 'info', ?, ?)
        """, (f"Entity match {mid} references non-existent person(s)",
              f"jackson_id={pj}, moors_id={pm}"))
        flag_count += 1

    # 6d: Photos with missing local files
    cursor.execute("SELECT photo_id, local_image_path, title_or_caption FROM photo_catalog")
    for phid, local_path, caption in cursor.fetchall():
        if local_path and not os.path.isabs(local_path):
            full_path = os.path.join(OUTPUT_DIR, local_path)
        else:
            full_path = local_path

        if full_path and not os.path.exists(str(full_path)):
            conn.execute("""
                INSERT INTO audit_flags (category, severity, description, evidence)
                VALUES ('orphaned_media', 'info', ?, ?)
            """, (f"Photo file missing on disk: '{caption or 'untitled'}'",
                  f"photo_id={phid}, path={local_path}"))
            flag_count += 1

    conn.commit()
    print(f"    → {flag_count} orphaned/dangling reference flags raised")
    return flag_count


# ─── Audit Module 7: Cross-Dataset Merge Quality ─────────────────────────
def audit_cross_dataset_merges(conn):
    """Review existing entity_matches and cross_dataset_match relationships for quality."""
    print("  [Audit 7] Reviewing cross-dataset merge quality...")
    cursor = conn.cursor()
    flag_count = 0

    # Check entity_matches with low confidence
    cursor.execute("""
        SELECT em.match_id, em.person_id_jackson, em.person_id_moors,
               em.confidence_score, em.match_status,
               pj.name, pm.name
        FROM entity_matches em
        JOIN persons pj ON em.person_id_jackson = pj.person_id
        JOIN persons pm ON em.person_id_moors = pm.person_id
    """)
    for mid, pj, pm, score, status, name_j, name_m in cursor.fetchall():
        if score and score < FUZZY_REVIEW_THRESHOLD:
            conn.execute("""
                INSERT INTO audit_flags
                (category, severity, person_id, person_id_secondary, description, evidence)
                VALUES ('merge_quality', 'warning', ?, ?, ?, ?)
            """, (pj, pm,
                  f"Low-confidence cross-dataset match ({score:.0%}): '{name_j}' ↔ '{name_m}'",
                  f"match_id={mid}, status={status}"))
            flag_count += 1

    conn.commit()
    print(f"    → {flag_count} merge quality flags raised")
    return flag_count


# ─── Auto-Resolution Engine ──────────────────────────────────────────────
def auto_resolve_safe_flags(conn):
    """
    Automatically resolve flags that have safe, unambiguous resolutions.
    Only resolves non-person entities with zero relationships (safe to ignore).
    """
    print("  [Auto-Resolve] Applying safe automatic resolutions...")
    cursor = conn.cursor()
    resolved = 0

    # Auto-resolve: non-person entities with no relationships can be marked for cleanup
    cursor.execute("""
        SELECT flag_id, person_id, description
        FROM audit_flags
        WHERE category = 'non_person'
          AND severity = 'warning'
          AND resolved_at IS NULL
          AND auto_resolved = 0
    """)
    for flag_id, pid, desc in cursor.fetchall():
        # Verify the person still has no relationships
        cursor.execute("""
            SELECT COUNT(*) FROM relationships
            WHERE person_a_id = ? OR person_b_id = ?
        """, (pid, pid))
        rel_count = cursor.fetchone()[0]

        if rel_count == 0:
            conn.execute("""
                UPDATE audit_flags
                SET resolution = 'Safe to remove: non-person entity with no relationship links',
                    auto_resolved = 1,
                    resolved_at = datetime('now')
                WHERE flag_id = ?
            """, (flag_id,))
            resolved += 1

    conn.commit()
    print(f"    → {resolved} flags auto-resolved")
    return resolved


# ─── Reporting ────────────────────────────────────────────────────────────
def generate_audit_report(conn):
    """Print a formatted summary of all audit findings."""
    cursor = conn.cursor()

    print("\n" + "=" * 72)
    print("  GENEALOGICAL AUDIT REPORT")
    print("=" * 72)

    # Summary by category
    cursor.execute("""
        SELECT category, severity, COUNT(*) as cnt
        FROM audit_flags
        WHERE resolved_at IS NULL
        GROUP BY category, severity
        ORDER BY
            CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
            category
    """)
    rows = cursor.fetchall()

    print("\n  ┌─ Unresolved Flags by Category ─────────────────────────────────┐")
    print(f"  │ {'Category':<25} {'Severity':<12} {'Count':>6}  │")
    print(f"  │{'─' * 46}│")
    total = 0
    for category, severity, count in rows:
        icon = "🔴" if severity == 'critical' else "🟡" if severity == 'warning' else "🔵"
        print(f"  │ {icon} {category:<23} {severity:<12} {count:>5}  │")
        total += count
    print(f"  │{'─' * 46}│")
    print(f"  │ {'TOTAL UNRESOLVED':<37} {total:>6}  │")
    print(f"  └{'─' * 47}┘")

    # Auto-resolved summary
    cursor.execute("SELECT COUNT(*) FROM audit_flags WHERE auto_resolved = 1")
    auto_count = cursor.fetchone()[0]
    if auto_count > 0:
        print(f"\n  ✅ {auto_count} flag(s) were safely auto-resolved.")

    # Top critical issues
    cursor.execute("""
        SELECT category, person_id, description
        FROM audit_flags
        WHERE severity = 'critical' AND resolved_at IS NULL
        ORDER BY flag_id
        LIMIT 15
    """)
    critical = cursor.fetchall()
    if critical:
        print("\n  ── Top Critical Issues ──")
        for cat, pid, desc in critical:
            pid_str = f"[Person {pid}]" if pid else "[N/A]"
            print(f"    ❗ {pid_str} {desc}")

    # Top duplicate candidates
    cursor.execute("""
        SELECT person_id, person_id_secondary, description
        FROM audit_flags
        WHERE category IN ('duplicate_exact', 'duplicate_fuzzy')
          AND severity = 'warning'
          AND resolved_at IS NULL
        ORDER BY flag_id
        LIMIT 10
    """)
    dupes = cursor.fetchall()
    if dupes:
        print("\n  ── Top Duplicate Merge Candidates ──")
        for pid_a, pid_b, desc in dupes:
            print(f"    🔀 [Person {pid_a} ↔ {pid_b}] {desc}")

    print("\n" + "=" * 72)
    print(f"  Audit completed at {datetime.now().isoformat()}")
    print("=" * 72 + "\n")


# ─── Main Orchestrator ───────────────────────────────────────────────────
def run_full_audit():
    """Execute all audit modules in sequence."""
    print("=" * 72)
    print("  GENEALOGICAL AUDIT & CONFLICT RESOLUTION ENGINE")
    print(f"  Database: {DB_PATH}")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 72)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Initialize schema and clear old unresolved flags
    init_audit_schema(conn)
    clear_previous_audit(conn)

    print("\n[Phase 1] Running Audit Modules...")
    total_flags = 0

    total_flags += audit_lifespans(conn)
    total_flags += audit_non_person_entities(conn)
    total_flags += audit_duplicates(conn)
    total_flags += audit_circular_relationships(conn)
    total_flags += audit_parent_child_gaps(conn)
    total_flags += audit_orphaned_records(conn)
    total_flags += audit_cross_dataset_merges(conn)

    print(f"\n[Phase 2] Auto-Resolving Safe Flags...")
    auto_resolved = auto_resolve_safe_flags(conn)

    print(f"\n[Phase 3] Generating Report...")
    generate_audit_report(conn)

    conn.close()
    print(f"Total flags raised: {total_flags}")
    print(f"Auto-resolved: {auto_resolved}")
    print(f"Remaining for manual review: {total_flags - auto_resolved}")


if __name__ == "__main__":
    run_full_audit()
