#!/usr/bin/env python3
"""
FastAPI Server for Lynn C. Jackson Genealogy Preservation Archive
===================================================================
Provides REST API endpoints for:
- /api/stats
- /api/surnames
- /api/persons
- /api/graph
- /api/records/{filename}
- /api/media
- Static media file serving (/assets/images)
"""

import os
import sqlite3
import re
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
ARCHIVE_MEDIA_DIR = os.path.join(OUTPUT_DIR, "assets", "archive_media")
IMAGES_DIR = ARCHIVE_MEDIA_DIR
MITSAWOKETT_PHOTOS_DIR = ARCHIVE_MEDIA_DIR

app = FastAPI(title="Genealogy Preservation API")

# Enable CORS for blog integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve canonical media assets
os.makedirs(ARCHIVE_MEDIA_DIR, exist_ok=True)
app.mount("/assets/archive_media", StaticFiles(directory=ARCHIVE_MEDIA_DIR), name="archive_media")
app.mount("/assets/images", StaticFiles(directory=ARCHIVE_MEDIA_DIR), name="images")
app.mount("/assets/mitsawokett_photos", StaticFiles(directory=ARCHIVE_MEDIA_DIR), name="mitsawokett_photos")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pages")
    pages = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM media_assets")
    media = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM persons")
    persons = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    relationships = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM photo_catalog")
    photos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM obituaries")
    obituaries = c.fetchone()[0]
    
    # Dataset breakdown by source
    c.execute("SELECT dataset_source, COUNT(*) FROM persons GROUP BY dataset_source")
    person_sources = {row[0]: row[1] for row in c.fetchall()}

    conn.close()
    return {
        "pages": pages,
        "media_assets": media,
        "persons": persons,
        "relationships": relationships,
        "photos": photos,
        "obituaries": obituaries,
        "sources": {
            "lynncjackson": {
                "name": "Lynn C. Jackson Family Archive",
                "domain": "lynncjackson.com",
                "persons": person_sources.get("lynncjackson", 0)
            },
            "moors_delaware": {
                "name": "The Moors of Delaware Database",
                "domain": "moors-delaware.com",
                "persons": person_sources.get("moors_delaware", 0)
            },
            "mitsawokett": {
                "name": "Mitsawokett Delaware Native Archive",
                "domain": "nativeamericansofdelawarestate.com",
                "persons": person_sources.get("mitsawokett_delaware", 0) + person_sources.get("mitsawokett_ssa", 0),
                "photos": photos,
                "obituaries": obituaries
            },
            "smithsonian_nmai_speck": {
                "name": "Smithsonian NMAI Frank G. Speck Collection (Series 8)",
                "domain": "americanindian.si.edu",
                "persons": person_sources.get("smithsonian_nmai_speck", 0)
            }
        }
    }

@app.get("/api/stats.json")
def get_stats_alias():
    return get_stats()

@app.get("/api/surnames")
@app.get("/api/surnames.json")
def get_surnames():
    """Return aggregated surname stats across all integrated datasets, merging phonetic spelling variants."""
    conn = get_db()
    c = conn.cursor()
    
    # Load variant mappings
    c.execute("SELECT canonical_name, variant_name FROM surname_aliases")
    alias_rows = c.fetchall()
    
    canonical_map = {}
    for canon, var in alias_rows:
        if canon not in canonical_map: canonical_map[canon] = set()
        canonical_map[canon].add(var)

    # Core Delaware / Mitsawokett / Moors / Jackson / Nanticoke family surnames
    key_surnames = set([
        "Durham", "Harmon", "Mosley", "Jackson", "Morgan", "Coker", 
        "Carney", "Dean", "Munce", "Wright", "Sisco", "Church", 
        "Carter", "Hansor", "Ridgeway", "Counselor", "Carty", "Cott", 
        "Sammons", "Johnson", "Sockum", "Seeney", "Thomas", "Clark", 
        "Greenage", "Francisco", "Pierce", "Cork", "Davis", "Hewes", 
        "Hughes", "Street", "Norwood", "Miller", "Morris", "Gould", "Cuff", 
        "Driggus", "Thompson", "Puckham", "Bookram", "Oakley", "Bantum", 
        "Copes", "Pinder", "Kinyon", "Reed", "Butcher"
    ])

    results = []
    processed_canonicals = set()

    for surname in sorted(key_surnames):
        # Determine variants
        variants = list(canonical_map.get(surname, {surname}))
        if surname not in variants: variants.append(surname)
        
        # Build SQL OR conditions for all variants
        person_conds = " OR ".join(["name LIKE ?"] * len(variants))
        person_params = [f"%{v}%" for v in variants]
        c.execute(f"SELECT COUNT(*) FROM persons WHERE {person_conds}", person_params)
        count = c.fetchone()[0]

        c.execute(f"SELECT COUNT(DISTINCT source_page) FROM persons WHERE {person_conds}", person_params)
        pages_count = c.fetchone()[0]

        photo_conds = " OR ".join(["(subject_names LIKE ? OR maiden_name LIKE ? OR married_surname LIKE ?)"] * len(variants))
        photo_params = []
        for v in variants: photo_params.extend([f"%{v}%", f"%{v}%", f"%{v}%"])
        c.execute(f"SELECT COUNT(*) FROM photo_catalog WHERE {photo_conds}", photo_params)
        photo_count = c.fetchone()[0]

        obit_conds = " OR ".join(["(deceased_name LIKE ? OR full_text LIKE ?)"] * len(variants))
        obit_params = []
        for v in variants: obit_params.extend([f"%{v}%", f"%{v}%"])
        c.execute(f"SELECT COUNT(*) FROM obituaries WHERE {obit_conds}", obit_params)
        obit_count = c.fetchone()[0]

        if count > 0 or photo_count > 0 or obit_count > 0:
            variant_badge = ", ".join([v for v in variants if v != surname])
            results.append({
                "surname": surname,
                "variants": variant_badge,
                "individual_count": count,
                "associated_pages": pages_count,
                "photo_count": photo_count,
                "obituary_count": obit_count
            })

    # Sort alphabetically (A-Z) by surname
    results.sort(key=lambda x: x["surname"].lower())

    conn.close()
    return results


