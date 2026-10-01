#!/usr/bin/env python3
"""
enrich_persons_from_documents.py
=================================
Audits every person profile in genealogy_preservation.db and non-destructively
enriches it with facts from THREE sources (in priority order):
  1. Person XML profiles in preservation_output/profiles/
  2. The person's linked source page (pages.filename = persons.source_page)
  3. Secondary cross-page name search across all scraped pages

Follows Zero Speculation and Zero Hallucination Policy:
  - Only extracts facts EXPLICITLY stated in a source document
  - Never overwrites an existing confirmed fact
  - Logs every action to audit_flags with full evidence attribution
  - Flags ambiguous matches for human review instead of auto-writing
  - Filters out paternal-side individuals of Jequan Davis / Jane Ellen Davis per policy.

Usage:
    python3 enrich_persons_from_documents.py [--dry-run] [--verbose] [--person-id N]

    --dry-run           Print proposed changes without writing anything to the DB
    --verbose           Show every match and extracted fact
    --person-id N       Run only for a specific person_id (for testing)
    --skip-xml          Skip Pass 1 (XML profile ingestion)
    --skip-cross-page   Skip Pass 3 (cross-page name search)
"""

import re
import sqlite3
import argparse
import sys
import os
import html
import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

DB_PATH = "preservation_output/genealogy_preservation.db"
PROFILES_DIR = "preservation_output/profiles"

# Minimum real-word count for a person name — filters garbage rows like "She never", "Larry is the"
MIN_NAME_WORDS = 2
MIN_NAME_ALPHA_RATIO = 0.6  # At least 60% alphabetic characters

# Surnames associated with the paternal lineage of Jequan Davis / Jane Ellen Davis
PATERNAL_SURNAMES = {
    'bush', 'anderson', 'brummel', 'brummell', 'brown', 'braham', 'branham',
    'carmean', 'ingram', 'turner', 'faver', 'favors', 'favor', 'rawlings',
    'wynne', 'hood', 'sherrer', 'bacon', 'frame', 'cordrey', 'lockwood', 'wymbs', 'cannon'
}

# ---------------------------------------------------------------------------
# Date extraction patterns — tuned for historical genealogical prose 1650–1950
# ---------------------------------------------------------------------------
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DAY   = r"(?:\d{1,2}(?:st|nd|rd|th)?)"
_YEAR  = r"(?:1[6789]\d{2}|20[012]\d)"

# Comprehensive date: "20 April, 1821", "Apr. 8th, 1870", "Jan. 11th 1866", "Dec. 31, 1908"
DATE_RE = re.compile(
    rf"\b(?:"
    rf"(?:{_MONTH}\.?\s+{_DAY}(?:\s*,?\s*{_YEAR}))"    # Month DD YYYY
    rf"|(?:{_DAY}\s+{_MONTH}\.?(?:\s*,?\s*{_YEAR}))"    # DD Month YYYY
    rf"|(?:{_YEAR})"                                      # Year only fallback
    rf")\b",
    re.IGNORECASE
)

# Place: captures "in [Place]" or "at [Place]" — up to 50 chars, stops at period/comma/clause
PLACE_RE = re.compile(
    r"(?:(?:in|at|near)\s+)((?:[A-Z][a-z]+\s*){1,6}(?:,\s*[A-Z][a-z]+\.?)?)",
    re.IGNORECASE
)

# Birth patterns
BIRTH_PATTERNS = [
    re.compile(
        rf"(?:was\s+born|born)\s*"
        rf"(?:on\s+)?(?P<date>{DATE_RE.pattern})?"
        rf"(?:\s*,?\s*(?:in|at|near)\s+(?P<place>[^,.;]+(?:,\s*[^,.;]+){{0,2}}))?"
        rf"(?:\s*\.\s*|,|\s+(?:and\s+died|he\s+|she\s+))",
        re.IGNORECASE
    ),
    re.compile(
        rf"\bborn\s+(?P<date>{DATE_RE.pattern})",
        re.IGNORECASE
    ),
    re.compile(
        rf"\bborned?\s+(?P<date>{DATE_RE.pattern})",
        re.IGNORECASE
    ),
]

