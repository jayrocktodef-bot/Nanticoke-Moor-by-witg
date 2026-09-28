#!/usr/bin/env python3
"""
Step 2: Digital Preservation Fixity & OAIS Packaging (RFC 8493 BagIt Standard)
Generates BagIt 1.0 compliant manifests, tagmanifests, and preservation metadata.
Produces an immutable canonical database snapshot (genealogy_preservation_canonical.db)
via VACUUM INTO so that live database queries and audit logs do not mutate the preserved image.
"""

import os
import hashlib
import datetime
import sqlite3
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
CANONICAL_DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation_canonical.db")
LEDGER_PATH = os.path.join(OUTPUT_DIR, "fixity_audit_ledger.jsonl")

BAG_DIR = OUTPUT_DIR

PAYLOAD_SUBDIRS = [
    "assets/archive_media/documents",
    "assets/archive_media/family_trees",
    "assets/archive_media/people",
    "assets/archive_media/tombstones",
    "ancestry_documents/delaware_census",
    "genealogy_preservation_canonical.db"
]

def calculate_sha256(filepath, chunk_size=65536):
    """Compute cryptographic SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def ensure_fixity_table(db_path):
    """Create the fixity_audit_log table if not present."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fixity_audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_timestamp TEXT NOT NULL,
            total_files_checked INTEGER NOT NULL,
            total_bytes_checked INTEGER NOT NULL,
            passed_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            missing_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            details_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_canonical_db_snapshot():
    """Create a pristine, defragmented immutable snapshot of the active database."""
    print(f"Creating canonical immutable database snapshot: {CANONICAL_DB_PATH}...")
    if os.path.exists(CANONICAL_DB_PATH):
        os.remove(CANONICAL_DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"VACUUM INTO '{CANONICAL_DB_PATH}'")
    conn.close()
    
    size_mb = os.path.getsize(CANONICAL_DB_PATH) / (1024 * 1024)
    print(f"Canonical snapshot created successfully ({size_mb:.2f} MB).")

def generate_bagit_manifest():
    ensure_fixity_table(DB_PATH)
    create_canonical_db_snapshot()

    manifest_entries = []
    total_bytes = 0
    total_files = 0

    print("Hashing preservation assets for RFC 8493 BagIt manifest...")

    for item in PAYLOAD_SUBDIRS:
        full_path = os.path.join(BAG_DIR, item)
        if not os.path.exists(full_path):
            print(f"Warning: path does not exist: {full_path}")
            continue

        if os.path.isfile(full_path):
            file_hash = calculate_sha256(full_path)
            file_size = os.path.getsize(full_path)
            rel_path = os.path.relpath(full_path, BAG_DIR)
            manifest_entries.append((file_hash, rel_path))
            total_bytes += file_size
            total_files += 1
        else:
            for root, _, files in os.walk(full_path):
                for f in sorted(files):
                    file_path = os.path.join(root, f)
                    if not os.path.isfile(file_path):
                        continue
                    file_hash = calculate_sha256(file_path)
                    file_size = os.path.getsize(file_path)
                    rel_path = os.path.relpath(file_path, BAG_DIR)
                    manifest_entries.append((file_hash, rel_path))
                    total_bytes += file_size
                    total_files += 1
                    if total_files % 500 == 0:
                        print(f"  Hashed {total_files} files ({total_bytes / (1024*1024):.1f} MB)...")

    # Sort manifest deterministically by relative path
    manifest_entries.sort(key=lambda x: x[1])

    # 1. Write manifest-sha256.txt
    manifest_path = os.path.join(BAG_DIR, "manifest-sha256.txt")
    with open(manifest_path, "w", encoding="utf-8") as f:
        for fhash, rpath in manifest_entries:
            f.write(f"{fhash}  {rpath}\n")
    print(f"Wrote {len(manifest_entries)} entries to {manifest_path}")

    # 2. Write bagit.txt
    bagit_path = os.path.join(BAG_DIR, "bagit.txt")
    with open(bagit_path, "w", encoding="utf-8") as f:
        f.write("BagIt-Version: 1.0\n")
        f.write("Tag-File-Character-Encoding: UTF-8\n")
    print(f"Wrote {bagit_path}")

    # 3. Write bag-info.txt
    bag_size_mb = f"{total_bytes / (1024 * 1024):.2f} MB"
    payload_oxum = f"{total_bytes}.{total_files}"
    today = datetime.date.today().isoformat()

    bag_info_path = os.path.join(BAG_DIR, "bag-info.txt")
    with open(bag_info_path, "w", encoding="utf-8") as f:
        f.write(f"Bag-Software-Agent: Antigravity-OAIS-Preservation-Engine/2.0\n")
        f.write(f"Bagging-Date: {today}\n")
        f.write(f"Payload-Oxum: {payload_oxum}\n")
        f.write(f"Bag-Size: {bag_size_mb}\n")
        f.write(f"Source-Organization: Lynn Jackson Delmarva Family Archive / Written In The Genome\n")
        f.write(f"Organization-Address: Millsboro, Sussex County, Delaware\n")
        f.write(f"Contact-Name: Jequan\n")
        f.write(f"External-Description: Preservation package containing verified historical documents, family portraits, census enumerations, cemetery tombstones, and SQLite relational database of the Nanticoke, Moor, Lenape, and Delmarva lineages.\n")
        f.write(f"Preservation-Standard: OAIS ISO 14721 / RFC 8493\n")
    print(f"Wrote {bag_info_path}")

    # 4. Write tagmanifest-sha256.txt
    tagmanifest_path = os.path.join(BAG_DIR, "tagmanifest-sha256.txt")
    tag_files = ["bagit.txt", "bag-info.txt", "manifest-sha256.txt"]
    with open(tagmanifest_path, "w", encoding="utf-8") as f:
        for tf in tag_files:
            tf_path = os.path.join(BAG_DIR, tf)
            tf_hash = calculate_sha256(tf_path)
            f.write(f"{tf_hash}  {tf}\n")
    print(f"Wrote {tagmanifest_path}")

    # 5. Log generation to SQLite fixity_audit_log and JSONL ledger
    timestamp = datetime.datetime.now().isoformat()
    log_data = {
        "timestamp": timestamp,
        "action": "BagIt 1.0 Manifest Generated",
        "bag_size": bag_size_mb,
        "payload_oxum": payload_oxum,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "status": "INITIALIZED"
    }

    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data) + "\n")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO fixity_audit_log (
            audit_timestamp, total_files_checked, total_bytes_checked, passed_count, failed_count, missing_count, status, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        total_files,
        total_bytes,
        total_files,
        0,
        0,
        "INITIALIZED",
        json.dumps(log_data)
    ))
    conn.commit()
    conn.close()

    print(f"\nBagIt 1.0 Packaging Complete:")
    print(f"  Total Files : {total_files}")
    print(f"  Total Bytes : {total_bytes:,} bytes ({bag_size_mb})")
    print(f"  Payload Oxum: {payload_oxum}")
    print(f"  Status      : INITIALIZED")

if __name__ == "__main__":
    generate_bagit_manifest()
