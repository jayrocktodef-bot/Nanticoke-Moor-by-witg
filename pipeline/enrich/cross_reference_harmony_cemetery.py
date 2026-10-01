import sqlite3
import urllib.request
import re
import time

DB_PATH = 'preservation_output/genealogy_preservation.db'
CEMETERY_ID = 104375

def get_database_names():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT person_id, name FROM persons')
    rows = c.fetchall()
    conn.close()
    
    names_map = {}
    for pid, name in rows:
        clean_name = re.sub(r'[^a-zA-Z\s]', '', name).lower().strip()
        parts = clean_name.split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[-1]
            key = f"{first_name} {last_name}"
            names_map[key] = (pid, name)
    return names_map

def extract_memorials(html):
    memorials = []
    # FindAGrave memorial links usually have titles containing the name
    links = re.findall(r'<a[^>]*href="(/memorial/\d+/[^"]+)"[^>]*>', html)
    
    unique_links = list(set(links))
    for link in unique_links:
        # The slug often has the name, e.g., /memorial/123/john-doe
        parts = link.split('/')
        if len(parts) >= 4:
            slug = parts[-1]
            # Replace dashes with spaces for name comparison
            slug_name = slug.replace('-', ' ').lower()
            slug_parts = slug_name.split()
            if len(slug_parts) >= 2:
                # Remove suffixes like jr, sr, etc.
                if slug_parts[-1] in ['jr', 'sr', 'i', 'ii', 'iii']:
                    slug_parts = slug_parts[:-1]
                
                if len(slug_parts) >= 2:
                    first = slug_parts[0]
                    last = slug_parts[-1]
                    key = f"{first} {last}"
                    memorials.append((key, f"https://www.findagrave.com{link}"))
    return memorials

def main():
    names_map = get_database_names()
    print(f"Loaded {len(names_map)} unique first/last name combinations from database.")
    
    matches_found = []
    
    for page in range(1, 10): # Let's check first 10 pages (~200 memorials)
        url = f'https://www.findagrave.com/cemetery/{CEMETERY_ID}/memorial-search?page={page}'
        print(f"Fetching {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                html = resp.read().decode('utf-8')
                
                memorials = extract_memorials(html)
                if not memorials:
                    print("No more memorials found. Stopping pagination.")
                    break
                    
                for key, link in memorials:
                    if key in names_map:
                        pid, db_name = names_map[key]
                        matches_found.append((pid, db_name, link))
                        print(f"  -> Match Found! DB Name: '{db_name}' | Harmony Cem: {link}")
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
            
        time.sleep(2)
        
    print(f"\n--- Total Matches Found in Harmony Cemetery: {len(matches_found)} ---")

if __name__ == "__main__":
    main()
