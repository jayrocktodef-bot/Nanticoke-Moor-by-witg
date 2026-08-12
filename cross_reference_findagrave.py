import sqlite3
import urllib.request
import urllib.parse
import re
import json
import time
from bs4 import BeautifulSoup

DB_PATH = "preservation_output/genealogy_preservation.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_candidates():
    """Fetch Delmarva historical profiles missing exact birth/death/cemetery details."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT person_id, name, birth_info, death_info, notes
        FROM persons
        WHERE (birth_info IS NULL OR birth_info = '' OR birth_info LIKE '%xxxx%' OR death_info IS NULL OR death_info = '' OR death_info LIKE '%xxxx%')
          AND (notes NOT LIKE '%FindAGrave%')
        LIMIT 20
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def search_findagrave(first_name, last_name, state_id=8): # state_id 8 = Delaware
    """Construct search URL and fetch search results."""
    params = {
        'firstname': first_name,
        'lastname': last_name,
        'stateid': state_id,
        'cemeteryname': ''
    }
    url = f"https://www.findagrave.com/memorial/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            return html
    except Exception as e:
        print(f"Error searching FindAGrave for {first_name} {last_name}: {e}")
        return None

def parse_memorial_page(url):
    """Parse direct memorial page for structured tombstone/burial data."""
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            
            birth_match = re.search(r'itemprop="birthDate">(.*?)<', html)
            death_match = re.search(r'itemprop="deathDate">(.*?)<', html)
            cemetery_match = re.search(r'itemprop="name">(.*?)</span>', html)
            
            return {
                'birth': birth_match.group(1).strip() if birth_match else None,
                'death': death_match.group(1).strip() if death_match else None,
                'cemetery': cemetery_match.group(1).strip() if cemetery_match else None,
                'url': url
            }
    except Exception as e:
        print(f"Error reading memorial page {url}: {e}")
        return None

def run_cross_reference():
    candidates = get_candidates()
    print(f"Found {len(candidates)} candidate profiles to cross-reference.")
    
    for pid, name, birth, death, notes in candidates:
        name_clean = name.strip()
        parts = name_clean.split()
        if len(parts) < 2:
            continue
            
        first_name = parts[0]
        last_name = parts[-1]
        
        print(f"\n[Searching] #{pid}: {first_name} {last_name}...")        
        html = search_findagrave(first_name, last_name)
        if not html:
            continue
            
        # Extract direct memorial links
        memorial_links = re.findall(r'href="(/memorial/\d+/[^"]+)"', html)
        if memorial_links:
            top_link = "https://www.findagrave.com" + memorial_links[0]
            print(f"  ✓ Found potential match: {top_link}")
            
            # Fetch memorial details
            details = parse_memorial_page(top_link)
            if details:
                print(f"    - Extracted Birth: {details['birth']}")
                print(f"    - Extracted Death: {details['death']}")
                print(f"    - Extracted Cemetery: {details['cemetery']}")
                
                # Update SQLite database cleanly
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                new_notes = (notes or '') + f" | Verified via FindAGrave Memorial: {top_link}"
                c.execute('''
                    UPDATE persons 
                    SET birth_info = COALESCE(NULLIF(?, ''), birth_info),
                        death_info = COALESCE(NULLIF(?, ''), death_info),
                        notes = ?
                    WHERE person_id = ?
                ''', (details['birth'], details['death'], new_notes, pid))
                conn.commit()
                conn.close()
        else:
            print("  x No direct memorial matches found.")
            
        # Polite delay to prevent rate limits
        time.sleep(2)

if __name__ == "__main__":
    run_cross_reference()
