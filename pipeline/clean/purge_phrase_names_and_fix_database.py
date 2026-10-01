#!/usr/bin/env python3
"""
Purge Phrase Names & Sentence Fragments (purge_phrase_names_and_fix_database.py)
================================================================================
Comprehensive database sanitizer that:
1. Deletes non-person phrases, sentence fragments, article titles, and site headlines from `persons`.
2. Extracts valid individuals from compound names (e.g. "Caleb and Rachel Dean" -> Caleb Dean, Rachel Dean).
3. Strips trailing verb/pronoun fragments (e.g. "Annanias Jackson was" -> "Annanias Jackson").
4. Cleans all relationship ties and photo junction links.
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

ARTICLE_OR_FRAGMENT_KEYWORDS = [
    "archive", "census", "history", "will of", "report", "voyage", "sovereignty", "atlas",
    "cemetery", "bible", "disaster", "powwow", "delaware", "county", "hundred", "view",
    "map", "story", "list", "article", "book", "site", "page", "index", "search", "email",
    "copyright", "wayback", "wikipedia", "district", "legislature", "community", "tribe",
    "tradition", "dissertation", "interview", "gouldtown", "forgotten", "essay", "essays",
    "one-drop", "blood", "quantum", "classification", "underground", "origins", "monograph",
    "record", "records", "file", "files", "court", "petition", "table", "contents", "guide",
    "menu", "intro", "remarks", "contributed by", "contribution", "comments", "wedlock",
    "perceptions", "relic", "racism", "rule", "crucible", "identity", "interpretation",
    "public", "great-grandmother", "multiracial", "american", "indians", "indian", "moors",
    "moor", "nanticoke", "lenape", "remnant", "races", "race", "change of race", "self-id",
    "self-identification", "patriots", "treaty", "treaties", "speech", "isolates", "island",
    "islands", "overview", "whats new", "introduction", "who we are", "intertribal", "union",
    "indentures", "indenture", "apprenticeship", "apprenticeships", "ministry", "challenges",
    "cedar chest", "bay window", "boughs", "norway maple", "trees", "last stand", "movie actor",
    "digging into", "past", "archaeology", "burial", "burials", "burial plot", "burial grounds",
    "state news", "courier-post", "artifacts", "escape", "gang", "heathen", "club", "settlement",
    "underground rr", "journal", "public", "nabb", "lower eastern shore", "voyage to", "killed in",
    "viet nam", "sign up", "separate schools", "died w/o heirs", "orphans court", "case file",
    "color removed", "no parents listed", "outside site", "site removed", "farm directory",
    "tombstones", "scroll down", "inventory", "appraisal", "estate", "legibility", "june -",
    "july -", "herman (harmon)", "died (no date)", "married into", "having married", "their",
    "was bornd", "was born", "was died", "was married"
]

def is_non_person_phrase(name):
    nl = name.lower().strip()
    if not nl or len(nl) < 3:
        return True

    # Standalone pronouns or small phrase fragments
    if nl in ['their', 'he', 'she', 'his', 'her', 'who', 'he was', 'she was', 'their live', 'was', 'were', 'who was', 'who married', 'who died']:
        return True

    # Check for keyword matches
    for kw in ARTICLE_OR_FRAGMENT_KEYWORDS:
        if kw in nl:
            return True

    # Starts or ends with invalid trailing words
    if re.search(r'\b(was|were|their|spent|having|into|by|about|from|the|with)\s*$', nl):
        return True

    # Pure date or year strings
    if re.match(r'^\d{4}.*$', nl) or re.match(r'^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec).*$', nl):
        return True

    return False

def clean_person_name_string(name):
    if not name:
        return ""
    
    n = name.strip()

    # Strip trailing phrase fragments e.g. "Annanias Jackson was" -> "Annanias Jackson"
    n = re.sub(r'\s+(was|were|spent\s+their|lived|died|married|born|bornd|having|into).*$', '', n, flags=re.IGNORECASE).strip()

    # Remove quotes
    n = n.replace('"', '').replace("'", "").strip()

    # If sentence fragment remains
    if is_non_person_phrase(n):
        return ""

    return n

def run_purge():
    print("=== Running Comprehensive Phrase Name Purge & Database Fix ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    c.execute("SELECT person_id, name, birth_info, death_info FROM persons")
    rows = c.fetchall()

    deleted_count = 0
    cleaned_count = 0
    split_count = 0

    for pid, raw_name, b_info, d_info in rows:
        if is_non_person_phrase(raw_name):
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            deleted_count += 1
            continue

        cleaned = clean_person_name_string(raw_name)

        if not cleaned:
            c.execute("DELETE FROM relationships WHERE person_a_id = ? OR person_b_id = ?", (pid, pid))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))
            c.execute("DELETE FROM audit_flags WHERE person_id = ? OR person_id_secondary = ?", (pid, pid))
            c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
            deleted_count += 1
            continue

        # Handle compound names like "Caleb and Rachel Dean" -> Caleb Dean & Rachel Dean
        and_match = re.search(r'^([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)$', cleaned)
        if and_match:
            fn1, fn2, sn = and_match.groups()
            name1 = f"{fn1} {sn}"
            name2 = f"{fn2} {sn}"

            c.execute("SELECT person_id FROM persons WHERE name = ?", (name1,))
            e1 = c.fetchone()
            if not e1:
                c.execute("UPDATE OR IGNORE persons SET name = ? WHERE person_id = ?", (name1, pid))
            else:
                c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
                deleted_count += 1

            c.execute("SELECT person_id FROM persons WHERE name = ?", (name2,))
            if not c.fetchone():
                c.execute("INSERT OR IGNORE INTO persons (name, dataset_source) VALUES (?, ?)", (name2, "mitsawokett_delaware"))

            split_count += 1
            continue

        if cleaned != raw_name:
            # Check if cleaned name already exists
            c.execute("SELECT person_id FROM persons WHERE name = ? AND person_id != ?", (cleaned, pid))
            ex = c.fetchone()
            if ex:
                target_id = ex[0]
                c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (target_id, pid))
                c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (target_id, pid))
                c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")

                c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (target_id, pid))
                c.execute("DELETE FROM person_photos WHERE person_id = ?", (pid,))

                c.execute("UPDATE OR IGNORE person_obituaries SET person_id = ? WHERE person_id = ?", (target_id, pid))
                c.execute("DELETE FROM person_obituaries WHERE person_id = ?", (pid,))

                c.execute("DELETE FROM persons WHERE person_id = ?", (pid,))
                deleted_count += 1
            else:
                c.execute("UPDATE OR IGNORE persons SET name = ? WHERE person_id = ?", (cleaned, pid))
                cleaned_count += 1

    conn.commit()
    conn.close()

    print(f"\n==================================================")
    print(f"Phrase Name Purge Complete.")
    print(f"Non-Person Phrases & Sentence Fragments Deleted: {deleted_count}")
    print(f"Person Names Cleaned: {cleaned_count}")
    print(f"Compound Names Split: {split_count}")
    print(f"==================================================")

if __name__ == "__main__":
    run_purge()
