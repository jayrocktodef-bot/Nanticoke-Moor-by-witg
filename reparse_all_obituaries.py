import sqlite3
import re
from html import unescape
import sys
sys.path.insert(0, '.')
from archive_naming_rules import get_clean_surname

def parse_smart_obituary(block):
    """
    Parses clean deceased name, accurate birth/death years, age, and cemetery location.
    Handles explicit header spans (1931-2002), calculates birth year from death year & age,
    and prevents inverted dates.
    """
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    first_line = lines[0] if lines else ""

    # 1. Header Date Span Check (e.g. "Phyllis Lorraine Durham Dangerfield 1931-2002")
    hdr_dates = re.search(r'[\~]?\b(18\d\d|19\d\d|20[0-2]\d)\b\s*[\-\/]\s*\b(18\d\d|19\d\d|20[0-2]\d)\b', first_line)
    
    # 2. Extract Deceased Name
    if hdr_dates:
        dname = first_line[:hdr_dates.start()].strip()
    else:
        m_head = re.search(r'(?:CHESWOLD|MILLSBORO|DOVER|BRIDGETON|REHOBOTH)?\:\s*([A-Z][a-zA-Z\.\'\-\s\(\"]+?)\,\s*(?:age|aged|\d{1,3})', first_line, re.IGNORECASE)
        if m_head:
            dname = m_head.group(1).strip()
        else:
            m_sur = re.match(r'^([A-Z]{2,20})\s*\:\s*(.*)', first_line)
            if m_sur:
                sn = m_sur.group(1).capitalize()
                rest = m_sur.group(2)
                name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z]\.|\s+[A-Z][a-z]+){1,3})\b', rest)
                if name_match:
                    found_n = name_match.group(1)
                    dname = found_n if sn.lower() in found_n.lower() else f"{found_n} {sn}"
                else:
                    dname = f"{sn} Obituary"
            else:
                cleaned = re.sub(r'^[A-Z\s]{3,20}\:\s*', '', first_line)
                cleaned = re.sub(r'[\~]?\b(18\d\d|19\d\d|20[0-2]\d)\b.*', '', cleaned).strip()
                cleaned = re.sub(r'[\:\-]$', '', cleaned).strip()
                dname = ' '.join(cleaned.split()[:4]) if cleaned else "Unknown Deceased"

    dname = re.sub(r'\s+', ' ', dname).strip()
    dname = re.sub(r'\s*\,\s*$', '', dname)

    # 3. Extract Age
    age_m = re.search(r'\b(?:age|aged)\s+(\d{1,3})\b|\b(\d{1,3})\s*(?:years?\s*old|yo)\b', block, re.IGNORECASE)
    age = None
    if age_m:
        age = age_m.group(1) or age_m.group(2)

    # 4. Extract Birth and Death Years Accurately
    byr = None
    dyr = None

    if hdr_dates:
        byr = hdr_dates.group(1)
        dyr = hdr_dates.group(2)
    else:
        # Find explicit death year in text (e.g. "died ... 1968" or "passed away ... 2015" or date in header)
        d_match = re.search(r'\b(?:died|passed away|departed this life|transitioned)[^\.\n]*?\b(18\d\d|19\d\d|20[0-2]\d)\b', block, re.IGNORECASE)
        if d_match:
            dyr = d_match.group(1)
            
        # Find explicit birth year in text (e.g. "born ... 1931")
        b_match = re.search(r'\b(?:born|birth)[^\.\n]*?\b(18\d\d|19\d\d|20[0-2]\d)\b', block, re.IGNORECASE)
        if b_match:
            byr = b_match.group(1)

        # Fallback 1: Calculate Birth Year if Death Year & Age are known
        if dyr and age and not byr:
            try:
                byr = str(int(dyr) - int(age))
            except ValueError:
                pass

        # Fallback 2: If all years in text, assign lowest as birth, highest as death (if valid age span)
        if not byr or not dyr:
            all_yrs = sorted([int(y) for y in re.findall(r'\b(18\d\d|19\d\d|20[0-2]\d)\b', block)])
            if len(all_yrs) >= 2:
                potential_b = str(all_yrs[0])
                potential_d = str(all_yrs[-1])
                span = int(potential_d) - int(potential_b)
                if 0 <= span <= 115:
                    if not byr: byr = potential_b
                    if not dyr: dyr = potential_d
            elif len(all_yrs) == 1 and not dyr:
                dyr = str(all_yrs[0])

    # Prevent inverted dates
    if byr and dyr:
        try:
            if int(byr) > int(dyr):
                # Inverted! Swap them or clear birth year
                if age and int(dyr) - int(age) > 1700:
                    byr = str(int(dyr) - int(age))
                else:
                    byr = None
        except ValueError:
            pass

    # Extract Cemetery
    cem_m = re.search(r'\b(?:Interment|Burial|Cemetery)\b[^\.\n]*', block, re.IGNORECASE)
    cemetery = cem_m.group(0).strip() if cem_m else None

    # Extract Source URL
    url_m = re.search(r'https?://[^\s\)]+', block)
    source_url = url_m.group(0) if url_m else None

    return dname or "Unknown Deceased", byr, dyr, age, cemetery, source_url

