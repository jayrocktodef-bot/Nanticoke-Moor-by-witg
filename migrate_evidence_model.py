import sqlite3
import os

DB_PATH = 'preservation_output/genealogy_preservation.db'

def migrate_to_evidence_model():
    print("Migrating flat database to strict Evidence and Citation model...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Create Evidence Tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            dataset TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            fact_type TEXT NOT NULL,
            date_string TEXT,
            place_string TEXT,
            value_string TEXT,
            FOREIGN KEY(person_id) REFERENCES persons(person_id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS citations (
            citation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER,
            source_id INTEGER,
            evidence_text TEXT,
            FOREIGN KEY(fact_id) REFERENCES facts(fact_id),
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        )
    """)
    
    # 2. Clear existing evidence data if script is re-run
    c.execute("DELETE FROM citations")
    c.execute("DELETE FROM facts")
    c.execute("DELETE FROM sources")

    # 3. Populate Sources from unique source_pages
    c.execute("SELECT DISTINCT source_page, dataset_source FROM persons WHERE source_page IS NOT NULL")
    source_rows = c.fetchall()
    
    source_map = {}
    for row in source_rows:
        spage, dataset = row
        title = f"Record: {spage}" if spage else "Unknown Source"
        c.execute("INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)", (title, spage, dataset))
        source_id = c.lastrowid
        source_map[spage] = source_id
        
    # 4. Migrate Facts and Citations from Persons
    c.execute("SELECT person_id, name, birth_info, death_info, source_page FROM persons")
    persons = c.fetchall()
    
    for p in persons:
        pid = p[0]
        name = p[1]
        binfo = p[2]
        dinfo = p[3]
        spage = p[4]
        
        sid = source_map.get(spage)
        
        # Name Fact
        if name:
            c.execute("INSERT INTO facts (person_id, fact_type, value_string) VALUES (?, 'Name', ?)", (pid, name))
            fid = c.lastrowid
            if sid:
                c.execute("INSERT INTO citations (fact_id, source_id) VALUES (?, ?)", (fid, sid))
                
        # Birth Fact
        if binfo:
            c.execute("INSERT INTO facts (person_id, fact_type, date_string) VALUES (?, 'Birth', ?)", (pid, binfo))
            fid = c.lastrowid
            if sid:
                c.execute("INSERT INTO citations (fact_id, source_id) VALUES (?, ?)", (fid, sid))
                
        # Death Fact
        if dinfo:
            c.execute("INSERT INTO facts (person_id, fact_type, date_string) VALUES (?, 'Death', ?)", (pid, dinfo))
            fid = c.lastrowid
            if sid:
                c.execute("INSERT INTO citations (fact_id, source_id) VALUES (?, ?)", (fid, sid))

    conn.commit()
    
    # Get stats
    c.execute("SELECT count(*) FROM sources")
    print(f"Sources generated: {c.fetchone()[0]}")
    c.execute("SELECT count(*) FROM facts")
    print(f"Facts generated: {c.fetchone()[0]}")
    c.execute("SELECT count(*) FROM citations")
    print(f"Citations generated: {c.fetchone()[0]}")
    
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_to_evidence_model()