@app.get("/api/surnames/{surname}")
@app.get("/api/surnames/{surname}.json")
def get_surname_portal(surname: str):
    clean_surname = surname.replace(".json", "")
    conn = get_db()
    c = conn.cursor()

    # Individual count & members
    c.execute("""
        SELECT p.person_id, p.name, p.first_name, p.middle_name, p.maiden_name,
               p.married_last_name, p.birth_info, p.death_info, p.notes,
               (SELECT COUNT(*) FROM person_photos pp WHERE pp.person_id = p.person_id) as photo_count
        FROM persons p
        WHERE p.name LIKE ? OR p.maiden_name LIKE ? OR p.married_last_name LIKE ?
        ORDER BY p.name ASC
    """, (f"%{clean_surname}%", f"%{clean_surname}%", f"%{clean_surname}%"))
    individuals = [dict(r) for r in c.fetchall()]

    # Photos & breakdown
    c.execute("""
        SELECT upc.photo_id, upc.category, upc.normalized_filename, upc.local_image_path,
               upc.subject_names, upc.approximate_year, upc.document_type
        FROM photo_surnames ps
        JOIN unified_photo_catalog upc ON ps.photo_id = upc.photo_id
        WHERE LOWER(ps.surname) = LOWER(?)
        ORDER BY upc.category ASC, upc.approximate_year DESC
    """, (clean_surname,))
    photos = [dict(r) for r in c.fetchall()]

    # Category counts
    c.execute("""
        SELECT upc.category, COUNT(DISTINCT upc.photo_id)
        FROM photo_surnames ps
        JOIN unified_photo_catalog upc ON ps.photo_id = upc.photo_id
        WHERE LOWER(ps.surname) = LOWER(?)
        GROUP BY upc.category
    """, (clean_surname,))
    cat_counts = dict(c.fetchall())

    # Obituaries
    c.execute("""
        SELECT o.id, o.deceased_name, o.age, o.birth_date, o.death_date, o.cemetery_location, o.full_text, o.source_url
        FROM obituaries o
        WHERE o.deceased_name LIKE ? OR o.full_text LIKE ?
        ORDER BY o.deceased_name ASC
    """, (f"%{clean_surname}%", f"%{clean_surname}%"))
    obits = [dict(r) for r in c.fetchall()]

    conn.close()

    return {
        "surname": clean_surname,
        "individual_count": len(individuals),
        "photo_count": len(photos),
        "category_counts": cat_counts,
        "obituary_count": len(obits),
        "variants": f"{clean_surname}s, {clean_surname}e",
        "photos": photos,
        "individuals": individuals,
        "obituaries": obits
    }


@app.get("/api/persons")
def get_persons(surname: str = Query(None), q: str = Query(None)):
    conn = get_db()
    c = conn.cursor()
    
    query = "SELECT person_id, name, source_page, notes FROM persons WHERE 1=1"
    params = []

    if surname:
        query += " AND name LIKE ?"
        params.append(f"%{surname}%")
    if q:
        query += " AND (name LIKE ? OR notes LIKE ?)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")

    query += " LIMIT 100"
    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