def rebuild_accurate_obituaries():
    conn = sqlite3.connect('preservation_output/genealogy_preservation.db')
    c = conn.cursor()

    # Pre-fetch persons map
    c.execute('SELECT person_id, name FROM persons')
    persons = c.fetchall()
    name_to_pid = {pname.strip().lower(): pid for pid, pname in persons}

    c.execute('SELECT filename, text_content FROM pages WHERE filename = "obit.htm" OR filename LIKE "obit-%"')
    pages = c.fetchall()

    c.execute('DELETE FROM person_obituaries')
    c.execute('DELETE FROM obituaries')

    all_obits = []
    seen_texts = set()

    for fn, txt_content in pages:
        txt = unescape(txt_content or '')
        if not txt or len(txt.strip()) < 50:
            continue
            
        if 'Full obits follow this list' in txt:
            # Monolithic page
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
                    # Deduplicate exact obituary blocks
                    sig = c_clean[:120].lower()
                    if sig not in seen_texts:
                        seen_texts.add(sig)
                        all_obits.append((fn, c_clean))
        else:
            # Multi-page documents
            chunks = re.split(r'\n{2,}|\r\n{2,}', txt)
            current_block = []
            for ch in chunks:
                c_clean = ch.strip()
                if not c_clean or 'Preserved Primary Document' in c_clean:
                    continue
                    
                is_new = bool(re.match(r'^[A-Z]{2,20}\:|^[A-Z][a-z]+\s+[A-Z][a-z]+\s+\d{4}', c_clean))
                if is_new and current_block:
                    full_txt = '\n\n'.join(current_block)
                    sig = full_txt[:120].lower()
                    if len(full_txt) > 80 and sig not in seen_texts:
                        seen_texts.add(sig)
                        all_obits.append((fn, full_txt))
                    current_block = [c_clean]
                else:
                    current_block.append(c_clean)
                    
            if current_block:
                full_txt = '\n\n'.join(current_block)
                sig = full_txt[:120].lower()
                if len(full_txt) > 80 and sig not in seen_texts:
                    seen_texts.add(sig)
                    all_obits.append((fn, full_txt))

    print(f'Extracted {len(all_obits)} unique individual obituaries.')

    obit_id = 0
    linked_count = 0

    for fn, obit_text in all_obits:
        name, byr, dyr, age, cemetery, source_url = parse_smart_obituary(obit_text)
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
    print(f'  ACCURATE OBITUARIES REBUILT!')
    print(f'  - Unique Obituaries Preserved: {obit_id}')
    print(f'  - Auto-linked to Person Profiles: {linked_count}')
    print(f'===========================================================')
    conn.close()

if __name__ == '__main__':
    rebuild_accurate_obituaries()
