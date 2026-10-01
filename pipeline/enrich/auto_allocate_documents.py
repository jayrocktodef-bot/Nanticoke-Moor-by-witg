import sqlite3
import spacy
from thefuzz import fuzz
from thefuzz import process
import re

DB_PATH = 'preservation_output/genealogy_preservation.db'

def get_or_create_source(c, title, url, dataset):
    c.execute("SELECT source_id FROM sources WHERE title = ? OR url = ?", (title, url))
    res = c.fetchone()
    if res:
        return res[0]
    c.execute("INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)", (title, url, dataset))
    return c.lastrowid

def get_primary_name_fact(c, person_id):
    c.execute("SELECT fact_id FROM facts WHERE person_id = ? AND fact_type = 'Name' LIMIT 1", (person_id,))
    res = c.fetchone()
    return res[0] if res else None

def auto_allocate():
    print("Loading spaCy NLP model (en_core_web_sm)...")
    nlp = spacy.load("en_core_web_sm")
    
    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Load known persons
    c.execute("SELECT person_id, name FROM persons WHERE name IS NOT NULL")
    person_rows = c.fetchall()
    person_dict = {row['name']: row['person_id'] for row in person_rows}
    person_names = list(person_dict.keys())
    
    print(f"Loaded {len(person_names)} known persons for fuzzy matching.")

    # Process Obituaries
    c.execute("SELECT id, deceased_name, full_text, source_url FROM obituaries WHERE full_text IS NOT NULL")
    obits = c.fetchall()

    new_citations = 0
    new_relationships = 0

    print(f"Scanning {len(obits)} obituaries...")
    for obit in obits:
        text = obit['full_text']
        source_id = get_or_create_source(c, f"Obituary: {obit['deceased_name']}", obit['source_url'], "mitsawokett_obits")
        
        doc = nlp(text)
        entities = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        
        for ent_name in set(entities):
            # Clean up entity name
            clean_name = re.sub(r'[^A-Za-z ]+', '', ent_name).strip()
            if len(clean_name) < 4: continue
                
            # Fuzzy Match against database
            match = process.extractOne(clean_name, person_names, scorer=fuzz.token_sort_ratio)
            if match and match[1] > 90:
                matched_person_name = match[0]
                person_id = person_dict[matched_person_name]
                
                # Add Citation to Person Profile
                fact_id = get_primary_name_fact(c, person_id)
                if fact_id:
                    # Check if citation exists
                    c.execute("SELECT citation_id FROM citations WHERE fact_id = ? AND source_id = ?", (fact_id, source_id))
                    if not c.fetchone():
                        c.execute("INSERT INTO citations (fact_id, source_id, evidence_text) VALUES (?, ?, ?)", 
                                  (fact_id, source_id, f"Detected in Obituary of {obit['deceased_name']}"))
                        new_citations += 1

                # Relationship verification (Very simplified: if deceased matches a known person, and this entity is another known person)
                # Check if deceased is known
                dec_match = process.extractOne(obit['deceased_name'], person_names, scorer=fuzz.token_sort_ratio)
                if dec_match and dec_match[1] > 90 and dec_match[0] != matched_person_name:
                    dec_person_id = person_dict[dec_match[0]]
                    
                    # See if kinship term is nearby in text
                    # Find index of ent_name in text
                    ent_idx = text.find(ent_name)
                    if ent_idx != -1:
                        window = text[max(0, ent_idx-50):ent_idx+len(ent_name)+50].lower()
                        kinship_types = {
                            "wife": "spouse", "husband": "spouse", "widow": "spouse",
                            "son": "child_of", "daughter": "child_of", "child": "child_of",
                            "father": "parent_of", "mother": "parent_of", "parent": "parent_of"
                        }
                        
                        detected_rel = None
                        for term, rtype in kinship_types.items():
                            if term in window:
                                detected_rel = rtype
                                break
                                
                        if detected_rel:
                            # Verify or add connection
                            c.execute("""
                                SELECT id FROM relationships 
                                WHERE (person_a_id = ? AND person_b_id = ?) 
                                   OR (person_a_id = ? AND person_b_id = ?)
                            """, (dec_person_id, person_id, person_id, dec_person_id))
                            
                            if not c.fetchone():
                                c.execute("INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text, certainty) VALUES (?, ?, ?, ?, 'inferred_nlp')",
                                          (dec_person_id, person_id, detected_rel, f"NLP Extracted from Obituary: '{window}'"))
                                new_relationships += 1
                                
    conn.commit()
    conn.close()
    
    print(f"NLP Scan Complete!")
    print(f"-> Generated {new_citations} new verified source citations.")
    print(f"-> Discovered & connected {new_relationships} new family relationships.")

if __name__ == "__main__":
    auto_allocate()
