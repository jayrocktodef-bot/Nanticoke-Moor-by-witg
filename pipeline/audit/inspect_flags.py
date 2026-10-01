import sqlite3
import re

DB_PATH = "preservation_output/genealogy_preservation.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

PHRASE_KEYWORDS = [
    'buried', 'daughter of', 'son of', 'wife of', 'husband of', 'married to', 'census',
    'resident', 'child of', 'family', 'unknown', 'page', 'http', 'www', 'index',
    'native american', 'community', 'county', 'delaware', 'jersey', 'cemetery',
    'tombstone', 'estate', 'probate', 'will of', 'church', 'bmd', 'record',
    'photo', 'picture', 'note:', 'see also', 'unidentified', 'infant', 'baby',
    'brother', 'sister', 'mother', 'father', 'nephew', 'niece', 'uncle', 'aunt',
    'cousin', 'ancestor', 'descendant', 'generation', 'lineage', 'tribute', 'obituary',
    '1870', '1880', '1900', '1910', '1920', '1930', '1940', '1950'
]

c.execute("SELECT person_id, name, source_page, dataset_source FROM persons")
flagged = []
for p in c.fetchall():
    name = p['name'].strip()
    nl = name.lower()
    reasons = []
    if len(name) > 40:
        reasons.append("Length > 40")
    if any(kw in nl for kw in PHRASE_KEYWORDS):
        reasons.append("Keyword")
    if re.search(r'\d{3,}', name):
        reasons.append("Dates")
    if len(name.split()) > 4 and not any(title in nl for title in ['dr', 'rev', 'capt', 'col', 'hon', 'jr', 'sr', 'iii', 'iv']):
        reasons.append(">4 words")
    if re.search(r'[,;:\(\)\[\]\{\}\/\\="]', name) and not re.match(r'^[A-Za-z\s\.\'-]+\([A-Za-z\s\.\'-]+\)$', name):
        reasons.append("Punctuation")
    if reasons:
        flagged.append((p['person_id'], name, reasons, p['source_page']))

print(f"Total Flagged: {len(flagged)}")
for item in flagged:
    print(f"ID #{item[0]}: '{item[1]}' | reasons: {item[2]} | src: {item[3]}")
