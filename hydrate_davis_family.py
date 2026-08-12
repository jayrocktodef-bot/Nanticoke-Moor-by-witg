import sqlite3
import urllib.request
import urllib.parse
import re
import time
import os

DB_PATH = "preservation_output/genealogy_preservation.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_davis_candidates():
    """Fetch all Davis surname profiles missing birth/death/cemetery details."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT person_id, name, birth_info, death_info, notes
        FROM persons
        WHERE LOWER(name) LIKE '%davis%'
          AND (notes NOT LIKE '%FindAGrave%')
        ORDER BY person_id ASC
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def search_findagrave(first_name, last_name, state_id=8): # state_id 8 = Delaware
    """Search FindAGrave for memorial entries."""
    params = {
        'firstname': first_name,
        'lastname': last_name,
        'stateid': state_id,
    }
    url = f"https://www.findagrave.com/memorial/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            return html
    except Exception as e:
        print(f"  [HTTP Error] {e}")
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
        print(f"  [Parse Error] {e}")
        return None

def run_davis_hydration():
    candidates = get_davis_candidates()
    print(f"=========================================================================")
    print(f"  STARTING DAVIS FAMILY FINDAGRAVE HYDRATION ({len(candidates)} Candidate Profiles)")
    print(f"=========================================================================\n")
    
    updated_count = 0
    
    for pid, name, birth, death, notes in candidates:
        name_clean = name.strip()
        
        # Clean name artifacts
        name_clean = re.sub(r'^(niece|widow|nephew|granddaughters of|front--|children:)\s*', '', name_clean, flags=re.IGNORECASE)
        parts = name_clean.split()
        if len(parts) < 2:
            continue
            
        first_name = parts[0]
        last_name = 'Davis'
        
        print(f"[Hydrating] #{pid:<5} | {name_clean:<35}...")
        html = search_findagrave(first_name, last_name)
        if not html:
            time.sleep(1.5)
            continue
            
        memorial_links = re.findall(r'href="(/memorial/\d+/[^"]+)"', html)
        if memorial_links:
            top_link = "https://www.findagrave.com" + memorial_links[0]
            print(f"  ✓ Found Match: {top_link}")
            
            details = parse_memorial_page(top_link)
            if details:
                b_val = details['birth'] or (birth if birth and birth != 'xxxx' else None)
                d_val = details['death'] or (death if death and death != 'xxxx' else None)
                cem_val = details['cemetery']
                
                print(f"    -> Birth:    {b_val}")
                print(f"    -> Death:    {d_val}")
                print(f"    -> Cemetery: {cem_val}")
                
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                new_notes = (notes or '') + f" | Verified via FindAGrave: {top_link}"
                if cem_val:
                    new_notes += f" (Buried at {cem_val})"
                    
                c.execute('''
                    UPDATE persons 
                    SET birth_info = COALESCE(?, birth_info),
                        death_info = COALESCE(?, death_info),
                        notes = ?
                    WHERE person_id = ?
                ''', (b_val, d_val, new_notes, pid))
                conn.commit()
                conn.close()
                updated_count += 1
        else:
            print("  x No direct Delaware FindAGrave memorial found.")
            
        time.sleep(1.5)
        
    print(f"\n=========================================================================")
    print(f"  DAVIS FAMILY HYDRATION COMPLETE! Updated {updated_count} profiles.")
    print(f"=========================================================================")

if __name__ == "__main__":
    run_davis_hydration()
