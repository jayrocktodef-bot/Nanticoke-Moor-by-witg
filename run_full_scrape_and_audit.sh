#!/bin/bash
set -e
echo "Starting full scrape..."
python3 scrape_mitsawokett.py
python3 scrape_mitsawokett_photos_v2.py
python3 scrape_moors_delaware.py
python3 scrape_obituaries.py

echo "Starting cleaning and deduplication..."
python3 clean_person_names_v2.py
python3 purge_phrase_names_and_fix_database.py
python3 sanitize_and_dedup_persons.py
python3 build_relationship_graph.py
python3 fix_surname_first_names.py
python3 auto_merge_all_duplicates_and_purge_junk.py

echo "Migrating to Evidence & Citation Model..."
python3 migrate_evidence_model.py

echo "Running NLP Document Allocation..."
python3 auto_allocate_documents.py

echo "Running FindAGrave Cross-Reference Sweep..."
python3 cross_reference_findagrave.py

echo "Running audits..."
python3 genealogy_audit.py
python3 run_audit_suite.py

echo "Exporting static build for UI..."
python3 export_static_build_for_vercel.py

echo "Exporting canonical archive to GEDCOM X XML..."
python3 export_gedcomx.py

echo "Done!"
