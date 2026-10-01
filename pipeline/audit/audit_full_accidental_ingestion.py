#!/usr/bin/env python3
"""
Full Archive Accidental Ingestion Audit Script
=============================================
Performs a rigorous, multi-layered audit across all tables in genealogy_preservation.db
to detect any accidental ingestions, scrapings of non-genealogical assets,
grammatical fragment entities, or web UI artifacts.
"""

import os
import sys
import sqlite3
import re
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRESERVATION_DIR = os.path.join(PROJECT_ROOT, "preservation_output")
DB_PATH = os.path.join(PRESERVATION_DIR, "genealogy_preservation.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

findings = {
    "pages": [],
    "photos": [],
    "media_assets": [],
    "persons": [],
    "obituaries": [],
    "document_records": [],
    "sources": [],
}

# -------------------------------------------------------------
# 1. AUDIT PAGES
# -------------------------------------------------------------
print("Auditing pages...")
cursor.execute("SELECT id, filename, title, length(text_content) as tlen, text_content, substr(clean_html, 1, 12) as html_start FROM pages")
suspicious_keywords = [
    "404 not found", "error 404", "apache", "nginx", "parked", "domain for sale",
    "buy this domain", "under construction", "sponsored listings", "search results",
    "godaddy", "sedo", "click here to enter", "top searches", "related links"
]

for p in cursor.fetchall():
    tcontent = (p["text_content"] or "").lower()
    title = (p["title"] or "").lower()
    fn = p["filename"]
    
    # Check binary signature
    hstart = p["html_start"] or ""
    if any(hstart.startswith(sig) for sig in ["GIF", "\x89PNG", "\xff\xd8", "%PDF"]):
        findings["pages"].append({
            "id": p["id"],
            "filename": fn,
            "issue": f"Binary file header in HTML column: {repr(hstart)}"
        })
        
    # Check suspicious keywords
    for kw in suspicious_keywords:
        if kw in title or kw in tcontent[:300]:
            findings["pages"].append({
                "id": p["id"],
                "filename": fn,
                "title": p["title"],
                "issue": f"Matched suspicious keyword: '{kw}'"
            })
            break
            
    # Check short / empty pages
    if (p["tlen"] or 0) < 60:
        words = len((p["text_content"] or "").split())
        findings["pages"].append({
            "id": p["id"],
            "filename": fn,
            "title": p["title"],
            "issue": f"Extremely short page: {p['tlen']} chars, {words} words. Content: {(p['text_content'] or '').strip()[:100]}"
        })

# -------------------------------------------------------------
# 2. AUDIT PHOTOS & MEDIA
# -------------------------------------------------------------
print("Auditing photos and media...")
cursor.execute("""
    SELECT photo_id, normalized_filename, original_filename, local_image_path, file_size_bytes, category, subject_names
    FROM unified_photo_catalog
""")

ui_name_patterns = [
    r"banner", r"button", r"icon", r"bullet", r"spacer", r"logo",
    r"navbar", r"header", r"footer", r"divider", r"arrow", r"rule",
    r"pixel", r"border", r"back_button", r"next_button", r"home_button",
    r"mail", r"email", r"counter", r"hit", r"dot\.gif", r"line\.gif"
]

for photo in cursor.fetchall():
    pid = photo["photo_id"]
    nfn = (photo["normalized_filename"] or "").lower()
    ofn = (photo["original_filename"] or "").lower()
    path = photo["local_image_path"]
    
    # Check filename patterns
    for pat in ui_name_patterns:
        if re.search(pat, nfn) or re.search(pat, ofn):
            findings["photos"].append({
                "photo_id": pid,
                "filename": photo["normalized_filename"],
                "issue": f"Filename matches UI pattern: '{pat}'"
            })
            break
            
    # Check physical file and dimensions
    abs_path = os.path.join(PRESERVATION_DIR, path) if not os.path.isabs(path) else path
    if not os.path.exists(abs_path):
        # Also check relative to PROJECT_ROOT
        alt_path = os.path.join(PROJECT_ROOT, path)
        if os.path.exists(alt_path):
            abs_path = alt_path
        else:
            findings["photos"].append({
                "photo_id": pid,
                "filename": photo["normalized_filename"],
                "issue": f"File does not exist: {path}"
            })
            continue

    try:
        fsize = os.path.getsize(abs_path)
        if fsize < 300: # < 300 bytes is almost certainly a 1x1 gif or spacer
            findings["photos"].append({
                "photo_id": pid,
                "filename": photo["normalized_filename"],
                "issue": f"File size suspiciously small: {fsize} bytes"
            })
        with Image.open(abs_path) as img:
            w, h = img.size
            # Aspect ratio or micro-dimension check
            if w < 25 or h < 25:
                findings["photos"].append({
                    "photo_id": pid,
                    "filename": photo["normalized_filename"],
                    "issue": f"Micro dimensions: {w}x{h} px"
                })
            elif (w > 400 and h < 25) or (h > 400 and w < 25): # Thin line / rule
                findings["photos"].append({
                    "photo_id": pid,
                    "filename": photo["normalized_filename"],
                    "issue": f"Thin strip / rule dimension: {w}x{h} px"
                })
    except Exception as e:
        findings["photos"].append({
            "photo_id": pid,
            "filename": photo["normalized_filename"],
            "issue": f"Failed to read image with PIL: {str(e)}"
        })

# -------------------------------------------------------------
# 3. AUDIT PERSONS
# -------------------------------------------------------------
print("Auditing persons...")
cursor.execute("SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, source_page FROM persons")

grammatical_verbs = {
    "went", "was", "died", "born", "lived", "had", "married", "moved", "came", "went", "saw",
    "been", "were", "is", "are", "left", "found", "went", "became", "entered", "departed"
}
prepositions_conjunctions = {
    "in", "at", "from", "to", "with", "by", "and", "or", "but", "for", "on", "into", "onto", "of"
}
noise_terms = {
    "click", "here", "enter", "index", "home", "search", "page", "unknown", "unknown unknown",
    "photo", "image", "document", "record", "cemetery", "county", "state", "delaware", "maryland",
    "new jersey", "pennsylvania"
}

for person in cursor.fetchall():
    pid = person["person_id"]
    name = (person["name"] or "").strip()
    source_page = person["source_page"] or ""
    
    # Check empty or whitespace
    if not name or len(name) < 2:
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name is empty or length < 2"
        })
        continue
        
    # Check length
    if len(name) > 80:
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name unusually long: {len(name)} chars"
        })
        
    tokens = re.split(r"\s+", name.lower())
    clean_tokens = [re.sub(r"[^\w]", "", t) for t in tokens if t]
    
    # Check if last token is a verb (grammatical fragment like 'Aaron Bass Jr. went')
    if len(clean_tokens) >= 2 and clean_tokens[-1] in grammatical_verbs:
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name ends with grammatical verb: '{clean_tokens[-1]}'"
        })
        
    # Check if name is solely noise/places/stopwords
    if " ".join(clean_tokens) in noise_terms:
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name is purely a noise / place token: '{name}'"
        })
        
    # Check for HTML entities or tags
    if re.search(r"&[a-z0-9]+;|[<>{}]", name):
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name contains HTML entities or tags: '{name}'"
        })
        
    # Check for digits in name
    if re.search(r"\d", name):
        # Check if Roman numeral (III, IV, etc.) or actual Arabic digit
        if not re.search(r"\b(1st|2nd|3rd|4th)\b", name):
            findings["persons"].append({
                "person_id": pid,
                "name": name,
                "issue": f"Name contains digits: '{name}'"
            })

    # Check for punctuation fragments like leading/trailing commas, quotes, parentheses mismatches
    if name.startswith(",") or name.endswith(",") or name.startswith(";") or name.endswith(";"):
        findings["persons"].append({
            "person_id": pid,
            "name": name,
            "issue": f"Name starts or ends with stray delimiter: '{name}'"
        })

