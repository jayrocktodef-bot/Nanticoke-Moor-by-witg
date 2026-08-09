import sqlite3
from fuzzywuzzy import fuzz
conn = sqlite3.connect('/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db')
c = conn.cursor()
c.execute("SELECT person_id, name FROM persons")
persons = c.fetchall()
person_list = []
for pid, name in persons:
    person_list.append((pid, name or ""))
    
c.execute("SELECT photo_id, subject_names FROM photo_catalog WHERE dataset_source = 'mitsawokett'")
photos = c.fetchall()

links_created = 0
for photo_id, subject_names in photos:
    if not subject_names: continue
    best_match_id = None
    best_score = 0
    for pid, name in person_list:
        score = fuzz.token_set_ratio(subject_names, name)
        if score > best_score and score >= 80:
            best_score = score
            best_match_id = pid
    if best_match_id is not None:
        c.execute("INSERT INTO person_photos (person_id, photo_id, confidence_score) VALUES (?, ?, ?)", 
                  (best_match_id, photo_id, best_score / 100.0))
        links_created += 1
conn.commit()
print(f"Created {links_created} person_photo links.")

c.execute("SELECT maiden_name, COUNT(*) FROM photo_catalog GROUP BY maiden_name ORDER BY COUNT(*) DESC LIMIT 10")
print("\nTop Surnames:")
for name, cnt in c.fetchall():
    print(f"  {name}: {cnt}")
    
conn.close()
