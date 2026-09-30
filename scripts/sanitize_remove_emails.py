#!/usr/bin/env python3
"""
Archive Privacy & Email Sanitization Routine
============================================
Exhaustively removes all personal, contributor, subscriber, and contact
email addresses and mailto artifacts across the entire Lynn Jackson archive:
1. SQLite Database: `pages`, `mitsawokett_reports`, `obituaries`, `citations`, `fts_genealogy_corpus`
2. XML Profiles & GedcomX Archives: `preservation_output/profiles/*.xml`, `preservation_output/genealogy_archive.xml`
3. Audit Reports: `disconnected_surnames_report.md`, `non_core_family_audit.md`
4. Preserves OAIS RFC 8493 BagIt Fixity Invariants.
"""

import os
import re
import sys
import glob
import sqlite3
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_preservation.db")
CANONICAL_DB_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_preservation_canonical.db")
ARCHIVE_XML_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_archive.xml")
PROFILES_DIR = os.path.join(PROJECT_ROOT, "preservation_output", "profiles")

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)

def sanitize_text(text: str) -> str:
    """Sanitize email addresses, mailto tags, and contact artifacts from text or HTML."""
    if not text:
        return text

    # 1. Clean mailto anchors where inner text is a person or contributor name
    # e.g., <a href="mailto:tireman37@peoplepc.com">Charles C. Counceller</a> -> Charles C. Counceller
    text = re.sub(r'<a\s+href=[\"\x27]mailto:[^\"\x27]+[\"\x27]>([^<@]+)</a>', r'\1', text, flags=re.IGNORECASE)

    # 2. Clean mailto anchors where inner text is an email address itself or contact prompt
    # e.g., <a href="mailto:ptj15m@gowebway.com">ptj15m@gowebway.com</a> -> ''
    text = re.sub(r'<a\s+href=[\"\x27]mailto:[^\"\x27]+[\"\x27]>.*?</a>', '', text, flags=re.IGNORECASE)

    # 3. Clean [mailto:foo@bar.com] or (mailto:foo@bar.com)
    text = re.sub(r'\[\s*mailto:[^\]]+\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(\s*mailto:[^\)]+\)', '', text, flags=re.IGNORECASE)

    # 4. Clean raw mailto: links
    text = re.sub(r'mailto:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '', text, flags=re.IGNORECASE)

    # 5. Clean email addresses enclosed in parens, brackets, or angle brackets
    text = re.sub(r'[\(<\[]\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s*[\)>\]]', '', text, flags=re.IGNORECASE)

    # 6. Any remaining email pattern
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\.?', '', text, flags=re.IGNORECASE)

    # 7. Clean up empty labels like Email <br/>, Email </font>, Email:
    text = re.sub(r'\b(?:Email|E-mail)\s*(?:<[^>]+>\s*)*\s*<br\s*/?>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:Email|E-mail)\s*[:\-]?\s*(?=\n|<br|</span>|</font|</p>|$)', '', text, flags=re.IGNORECASE)

    # 8. Clean up 'From: (John C. Carter)' -> 'From: John C. Carter'
    text = re.sub(r'From:\s+\(([^\)]+)\)', r'From: \1', text)

    # 9. Clean up dangling 'or' before punctuation/end of sentence (e.g. '...delmarvaobits.com or .')
    text = re.sub(r'\s+or\s+(?=\.|$)', '', text)

    # 10. Clean up CC: line if CC email was stripped
    text = re.sub(r'CC:\s*(?=\n|<|$)', '', text)

    # 11. Clean up residual Geocities navigation artifacts "EMAIL US" / "EMAIL"
    text = re.sub(r'<h3[^>]*>\s*EMAIL\s+US\s*</h3>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'MAIN\s+MENU\s+EMAIL\s+US', 'MAIN MENU', text, flags=re.IGNORECASE)
    text = re.sub(r'\bEMAIL\s+US\b', '', text, flags=re.IGNORECASE)

    # 12. Normalize multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def sanitize_database(conn: sqlite3.Connection):
    """Sanitize all SQLite tables containing emails."""
    cur = conn.cursor()
    print("Step 1: Sanitizing SQLite Database...")

    # 1a. Table: pages
    print("  -> Sanitizing table: pages...")
    cur.execute("SELECT id, clean_html, text_content FROM pages")
    pages = cur.fetchall()
    updated_pages = 0
    for pid, c_html, t_content in pages:
        new_html = sanitize_text(c_html)
        new_text = sanitize_text(t_content)
        if new_html != c_html or new_text != t_content:
            cur.execute("""
                UPDATE pages
                SET clean_html = ?, text_content = ?
                WHERE id = ?
            """, (new_html, new_text, pid))
            updated_pages += 1
    print(f"     Updated {updated_pages} rows in pages.")

    # 1b. Table: mitsawokett_reports
    print("  -> Sanitizing table: mitsawokett_reports...")
    cur.execute("SELECT id, summary_text, clean_html FROM mitsawokett_reports")
    reports = cur.fetchall()
    updated_reports = 0
    for rid, summary, c_html in reports:
        new_summary = sanitize_text(summary)
        new_html = sanitize_text(c_html)
        if new_summary != summary or new_html != c_html:
            cur.execute("""
                UPDATE mitsawokett_reports
                SET summary_text = ?, clean_html = ?
                WHERE id = ?
            """, (new_summary, new_html, rid))
            updated_reports += 1
    print(f"     Updated {updated_reports} rows in mitsawokett_reports.")

    # 1c. Table: obituaries
    print("  -> Sanitizing table: obituaries...")
    cur.execute("SELECT id, full_text, clean_html FROM obituaries")
    obits = cur.fetchall()
    updated_obits = 0
    for oid, f_text, c_html in obits:
        new_text = sanitize_text(f_text)
        new_html = sanitize_text(c_html)
        if new_text != f_text or new_html != c_html:
            cur.execute("""
                UPDATE obituaries
                SET full_text = ?, clean_html = ?
                WHERE id = ?
            """, (new_text, new_html, oid))
            updated_obits += 1
    print(f"     Updated {updated_obits} rows in obituaries.")

    # 1d. Table: citations
    print("  -> Sanitizing table: citations...")
    cur.execute("SELECT citation_id, evidence_text FROM citations")
    cits = cur.fetchall()
    updated_cits = 0
    for cid, ev_text in cits:
        new_ev = sanitize_text(ev_text)
        if new_ev != ev_text:
            cur.execute("""
                UPDATE citations
                SET evidence_text = ?
                WHERE citation_id = ?
            """, (new_ev, cid))
            updated_cits += 1
    print(f"     Updated {updated_cits} rows in citations.")

    # 1e. Rebuild SQLite FTS5 table
    print("  -> Rebuilding SQLite FTS5 table: fts_genealogy_corpus...")
    cur.execute("DROP TABLE IF EXISTS fts_genealogy_corpus")
    cur.execute("""
        CREATE VIRTUAL TABLE fts_genealogy_corpus USING fts5(
            doc_type UNINDEXED,
            source_id UNINDEXED,
            title,
            full_text,
            metadata,
            tokenize = 'porter unicode61'
        )
    """)

    cur.execute("""
        SELECT id, deceased_name, full_text, surviving_kin, birth_date, death_date, cemetery_location
        FROM obituaries
    """)
    for oid, dname, ftext, kin, bdate, ddate, cem in cur.fetchall():
        meta = f"Born: {bdate or ''} | Died: {ddate or ''} | Cemetery: {cem or ''} | Kin: {kin or ''}"
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('obituary', ?, ?, ?, ?)
        """, (str(oid), dname or "", ftext or "", meta))

    cur.execute("SELECT filename, title, text_content FROM pages")
    for fn, title, ctext in cur.fetchall():
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('page', ?, ?, ?, ?)
        """, (fn, title or fn, ctext or "", f"Filename: {fn}"))

    cur.execute("SELECT id, surname, given_names, maiden_or_full_name FROM ss_applications")
    for sid, sname, gnames, mname in cur.fetchall():
        full_n = f"{gnames or ''} {sname or ''}".strip()
        meta = f"Surname: {sname or ''} | Given: {gnames or ''} | Maiden/Full: {mname or ''}"
        cur.execute("""
            INSERT INTO fts_genealogy_corpus(doc_type, source_id, title, full_text, metadata)
            VALUES ('ss_application', ?, ?, ?, ?)
        """, (str(sid), full_n, f"Social Security Application for {full_n}. Name: {mname or full_n}.", meta))

    conn.commit()
    print("  -> FTS5 table successfully rebuilt with sanitized corpus.")


def sanitize_xml_profiles():
    """Sanitize XML profiles and GedcomX master archive."""
    print("Step 2: Sanitizing XML profiles and master archive...")
    
    # Sanitize master archive
    if os.path.exists(ARCHIVE_XML_PATH):
        with open(ARCHIVE_XML_PATH, "r", encoding="utf-8") as f:
            xml_content = f.read()
        
        # Specific known GedcomX person name entries with email artifacts
        new_xml = xml_content
        new_xml = re.sub(r'<fullText>Helen Pierce \[mailto:pierceh@gmail\.com\]</fullText>',
                         '<fullText>Helen Pierce</fullText>', new_xml)
        new_xml = re.sub(r'<fullText>Lisa KURECZ@aol\.com</fullText>',
                         '<fullText>Lisa</fullText>', new_xml)
        new_xml = re.sub(r'<fullText>Nancy wcranden@earthlink\.net</fullText>',
                         '<fullText>Nancy</fullText>', new_xml)
        new_xml = re.sub(r'<fullText>CC: lightningfawn@com\.net</fullText>',
                         '<fullText>[Unidentified Correspondent]</fullText>', new_xml)
        
        # General email pattern pass in case of others
        new_xml = EMAIL_REGEX.sub('', new_xml)

        if new_xml != xml_content:
            with open(ARCHIVE_XML_PATH, "w", encoding="utf-8") as f:
                f.write(new_xml)
            print("  -> Sanitized preservation_output/genealogy_archive.xml")

    # Sanitize individual person profiles
    for prof_path in glob.glob(os.path.join(PROFILES_DIR, "*.xml")):
        with open(prof_path, "r", encoding="utf-8") as f:
            content = f.read()
        if EMAIL_REGEX.search(content) or "mailto:" in content:
            cleaned = content
            cleaned = re.sub(r'<fullText>Helen Pierce \[mailto:pierceh@gmail\.com\]</fullText>',
                             '<fullText>Helen Pierce</fullText>', cleaned)
            cleaned = re.sub(r'<fullText>Lisa KURECZ@aol\.com</fullText>',
                             '<fullText>Lisa</fullText>', cleaned)
            cleaned = re.sub(r'<fullText>Nancy wcranden@earthlink\.net</fullText>',
                             '<fullText>Nancy</fullText>', cleaned)
            cleaned = re.sub(r'<fullText>CC: lightningfawn@com\.net</fullText>',
                             '<fullText>[Unidentified Correspondent]</fullText>', cleaned)
            cleaned = EMAIL_REGEX.sub('', cleaned)
            with open(prof_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
            print(f"  -> Sanitized profile: {os.path.basename(prof_path)}")


def sanitize_markdown_reports():
    """Sanitize markdown audit reports that referenced scraped emails."""
    print("Step 3: Sanitizing Markdown Audit Reports...")
    reports = [
        os.path.join(PROJECT_ROOT, "disconnected_surnames_report.md"),
        os.path.join(PROJECT_ROOT, "non_core_family_audit.md"),
    ]
    for rep in reports:
        if os.path.exists(rep):
            with open(rep, "r", encoding="utf-8") as f:
                content = f.read()
            if EMAIL_REGEX.search(content) or "mailto:" in content:
                cleaned = content
                cleaned = re.sub(r'\[mailto:pierceh@gmail\.com\]', '[email redacted]', cleaned)
                cleaned = EMAIL_REGEX.sub('[email redacted]', cleaned)
                with open(rep, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                print(f"  -> Sanitized report: {os.path.basename(rep)}")


def refresh_canonical_database(conn: sqlite3.Connection):
    """Vacuum into canonical database snapshot to maintain OAIS fixity invariant."""
    print("Step 4: Refreshing Canonical Database Snapshot...")
    if os.path.exists(CANONICAL_DB_PATH):
        os.remove(CANONICAL_DB_PATH)
    cur = conn.cursor()
    cur.execute(f"VACUUM INTO '{CANONICAL_DB_PATH}'")
    print(f"  -> Successfully created canonical snapshot at {CANONICAL_DB_PATH}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        sanitize_database(conn)
        sanitize_xml_profiles()
        sanitize_markdown_reports()
        refresh_canonical_database(conn)
    finally:
        conn.close()

    print("Step 5: Regenerating Static JSON APIs & Manifests...")
    # Run export_static_build_for_vercel.py to re-export sanitized static API payloads
    export_script = os.path.join(PROJECT_ROOT, "export_static_build_for_vercel.py")
    subprocess.run([sys.executable, export_script], cwd=PROJECT_ROOT, check=True)

    # Regenerate BagIt Package
    bagit_script = os.path.join(PROJECT_ROOT, "scripts", "generate_bagit_package.py")
    subprocess.run([sys.executable, bagit_script], cwd=PROJECT_ROOT, check=True)

    # Verify BagIt Fixity
    verify_script = os.path.join(PROJECT_ROOT, "scripts", "verify_bagit_fixity.py")
    subprocess.run([sys.executable, verify_script], cwd=PROJECT_ROOT, check=True)

    print("\nSanitization and fixity verification complete.")

if __name__ == "__main__":
    main()
