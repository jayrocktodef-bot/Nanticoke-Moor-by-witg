#!/usr/bin/env python3
"""
integrate_census_documents.py

Integrates scraped Ancestry.com Delaware Census records into:
1. SQLite database (unified_photo_catalog and photo_catalog)
2. Person linkages (matching Davis ancestors)
3. Frontend transcription JSONs for the Document Drawer
"""

import json
import os
import glob
import re
import sqlite3
import hashlib

DOCS_DIR = "preservation_output/ancestry_documents/delaware_census"
DB_PATH = "preservation_output/genealogy_preservation.db"
FRONTEND_PUBLIC_DIR = "frontend/public"
FRONTEND_TRANSCRIPTIONS_DIR = "frontend/public/api/transcriptions"

EXPLICIT_DAVIS_ALIASES = {
    "charleymdavis": (8676, "Charles Charlie Morris Davis"),
    "charlesmdavis": (8676, "Charles Charlie Morris Davis"),
    "charlesdavis": (8676, "Charles Charlie Morris Davis"),
    "charlescharliedavis": (8676, "Charles Charlie Morris Davis"),
    "berthamdavis": (8675, "Bertha M Davis"),
    "berthamaydavis": (8675, "Bertha M Davis"),
    "carmenthisdavis": (10087, "Albert Davis"),
    "albertcarmenthisdavis": (10087, "Albert Davis"),
    "albertdavis": (10087, "Albert Davis"),
    "delphinadavis": (8182, "Delphine Mae Davis"),
    "delphinedavis": (8182, "Delphine Mae Davis"),
    "delphinemaedavis": (8182, "Delphine Mae Davis"),
    "clarencedavis": (10813, "Clarence Drexel Davis"),
    "clarenceddavis": (10813, "Clarence Drexel Davis"),
    "clerencedoris": (10813, "Clarence Drexel Davis"),
    "carmerthusdoris": (10087, "Albert Davis"),
    "augustusdoris": (10087, "Albert Davis"),
    "alonzodavis": (4574, "Alonzo Davis"),
    "alonzofdavis": (4574, "Alonzo Davis"),
    "mauricedavis": (8676, "Charles Charlie Morris Davis"),
    "williamhdavis": (10618, "William H Davis"),
    "williamhenrydavis": (4867, "William Henry Davis Jr"),
    "robertdavis": (11871, "Robert Davis Jr"),
    "robertdavisjr": (11871, "Robert Davis Jr"),
}

def get_person_matches(conn):
    """Map normalized names and Davis variants to person_ids in persons table."""
    c = conn.cursor()
    c.execute("SELECT person_id, name, birth_info, death_info FROM persons WHERE LOWER(name) LIKE '%davis%'")
    rows = c.fetchall()
    
    person_map = {}
    for pid, name, birth, death in rows:
        clean_name = re.sub(r'^(front--|children:|niece|nephew|widow)\s*', '', name, flags=re.IGNORECASE).strip()
        norm = re.sub(r'[^a-zA-Z0-9]', '', clean_name.lower())
        person_map[norm] = {"pid": pid, "name": name, "birth": birth, "death": death}
        
        parts = clean_name.split()
        if len(parts) >= 2:
            first_last = f"{parts[0]} {parts[-1]}".lower()
            norm_fl = re.sub(r'[^a-zA-Z0-9]', '', first_last)
            if norm_fl not in person_map:
                person_map[norm_fl] = {"pid": pid, "name": name, "birth": birth, "death": death}
                
    return person_map

def find_best_person_match(person_name, person_map):
    norm = re.sub(r'[^a-zA-Z0-9]', '', person_name.lower())
    if norm in EXPLICIT_DAVIS_ALIASES:
        pid, name = EXPLICIT_DAVIS_ALIASES[norm]
        return {"pid": pid, "name": name}

    if norm in person_map:
        return person_map[norm]
        
    parts = person_name.split()
    if len(parts) >= 2:
        norm_fl = re.sub(r'[^a-zA-Z0-9]', '', f"{parts[0]} {parts[-1]}".lower())
        if norm_fl in EXPLICIT_DAVIS_ALIASES:
            pid, name = EXPLICIT_DAVIS_ALIASES[norm_fl]
            return {"pid": pid, "name": name}
        if norm_fl in person_map:
            return person_map[norm_fl]
            
    # Fuzzy substring
    for k, v in person_map.items():
        if len(parts) > 0 and parts[0].lower() in k and "davis" in k:
            return v
            
    return None