@app.get("/api/graph")
@app.get("/api/graph.json")
def get_graph(surname: str = Query(None)):
    """Return nodes and edges for network graph visualization, prioritizing connected lineages."""
    conn = get_db()
    c = conn.cursor()

    if surname:
        # Get persons matching surname who have relationships
        c.execute("""
            SELECT DISTINCT p.person_id, p.name, p.source_page
            FROM persons p
            JOIN relationships r ON p.person_id = r.person_a_id OR p.person_id = r.person_b_id
            WHERE p.name LIKE ?
            LIMIT 80
        """, (f"%{surname}%",))
        initial_nodes = c.fetchall()
        
        # If no connected persons found with filter, fallback to any matching persons
        if not initial_nodes:
            c.execute("SELECT person_id, name, source_page FROM persons WHERE name LIKE ? LIMIT 60", (f"%{surname}%",))
            initial_nodes = c.fetchall()
    else:
        # Get persons who have active relationships
        c.execute("""
            SELECT DISTINCT p.person_id, p.name, p.source_page
            FROM persons p
            JOIN relationships r ON p.person_id = r.person_a_id OR p.person_id = r.person_b_id
            LIMIT 120
        """)
        initial_nodes = c.fetchall()

    node_dict = {row["person_id"]: dict(row) for row in initial_nodes}

    # Fetch all relationships where at least one person is in node_dict
    if node_dict:
        placeholders = ",".join("?" * len(node_dict))
        query = f"""
            SELECT id, person_a_id, person_b_id, relationship_type, evidence_text 
            FROM relationships 
            WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})
        """
        c.execute(query, list(node_dict.keys()) + list(node_dict.keys()))
        edges_rows = c.fetchall()
    else:
        edges_rows = []

    # Ensure person_a and person_b are both present in node_dict so edges aren't broken
    missing_ids = set()
    for r in edges_rows:
        if r["person_a_id"] not in node_dict: missing_ids.add(r["person_a_id"])
        if r["person_b_id"] not in node_dict: missing_ids.add(r["person_b_id"])

    if missing_ids:
        placeholders = ",".join("?" * len(missing_ids))
        c.execute(f"SELECT person_id, name, source_page FROM persons WHERE person_id IN ({placeholders})", list(missing_ids))
        for row in c.fetchall():
            node_dict[row["person_id"]] = dict(row)

    nodes = []
    for pid, r in node_dict.items():
        surname_group = r["name"].split()[-1] if r["name"] else "Unknown"
        nodes.append({
            "id": r["person_id"],
            "label": r["name"],
            "group": surname_group,
            "source_page": r["source_page"]
        })

    edges = []
    for r in edges_rows:
        edges.append({
            "from": r["person_a_id"],
            "to": r["person_b_id"],
            "label": r["relationship_type"],
            "type": r["relationship_type"],
            "evidence": r["evidence_text"]
        })

    conn.close()
    return {"nodes": nodes, "edges": edges}

@app.get("/api/records/{filename:path}")
def get_record(filename: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT filename, title, clean_html, text_content, wayback_url, timestamp FROM pages WHERE filename = ?", (filename,))
    page = c.fetchone()
    
    if not page:
        conn.close()
        raise HTTPException(status_code=404, detail="Preserved record not found")

    c.execute("SELECT local_path, caption FROM media_assets WHERE associated_page = ?", (filename,))
    media = [dict(m) for m in c.fetchall()]

    conn.close()
    return {
        "filename": page["filename"],
        "title": page["title"],
        "clean_html": page["clean_html"],
        "text_content": page["text_content"],
        "wayback_url": page["wayback_url"],
        "timestamp": page["timestamp"],
        "media_assets": media
    }

@app.get("/api/pdf/{identifier:path}")
@app.get("/api/transcriptions-pdf/{identifier:path}")
def get_pdf_route(identifier: str):
    clean_id = identifier.replace(".pdf", "")
    data = get_transcription_endpoint(clean_id)
    pdf_bytes = generate_transcription_pdf(data)
    filename_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', data.get("title", clean_id))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{filename_slug}_transcription.pdf\""}
    )


