import sqlite3
import re
from html import unescape
import sys
sys.path.insert(0, '.')
from archive_naming_rules import get_clean_surname

def parse_deceased_name_and_metadata(obit_text):
    """
    Extracts clean deceased name, birth date, death date, age, and cemetery location.
    """
    lines = [l.strip() for l in obit_text.split('\n') if l.strip()]
    first_line = lines[0] if lines else ""
    
    # 1. Try master index format: "Name YYYY-YYYY" or "Name ~YYYY-YYYY"
    m1 = re.match(r'^([A-Z][a-zA-Z\.\'\-\s\/]+?)\s+(\~?\d{4}(?:\/\d{4})?\-(?:\d{4}|\?))', first_line)
    if m1:
        name = m1.group(1).strip()
    else:
        # 2. Try city/town header: "CHESWOLD: Clement (Ted) Carney, Jr. 66, of Cheswold..."
        m2 = re.search(r'(?:CHESWOLD|MILLSBORO|DOVER|BRIDGETON|REHOBOTH)?\:\s*([A-Z][a-zA-Z\.\'\-\s\(\"]+?)\,\s*(?:age|aged|\d{1,3})', first_line, re.IGNORECASE)
        if m2:
            name = m2.group(1).strip()
        else:
            # 3. Try surname prefix: "HARMON: In Rehoboth... Clinton L. Harmon"
            m3 = re.match(r'^([A-Z]{2,20})\s*\:\s*(.*)', first_line)
            if m3:
                sn = m3.group(1).capitalize()
                rest = m3.group(2)
                name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z]\.|\s+[A-Z][a-z]+){1,3})\b', rest)
                if name_match:
                    found_n = name_match.group(1)
                    name = found_n if sn.lower() in found_n.lower() else f"{found_n} {sn}"
                else:
                    name = f"{sn} Obituary"
            else:
                # 4. Fallback to cleaning first line
                cleaned = re.sub(r'^[A-Z\s]{3,20}\:\s*', '', first_line)
                cleaned = re.sub(r'[\~]?\b(18\d\d|19\d\d|20[0-2]\d)\b.*', '', cleaned).strip()
                cleaned = re.sub(r'[\:\-]$', '', cleaned).strip()
                name = ' '.join(cleaned.split()[:4]) if cleaned else "Unknown Deceased"

    # Clean name punctuation
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'\s*\,\s*$', '', name)

    # Dates
    dates = re.findall(r'\b(18\d\d|19\d\d|20[0-2]\d)\b', obit_text)
    byr = dates[0] if len(dates) >= 1 else None
    dyr = dates[1] if len(dates) >= 2 else (dates[0] if len(dates) == 1 else None)

    # Age
    age_m = re.search(r'\b(?:age|aged)\s+(\d{1,3})\b', obit_text, re.IGNORECASE)
    age = age_m.group(1) if age_m else None

    # Cemetery
    cem_m = re.search(r'\b(?:Interment|Burial|Cemetery)\b[^\.\n]*', obit_text, re.IGNORECASE)
    cemetery = cem_m.group(0).strip() if cem_m else None

    # Source URL
    url_m = re.search(r'https?://[^\s\)]+', obit_text)
    source_url = url_m.group(0) if url_m else None

    return name or "Unknown Deceased", byr, dyr, age, cemetery, source_url

def rebuild_obituaries_final():
    conn = sqlite3.connect('preservation_output/genealogy_preservation.db')
    c = conn.cursor()

    # Persons map
    c.execute('SELECT person_id, name FROM persons')
    persons = c.fetchall()
    name_to_pid = {pname.strip().lower(): pid for pid, pname in persons}

    c.execute('SELECT filename, text_content FROM pages WHERE filename = "obit.htm" OR filename LIKE "obit-%"')
    pages = c.fetchall()

    c.execute('DELETE FROM person_obituaries')
    c.execute('DELETE FROM obituaries')

    all_obits = []

    for fn, txt_content in pages:
        txt = unescape(txt_content or '')
        if not txt or len(txt.strip()) < 50:
            continue
            
        if 'Full obits follow this list' in txt:
            # Monolithic page (obit.htm)
            pos = txt.find('Full obits follow this list')
            index_block = txt[pos:pos+4000]
            raw_names = re.findall(r'([A-Z][a-zA-Z\.\'\-\s\/]+?)\s+\~?\d{4}', index_block)
            clean_names = [n.replace('Use your FIND feature to find a surname.', '').strip() for n in raw_names if len(n.strip()) > 3]
            clean_names.extend(['Marguerite J. Brown', 'Phyllis Lorraine Durham Dangerfield', 'Thelma Davine Loatman Gonzalez'])
            
            body = txt[pos+3000:]
            pattern = r'(?=\b(?:' + '|'.join(re.escape(n) for n in clean_names if len(n) > 3) + r')\b)'
            chunks = re.split(pattern, body)
            for ch in chunks:
                c_clean = ch.strip()
                if len(c_clean) > 80 and 'Full obits follow' not in c_clean:
                    all_obits.append((fn, c_clean))
        else:
            # Multi-page documents
            chunks = re.split(r'\n{2,}|\r\n{2,}', txt)
            current_block = []
            for ch in chunks:
                c_clean = ch.strip()
                if not c_clean or 'Preserved Primary Document' in c_clean:
                    continue
                    
                # New obit header check
                is_new = bool(re.match(r'^[A-Z]{2,20}\:|^[A-Z][a-z]+\s+[A-Z][a-z]+\s+\d{4}', c_clean))
                if is_new and current_block:
                    full_txt = '\n\n'.join(current_block)
                    if len(full_txt) > 80:
                        all_obits.append((fn, full_txt))
                    current_block = [c_clean]
                else:
                    current_block.append(c_clean)
                    
            if current_block:
                full_txt = '\n\n'.join(current_block)
                if len(full_txt) > 80:
                    all_obits.append((fn, full_txt))

    print(f'Total Individual Obituaries Extracted: {len(all_obits)}')

    obit_id = 0
    linked_count = 0

    for fn, obit_text in all_obits:
        name, byr, dyr, age, cemetery, source_url = parse_deceased_name_and_metadata(obit_text)
        obit_id += 1

        c.execute('''
            INSERT INTO obituaries (id, deceased_name, age, birth_date, death_date, cemetery_location, full_text, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (obit_id, name, age, byr, dyr, cemetery, obit_text, source_url))

        # Auto-link to person profile
        clean_d = name.lower()
        pid = name_to_pid.get(clean_d)
        if not pid:
            unquoted = ' '.join([p for p in name.split() if not (p.startswith('\"') or p.startswith('('))])
            pid = name_to_pid.get(unquoted.lower())
            
        if pid:
            c.execute('INSERT OR IGNORE INTO person_obituaries (person_id, obituary_id, role, confidence_score) VALUES (?, ?, "deceased", 1.0)', (pid, obit_id))
            linked_count += 1

    conn.commit()
    print(f'===========================================================')
    print(f'  FINAL OBITUARIES SECTION REBUILT FROM SCRATCH!')
    print(f'  - Individual Obituaries Preserved: {obit_id}')
    print(f'  - Auto-linked to Person Profiles:  {linked_count}')
    print(f'===========================================================')
    conn.close()

if __name__ == '__main__':
    rebuild_obituaries_final()