def format_markdown_transcription(meta):
    year = meta.get("census_year", "Census")
    pname = meta.get("person_name", "Household")
    fields = meta.get("fields", {})
    citation = meta.get("citation", "")
    household = meta.get("household", [])
    
    location = fields.get(f"Home in {year}", fields.get("Residence", "Sussex County, Delaware"))
    race = fields.get("Race", "Not Specified")
    
    md = []
    md.append(f"## {year} United States Federal Census - {pname} Household")
    md.append(f"**Jurisdiction**: {location}")
    if citation:
        md.append(f"**Archival Citation**: {citation}")
    md.append("")
    
    md.append("### Individual Classification")
    md.append(f"- **Primary Name**: {pname}")
    md.append(f"- **Age in {year}**: {fields.get('Age', 'N/A')}")
    md.append(f"- **Birthplace**: {fields.get('Birthplace', 'Delaware')}")
    md.append(f"- **Racial Designation**: `{race}`")
    md.append(f"- **Marital Status**: {fields.get('Marital Status', 'N/A')}")
    md.append(f"- **Relation to Head of House**: {fields.get('Relation to Head of House', 'N/A')}")
    if "Father's Name" in fields:
        md.append(f"- **Father's Name**: {fields['Father\'s Name']}")
    if "Mother's Name" in fields:
        md.append(f"- **Mother's Name**: {fields['Mother\'s Name']}")
    if "Occupation" in fields:
        md.append(f"- **Occupation**: {fields['Occupation']}")
    md.append("")
    
    # Household members table
    if len(household) > 1:
        md.append("### Household Members")
        md.append("| Name | Age | Relationship |")
        md.append("| :--- | :--- | :--- |")
        for row in household[1:]:
            if len(row) >= 3:
                md.append(f"| {row[0]} | {row[1]} | {row[2]} |")
            elif len(row) == 2:
                md.append(f"| {row[0]} | {row[1]} | Member |")
        md.append("")
        
    md.append("---")
    md.append("*Source: Ancestry.com Delaware Federal Census Archive & NARA Microfilm Scans.*")
    return "\n".join(md)

