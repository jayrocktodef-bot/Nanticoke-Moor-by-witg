import sqlite3
import urllib.request
import urllib.parse
import re
import time
import sys

DB_PATH = "preservation_output/genealogy_preservation.db"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BATCH_SIZE = 20   # candidates per run
DELAY      = 2.5  # seconds between FindAGrave requests

def get_candidates(offset=0, limit=BATCH_SIZE):
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
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = c.fetchall()
    conn.close()
    return rows

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
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f"  [ERROR] Search failed for {first_name} {last_name}: {e}")
        return None

def parse_memorial(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
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
    except Exception as e:
        print(f"  [ERROR] Memorial parse failed {url}: {e}")
        return None

def run_batch(offset=0):
    candidates = get_candidates(offset=offset)
    if not candidates:
        print("No more candidates to process.")
        return 0

    hydrated = 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for pid, name, birth, death, notes in candidates:
        # Normalise name — strip leading punctuation/spaces
        name_clean = re.sub(r'[^a-zA-Z\s]', ' ', name).strip()
        parts = name_clean.split()
        if len(parts) < 2:
            continue

        first_name = parts[0]
        last_name  = parts[-1]

        # Try Delaware first (8), then Maryland (20), then New Jersey (30)
        found = False
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
                    print(f"  ✓ #{pid} {name}: B={details['birth']} D={details['death']} [{top_link}]")
                    hydrated += 1
                    found = True
                    break
            time.sleep(DELAY)

        if not found:
            # Mark as attempted so we skip it next time
            cur.execute("UPDATE persons SET notes = COALESCE(notes,'') || ' | FindAGrave: no match' WHERE person_id = ?", (pid,))

    conn.commit()
    conn.close()
    return hydrated

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    remaining_start = count_remaining()
    print(f"Starting continuous hydration. Profiles remaining: {remaining_start}")
    print("Running until all unhydrated profiles are attempted (Ctrl+C to stop).\n")

    total_hydrated = 0
    offset = 0

    while True:
        remaining = count_remaining()
        if remaining == 0:
            print("\n✅ All profiles have been attempted!")
            break

        print(f"\n[Batch offset={offset}] Remaining: {remaining} | Hydrated this session: {total_hydrated}")
        h = run_batch(offset=0)  # Always re-query from offset 0 since processed ones get the FindAGrave note
        total_hydrated += h

        if h == 0:
            print(f"\n⚠️  Batch returned 0 hydrations. Remaining: {count_remaining()}")
            # If zero were hydrated but candidates remain, check if any candidates exist
            cands = get_candidates(offset=0, limit=5)
            if not cands:
                print("✅ No more candidates. Done!")
                break
            print("Continuing anyway...")

        time.sleep(1)

    print(f"\n=== SESSION COMPLETE ===")
    print(f"Total profiles hydrated this session: {total_hydrated}")
    print(f"Profiles still unhydrated: {count_remaining()}")
