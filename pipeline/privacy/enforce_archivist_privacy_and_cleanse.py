#!/usr/bin/env python3
"""
Enforce Archivist Privacy & Outbound Link Neutralization
========================================================
Implements Lynn Jackson's explicit archival directive:
"nothing links back to her old site directly or publicly.
We can use all photos and documents, just make sure it does not link back to lynn's original website."

Actions performed:
1. Purges 15 HTTP 500 error pages and 1 domain parking ad farm page (probt-s7.htm) from pages,
   their matching 16 orphaned source records, and deletes their static JSON files.
2. Removes all outbound URLs to Lynn Jackson's websites:
   - lynncjackson.com
   - mitsawokett.com
   - nativeamericansofdelawarestate.com
   - web.archive.org snapshots of these domains
   from database columns:
   - pages.wayback_url
   - mitsawokett_reports.report_url
   - photo_catalog.source_url
   - unified_photo_catalog.source_url
   - media_assets.wayback_url
   - obituaries.source_url
   - sources.url
   - ss_applications.image_url
3. Cleanses embedded HTML (<a href="...">) in pages.clean_html and mitsawokett_reports.clean_html:
   - Unwraps or replaces outbound hyperlinks to Lynn's domains with clean text/spans so no clickable external link remains.
4. Removes 0-byte database placeholder files in repository root.
5. Rebuilds SQLite FTS5 search index.
6. Refreshes canonical snapshot.
"""

import os
import re
import glob
import sqlite3
from bs4 import BeautifulSoup

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRESERVATION_DIR = os.path.join(PROJECT_ROOT, "preservation_output")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")
CANONICAL_DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation_canonical.db")

FRONTEND_PUBLIC = os.path.join(PROJECT_ROOT, "frontend", "public")
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")

ERROR_PAGE_IDS = [7, 11, 23, 57, 126, 128, 170, 190, 215, 216, 217, 218, 219, 221, 288, 319]
ERROR_SOURCE_IDS = [670, 671, 674, 693, 714, 716, 732, 740, 760, 761, 762, 763, 764, 766, 825, 841]

LYNN_DOMAINS = [
    "lynncjackson.com",
    "mitsawokett.com",
    "nativeamericansofdelawarestate.com",
    "www.lynncjackson.com",
    "www.mitsawokett.com",
    "www.nativeamericansofdelawarestate.com"
]

def is_lynn_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    return any(d in u for d in LYNN_DOMAINS)

def cleanse_html(html: str) -> str:
    if not html:
        return ""
    if not any(d in html.lower() for d in LYNN_DOMAINS):
        return html
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if is_lynn_url(a["href"]):
            # Replace <a> tag with its inner text or an unlinked span
            span = soup.new_tag("span", **{"class": "preserved-document-text"})
            span.string = a.get_text()
            a.replace_with(span)
    # Also strip any email icon links if present
    for img in soup.find_all("img", src=True):
        if any(tok in img["src"].lower() for tok in ["email.jpg", "email.fw.png", "ind-footer.gif"]):
            img.decompose()
    return str(soup)