# Death patterns
DEATH_PATTERNS = [
    re.compile(
        rf"(?:died|departed\s+this\s+life|death\s+of)\s*"
        rf"(?:on\s+)?(?P<date>{DATE_RE.pattern})?"
        rf"(?:\s*,?\s*(?:in|at|near)\s+(?P<place>[^,.;]+(?:,\s*[^,.;]+){{0,2}}))?",
        re.IGNORECASE
    ),
    re.compile(
        rf"(?:died|d\.)\s*(?:on\s+)?(?P<date>{DATE_RE.pattern})",
        re.IGNORECASE
    ),
    re.compile(
        rf"departed\s+this\s+life\s+(?P<date>{DATE_RE.pattern})",
        re.IGNORECASE
    ),
]

# Marriage patterns
MARRIAGE_PATTERNS = [
    re.compile(
        rf"(?:married|wed(?:ded)?|were\s+married|was\s+married\s+to)\s*"
        rf"(?P<spouse>[A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,3}})?\s*"
        rf"(?:on\s+)?(?P<date>{DATE_RE.pattern})?"
        rf"(?:\s*,?\s*(?:in|at|near)\s+(?P<place>[^,.;]+(?:,\s*[^,.;]+){{0,2}}))?",
        re.IGNORECASE
    ),
    re.compile(
        rf"(?:married|wed)\s+(?:on\s+)?(?P<date>{DATE_RE.pattern})",
        re.IGNORECASE
    ),
]

# Burial patterns
BURIAL_PATTERNS = [
    re.compile(
        rf"(?:buried|interred|is\s+buried)\s*"
        rf"(?:at|in|with)?\s*(?P<place>[^,.;\n]+(?:Church|Cemetery|Graveyard|Chapel|Churchyard)[^,.;\n]*)",
        re.IGNORECASE
    ),
]

NAME_ABBREVIATIONS: dict[str, list[str]] = {
    "John":    ["Jno", "Jon"],
    "William": ["Wm", "Will"],
    "Thomas":  ["Thos"],
    "James":   ["Jas"],
    "Robert":  ["Robt"],
    "Samuel":  ["Sam"],
    "Charles":  ["Chas"],
    "Richard": ["Richd"],
    "Joseph":  ["Jos"],
    "Elizabeth": ["Eliza", "Betsy", "Bess"],
    "Mary":    ["Molly", "Polly"],
    "Margaret": ["Maggie", "Peggy"],
    "Catherine": ["Catharine", "Cathrine", "Kate", "Cath"],
}

@dataclass
class ExtractedFact:
    fact_type: str              # Birth | Death | Marriage | Burial
    date_string: Optional[str]
    place_string: Optional[str]
    value_string: str           # Full raw matched text preserved verbatim
    confidence: str             # HIGH | MEDIUM | LOW
    context_text: str           # Surrounding passage (for audit log)
    source_filename: str

@dataclass
class EnrichmentStats:
    persons_audited: int = 0
    persons_enriched: int = 0
    facts_added: int = 0
    conflicts_logged: int = 0
    no_source_page: int = 0
    name_not_found: int = 0
    ambiguous_matches: int = 0
    xml_profile_facts: int = 0
    cross_page_facts: int = 0
    skipped_garbage_names: int = 0
    skipped_paternal_persons: int = 0
    errors: int = 0


def is_valid_person_name(name: str) -> bool:
    """Filter out garbage rows created by scraper errors (e.g., 'She never', 'Larry is the')."""
    if not name or not name.strip():
        return False
    words = name.strip().split()
    if len(words) < MIN_NAME_WORDS:
        return False
    alpha_chars = sum(1 for c in name if c.isalpha())
    if len(name) == 0 or alpha_chars / len(name) < MIN_NAME_ALPHA_RATIO:
        return False
    stop_suffixes = {
        "the", "a", "an", "and", "or", "is", "was", "were", "had", "has",
        "in", "on", "at", "of", "to", "for", "with", "by", "never", "not"
    }
    last_word = words[-1].lower().rstrip(".,-")
    if last_word in stop_suffixes:
        return False
    return True