@app.get("/api/transcriptions/{identifier:path}")
def get_transcription_endpoint(identifier: str):
    if identifier.endswith(".json"):
        identifier = identifier[:-5]
    elif identifier.endswith(".pdf"):
        identifier = identifier[:-4]

    import urllib.parse
    conn = get_db()
    c = conn.cursor()

    is_int = False
    try:
        pid = int(identifier)
        is_int = True
    except ValueError:
        is_int = False

    transcribed_text = None
    title = None
    doc_type = "Historical Document"
    approx_year = "Historical Record"
    source_url = None
    local_image = None
    original_filename = None
    surname = None
    clean_html = None

    if is_int:
        c.execute("""
            SELECT photo_id, category, normalized_filename, original_filename,
                   local_image_path, subject_names, surname, given_names,
                   approximate_year, document_type, dataset_source, source_url
            FROM unified_photo_catalog
            WHERE photo_id = ?
        """, (pid,))
        doc = c.fetchone()
        if doc:
            doc = dict(doc)
            title = doc.get("subject_names") or doc.get("normalized_filename")
            doc_type = (doc.get("document_type") or doc.get("category") or "document").replace("_", " ").title()
            approx_year = doc.get("approximate_year") or "Historical Record"
            source_url = doc.get("source_url")
            local_image = doc.get("local_image_path")
            original_filename = doc.get("original_filename")
            surname = doc.get("surname")

            if source_url:
                slug = source_url.split("/")[-1]
                slug_decoded = urllib.parse.unquote(slug)
                slug_quoted = urllib.parse.quote(slug_decoded)
                c.execute("""
                    SELECT title, text_content, clean_html, wayback_url 
                    FROM pages 
                    WHERE filename = ? OR filename = ? OR filename LIKE ? OR wayback_url = ?
                    LIMIT 1
                """, (slug, slug_quoted, f"%{slug_decoded}%", source_url))
                p = c.fetchone()
                if p:
                    if p["title"] and not p["title"].startswith("Mitsawokett"):
                        title = p["title"]
                    transcribed_text = p["text_content"]
                    clean_html = p["clean_html"]
    else:
        decoded = urllib.parse.unquote(identifier)
        quoted = urllib.parse.quote(decoded)
        c.execute("""
            SELECT filename, title, text_content, clean_html, wayback_url 
            FROM pages 
            WHERE filename = ? OR filename = ? OR filename LIKE ? OR wayback_url = ?
            LIMIT 1
        """, (identifier, quoted, f"%{decoded}%", identifier))
        p = c.fetchone()
        if p:
            title = p["title"] or decoded
            transcribed_text = p["text_content"]
            clean_html = p["clean_html"]
            source_url = p["wayback_url"]
            original_filename = p["filename"]

            c.execute("SELECT local_path, caption FROM media_assets WHERE associated_page = ? LIMIT 1", (p["filename"],))
            m = c.fetchone()
            if m:
                local_image = m["local_path"]

            low = (p["filename"] + " " + (p["title"] or "")).lower()
            if "bible" in low:
                doc_type = "Family Bible Register"
            elif "will" in low or "probate" in low:
                doc_type = "Last Will & Testament / Probate"
            elif "deed" in low or "land" in low:
                doc_type = "Land Deed / Indenture"
            elif "census" in low or "race" in low:
                doc_type = "Census Enumeration / Reclassification"
            elif "apprentice" in low:
                doc_type = "Apprentice Binding Indenture"
            elif "church" in low:
                doc_type = "Church Record / Register"
            else:
                doc_type = "Preserved Primary Document"

    conn.close()

    if not title and not transcribed_text:
        raise HTTPException(status_code=404, detail="Document record not found")

    if not title:
        title = f"Archival Document #{identifier}"

    if transcribed_text:
        raw_lines = [l.strip() for l in transcribed_text.splitlines() if l.strip()]
        lines = raw_lines
        full_text = "\n".join(lines)
    else:
        lines = [
            f"DOCUMENT TITLE: {title}",
            f"RECORD CLASSIFICATION: {doc_type}",
            f"ARCHIVAL HOLDING: Native Americans of Delaware State / Mitsawokett Historical Archive",
            f"ESTIMATED DATE / ERA: {approx_year}",
            "--------------------------------------------------------------------------------",
            "TRANSCRIPTION RECORD & SUMMARY:",
            f"This primary document was preserved as part of the Delmarva genealogical survey of the Nanticoke, Moor, and Lenape families.",
            f"Associated File: {original_filename or identifier}",
            f"Lineage / Surnames Documented: {surname or 'Delmarva tribal families'}",
            "--------------------------------------------------------------------------------",
            "VERIFICATION & CITATION:",
            f"Source URL: {source_url or 'Preserved in Mitsawokett Digital Archive'}",
            f"Archive Identifier: Item #{identifier}"
        ]
        full_text = "\n".join(lines)

    words = len(full_text.split())
    citation = f'"{title}." Historical Document Record ({approx_year}). Preserved in the Nanticoke & Moor Historical Archive (Written in the Genome Collection).'
    if source_url:
        citation += f' Original source: {source_url}.'

    return {
        "identifier": identifier,
        "title": title,
        "document_type": doc_type,
        "approximate_year": approx_year,
        "repository": "Delaware Native American Archives / Mitsawokett Collection",
        "transcriber": "Archival Transcriber / Written in the Genome",
        "status": "verified",
        "citation": citation,
        "source_url": source_url,
        "local_image_path": local_image,
        "line_count": len(lines),
        "word_count": words,
        "lines": lines,
        "full_text": full_text,
        "clean_html": clean_html
    }


