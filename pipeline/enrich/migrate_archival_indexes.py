#!/usr/bin/env python3
"""
Step 1: Relational Schema & Query Performance Index Migration
Adds explicit B-Tree indexes for all foreign keys and high-frequency join columns in genealogy_preservation.db.
"""

import sqlite3
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_preservation.db")

INDEXES_TO_CREATE = [
    # Facts & Citations
    ("idx_facts_person", "facts", "person_id"),
    ("idx_facts_type", "facts", "fact_type"),
    ("idx_citations_fact", "citations", "fact_id"),
    ("idx_citations_source", "citations", "source_id"),
    
    # Kinship & Relationships
    ("idx_relationships_person_a", "relationships", "person_a_id"),
    ("idx_relationships_person_b", "relationships", "person_b_id"),
    ("idx_relationships_type", "relationships", "relationship_type"),
    
    # Media & Biometrics
    ("idx_person_photos_person", "person_photos", "person_id"),
    ("idx_person_photos_photo", "person_photos", "photo_id"),
    ("idx_face_embeddings_person", "face_embeddings", "person_id"),
    ("idx_face_embeddings_photo", "face_embeddings", "photo_id"),
    ("idx_face_embeddings_engine", "face_embeddings", "engine"),
    
    # Documents, Obituaries & Surnames
    ("idx_person_obituaries_person", "person_obituaries", "person_id"),
    ("idx_person_obituaries_obit", "person_obituaries", "obituary_id"),
    ("idx_document_records_photo", "document_records", "photo_id"),
    ("idx_persons_name", "persons", "name"),
    ("idx_persons_surname", "persons", "married_last_name"),
    ("idx_persons_maiden", "persons", "maiden_name"),
    ("idx_photo_surnames_photo", "photo_surnames", "photo_id"),
    ("idx_photo_surnames_surname", "photo_surnames", "surname")
]

def benchmark_sample_queries(cursor):
    """Run EXPLAIN QUERY PLAN on common queries to verify index usage."""
    test_queries = [
        ("Person Facts Join", "EXPLAIN QUERY PLAN SELECT f.fact_type, f.value_string, c.evidence_text FROM facts f LEFT JOIN citations c ON f.fact_id = c.fact_id WHERE f.person_id = 8814"),
        ("Kinship Edges Traversal", "EXPLAIN QUERY PLAN SELECT r.*, p.name FROM relationships r JOIN persons p ON r.person_b_id = p.person_id WHERE r.person_a_id = 8814"),
        ("Face Embeddings Lookup", "EXPLAIN QUERY PLAN SELECT * FROM face_embeddings WHERE person_id = 8814"),
        ("Person Photo Junction", "EXPLAIN QUERY PLAN SELECT ph.* FROM person_photos pp JOIN unified_photo_catalog ph ON pp.photo_id = ph.photo_id WHERE pp.person_id = 8814"),
        ("Surname Query", "EXPLAIN QUERY PLAN SELECT person_id, name FROM persons WHERE married_last_name = 'Davis'")
    ]
    plans = []
    for name, q in test_queries:
        res = cursor.execute(q).fetchall()
        plan_desc = "; ".join([str(row[3]) for row in res])
        plans.append((name, plan_desc))
    return plans

def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    print(f"Connecting to database: {DB_PATH}")
    print("--- Before Index Migration Query Plans ---")
    plans_before = benchmark_sample_queries(cur)
    for name, plan in plans_before:
        print(f"  {name}: {plan}")

    start_time = time.time()
    created_count = 0
    for idx_name, table, cols in INDEXES_TO_CREATE:
        sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({cols});"
        cur.execute(sql)
        created_count += 1
        print(f"Verified/Created index: {idx_name} ON {table}({cols})")

    # Run ANALYZE to update SQLite query planner statistics
    print("Running PRAGMA optimize / ANALYZE...")
    cur.execute("ANALYZE")
    conn.commit()
    elapsed = time.time() - start_time

    print(f"\nSuccessfully migrated {created_count} indexes in {elapsed:.3f}s")
    print("--- After Index Migration Query Plans ---")
    plans_after = benchmark_sample_queries(cur)
    for name, plan in plans_after:
        print(f"  {name}: {plan}")

    # Check database integrity
    integrity = cur.execute("PRAGMA quick_check").fetchone()[0]
    print(f"\nDatabase Quick Check: {integrity}")

    conn.close()

if __name__ == "__main__":
    main()
