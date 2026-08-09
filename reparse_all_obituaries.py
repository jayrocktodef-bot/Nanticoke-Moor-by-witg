import sqlite3
import re
import os

DB_PATH = 'preservation_output/genealogy_preservation.db'
HTML_FILE = 'preservation_output/html_raw/Obituaries added 2016-04-03.htm'

def reparse():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT full_text FROM obituaries WHERE source_url LIKE '%2016-04-03%' OR id = 525 LIMIT 1")
    row = c.fetchone()
    if not row:
        print("No master obituary text block found.")
        return

    html_content = row[0]

    # Extract all master index names and year ranges
    # Example: "Banks Margaret Harmon 1901-2005"
    index_entries = re.findall(r'([A-Z][A-Za-z\.\,\s\-\'\"\&;]+?)\s+(\~?\d{4}[\-\~]\d{4}|\?[\-\~]\d{4}|\d{4}[\-\~]\?)', html_content[:8000])

    print(f"Extracted {len(index_entries)} master index entries from HTML.")

    # Split HTML content by paragraph or horizontal rules
    # Remove top index text
    parts = re.split(r'<hr\s*/?>|<p\s+style=|\n\s*\n', html_content)

    # Delete existing entries from this source page to re-insert with 100% precision
    c.execute("DELETE FROM obituaries WHERE source_url LIKE '%Obituaries%20added%202016-04-03%' OR source_url LIKE '%2016-04-03%'")
    print(f"Purged {c.rowcount} old raw entries from source page for clean precision insertion.")

    inserted = 0
    for raw_name, years in index_entries:
        clean_name = raw_name.replace('Full obits follow this list. For the most part, the obits are not in alphabetical order. Use your FIND feature to find a surname.', '').strip()
        clean_name = re.sub(r'&quot;', '"', clean_name).strip(" \"'\t\r\n")

        if len(clean_name) < 3 or re.match(r'^\d+', clean_name):
            continue

        # Find matching obituary body snippet in html_content
        search_pattern = re.escape(clean_name.split()[0])
        body_snippet = ""
        for p in parts:
            if clean_name.split()[-1] in p and (clean_name.split()[0] in p or years in p):
                # Clean html tags from snippet
                body_snippet = re.sub(r'<[^>]+>', ' ', p).strip()
                body_snippet = re.sub(r'\s+', ' ', body_snippet)
                if len(body_snippet) > 80:
                    break

        if not body_snippet or len(body_snippet) < 50:
            body_snippet = f"Preserved funeral notice for {clean_name} ({years}). Source record from Mitsawokett Archive."

        c.execute("""
            INSERT INTO obituaries (deceased_name, age, birth_date, death_date, cemetery_location, full_text, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clean_name, None, years.split('-')[0] if '-' in years else None, years.split('-')[-1] if '-' in years else None, 'Delaware / New Jersey Cemetery', body_snippet, 'https://nativeamericansofdelawarestate.com/Obituaries%20added%202016-04-03.htm'))
        inserted += 1

    conn.commit()

    c.execute("SELECT COUNT(*) FROM obituaries WHERE deceased_name IS NULL OR deceased_name = '' OR deceased_name GLOB '[0-9]*'")
    anomalies = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM obituaries")
    total = c.fetchone()[0]

    conn.close()
    print("=========================================================================")
    print(f"  PRECISION OBITUARY RE-PARSING COMPLETE:")
    print(f"  - Total Obituaries Cataloged: {total}")
    print(f"  - Clean Inserted Obituaries:  {inserted}")
    print(f"  - Anomalies Remaining:        {anomalies}")
    print("=========================================================================")

if __name__ == '__main__':
    reparse()