def to_pdf_safe_text(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "—": " - ",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "\u00a0": " ",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_transcription_pdf(data: dict) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Top Header Banner
    pdf.set_fill_color(26, 23, 20)
    pdf.set_text_color(198, 139, 89)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(pdf.epw, 8, to_pdf_safe_text("DELAWARE NATIVE AMERICAN ARCHIVES — PRESERVED MANUSCRIPT"), new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    pdf.ln(4)

    # Document Title
    pdf.set_text_color(24, 20, 16)
    pdf.set_font("Helvetica", "B", 15)
    title = data.get("title") or "Historical Document Transcription"
    pdf.multi_cell(pdf.epw, 7, to_pdf_safe_text(title), align="C")

    # Document Metadata Header
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 100, 90)
    meta_parts = [
        f"Classification: {data.get('document_type', 'Primary Record')}",
        f"Year: {data.get('approximate_year', 'Historical Record')}",
        f"Length: {data.get('line_count', len(data.get('lines', [])))} Lines ({data.get('word_count', 0)} Words)"
    ]
    pdf.multi_cell(pdf.epw, 5, to_pdf_safe_text(" | ".join(meta_parts)), align="C")

    pdf.ln(3)
    pdf.set_draw_color(198, 139, 89)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    # Transcription Lines Body
    lines = data.get("lines") or []
    pdf.set_font("Helvetica", "", 9.5)

    for idx, line in enumerate(lines, 1):
        if line.startswith("---") or line.startswith("==="):
            pdf.ln(2)
            pdf.set_draw_color(210, 200, 190)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(2)
            continue

        if line.startswith("DOCUMENT TITLE:") or line.startswith("RECORD CLASSIFICATION:") or line.startswith("TRANSCRIPTION") or line.startswith("ARCHIVAL CITATION:"):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(198, 139, 89)
            pdf.multi_cell(pdf.epw, 5, to_pdf_safe_text(line))
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(30, 30, 30)
            continue

        line_num = f"{idx:3d}  "
        safe_line = to_pdf_safe_text(line)

        pdf.set_font("Courier", "", 8)
        pdf.set_text_color(150, 140, 130)
        pdf.cell(10, 5, line_num)

        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(pdf.epw - 10, 5, safe_line)

    if data.get("citation"):
        pdf.ln(6)
        pdf.set_fill_color(245, 243, 240)
        pdf.set_draw_color(200, 190, 180)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(198, 139, 89)
        pdf.cell(pdf.epw, 6, "ARCHIVAL CITATION", new_x="LMARGIN", new_y="NEXT", fill=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(60, 60, 60)
        safe_citation = to_pdf_safe_text(data["citation"])
        pdf.multi_cell(pdf.epw, 5, safe_citation, fill=True)

    return bytes(pdf.output())


@app.get("/api/transcriptions/{identifier:path}/pdf")
def get_transcription_pdf_endpoint(identifier: str):
    clean_id = identifier.replace(".pdf", "")
    data = get_transcription_endpoint(clean_id)
    pdf_bytes = generate_transcription_pdf(data)
    filename_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', data.get("title", clean_id))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{filename_slug}_transcription.pdf\""}
    )


@app.get("/api/media")
def get_media_gallery():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, original_filename, local_path, caption, associated_page 
        FROM media_assets 
        WHERE (local_path LIKE '%.jpg' OR local_path LIKE '%.jpeg' OR local_path LIKE '%.png')
          AND original_filename NOT LIKE '%return%' 
          AND original_filename NOT LIKE '%redrule%'
          AND original_filename NOT LIKE '%banner%'
          AND original_filename NOT LIKE '%sorry%'
        LIMIT 100
    """)
    media = [dict(m) for m in c.fetchall()]
    conn.close()
    return media


def get_surname_variants(surname: str):
    """Return list of all phonetic spelling variants for a surname (e.g. Hansor -> Hansor, Hanzer, Handsor)."""
    if not surname: return []
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT variant_name FROM surname_aliases 
        WHERE LOWER(canonical_name) = LOWER(?) OR LOWER(variant_name) = LOWER(?)
        UNION
        SELECT DISTINCT canonical_name FROM surname_aliases 
        WHERE LOWER(canonical_name) = LOWER(?) OR LOWER(variant_name) = LOWER(?)
    """, (surname, surname, surname, surname))
    rows = c.fetchall()
    conn.close()
    if rows:
        variants = {r[0] for r in rows if r[0]}
        variants.add(surname)
        return list(variants)
    return [surname]


# ─── Photo Catalog: Surname-grouped photo gallery ────────────────────────
@app.get("/api/photos")
def get_photos(surname: str = Query(None), limit: int = Query(300)):
    """Return cataloged photos, automatically matching all phonetic surname variants."""
    conn = get_db()
    c = conn.cursor()
    if surname:
        variants = get_surname_variants(surname)
        # Build SQL OR conditions for all variants
        conds = []
        params = []
        for v in variants:
            conds.append("(subject_names LIKE ? OR maiden_name LIKE ? OR married_surname LIKE ?)")
            params.extend([f"%{v}%", f"%{v}%", f"%{v}%"])
        
        where_clause = " OR ".join(conds)
        params.append(limit)
        c.execute(f"""
            SELECT photo_id, title_or_caption, subject_names, maiden_name, 
                   married_surname, approximate_year, local_image_path, source_url
            FROM photo_catalog
            WHERE {where_clause}
            ORDER BY maiden_name, subject_names
            LIMIT ?
        """, params)
    else:
        c.execute("""
            SELECT photo_id, title_or_caption, subject_names, maiden_name,
                   married_surname, approximate_year, local_image_path, source_url
            FROM photo_catalog
            ORDER BY maiden_name, subject_names
            LIMIT ?
        """, (limit,))
    photos = [dict(r) for r in c.fetchall()]
    conn.close()
    return photos


