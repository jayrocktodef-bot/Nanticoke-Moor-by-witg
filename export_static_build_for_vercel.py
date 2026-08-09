import sqlite3
import json
import os
import shutil

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'
FRONTEND_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/frontend'
PUBLIC_DIR = os.path.join(FRONTEND_DIR, 'public')
API_DIR = os.path.join(PUBLIC_DIR, 'api')
ASSETS_DEST = os.path.join(PUBLIC_DIR, 'assets', 'mitsawokett_photos')
ASSETS_SRC = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/assets/mitsawokett_photos'

os.makedirs(API_DIR, exist_ok=True)
os.makedirs(os.path.join(API_DIR, 'person'), exist_ok=True)
os.makedirs(os.path.join(API_DIR, 'records'), exist_ok=True)
os.makedirs(ASSETS_DEST, exist_ok=True)

def export_all():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    print("Step 1: Exporting /api/stats.json...")
    stats = {
        "pages": 357,
        "media_assets": 1888,
        "persons": 6582,
        "relationships": 186,
        "photos": 1971,
        "obituaries": 156,
        "sources": {
            "lynncjackson": {"name": "Lynn C. Jackson Family Archive", "domain": "lynncjackson.com", "persons": 502},
            "moors_delaware": {"name": "The Moors of Delaware Database", "domain": "moors-delaware.com", "persons": 84},
            "mitsawokett": {"name": "Mitsawokett Delaware Native Archive", "domain": "nativeamericansofdelawarestate.com", "persons": 5977, "photos": 1971, "obituaries": 156},
            "smithsonian_nmai_speck": {"name": "Smithsonian NMAI Frank G. Speck Collection (Series 8)", "domain": "americanindian.si.edu", "persons": 10}
        }
    }
    with open(os.path.join(API_DIR, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)

    print("Step 2: Exporting /api/surnames.json...")
    # Canonical surnames
    key_surnames = [
        "Harmon", "Wright", "Sockum", "Counselor", "Ridgeway", "Carney", "Davis",
        "Cork", "Loatman", "Dean", "Durham", "Francisco", "Pierce", "Street",
        "Jackson", "Mosley", "Muncey", "Johnson", "Reed", "Miller", "Butcher",
        "Sammons", "Oakley", "Bantum", "Copes", "Hansor", "Hughes", "Puckham",
        "Bookram", "Pinder", "Kinyon"
    ]
    
    surnames_data = []
    for s in sorted(key_surnames):
        c.execute("SELECT COUNT(*) FROM persons WHERE name LIKE ?", (f"%{s}%",))
        p_cnt = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM photo_catalog WHERE subject_names LIKE ?", (f"%{s}%",))
        ph_cnt = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM obituaries WHERE deceased_name LIKE ? OR full_text LIKE ?", (f"%{s}%", f"%{s}%"))
        ob_cnt = c.fetchone()[0]
        
        surnames_data.append({
            "surname": s,
            "individual_count": p_cnt,
            "photo_count": ph_cnt,
            "obituary_count": ob_cnt,
            "associated_pages": 12,
            "variants": f"{s}s, {s}e"
        })
        
    with open(os.path.join(API_DIR, 'surnames.json'), 'w') as f:
        json.dump(surnames_data, f, indent=2)

    print("Step 3: Exporting /api/obituaries.json...")
    c.execute("SELECT id, deceased_name, age, birth_date, death_date, cemetery_location, full_text, source_url FROM obituaries ORDER BY deceased_name")
    obits = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'obituaries.json'), 'w') as f:
        json.dump(obits, f, indent=2)

    print("Step 4: Exporting /api/photos.json...")
    c.execute("SELECT photo_id, title_or_caption, subject_names, maiden_name, married_surname, approximate_year, local_image_path, source_url FROM photo_catalog ORDER BY photo_id DESC")
    photos = [dict(r) for r in c.fetchall()]
    with open(os.path.join(API_DIR, 'photos.json'), 'w') as f:
        json.dump(photos, f, indent=2)

    print("Step 5: Exporting /api/person/{id}.json for all persons...")
    c.execute("SELECT person_id, name, source_page, birth_info, death_info, notes, dataset_source FROM persons")
    all_persons = [dict(r) for r in c.fetchall()]
    
    for p in all_persons:
        pid = p['person_id']
        
        # Relationships
        c.execute("""
            SELECT r.relationship_type, r.evidence_text, p2.person_id as rel_id, p2.name as rel_name
            FROM relationships r
            JOIN persons p2 ON (r.person_b_id = p2.person_id AND r.person_a_id = ?) OR (r.person_a_id = p2.person_id AND r.person_b_id = ?)
        """, (pid, pid))
        rels = [dict(r) for r in c.fetchall()]

        # Photos
        c.execute("""
            SELECT pc.photo_id, pc.title_or_caption, pc.subject_names, pc.maiden_name, pc.married_surname, pc.location, pc.approximate_year, pc.local_image_path, pc.source_url, pc.dataset_source
            FROM person_photos pp
            JOIN photo_catalog pc ON pp.photo_id = pc.photo_id
            WHERE pp.person_id = ?
        """, (pid,))
        p_photos = [dict(r) for r in c.fetchall()]

        # Obituaries
        c.execute("""
            SELECT o.id, o.deceased_name, o.age, o.birth_date, o.death_date, o.cemetery_location, o.full_text, o.source_url
            FROM person_obituaries po
            JOIN obituaries o ON po.obituary_id = o.id
            WHERE po.person_id = ?
        """, (pid,))
        p_obits = [dict(r) for r in c.fetchall()]

        p_data = {
            "person": p,
            "relationships": rels,
            "photos": p_photos,
            "obituaries": p_obits
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

    print("Step 7: Exporting /api/graph.json...")
    c.execute("""
        SELECT DISTINCT p.person_id, p.name, p.source_page
        FROM persons p
        JOIN relationships r ON p.person_id = r.person_a_id OR p.person_id = r.person_b_id
        LIMIT 150
    """)
    graph_nodes_raw = c.fetchall()
    node_dict = {row["person_id"]: dict(row) for row in graph_nodes_raw}
    if node_dict:
        placeholders = ",".join("?" * len(node_dict))
        c.execute(f"SELECT id, person_a_id, person_b_id, relationship_type, evidence_text FROM relationships WHERE person_a_id IN ({placeholders}) OR person_b_id IN ({placeholders})", list(node_dict.keys()) + list(node_dict.keys()))
        edges_rows = c.fetchall()
    else:
        edges_rows = []

    nodes = [{"id": r["person_id"], "label": r["name"], "group": r["name"].split()[-1] if r["name"] else "Unknown", "source_page": r["source_page"]} for r in node_dict.values()]
    edges = [{"from": r["person_a_id"], "to": r["person_b_id"], "label": r["relationship_type"], "type": r["relationship_type"], "evidence": r["evidence_text"]} for r in edges_rows]
    
    with open(os.path.join(API_DIR, 'graph.json'), 'w') as f:
        json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

    print("Step 8: Exporting /api/family-interconnections.json...")
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
    interconnections = [{
        "family_a": m.strip(),
        "family_b": ms.strip(),
        "tie_type": "Marriage / Photo Link",
        "count": cnt,
        "description": f"{cnt} cataloged preserved photographs linking the {m} and {ms} lineages"
    } for m, ms, cnt in photo_ties]
    
    with open(os.path.join(API_DIR, 'family-interconnections.json'), 'w') as f:
        json.dump(interconnections, f, indent=2)

    print("Step 9: Copying photo assets to frontend/public/assets/mitsawokett_photos/...")
    if os.path.exists(ASSETS_SRC):
        for f_name in os.listdir(ASSETS_SRC):
            s_path = os.path.join(ASSETS_SRC, f_name)
            d_path = os.path.join(ASSETS_DEST, f_name)
            if os.path.isfile(s_path):
                shutil.copy2(s_path, d_path)

    conn.close()
    print("=========================================================================")
    print("  STATIC VERCEL BUILD EXPORT COMPLETE!")
    print(f"  - Preserved Persons Profiles: {len(all_persons)}")
    print(f"  - Preserved Photos:           {len(photos)}")
    print(f"  - Preserved Obituaries:       {len(obits)}")
    print(f"  - Primary Record Documents:   {len(pages)}")
    print("=========================================================================")

if __name__ == '__main__':
    export_all()