# -------------------------------------------------------------
# 4. AUDIT OBITUARIES
# -------------------------------------------------------------
print("Auditing obituaries...")
cursor.execute("SELECT id, deceased_name, length(full_text) as tlen, full_text, source_url FROM obituaries")
for ob in cursor.fetchall():
    oid = ob["id"]
    dname = ob["deceased_name"] or ""
    txt = ob["full_text"] or ""
    tlen = ob["tlen"] or 0
    
    if tlen < 40:
        findings["obituaries"].append({
            "id": oid,
            "deceased_name": dname,
            "issue": f"Obituary text extremely short: {tlen} chars: {repr(txt)}"
        })
        
    # Check for error or spam text in obituary
    for kw in ["404 not found", "error", "domain name", "sponsored links"]:
        if kw in txt.lower():
            findings["obituaries"].append({
                "id": oid,
                "deceased_name": dname,
                "issue": f"Obituary text contains suspicious keyword: '{kw}'"
            })

# -------------------------------------------------------------
# 5. AUDIT MEDIA ASSETS
# -------------------------------------------------------------
print("Auditing media_assets...")
cursor.execute("SELECT id, original_filename, local_path, caption, associated_page FROM media_assets")
for m in cursor.fetchall():
    mid = m["id"]
    fn = (m["original_filename"] or "").lower()
    for pat in ui_name_patterns:
        if re.search(pat, fn):
            findings["media_assets"].append({
                "id": mid,
                "filename": m["original_filename"],
                "issue": f"Media asset matches UI pattern: '{pat}'"
            })
            break

# -------------------------------------------------------------
# 6. AUDIT SOURCES
# -------------------------------------------------------------
print("Auditing sources...")
cursor.execute("SELECT source_id, title, url FROM sources")
for s in cursor.fetchall():
    sid = s["source_id"]
    title = (s["title"] or "").lower()
    url = (s["url"] or "").lower()
    for kw in ["parked", "sedo", "godaddy", "domain sale", "404"]:
        if kw in title or kw in url:
            findings["sources"].append({
                "source_id": sid,
                "title": s["title"],
                "url": s["url"],
                "issue": f"Source matches suspicious keyword: '{kw}'"
            })

print("\n" + "="*70)
print("AUDIT RESULTS SUMMARY")
print("="*70)
total_issues = 0
for cat, items in findings.items():
    print(f"Category: {cat.upper()} - {len(items)} potential issues flagged")
    total_issues += len(items)
    for it in items[:15]:
        print(f"  * {it}")
    if len(items) > 15:
        print(f"  ... and {len(items) - 15} more")
    print()

print(f"Total flagged items across all categories: {total_issues}")
