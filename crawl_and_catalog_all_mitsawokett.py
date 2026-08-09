import urllib.request
import urllib.parse
import sqlite3
import os
import re
import concurrent.futures
from bs4 import BeautifulSoup

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'
ASSETS_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/assets/mitsawokett_photos'
os.makedirs(ASSETS_DIR, exist_ok=True)

BASE_URL = 'https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/'
INDEX_PAGES = [
    'IndexA-C.htm',
    'IndexD.htm',
    'IndexE-L.htm',
    'IndexM.htm',
    'IndexN-R.htm',
    'IndexS-Z.htm'
]

BAD_FILENAMES = [
    'ind-footer', 'email', 'copyright', 'redrule', 'return', 'banner', 'sorry',
    'index', 'gotoe-mail', 'mail.jpg', 'us.jpg', 'home.jpg', 'back.jpg'
]

BAD_NAME_PHRASES = [
    'photo courtesy', 'identification by', 'how are the', 'ladies related',
    'photo index', 'main menu', 'email us', 'kuskarawoak', 'mitsawokett',
    'all rights reserved', 'a photographic survey', 'indian river hundred',
    'in possession of', 'courtesy of', 'family records', 'tombstone story',
    'church meeting', 'added 20', 'click here', 'see below', 'probate record'
]

def discover_all_detail_pages():
    detail_pages = set()
    for ip in INDEX_PAGES:
        url = urllib.parse.urljoin(BASE_URL, ip)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.endswith('.htm') or href.endswith('.html'):
                    if not any(x in href for x in ['Index', 'MainMenu', 'IndexA-C', 'IndexD', 'IndexE-L', 'IndexM', 'IndexN-R', 'IndexS-Z']):
                        full_u = urllib.parse.urljoin(url, href)
                        detail_pages.add(full_u)
        except Exception as e:
            print(f"Error reading index {url}: {e}")
    return sorted(list(detail_pages))

def clean_person_name(raw_name):
    if not raw_name:
        return ''
    n = raw_name.strip()
    n = re.sub(r'https?://\S+', '', n).strip()
    n = re.sub(r'~?\d{4}-\d{4}', '', n).strip()
    n = re.sub(r'b\.\s*\d{4}', '', n, flags=re.I).strip()
    n = re.sub(r'd\.\s*\d{4}', '', n, flags=re.I).strip()
    n = re.sub(r'c\.\s*\d{4}', '', n, flags=re.I).strip()
    n = re.sub(r'\s*\([^)]*\)', '', n).strip() # Strip parentheticals
    n = re.sub(r'^(SMYRNA|DOVER|BRIDGETON|CHESTERTOWN|WILMINGTON|MILLSBORO|GEORGETOWN|KENTON|FELTON)\s*-\s*', '', n, flags=re.I).strip()
    n = re.sub(r'^(Chief|Rev\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s+', '', n, flags=re.I).strip()
    n = re.sub(r',?\s*age.*$', '', n, flags=re.I).strip()
    n = re.sub(r'[0-9]', '', n).strip()
    
    if any(b in n.lower() for b in BAD_NAME_PHRASES):
        return ''
    if len(n.split()) < 2 or len(n.split()) > 5:
        return ''
    return n

def extract_names_and_surnames(lines, page_url):
    names = []
    
    # Try parsing couple format e.g. "Charles Edward & Della Mae (Ridgway) Carey"
    for line in lines:
        line_clean = line.strip()
        if any(b in line_clean.lower() for b in BAD_NAME_PHRASES):
            continue
            
        # Match pattern: First & Second (Maiden) Surname
        m_couple = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*&\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\(([^)]+)\))?\s*([A-Z][a-z]+)', line_clean)
        if m_couple:
            p1_first, p2_first, maiden, surname = m_couple.groups()
            name1 = f"{p1_first} {surname}"
            name2 = f"{p2_first} {maiden} {surname}" if maiden else f"{p2_first} {surname}"
            
            c1 = clean_person_name(name1)
            c2 = clean_person_name(name2)
            if c1: names.append({'name': c1, 'maiden': None, 'surname': surname})
            if c2: names.append({'name': c2, 'maiden': maiden, 'surname': surname})
            continue

        # Match single person with maiden e.g. "Arzelia (Morris) Clark"
        m_single_maiden = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\(([^)]+)\)\s*([A-Z][a-z]+)', line_clean)
        if m_single_maiden:
            first, maiden, surname = m_single_maiden.groups()
            cname = clean_person_name(f"{first} {maiden} {surname}")
            if cname:
                names.append({'name': cname, 'maiden': maiden, 'surname': surname})
            continue

        # Match comma separated list e.g. "Phyllis Harmon Morris, Jeanette Harmon, Wanda Harmon Radish"
        if ',' in line_clean:
            parts = line_clean.split(',')
            for p in parts:
                cn = clean_person_name(p)
                if cn:
                    surn = cn.split()[-1]
                    names.append({'name': cn, 'maiden': None, 'surname': surn})
            continue

        # Single name
        cn = clean_person_name(line_clean)
        if cn:
            surn = cn.split()[-1]
            names.append({'name': cn, 'maiden': None, 'surname': surn})

    # If no names extracted from lines, try parsing the URL filename
    if not names:
        filename = os.path.basename(page_url).replace('.htm', '').replace('.html', '')
        # Un-camelcase filename e.g. CareyCharlesE&DellaRidgeway
        filename_spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', filename)
        filename_spaced = filename_spaced.replace('&', ' & ')
        cn = clean_person_name(filename_spaced)
        if cn:
            surn = cn.split()[-1]
            names.append({'name': cn, 'maiden': None, 'surname': surn})

    return names

