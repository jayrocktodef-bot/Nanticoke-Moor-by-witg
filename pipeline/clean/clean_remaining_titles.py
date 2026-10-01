#!/usr/bin/env python3
"""
Clean Remaining Titles (clean_remaining_titles.py)
==================================================
Cleans up remaining title fragments and extracts clean person names:
- "Daniel- husband of Caroline Durham" -> Daniel Durham
- "Descendants of Abner Coker" -> Abner Coker
- "Descendants of Israel Pierce" -> Israel Pierce
- Deletes "Ann and", "Bridget and", "Butchers and Franciscos", "Ancestry of the children..."
"""

import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

EXACT_DELETE = [
    "Ann and", "Bridget and", "Butchers and Franciscos",
    "Ancestry of the children of Effie James Carney", "Cheswold Home Town Of Senator Boggs",
    "Daughters Isabella and Araminta", "Andw Naudain Thos Denney", "Ashton PIERCE and William WRIGHT"
]

def run_clean():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()

    # 1. Exact deletes
    for d in EXACT_DELETE:
        c.execute("DELETE FROM persons WHERE name = ?", (d,))

    # 2. Pattern replacements
    c.execute("SELECT person_id, name FROM persons WHERE name LIKE 'Descendants of %' OR name LIKE '%- husband of %'")
    rows = c.fetchall()

    for pid, name in rows:
        if name.startswith("Descendants of "):
            clean = name.replace("Descendants of ", "").strip()
            c.execute("UPDATE OR IGNORE persons SET name = ? WHERE person_id = ?", (clean, pid))
        elif "- husband of " in name:
            fn = name.split("-")[0].strip()
            spouse_sn = name.split()[-1].strip()
            clean = f"{fn} {spouse_sn}"
            c.execute("UPDATE OR IGNORE persons SET name = ? WHERE person_id = ?", (clean, pid))

    conn.commit()
    conn.close()
    print("=== Remaining Titles Cleaned! ===")

if __name__ == "__main__":
    run_clean()
