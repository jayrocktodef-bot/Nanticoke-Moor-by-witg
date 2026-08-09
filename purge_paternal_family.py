import sqlite3

DB_PATH = 'preservation_output/genealogy_preservation.db'

def purge():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    paternal_surnames = [
        'Bush', 'Anderson', 'Brummel', 'Brummell', 'Brown', 'Braham', 'Branham',
        'Carmean', 'Ingram', 'Turner', 'Faver', 'Favors', 'Favor', 'Rawlings',
        'Wynne', 'Hood', 'Sherrer', 'Bacon', 'Frame', 'Cordrey', 'Lockwood', 'Wymbs', 'Cannon'
    ]

    conditions = ' OR '.join(['name LIKE ?' for _ in paternal_surnames])
    params = [f'%{s}%' for s in paternal_surnames]

    # Get IDs of persons to purge
    c.execute(f'SELECT person_id, name FROM persons WHERE {conditions}', params)
    purge_targets = c.fetchall()
    purge_ids = set([r[0] for r in purge_targets])

    print(f"Purging {len(purge_ids)} paternal persons from database...")

    if purge_ids:
        placeholders = ','.join('?' for _ in purge_ids)
        id_list = list(purge_ids)

        # Delete relationships
        c.execute(f'DELETE FROM relationships WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})', id_list + id_list)
        rels_deleted = c.rowcount

        # Delete person_photos
        c.execute(f'DELETE FROM person_photos WHERE person_id IN ({placeholders})', id_list)
        photos_deleted = c.rowcount

        # Delete person_obituaries
        c.execute(f'DELETE FROM person_obituaries WHERE person_id IN ({placeholders})', id_list)
        obits_deleted = c.rowcount

        # Delete persons
        c.execute(f'DELETE FROM persons WHERE person_id IN ({placeholders})', id_list)
        persons_deleted = c.rowcount

        conn.commit()

        print("-------------------------------------------------------------------------")
        print("  PURGE SUMMARY REPORT:")
        print(f"  - Persons Removed:       {persons_deleted}")
        print(f"  - Kinship Links Removed: {rels_deleted}")
        print(f"  - Photo Links Removed:   {photos_deleted}")
        print(f"  - Obituary Links Removed: {obits_deleted}")
        print("-------------------------------------------------------------------------")

    c.execute("SELECT COUNT(*) FROM persons")
    remaining_persons = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    remaining_rels = c.fetchone()[0]

    print(f"  Preserved Delmarva Archive Status: {remaining_persons} persons, {remaining_rels} kinship ties")
    conn.close()

if __name__ == '__main__':
    purge()
