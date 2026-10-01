"""
Tests for GEDCOM X XML exporter.
Uses ephemeral in-memory / tmp_path SQLite fixtures without modifying production database.
"""
import os
import sqlite3
import xml.etree.ElementTree as ET
import pytest
from pipeline.export.export_gedcomx import export_to_gedcomx, prettify


def test_prettify_xml():
    """Verify XML pretty-printing format and indentation."""
    root = ET.Element("gedcomx", xmlns="http://gedcomx.org/v1/")
    ET.SubElement(root, "person", id="p_1")
    xml_str = prettify(root)
    assert 'xmlns="http://gedcomx.org/v1/"' in xml_str
    assert '<person id="p_1"' in xml_str


def test_export_to_gedcomx_workflow(tmp_path):
    """Verify GEDCOM X generation from SQLite schema into valid XML files."""
    db_path = tmp_path / "test_genealogy.db"
    out_dir = tmp_path / "gedcomx_profiles"

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE persons (
            person_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE sources (
            source_id INTEGER PRIMARY KEY,
            title TEXT,
            url TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE facts (
            fact_id INTEGER PRIMARY KEY,
            person_id INTEGER,
            fact_type TEXT,
            date_string TEXT,
            place_string TEXT,
            value_string TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE citations (
            citation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER,
            source_id INTEGER,
            evidence_text TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_a_id INTEGER,
            person_b_id INTEGER,
            relationship_type TEXT,
            evidence_text TEXT
        )
    """)

    # Seed representative ancestor
    cur.execute("INSERT INTO persons (person_id, name) VALUES (101, 'Levin Sockum')")
    cur.execute("INSERT INTO persons (person_id, name) VALUES (102, 'Hannah Sockum')")
    cur.execute("INSERT INTO sources (source_id, title, url) VALUES (1, '1860 Sussex Co Census', 'https://example.com/census1860')")
    cur.execute("""
        INSERT INTO facts (fact_id, person_id, fact_type, date_string, place_string, value_string)
        VALUES (1, 101, 'Name', NULL, NULL, 'Levin Sockum')
    """)
    cur.execute("""
        INSERT INTO facts (fact_id, person_id, fact_type, date_string, place_string, value_string)
        VALUES (2, 101, 'Birth', 'abt 1805', 'Long Neck, Sussex County, Delaware', NULL)
    """)
    cur.execute("INSERT INTO citations (fact_id, source_id, evidence_text) VALUES (2, 1, 'Verbatim census excerpt: Levin Sockum, age 55, farmer.')")
    cur.execute("""
        INSERT INTO relationships (person_a_id, person_b_id, relationship_type, evidence_text)
        VALUES (101, 102, 'Spouse', 'Married in Delaware')
    """)
    conn.commit()
    conn.close()

    # Run exporter against test fixture
    export_to_gedcomx(db_path=str(db_path), output_dir=str(out_dir))

    # Verify generated XML
    xml_path = out_dir / "person_101.xml"
    assert os.path.exists(xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Namespace check
    assert "gedcomx" in root.tag
    
    # Person element check
    person_elem = root.find("{http://gedcomx.org/v1/}person")
    assert person_elem is not None
    assert person_elem.attrib.get("id") == "p_101"

    # Facts check
    facts = person_elem.findall("{http://gedcomx.org/v1/}fact")
    assert len(facts) >= 1
    birth_fact = next(f for f in facts if f.attrib.get("type") == "http://gedcomx.org/Birth")
    date_elem = birth_fact.find("{http://gedcomx.org/v1/}date/{http://gedcomx.org/v1/}original")
    place_elem = birth_fact.find("{http://gedcomx.org/v1/}place/{http://gedcomx.org/v1/}original")
    assert date_elem.text == "abt 1805"
    assert "Sussex County" in place_elem.text

    # Citation source reference check
    source_ref = birth_fact.find("{http://gedcomx.org/v1/}source")
    assert source_ref is not None
    assert source_ref.attrib.get("description") == "#s_1"

    # Source description check
    src_desc = root.find("{http://gedcomx.org/v1/}sourceDescription")
    assert src_desc is not None
    assert src_desc.attrib.get("id") == "s_1"
