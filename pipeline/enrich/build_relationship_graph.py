#!/usr/bin/env python3
"""
Module 3: Relationship Graph Extractor (build_relationship_graph.py)
==================================================================
Extends genealogy_preservation.db with persons and relationships tables.
Parses inline hyperlinked lineage text, genealogical records, and parent/child/spouse
indicators to build an explicit genealogical relationship graph.
"""

import os
import re
import sqlite3
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

def init_graph_schema(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            person_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            source_page TEXT,
            birth_info TEXT,
            death_info TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_a_id INTEGER,
            person_b_id INTEGER,
            relationship_type TEXT,
            evidence_text TEXT,
            FOREIGN KEY(person_a_id) REFERENCES persons(person_id),
            FOREIGN KEY(person_b_id) REFERENCES persons(person_id)
        )
    """)
    conn.commit()

def get_or_create_person(cursor, name: str, source_page: str, notes: str = "") -> int:
    name = name.strip()
    cursor.execute("SELECT person_id FROM persons WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    cursor.execute("""
        INSERT INTO persons (name, source_page, notes)
        VALUES (?, ?, ?)
    """, (name, source_page, notes))
    return cursor.lastrowid

def add_relationship(cursor, person_a_id: int, person_b_id: int, rel_type: str, evidence: str):
    cursor.execute("""
        INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
        VALUES (?, ?, ?, ?)
    """, (person_a_id, person_b_id, rel_type, evidence))

def parse_lineage_graph():
    print("=== [Module 3] Starting Relationship Graph Extractor ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    init_graph_schema(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT filename, clean_html, title FROM pages")
    pages = cursor.fetchall()

    rel_count = 0

    # Patterns for relationship parsing
    rel_patterns = [
        (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:was\s+)?married\s+(?:to\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "spouse"),
        (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:son|daughter)\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "child_of"),
        (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+were\s+married", "spouse"),
        (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+father\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "parent_of"),
        (r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+mother\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", "parent_of")
    ]

    for filename, clean_html, page_title in pages:
        if not clean_html:
            continue

        soup = BeautifulSoup(clean_html, "html.parser")
        
        # 1. Parse hyperlinked relative connections (<a> tags pointing to person profiles)
        links = soup.find_all("a")
        for link in links:
            text = link.get_text(strip=True)
            href = link.get("href", "")
            if text and len(text.split()) >= 2 and ("family" in href or ".htm" in href):
                person_id = get_or_create_person(cursor, text, filename, notes=f"Linked to {href}")

        # 2. Extract explicit relationships using text regex matching
        page_text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]

        for line in lines:
            for pattern, rel_type in rel_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    name_a, name_b = match[0].strip(), match[1].strip()
                    if len(name_a) > 3 and len(name_b) > 3:
                        p_a = get_or_create_person(cursor, name_a, filename)
                        p_b = get_or_create_person(cursor, name_b, filename)
                        add_relationship(cursor, p_a, p_b, rel_type, line[:200])
                        rel_count += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM persons")
    total_persons = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM relationships")
    total_rels = cursor.fetchone()[0]

    conn.close()
    print(f"=== [Module 3] Completed. Extracted {total_persons} persons and {total_rels} relationships. ===")

if __name__ == "__main__":
    parse_lineage_graph()
