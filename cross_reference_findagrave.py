import sqlite3
import urllib.request
import urllib.parse
import re
import time
import sys

DB_PATH = "preservation_output/genealogy_preservation.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
BATCH_SIZE = 15
INITIAL_DELAY = 3.0  # seconds between FindAGrave requests

STOP_WORDS = set(['who', 'was', 'brother', 'sister', 'remained', 'their', 'will', 'had', 'living', 'died', 'born', 'them', 'they', 'here', 'there', 'from', 'with', 'also', 'said', 'were', 'been', 'this', 'that', 'have'])

def get_candidates(limit=BATCH_SIZE):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT person_id, name, birth_info, death_info, notes
        FROM persons
        WHERE (birth_info IS NULL OR birth_info = '' OR birth_info LIKE '%xxxx%'
            OR death_info IS NULL OR death_info = '' OR death_info LIKE '%xxxx%')
          AND (notes NOT LIKE '%FindAGrave%')
          AND length(name) > 4
        ORDER BY person_id
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    
    # Filter candidates to valid two-name entries
    valid = []
    for r in rows:
        name_parts = [w.strip(',') for w in r[1].split() if len(w) > 1 and w.lower() not in STOP_WORDS]
        if len(name_parts) >= 2:
            valid.append(r)
    return valid

def count_remaining():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM persons
        WHERE (birth_info IS NULL OR birth_info = '' OR birth_info LIKE '%xxxx%'
            OR death_info IS NULL OR death_info = '' OR death_info LIKE '%xxxx%')
          AND (notes NOT LIKE '%FindAGrave%')
          AND length(name) > 4
    ''')
    n = c.fetchone()[0]
    conn.close()
    return n

def search_findagrave(first_name, last_name, state_id=8):
    params = {
        'firstname': first_name,
        'lastname': last_name,
        'stateid': state_id,
        'cemeteryname': ''
    }
    url = f"https://www.findagrave.com/memorial/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (attempt + 1) * 10
                print(f"  [RATE-LIMITED 429] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"  [HTTP Error {e.code}] {first_name} {last_name}")
                return None
        except Exception as e:
            print(f"  [ERROR] Search failed for {first_name} {last_name}: {e}")
            return None
    return None

def parse_memorial(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode('utf-8')
                birth = re.search(r'itemprop="birthDate">(.*?)<', html)
                death = re.search(r'itemprop="deathDate">(.*?)<', html)
                cemetery = re.search(r'itemprop="name">(.*?)</span>', html)
                return {
                    'birth': birth.group(1).strip() if birth else None,
                    'death': death.group(1).strip() if death else None,
                    'cemetery': cemetery.group(1).strip() if cemetery else None,
                    'url': url
                }
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(10)
            else:
                return None
        except Exception:
            return None
    return None

def run_batch():
    candidates = get_candidates(limit=BATCH_SIZE)
    if not candidates:
        return 0

    hydrated = 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for pid, name, birth, death, notes in candidates:
        parts = [w.strip(',') for w in name.split() if len(w) > 1 and w.lower() not in STOP_WORDS]
        if len(parts) < 2:
            cur.execute("UPDATE persons SET notes = COALESCE(notes,'') || ' | FindAGrave: skipped invalid name' WHERE person_id = ?", (pid,))
            continue

        first_name = parts[0]
        last_name  = parts[-1]

        found = False
        # Try Delaware (8), Maryland (20), New Jersey (30)
        for state_id in [8, 20, 30]:
            html = search_findagrave(first_name, last_name, state_id=state_id)
            if not html:
                continue

            memorial_links = re.findall(r'href="(/memorial/\d+/[^"]+)"', html)
            if memorial_links:
                top_link = "https://www.findagrave.com" + memorial_links[0]
                details  = parse_memorial(top_link)
                if details and (details['birth'] or details['death']):
                    new_notes = (notes or '') + f" | Verified via FindAGrave: {top_link}"
                    cur.execute('''
                        UPDATE persons
                        SET birth_info = COALESCE(NULLIF(?, ''), birth_info),
                            death_info = COALESCE(NULLIF(?, ''), death_info),
                            notes = ?
                        WHERE person_id = ?
                    ''', (details['birth'], details['death'], new_notes, pid))

                    # Insert into Evidence Model (sources, facts, citations)
                    cur.execute("INSERT OR IGNORE INTO sources (title, url, dataset) VALUES (?, ?, 'findagrave')",
                                (f"FindAGrave Memorial #{top_link.split('/')[4]}", top_link))
                    cur.execute("SELECT source_id FROM sources WHERE url = ?", (top_link,))
                    sres = cur.fetchone()
                    if sres:
                        sid = sres[0]
                        if details['birth']:
                            cur.execute("INSERT INTO facts (person_id, fact_type, date_string, place_string) VALUES (?, 'Birth', ?, ?)", 
                                        (pid, details['birth'], details.get('cemetery')))
                            fid = cur.lastrowid
                            cur.execute("INSERT INTO citations (fact_id, source_id, evidence_text) VALUES (?, ?, ?)",
                                        (fid, sid, f"FindAGrave Burial Record: {details.get('cemetery', '')}"))
                        if details['death']:
                            cur.execute("INSERT INTO facts (person_id, fact_type, date_string, place_string) VALUES (?, 'Death', ?, ?)", 
                                        (pid, details['death'], details.get('cemetery')))
                            fid = cur.lastrowid
                            cur.execute("INSERT INTO citations (fact_id, source_id, evidence_text) VALUES (?, ?, ?)",
                                        (fid, sid, f"FindAGrave Burial Record: {details.get('cemetery', '')}"))

                    print(f"  ✓ #{pid} {name}: B={details['birth']} D={details['death']} [{top_link}]")
                    hydrated += 1
                    found = True
                    break
            time.sleep(INITIAL_DELAY)

        if not found:
            cur.execute("UPDATE persons SET notes = COALESCE(notes,'') || ' | FindAGrave: no match' WHERE person_id = ?", (pid,))

    conn.commit()
    conn.close()
    return hydrated

if __name__ == "__main__":
    remaining_start = count_remaining()
    print(f"Starting rate-limited FindAGrave hydration. Profiles remaining: {remaining_start}\n")

    total_hydrated = 0
    batch_num = 1

    while True:
        remaining = count_remaining()
        if remaining == 0 or batch_num > 5:  # Run up to 5 clean batches per session to stay within rate limits
            break

        print(f"[Batch #{batch_num}] Remaining unattempted: {remaining}")
        h = run_batch()
        total_hydrated += h
        batch_num += 1

        if h == 0:
            print("No new matches found in this batch.")

        time.sleep(5)

    print(f"\n=== FindAGrave Sweep Session Complete ===")
    print(f"Total profiles hydrated this session: {total_hydrated}")
    print(f"Profiles remaining: {count_remaining()}")