def process_detail_page(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        page_filename = os.path.basename(url)
        title = soup.title.get_text().strip() if soup.title else ''
        text = soup.get_text()
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        extracted_names = extract_names_and_surnames(lines, url)

        # Get images
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if not any(b in src.lower() for b in BAD_FILENAMES):
                full_img_url = urllib.parse.urljoin(url, src)
                images.append(full_img_url)

        results = []
        for img_url in images:
            img_filename = os.path.basename(img_url)
            # Local filename sanitized
            local_filename = f"mitsawokett_{re.sub(r'[^a-zA-Z0-9_.-]', '_', img_filename)}"
            local_path = os.path.join(ASSETS_DIR, local_filename)
            db_local_path = f"assets/mitsawokett_photos/{local_filename}"

            # Download image if missing or small
            if not os.path.exists(local_path) or os.path.getsize(local_path) < 100:
                try:
                    img_req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                    img_data = urllib.request.urlopen(img_req, timeout=10).read()
                    with open(local_path, 'wb') as f:
                        f.write(img_data)
                except Exception as e:
                    pass

            # Determine caption & subject names
            subj = ", ".join([n['name'] for n in extracted_names]) if extracted_names else title
            maiden = extracted_names[0]['maiden'] if extracted_names else None
            married = extracted_names[0]['surname'] if extracted_names else None

            results.append({
                'title': title or subj,
                'subject': subj,
                'maiden': maiden,
                'married': married,
                'local_path': db_local_path,
                'source_url': url,
                'extracted_names': extracted_names,
                'page_filename': page_filename
            })

        return results
    except Exception as e:
        return []

def main():
    print("Step 1: Discovering all photo detail pages...")
    detail_urls = discover_all_detail_pages()
    print(f"Discovered {len(detail_urls)} total detail pages across all index tabs.")

    print("Step 2: Crawling and parsing detail pages concurrently...")
    all_photo_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(process_detail_page, u): u for u in detail_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            res = future.result()
            if res:
                all_photo_records.extend(res)

    print(f"Extracted {len(all_photo_records)} photo records.")

    print("Step 3: Ingesting into database...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")
    c = conn.cursor()

    photo_inserted = 0
    person_inserted = 0
    junction_inserted = 0
    rel_inserted = 0

    for rec in all_photo_records:
        # Upsert photo_catalog
        c.execute("SELECT photo_id FROM photo_catalog WHERE local_image_path = ? OR source_url = ?", (rec['local_path'], rec['source_url']))
        row = c.fetchone()
        if row:
            photo_id = row[0]
            c.execute("""
                UPDATE photo_catalog
                SET title_or_caption = ?, subject_names = ?, maiden_name = ?, married_surname = ?, local_image_path = ?
                WHERE photo_id = ?
            """, (rec['title'], rec['subject'], rec['maiden'], rec['married'], rec['local_path'], photo_id))
        else:
            c.execute("""
                INSERT INTO photo_catalog (title_or_caption, subject_names, maiden_name, married_surname, approximate_year, local_image_path, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rec['title'], rec['subject'], rec['maiden'], rec['married'], '', rec['local_path'], rec['source_url']))
            photo_id = c.lastrowid
            photo_inserted += 1

        # Upsert persons and junction links
        p_ids = []
        for n_info in rec['extracted_names']:
            pname = n_info['name']
            if not pname: continue
            
            c.execute("SELECT person_id FROM persons WHERE LOWER(name) = LOWER(?)", (pname,))
            prow = c.fetchone()
            if prow:
                pid = prow[0]
            else:
                c.execute("INSERT INTO persons (name, source_page, notes, dataset_source) VALUES (?, ?, ?, ?)",
                          (pname, rec['page_filename'], f"Ingested from {rec['page_filename']}", 'mitsawokett_delaware'))
                pid = c.lastrowid
                person_inserted += 1

            p_ids.append(pid)

            # Link person_photos
            c.execute("INSERT OR IGNORE INTO person_photos (person_id, photo_id) VALUES (?, ?)", (pid, photo_id))
            junction_inserted += 1

        # Add relationships if 2 persons found on couple page
        if len(p_ids) == 2:
            pid1, pid2 = p_ids[0], p_ids[1]
            c.execute("SELECT id FROM relationships WHERE (person_a_id = ? AND person_b_id = ?) OR (person_a_id = ? AND person_b_id = ?)",
                      (pid1, pid2, pid2, pid1))
            if not c.fetchone():
                c.execute("INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text) VALUES (?, ?, ?, ?)",
                          (pid1, pid2, 'spouse', f"Appears together in photograph on {rec['page_filename']}"))
                rel_inserted += 1

    conn.commit()
    conn.close()

    print("=========================================================================")
    print(f"  INGESTION COMPLETE:")
    print(f"  - New Photo Catalog Records:  {photo_inserted}")
    print(f"  - New Persons Ingested:        {person_inserted}")
    print(f"  - Person-Photo Junction Links: {junction_inserted}")
    print(f"  - Family Spousal Relationships:{rel_inserted}")
    print("=========================================================================")

if __name__ == '__main__':
    main()
