import sqlite3
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

DB_PATH = 'preservation_output/genealogy_preservation.db'
OUTPUT_DIR = 'preservation_output/profiles'

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def export_to_gedcomx():
    print("Exporting database to individual GEDCOM X XML profiles using Strict Evidence Model...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Cache sources
    c.execute("SELECT source_id, title, url FROM sources")
    sources = {r['source_id']: r for r in c.fetchall()}

    # Group facts by person
    c.execute("SELECT fact_id, person_id, fact_type, date_string, place_string, value_string FROM facts")
    all_facts = c.fetchall()
    facts_by_person = defaultdict(list)
    for f in all_facts:
        facts_by_person[f['person_id']].append(f)

    # Group citations by fact
    c.execute("SELECT fact_id, source_id, evidence_text FROM citations")
    all_citations = c.fetchall()
    citations_by_fact = defaultdict(list)
    for cit in all_citations:
        citations_by_fact[cit['fact_id']].append(cit)

    # Group relationships by person
    c.execute("SELECT id, person_a_id, person_b_id, relationship_type, evidence_text FROM relationships")
    relationships = c.fetchall()
    rels_by_person = defaultdict(list)
    for r in relationships:
        rels_by_person[r['person_a_id']].append(r)
        rels_by_person[r['person_b_id']].append(r)

    # Fetch persons
    c.execute("SELECT person_id FROM persons")
    persons = c.fetchall()

    for p in persons:
        pid = p['person_id']
        gedcomx = ET.Element('gedcomx', xmlns="http://gedcomx.org/v1/")
        
        person_elem = ET.SubElement(gedcomx, 'person', id=f"p_{pid}")
        
        person_sources = set()

        for f in facts_by_person.get(pid, []):
            ftype = f['fact_type']
            if ftype == 'Name':
                name_elem = ET.SubElement(person_elem, 'name')
                nameForm_elem = ET.SubElement(name_elem, 'nameForm')
                fullText_elem = ET.SubElement(nameForm_elem, 'fullText')
                fullText_elem.text = f['value_string']
                # Citations for Name
                for cit in citations_by_fact.get(f['fact_id'], []):
                    person_sources.add(cit['source_id'])
                    # For simplicity, attaching source to person root as per GEDCOM X loosely for name
                    ET.SubElement(person_elem, 'source', description=f"#s_{cit['source_id']}")
            else:
                gedcomx_type = f"http://gedcomx.org/{ftype}"
                fact_elem = ET.SubElement(person_elem, 'fact', type=gedcomx_type)
                
                if f['date_string']:
                    date_elem = ET.SubElement(fact_elem, 'date')
                    orig_elem = ET.SubElement(date_elem, 'original')
                    orig_elem.text = f['date_string']
                
                if f['place_string']:
                    place_elem = ET.SubElement(fact_elem, 'place')
                    orig_elem = ET.SubElement(place_elem, 'original')
                    orig_elem.text = f['place_string']
                    
                if f['value_string']:
                    val_elem = ET.SubElement(fact_elem, 'value')
                    val_elem.text = f['value_string']
                
                # Citations for Fact
                for cit in citations_by_fact.get(f['fact_id'], []):
                    person_sources.add(cit['source_id'])
                    ET.SubElement(fact_elem, 'source', description=f"#s_{cit['source_id']}")

        # Relationships
        added_rels = set()
        for r in rels_by_person.get(pid, []):
            if r['id'] in added_rels:
                continue
            added_rels.add(r['id'])
            
            rel_type = r['relationship_type']
            gedcomx_type = "http://gedcomx.org/Unknown"

            if rel_type in ["child_of", "parent_of"]:
                gedcomx_type = "http://gedcomx.org/ParentChild"
            elif rel_type == "spouse":
                gedcomx_type = "http://gedcomx.org/Couple"

            rel_elem = ET.SubElement(gedcomx, 'relationship', type=gedcomx_type)
            ET.SubElement(rel_elem, 'person1', resource=f"#p_{r['person_a_id']}")
            ET.SubElement(rel_elem, 'person2', resource=f"#p_{r['person_b_id']}")

            if r['evidence_text']:
                note_elem = ET.SubElement(rel_elem, 'note')
                text_elem = ET.SubElement(note_elem, 'text')
                text_elem.text = f"Evidence: {r['evidence_text']}"

        # Build Source Descriptions
        for sid in person_sources:
            s_data = sources.get(sid)
            if s_data:
                desc_elem = ET.SubElement(gedcomx, 'sourceDescription', id=f"s_{sid}")
                ET.SubElement(desc_elem, 'about', resource=s_data['url'] if s_data['url'] else '')
                title_elem = ET.SubElement(desc_elem, 'title')
                title_elem.text = s_data['title']

        # Save individual file
        file_path = os.path.join(OUTPUT_DIR, f"person_{pid}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prettify(gedcomx))

    conn.close()
    print(f"Exported {len(persons)} evidence-backed GEDCOM X XML profiles to {OUTPUT_DIR}.")

if __name__ == "__main__":
    export_to_gedcomx()