def run_integration():
    os.makedirs(FRONTEND_TRANSCRIPTIONS_DIR, exist_ok=True)
    json_files = glob.glob(os.path.join(DOCS_DIR, "*.json"))
    print(f"Found {len(json_files)} census metadata records in {DOCS_DIR}")
    
    conn = sqlite3.connect(DB_PATH)
    person_map = get_person_matches(conn)
    c = conn.cursor()
    
    # Get max photo_id
    c.execute("SELECT COALESCE(MAX(photo_id), 0) FROM unified_photo_catalog")
    next_id = c.fetchone()[0] + 1
    
    integrated_count = 0
    updated_count = 0
    
    for jf in sorted(json_files):
        with open(jf, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        pname = meta.get("person_name", "")
        year = meta.get("census_year", "")
        record_id = meta.get("record_id", "")
        coll_id = meta.get("collection_id", "")
        image_file = meta.get("image_file")
        
        # Resolve image file if null
        if not image_file:
            possible_jpgs = [f for f in os.listdir(DOCS_DIR) if f.endswith(".jpg")]
            for pj in possible_jpgs:
                if pj in jf or pj.split(".")[0] in json.dumps(meta):
                    image_file = pj
                    meta["image_file"] = pj
                    with open(jf, "w", encoding="utf-8") as fw:
                        json.dump(meta, fw, indent=2)
                    break
                    
        match = find_best_person_match(pname, person_map)
        matched_pid = match["pid"] if match else None
        matched_name = match["name"] if match else pname
        
        markdown_transcript = format_markdown_transcription(meta)
        title = f"{year} Federal Census - {pname} Household"
        fields = meta.get("fields", {})
        location = fields.get(f"Home in {year}", fields.get("Residence", "Sussex County, Delaware"))
        
        local_rel_path = f"ancestry_documents/delaware_census/{image_file}" if image_file else ""
        full_img_path = os.path.join(DOCS_DIR, image_file) if image_file else None
        
        file_size = os.path.getsize(full_img_path) if (full_img_path and os.path.exists(full_img_path)) else 0
        sha256 = ""
        if full_img_path and os.path.exists(full_img_path):
            with open(full_img_path, "rb") as bf:
                sha256 = hashlib.sha256(bf.read()).hexdigest()
                
        source_url = meta.get("source_url", "")
        c.execute("SELECT photo_id FROM unified_photo_catalog WHERE source_url = ?", (source_url,))
        existing = c.fetchone()
        
        if existing:
            photo_id = existing[0]
            # Update linkage if improved
            c.execute('''
                UPDATE unified_photo_catalog
                SET primary_person_id = COALESCE(?, primary_person_id),
                    primary_person_name = COALESCE(?, primary_person_name),
                    local_image_path = CASE WHEN local_image_path = '' THEN ? ELSE local_image_path END,
                    normalized_filename = CASE WHEN normalized_filename LIKE '%.json' THEN ? ELSE normalized_filename END,
                    file_size_bytes = CASE WHEN file_size_bytes = 0 THEN ? ELSE file_size_bytes END,
                    transcription = ?
                WHERE photo_id = ?
            ''', (matched_pid, matched_name, local_rel_path, image_file or os.path.basename(jf), file_size, markdown_transcript, photo_id))
            
            c.execute('''
                UPDATE photo_catalog
                SET primary_person_id = COALESCE(?, primary_person_id),
                    primary_person_name = COALESCE(?, primary_person_name),
                    local_image_path = CASE WHEN local_image_path = '' THEN ? ELSE local_image_path END,
                    transcript = ?
                WHERE photo_id = ?
            ''', (matched_pid, matched_name, local_rel_path, markdown_transcript, photo_id))
            updated_count += 1
        else:
            photo_id = next_id
            next_id += 1
            
            c.execute('''
                INSERT INTO unified_photo_catalog (
                    photo_id, category, normalized_filename, original_filename,
                    local_image_path, sha256_hash, file_size_bytes, mime_type,
                    subject_names, surname, given_names, approximate_year,
                    document_type, dataset_source, source_url, is_primary_copy,
                    asset_type, subtype, confidence_score, contains_face,
                    transcription, dates_mentioned, primary_person_id, primary_person_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                photo_id,
                "documents",
                image_file or os.path.basename(jf),
                image_file or os.path.basename(jf),
                local_rel_path,
                sha256,
                file_size,
                "image/jpeg" if image_file else "application/json",
                title,
                "Davis",
                pname.replace("Davis", "").strip(),
                year,
                "census_record",
                "Ancestry.com Delaware Census Records",
                source_url,
                1,
                "document",
                "census",
                1.0,
                0,
                markdown_transcript,
                year,
                matched_pid,
                matched_name
            ))
            
            c.execute('''
                INSERT INTO photo_catalog (
                    photo_id, title_or_caption, subject_names, location, approximate_year,
                    local_image_path, source_url, dataset_source, media_type, transcript,
                    document_type, asset_type, subtype, confidence_score, dates_mentioned,
                    primary_person_id, primary_person_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                photo_id,
                title,
                title,
                location,
                year,
                local_rel_path,
                source_url,
                "Ancestry.com Delaware Census Records",
                "document",
                markdown_transcript,
                "census_record",
                "document",
                "census",
                1.0,
                year,
                matched_pid,
                matched_name
            ))
            integrated_count += 1
            print(f"  ✓ Registered [Doc #{photo_id}] {title} -> {matched_name} (#{matched_pid})")

        # Ensure photo_surnames has Davis linked
        c.execute("INSERT OR IGNORE INTO photo_surnames (photo_id, surname, is_primary) VALUES (?, ?, 1)", (photo_id, "Davis"))

        # Ensure person_photos has ancestor linked if matched
        if matched_pid:
            c.execute("SELECT id FROM person_photos WHERE person_id = ? AND photo_id = ?", (matched_pid, photo_id))
            if not c.fetchone():
                c.execute("INSERT INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, ?, 1.0)", (matched_pid, photo_id))
            
        # Write frontend transcription json
        trans_data = {
            "document_id": photo_id,
            "title": title,
            "year": year,
            "location": location,
            "person_name": pname,
            "matched_person_id": matched_pid,
            "matched_person_name": matched_name,
            "citation": meta.get("citation", ""),
            "fields": fields,
            "household": meta.get("household", []),
            "markdown": markdown_transcript,
            "image_url": f"/ancestry_documents/delaware_census/{image_file}" if image_file else ""
        }
        
        json_out_path = os.path.join(FRONTEND_TRANSCRIPTIONS_DIR, f"doc_{photo_id}.json")
        with open(json_out_path, "w", encoding="utf-8") as tf:
            json.dump(trans_data, tf, indent=2)

        json_out_id = os.path.join(FRONTEND_TRANSCRIPTIONS_DIR, f"{photo_id}.json")
        with open(json_out_id, "w", encoding="utf-8") as tf:
            json.dump(trans_data, tf, indent=2)
            
    conn.commit()
    conn.close()
    print(f"\n=======================================================")
    print(f"  INTEGRATION COMPLETE: {integrated_count} new, {updated_count} updated census documents linked!")
    print(f"=======================================================\n")

if __name__ == "__main__":
    run_integration()