@app.get("/api/photos/surnames")
def get_photo_surnames():
    """Return surname groups with photo counts for the gallery portal."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT maiden_name AS surname, COUNT(*) AS photo_count
        FROM photo_catalog
        WHERE maiden_name IS NOT NULL AND maiden_name != '' AND LENGTH(maiden_name) > 1
        GROUP BY maiden_name
        HAVING photo_count >= 1
        ORDER BY maiden_name ASC
    """)
    results = [dict(r) for r in c.fetchall()]
    conn.close()
    return results


@app.get("/api/surnames/aliases")
def get_surname_aliases():
    """Return canonical surname clusters with all historical spelling variants."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT canonical_name, GROUP_CONCAT(variant_name, ', ') AS variants
        FROM surname_aliases
        GROUP BY canonical_name
        ORDER BY canonical_name ASC
    """)
    aliases = [dict(r) for r in c.fetchall()]
    conn.close()
    return aliases


@app.get("/api/family-interconnections")
def get_family_interconnections():
    """Return interconnected family pairs with marriage, photo, and lineage ties."""
    conn = get_db()
    c = conn.cursor()

    interconnections = []

    # 1. Inter-family marriages from photo catalog
    c.execute("""
        SELECT maiden_name, married_surname, COUNT(*) AS photo_count
        FROM photo_catalog
        WHERE maiden_name IS NOT NULL AND married_surname IS NOT NULL
          AND maiden_name != '' AND married_surname != ''
          AND LOWER(maiden_name) != LOWER(married_surname)
        GROUP BY maiden_name, married_surname
        HAVING photo_count >= 2
        ORDER BY photo_count DESC
    """)
    photo_ties = c.fetchall()

    for m, ms, cnt in photo_ties:
        interconnections.append({
            "family_a": m.strip(),
            "family_b": ms.strip(),
            "tie_type": "Marriage / Photo Link",
            "count": cnt,
            "description": f"{cnt} cataloged preserved photographs linking the {m} and {ms} lineages"
        })

    # 2. Spousal & Parent-Child ties from relationships table
    c.execute("""
        SELECT p1.name AS name_a, p2.name AS name_b, r.relationship_type, r.evidence_text
        FROM relationships r
        JOIN persons p1 ON r.person_a_id = p1.person_id
        JOIN persons p2 ON r.person_b_id = p2.person_id
        WHERE p1.name IS NOT NULL AND p2.name IS NOT NULL
    """)
    rel_rows = c.fetchall()

    for r in rel_rows:
        n_a = r["name_a"]
        n_b = r["name_b"]
        sn_a = n_a.split()[-1] if n_a else ""
        sn_b = n_b.split()[-1] if n_b else ""
        if sn_a and sn_b and sn_a.lower() != sn_b.lower() and len(sn_a) > 2 and len(sn_b) > 2:
            interconnections.append({
                "family_a": sn_a,
                "family_b": sn_b,
                "person_a": n_a,
                "person_b": n_b,
                "tie_type": r["relationship_type"].capitalize(),
                "count": 1,
                "description": r["evidence_text"] or f"{n_a} linked to {n_b}"
            })

    conn.close()
    return interconnections


# ─── Audit Flags: Review & Resolution UI ──────────────────────────────────
@app.get("/api/audit/flags")
def get_audit_flags(
    category: str = Query(None),
    severity: str = Query(None),
    resolved: bool = Query(False),
    limit: int = Query(100)
):
    """Return audit flags for the resolution UI."""
    conn = get_db()
    c = conn.cursor()
    query = """
        SELECT af.flag_id, af.category, af.severity, af.person_id, af.person_id_secondary,
               af.description, af.evidence, af.resolution, af.resolved_at, af.auto_resolved,
               af.created_at,
               p1.name AS person_name, p2.name AS person_secondary_name
        FROM audit_flags af
        LEFT JOIN persons p1 ON af.person_id = p1.person_id
        LEFT JOIN persons p2 ON af.person_id_secondary = p2.person_id
        WHERE 1=1
    """
    params = []
    if not resolved:
        query += " AND af.resolved_at IS NULL"
    if category:
        query += " AND af.category = ?"
        params.append(category)
    if severity:
        query += " AND af.severity = ?"
        params.append(severity)
    query += " ORDER BY CASE af.severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, af.flag_id LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    flags = [dict(r) for r in c.fetchall()]
    conn.close()
    return flags


@app.get("/api/audit/summary")
def get_audit_summary():
    """Return audit flag counts by category and severity."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT category, severity, COUNT(*) AS count,
               SUM(CASE WHEN resolved_at IS NOT NULL THEN 1 ELSE 0 END) AS resolved
        FROM audit_flags
        GROUP BY category, severity
        ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, category
    """)
    summary = [dict(r) for r in c.fetchall()]
    conn.close()
    return summary


from fastapi import Body

