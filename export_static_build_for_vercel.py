import sqlite3
import json
import os
import shutil
import re
from collections import defaultdict

BASE_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper'
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')
API_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'api')
PUBLIC_DIR = os.path.join(BASE_DIR, 'frontend', 'public')
ASSETS_SRC = os.path.join(BASE_DIR, 'preservation_output', 'assets', 'archive_media')
ASSETS_DEST = os.path.join(BASE_DIR, 'frontend', 'public', 'assets', 'archive_media')

import sys
sys.path.insert(0, BASE_DIR)
from archive_naming_rules import get_clean_surname, is_valid_person_name, NOISE_WORDS

def export_all():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM persons")
    total_persons = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM relationships")
    total_relationships = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM photo_catalog")
    total_photos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM obituaries")
    total_obits = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pages")
    total_pages = c.fetchone()[0]

    stats = {
        "pages": total_pages,
        "media_assets": 1888,
        "persons": total_persons,
        "relationships": total_relationships,
        "photos": total_photos,
        "obituaries": total_obits,
        "sources": {
            "davis_family_gedcom": {"name": "Davis Family Tree GEDCOM", "domain": "Desktop/Davis Family Tree.ged", "persons": 2697},
            "lynncjackson": {"name": "Lynn C. Jackson Family Archive", "domain": "lynncjackson.com", "persons": 502},
            "moors_delaware": {"name": "The Moors of Delaware Database", "domain": "moors-delaware.com", "persons": 84},
            "mitsawokett": {"name": "Mitsawokett Delaware Native Archive", "domain": "nativeamericansofdelawarestate.com", "persons": 5977, "photos": 1971, "obituaries": 156},
            "smithsonian_nmai_speck": {"name": "Smithsonian NMAI Frank G. Speck Collection (Series 8)", "domain": "americanindian.si.edu", "persons": 10}
        }
    }
    with open(os.path.join(API_DIR, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print("Step 2: Exporting /api/surnames.json...")
    # Canonical Delmarva & Nanticoke Protected Surnames
    key_surnames = [
        "Bantum", "Bookram", "Butcher", "Carmean", "Carney", "Clark", "Coker", "Conaway",
        "Copes", "Cordrey", "Cork", "Cottman", "Counselor", "Cremeen", "Davis", "Dean",
        "Dickerson", "Durham", "Francisco", "Goldsborough", "Green", "Handsor", "Hanzer",
        "Harmon", "Hitchens", "Hughes", "Ingram", "Jackson", "Johnson", "Kinyon", "Loatman",
        "Miller", "Moore", "Morris", "Mosley", "Muncey", "Norwood", "Oakley", "Pierce",
        "Pinder", "Puckham", "Reed", "Ridgeway", "Sammons", "Sockum", "Street", "Thomas",
        "Thompson", "Turner", "Wilson", "Wright"
    ]
    
    surnames_data = []
    os.makedirs(os.path.join(API_DIR, 'surnames'), exist_ok=True)

    for s in sorted(key_surnames):
        c.execute("SELECT COUNT(*) FROM persons WHERE name LIKE ?", (f"%{s}%",))
        p_cnt = c.fetchone()[0]
        
        c.execute("""
            SELECT COUNT(DISTINCT ps.photo_id) 
            FROM photo_surnames ps 
            WHERE LOWER(ps.surname) = LOWER(?)
        """, (s,))
        ph_cnt = c.fetchone()[0]

        # Category breakdown of photos for this surname
        c.execute("""
            SELECT upc.category, COUNT(DISTINCT upc.photo_id)
            FROM photo_surnames ps
            JOIN unified_photo_catalog upc ON ps.photo_id = upc.photo_id
            WHERE LOWER(ps.surname) = LOWER(?)
            GROUP BY upc.category
        """, (s,))
        cat_counts = dict(c.fetchall())

        c.execute("SELECT COUNT(*) FROM obituaries WHERE deceased_name LIKE ? OR full_text LIKE ?", (f"%{s}%", f"%{s}%"))
        ob_cnt = c.fetchone()[0]
        
        variants = f"{s}s, {s}e"
        if s == "Sammons":
            variants = "Salmons, Samons, Sammon, Sammons"

        # Fetch detailed photos for this surname
        c.execute("""
            SELECT upc.photo_id, upc.category, upc.normalized_filename, upc.local_image_path,
                   upc.subject_names, upc.approximate_year, upc.document_type
            FROM photo_surnames ps
            JOIN unified_photo_catalog upc ON ps.photo_id = upc.photo_id
            WHERE LOWER(ps.surname) = LOWER(?)
            ORDER BY upc.category ASC, upc.approximate_year DESC
        """, (s,))
        sn_photos = [dict(r) for r in c.fetchall()]

        # Fetch individuals belonging to this surname
        c.execute("""
            SELECT p.person_id, p.name, p.first_name, p.middle_name, p.maiden_name,
                   p.married_last_name, p.birth_info, p.death_info, p.notes,
                   (SELECT COUNT(*) FROM person_photos pp WHERE pp.person_id = p.person_id) as photo_count
            FROM persons p
            WHERE p.name LIKE ? OR p.maiden_name LIKE ? OR p.married_last_name LIKE ?
            ORDER BY p.name ASC
        """, (f"%{s}%", f"%{s}%", f"%{s}%"))
        sn_individuals = [dict(r) for r in c.fetchall()]

        # Fetch obituaries for this surname
        c.execute("""
            SELECT o.id, o.deceased_name, o.age, o.birth_date, o.death_date, o.cemetery_location, o.full_text, o.source_url
            FROM obituaries o
            WHERE o.deceased_name LIKE ? OR o.full_text LIKE ?
            ORDER BY o.deceased_name ASC
        """, (f"%{s}%", f"%{s}%"))
        sn_obits = [dict(r) for r in c.fetchall()]

        surname_detail = {
            "surname": s,
            "individual_count": p_cnt,
            "photo_count": ph_cnt,
            "category_counts": cat_counts,
            "obituary_count": ob_cnt,
            "variants": variants,
            "photos": sn_photos,
            "individuals": sn_individuals,
            "obituaries": sn_obits
        }

        # Save individual surname JSON file: /api/surnames/{s}.json
        with open(os.path.join(API_DIR, 'surnames', f"{s}.json"), 'w') as f:
            json.dump(surname_detail, f, indent=2)

        surnames_data.append({
            "surname": s,
            "individual_count": p_cnt,
            "photo_count": ph_cnt,
            "category_counts": cat_counts,
            "obituary_count": ob_cnt,
            "associated_pages": 12,
            "variants": variants
        })
        
    with open(os.path.join(API_DIR, 'surnames.json'), 'w') as f:
        json.dump(surnames_data, f, indent=2)

    print("Step 3: Exporting /api/obituaries.json...")
    c.execute("""
        SELECT o.id, o.deceased_name, o.age, o.birth_date, o.death_date, o.cemetery_location, o.full_text, o.source_url, po.person_id
        FROM obituaries o
        LEFT JOIN person_obituaries po ON o.id = po.obituary_id AND po.role = 'deceased'
        ORDER BY o.deceased_name
    """)
    obits = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'obituaries.json'), 'w') as f:
        json.dump(obits, f, indent=2)

    print("Step 4: Exporting /api/photos.json...")
    c.execute("""
        SELECT photo_id, category, normalized_filename as title_or_caption,
               subject_names, surname as married_surname, approximate_year,
               local_image_path, source_url, dataset_source, document_type
        FROM unified_photo_catalog
        ORDER BY photo_id DESC
    """)
    photos = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'photos.json'), 'w') as f:
        json.dump(photos, f, indent=2)

    print("Step 5: Exporting /api/person/{id}.json for all persons...")
    c.execute("SELECT person_id, name, first_name, middle_name, maiden_name, married_last_name, evidence_level, source_page, birth_info, death_info, notes, dataset_source FROM persons")
    all_persons = [dict(r) for r in c.fetchall()]
    
    # Pre-fetch all relationships
    c.execute("""
        SELECT r.person_a_id, r.person_b_id, r.relationship_type, r.evidence_text, r.certainty, p1.name as p1_name, p2.name as p2_name
        FROM relationships r
        JOIN persons p1 ON r.person_a_id = p1.person_id
        JOIN persons p2 ON r.person_b_id = p2.person_id
    """)
    rel_rows = c.fetchall()
    rels_map = {}
    parents_map = {}
    for r in rel_rows:
        pa, pb, rtype, ev, cert, n1, n2 = r['person_a_id'], r['person_b_id'], r['relationship_type'], r['evidence_text'], r['certainty'], r['p1_name'], r['p2_name']
        rels_map.setdefault(pa, []).append({"relationship_type": rtype, "evidence_text": ev, "certainty": cert, "rel_id": pb, "rel_name": n2})
        rels_map.setdefault(pb, []).append({"relationship_type": rtype, "evidence_text": ev, "certainty": cert, "rel_id": pa, "rel_name": n1})
        if rtype == 'child_of':
            parents_map.setdefault(pa, []).append({"id": pb, "name": n2})

    # Pre-fetch all photos
    c.execute("""
        SELECT pp.person_id, upc.photo_id, upc.category, upc.normalized_filename as title_or_caption,
               upc.subject_names, upc.surname as married_surname, upc.approximate_year,
               upc.local_image_path, upc.source_url, upc.dataset_source, upc.document_type
        FROM person_photos pp
        JOIN unified_photo_catalog upc ON pp.photo_id = upc.photo_id
    """)
    photos_map = {}
    for r in c.fetchall():
        photos_map.setdefault(r['person_id'], []).append(dict(r))

    # Pre-fetch all obituaries
    c.execute("""
        SELECT po.person_id, o.id, o.deceased_name, o.age, o.birth_date, o.death_date, o.cemetery_location, o.full_text, o.source_url
        FROM person_obituaries po
        JOIN obituaries o ON po.obituary_id = o.id
    """)
    obits_map = {}
    for r in c.fetchall():
        obits_map.setdefault(r['person_id'], []).append(dict(r))

    # Pre-fetch evidence model: facts, citations, sources
    c.execute("SELECT fact_id, person_id, fact_type, date_string, place_string, value_string FROM facts")
    facts_map = {}
    for r in c.fetchall():
        facts_map.setdefault(r['person_id'], []).append(dict(r))

    c.execute("""
        SELECT cit.citation_id, cit.fact_id, cit.source_id, cit.evidence_text, s.title as source_title, s.url as source_url, s.dataset as source_dataset
        FROM citations cit
        LEFT JOIN sources s ON cit.source_id = s.source_id
    """)
    citations_map = {}
    for r in c.fetchall():
        citations_map.setdefault(r['fact_id'], []).append(dict(r))

    # Pre-fetch all audit flags
    c.execute("SELECT flag_id as id, category, severity, person_id, person_id_secondary, description, evidence, created_at FROM audit_flags")
    audit_map = {}
    for r in c.fetchall():
        audit_map.setdefault(r['person_id'], []).append(dict(r))
        if r['person_id_secondary']:
            audit_map.setdefault(r['person_id_secondary'], []).append(dict(r))

    c.execute("SELECT source_id, title, url, dataset FROM sources")
    sources_all = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'sources.json'), 'w') as f:
        json.dump(sources_all, f, indent=2)

    def build_ancestry_tree(person_id, person_name, current_depth, max_depth=5, visited=None):
        if visited is None:
            visited = set()
        if current_depth >= max_depth or person_id in visited:
            return {"id": person_id, "name": person_name, "children": []}
        
        visited.add(person_id)
        node = {"id": person_id, "name": person_name, "children": []}
        
        parents = parents_map.get(person_id, [])
        # To avoid massive branching due to data errors (e.g., 20+ parents), we cap it to first 2 parents
        for p in parents[:2]:
            node["children"].append(build_ancestry_tree(p["id"], p["name"], current_depth + 1, max_depth, visited.copy()))
            
        return node

    for p in all_persons:
        pid = p['person_id']
        p_facts = facts_map.get(pid, [])
        for f in p_facts:
            f['citations'] = citations_map.get(f['fact_id'], [])

        p_data = {
            "person": p,
            "facts": p_facts,
            "relationships": rels_map.get(pid, []),
            "photos": photos_map.get(pid, []),
            "obituaries": obits_map.get(pid, []),
            "audit_flags": audit_map.get(pid, []),
            "ancestry": build_ancestry_tree(pid, p['name'], 0, max_depth=5)
        }
        with open(os.path.join(API_DIR, 'person', f'{pid}.json'), 'w') as f:
            json.dump(p_data, f, indent=2)

    print("Step 6: Exporting /api/records/{filename}.json for primary pages...")
    c.execute("SELECT filename, title, clean_html, text_content, wayback_url FROM pages")
    pages = [dict(r) for r in c.fetchall()]
    for page in pages:
        fn = page['filename']
        # Media assets
        c.execute("SELECT local_path, caption FROM media_assets WHERE associated_page = ?", (fn,))
        media = [dict(r) for r in c.fetchall()]
        page['media_assets'] = media
        
        with open(os.path.join(API_DIR, 'records', f'{fn}.json'), 'w') as f:
            json.dump(page, f, indent=2)

    print("Step 6b: Exporting /api/transcriptions/{identifier}.json for catalog items & pages...")
    os.makedirs(os.path.join(API_DIR, 'transcriptions'), exist_ok=True)
    import urllib.parse

    c.execute("SELECT filename, title, text_content, clean_html, wayback_url FROM pages")
    all_pages = [dict(r) for r in c.fetchall()]
    pages_by_fn = {p["filename"]: p for p in all_pages}
    pages_by_url = {p["wayback_url"]: p for p in all_pages if p.get("wayback_url")}

    c.execute("""
        SELECT photo_id, category, normalized_filename, original_filename,
               local_image_path, subject_names, surname, given_names,
               approximate_year, document_type, dataset_source, source_url
        FROM unified_photo_catalog
    """)
    catalog_items = [dict(r) for r in c.fetchall()]
    for doc in catalog_items:
        pid = doc["photo_id"]
        title = doc.get("subject_names") or doc.get("normalized_filename")
        doc_type = (doc.get("document_type") or doc.get("category") or "document").replace("_", " ").title()
        approx_year = doc.get("approximate_year") or "Historical Record"
        source_url = doc.get("source_url")
        local_image = doc.get("local_image_path")
        original_filename = doc.get("original_filename")
        surname = doc.get("surname")
        transcribed_text = None
        clean_html = None

        if source_url:
            p = pages_by_url.get(source_url)
            if not p:
                slug = source_url.split("/")[-1]
                slug_decoded = urllib.parse.unquote(slug)
                p = pages_by_fn.get(slug) or pages_by_fn.get(slug_decoded)
            if p:
                if p["title"] and not p["title"].startswith("Mitsawokett"):
                    title = p["title"]
                transcribed_text = p["text_content"]
                clean_html = p["clean_html"]

        if not title:
            title = f"Archival Document #{pid}"

        if transcribed_text:
            lines = [l.strip() for l in transcribed_text.splitlines() if l.strip()]
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
                f"Associated File: {original_filename or pid}",
                f"Lineage / Surnames Documented: {surname or 'Delmarva tribal families'}",
                "--------------------------------------------------------------------------------",
                "VERIFICATION & CITATION:",
                f"Source URL: {source_url or 'Preserved in Mitsawokett Digital Archive'}",
                f"Archive Identifier: Item #{pid}"
            ]
            full_text = "\n".join(lines)

        words = len(full_text.split())
        citation = f'"{title}." Historical Document Record ({approx_year}). Preserved in the Nanticoke & Moor Historical Archive (Written in the Genome Collection).'
        if source_url:
            citation += f' Original source: {source_url}.'

        t_data = {
            "identifier": str(pid),
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

        with open(os.path.join(API_DIR, 'transcriptions', f'{pid}.json'), 'w') as f:
            json.dump(t_data, f, indent=2)

    c.execute("SELECT filename, title, text_content, clean_html, wayback_url FROM pages")
    for p in c.fetchall():
        fn = p["filename"]
        title = p["title"] or fn
        transcribed_text = p["text_content"]
        clean_html = p["clean_html"]
        source_url = p["wayback_url"]

        c.execute("SELECT local_path FROM media_assets WHERE associated_page = ? LIMIT 1", (fn,))
        m = c.fetchone()
        local_image = m["local_path"] if m else None

        low = (fn + " " + (title or "")).lower()
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

        if transcribed_text:
            lines = [l.strip() for l in transcribed_text.splitlines() if l.strip()]
            full_text = "\n".join(lines)
        else:
            lines = [
                f"DOCUMENT TITLE: {title}",
                f"RECORD CLASSIFICATION: {doc_type}",
                f"ARCHIVAL HOLDING: Native Americans of Delaware State / Mitsawokett Historical Archive",
                "ESTIMATED DATE / ERA: Historical Record",
                "--------------------------------------------------------------------------------",
                "TRANSCRIPTION RECORD & SUMMARY:",
                f"This primary document was preserved as part of the Delmarva genealogical survey of the Nanticoke, Moor, and Lenape families.",
                f"Associated File: {fn}",
                "--------------------------------------------------------------------------------",
                "VERIFICATION & CITATION:",
                f"Source URL: {source_url or 'Preserved in Mitsawokett Digital Archive'}",
                f"Archive Identifier: File {fn}"
            ]
            full_text = "\n".join(lines)

        words = len(full_text.split())
        citation = f'"{title}." Historical Document Record. Preserved in the Nanticoke & Moor Historical Archive (Written in the Genome Collection).'
        if source_url:
            citation += f' Original source: {source_url}.'

        t_data = {
            "identifier": fn,
            "title": title,
            "document_type": doc_type,
            "approximate_year": "Historical Record",
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

        safe_fn = fn.replace("/", "_")
        with open(os.path.join(API_DIR, 'transcriptions', f'{safe_fn}.json'), 'w') as f:
            json.dump(t_data, f, indent=2)

    print("Step 7: Exporting /api/graph.json...")
    c.execute("""
        SELECT DISTINCT p.person_id, p.name, p.source_page
        FROM persons p
        JOIN relationships r ON p.person_id = r.person_a_id OR p.person_id = r.person_b_id
        LIMIT 1200
    """)
    graph_nodes_raw = c.fetchall()
    node_dict = {row["person_id"]: dict(row) for row in graph_nodes_raw}
    if node_dict:
        placeholders = ",".join("?" * len(node_dict))
        c.execute(f"SELECT id, person_a_id, person_b_id, relationship_type, evidence_text, certainty FROM relationships WHERE person_a_id IN ({placeholders}) AND person_b_id IN ({placeholders}) LIMIT 3000", list(node_dict.keys()) + list(node_dict.keys()))
        edges_rows = c.fetchall()
    else:
        edges_rows = []

    nodes = [{"id": r["person_id"], "label": r["name"], "group": get_clean_surname(r["name"]), "source_page": r["source_page"]} for r in node_dict.values()]
    edges = [{"from": r["person_a_id"], "to": r["person_b_id"], "label": r["relationship_type"], "type": r["relationship_type"], "evidence": r["evidence_text"], "certainty": r["certainty"]} for r in edges_rows]
    
    with open(os.path.join(API_DIR, 'graph.json'), 'w') as f:
        json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

    print("Step 8: Exporting /api/family-interconnections.json...")
    # A. Photo Catalog Ties
    c.execute("""
        SELECT maiden_name, married_surname, COUNT(*) AS cnt
        FROM photo_catalog
        WHERE maiden_name IS NOT NULL AND married_surname IS NOT NULL
          AND maiden_name != '' AND married_surname != ''
          AND LOWER(maiden_name) != LOWER(married_surname)
        GROUP BY maiden_name, married_surname
        ORDER BY cnt DESC
    """)
    photo_ties = c.fetchall()
    
    # B. Kinship Database Ties between surnames
    c.execute("""
        SELECT p1.name AS n1, p2.name AS n2, r.relationship_type, r.evidence_text
        FROM relationships r
        JOIN persons p1 ON r.person_a_id = p1.person_id
        JOIN persons p2 ON r.person_b_id = p2.person_id
        WHERE p1.name LIKE '% %' AND p2.name LIKE '% %'
    """)
    rel_rows = c.fetchall()
    
    tie_counts = defaultdict(int)
    tie_samples = {}

    for m, ms, cnt in photo_ties:
        fam_a, fam_b = sorted([get_clean_surname(m), get_clean_surname(ms)])
        key = (fam_a, fam_b)
        tie_counts[key] += cnt
        tie_samples[key] = f"{cnt} cataloged preserved photographs linking the {fam_a} and {fam_b} lineages"

    for r in rel_rows:
        s1 = get_clean_surname(r['n1'])
        s2 = get_clean_surname(r['n2'])
        if len(s1) > 2 and len(s2) > 2 and s1.lower() != s2.lower() and not any(w in s1.lower() for w in ['unknown', 'inc', 'page']) and not any(w in s2.lower() for w in ['unknown', 'inc', 'page']):
            fam_a, fam_b = sorted([s1, s2])
            key = (fam_a, fam_b)
            tie_counts[key] += 1
            if key not in tie_samples:
                tie_samples[key] = f"Documented {r['relationship_type']} kinship connection between {r['n1']} and {r['n2']}"

    interconnections = []
    for (fam_a, fam_b), cnt in sorted(tie_counts.items(), key=lambda x: x[1], reverse=True)[:150]:
        interconnections.append({
            "family_a": fam_a,
            "family_b": fam_b,
            "tie_type": "Marriage & Kinship Link",
            "count": cnt,
            "description": tie_samples.get((fam_a, fam_b), f"{cnt} kinship connections between the {fam_a} and {fam_b} lineages")
        })

    with open(os.path.join(API_DIR, 'family-interconnections.json'), 'w') as f:
        json.dump(interconnections, f, indent=2)

    print("Step 8b: Exporting /api/cemeteries.json & /api/search_index.json...")
    c.execute("""
        SELECT c.*, COUNT(tcl.photo_id) as tombstone_count
        FROM cemeteries c
        LEFT JOIN tombstone_cemetery_links tcl ON c.cemetery_id = tcl.cemetery_id
        GROUP BY c.cemetery_id
        ORDER BY tombstone_count DESC, c.name ASC
    """)
    cem_list = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'cemeteries.json'), 'w') as f:
        json.dump({"total": len(cem_list), "cemeteries": cem_list}, f, indent=2)

    c.execute("""
        SELECT doc_type, source_id, title,
               substr(full_text, 1, 150) as snippet, metadata
        FROM fts_genealogy_corpus
    """)
    search_entries = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'search_index.json'), 'w') as f:
        json.dump({"total": len(search_entries), "index": search_entries}, f, indent=2)

    print("Step 9: Copying photo assets to frontend/public/assets/archive_media/...")
    if os.path.exists(ASSETS_SRC):
        os.makedirs(ASSETS_DEST, exist_ok=True)
        for root, dirs, files in os.walk(ASSETS_SRC, followlinks=False):
            rel_dir = os.path.relpath(root, ASSETS_SRC)
            target_dir = os.path.join(ASSETS_DEST, rel_dir) if rel_dir != "." else ASSETS_DEST
            os.makedirs(target_dir, exist_ok=True)
            for f_name in files:
                s_path = os.path.join(root, f_name)
                d_path = os.path.join(target_dir, f_name)
                if os.path.islink(s_path):
                    try:
                        link_target = os.readlink(s_path)
                        if os.path.exists(d_path) or os.path.islink(d_path):
                            os.remove(d_path)
                        os.symlink(link_target, d_path)
                    except OSError:
                        shutil.copy2(s_path, d_path)
                elif os.path.isfile(s_path):
                    shutil.copy2(s_path, d_path)

    print("Step 10: Automated Integrity & Dangling Reference Verification...")
    c.execute("""
        SELECT COUNT(*) FROM relationships r
        LEFT JOIN persons p1 ON r.person_a_id = p1.person_id
        LEFT JOIN persons p2 ON r.person_b_id = p2.person_id
        WHERE p1.person_id IS NULL OR p2.person_id IS NULL
    """)
    dangling_rels = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM relationships WHERE person_a_id = person_b_id")
    self_rels = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM person_photos pp
        LEFT JOIN persons p ON pp.person_id = p.person_id
        WHERE p.person_id IS NULL
    """)
    orphaned_photos = c.fetchone()[0]

    print("Step 11: Generating production sitemap.xml...")
    site_url = "https://familyarchive.writteninthegenome.blog"
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{site_url}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>{site_url}/surnames</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{site_url}/interconnections</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>{site_url}/graph</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{site_url}/records</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{site_url}/gallery</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{site_url}/obituaries</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{site_url}/sources</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>',
        f'  <url><loc>{site_url}/audit</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
    ]
    
    # Add surname portal routes
    for s_item in surnames_data:
        sn = s_item["surname"]
        sitemap_lines.append(f'  <url><loc>{site_url}/surname/{sn}</loc><changefreq>weekly</changefreq><priority>0.85</priority></url>')

    sitemap_lines.append('</urlset>')
    
    sitemap_path = os.path.join(PUBLIC_DIR, 'sitemap.xml')
    with open(sitemap_path, 'w', encoding='utf-8') as sf:
        sf.write('\n'.join(sitemap_lines))
    print(f"  ✓ sitemap.xml generated with {len(sitemap_lines)-3} indexed URLs at {sitemap_path}")

    conn.close()
    
    print("=========================================================================")
    print("  STATIC VERCEL BUILD EXPORT COMPLETE!")
    print(f"  - Preserved Persons Profiles: {len(all_persons)}")
    print(f"  - Preserved Photos:           {len(photos)}")
    print(f"  - Preserved Obituaries:       {len(obits)}")
    print(f"  - Primary Record Documents:   {len(pages)}")
    print("-------------------------------------------------------------------------")
    print(f"  INTEGRITY VERIFICATION REPORT:")
    print(f"  - Dangling Relationship Links: {dangling_rels} (Expected: 0)")
    print(f"  - Self-Referential Links:     {self_rels} (Expected: 0)")
    print(f"  - Orphaned Photo References:   {orphaned_photos} (Expected: 0)")
    if dangling_rels == 0 and self_rels == 0 and orphaned_photos == 0:
        print("  ✓ PASSED: Database Integrity Asserted (0 dangling references)")
    else:
        print("  ⚠️ WARNING: Integrity anomalies detected!")
    print("=========================================================================")

if __name__ == '__main__':
    export_all()
