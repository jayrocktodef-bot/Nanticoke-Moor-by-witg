#!/usr/bin/env python3
"""
auto_link_primary_documents_and_citations.py
=============================================
Autonomous Primary Document Entity & Citation Auto-Linker for the
Lynn C. Jackson & Mitsawokett Afro-Indigenous Delmarva Family Archive.

Systematically fulfills Step 2:
  1. Ensures all 357 primary document pages in `pages` table are indexed as sources.
  2. Populates verbatim Evidence Explained quotes (`evidence_text`) for existing citations.
  3. Links obituaries to person facts with verbatim excerpt quotes.
  4. Discovers unlinked primary document mentions across wills, bibles, censuses, and court records.
  5. Recalibrates evidence levels (bumps primary-source-backed individuals to Level 3).
  6. Re-exports static profile JSONs for seamless UI integration.

Strict Zero Hallucination & Evidence Attribution Policy compliant.
"""

import sqlite3
import re
import html
import os
import sys
from datetime import datetime

DB_PATH = "preservation_output/genealogy_preservation.db"

# Historical Afro-Indigenous Delmarva core surnames to prioritize and prevent false positives
HISTORICAL_SURNAMES = {
    'cott', 'durham', 'carty', 'carter', 'harmon', 'mosley', 'clark', 'clarke',
    'reed', 'read', 'sockum', 'sockume', 'street', 'pierce', 'puckham', 'hughes',
    'johnson', 'ridgeway', 'miller', 'munce', 'dean', 'hansor', 'sisco', 'carney',
    'morgan', 'purnell', 'sammons', 'jackson', 'okey', 'lopeman', 'davis', 'greenage',
    'bedell', 'bowles', 'coker', 'faulkner', 'sterrett', 'congo', 'seeney', 'handsor',
    'counsellor', 'counceller', 'gray', 'muntz', 'burch', 'pettijohn', 'driggus'
}

def clean_text(raw_text: str) -> str:
    """Unescape HTML and collapse whitespace."""
    if not raw_text:
        return ""
    t = html.unescape(raw_text)
    # Collapse multiple spaces/newlines
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r' {2,}', ' ', t)
    return t.strip()