def is_paternal_side_person(person: dict) -> bool:
    """
    Check if a person belongs to the paternal side of Jequan Davis or Jane Ellen Davis.
    Per user directive: Do not enrich or add paternal side individuals.
    """
    name = (person.get("name") or "").lower()
    last_name = (person.get("married_last_name") or "").lower()
    maiden_name = (person.get("maiden_name") or "").lower()
    dataset_source = (person.get("dataset_source") or "").lower()
    source_page = (person.get("source_page") or "").lower()

    if dataset_source == "davis_family_gedcom" or "davis family tree.ged" in source_page:
        for s in PATERNAL_SURNAMES:
            if s in name or s in last_name or s in maiden_name:
                return True

    for s in PATERNAL_SURNAMES:
        if s in last_name or s in maiden_name:
            return True

    return False


GEDCOMX_NS = "http://gedcomx.org/v1/"
FACT_TYPE_MAP = {
    "http://gedcomx.org/Birth":    "Birth",
    "http://gedcomx.org/Death":    "Death",
    "http://gedcomx.org/Marriage": "Marriage",
    "http://gedcomx.org/Burial":   "Burial",
}


def ingest_xml_profile(person_id: int, cur: sqlite3.Cursor,
                       stats: EnrichmentStats, dry_run: bool, verbose: bool) -> bool:
    xml_path = os.path.join(PROFILES_DIR, f"person_{person_id}.xml")
    if not os.path.exists(xml_path):
        return False

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        return False

    existing = get_existing_facts(cur, person_id)
    enriched = False

    for fact_el in root.findall(f".//{{{GEDCOMX_NS}}}fact"):
        fact_type_uri = fact_el.get("type", "")
        fact_type = FACT_TYPE_MAP.get(fact_type_uri)
        if not fact_type:
            continue

        date_el = fact_el.find(f".//{{{GEDCOMX_NS}}}date/{{{GEDCOMX_NS}}}original")
        place_el = fact_el.find(f".//{{{GEDCOMX_NS}}}place/{{{GEDCOMX_NS}}}original")

        date_str = html.unescape((date_el.text or "").strip()) if date_el is not None and date_el.text else None
        place_str = html.unescape((place_el.text or "").strip()) if place_el is not None and place_el.text else None

        if not date_str and not place_str:
            continue

        if date_str:
            year_m = re.search(r"\b(1[6789]\d{2}|19[0-5]\d)\b", date_str)
            if not year_m:
                continue

        existing_for_type = existing.get(fact_type, [])
        all_unknown = all(
            is_unknown_or_empty(e.get("date_string")) and is_unknown_or_empty(e.get("place_string"))
            for e in existing_for_type
        )

        if existing_for_type and not all_unknown:
            for ex in existing_for_type:
                ex_date = ex.get("date_string") or ""
                if not is_unknown_or_empty(ex_date) and values_conflict(ex_date, date_str or ""):
                    if verbose:
                        print(f"  [XML] ⚡ CONFLICT {fact_type}: existing={ex_date!r} xml={date_str!r}")
                    log_audit_flag(cur, person_id, "ENRICHMENT_CONFLICT",
                                   f"{fact_type} conflict: existing='{ex_date}' vs XML='{date_str}'",
                                   f"source: {xml_path}",
                                   severity="warning", dry_run=dry_run)
                    stats.conflicts_logged += 1
            continue

        ef = ExtractedFact(
            fact_type=fact_type,
            date_string=date_str or None,
            place_string=place_str or None,
            value_string=f"{date_str} {place_str}".strip()[:200],
            confidence="HIGH",
            context_text=f"Source: {xml_path}",
            source_filename=xml_path,
        )
        if verbose:
            print(f"  [XML] ✓ Adding {fact_type}: date={date_str!r} place={place_str!r}")
        add_fact(cur, None, ef, dry_run=dry_run, person_id_override=person_id)
        log_audit_flag(cur, person_id, "ENRICHMENT_ADDED",
                       f"[XML] Added {fact_type}: date='{date_str}', place='{place_str}'",
                       f"source: {xml_path}",
                       severity="info", dry_run=dry_run)
        stats.facts_added += 1
        stats.xml_profile_facts += 1
        enriched = True

        existing.setdefault(fact_type, []).append({"date_string": date_str, "place_string": place_str, "value_string": ""})

        if fact_type == "Birth" and date_str:
            update_person_summary(cur, person_id, date_str, None, dry_run=dry_run)
        if fact_type == "Death" and date_str:
            update_person_summary(cur, person_id, None, date_str, dry_run=dry_run)

    return enriched


