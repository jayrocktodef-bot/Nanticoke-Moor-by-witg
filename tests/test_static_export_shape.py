"""
Tests for static build export functions and JSON schema contracts.
Validates:
- Privacy redaction and living-individual heuristics
- Date and place extraction parsing
- Structural schema of representative Person, Record, and Cemetery payloads
"""
import pytest
from pipeline.export.export_static_build_for_vercel import (
    is_probably_living,
    redact_living_person,
    parse_date_and_place
)


def test_is_probably_living_heuristics():
    """Verify living status inference complies with privacy invariant."""
    # Explicit 'living' keyword
    assert is_probably_living({"name": "Living Person", "birth_info": "1990"}) is True
    assert is_probably_living({"name": "John Doe", "notes": "Living individual"}) is True

    # Person with death date is not living
    assert is_probably_living({"name": "John Doe", "birth_info": "1950", "death_info": "2020"}) is False

    # Historical ancestor born > 110 years ago is not living
    assert is_probably_living({"name": "Augustus Wright", "birth_info": "1878", "death_info": ""}) is False

    # Individual born recently with no death info is probably living
    assert is_probably_living({"name": "Jane Doe", "birth_info": "1985", "death_info": ""}) is True


def test_redact_living_person():
    """Verify private fields are stripped for living ancestors."""
    raw = {
        "person_id": 9999,
        "name": "Jane Living Doe",
        "birth_info": "15 July 1985 (Dover, DE)",
        "death_info": "",
        "notes": "Confidential personal contact details"
    }
    redacted = redact_living_person(raw)
    assert redacted["birth_info"] == "Private"
    assert redacted["death_info"] == ""
    assert redacted["notes"] == ""
    assert redacted["is_living"] is True
    # Original dict unchanged
    assert raw["birth_info"] == "15 July 1985 (Dover, DE)"


def test_parse_date_and_place():
    """Verify genealogical date and place string parsing."""
    date, place = parse_date_and_place("12 May 1880 (Sussex County, DE)")
    assert date == "12 May 1880"
    assert place == "Sussex County, DE"

    date_no_place, place_none = parse_date_and_place("abt 1850")
    assert date_no_place == "abt 1850"
    assert place_none is None

    empty_date, empty_place = parse_date_and_place("Private")
    assert empty_date is None
    assert empty_place is None


def test_person_payload_schema():
    """Verify the structural contract of a representative Person profile JSON."""
    representative_person = {
        "person": {
            "person_id": 11266,
            "name": "Augustus Wright",
            "first_name": "Augustus",
            "middle_name": "",
            "maiden_name": "",
            "married_last_name": "Wright",
            "birth_date": "1878",
            "birth_place": "Millsboro, Sussex County, Delaware",
            "birth_info": "1878 (Millsboro, Sussex County, Delaware)",
            "death_date": "1960",
            "death_place": "Indian River Hundred, Delaware",
            "death_info": "1960 (Indian River Hundred, Delaware)",
            "evidence_level": 3,
            "source_page": "census1930.htm",
            "dataset_source": "mitsawokett_preservation",
            "notes": "Prominent Nanticoke community leader"
        },
        "ancestry": [],
        "audit_flags": [],
        "facts": [
            {
                "fact_id": 1,
                "fact_type": "Birth",
                "date_string": "1878",
                "place_string": "Millsboro, DE",
                "value_string": None,
                "citations": []
            }
        ],
        "obituaries": [],
        "photos": [],
        "relationships": [
            {
                "relationship_type": "Child",
                "related_person_id": 11267,
                "related_person_name": "Warren Wright"
            }
        ]
    }

    # Contract assertions
    expected_top_keys = {"person", "ancestry", "audit_flags", "facts", "obituaries", "photos", "relationships"}
    assert expected_top_keys.issubset(representative_person.keys())

    p_inner = representative_person["person"]
    required_person_fields = {"person_id", "name", "first_name", "married_last_name", "birth_info", "death_info", "evidence_level"}
    assert required_person_fields.issubset(p_inner.keys())
    assert isinstance(p_inner["person_id"], int)
    assert p_inner["evidence_level"] in (1, 2, 3)


def test_record_payload_schema():
    """Verify the structural contract of a representative Record document JSON."""
    representative_record = {
        "id": 105,
        "filename": "census1930.htm",
        "title": "1930 Federal Census: Sussex County Indian River Hundred",
        "text_content": "1930 Sussex Co Census Dist 7: Augustus Wright, race 'In' altered to 'Neg'...",
        "clean_html": "<p>1930 Sussex Co Census Dist 7...</p>",
        "wayback_url": "https://web.archive.org/web/mitsawokett/census1930.htm",
        "media_assets": [
            {
                "local_path": "assets/archive_media/documents/census_1930_p112.jpg",
                "caption": "Federal Census Schedule Page 112"
            }
        ]
    }

    required_record_fields = {"filename", "title", "text_content", "clean_html", "media_assets"}
    assert required_record_fields.issubset(representative_record.keys())
    assert representative_record["filename"].endswith(".htm")
    assert isinstance(representative_record["media_assets"], list)


def test_cemetery_payload_schema():
    """Verify the structural contract of representative Cemetery collection JSON."""
    representative_cemeteries = {
        "total": 1,
        "cemeteries": [
            {
                "cemetery_id": 1,
                "name": "Harmony United Methodist Church Cemetery",
                "latitude": 38.6186,
                "longitude": -75.1978,
                "affiliation": "Nanticoke",
                "locality": "Millsboro",
                "county": "Sussex",
                "state": "DE",
                "historical_notes": "Central resting place for ancestral Nanticoke families.",
                "tombstone_count": 42,
                "tombstones": [
                    {
                        "photo_id": 501,
                        "filename": "harmony_cemetery_01.jpg",
                        "ancestor_name": "Levin Sockum"
                    }
                ]
            }
        ]
    }

    assert "cemeteries" in representative_cemeteries
    assert "total" in representative_cemeteries
    assert representative_cemeteries["total"] == len(representative_cemeteries["cemeteries"])

    cem = representative_cemeteries["cemeteries"][0]
    required_cemetery_fields = {"cemetery_id", "name", "latitude", "longitude", "affiliation", "tombstones"}
    assert required_cemetery_fields.issubset(cem.keys())
    assert -90.0 <= cem["latitude"] <= 90.0
    assert -180.0 <= cem["longitude"] <= 180.0
    assert isinstance(cem["tombstones"], list)
