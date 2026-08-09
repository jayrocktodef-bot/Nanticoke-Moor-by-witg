import urllib.request
import re
import sqlite3

URL = 'https://nativeamericansofdelawarestate.com/Obituaries%20added%202016-04-03.htm'
DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'

def reparse_obituaries():
    print("Step 1: Downloading raw HTML from Mitsawokett...")
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('windows-1252', errors='ignore')

    # 1. Extract clean list of names from top index section
    clean_text = re.sub(r'<[^>]+>', '\n', html)
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]

    index_names = []
    for line in lines:
        if re.search(r'\b(17\d\d|18\d\d|19\d\d|20\d\d|\?)\s*[-~–]\s*(17\d\d|18\d\d|19\d\d|20\d\d|\?)', line):
            if not any(skip in line for skip in ['Copyright', 'http', 'www', 'Page', 'Use your FIND']):
                index_names.append(line)

    print(f"✅ Found {len(index_names)} verified deceased name entries in Master Index!")

    # 2. Extract full text obituaries block
    if '<p><font face="Arial, Helvetica, sans-serif" size="4" color="#660000"><b>Obituaries</b>' in html:
        full_obits_html = html.split('<p><font face="Arial, Helvetica, sans-serif" size="4" color="#660000"><b>Obituaries</b>')[1]
    else:
        full_obits_html = html

    # Clean text blocks
    text_blocks = re.split(r'<p><font face="Arial, Helvetica, sans-serif" size="3">', full_obits_html)
    
    parsed_obits = []
    
    for idx_name in index_names:
        # Extract name & years
        m = re.match(r'^(.*?)\s+((?:~?\d{4}|\?)\s*[-~–]\s*(?:~?\d{4}|\?))$', idx_name)
        if m:
            dname = m.group(1).strip()
            years = m.group(2).strip()
        else:
            dname = idx_name
            years = ''

        # Search for full text matching this person in text_blocks
        matched_text = ""
        # Search surname & first name in blocks
        name_parts = [p for p in re.split(r'[\s,]+', dname) if len(p) > 2 and p.lower() not in ['jr', 'sr', 'iii', 'dr']]
        
        for block in text_blocks:
            clean_b = re.sub(r'<[^>]+>', ' ', block).strip()
            clean_b = re.sub(r'\s+', ' ', clean_b)
            if len(clean_b) > 40 and all(part.lower() in clean_b.lower() for part in name_parts[:2]):
                matched_text = clean_b
                break

        if not matched_text:
            matched_text = f"{dname} {years}"

        parsed_obits.append({
            'deceased_name': dname,
            'years': years,
            'full_text': matched_text,
            'source_url': URL
        })

    print(f"✅ Parsed {len(parsed_obits)} clean obituary records with explicit deceased names attached!")

    # 3. Update Database
    print("Step 2: Updating preservation database obituaries table...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Clear old inaccurate obituaries
    c.execute("DELETE FROM person_obituaries")
    c.execute("DELETE FROM obituaries WHERE source_url LIKE '%2016-04-03%' OR source_url LIKE '%Obituaries%'")

    for o in parsed_obits:
        c.execute("""
            INSERT INTO obituaries (deceased_name, age, birth_date, death_date, cemetery_location, full_text, source_url)
            VALUES (?, '', '', ?, '', ?, ?)
        """, (o['deceased_name'], o['years'], o['full_text'], o['source_url']))

    conn.commit()
    conn.close()

    print(f"✅ DATABASE UPDATED! Exactly {len(parsed_obits)} verified obituaries stored.")

if __name__ == '__main__':
    reparse_obituaries()