def build_name_patterns(first_name: str, last_name: str, middle_name: str = "",
                        maiden_name: str = "") -> list[re.Pattern]:
    patterns = []

    def _make_pat(given: str, surname: str) -> re.Pattern:
        g = re.escape(given.strip())
        s = re.escape(surname.strip())
        return re.compile(rf"\b{g}\b.{{0,40}}\b{s}\b", re.IGNORECASE | re.DOTALL)

    if first_name and last_name:
        patterns.append(_make_pat(first_name, last_name))

    if first_name and middle_name and last_name:
        patterns.append(_make_pat(f"{first_name} {middle_name}", last_name))

    if first_name and maiden_name:
        patterns.append(_make_pat(first_name, maiden_name))

    alts = NAME_ABBREVIATIONS.get(first_name, [])
    for alt in alts:
        if last_name:
            patterns.append(_make_pat(alt, last_name))
        if maiden_name:
            patterns.append(_make_pat(alt, maiden_name))

    return patterns


def find_name_contexts(text: str, patterns: list[re.Pattern],
                       window: int = 400) -> list[dict]:
    contexts = []
    seen_positions = []

    for pat in patterns:
        for m in pat.finditer(text):
            start = max(0, m.start() - window // 2)
            end   = min(len(text), m.end() + window // 2)
            passage = text[start:end].strip()

            already = any(abs(m.start() - p) < 100 for p in seen_positions)
            if already:
                continue

            seen_positions.append(m.start())
            contexts.append({
                "passage": passage,
                "match_text": m.group(0),
                "position": m.start(),
                "pattern": pat.pattern[:60],
            })

    return contexts


def is_ambiguous(contexts: list[dict]) -> bool:
    if len(contexts) <= 1:
        return False
    positions = sorted(c["position"] for c in contexts)
    for i in range(1, len(positions)):
        if positions[i] - positions[i - 1] > 200:
            return True
    return False


def extract_date_and_place(text: str) -> tuple[Optional[str], Optional[str]]:
    date_m = DATE_RE.search(text)
    date = date_m.group(0).strip() if date_m else None
    place_m = PLACE_RE.search(text)
    place = place_m.group(1).strip() if place_m else None
    return date, place


def run_patterns(patterns: list[re.Pattern], passage: str,
                 fact_type: str, source_filename: str,
                 context: dict) -> list[ExtractedFact]:
    results = []

    for pat in patterns:
        for m in pat.finditer(passage):
            raw = m.group(0).strip()
            if not raw or len(raw) < 4:
                continue

            try:
                date = (m.group("date") or "").strip() or None
            except IndexError:
                date = None

            try:
                place = (m.group("place") or "").strip() or None
            except IndexError:
                place = None

            if not date:
                date_m = DATE_RE.search(raw)
                date = date_m.group(0).strip() if date_m else None

            if not place and date:
                after_date = raw[raw.find(date) + len(date):] if date else raw
                place_m = PLACE_RE.search(after_date)
                place = place_m.group(1).strip() if place_m else None

            if fact_type in ("Birth", "Death", "Marriage") and not date:
                continue

            if date:
                year_m = re.search(r"\b(1[6789]\d{2}|19[0-5]\d)\b", date)
                if not year_m:
                    continue

            pos_in_passage = m.start()
            if pos_in_passage < 150:
                confidence = "HIGH"
            elif pos_in_passage < 300:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            results.append(ExtractedFact(
                fact_type=fact_type,
                date_string=date,
                place_string=place,
                value_string=raw[:300],
                confidence=confidence,
                context_text=context["passage"][:400],
                source_filename=source_filename,
            ))
            break

    return results


def extract_facts_from_passage(passage: str, source_filename: str,
                                context: dict) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    facts += run_patterns(BIRTH_PATTERNS,    passage, "Birth",    source_filename, context)
    facts += run_patterns(DEATH_PATTERNS,    passage, "Death",    source_filename, context)
    facts += run_patterns(MARRIAGE_PATTERNS, passage, "Marriage", source_filename, context)
    facts += run_patterns(BURIAL_PATTERNS,   passage, "Burial",   source_filename, context)
    return facts


def get_existing_facts(cur: sqlite3.Cursor, person_id: int) -> dict[str, list[dict]]:
    cur.execute(
        "SELECT fact_type, date_string, place_string, value_string FROM facts WHERE person_id = ?",
        (person_id,)
    )
    result: dict[str, list[dict]] = {}
    for row in cur.fetchall():
        ft = row["fact_type"]
        result.setdefault(ft, []).append(dict(row))
    return result


def is_unknown_or_empty(val: Optional[str]) -> bool:
    if not val:
        return True
    return val.strip().lower() in ("", "unknown", "?", "not known", "none", "n/a")


def values_conflict(existing: str, new: str) -> bool:
    def norm(s: str) -> str:
        s = html.unescape(s or "")
        return " ".join(s.lower().split())
    return norm(existing) != norm(new)


def log_audit_flag(cur: sqlite3.Cursor, person_id: int, category: str,
                   description: str, evidence: str, severity: str = "info",
                   dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [AUDIT] [{severity.upper()}] {category}: {description[:120]}")
        return
    cur.execute(
        """INSERT INTO audit_flags (category, severity, person_id, description, evidence, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (category, severity, person_id, description, evidence, datetime.utcnow().isoformat())
    )


def add_fact(cur: sqlite3.Cursor, fact_holder, fact: ExtractedFact,
             dry_run: bool = False, person_id_override: int = None) -> None:
    pid = person_id_override if person_id_override is not None else (
        fact_holder["person_id"] if fact_holder else None
    )
    if dry_run:
        print(f"  [ADD FACT] {fact.fact_type}: date={fact.date_string!r} place={fact.place_string!r}")
        return
    cur.execute(
        """INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
           VALUES (?, ?, ?, ?, ?)""",
        (pid, fact.fact_type, fact.date_string, fact.place_string, fact.value_string)
    )


def update_person_summary(cur: sqlite3.Cursor, person_id: int,
                          birth: Optional[str], death: Optional[str],
                          dry_run: bool = False) -> None:
    if dry_run:
        if birth:
            print(f"  [UPDATE] persons.birth_info → {birth!r}")
        if death:
            print(f"  [UPDATE] persons.death_info → {death!r}")
        return

    if birth:
        cur.execute(
            "UPDATE persons SET birth_info = ? WHERE person_id = ? AND (birth_info IS NULL OR LOWER(birth_info) = 'unknown')",
            (birth, person_id)
        )
    if death:
        cur.execute(
            "UPDATE persons SET death_info = ? WHERE person_id = ? AND (death_info IS NULL OR LOWER(death_info) = 'unknown')",
            (death, person_id)
        )


def bump_evidence_level(cur: sqlite3.Cursor, person_id: int,
                        dry_run: bool = False) -> None:
    if dry_run:
        return
    cur.execute(
        "UPDATE persons SET evidence_level = COALESCE(evidence_level, 0) + 1 WHERE person_id = ?",
        (person_id,)
    )


def enrich_person(person: dict, page_text: str, cur: sqlite3.Cursor,
                  stats: EnrichmentStats, dry_run: bool, verbose: bool) -> bool:
    pid = person["person_id"]
    name = person["name"] or ""
    first_name = person["first_name"] or ""
    middle_name = person["middle_name"] or ""
    maiden_name = person["maiden_name"] or ""
    last_name = person["married_last_name"] or ""
    source_filename = person["source_page"] or ""

    if verbose:
        print(f"\n── Person #{pid}: {name} (source: {source_filename})")

    patterns = build_name_patterns(first_name, last_name, middle_name, maiden_name)
    if not patterns:
        log_audit_flag(cur, pid, "NAME_NOT_FOUND_IN_SOURCE",
                       f"Could not build name patterns for '{name}'",
                       f"first={first_name!r} last={last_name!r}",
                       severity="warning", dry_run=dry_run)
        stats.name_not_found += 1
        return False

    contexts = find_name_contexts(page_text, patterns)

    if not contexts:
        if verbose:
            print(f"  Name not found in {source_filename}")
        log_audit_flag(cur, pid, "NAME_NOT_FOUND_IN_SOURCE",
                       f"'{name}' not found in source document",
                       f"source: {source_filename}",
                       severity="info", dry_run=dry_run)
        stats.name_not_found += 1
        return False

    if is_ambiguous(contexts):
        if verbose:
            print(f"  ⚠ Ambiguous match ({len(contexts)} occurrences far apart)")
        log_audit_flag(cur, pid, "AMBIGUOUS_MATCH",
                       f"Multiple disjoint occurrences of '{name}' — requires human review",
                       f"source: {source_filename}, matches: {len(contexts)}",
                       severity="warning", dry_run=dry_run)
        stats.ambiguous_matches += 1
        return False

    existing = get_existing_facts(cur, pid)

    all_new_facts: list[ExtractedFact] = []
    for ctx in contexts:
        extracted = extract_facts_from_passage(ctx["passage"], source_filename, ctx)
        all_new_facts.extend(extracted)

    if verbose and all_new_facts:
        print(f"  Extracted {len(all_new_facts)} candidate fact(s)")

    person_enriched = False
    new_birth_date = None
    new_death_date = None

    for fact in all_new_facts:
        if fact.confidence == "LOW":
            if verbose:
                print(f"  LOW confidence {fact.fact_type}, skipping")
            continue

        existing_for_type = existing.get(fact.fact_type, [])

        already_has = any(
            not values_conflict(e.get("date_string") or "", fact.date_string or "")
            for e in existing_for_type
            if not is_unknown_or_empty(e.get("date_string"))
        )
        if already_has:
            if verbose:
                print(f"  Already have {fact.fact_type} with matching date — skip")
            continue

        all_unknown = all(
            is_unknown_or_empty(e.get("date_string")) and is_unknown_or_empty(e.get("place_string"))
            for e in existing_for_type
        )

        if existing_for_type and not all_unknown:
            for ex in existing_for_type:
                ex_date = ex.get("date_string") or ""
                if not is_unknown_or_empty(ex_date):
                    if values_conflict(ex_date, fact.date_string or ""):
                        if verbose:
                            print(f"  ⚡ CONFLICT {fact.fact_type}: existing={ex_date!r} new={fact.date_string!r}")
                        log_audit_flag(
                            cur, pid, "ENRICHMENT_CONFLICT",
                            f"{fact.fact_type} conflict: existing='{ex_date}' vs found='{fact.date_string}'",
                            f"source: {source_filename} | context: {fact.context_text[:200]}",
                            severity="warning", dry_run=dry_run
                        )
                        stats.conflicts_logged += 1
                    continue

        if verbose:
            print(f"  ✓ Adding {fact.fact_type}: date={fact.date_string!r} place={fact.place_string!r} conf={fact.confidence}")

        add_fact(cur, None, fact, dry_run=dry_run, person_id_override=pid)
        log_audit_flag(
            cur, pid, "ENRICHMENT_ADDED",
            f"Added {fact.fact_type}: date='{fact.date_string}', place='{fact.place_string}' "
            f"[confidence={fact.confidence}]",
            f"source: {source_filename} | verbatim: {fact.value_string[:200]}",
            severity="info", dry_run=dry_run
        )
        stats.facts_added += 1
        person_enriched = True

        if fact.fact_type == "Birth" and fact.date_string and not new_birth_date:
            new_birth_date = fact.date_string
        if fact.fact_type == "Death" and fact.date_string and not new_death_date:
            new_death_date = fact.date_string

    if new_birth_date or new_death_date:
        update_person_summary(cur, pid, new_birth_date, new_death_date, dry_run=dry_run)

    if person_enriched:
        bump_evidence_level(cur, pid, dry_run=dry_run)
        stats.persons_enriched += 1

    return person_enriched


def build_surname_index(pages: dict[str, str]) -> dict[str, list[tuple[str, dict]]]:
    GEN_KEYWORDS = re.compile(
        r"\b(?:born|borned|died|death|married|wed|buried|interred|departed|son\s+of|daughter\s+of)\b",
        re.IGNORECASE
    )
    index: dict[str, list[tuple[str, dict]]] = {}
    for filename, text in pages.items():
        for m in GEN_KEYWORDS.finditer(text):
            start   = max(0, m.start() - 200)
            end     = min(len(text), m.end() + 200)
            passage = text[start:end].strip()
            for word in re.findall(r"\b([A-Z][a-z]{2,})\b", passage):
                key = word.lower()
                ctx = {
                    "passage":    passage,
                    "position":   m.start(),
                    "pattern":    "surname_index",
                    "match_text": word,
                }
                index.setdefault(key, []).append((filename, ctx))
    return index


def main():
    parser = argparse.ArgumentParser(description="Enrich person profiles from transcribed documents.")
    parser.add_argument("--dry-run", action="store_true", help="Print proposed changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Show every match and extracted fact")
    parser.add_argument("--person-id", type=int, default=None, help="Run for a single person_id only")
    parser.add_argument("--skip-xml", action="store_true", help="Skip Pass 1: XML profile ingestion")
    parser.add_argument("--skip-cross-page", action="store_true", help="Skip Pass 3: cross-page name search")
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN MODE — no changes will be written")
        print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT filename, text_content FROM pages WHERE text_content IS NOT NULL AND text_content != ''"
    )
    pages: dict[str, str] = {
        row["filename"]: re.sub(r"[ \t]*\r?\n[ \t]*", " ", row["text_content"])
        for row in cur.fetchall()
    }
    print(f"Loaded {len(pages)} pages with text content")

    if not args.skip_cross_page:
        print("Building surname index for cross-page search...")
        surname_index = build_surname_index(pages)
        print(f"  Index built: {len(surname_index)} unique surname tokens")
    else:
        surname_index = {}

    if args.person_id:
        cur.execute("SELECT * FROM persons WHERE person_id = ?", (args.person_id,))
    else:
        cur.execute("SELECT * FROM persons")

    persons = cur.fetchall()
    print(f"Auditing {len(persons)} person profile(s)...")

    stats = EnrichmentStats()

    for person in persons:
        stats.persons_audited += 1
        pid = person["person_id"]
        name = person["name"] or ""
        source_page = person["source_page"] or ""

        if not is_valid_person_name(name):
            if args.verbose:
                print(f"  #{pid}: Skipping garbage name {name!r}")
            stats.skipped_garbage_names += 1
            continue

        person_dict = dict(person)

        # Policy filter: Skip paternal side individuals of Jequan Davis / Jane Ellen Davis
        if is_paternal_side_person(person_dict):
            if args.verbose:
                print(f"  #{pid}: Skipping paternal side person {name!r}")
            stats.skipped_paternal_persons += 1
            continue

        person_enriched_this_round = False

        # ── PASS 1: XML profile ──────────────────────────────────────────────
        if not args.skip_xml:
            try:
                if ingest_xml_profile(pid, cur, stats, dry_run=args.dry_run, verbose=args.verbose):
                    person_enriched_this_round = True
            except Exception as e:
                stats.errors += 1
                print(f"  ERROR [XML] person #{pid}: {e}", file=sys.stderr)

        # ── PASS 2: source page text ─────────────────────────────────────────
        page_text = pages.get(source_page) if source_page else None
        if page_text:
            try:
                if enrich_person(person_dict, page_text, cur, stats,
                                 dry_run=args.dry_run, verbose=args.verbose):
                    person_enriched_this_round = True
            except Exception as e:
                stats.errors += 1
                print(f"  ERROR [source-page] person #{pid} ({name}): {e}", file=sys.stderr)
                if not args.dry_run:
                    log_audit_flag(cur, pid, "ENRICHMENT_ERROR",
                                   f"Script error: {e}",
                                   f"source: {source_page}",
                                   severity="error", dry_run=False)
        elif source_page:
            stats.no_source_page += 1

        # ── PASS 3: cross-page name search ───────────────────────────────────
        if not args.skip_cross_page and not person_enriched_this_round and surname_index:
            last_name   = (person["married_last_name"] or "").strip().lower()
            maiden_name = (person["maiden_name"] or "").strip().lower()
            first_name  = (person["first_name"] or "").strip()

            candidate_pages: dict[str, list[dict]] = {}
            for sname in filter(None, [last_name, maiden_name]):
                for filename, ctx in surname_index.get(sname, []):
                    if filename == source_page:
                        continue
                    candidate_pages.setdefault(filename, []).append(ctx)

            for filename, ctxs in candidate_pages.items():
                if person_enriched_this_round:
                    break
                for ctx in ctxs:
                    if person_enriched_this_round:
                        break
                    if first_name and first_name.lower() not in ctx["passage"].lower():
                        continue
                    for fact in extract_facts_from_passage(ctx["passage"], filename, ctx):
                        if fact.confidence != "HIGH" or not fact.date_string:
                            continue
                        existing_for_type = get_existing_facts(cur, pid).get(fact.fact_type, [])
                        all_unknown = all(
                            is_unknown_or_empty(e.get("date_string")) and
                            is_unknown_or_empty(e.get("place_string"))
                            for e in existing_for_type
                        )
                        if existing_for_type and not all_unknown:
                            continue
                        if args.verbose:
                            print(f"  [XPAGE:{filename}] {fact.fact_type}: date={fact.date_string!r}")
                        try:
                            add_fact(cur, None, fact, dry_run=args.dry_run, person_id_override=pid)
                            log_audit_flag(
                                cur, pid, "ENRICHMENT_ADDED",
                                f"[XPAGE:{filename}] {fact.fact_type}: date='{fact.date_string}'",
                                f"verbatim: {fact.value_string[:200]}",
                                severity="info", dry_run=args.dry_run
                            )
                            stats.facts_added += 1
                            stats.cross_page_facts += 1
                            person_enriched_this_round = True
                            break
                        except Exception as e:
                            stats.errors += 1

        if person_enriched_this_round:
            bump_evidence_level(cur, pid, dry_run=args.dry_run)
            stats.persons_enriched += 1

        if not args.dry_run and stats.persons_audited % 200 == 0:
            conn.commit()
            print(f"  ... {stats.persons_audited} persons processed")

    if not args.dry_run:
        conn.commit()

    conn.close()

    source_page_facts = stats.facts_added - stats.xml_profile_facts - stats.cross_page_facts
    print()
    print("=" * 60)
    print("ENRICHMENT AUDIT COMPLETE")
    print("=" * 60)
    print(f"  Persons audited:              {stats.persons_audited}")
    print(f"  Skipped (garbage names):      {stats.skipped_garbage_names}")
    print(f"  Skipped (paternal side):      {stats.skipped_paternal_persons}")
    print(f"  Persons enriched:             {stats.persons_enriched}")
    print(f"  Total new facts added:        {stats.facts_added}")
    print(f"    via XML profiles (Pass 1):  {stats.xml_profile_facts}")
    print(f"    via source page  (Pass 2):  {source_page_facts}")
    print(f"    via cross-page   (Pass 3):  {stats.cross_page_facts}")
    print(f"  Conflicts logged (no write):  {stats.conflicts_logged}")
    print(f"  No source page found:         {stats.no_source_page}")
    print(f"  Name not found in source:     {stats.name_not_found}")
    print(f"  Ambiguous matches flagged:    {stats.ambiguous_matches}")
    print(f"  Errors:                       {stats.errors}")
    if args.dry_run:
        print()
        print("  [DRY RUN] No changes were written to the database.")
    print("=" * 60)


if __name__ == "__main__":
    main()
