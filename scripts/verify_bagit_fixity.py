#!/usr/bin/env python3
"""
Step 2 Verification: Digital Preservation Fixity Auditor
Verifies RFC 8493 BagIt manifests against live files on disk.
Computes cryptographic SHA-256 fixity, detects bit rot or tampering,
and logs the verification run into the database and JSONL ledger.
"""

import os
import hashlib
import datetime
import sqlite3
import json
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
LEDGER_PATH = os.path.join(OUTPUT_DIR, "fixity_audit_ledger.jsonl")
BAG_DIR = OUTPUT_DIR

def calculate_sha256(filepath, chunk_size=65536):
    """Compute cryptographic SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_fixity():
    manifest_path = os.path.join(BAG_DIR, "manifest-sha256.txt")
    tagmanifest_path = os.path.join(BAG_DIR, "tagmanifest-sha256.txt")

    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found at {manifest_path}. Run generate_bagit_package.py first.")
        sys.exit(1)

    # 1. Verify tagmanifest
    tag_errors = []
    if os.path.exists(tagmanifest_path):
        with open(tagmanifest_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    expected_hash, rel_path = parts[0], parts[1].strip()
                    file_path = os.path.join(BAG_DIR, rel_path)
                    if not os.path.exists(file_path):
                        tag_errors.append(f"Missing tag file: {rel_path}")
                    else:
                        actual_hash = calculate_sha256(file_path)
                        if actual_hash != expected_hash:
                            tag_errors.append(f"Tag file checksum mismatch: {rel_path}")

    # 2. Verify payload manifest
    total_files = 0
    total_bytes = 0
    passed_count = 0
    failed_count = 0
    missing_count = 0
    failures = []

    print("Beginning OAIS / BagIt fixity verification...")
    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, 1):
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        expected_hash, rel_path = parts[0], parts[1].strip()
        full_path = os.path.join(BAG_DIR, rel_path)
        total_files += 1

        if not os.path.exists(full_path):
            missing_count += 1
            failures.append({"file": rel_path, "issue": "MISSING"})
            continue

        file_size = os.path.getsize(full_path)
        total_bytes += file_size
        actual_hash = calculate_sha256(full_path)

        if actual_hash == expected_hash:
            passed_count += 1
        else:
            failed_count += 1
            failures.append({
                "file": rel_path,
                "issue": "CORRUPT_OR_MODIFIED",
                "expected": expected_hash,
                "actual": actual_hash
            })

        if idx % 500 == 0 or idx == len(lines):
            print(f"  Verified {idx}/{len(lines)} files ({passed_count} passed, {failed_count} failed, {missing_count} missing)...")

    overall_status = "PASSED" if (failed_count == 0 and missing_count == 0 and len(tag_errors) == 0) else "FAILED"
    timestamp = datetime.datetime.now().isoformat()

    # 3. Log to JSONL ledger
    audit_record = {
        "timestamp": timestamp,
        "action": "Fixity Verification",
        "status": overall_status,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "missing_count": missing_count,
        "tag_errors": tag_errors,
        "failures_sample": failures[:20]
    }
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_record) + "\n")

    # 4. Log to SQLite fixity_audit_log
    conn = sqlite3.connect(DB_PATH)
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
    cur.execute("""
        INSERT INTO fixity_audit_log (
            audit_timestamp, total_files_checked, total_bytes_checked, passed_count, failed_count, missing_count, status, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        total_files,
        total_bytes,
        passed_count,
        failed_count,
        missing_count,
        overall_status,
        json.dumps({
            "tag_errors": tag_errors,
            "failures": failures[:100],
            "total_failures": len(failures)
        })
    ))
    conn.commit()
    conn.close()

    print("\n=== OAIS Fixity Verification Report ===")
    print(f"  Overall Status : {overall_status}")
    print(f"  Files Checked  : {total_files}")
    print(f"  Bytes Checked  : {total_bytes:,} bytes ({total_bytes / (1024*1024):.2f} MB)")
    print(f"  Passed Fixity  : {passed_count}")
    print(f"  Failed Fixity  : {failed_count}")
    print(f"  Missing Assets : {missing_count}")
    if tag_errors:
        print(f"  Tag Manifest Errors: {tag_errors}")

    if overall_status != "PASSED":
        print("  Failures sample:", failures[:5])
        sys.exit(1)

    return overall_status

if __name__ == "__main__":
    verify_fixity()
