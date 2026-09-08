def merge_persons(primary_id, duplicate_id, c):
    """
    Safely merges duplicate_id into primary_id across all foreign key tables.
    Handles unique constraints gracefully by deleting duplicate edges before updating.
    """
    print(f"Merging duplicate #{duplicate_id} into primary #{primary_id}...")

    # 1. Update relationships
    # If primary already has an edge to person_b with the same relationship_type, delete duplicate's edge
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

    # If primary already has an edge from person_a with the same relationship_type, delete duplicate's edge
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

    # Now safely update the remaining relationships
    c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (primary_id, duplicate_id))
    c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (primary_id, duplicate_id))
    # Remove self-loops
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

    # 6. Merge birth_info, death_info, notes if missing on primary
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
            new_n = f"{new_n} | Merged from duplicate #{duplicate_id}: {dup_n}".strip(" |")
        c.execute("UPDATE persons SET birth_info = ?, death_info = ?, notes = ? WHERE person_id = ?",
                  (new_b, new_d, new_n, primary_id))

    # 7. Delete duplicate record from persons
    c.execute("DELETE FROM persons WHERE person_id = ?", (duplicate_id,))
