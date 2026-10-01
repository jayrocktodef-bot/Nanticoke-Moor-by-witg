#!/usr/bin/env python3
import os
import re
import sqlite3
import urllib.parse
import time
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
MITSAWOKETT_PHOTOS_DIR = os.path.join(OUTPUT_DIR, "assets", "mitsawokett_photos")

os.makedirs(MITSAWOKETT_PHOTOS_DIR, exist_ok=True)

TARGET_INDEXES = [
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexA-C.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexD.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexE-L.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexM.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexN-R.htm",
    "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexS-Z.htm"
]

IGNORE_IMAGES = [
    "ind-footer.gif", "email.fw.png", "email.jpg", "bg.jpg", 
    "background.jpg", "backgr.jpg", "back.jpg", "logo.jpg", "logo.gif", "email1.jpg",
    "line.gif", "redrule.gif", "sorry.gif"
]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 MitsawokettPhotoScraperV2/1.0"})

def link_photos_to_persons(conn):
    print("Linking photos to persons via fuzzy matching...", flush=True)
    c = conn.cursor()
    c.execute("SELECT person_id, name FROM persons")
    persons = c.fetchall()
    person_list = [(pid, (name or "").lower().strip()) for pid, name in persons if name and len(name.strip()) > 3]
        
    c.execute("SELECT photo_id, subject_names FROM photo_catalog WHERE dataset_source = 'mitsawokett'")
    photos = c.fetchall()
    
    links_created = 0
    for photo_id, subject_names in photos:
        if not subject_names or len(subject_names.strip()) < 3:
            continue
        subj_lower = subject_names.lower().strip()
        best_match_id = None
        best_score = 0
        
        for pid, person_name in person_list:
            score = SequenceMatcher(None, subj_lower, person_name).ratio()
            if score > best_score and score >= 0.75:
                best_score = score
                best_match_id = pid
                
        if best_match_id is not None:
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, ?, ?)", 
                      (best_match_id, photo_id, best_score))
            links_created += 1
            
    conn.commit()
    print(f"Created {links_created} person_photo links.", flush=True)

