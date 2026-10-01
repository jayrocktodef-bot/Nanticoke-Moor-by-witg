# Genealogical File Organization Engine — System Prompt v2.0
# This file is the canonical reference for all naming, categorization,
# and file-organization rules used by the archive pipeline.
# See: genealogy_file_organization_system_prompt_v2.md for full documentation.

SUFFIXES = {'sr', 'sr.', 'jr', 'jr.', 'ii', 'iii', 'iv', 'v', 'vi', 'esq', 'esq.', 'md', 'phd'}

HONORIFICS = {'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'miss', 'ms', 'ms.', 'rev', 'rev.',
              'capt', 'capt.', 'col', 'col.', 'hon', 'hon.', 'prof', 'prof.', 'sgt', 'sgt.'}

NOISE_WORDS = {
    # Geographic locations
    'cheswold', 'dover', 'millsboro', 'smyrna', 'clayton', 'wilmington', 'bridgeton',
    'delaware', 'maryland', 'virginia', 'jersey', 'pennsylvania', 'michigan',
    'washington', 'rockingham', 'sussex', 'kent', 'cumberland', 'fairfield',
    'gouldtown', 'indian', 'river', 'city', 'county', 'township',
    # Record types / legal / admin
    'deed', 'grantee', 'executor', 'certificate', 'census', 'state', 'probate',
    'obituary', 'photo', 'page', 'inc', 'file', 'record', 'index',
    # Month / day names
    'january', 'february', 'march', 'april', 'may', 'june', 'july',
    'august', 'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    # Occupations / descriptors
    'farmer', 'senior', 'minor', 'laborer', 'servant', 'slave',
    # Relationship labels
    'mother', 'father', 'daughter', 'son', 'husband', 'wife', 'brother', 'sister',
    'sons', 'daughters', 'grandchildren', 'granddaughter', 'grandson',
    # Institutional words
    'university', 'hospital', 'church', 'school', 'cemetery',
    # Common English stopwords that appear as false names
    'of', 'and', 'the', 'was', 'to', 'in', 'at', 'by', 'for', 'from', 'with',
    'about', 'abt', 'is', 'are', 'or', 'an', 'on', 'it', 'be', 'as', 'if',
    'her', 'his', 'he', 'she', 'they', 'them', 'their', 'our', 'we', 'us',
    'man', 'woman', 'boy', 'girl', 'people', 'family', 'families',
    'left', 'right', 'standing', 'born', 'died', 'married', 'lived',
    'said', 'says', 'home', 'time', 'name', 'war', 'friends',
    'ancestry', '//', "'s", '--', 'st', 'rr', 'de', 'nj', 'md', 'pa',
}

CATEGORY_FOLDERS = {
    '01_Vital_Records': ['Birth_Record', 'Baptism', 'Marriage_License', 'Marriage_Record',
                         'Divorce_Decree', 'Death_Certificate', 'Burial_Record', 'Tombstone'],
    '02_Census_and_Land': ['Census_Federal', 'Census_State', 'Tax_List', 'Tax_Assessment',
                           'Land_Deed', 'Land_Grant', 'Mortgage'],
    '03_Military': ['Enlistment', 'Draft_Card', 'Service_Roster', 'Pension_File', 'Discharge_Paper'],
    '04_Photos_and_Media': ['Photo_Portrait', 'Photo_Group', 'Photo_Document',
                            'Audio_Interview', 'Video_Recording'],
    '05_Stories_and_Documents': ['Will', 'Probate_File', 'Letter', 'Diary',
                                 'Newspaper_Clipping', 'Oral_History', 'Bible_Record'],
    '06_Other': ['Immigration_Record', 'Church_Roll', 'School_Record', 'Miscellaneous'],
}


def get_clean_surname(name):
    """
    Extract the true family surname from a full name string.
    Implements Step 2b of the v2.0 system prompt:
      - Strips honorifics (Dr., Mr., Mrs., Rev., etc.)
      - Strips generational suffixes (Sr., Jr., III, etc.)
      - Returns 'Unknown' for empty/noise inputs
    """
    if not name:
        return "Unknown"
    parts = [p.strip(' .,;:/()"\'\t\r\n') for p in name.strip().split() if p.strip(' .,;:/()"\'\t\r\n')]
    if not parts:
        return "Unknown"
    # Strip leading honorifics
    while parts and parts[0].lower().rstrip('.') in {h.rstrip('.') for h in HONORIFICS}:
        parts.pop(0)
    if not parts:
        return "Unknown"
    # Strip trailing suffixes
    while len(parts) > 1 and parts[-1].lower().rstrip('.') in {s.rstrip('.') for s in SUFFIXES}:
        parts.pop()
    surname = parts[-1] if parts else "Unknown"
    # Reject noise words
    if surname.lower() in NOISE_WORDS or len(surname) < 2 or surname.isdigit():
        return "Unknown"
    return surname


def is_valid_person_name(name):
    """
    Returns True only if the name string represents a plausible human individual.
    Implements the Named Entity Resolution rules from v2.0.
    """
    if not name:
        return False
    parts = [p.strip(' .,;:/()"\'\t\r\n') for p in name.strip().split() if p.strip(' .,;:/()"\'\t\r\n')]
    if len(parts) < 2:
        return False
    surname = get_clean_surname(name)
    if surname == "Unknown":
        return False
    # Check that at least one part looks like a given name (capitalized, not a noise word)
    given = parts[0].strip(' .,;:/()"\'')
    if given.lower() in NOISE_WORDS or len(given) < 2 or given.isdigit():
        return False
    return True


def build_subfolder_name(first_name, middle_names=None, suffix=None,
                         birth_year=None, death_year=None, person_id=None):
    """
    Build the individual subfolder name per Step 2a of v2.0.
    Example: John_Paul_Jr_1850-1920_ID42
    """
    parts = [first_name.replace(' ', '_')]
    if middle_names:
        if isinstance(middle_names, list):
            parts.extend([m.replace(' ', '_') for m in middle_names])
        else:
            parts.append(middle_names.replace(' ', '_'))
    if suffix:
        parts.append(suffix.replace('.', '').replace(' ', '_'))

    by = str(birth_year) if birth_year else 'xxxx'
    dy = str(death_year) if death_year else 'xxxx'
    parts.append(f"{by}-{dy}")

    if person_id:
        parts.append(str(person_id))

    return '_'.join(parts)


def format_date_element(year=None, month=None, day=None, approximate=False):
    """
    Format a date element per Step 4 of v2.0.
    Returns strings like: 1910-04-15, 1910-00-00, 1910ca-00-00, xxxx-00-00
    """
    if year is None:
        return 'xxxx-00-00'
    y_str = f"{year}ca" if approximate else str(year)
    m_str = f"{month:02d}" if month else '00'
    d_str = f"{day:02d}" if day else '00'
    return f"{y_str}-{m_str}-{d_str}"
