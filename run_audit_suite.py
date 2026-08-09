import sqlite3
import re
from collections import defaultdict

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'

def run_audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT person_id, name, birth_info, death_info, notes, source_page, dataset_source FROM persons')
    all_persons = c.fetchall()

    print(f"=========================================================================")
    print(f"  GENEALOGY DATABASE AUDIT REPORT — TOTAL RECORDS: {len(all_persons)}")
    print(f"=========================================================================\n")

    # 1. Non-Person Phrase Detection
    PHRASE_KEYWORDS = [
        'buried', 'daughter of', 'son of', 'wife of', 'husband of', 'married to', 'census',
        'resident', 'child of', 'family', 'unknown', 'page', 'http', 'www', 'index',
        'native american', 'community', 'county', 'delaware', 'jersey', 'cemetery',
        'tombstone', 'estate', 'probate', 'will of', 'church', 'bmd', 'record',
        'photo', 'picture', 'note:', 'see also', 'unidentified', 'infant', 'baby',
        'brother', 'sister', 'mother', 'father', 'nephew', 'niece', 'uncle', 'aunt',
        'cousin', 'ancestor', 'descendant', 'generation', 'lineage', 'tribute', 'obituary',
        '1870', '1880', '1900', '1910', '1920', '1930', '1940', '1950', '25.', '30.'
    ]

    non_person_phrases = []
    for p in all_persons:
        name = p['name'].strip()
        name_lower = name.lower()
        
        reasons = []
        if len(name) > 40:
            reasons.append("Length > 40 chars")
        if any(kw in name_lower for kw in PHRASE_KEYWORDS):
            reasons.append("Non-person title/sentence keyword")
        if re.search(r'\d{3,}', name):
            reasons.append("Contains numeric years/dates")
        if len(name.split()) > 4 and not any(title in name_lower for title in ['dr', 'rev', 'capt', 'col', 'hon', 'jr', 'sr', 'iii', 'iv']):
            reasons.append("More than 4 words")
        if re.search(r'[,;:\(\)\[\]\{\}\/\\="]', name) and not re.match(r'^[A-Za-z\s\.\'-]+\([A-Za-z\s\.\'-]+\)$', name):
            reasons.append("Invalid punctuation or HTML tag fragment")

        if reasons:
            non_person_phrases.append((p, reasons))

    print(f"🚩 Category 1: Non-Person Entities & Sentence Phrases ({len(non_person_phrases)} flagged)")
    print("-" * 75)
    for p, r in non_person_phrases[:20]:
        print(f"  • ID #{p['person_id']}: \"{p['name']}\"")
        print(f"    Reasons: {', '.join(r)} | Source: {p['source_page']}")

    # 2. Duplicate Person Detection
    name_map = defaultdict(list)
    for p in all_persons:
        clean_name = re.sub(r'[\s\.\'-]+', '', p['name'].lower())
        if len(clean_name) > 3 and clean_name not in ['unknown', 'baby', 'infant']:
            name_map[clean_name].append(p)

    exact_dupes = {k: v for k, v in name_map.items() if len(v) > 1}
    dupe_count = sum(len(v) for v in exact_dupes.values())
    print(f"\n🚩 Category 2: Duplicate Individual Names ({len(exact_dupes)} duplicate groups, {dupe_count} total records)")
    print("-" * 75)
    count = 0
    for k, v in exact_dupes.items():
        if count >= 15: break
        print(f"  • Group \"{v[0]['name']}\" ({len(v)} occurrences):")
        for p in v[:4]:
            print(f"    └─ ID #{p['person_id']} | Source: {p['source_page']} | Dataset: {p['dataset_source']}")
        count += 1

    # 3. Relationship Anomalies
    c.execute('SELECT id, person_a_id, person_b_id, relationship_type FROM relationships WHERE person_a_id = person_b_id')
    self_rels = c.fetchall()
    print(f"\n🚩 Category 3: Self-Referential Relationships ({len(self_rels)} flagged)")
    for r in self_rels:
        print(f"  • Rel ID #{r['id']}: Person #{r['person_a_id']} linked to self as {r['relationship_type']}")

    c.execute('SELECT COUNT(*) FROM relationships WHERE person_a_id NOT IN (SELECT person_id FROM persons) OR person_b_id NOT IN (SELECT person_id FROM persons)')
    orphaned_rels = c.fetchone()[0]
    print(f"🚩 Category 4: Orphaned Relationship References ({orphaned_rels} flagged)")

    # 4. Photo Catalog & Obituary Anomalies
    c.execute('SELECT photo_id, subject_names, maiden_name FROM photo_catalog WHERE subject_names LIKE "%?%" OR subject_names LIKE "%http%" OR subject_names LIKE "%htm%"')
    junk_photos = c.fetchall()
    print(f"\n🚩 Category 5: Photo Catalog Subject Name Anomalies ({len(junk_photos)} flagged)")
    for ph in junk_photos[:10]:
        print(f"  • Photo #{ph['photo_id']}: \"{ph['subject_names']}\"")

    c.execute("SELECT id, deceased_name FROM obituaries WHERE deceased_name LIKE '%1.%' OR deceased_name LIKE '%2.%' OR deceased_name LIKE '%\"%'")
    junk_obits = c.fetchall()
    print(f"\n🚩 Category 6: Obituary Title Anomalies ({len(junk_obits)} flagged)")
    for ob in junk_obits[:10]:
        print(f"  • Obit #{ob['id']}: \"{ob['deceased_name']}\"")

    conn.close()

if __name__ == '__main__':
    run_audit()