@app.post("/api/audit/resolve/{flag_id}")
def resolve_audit_flag(flag_id: int, body: dict = Body(...)):
    """Resolve an audit flag with a resolution action."""
    conn = get_db()
    c = conn.cursor()
    resolution = body.get("resolution", "Manually resolved")
    action = body.get("action", "dismiss")  # dismiss, merge, delete

    # Handle merge action
    if action == "merge":
        c.execute("SELECT person_id, person_id_secondary FROM audit_flags WHERE flag_id = ?", (flag_id,))
        flag = c.fetchone()
        if flag and flag["person_id"] and flag["person_id_secondary"]:
            keep_id = flag["person_id"]
            remove_id = flag["person_id_secondary"]
            # Reassign relationships
            c.execute("UPDATE relationships SET person_a_id = ? WHERE person_a_id = ?", (keep_id, remove_id))
            c.execute("UPDATE relationships SET person_b_id = ? WHERE person_b_id = ?", (keep_id, remove_id))
            c.execute("DELETE FROM relationships WHERE person_a_id = person_b_id")
            # Reassign photos
            c.execute("UPDATE OR IGNORE person_photos SET person_id = ? WHERE person_id = ?", (keep_id, remove_id))
            c.execute("DELETE FROM person_photos WHERE person_id = ?", (remove_id,))
            # Delete duplicate
            conn.execute("PRAGMA foreign_keys=OFF")
            c.execute("DELETE FROM persons WHERE person_id = ?", (remove_id,))
            resolution = f"Merged person {remove_id} into {keep_id}"

    c.execute("""
        UPDATE audit_flags
        SET resolution = ?, resolved_at = datetime('now')
        WHERE flag_id = ?
    """, (resolution, flag_id))
    conn.commit()
    conn.close()
    return {"status": "resolved", "flag_id": flag_id, "resolution": resolution}


# ─── Obituaries API: Browse & Search Preserved Obituaries ────────────────
@app.get("/api/obituaries")
def get_obituaries(q: str = Query(None), limit: int = Query(100)):
    """Return preserved obituaries with optional search."""
    conn = get_db()
    c = conn.cursor()
    query = """
        SELECT id, deceased_name, maiden_name, married_surname, birth_date, death_date, age,
               cemetery_location, surviving_kin, full_text, source_url
        FROM obituaries
        WHERE 1=1
    """
    params = []
    if q:
        query += " AND (deceased_name LIKE ? OR full_text LIKE ? OR cemetery_location LIKE ?)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")
        params.append(f"%{q}%")
    query += " ORDER BY id LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    obits = [dict(r) for r in c.fetchall()]
    conn.close()
    return obits


# ─── GEDCOM 5.5.1 Standard Exporter ──────────────────────────────────────
from fastapi.responses import Response

@app.get("/api/export/gedcom")
def export_gedcom():
    """Export the unified genealogical graph as a standard GEDCOM 5.5.1 file."""
    conn = get_db()
    c = conn.cursor()

    ged_lines = [
        "0 HEAD",
        "1 SOUR DelmarvaGenealogyPreservationArchive",
        "2 VERS 1.0",
        "2 NAME Delmarva Genealogical Preservation Archive",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
        "1 SUBM @SUBM1@",
        "0 @SUBM1@ SUBM",
        "1 NAME Genealogical Preservation Project"
    ]

    c.execute("SELECT person_id, name, birth_info, death_info, notes, source_page, dataset_source FROM persons")
    persons = c.fetchall()

    for p in persons:
        pid = p["person_id"]
        name = p["name"] or "Unknown"
        ged_lines.append(f"0 @P{pid}@ INDI")
        ged_lines.append(f"1 NAME {name}")
        if p["birth_info"]:
            ged_lines.append("1 BIRT")
            ged_lines.append(f"2 DATE {p['birth_info']}")
        if p["death_info"]:
            ged_lines.append("1 DEAT")
            ged_lines.append(f"2 DATE {p['death_info']}")
        if p["notes"]:
            ged_lines.append(f"1 NOTE {p['notes']}")
        ged_lines.append(f"1 SOUR {p['source_page']} ({p['dataset_source']})")

    # Families / Relationships
    c.execute("SELECT id, person_a_id, person_b_id, relationship_type, evidence_text FROM relationships")
    rels = c.fetchall()

    fam_idx = 1
    for r in rels:
        rtype = r["relationship_type"]
        if rtype == "spouse":
            ged_lines.append(f"0 @F{fam_idx}@ FAM")
            ged_lines.append(f"1 HUSB @P{r['person_a_id']}@")
            ged_lines.append(f"1 WIFE @P{r['person_b_id']}@")
            if r["evidence_text"]:
                ged_lines.append(f"1 NOTE {r['evidence_text']}")
            fam_idx += 1
        elif rtype in ("child_of", "parent_of"):
            child = r['person_a_id'] if rtype == 'child_of' else r['person_b_id']
            parent = r['person_b_id'] if rtype == 'child_of' else r['person_a_id']
            ged_lines.append(f"0 @F{fam_idx}@ FAM")
            ged_lines.append(f"1 HUSB @P{parent}@")
            ged_lines.append(f"1 CHIL @P{child}@")
            fam_idx += 1

    ged_lines.append("0 TRLR")
    conn.close()

    content = "\n".join(ged_lines)
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=delmarva_genealogy_preservation.ged"}
    )


