#!/usr/bin/env python3
"""
Obituary Scraper & Relational Linker (scrape_obituaries.py)
==========================================================
Scrapes, parses, and catalogers obituaries and death notices from
https://nativeamericansofdelawarestate.com/Obituaries%20added%202016-04-03.htm

Features:
- Crawls the 268KB primary obituary page containing 350+ full transcribed obituaries
- Extracts deceased names, birth/death years, age, cemetery locations
- Links deceased & surviving kinsmen to the unified persons table
"""

import os
import re
import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

TARGET_URL = "https://nativeamericansofdelawarestate.com/Obituaries%20added%202016-04-03.htm"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 MitsawokettObituaryScraper/2.0"})

def init_obituary_schema(conn):
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS person_obituaries")
    c.execute("DROP TABLE IF EXISTS obituaries")
    c.execute("""
        CREATE TABLE obituaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deceased_name TEXT NOT NULL,
            maiden_name TEXT,
            married_surname TEXT,
            birth_date TEXT,
            death_date TEXT,
            age TEXT,
            cemetery_location TEXT,
            surviving_kin TEXT,
            full_text TEXT,
            clean_html TEXT,
            source_url TEXT,
            dataset_source TEXT DEFAULT 'mitsawokett_obits'
        )
    """)
    c.execute("""
        CREATE TABLE person_obituaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            obituary_id INTEGER,
            role TEXT DEFAULT 'deceased',
            confidence_score REAL DEFAULT 1.0,
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            FOREIGN KEY(obituary_id) REFERENCES obituaries(id)
        )
    """)
    conn.commit()

def parse_date_and_age(text):
    birth = ""
    death = ""
    age = ""
    
    age_m = re.search(r'\baged?\s+(\d{1,3})\b|\b(\d{1,3})\s+years?\s+old\b|\b,?\s*(\d{2,3}),?\s+of\b', text, re.IGNORECASE)
    if age_m:
        age = age_m.group(1) or age_m.group(2) or age_m.group(3)
        
    years = re.findall(r'\b(1[789]\d{2}|20[012]\d)\b', text)
    if len(years) >= 2:
        birth = years[0]
        death = years[1]
    elif len(years) == 1:
        death = years[0]
        
    return birth, death, age

def extract_deceased_name(text):
    # Match patterns like "Marguerite J. Brown, 88, of Quinton" or "John H. Durham died on"
    m = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z\'-]+)(?:,?\s+\d{1,3}|,?\s+died|,?\s+passed)', text)
    if m:
        return m.group(1).strip()
    
    # Fallback to first 5 words
    words = text.split()[:4]
    return " ".join(words).strip(",. ")

def scrape_obituaries():
    print("=== Starting Mitsawokett Obituary Scraper V2 ===", flush=True)
    
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    init_obituary_schema(conn)
    c = conn.cursor()
    
    print(f"Fetching primary obituaries archive: {TARGET_URL}", flush=True)
    r = session.get(TARGET_URL, timeout=30)
    r.encoding = r.apparent_encoding or "windows-1252"
    soup = BeautifulSoup(r.text, "html.parser")
    
    paragraphs = soup.find_all(['p', 'div', 'blockquote', 'tr'])
    obits_collected = []
    
    for p in paragraphs:
        txt = p.get_text(separator=" ", strip=True)
        if len(txt) < 70:
            continue
            
        txt_lower = txt.lower()
        if any(kw in txt_lower for kw in ['died', 'passed away', 'funeral', 'interment', 'burial', 'services will be held', 'survived by']):
            deceased_name = extract_deceased_name(txt)
            birth, death, age = parse_date_and_age(txt)
            
            # Cemetery location
            cemetery = ""
            cem_m = re.search(r'(?:cemetery|cem\.|memorial park|burying ground)[^,.]*', txt, re.IGNORECASE)
            if cem_m:
                cemetery = cem_m.group(0).strip()
                
            obits_collected.append((deceased_name, "", "", birth, death, age, cemetery, "", txt, str(p), TARGET_URL, 'mitsawokett_obits'))

    print(f"Parsed {len(obits_collected)} full obituaries from archive.", flush=True)
    
    c.executemany("""
        INSERT INTO obituaries
        (deceased_name, maiden_name, married_surname, birth_date, death_date, age, cemetery_location, surviving_kin, full_text, clean_html, source_url, dataset_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, obits_collected)
    conn.commit()
    
    # Link obituaries to persons table
    c.execute("SELECT id, deceased_name, full_text FROM obituaries")
    obits = c.fetchall()
    
    c.execute("SELECT person_id, name FROM persons")
    persons = [(p[0], p[1].lower().strip()) for p in c.fetchall() if p[1] and len(p[1]) > 3]
    
    links = 0
    for obit_id, name, full_text in obits:
        name_lower = name.lower()
        for pid, pname in persons:
            if pname in name_lower or (full_text and pname in full_text.lower()):
                score = SequenceMatcher(None, pname, name_lower).ratio()
                c.execute("""
                    INSERT OR IGNORE INTO person_obituaries (person_id, obituary_id, confidence_score)
                    VALUES (?, ?, ?)
                """, (pid, obit_id, score))
                links += 1

    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM obituaries")
    total_obits = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM person_obituaries")
    total_links = c.fetchone()[0]
    
    conn.close()
    print(f"=== Obituary Preservation Complete! Saved {total_obits} obituaries and {total_links} person-obituary links. ===", flush=True)

if __name__ == "__main__":
    scrape_obituaries()
