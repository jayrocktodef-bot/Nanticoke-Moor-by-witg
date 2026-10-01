"""
Tests for BagIt packaging, SHA-256 manifest generation, and OAIS fixity verification.
Uses tmp_path and ephemeral fixtures — never touches production database or preservation assets.
"""
import os
import sqlite3
import pytest
from pipeline.export.generate_bagit_package import (
    calculate_sha256,
    generate_bagit_manifest,
    ensure_fixity_table
)
from pipeline.export.verify_bagit_fixity import verify_fixity


def test_calculate_sha256(tmp_path):
    """Test standard cryptographic SHA-256 digest calculation."""
    test_file = tmp_path / "hello.txt"
    test_file.write_bytes(b"hello world")
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert calculate_sha256(str(test_file)) == expected


def test_bagit_manifest_and_fixity_workflow(tmp_path):
    """Test full cycle: dummy payload creation -> BagIt packaging -> Fixity verification."""
    # 1. Setup small fixture directory
    bag_dir = tmp_path / "bag"
    bag_dir.mkdir()
    data_dir = bag_dir / "assets"
    data_dir.mkdir()

    file_a = data_dir / "portrait_1.txt"
    file_a.write_text("historical portrait data A", encoding="utf-8")
    file_b = data_dir / "document_1.txt"
    file_b.write_text("historical land deed verbatim text B", encoding="utf-8")

    db_path = tmp_path / "test_preservation.db"
    ensure_fixity_table(str(db_path))

    # 2. Generate BagIt manifest
    payload_items = ["assets/portrait_1.txt", "assets/document_1.txt"]
    result = generate_bagit_manifest(
        bag_dir=str(bag_dir),
        db_path=str(db_path),
        payload_subdirs=payload_items,
        skip_db_snapshot=True
    )

    assert result["total_files"] == 2
    assert os.path.exists(bag_dir / "manifest-sha256.txt")
    assert os.path.exists(bag_dir / "bagit.txt")
    assert os.path.exists(bag_dir / "bag-info.txt")
    assert os.path.exists(bag_dir / "tagmanifest-sha256.txt")

    # Verify bagit.txt content
    bagit_content = (bag_dir / "bagit.txt").read_text(encoding="utf-8")
    assert "BagIt-Version: 1.0" in bagit_content
    assert "UTF-8" in bagit_content

    # 3. Verify fixity passes on pristine package
    status = verify_fixity(
        bag_dir=str(bag_dir),
        db_path=str(db_path),
        exit_on_failure=False
    )
    assert status == "PASSED"

    # Verify fixity logged in SQLite table
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT status FROM fixity_audit_log ORDER BY audit_id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "PASSED"


def test_fixity_tamper_detection(tmp_path):
    """Test that verify_fixity detects altered or corrupted payload files."""
    bag_dir = tmp_path / "tamper_bag"
    bag_dir.mkdir()
    data_file = bag_dir / "census_record.txt"
    data_file.write_text("Original 1860 census entry", encoding="utf-8")

    db_path = tmp_path / "audit.db"
    ensure_fixity_table(str(db_path))

    generate_bagit_manifest(
        bag_dir=str(bag_dir),
        db_path=str(db_path),
        payload_subdirs=["census_record.txt"],
        skip_db_snapshot=True
    )

    # Tamper with the payload file
    data_file.write_text("Tampered or corrupted content", encoding="utf-8")

    status = verify_fixity(
        bag_dir=str(bag_dir),
        db_path=str(db_path),
        exit_on_failure=False
    )
    assert status == "FAILED"
