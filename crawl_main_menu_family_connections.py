#!/usr/bin/env python3
"""
Crawl Main Menu Family Connections (crawl_main_menu_family_connections.py)
=======================================================================
Deep-crawls all historical family history pages, wills, probate records, Bibles,
apprenticeship indentures, and social security applications linked from MainMenu.html
on nativeamericansofdelawarestate.com, ingesting structured person & relationship data into genealogy_preservation.db.
"""

import os
import re
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

BASE_URL = "https://nativeamericansofdelawarestate.com/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

MAIN_MENU_PAGES = [
    "MainMenu.html",
    "Probate.htm",
    "George%20Durham%20Will%201844.htm",
    "Durham%20Joel%20Petition%201864.htm",
    "HarmonEmmanuelProbate.htm",
    "CorkPerry.htm",
    "ClarkThomas.htm",
    "HarmonEdwardRevWar.htm",
    "Consellor%20Lineage.htm",
    "Apprenticeships/WarrenWrightsChildren/Apprentice%20Indentures%20-%20Warren%20Wright%20family%201843.htm",
    "Apprenticeships/Samuel%20Loatman/Samuel%20Loatman%20Apprenticeship.htm",
    "Apprenticeships/Edward%20Concealer/Edward%20Concealer%20Apprenticeship.htm",
    "DurhamsOfKentCoDE.htm",
    "HughesPerry&CornMortar.htm",
    "Jonathan%20Pierce.htm",
    "Cheswold%20origins%20by%20Joann%20Sammons.htm",
    "Winnesoccum.htm",
    "IdentifiedIndians.htm",
    "LegislativeActs.htm",
    "Bible%20Records/Perkins-Adams-Morris-JacksonBible.htm",
    "Bible%20Records/EmilyCJohnsonWrightBible.htm",
    "Bible%20Records/GreenageJames&HarriettBible.htm",
    "Bible%20Records/Reed_Effie_Bible.htm",
    "Bible%20Records/MAYMIE_DURHAM_BIBLE.htm",
    "Bible%20Records/Ida_Carter_Webster_Bible.htm",
    "Bible%20Records/Carty-Carter-WyattFamilyBible/Carty-Carter-WyattFamilyBible.htm",
    "Bible%20Records/MunceJames&HesterBible.htm",
    "Bible%20Records/MunceJamesPurnellBible.htm",
    "SocialSecurityApplications.htm"
]

def clean_person_name(name):
    if not name: return ""
    name = re.sub(r'[\r\n\t]+', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # Strip relative clauses
    name = re.sub(r'\s+(who|whose|who was|who died|who married).*$', '', name, flags=re.IGNORECASE)
    # Fix flip-flopped names e.g. "Durham Joel" -> "Joel Durham"
    parts = name.split()
    if len(parts) == 2 and parts[0] in ["Durham", "Harmon", "Mosley", "Jackson", "Beckett", "Carney", "Coker", "Consellor", "Conselah", "Dean", "Loatman", "Sammons", "Wright"]:
        name = f"{parts[1]} {parts[0]}"
    return name

def crawl_main_menu():
    print("=== Crawling Main Menu Family Connections ===", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    total_persons_ingested = 0

    for page_rel in MAIN_MENU_PAGES:
        page_url = urljoin(BASE_URL, page_rel)
        filename = os.path.basename(page_rel)
        print(f"\nFetching: {page_url}...", flush=True)

        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"  ❌ Status {r.status_code} for {filename}", flush=True)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            text_content = soup.get_text()
            title = soup.title.string.strip() if soup.title and soup.title.string else filename

            # Store page HTML in pages table for document viewer
            c.execute("""
                INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (filename, title, str(soup.find('body') or soup), text_content, page_url))

            # Extract bold names, list items, and table cells containing family members
            raw_names = []
            for tag in soup.find_all(['b', 'strong', 'td', 'li', 'h3', 'h4']):
                txt = tag.get_text().strip()
                # Ignore non-person headers
                if len(txt) > 3 and len(txt) < 60 and not any(ign in txt.lower() for ign in ["copyright", "http", "click", "return", "table", "menu", "page", "index", "native", "tribe", "chapter"]):
                    raw_names.append(txt)

            for raw in raw_names:
                cleaned = clean_person_name(raw)
                if len(cleaned) > 4 and " " in cleaned:
                    # Check if exists
                    c.execute("SELECT person_id FROM persons WHERE name = ?", (cleaned,))
                    row = c.fetchone()
                    if not row:
                        c.execute("""
                            INSERT INTO persons (name, source_page, notes, dataset_source)
                            VALUES (?, ?, ?, ?)
                        """, (cleaned, filename, f"Ingested from preserved {filename} record", "mitsawokett_delaware"))
                        total_persons_ingested += 1

        except Exception as e:
            print(f"  ❌ Error fetching {filename}: {e}", flush=True)

    conn.commit()
    conn.close()

    print(f"\n==================================================")
    print(f"Main Menu Family Connections Crawl Complete.")
    print(f"New Persons Ingested: {total_persons_ingested}")
    print(f"==================================================")

if __name__ == "__main__":
    crawl_main_menu()