# ─── Person Profile API Endpoint ─────────────────────────────────────────
@app.get("/api/person/{person_id}")
def get_person_profile(person_id: int):
    """Return detailed person profile with immediate family, photos, and obituaries."""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT person_id, name, source_page, birth_info, death_info, notes, dataset_source FROM persons WHERE person_id = ?", (person_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Person not found")

    person = dict(row)

    # Relationships
    c.execute("""
        SELECT r.relationship_type, r.evidence_text, p2.person_id AS rel_id, p2.name AS rel_name
        FROM relationships r
        JOIN persons p2 ON (r.person_b_id = p2.person_id AND r.person_a_id = ?) 
                        OR (r.person_a_id = p2.person_id AND r.person_b_id = ?)
    """, (person_id, person_id))
    rels = [dict(r) for r in c.fetchall()]

    # Photos
    c.execute("""
        SELECT pc.* FROM person_photos pp
        JOIN photo_catalog pc ON pp.photo_id = pc.photo_id
        WHERE pp.person_id = ?
    """, (person_id,))
    photos = [dict(r) for r in c.fetchall()]

    # Obituaries
    c.execute("""
        SELECT o.* FROM person_obituaries po
        JOIN obituaries o ON po.obituary_id = o.id
        WHERE po.person_id = ?
    """, (person_id,))
    obits = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "person": person,
        "relationships": rels,
        "photos": photos,
        "obituaries": obits
    }

@app.get("/api/search")
def search_archive(q: str = Query(..., min_length=2, description="Search query")):
    """Full-text search across obituaries, historical articles, and documents using SQLite FTS5."""
    conn = get_db()
    c = conn.cursor()
    
    # Sanitize FTS query for safe matching
    safe_q = re.sub(r'[^\w\s]', ' ', q).strip()
    if not safe_q:
        return {"query": q, "total_results": 0, "results": []}
    
    match_terms = " ".join([f'"{term}"*' for term in safe_q.split()])
    
    try:
        c.execute("""
            SELECT doc_type, source_id, title,
                   snippet(fts_genealogy_corpus, 3, '<mark>', '</mark>', '...', 12) as text_snippet,
                   metadata
            FROM fts_genealogy_corpus
            WHERE fts_genealogy_corpus MATCH ?
            ORDER BY rank
            LIMIT 50
        """, (match_terms,))
        results = [dict(r) for r in c.fetchall()]
    except Exception:
        results = []
        
    conn.close()
    return {
        "query": q,
        "total_results": len(results),
        "results": results
    }

@app.get("/api/cemeteries")
def get_cemeteries():
    """Returns all historical Nanticoke & Moor cemeteries with geocoordinates and tombstone counts."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.*, COUNT(tcl.photo_id) as tombstone_count
        FROM cemeteries c
        LEFT JOIN tombstone_cemetery_links tcl ON c.cemetery_id = tcl.cemetery_id
        GROUP BY c.cemetery_id
        ORDER BY tombstone_count DESC, c.name ASC
    """)
    cemeteries = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"total": len(cemeteries), "cemeteries": cemeteries}

@app.get("/api/cemeteries/{cemetery_id}")
def get_cemetery_detail(cemetery_id: int):
    """Returns cemetery details and associated tombstone photos."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cemeteries WHERE cemetery_id = ?", (cemetery_id,))
    cem = c.fetchone()
    if not cem:
        conn.close()
        raise HTTPException(status_code=404, detail="Cemetery not found")
        
    c.execute("""
        SELECT upc.photo_id, upc.normalized_filename, upc.local_image_path, upc.subject_names
        FROM tombstone_cemetery_links tcl
        JOIN unified_photo_catalog upc ON tcl.photo_id = upc.photo_id
        WHERE tcl.cemetery_id = ?
    """, (cemetery_id,))
    tombstones = [dict(r) for r in c.fetchall()]
    conn.close()
    return {
        "cemetery": dict(cem),
        "tombstones": tombstones
    }

@app.get("/api/person/{person_id}/timeline")
def get_person_timeline(person_id: int):
    """Returns an ordered chronological timeline of life facts and events with citations."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT f.fact_id, f.fact_type, f.date_string, f.place_string, f.value_string,
               s.title as source_title, c.evidence_text
        FROM facts f
        LEFT JOIN citations c ON f.fact_id = c.fact_id
        LEFT JOIN sources s ON c.source_id = s.source_id
        WHERE f.person_id = ?
        ORDER BY f.date_string ASC, f.fact_id ASC
    """, (person_id,))
    timeline = [dict(r) for r in c.fetchall()]
    conn.close()
    return {
        "person_id": person_id,
        "timeline_events_count": len(timeline),
        "events": timeline
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