def scrape_mitsawokett_photos():
    print("=== Starting Mitsawokett Photo Archive Scraper V2 ===", flush=True)
    
    pages_to_visit = []
    visited_pages = set()
    
    # 1. Discover detail links from all 6 indexes
    for idx_url in TARGET_INDEXES:
        print(f"[Photo Index] Crawling: {idx_url}", flush=True)
        try:
            r = session.get(idx_url, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception as e:
            print(f"Failed to fetch index {idx_url}: {e}", flush=True)
            continue
            
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href or href.startswith("#") or href.startswith("mailto:"): continue
            full_url = urllib.parse.urljoin(idx_url, href)
            
            if ("mitsawokett" in full_url.lower() or "delawarestate.com" in full_url.lower()) and full_url.endswith((".htm", ".html")) and "Index" not in full_url:
                b_tag = a.find("b")
                subject_name = b_tag.get_text(strip=True) if b_tag else a.get_text(strip=True)
                
                married_surname = ""
                nxt = a.next_sibling
                while nxt and isinstance(nxt, str):
                    text_content = nxt.strip()
                    if "(" in text_content and ")" in text_content:
                        match = re.search(r'\(([^)]+)\)', text_content)
                        if match:
                            married_surname = match.group(1).strip()
                            break
                    nxt = nxt.next_sibling
                    
                # Clean subject name and extract maiden surname
                clean_subj = re.sub(r'\s+\d+$', '', subject_name)
                words = [w for w in clean_subj.split() if w.isalpha() and len(w) > 1]
                maiden_name = words[-1] if words else ""
                
                # Fallback to URL filename if maiden_name is missing or invalid
                if not maiden_name:
                    fn = os.path.basename(urllib.parse.urlparse(full_url).path)
                    m_fn = re.match(r'^([A-Z][a-z]+)', urllib.parse.unquote(fn))
                    if m_fn and m_fn.group(1).lower() not in ('index', 'photo', 'whare', 'these'):
                        maiden_name = m_fn.group(1)

                pages_to_visit.append((subject_name, maiden_name, married_surname, full_url))
                
    print(f"Discovered {len(pages_to_visit)} initial detail pages from indexes.", flush=True)
    
    photos_downloaded = 0
    downloaded_urls = set()
    catalog_rows = []
    
    # 2. Crawl detail pages and collect image records in memory
    while pages_to_visit:
        subject_name, maiden_name, married_surname, page_url = pages_to_visit.pop(0)
        
        if page_url in visited_pages: continue
        visited_pages.add(page_url)
        
        try:
            r = session.get(page_url, timeout=15)
            if r.status_code != 200: continue
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception:
            continue
            
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        page_text = soup.get_text(separator=" ", strip=True)
        
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src: continue
            
            if any(ign in src.lower() for ign in IGNORE_IMAGES) or "email" in src.lower() or "button" in src.lower() or "line" in src.lower() or "goto" in src.lower():
                continue
                
            img_url = urllib.parse.urljoin(page_url, src)
            if img_url in downloaded_urls: continue
            downloaded_urls.add(img_url)
            
            alt = img.get("alt", "").strip()
            caption = f"{alt} | {title} | {page_text[:150]}...".strip(" | ")
            year_match = re.search(r"\b(18\d\d|19\d\d|20\d\d)\b", caption + " " + page_text)
            approx_year = year_match.group(1) if year_match else ""
            
            orig_filename = os.path.basename(urllib.parse.urlparse(img_url).path)
            orig_filename = urllib.parse.unquote(orig_filename)
            local_filename = f"mitsawokett_{orig_filename}"
            local_file_path = os.path.join(MITSAWOKETT_PHOTOS_DIR, local_filename)
            rel_db_path = f"assets/mitsawokett_photos/{local_filename}"
            
            if not os.path.exists(local_file_path):
                try:
                    img_res = session.get(img_url, timeout=15)
                    if img_res.status_code == 200:
                        with open(local_file_path, "wb") as f:
                            f.write(img_res.content)
                        photos_downloaded += 1
                except Exception as e:
                    print(f"  [Download Error] {img_url}: {e}", flush=True)
                    
            catalog_rows.append((caption, subject_name, maiden_name, married_surname, "Delaware / Delmarva", approx_year, rel_db_path, page_url, 'mitsawokett'))
            
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href: continue
            full_url = urllib.parse.urljoin(page_url, href)
            if ("mitsawokett" in full_url.lower() or "delawarestate.com" in full_url.lower()) and full_url.endswith((".htm", ".html")) and "Index" not in full_url:
                if full_url not in visited_pages:
                    pages_to_visit.append((subject_name, maiden_name, married_surname, full_url))
                    
    print(f"Crawled {len(visited_pages)} detail pages.", flush=True)
    print(f"Collected {len(catalog_rows)} photo records.", flush=True)
    print(f"Downloaded {photos_downloaded} new image files.", flush=True)
    
    # 3. Insert all records in one fast transaction to avoid locks
    print("Writing catalog records to database...", flush=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS photo_catalog (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_or_caption TEXT,
            subject_names TEXT,
            maiden_name TEXT,
            married_surname TEXT,
            location TEXT,
            approximate_year TEXT,
            local_image_path TEXT,
            source_url TEXT,
            dataset_source TEXT DEFAULT 'mitsawokett'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS person_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            photo_id INTEGER,
            confidence_score REAL DEFAULT 1.0,
            FOREIGN KEY(person_id) REFERENCES persons(person_id),
            FOREIGN KEY(photo_id) REFERENCES photo_catalog(photo_id)
        )
    """)
    
    c.execute("DELETE FROM person_photos")
    c.execute("DELETE FROM photo_catalog")
    
    c.executemany("""
        INSERT INTO photo_catalog 
        (title_or_caption, subject_names, maiden_name, married_surname, location, approximate_year, local_image_path, source_url, dataset_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, catalog_rows)
    conn.commit()
    
    link_photos_to_persons(conn)
    
    c.execute("SELECT maiden_name, COUNT(*) FROM photo_catalog GROUP BY maiden_name ORDER BY COUNT(*) DESC LIMIT 15")
    print("\nTop Surnames in Catalog:", flush=True)
    for name, cnt in c.fetchall():
        print(f"  {name}: {cnt}", flush=True)
        
    conn.close()
    print("=== Scraping & Cataloging Complete ===", flush=True)

if __name__ == "__main__":
    try:
        scrape_mitsawokett_photos()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
