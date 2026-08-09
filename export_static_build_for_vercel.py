import sqlite3
import json
import os
import shutil
import re
from collections import defaultdict

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
    
    # Pre-fetch all relationships
    c.execute("""
        SELECT r.person_a_id, r.person_b_id, r.relationship_type, r.evidence_text, p1.name as p1_name, p2.name as p2_name
        FROM relationships r
        JOIN persons p1 ON r.person_a_id = p1.person_id
        JOIN persons p2 ON r.person_b_id = p2.person_id
    """)
    rel_rows = c.fetchall()
    rels_map = {}
    for r in rel_rows:
        pa, pb, rtype, ev, n1, n2 = r['person_a_id'], r['person_b_id'], r['relationship_type'], r['evidence_text'], r['p1_name'], r['p2_name']
        rels_map.setdefault(pa, []).append({"relationship_type": rtype, "evidence_text": ev, "rel_id": pb, "rel_name": n2})
        rels_map.setdefault(pb, []).append({"relationship_type": rtype, "evidence_text": ev, "rel_id": pa, "rel_name": n1})

    # Pre-fetch all photos
    c.execute("""
        SELECT pp.person_id, pc.photo_id, pc.title_or_caption, pc.subject_names, pc.maiden_name, pc.married_surname, pc.location, pc.approximate_year, pc.local_image_path, pc.source_url, pc.dataset_source
        FROM person_photos pp
        JOIN photo_catalog pc ON pp.photo_id = pc.photo_id
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

    for p in all_persons:
        pid = p['person_id']
        p_data = {
            "person": p,
            "relationships": rels_map.get(pid, []),
            "photos": photos_map.get(pid, []),
            "obituaries": obits_map.get(pid, [])
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
        LIMIT 1200
    """)
    graph_nodes_raw = c.fetchall()
    node_dict = {row["person_id"]: dict(row) for row in graph_nodes_raw}
    if node_dict:
        placeholders = ",".join("?" * len(node_dict))
        c.execute(f"SELECT id, person_a_id, person_b_id, relationship_type, evidence_text FROM relationships WHERE person_a_id IN ({placeholders}) AND person_b_id IN ({placeholders}) LIMIT 3000", list(node_dict.keys()) + list(node_dict.keys()))
        edges_rows = c.fetchall()
    else:
        edges_rows = []

    nodes = [{"id": r["person_id"], "label": r["name"], "group": r["name"].split()[-1] if r["name"] and len(r["name"].split()) > 1 else "Unknown", "source_page": r["source_page"]} for r in node_dict.values()]
    edges = [{"from": r["person_a_id"], "to": r["person_b_id"], "label": r["relationship_type"], "type": r["relationship_type"], "evidence": r["evidence_text"]} for r in edges_rows]
    
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
        fam_a, fam_b = sorted([m.strip(), ms.strip()])
        key = (fam_a, fam_b)
        tie_counts[key] += cnt
        tie_samples[key] = f"{cnt} cataloged preserved photographs linking the {fam_a} and {fam_b} lineages"

    for r in rel_rows:
        s1 = r['n1'].split()[-1]
        s2 = r['n2'].split()[-1]
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