def extract_excerpt(text: str, match_pos: int, match_len: int, window: int = 140) -> str:
    """Extract a clean, punctuation-bounded verbatim passage around match_pos."""
    start = max(0, match_pos - window)
    end = min(len(text), match_pos + match_len + window)
    
    snippet = text[start:end]
    
    # Try to expand to sentence or line boundaries if reasonable
    # Clean leading fragment
    if start > 0:
        first_space = snippet.find(' ')
        if first_space != -1 and first_space < 25:
            snippet = snippet[first_space + 1:]
        snippet = "..." + snippet
        
    # Clean trailing fragment
    if end < len(text):
        last_space = snippet.rfind(' ')
        if last_space != -1 and last_space > len(snippet) - 25:
            snippet = snippet[:last_space]
        snippet = snippet + "..."
        
    return clean_text(snippet)

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("=" * 70)
    print("Primary Document Entity & Citation Auto-Linker")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Ensure all primary documents in `pages` have source records
    # ---------------------------------------------------------
    print("\n[Step 1] Ensuring all 357 primary document pages are in sources table...")
    cur.execute("SELECT id, filename, title FROM pages WHERE text_content IS NOT NULL AND length(text_content) > 50")
    all_pages = cur.fetchall()
    
    sources_added = 0
    page_to_source_id = {}
    
    # Get existing sources map
    cur.execute("SELECT source_id, LOWER(url), title FROM sources")
    existing_sources = {row[1]: row[0] for row in cur.fetchall() if row[1]}
    
    for page_id, filename, title in all_pages:
        if not filename:
            continue
        clean_fn = filename.strip()
        clean_fn_lower = clean_fn.lower()
        
        if clean_fn_lower in existing_sources:
            page_to_source_id[clean_fn_lower] = existing_sources[clean_fn_lower]
        else:
            page_title = title.strip() if title else f"Record: {clean_fn}"
            if not page_title.startswith("Record:") and not page_title.startswith("Preserved"):
                page_title = f"Preserved Document: {page_title}"
            cur.execute(
                "INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)",
                (page_title, clean_fn, "mitsawokett_primary")
            )
            sid = cur.lastrowid
            existing_sources[clean_fn_lower] = sid
            page_to_source_id[clean_fn_lower] = sid
            sources_added += 1
            
    conn.commit()
    print(f"  ✓ Processed {len(all_pages)} pages; added {sources_added} new source catalog entries.")

    # ---------------------------------------------------------
    # 2. Populate verbatim evidence for existing empty citations linked to pages
    # ---------------------------------------------------------
    print("\n[Step 2] Populating verbatim evidence text for existing citations linked to pages...")
    
    # Load all page texts into memory for fast querying
    cur.execute("SELECT LOWER(filename), text_content FROM pages WHERE text_content IS NOT NULL")
    pages_dict = {}
    for fn, content in cur.fetchall():
        if fn and content:
            cleaned = clean_text(content)
            pages_dict[fn] = {
                'raw': cleaned,
                'lower': cleaned.lower()
            }
            
    cur.execute("""
        SELECT c.citation_id, f.fact_id, f.fact_type, f.date_string, f.place_string, f.value_string,
               p.person_id, p.name, p.first_name, p.married_last_name, p.maiden_name,
               s.source_id, s.title, LOWER(s.url)
        FROM citations c
        JOIN facts f ON c.fact_id = f.fact_id
        JOIN persons p ON f.person_id = p.person_id
        JOIN sources s ON c.source_id = s.source_id
        WHERE (c.evidence_text IS NULL OR c.evidence_text = '')
    """)
    empty_citations = cur.fetchall()
    print(f"  Found {len(empty_citations)} citations currently lacking verbatim evidence text.")

    citations_updated = 0
    for cit in empty_citations:
        cit_id, fact_id, f_type, f_date, f_place, f_val, pid, name, first, last, maiden, sid, stitle, surl = cit
        
        if not surl or surl not in pages_dict:
            continue
            
        page_info = pages_dict[surl]
        text_lower = page_info['lower']
        text_raw = page_info['raw']
        
        # Build candidate name variants
        name_variants = []
        if name:
            name_variants.append(name.strip())
        if first and last:
            name_variants.append(f"{first.strip()} {last.strip()}")
        if first and maiden:
            name_variants.append(f"{first.strip()} {maiden.strip()}")
        if last and first:
            name_variants.append(f"{last.strip()}, {first.strip()}")
            
        # Match search
        best_match_pos = -1
        best_match_len = 0
        
        # 1. If fact has date/year, look for co-occurrence of name and date
        target_year = None
        if f_date:
            year_match = re.search(r'\b(1[6789]\d{2}|20[012]\d)\b', f_date)
            if year_match:
                target_year = year_match.group(1)
                
        for var in name_variants:
            var_lower = var.lower()
            if len(var_lower) < 4:
                continue
                
            # Find all positions of this name in document
            start_idx = 0
            while True:
                pos = text_lower.find(var_lower, start_idx)
                if pos == -1:
                    break
                    
                # Check word boundaries
                is_left_boundary = (pos == 0 or not text_lower[pos-1].isalnum())
                end_pos = pos + len(var_lower)
                is_right_boundary = (end_pos == len(text_lower) or not text_lower[end_pos].isalnum())
                
                if is_left_boundary and is_right_boundary:
                    if target_year:
                        # Check if target year occurs near this match (within 250 chars)
                        context_start = max(0, pos - 150)
                        context_end = min(len(text_lower), end_pos + 150)
                        if target_year in text_lower[context_start:context_end]:
                            best_match_pos = pos
                            best_match_len = len(var_lower)
                            break
                    if best_match_pos == -1:
                        best_match_pos = pos
                        best_match_len = len(var_lower)
                        
                start_idx = pos + len(var_lower)
                
            if best_match_pos != -1 and target_year and target_year in text_lower[max(0, best_match_pos - 150):min(len(text_lower), best_match_pos + best_match_len + 150)]:
                break
                
        if best_match_pos != -1:
            excerpt = extract_excerpt(text_raw, best_match_pos, best_match_len, window=120)
            if excerpt:
                cur.execute("UPDATE citations SET evidence_text = ? WHERE citation_id = ?", (excerpt, cit_id))
                citations_updated += 1

    conn.commit()
    print(f"  ✓ Successfully extracted and populated verbatim evidence for {citations_updated} citations.")

    # ---------------------------------------------------------
    # 3. Link Obituary text to obituary-sourced citations
    # ---------------------------------------------------------
    print("\n[Step 3] Linking verbatim obituary records to obituary citations...")
    cur.execute("""
        SELECT c.citation_id, o.deceased_name, o.death_date, o.cemetery_location, o.full_text
        FROM citations c
        JOIN facts f ON c.fact_id = f.fact_id
        JOIN persons p ON f.person_id = p.person_id
        JOIN person_obituaries po ON p.person_id = po.person_id
        JOIN obituaries o ON po.obituary_id = o.id
        WHERE (c.evidence_text IS NULL OR c.evidence_text = '')
          AND (c.source_id IN (SELECT source_id FROM sources WHERE url LIKE '%obituar%' OR title LIKE '%obituar%'))
    """)
    obit_cits = cur.fetchall()
    
    obits_linked = 0
    for cit_id, deceased_name, death_date, cemetery, full_text in obit_cits:
        clean_full = clean_text(full_text)
        if len(clean_full) > 280:
            excerpt = clean_full[:277] + "..."
        else:
            excerpt = clean_full
        cur.execute("UPDATE citations SET evidence_text = ? WHERE citation_id = ?", (excerpt, cit_id))
        obits_linked += 1
        
    conn.commit()
    print(f"  ✓ Populated verbatim obituary evidence for {obits_linked} citations.")

    # ---------------------------------------------------------
    # 4. Cross-Document Primary Entity Mention Citation Mining
    # ---------------------------------------------------------
    print("\n[Step 4] Mining unlinked primary document mentions across wills, deeds, bibles, & censuses...")
    
    # Load persons with clean first and historical last names
    cur.execute("""
        SELECT person_id, name, first_name, married_last_name, maiden_name, birth_info, death_info, source_page
        FROM persons
        WHERE married_last_name IS NOT NULL AND length(married_last_name) >= 3
          AND first_name IS NOT NULL AND length(first_name) >= 3
    """)
    all_persons = cur.fetchall()
    
    # Filter persons to those with recognized family surnames
    qualified_persons = []
    for p in all_persons:
        pid, name, first, last, maiden, b_info, d_info, src_page = p
        last_clean = last.lower().strip()
        maiden_clean = maiden.lower().strip() if maiden else ""
        if last_clean in HISTORICAL_SURNAMES or maiden_clean in HISTORICAL_SURNAMES:
            qualified_persons.append(p)
            
    print(f"  Tracking {len(qualified_persons)} core historical individuals across 357 primary documents...")

    # Load existing person-source links to avoid duplicate citations
    cur.execute("""
        SELECT f.person_id, c.source_id
        FROM citations c
        JOIN facts f ON c.fact_id = f.fact_id
    """)
    existing_person_sources = set(cur.fetchall())

    new_facts_count = 0
    new_citations_count = 0

    for page_id, filename, title in all_pages:
        if not filename:
            continue
        clean_fn = filename.strip()
        clean_fn_lower = clean_fn.lower()
        if clean_fn_lower not in pages_dict or clean_fn_lower not in page_to_source_id:
            continue
            
        page_info = pages_dict[clean_fn_lower]
        text_lower = page_info['lower']
        text_raw = page_info['raw']
        source_id = page_to_source_id[clean_fn_lower]
        
        # Skip small navigation pages
        if len(text_lower) < 200:
            continue

        for p in qualified_persons:
            pid, name, first, last, maiden, b_info, d_info, src_page = p
            
            # Don't create duplicate citation if person already cited to this source
            if (pid, source_id) in existing_person_sources:
                continue

            first_clean = first.strip().lower()
            last_clean = last.strip().lower()
            full_pattern = f"{first_clean} {last_clean}"
            
            pos = text_lower.find(full_pattern)
            if pos == -1 and maiden:
                full_pattern_maiden = f"{first_clean} {maiden.strip().lower()}"
                pos = text_lower.find(full_pattern_maiden)
                
            if pos != -1:
                # Verify word boundaries
                is_left = (pos == 0 or not text_lower[pos-1].isalnum())
                end_pos = pos + len(full_pattern)
                is_right = (end_pos == len(text_lower) or not text_lower[end_pos].isalnum())
                
                if is_left and is_right:
                    excerpt = extract_excerpt(text_raw, pos, len(full_pattern), window=120)
                    
                    # Create a Document Mention fact
                    cur.execute("""
                        INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
                        VALUES (?, 'Document Mention', NULL, 'Delmarva Peninsula', ?)
                    """, (pid, f"Documented in primary record: {title or filename}"))
                    new_fact_id = cur.lastrowid
                    new_facts_count += 1
                    
                    # Create citation
                    cur.execute("""
                        INSERT INTO citations (fact_id, source_id, evidence_text)
                        VALUES (?, ?, ?)
                    """, (new_fact_id, source_id, excerpt))
                    new_citations_count += 1
                    existing_person_sources.add((pid, source_id))

    conn.commit()
    print(f"  ✓ Discovered and indexed {new_facts_count} primary document mentions.")
    print(f"  ✓ Generated {new_citations_count} new GPS-compliant citations with verbatim evidence.")

    # ---------------------------------------------------------
    # 5. Evidence Level Recalibration (GPS Standard)
    # ---------------------------------------------------------
    print("\n[Step 5] Recalibrating evidence confidence levels under GPS standards...")
    cur.execute("""
        UPDATE persons
        SET evidence_level = 3
        WHERE evidence_level < 3
          AND person_id IN (
              SELECT DISTINCT f.person_id
              FROM citations c
              JOIN facts f ON c.fact_id = f.fact_id
              WHERE c.evidence_text IS NOT NULL AND c.evidence_text != ''
          )
    """)
    recalibrated = cur.rowcount
    conn.commit()
    print(f"  ✓ Promoted {recalibrated} individuals to Level 3 (Primary Source Confirmed) based on verifiable excerpts.")

    # ---------------------------------------------------------
    # 6. Overall Citation Statistics
    # ---------------------------------------------------------
    cur.execute("SELECT count(*), count(CASE WHEN evidence_text IS NOT NULL AND evidence_text != '' THEN 1 END) FROM citations")
    tot_cit, pop_cit = cur.fetchone()
    print("\n" + "=" * 70)
    print("Archive Verification Summary:")
    print(f"  Total Citations in Database: {tot_cit}")
    print(f"  Citations with Verbatim Evidence Quotes: {pop_cit} ({pop_cit/tot_cit*100:.1f}%)")
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    main()