def main():
    print("=== Starting Enforce Archivist Privacy & Outbound Link Neutralization ===")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Purge the 16 Error / Parked Ad Pages
    print("\nStep 1: Purging 15 HTTP 500 error pages and 1 domain parking ad farm page...")
    for pid in ERROR_PAGE_IDS:
        cursor.execute("SELECT filename FROM pages WHERE id = ?", (pid,))
        row = cursor.fetchone()
        if row:
            fn = row[0]
            print(f"  - Purging Page [{pid}]: {fn}")
            for d in [os.path.join(FRONTEND_PUBLIC, "api", "records"),
                      os.path.join(FRONTEND_DIST, "api", "records"),
                      os.path.join(FRONTEND_PUBLIC, "api", "transcriptions"),
                      os.path.join(FRONTEND_DIST, "api", "transcriptions")]:
                jf = os.path.join(d, f"{fn}.json")
                if os.path.exists(jf):
                    os.remove(jf)
                    print(f"    ✓ Deleted static file: {jf}")
            cursor.execute("DELETE FROM pages WHERE id = ?", (pid,))

    for sid in ERROR_SOURCE_IDS:
        cursor.execute("DELETE FROM sources WHERE source_id = ?", (sid,))
    print(f"  ✓ Purged {len(ERROR_PAGE_IDS)} pages and {len(ERROR_SOURCE_IDS)} source records.")

    # Step 2: Cleanse pages table (wayback_url and clean_html)
    print("\nStep 2: Cleansing pages table...")
    cursor.execute("SELECT id, wayback_url, clean_html FROM pages")
    pages_to_update = []
    for pid, wurl, html in cursor.fetchall():
        new_wurl = "" if is_lynn_url(wurl) else wurl
        new_html = cleanse_html(html)
        if new_wurl != wurl or new_html != html:
            pages_to_update.append((new_wurl, new_html, pid))
    
    for new_wurl, new_html, pid in pages_to_update:
        cursor.execute("UPDATE pages SET wayback_url = ?, clean_html = ? WHERE id = ?", (new_wurl, new_html, pid))
    print(f"  ✓ Cleaned {len(pages_to_update)} pages (outbound URLs and embedded links neutralized).")

    # Step 3: Cleanse mitsawokett_reports table
    print("\nStep 3: Cleansing mitsawokett_reports table...")
    cursor.execute("SELECT id, report_url, clean_html FROM mitsawokett_reports")
    reports_to_update = []
    for rid, rurl, html in cursor.fetchall():
        new_rurl = f"preserved_report_{rid}" if is_lynn_url(rurl) else rurl
        new_html = cleanse_html(html)
        if new_rurl != rurl or new_html != html:
            reports_to_update.append((new_rurl, new_html, rid))
    
    for new_rurl, new_html, rid in reports_to_update:
        cursor.execute("UPDATE mitsawokett_reports SET report_url = ?, clean_html = ? WHERE id = ?", (new_rurl, new_html, rid))
    print(f"  ✓ Cleaned {len(reports_to_update)} mitsawokett_reports (outbound URLs and embedded links neutralized).")

    # Step 4: Cleanse photo catalogs
    print("\nStep 4: Cleansing photo_catalog and unified_photo_catalog...")
    cursor.execute("SELECT photo_id, source_url FROM photo_catalog WHERE source_url IS NOT NULL AND source_url != ''")
    cnt_pc = 0
    for pid, surl in cursor.fetchall():
        if is_lynn_url(surl):
            cursor.execute("UPDATE photo_catalog SET source_url = '' WHERE photo_id = ?", (pid,))
            cnt_pc += 1

    cnt_upc = 0
    cursor.execute("SELECT photo_id, source_url FROM unified_photo_catalog WHERE source_url IS NOT NULL AND source_url != ''")
    for pid, surl in cursor.fetchall():
        if is_lynn_url(surl):
            cursor.execute("UPDATE unified_photo_catalog SET source_url = '' WHERE photo_id = ?", (pid,))
            cnt_upc += 1
    print(f"  ✓ Neutralized source_url in photo_catalog ({cnt_pc} rows) and unified_photo_catalog ({cnt_upc} rows).")

    # Step 5: Cleanse media_assets
    print("\nStep 5: Cleansing media_assets...")
    cursor.execute("SELECT id, wayback_url FROM media_assets WHERE wayback_url IS NOT NULL AND wayback_url != ''")
    cnt_ma = 0
    for mid, wurl in cursor.fetchall():
        if is_lynn_url(wurl):
            cursor.execute("UPDATE media_assets SET wayback_url = '' WHERE id = ?", (mid,))
            cnt_ma += 1
    print(f"  ✓ Neutralized wayback_url in media_assets ({cnt_ma} rows).")

    # Step 6: Cleanse obituaries
    print("\nStep 6: Cleansing obituaries...")
    cursor.execute("SELECT id, source_url FROM obituaries WHERE source_url IS NOT NULL AND source_url != ''")
    cnt_ob = 0
    for oid, surl in cursor.fetchall():
        if is_lynn_url(surl):
            cursor.execute("UPDATE obituaries SET source_url = '' WHERE id = ?", (oid,))
            cnt_ob += 1
    print(f"  ✓ Neutralized source_url in obituaries ({cnt_ob} rows).")

    # Step 7: Cleanse sources
    print("\nStep 7: Cleansing sources table...")
    cursor.execute("SELECT source_id, url FROM sources WHERE url IS NOT NULL AND url != ''")
    cnt_src = 0
    for sid, surl in cursor.fetchall():
        if is_lynn_url(surl):
            cursor.execute("UPDATE sources SET url = '' WHERE source_id = ?", (sid,))
            cnt_src += 1
    print(f"  ✓ Neutralized url in sources ({cnt_src} rows).")

    # Step 8: Cleanse ss_applications
    print("\nStep 8: Cleansing ss_applications...")
    cursor.execute("SELECT id, image_url FROM ss_applications WHERE image_url IS NOT NULL AND image_url != ''")
    cnt_ss = 0
    for ssid, iurl in cursor.fetchall():
        if is_lynn_url(iurl):
            cursor.execute("UPDATE ss_applications SET image_url = ? WHERE id = ?", (f"preserved_ss_app_{ssid}", ssid))
            cnt_ss += 1
    print(f"  ✓ Neutralized image_url in ss_applications ({cnt_ss} rows).")

    # Step 9: Remove 0-byte root placeholder files
    print("\nStep 9: Removing 0-byte database files in repository root...")
    for rf in ["database.db", "genealogy_archive.db", "genealogy.db"]:
        p = os.path.join(PROJECT_ROOT, rf)
        if os.path.exists(p) and os.path.getsize(p) == 0:
            os.remove(p)
            print(f"  ✓ Removed 0-byte placeholder: {rf}")

    conn.commit()

    # Step 10: Rebuilding SQLite FTS5 Index
    print("\nStep 10: Rebuilding SQLite FTS5 Corpus...")
    cursor.execute("DROP TABLE IF EXISTS fts_genealogy_corpus;")
    cursor.execute("""
        CREATE VIRTUAL TABLE fts_genealogy_corpus USING fts5(
            doc_id UNINDEXED,
            category UNINDEXED,
            title,
            content,
            tokenize = 'porter unicode61'
        );
    """)
    cursor.execute("""
        INSERT INTO fts_genealogy_corpus (doc_id, category, title, content)
        SELECT person_id, 'person', name,
               COALESCE(first_name, '') || ' ' || COALESCE(middle_name, '') || ' ' ||
               COALESCE(maiden_name, '') || ' ' || COALESCE(married_last_name, '') || ' ' ||
               COALESCE(birth_info, '') || ' ' || COALESCE(death_info, '') || ' ' || COALESCE(notes, '')
        FROM persons;
    """)
    cursor.execute("""
        INSERT INTO fts_genealogy_corpus (doc_id, category, title, content)
        SELECT id, 'page', title, text_content
        FROM pages;
    """)
    cursor.execute("""
        INSERT INTO fts_genealogy_corpus (doc_id, category, title, content)
        SELECT id, 'obituary', deceased_name, full_text
        FROM obituaries;
    """)
    cursor.execute("""
        INSERT INTO fts_genealogy_corpus (doc_id, category, title, content)
        SELECT photo_id, 'photo', normalized_filename,
               COALESCE(subject_names, '') || ' ' || COALESCE(surname, '') || ' ' ||
               COALESCE(given_names, '') || ' ' || COALESCE(transcription, '')
        FROM unified_photo_catalog;
    """)
    conn.commit()
    print("  ✓ FTS5 corpus successfully rebuilt.")

    # Step 11: Refresh canonical database snapshot
    print("\nStep 11: Refreshing Canonical Database Snapshot...")
    if os.path.exists(CANONICAL_DB_PATH):
        os.remove(CANONICAL_DB_PATH)
    conn.execute(f"VACUUM INTO '{CANONICAL_DB_PATH}';")
    conn.close()
    print(f"  ✓ Canonical snapshot created at {CANONICAL_DB_PATH} ({os.path.getsize(CANONICAL_DB_PATH) / (1024*1024):.2f} MB)")

    print("\nDatabase privacy neutralization complete.")

if __name__ == "__main__":
    main()
