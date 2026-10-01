"""
Tests for citation auto-linker core matching logic:
- HTML cleaning & whitespace normalization
- Verbatim passage extraction with windowing boundaries
- Candidate name variant expansion
- Word boundary enforcement
- Temporal co-occurrence scoring (year proximity boost)
"""
import pytest
from pipeline.enrich.auto_link_primary_documents_and_citations import (
    clean_text,
    extract_excerpt,
    generate_name_variants,
    find_best_name_match
)


def test_clean_text():
    """Verify HTML entities unescaping and whitespace collapsing."""
    raw = "  Augustus &amp; Warren&nbsp;Wright \n\n lived in Sussex &quot;Indian River&quot;  "
    cleaned = clean_text(raw)
    assert cleaned == 'Augustus & Warren Wright lived in Sussex "Indian River"'


def test_clean_text_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""


def test_extract_excerpt():
    """Verify verbatim snippet extraction around match position."""
    doc = (
        "In the year 1880, Augustus Wright of Sussex County, Delaware, was enumerated "
        "as a member of the Nanticoke Indian community, residing near Millsboro."
    )
    pos = doc.find("Augustus Wright")
    match_len = len("Augustus Wright")

    snippet = extract_excerpt(doc, pos, match_len, window=30)
    assert "Augustus Wright" in snippet
    assert "1880" in snippet or "Sussex County" in snippet


def test_generate_name_variants():
    """Verify surname + given name variations generation for cross-document linking."""
    variants = generate_name_variants(
        name="Augustus Wright",
        first="Augustus",
        last="Wright",
        maiden=None
    )
    assert "Augustus Wright" in variants
    assert "Wright, Augustus" in variants

    # Married with maiden
    female_variants = generate_name_variants(
        name="Hannah Clark Harmon",
        first="Hannah",
        last="Harmon",
        maiden="Clark"
    )
    assert "Hannah Clark Harmon" in female_variants
    assert "Hannah Harmon" in female_variants
    assert "Harmon, Hannah" in female_variants
    assert "Hannah Clark" in female_variants


def test_find_best_name_match_exact():
    """Verify exact name matching with boundary recognition."""
    text = "The deed was signed by Levin Sockum in 1845 before the Sussex County court."
    variants = ["Levin Sockum", "Sockum, Levin"]
    pos, length = find_best_name_match(text, variants)
    assert pos != -1
    assert text[pos:pos + length] == "Levin Sockum"


def test_find_best_name_match_word_boundary():
    """Verify matcher rejects partial substrings within larger words."""
    text = "The celebration happened in Levintown without Sockumberland."
    variants = ["Levin Sockum"]
    pos, length = find_best_name_match(text, variants)
    assert pos == -1
    assert length == 0


def test_find_best_name_match_year_proximity():
    """Verify target year proximity prioritizes the correct instance of duplicate names."""
    text = (
        "First mention: Augustus Wright born in 1812 in Millsboro. "
        "Second mention: Augustus Wright married in 1878 in Indian River Hundred."
    )
    variants = ["Augustus Wright"]
    
    # Target 1878 should pick the second occurrence
    pos, length = find_best_name_match(text, variants, target_year=1878)
    assert pos != -1
    matched_snippet = text[pos:pos + 80]
    assert "1878" in matched_snippet
