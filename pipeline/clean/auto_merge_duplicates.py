#!/usr/bin/env python3
"""
Auto-Merge Exact Duplicates (auto_merge_duplicates.py)
======================================================
Merges person records that are exact duplicates after normalization
(case, spacing, punctuation differences only). Preserves all relationships
and photo links by reassigning them to the surviving record.

Zero-speculation policy: only merges records where normalized names
are identical. Does NOT touch fuzzy matches.
"""

import os
import re
import sqlite3
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")


def normalize_name(name):
    """Normalize: lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r'[.,;:()\[\]"\'!?]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name


def merge_persons(conn, keep_id, remove_id, keep_name, remove_name):
    """
    Merge remove_id into keep_id:
    - Reassign all relationships from remove_id to keep_id
    - Reassign all person_photos from remove_id to keep_id
    - Reassign entity_matches from remove_id to keep_id
    - Copy any non-null fields from remove to keep (if keep is null)
    - Delete the duplicate person record
    """
    cursor = conn.cursor()

    # 1. Merge metadata: fill in any null fields on keep from remove
    cursor.execute("SELECT birth_info, death_info, notes, dataset_source FROM persons WHERE person_id = ?", (remove_id,))
    remove_data = cursor.fetchone()
    if remove_data:
        cursor.execute("SELECT birth_info, death_info, notes FROM persons WHERE person_id = ?", (keep_id,))
        keep_data = cursor.fetchone()
        updates = []
        params = []
        if not keep_data[0] and remove_data[0]:
            updates.append("birth_info = ?")
            params.append(remove_data[0])
        if not keep_data[1] and remove_data[1]:
            updates.append("death_info = ?")
            params.append(remove_data[1])
        if not keep_data[2] and remove_data[2]:
            updates.append("notes = COALESCE(notes, '') || ' | ' || ?")
            params.append(remove_data[2])
        if updates:
            params.append(keep_id)
            cursor.execute(f"UPDATE persons SET {', '.join(updates)} WHERE person_id = ?", params)

    # 2. Reassign relationships
    cursor.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (keep_id, remove_id))
    cursor.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (keep_id, remove_id))

    # Remove self-referencing relationships that may have been created
    cursor.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

    # Remove duplicate relationships (same pair + type)
    cursor.execute("""
        DELETE FROM relationships WHERE id NOT IN (
            SELECT MIN(id) FROM relationships
            GROUP BY person_a_id, person_b_id, relationship_type
        )
    """)

    # 3. Reassign person_photos
    cursor.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (keep_id, remove_id))
    cursor.execute("DELETE FROM person_photos WHERE person_id = ?", (remove_id,))

    # 4. Reassign entity_matches
    cursor.execute("UPDATE OR IGNORE entity_matches SET person_id_jackson = ? WHERE person_id_jackson = ?", (keep_id, remove_id))
    cursor.execute("UPDATE OR IGNORE entity_matches SET person_id_moors = ? WHERE person_id_moors = ?", (keep_id, remove_id))

    # 5. Delete the duplicate person
    cursor.execute("DELETE FROM persons WHERE person_id = ?", (remove_id,))

    # 6. Mark the audit flag as resolved
    cursor.execute("""
        UPDATE audit_flags
        SET resolution = ?, resolved_at = datetime('now'), auto_resolved = 1
        WHERE category = 'duplicate_exact'
          AND ((person_id = ? AND person_id_secondary = ?) OR (person_id = ? AND person_id_secondary = ?))
          AND resolved_at IS NULL
    """, (f"Merged '{remove_name}' (ID {remove_id}) into '{keep_name}' (ID {keep_id})",
          keep_id, remove_id, remove_id, keep_id))


def is_actual_person(name):
    """Filter out non-person entities that shouldn't be merged."""
    non_person_patterns = [
        r"^(see\s+)?family\s+(history|report|bible)",
        r"^(census|bible|probate|marriage|obituary)\s+records?",
        r"^\d{4}\s+(census|de\s+federal)",
        r"^(his|her|the)\s+(will|family)",
        r"^(he|she)\s+(was|is)\s+the",
        r"^(linked\s+to|see\s+also|index)",
    ]
    name_lower = name.lower().strip()
    for pattern in non_person_patterns:
        if re.match(pattern, name_lower):
            return False
    if len(name_lower) < 3:
        return False
    return True


def run_auto_merge():
    print("=" * 60)
    print("  AUTO-MERGE EXACT DUPLICATE PERSONS")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    # Disable FK enforcement — we handle all reassignments manually
    conn.execute("PRAGMA foreign_keys=OFF")
    cursor = conn.cursor()

    # Build normalization groups
    cursor.execute("SELECT person_id, name, dataset_source FROM persons")
    persons = cursor.fetchall()

    norm_map = defaultdict(list)
    for pid, name, source in persons:
        nname = normalize_name(name)
        if len(nname) >= 3:
            norm_map[nname].append((pid, name, source))

    merged_count = 0
    skipped_non_person = 0

    for nname, entries in sorted(norm_map.items()):
        if len(entries) <= 1:
            continue

        # Skip non-person entities
        if not is_actual_person(entries[0][1]):
            skipped_non_person += 1
            continue

        # Keep the record with the lowest ID (original) as the canonical one
        # Prefer records that have more metadata
        primary = entries[0]
        for duplicate in entries[1:]:
            keep_id, keep_name, keep_src = primary
            remove_id, remove_name, remove_src = duplicate

            print(f"  🔀 Merging: '{remove_name}' (ID {remove_id}, {remove_src}) → '{keep_name}' (ID {keep_id}, {keep_src})")
            merge_persons(conn, keep_id, remove_id, keep_name, remove_name)
            merged_count += 1

    conn.commit()

    # Report final counts
    cursor.execute("SELECT COUNT(*) FROM persons")
    total_persons = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM relationships")
    total_rels = cursor.fetchone()[0]

    print(f"\n{'=' * 60}")
    print(f"  MERGE COMPLETE")
    print(f"  Records merged: {merged_count}")
    print(f"  Non-person entities skipped: {skipped_non_person}")
    print(f"  Remaining persons: {total_persons}")
    print(f"  Remaining relationships: {total_rels}")
    print(f"{'=' * 60}")

    conn.close()


if __name__ == "__main__":
    run_auto_merge()
