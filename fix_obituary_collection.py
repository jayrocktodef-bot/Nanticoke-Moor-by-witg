import sqlite3
import re

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'

def fix_obituaries():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT id, deceased_name, maiden_name, married_surname, birth_date, death_date, age, cemetery_location, surviving_kin, full_text, source_url FROM obituaries ORDER BY id')
    rows = [dict(r) for r in c.fetchall()]

    print(f"Loaded {len(rows)} raw obituary entries.")

    fragment_prefixes = [
        'services ', 'funeral ', 'he is survived', 'she is survived', 'in addition to',
        'family and friends', 'relatives and friends', 'a funeral service', 'predeceased by',
        'he was preceded', 'condolences', 'interment', 'burial', 'viewing', 'memorial ',
        'friends may call', 'written condolences', 'in lieu of flowers', 'contributions',
        'although ken', 'the funeral', 'mr. ', 'mrs. ', 'in memory of', 'obituary for',
        'visitations will', 'visitation ', 'ken is survived', 'charles is survived',
        'she was preceded', 'preceded in death', 'gary is survived', 'the husband of',
        'the burial will', 'a beautiful and', 'durham.-millie'
    ]

    def is_fragment(dname, ftext):
        dn = dname.strip().lower()
        if any(dn.startswith(p) for p in fragment_prefixes):
            return True
        if 'obituary.aspx' in dn or 'http://' in dn or 'www.' in dn or 'delawareonline' in dn:
            return True
        if len(dn.split()) > 6:
            return True
        return False

    def clean_name_key(name):
        n = name.lower()
        n = re.sub(r'[^a-z\s]', '', n)
        n = re.sub(r'\b(jr|sr|iii|ii|iv|chief|dr|rev|mr|mrs|ms)\b', '', n).strip()
        tokens = [t for t in n.split() if len(t) > 1]
        return ' '.join(tokens)

    def extract_clean_name(dname, ftext):
        n = dname.strip()
        n = re.sub(r'https?://\S+', '', n).strip()
        n = re.sub(r'~?\d{4}-\d{4}', '', n).strip()
        n = re.sub(r'\s*\([^)]*\)', '', n).strip()
        n = re.sub(r'^(SMYRNA|DOVER|BRIDGETON|CHESTERTOWN|WILMINGTON|MILLSBORO|GEORGETOWN|KENTON|FELTON)\s*-\s*', '', n, flags=re.I).strip()
        n = re.sub(r'^(Chief|Rev\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s+', '', n, flags=re.I).strip()
        n = re.sub(r',?\s*age.*$', '', n, flags=re.I).strip()
        n = re.sub(r"''", "'", n)
        
        if n and not is_fragment(n, ftext) and len(n.split()) <= 5 and len(n) > 2:
            return n

        # Extract from full_text
        m = re.search(r'^([A-Z][a-z]+(?:\s+[\"“\'][^\"”\']+[\"“\'])?(?:\s+[A-Z][a-z\'-]+){1,4})(?:,|\s+age|\s+of|\s+died|\s+passed|\s+born|\s+\(|\s+~)', ftext.strip(), re.I)
        if m:
            cand = m.group(1).strip()
            cand = re.sub(r'^(SMYRNA|DOVER|BRIDGETON|CHESTERTOWN|WILMINGTON|MILLSBORO|GEORGETOWN|KENTON|FELTON)\s*-\s*', '', cand, flags=re.I).strip()
            cand = re.sub(r'^(Chief|Rev\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s+', '', cand, flags=re.I).strip()
            if not is_fragment(cand, ftext) and len(cand.split()) <= 5:
                return cand

        # Extract from legacy url slug
        m2 = re.search(r'obituary\.aspx\?n=([A-Za-z-]+)', dname + ' ' + ftext)
        if m2:
            return m2.group(1).replace('-', ' ').title()

        return 'Unknown Deceased'

    # Step 1: Group adjacent text fragment rows
    grouped = []
    current = None

    for r in rows:
        dname = r['deceased_name'] or ''
        ftext = r['full_text'] or ''

        if is_fragment(dname, ftext) and current is not None:
            current['full_text'] += '\n\n' + ftext
            current['merged_ids'].append(r['id'])
            if not current['cemetery_location'] and r['cemetery_location']:
                current['cemetery_location'] = r['cemetery_location']
            if not current['surviving_kin'] and r['surviving_kin']:
                current['surviving_kin'] = r['surviving_kin']
        else:
            if current is not None:
                grouped.append(current)
            r['merged_ids'] = [r['id']]
            current = r

    if current is not None:
        grouped.append(current)

    print(f"Grouped into {len(grouped)} distinct obituary blocks.")

    # Step 2: Extract clean names & deduplicate identical persons
    name_map = {}
    unified_obits = []

    for g in grouped:
        cname = extract_clean_name(g['deceased_name'], g['full_text'])
        g['clean_name'] = cname
        key = clean_name_key(cname)

        if key and len(key) >= 3 and key in name_map:
            existing = name_map[key]
            existing['full_text'] += '\n\n' + g['full_text']
            existing['merged_ids'].extend(g['merged_ids'])
            if len(cname) > len(existing['clean_name']) and 'Unknown' not in cname:
                existing['clean_name'] = cname
        else:
            if key and len(key) >= 3:
                name_map[key] = g
            unified_obits.append(g)

    print(f"Unified into {len(unified_obits)} unique obituaries (Merged {len(rows) - len(unified_obits)} fragment/duplicate records).")

    # Step 3: Perform database updates and re-assign junction tables
    conn.execute("PRAGMA foreign_keys=OFF")
    
    # Track surviving primary IDs vs deleted IDs
    surviving_primary_ids = set()
    reassignments = {} # old_id -> primary_id

    for ob in sorted(unified_obits, key=lambda x: x['id']):
        primary_id = ob['merged_ids'][0]
        surviving_primary_ids.add(primary_id)
        
        # All merged IDs map to primary_id
        for mid in ob['merged_ids']:
            reassignments[mid] = primary_id

        # Update primary record
        c.execute("""
            UPDATE obituaries
            SET deceased_name = ?, full_text = ?, cemetery_location = ?, surviving_kin = ?
            WHERE id = ?
        """, (ob['clean_name'], ob['full_text'].strip(), ob['cemetery_location'], ob['surviving_kin'], primary_id))

    # Reassign person_obituaries junction records
    for old_id, new_id in reassignments.items():
        if old_id != new_id:
            c.execute("UPDATE OR IGNORE person_obituaries SET obituary_id = ? WHERE obituary_id = ?", (new_id, old_id))
            c.execute("DELETE FROM person_obituaries WHERE obituary_id = ?", (old_id,))

    # Delete non-primary obituary rows
    all_row_ids = [r['id'] for r in rows]
    deleted_ids = [rid for rid in all_row_ids if rid not in surviving_primary_ids]
    
    if deleted_ids:
        placeholders = ','.join('?' * len(deleted_ids))
        c.execute(f"DELETE FROM obituaries WHERE id IN ({placeholders})", deleted_ids)
        print(f"Deleted {len(deleted_ids)} redundant fragment/duplicate obituary rows.")

    conn.commit()
    conn.close()
    print("Obituary collection cleaning and deduplication completed successfully!")

if __name__ == '__main__':
    fix_obituaries()
