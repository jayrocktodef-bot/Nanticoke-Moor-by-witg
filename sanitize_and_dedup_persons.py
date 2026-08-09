import sqlite3
import re

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'

def sanitize_and_dedup():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT person_id, name, source_page, notes FROM persons ORDER BY person_id')
    rows = [dict(r) for r in c.fetchall()]
    print(f"Loaded {len(rows)} raw person records.")

    bad_phrases = [
        'photo courtesy', 'identification by', 'how are the', 'ladies related',
        'photo index', 'main menu', 'email us', 'kuskarawoak', 'mitsawokett',
        'all rights reserved', 'a photographic survey', 'indian river hundred',
        'in possession of', 'courtesy of', 'family records', 'tombstone story',
        'church meeting', 'added 20', 'click here', 'see below', 'probate record',
        'unknown', 'return', 'redrule', 'banner', 'page', 'http', 'www.', 'jpg', 'gif', 'htm'
    ]

    def sanitize_name(name):
        if not name: return ''
        n = name.strip()
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
        n = re.sub(r'\s+', ' ', n).strip()
        
        if any(b in n.lower() for b in bad_phrases): return ''
        words = n.split()
        if len(words) < 2 or len(words) > 5: return ''
        return n

    conn.execute("PRAGMA foreign_keys=OFF")

    name_to_primary = {}
    deleted_pids = set()

    for r in rows:
        pid = r['person_id']
        clean_n = sanitize_name(r['name'])
        
        if not clean_n:
            deleted_pids.add(pid)
        else:
            key = clean_n.lower()
            if key in name_to_primary:
                primary_id = name_to_primary[key]
                # Reassign relationships
                c.execute('UPDATE OR IGNORE relationships SET person_a_id = ? WHERE person_a_id = ?', (primary_id, pid))
                c.execute('UPDATE OR IGNORE relationships SET person_b_id = ? WHERE person_b_id = ?', (primary_id, pid))
                # Reassign person_photos
                c.execute('UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?', (primary_id, pid))
                deleted_pids.add(pid)
            else:
                name_to_primary[key] = pid
                if clean_n != r['name']:
                    c.execute('UPDATE OR IGNORE persons SET name = ? WHERE person_id = ?', (clean_n, pid))

    # Delete invalid and duplicate records
    if deleted_pids:
        deleted_list = list(deleted_pids)
        placeholders = ','.join('?' * len(deleted_list))
        c.execute(f'DELETE FROM persons WHERE person_id IN ({placeholders})', deleted_list)
        c.execute(f'DELETE FROM person_photos WHERE person_id IN ({placeholders})', deleted_list)
        c.execute(f'DELETE FROM relationships WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})', deleted_list + deleted_list)

    conn.commit()

    c.execute('SELECT COUNT(*) FROM persons')
    final_count = c.fetchone()[0]
    print(f"Sanitization complete! Final clean person records count: {final_count}")
    conn.close()

if __name__ == '__main__':
    sanitize_and_dedup()
