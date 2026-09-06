# Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Family Archive

An archival digital preservation platform, genealogical proof engine, and cartographic atlas dedicated to the documented lineages, primary records, and oral histories of the **Nanticoke, Lenape (Moor), and Afro-Indigenous remnant communities** of the Delmarva Peninsula (Delaware, Maryland Eastern Shore, and Southern New Jersey).

---

## Key Features & Research Engines

### 1. Scholarly Citations & GEDCOM 5.5.1 Exporter
* **Elizabeth Shown Mills (*Evidence Explained*)**: Generates standard Reference Notes and Source List Entries compliant with the Genealogical Proof Standard (GPS) for all individual profiles, primary records, and obituaries.
* **Chicago Manual of Style (17th ed.)**: Generates academic Footnotes and Bibliography entries.
* **BibTeX**: Generates `@misc` bibliography blocks for reference managers (Zotero, Mendeley, LaTeX).
* **GEDCOM 5.5.1**: One-click download of UTF-8 encoded `.ged` lineage files compatible with Gramps, RootsMagic, and Family Tree Maker.

### 2. Primary Document Entity & Citation Auto-Linker
* **354 Primary Source Documents**: Court records, family Bibles, probate registers, land patents, and census schedules cataloged in the repository.
* **Verbatim Evidence Attribution**: Over **4,800 source citations** populated with verbatim historical quotes.
* **Evidence Level Recalibration**: Automatically recalibrates confidence levels under GPS rules, promoting verified individuals to **Level 3 (Primary Source Confirmed)**.

### 3. Historical Racial Reclassification & Evidence Conflict Modeling
* **Tripartite Boundary Negotiations**: Traces changing federal census designations (`M` [Mulatto], `B` [Black], `W` [White], `In` [Indian], `Free Colored`) across 1790–1930 records.
* **1930 Sussex County Alterations**: Models the historical intervention where federal supervisors struck through local enumerator records of tribal affiliation and race from `'In'` (Indian) to `'Neg'` (Negro).
* **Chronological Conflict Summaries**: Documents multi-census transitions (e.g. `1850: Mulatto ➔ 1860: Mulatto ➔ 1870: White`) in the evidence dossier with historical explanatory context.

### 4. Interactive Historical Migration & Cemetery Atlas
* **Delmarva Cartographic Model**: Custom interactive SVG & D3 atlas calibrated to the Delmarva Peninsula and Southern New Jersey (38.2°N–39.85°N, 76.3°W–74.8°W).
* **6 Settlement Centers**:
  * **Millsboro & Indian River Hundred, DE**: Ancient Nanticoke tribal homeland & 1711 Maryland reservation.
  * **Cheswold & Fork Branch, DE**: Kent County Lenape / Moor settlement.
  * **Gouldtown & Fairfield, NJ**: Historic sovereign community founded c. 1700 by Benjamin Gould & Elizabeth Adams.
  * **Salem & Woodstown, NJ**: South Jersey Cuff, Pierce, and Murray ancestral tracts.
  * **Caroline & Federalsburg, MD**: Upper Choptank trans-border sanctuary corridor.
  * **Woodland & Seaford, DE**: Nanticoke River ferry & crossing.
* **4 Migration Corridors**: Animated flow lines for the Delaware Bay Maritime Crossing, Delmarva Kings Highway Spine, Maryland Eastern Shore Trans-Border Passage, and South Jersey Inland Network.
* **13 Preserved Cemeteries**: Exact GPS coordinates, community affiliations, historical significance notes, and interactive tombstone photo previews.

### 5. Archival Preservation & Strict Entity Resolution
* **Archival Medium Typology**: Physical classification (`photograph`, `document`, `family_tree`, `tombstone`, `census_page`) with face context scoring and routing targets.
* **Disambiguation**: Strict surname + given name matching preventing generational suffix collisions (Jr vs Sr) and decoupling non-portrait artifacts.
* **100% Hydration**: 3,820 individual ancestor profiles verified with dates, facts, kinships, and source links with zero dangling references.

---

## Project Structure

```
├── preservation_output/
│   ├── genealogy_preservation.db       # Primary SQLite archive database
│   ├── assets/archive_media/           # Restored ancestor portraits, documents, & tombstones
│   │   ├── people/                     # Individual & family portraits
│   │   ├── documents/                  # Deeds, diplomas, maps, wills
│   │   ├── family_trees/               # 5-generation pedigree charts
│   │   └── tombstones/                 # Cemetery headstone photographs
│   └── profiles/                       # Archived XML source dossiers
├── frontend/
│   ├── public/api/                     # Static JSON endpoints for Vercel edge deployment
│   │   ├── person/{id}.json            # 3,820 hydrated individual profile dossiers
│   │   ├── records/{filename}.json     # 357 primary document transcriptions
│   │   ├── cemeteries.json             # 13 GPS-verified cemeteries with tombstones
│   │   ├── surnames.json               # 50+ lineage surname portals
│   │   └── search_index.json           # Full-text search index
│   └── src/
│       ├── components/
│       │   ├── CitationModal.jsx           # Evidence Explained & Chicago citation dialog
│       │   ├── HistoricalMigrationMap.jsx  # Interactive Delmarva migration & cemetery atlas
│       │   ├── HomeScreen.jsx              # Main archive workspace & navigation
│       │   ├── PersonProfileView.jsx       # Editorial individual dossier view
│       │   ├── TranscribedDocumentView.jsx # Document reader with PDF export & citation
│       │   └── ObituaryViewer.jsx          # Broadsheet obituary vault & audio reader
│       └── utils/
│           └── citationGenerator.js        # Academic citation & GEDCOM export engine
├── auto_link_primary_documents_and_citations.py    # Primary document citation auto-linker
├── model_racial_classifications_and_conflicts.py   # Census race fluidity & conflict modeler
├── migrate_archival_schema.py                      # DeepSeek preservation schema migration
└── export_static_build_for_vercel.py               # Production static API & asset exporter
```

---

## Pipeline Execution & Build

### 1. Ingest & Auto-Link Primary Document Citations
```bash
python3 auto_link_primary_documents_and_citations.py
```

### 2. Model Racial Classifications & Evidence Conflicts
```bash
python3 model_racial_classifications_and_conflicts.py
```

### 3. Export Static APIs for Production Hosting
```bash
python3 export_static_build_for_vercel.py
```

### 4. Build Frontend Application
```bash
cd frontend
npm install
npm run build
```

---

## Academic Citation Format

When citing the archive in research publications or lineage societies:

**Evidence Explained (GPS Reference Note):**
> Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Archive, digital evidence database and genealogical proof repository (https://lynncjackson-genealogy.vercel.app : accessed 6 September 2026), individual profile and evidence model for Augustus Wright (b. 1878, d. 1960), ID #11266.

**Chicago Manual of Style (17th ed.):**
> Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Archive, s.v. "Augustus Wright," Individual Record #11266, accessed September 6, 2026, https://lynncjackson-genealogy.vercel.app/#person-11266.
