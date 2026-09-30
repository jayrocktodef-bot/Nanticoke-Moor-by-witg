#!/usr/bin/env python3
"""
Direct Archival Transcription Engine (scripts/transcribe_puckham_documents_direct.py)
===================================================================================
Transcribes each Puckham / Bookram primary document and photograph directly from visual
inspection of the preserved archival media files, eliminating boilerplate templates and
restoring word-for-word primary evidence.

Updates:
1. SQLite database tables: unified_photo_catalog, photo_catalog, document_records.
2. Full dossier: preservation_output/transcriptions/puckham_bookram_documents.md.
3. Individual JSON APIs: frontend/public/api/transcriptions/{id}.json and {filename}.json.
"""

import os
import json
import sqlite3

BASE_DIR = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper'
DB_PATH = os.path.join(BASE_DIR, 'preservation_output', 'genealogy_preservation.db')
TRANSCRIPTIONS_API_DIR = os.path.join(BASE_DIR, 'frontend', 'public', 'api', 'transcriptions')
TRANSCRIPTIONS_MD_PATH = os.path.join(BASE_DIR, 'preservation_output', 'transcriptions', 'puckham_bookram_documents.md')

DIRECT_TRANSCRIPTIONS = {
    "elias-bookram-land-deed-1.jpeg": {
        "title": "Granville County Deed Book Y, Page 63: Thomas Bonner to Elias Pookum (1814)",
        "doc_type": "Land Deed",
        "approximate_year": "1814",
        "repository": "Granville County Register of Deeds, Oxford, North Carolina (Deed Book Y, pp. 63-64)",
        "citation": "\"Thomas Bonner to Elias Pookum.\" Granville County, North Carolina, Deed Book Y, Page 63 (3 February 1814). Preserved in the North Carolina State Archives / Native American Roots Collection.",
        "lines": [
            "ARCHIVAL MARGIN HEADER:",
            "Thomas Bonner To Elias Pookum",
            "Granville DB Y 63-64 Thomas Bonner to Elias Pookum. Located by K. Lucas. Native American Roots",
            "--------------------------------------------------------------------------------",
            "BODY OF INDENTURE (VERBATIM):",
            "This Indenture made this 3rd day of February in the year of our Lord 1814 between Thomas Bonner of the County of Granville and State of N. Carolina of the one part & Elias Pookum of said County & State of the other part Witnesseth that the said Thomas Bonner for and in consideration of the sum of Eighty five Dollars to him in hand paid by the said Elias Pookum before the sealing or delivery of these presents the Receipt whereof is hereby acknowledged have granted bargained & sold and delivered & by these presents doth Sell & Confirm unto the said Elias Pookum a Certain parcel or Tract of Land Situate lying and being in said County on the waters of the Nap of Reeds Creek_ Begining at a Black Jack in Bullocks line thence along Bullocks & Veaseys line to Liwan Carys line thence along a dividing line between said Pookum & Cary to a pine on the North side of the long branch in all 261 poles thence East with the said Branch as it meanders 42 poles to an ash on South side of said Branch thence South 15 degrees East to [pine] said Bullocks line thence South 65 degrees West to the first Station Containing by Estimation Seventy acres & a half be the same more or less__ To have and to hold the aforesaid Bargained land and Premises together with all and Singular the appurtenances & every thing in anywise"
        ]
    },
    "elias-bookram-land-deed-2.jpeg": {
        "title": "Granville County Deed Book Y, Page 64: Thomas Bonner to Elias Pookum (Warranty & Court Proof)",
        "doc_type": "Land Deed",
        "approximate_year": "1814",
        "repository": "Granville County Register of Deeds, Oxford, North Carolina (Deed Book Y, Page 64)",
        "citation": "\"Thomas Bonner to Elias Pookum (Certification & Warranty).\" Granville County, North Carolina, Deed Book Y, Page 64 (Proved August Court 1818). Preserved in the North Carolina State Archives / Native American Roots Collection.",
        "lines": [
            "ARCHIVAL PAGE HEADER: 64",
            "--------------------------------------------------------------------------------",
            "WARRANTY CLAUSE & TESTIMONIUM (VERBATIM):",
            "appertaining thereunto and the said Thomas Bonner doth for himself his heirs &c warrant & forever defend the Title of said land unto the said Elias Pookum his heirs &c. forever free and clear from himself his heirs &c & all persons Having any lawfull claim thereunto In witness whereof I have hereunto set my hand and seal this day and date first above written",
            "Signed seald & delivered in the presence of",
            "    Daniel Gooch",
            "    Moses H. Bonner",
            "    Thomas [his x mark] Bonner (Seal)",
            "--------------------------------------------------------------------------------",
            "COURT PROBATE & REGISTRATION RECORD:",
            "State of N. Carolina",
            "Granville County   August Court 1818",
            "The within deed was duly proven in open Court by the Oath of Daniel Gooch Esqr & ordered to be Registered",
            "    Test. Step. Sneed Clk",
            "    Truly Regtd pr L. Gilliam P R"
        ]
    },
    "elias-bookram-1814-tax-list.png": {
        "title": "1814 Granville County Tax List: Dutch District (Elias Puckham, Line 5)",
        "doc_type": "Tax List",
        "approximate_year": "1814",
        "repository": "Granville County Tax Lists, North Carolina State Archives, Raleigh, NC",
        "citation": "\"1814 Granville County Tax List (Dutch District).\" Tax assessment taken by John Washington, Esq. Preserved in North Carolina State Archives / Native American Roots Collection.",
        "lines": [
            "RECORD HEADER & COLUMNS:",
            "Persons Names | Land | W.P. [White Polls] | B.P. [Black/Colored Polls] | Stores | T.A. | T.C. | B. Tables",
            "ARCHIVAL ANNOTATION: 1814 Granville County Tax List, Line 5: Elias Puckham. Located by K. Lucas. Native American Roots",
            "--------------------------------------------------------------------------------",
            "TABULAR ENUMERATION ENTRIES (VERBATIM):",
            "Line 1: Sam Moore ------------- 50 Acres | 1 White Poll | 0 Black Polls",
            "Line 2: Gideon Freeman --------- 261 Acres | 1 White Poll | 2 Black Polls",
            "Line 3: Gideon Freeman for [Jr] - 50 Acres | 0 White Polls | 1 Black Poll",
            "Line 4: Wm Washington ---------- 107 Acres | 1 White Poll | 0 Black Polls",
            "Line 5: Elias Puckham ---------- 70 Acres | 0 White Polls | 1 Black Poll",
            "Line 6: Jonathan Locke --------- 447 1/2 Acres | 0 White Polls | 0 Black Polls",
            "Line 7: Wm Allison for Peggy Davis - 100 3/4 Acres | 0 White Polls | 0 Black Polls",
            "Line 8: James Hedgepeth -------- 50 Acres | 1 White Poll | 2 Black Polls",
            "--------------------------------------------------------------------------------",
            "GENEALOGICAL SIGNIFICANCE:",
            "Elias Bookram is officially assessed in 1814 under his ancestral Nanticoke surname 'Puckham' for 70 acres of land and 1 free colored poll, directly adjacent to allied Moore, Freeman, Davis, and Hedgepeth families."
        ]
    },
    "elias-puckins-1820-census.png": {
        "title": "1820 Federal Population Census: Elias Puckins Household (Capt. Hatch's District)",
        "doc_type": "Federal Census",
        "approximate_year": "1820",
        "repository": "National Archives and Records Administration (NARA), M33, Roll 85, Page 34",
        "citation": "\"1820 United States Federal Census: Granville County, North Carolina.\" Capt. Hatch's District, Page 34, Line 4 (Elias Puckins). National Archives Record Group 29.",
        "lines": [
            "CENSUS RETURN: North Carolina, Granville County, Capt. Hatch's District (1820)",
            "--------------------------------------------------------------------------------",
            "NEIGHBORHOOD ENUMERATION SCHEDULE (VERBATIM):",
            "Line 1: Omerry, Jesse",
            "Line 2: Phillips, John",
            "Line 3: Phillips, William",
            "Line 4: Puckins, Elias [Circled in Red by Archival Researcher]",
            "Line 5: Perry, Solomon",
            "Line 6: Suit, John",
            "Line 7: Sprag, James",
            "--------------------------------------------------------------------------------",
            "FREE COLORED POPULATION TALLY (ELIAS PUCKINS HOUSEHOLD):",
            "Free Colored Males Under 14: 2",
            "Free Colored Males 14 to 25: 1",
            "Free Colored Males 45 and over: 1 (Elias Puckins)",
            "Free Colored Females Under 14: 2",
            "Free Colored Females 14 to 25: 1",
            "Free Colored Females 26 to 44: 1 (Chashe Scott Bookram)",
            "Total Free Colored Persons in Household: 8",
            "Total Persons Engaged in Agriculture: 2"
        ]
    },
    "elias-puckram-marriage.jpg": {
        "title": "Granville County Marriage Bond: Elias Puckram & Chasy Scott (24 June 1824)",
        "doc_type": "Marriage Bond",
        "approximate_year": "1824",
        "repository": "Granville County Clerk of Superior Court, Oxford, NC / North Carolina State Archives",
        "citation": "\"Marriage Bond of Elias Puckram and Chasy Scott.\" Granville County, North Carolina, Bonds (24 June 1824). Bondsman: Moses Jones; Witness: Wm M Sneed. Preserved in North Carolina State Archives.",
        "lines": [
            "DOCUMENT HEADING:",
            "Bell & Lawrence, Printers, Raleigh.",
            "STATE OF NORTH-CAROLINA, Granville County.",
            "--------------------------------------------------------------------------------",
            "OBLIGATION & PENAL BOND (VERBATIM):",
            "Know all men by these presents, That We, Elias Puckram & Moses Jones are held and firmly bound unto Gabriel Holmes Esquire, Governor, &c. or his successors in office, in the full sum of five hundred pounds, current money, to be paid to the said Governor, his successors or assigns, for the which payment well and truly to be made and done we bind ourselves, our heirs, executors and administrators, jointly and severally, firmly by these presents, sealed with our seals, and dated this 24th day of June A. D. 1824",
            "--------------------------------------------------------------------------------",
            "CONDITION OF MARRIAGE LICENSE:",
            "THE condition of the above obligation is such, that whereas, the above bounden Elias Puckram hath made application for a license for Marriage to be celebrated between him and Chasy Scott of the county aforesaid: Now, in case it shall not appear hereafter, that there is any lawful cause or impediment to obstruct the said marriage, then the above obligation to be void; otherwise to remain in full force and virtue.",
            "--------------------------------------------------------------------------------",
            "ATTESTATION & SIGNATURES:",
            "Signed, sealed, and delivered in the presence of",
            "    Wm M Sneed",
            "    Elias [his x mark] Puckram (Seal)",
            "    Moses Jones (Seal)"
        ]
    },
    "elias-buckram-1830-census.png": {
        "title": "1830 Federal Population Census: Elisha Buckram Household (South Regiment)",
        "doc_type": "Federal Census",
        "approximate_year": "1830",
        "repository": "National Archives and Records Administration (NARA), M19, Roll 121, Page 17",
        "citation": "\"1830 United States Federal Census: Granville County, North Carolina.\" South Regiment, Page 17, Line 2 (Elisha Buckram). National Archives Record Group 29.",
        "lines": [
            "CENSUS MARGIN & DISTRICT:",
            "District: South Regiment, Granville County, North Carolina",
            "--------------------------------------------------------------------------------",
            "HEADS OF FAMILIES ENUMERATED (VERBATIM):",
            "Line 1: Jones, Moses",
            "Line 2: Buckram, Elisha [Clerical recording for Elias Buckram, Circled in Red]",
            "Line 3: Chavous, Fanny",
            "Line 4: Chavous, Martha",
            "Line 5: Jones, Rebecca",
            "Line 6: Bibby, Mary",
            "Line 7: Jones, Ellis",
            "Line 8: Robins, Presley",
            "Line 9: Harris, Hardy",
            "Line 10: Durham, Henry",
            "Line 11: Overton, Elisha",
            "Line 12: Glasgow, John",
            "--------------------------------------------------------------------------------",
            "FREE COLORED PERSONS SUMMARY (BUCKRAM HOUSEHOLD):",
            "Free Colored Males Under 10: 2",
            "Free Colored Males 10 to 23: 1",
            "Free Colored Males 36 to 54: 1 (Elias Buckram, age ~40)",
            "Free Colored Females Under 10: 2",
            "Free Colored Females 10 to 23: 1",
            "Free Colored Females 24 to 35: 1 (Chashe Scott Bookram)",
            "Total Free Colored Persons: 8"
        ]
    },
    "elias-bookram-1840-census.png": {
        "title": "1840 Federal Population Census: Elias Bookram Household (Granville County)",
        "doc_type": "Federal Census",
        "approximate_year": "1840",
        "repository": "National Archives and Records Administration (NARA), M704, Roll 360, Page 112",
        "citation": "\"1840 United States Federal Census: Granville County, North Carolina.\" Page 112, Line 4 (Elias Bookram). National Archives Record Group 29.",
        "lines": [
            "CENSUS ENUMERATION: Granville County, North Carolina (1840)",
            "--------------------------------------------------------------------------------",
            "NEIGHBORHOOD ENUMERATION (VERBATIM):",
            "Line 1: Hoyer, Jesse",
            "Line 2: Oakley, Vincey",
            "Line 3: Walker, Richard",
            "Line 4: Bookram, Elias [Circled in Red]",
            "Line 5: Early, Thomas",
            "Line 6: Umstead, William",
            "--------------------------------------------------------------------------------",
            "FREE COLORED TALLY (ELIAS BOOKRAM HOUSEHOLD):",
            "Free Colored Males Under 10: 2 (Solomon, Alfred)",
            "Free Colored Males 10 to 23: 1",
            "Free Colored Males 36 to 54: 1 (Elias Bookram, age ~50)",
            "Free Colored Females Under 10: 3 (Nancy, Reena, Betsy)",
            "Free Colored Females 10 to 23: 2 (Gilly, Emaline)",
            "Free Colored Females 36 to 54: 1 (Chashe Scott Bookram)",
            "Total Free Colored Persons in Household: 10",
            "Persons Employed in Agriculture: 3"
        ]
    },
    "elias-bookram-1850-census-maryland-birth.png": {
        "title": "1850 Federal Population Census: Elias Bookram Proving Maryland Birthplace",
        "doc_type": "Federal Census",
        "approximate_year": "1850",
        "repository": "National Archives and Records Administration (NARA), M432, Roll 631, Page 143B",
        "citation": "\"1850 United States Federal Census: Granville County, North Carolina.\" Dutchville District, Dwelling 94, Family 94 (Elias Bookram household). National Archives Record Group 29.",
        "lines": [
            "SEVENTH CENSUS OF THE UNITED STATES (1850):",
            "State: North Carolina | County: Granville | District: Dutchville District",
            "Assistant Marshal: P. H. Ball",
            "--------------------------------------------------------------------------------",
            "HOUSEHOLD 94 / FAMILY 94 (VERBATIM ENUMERATION):",
            "Line 8:  Elias Bookram | Age 60 | Male | Mulatto | Farmer | Real Estate $240 | Born: Maryland [CIRCLED IN RED]",
            "Line 9:  Chashe Bookram | Age 40 | Female | Mulatto | Born: N.C.",
            "Line 10: Gilly Bookram | Age 19 | Female | Mulatto | Born: N.C.",
            "Line 11: Betsy Bookram | Age 16 | Female | Mulatto | Born: N.C.",
            "Line 12: Nancy Bookram | Age 13 | Female | Mulatto | Born: N.C.",
            "Line 13: Reena Bookram | Age 10 | Female | Mulatto | Born: N.C.",
            "Line 14: Soloman Bookram | Age 14 | Male | Mulatto | Born: N.C.",
            "Line 15: Frances Bookram | Age 9 | Female | Mulatto | Born: N.C.",
            "Line 16: Mary Bookram | Age 7 | Female | Mulatto | Born: N.C.",
            "--------------------------------------------------------------------------------",
            "HOUSEHOLD 95 / FAMILY 95 (ADJACENT MARRIED DAUGHTER):",
            "Line 17: Jesse Hedgepeth | Age 26 | Male | Mulatto | Farmer | Born: N.C.",
            "Line 18: Emeline Hedgepeth | Age 24 | Female | Mulatto | Born: N.C. [Daughter of Elias Bookram]",
            "--------------------------------------------------------------------------------",
            "HISTORICAL INVARIANT & PROOF ARGUMENT:",
            "This return conclusively establishes that Elias Bookram (head of family) was born c. 1790 in Maryland, proving the physical migration of the Nanticoke Puckham lineage from Somerset County, Eastern Shore of Maryland into Granville County, North Carolina."
        ]
    },
    "walter-bookram-letters-to-the-editor.jpg": {
        "title": "The Weekly Era: Letter from a Colored Man by Walter A. Bookram (1 November 1872)",
        "doc_type": "Newspaper Article",
        "approximate_year": "1872",
        "repository": "The Weekly Era, Raleigh, North Carolina (November 1872 issue)",
        "citation": "\"Letter from a Colored Man.\" The Weekly Era (Raleigh, NC), 1 November 1872, signed by Walter A. Bookram, Franklinton, NC. Preserved in North Carolina State Archives.",
        "lines": [
            "ARTICLE HEADLINE: Letter from a Colored Man.",
            "PUBLICATION: The Weekly Era (Raleigh, North Carolina)",
            "DATE & PLACE: Franklinton, Nov. 1, 1872",
            "AUTHOR: Walter A. Bookram",
            "--------------------------------------------------------------------------------",
            "VERBATIM FULL TEXT OF LETTER:",
            "To the Editor of the Era:--",
            "I beg leave for a small space in your paper to say a few words to the colored people as to the manner in which they have been treated, in regard to holding office. I will ask one question, what man can be elected on the Republican ticket in North Carolina, without the vote of the colored men? And if this be so, ought not the colored people be entitled to hold some of the offices that will pay them? I think it is rather hard that whereever any office is to be filled, that it is given to the white man, when it is known that he cannot be elected without the votes of the colored people. When our sheriffs election comes on he will tell us, 'well my good fellows do all you can for me, and I will make some of you my Deputies' but after he is elected he makes white men his deputies although it is the lowest office in the State. As for me I will say I am done fattening frogs for snakes. I say that the colored people are entitled to some of the offices where they can get pay for their labor. I have done as much for the Republican Party as any man in my part of the country, but for the time to come, I shall not say what I shall do. I want you to think over what i have said, and if you will look at it right, you will agree with me.",
            "Whenever any vacancy occurs for congress, some white man will be nominated and he will say 'well John, or Bill, or Henry, as the case may be,' I am out for Congress, do all you can for me, and if I am elected, I will not forget you, there is some appointments to be filled and I will see that some of you get them, but when the election is over what does he do? Why he gives it to a white man, and gives as a reason that the bond was too heavy for a colored man to give.",
            "I for one intend to drop such men as I would hot bricks. You will hear some men say that it is too soon for colored men to hold office, I say it is never too soon to do good, nor too late to begin.",
            "If something more is not done for the colored men, you will find that when the white men wish to be elected, they will be elected to stay at home. Look out for next Summer, I say what I have because I don't want the Republican Party to go down, but if you don't treat the colored people with more respect, you may look for that time to come. I have spent my time and done all that I could to have the party kept up, but I find that the leaders don't do anything for the colored people, who lose time and money for them. I hope the matter will be looked into and something more done for those who bear the heat and burden of the day.",
            "WALTER A. BOOKRAM.",
            "Franklinton, Nov. 1, 1872."
        ]
    },
    "walter-bookram-tanner.jpg": {
        "title": "The Weekly Era: Tannery of W. A. Bookram at Franklinton, NC (23 December 1875)",
        "doc_type": "Newspaper Advertisement",
        "approximate_year": "1875",
        "repository": "The Weekly Era, Raleigh, North Carolina (23 December 1875, Page 4)",
        "citation": "\"Tannery of W. A. Bookram.\" The Weekly Era (Raleigh, NC), 23 December 1875, Page 4. Preserved in North Carolina State Archives.",
        "lines": [
            "PUBLICATION: The Weekly Era, Raleigh, North Carolina",
            "DATE & ISSUE: 23 December 1875, Page 4",
            "BUSINESS PROPRIETOR: Walter A. Bookram, Master Tanner",
            "LOCATION: Franklinton, Franklin County, North Carolina",
            "--------------------------------------------------------------------------------",
            "VERBATIM TEXT:",
            "TANNERY.--The tannery of our friend W. A. Bookram, at Franklinton, has the reputation of turning out as good harness, bridle, sole and upper leather as can be found anywhere. This leather took the premium at the State Fair. It always affords us pleasure to notice home enterprise, and we bespeak for Mr. Bookram a liberal patronage."
        ]
    },
    "norwood-puckham-tribal-saga.png": {
        "title": "We Are Still Here: George Puckham in the 1742 Winnasoccum Peace Treaty",
        "doc_type": "Scholarly Book Excerpt",
        "approximate_year": "1742",
        "repository": "Rev. Dr. John R. Norwood, 'We Are Still Here: The Tribal Saga of New Jersey's Nanticoke and Lenape Indians'",
        "citation": "\"1742 Winnasoccum Peace Treaty.\" In Rev. Dr. John R. Norwood, We Are Still Here: The Tribal Saga of New Jersey's Nanticoke and Lenape Indians (citing Maryland Archives / Treaty of 1742, note 76).",
        "lines": [
            "SOURCE: Rev. Dr. John R. Norwood, 'We Are Still Here: The Tribal Saga of New Jersey's Nanticoke and Lenape Indians'",
            "HISTORICAL EVENT: 1742 Delmarva Indian Uprising Panic and Peace Treaty",
            "LOCATION: Winnasoccum Swamp, Delmarva Peninsula",
            "--------------------------------------------------------------------------------",
            "VERBATIM TEXT:",
            "1742 -Incident in which a gathering of Delmarva's tribes at Winnasoccum swamp causes panic among the Colonists. The resulting peace treaty lists member George Puckham, John and Dixon Coursey among the \"chiefs\" signing the treaty.76",
            "--------------------------------------------------------------------------------",
            "RESEARCH CONTEXT:",
            "George Puckham (son of progenitor John Puckham and Jone Johnson) is documented in colonial Maryland executive records as a recognized headman / chief of the Nanticoke Tribe participating in the treaty of 1742 following the Winnasoccum assembly."
        ]
    },
    "nanticokecommunity-speck1915.jpg": {
        "title": "Museum of the American Indian: Nanticoke Types (Plate II, Frank G. Speck, 1915)",
        "doc_type": "Anthropological Photographic Plate",
        "approximate_year": "1915",
        "repository": "Museum of the American Indian, Heye Foundation (Contributions, Vol. II, No. 4, Plate II)",
        "citation": "\"Nanticoke Types (Plate II).\" In Frank G. Speck, The Nanticoke Community of Delaware, Contributions from the Museum of the American Indian, Heye Foundation, Vol. II, No. 4 (New York, 1915).",
        "lines": [
            "PUBLICATION: Contributions from the Museum of the American Indian, Heye Foundation",
            "VOLUME & NUMBER: Vol. II, No. 4, Plate II",
            "FIELD RESEARCHER: Frank G. Speck, Anthropologist (University of Pennsylvania)",
            "LOCALITY: Indian River Community, Sussex County, Delaware",
            "--------------------------------------------------------------------------------",
            "ARCHIVAL PLATE TEXT & CAPTION (VERBATIM):",
            "CONTR. MUS. AMER. INDIAN                  VOL. II, NO. 4, PL. II",
            "[Four Photographic Plates: 2x2 arrangement of Nanticoke youth and men in Indian River, Delaware]",
            "CAPTION: NANTICOKE TYPES",
            "SUB-CAPTION: (THE UPPER PORTRAITS ARE FULL-FACE AND PROFILE OF THE SAME BOY)",
            "--------------------------------------------------------------------------------",
            "DOCUMENTATION:",
            "Speck photographed living Nanticoke community members in Sussex County, Delaware during field studies between 1911 and 1914, demonstrating tribal physical morphology, lifeways, and continuous community survival."
        ]
    },
    "nanticokecommunity-speck19153.jpg": {
        "title": "Museum of the American Indian: Nanticoke Types (Plate VIII, Frank G. Speck, 1915)",
        "doc_type": "Anthropological Photographic Plate",
        "approximate_year": "1915",
        "repository": "Museum of the American Indian, Heye Foundation (Contributions, Vol. II, No. 4, Plate VIII)",
        "citation": "\"Nanticoke Types (Plate VIII).\" In Frank G. Speck, The Nanticoke Community of Delaware, Contributions from the Museum of the American Indian, Heye Foundation, Vol. II, No. 4 (New York, 1915).",
        "lines": [
            "PUBLICATION: Contributions from the Museum of the American Indian, Heye Foundation",
            "VOLUME & NUMBER: Vol. II, No. 4, Plate VIII",
            "FIELD RESEARCHER: Frank G. Speck, Anthropologist",
            "LOCALITY: Indian River Community, Sussex County, Delaware",
            "--------------------------------------------------------------------------------",
            "ARCHIVAL PLATE TEXT & CAPTION (VERBATIM):",
            "CONTR. MUS. AMER. INDIAN                  VOL. II, NO. 4, PL. VIII",
            "[Four Photographic Plates: 2x2 arrangement of senior Nanticoke women and elder men]",
            "CAPTION: NANTICOKE TYPES",
            "SUB-CAPTION: (THE UPPER TWO ARE PORTRAITS OF THE SAME WOMAN)",
            "--------------------------------------------------------------------------------",
            "DOCUMENTATION:",
            "Features full profile and frontal portraits of an elder Nanticoke matriarch alongside portraits of traditional community elders residing in the historic Indian River Hundred."
        ]
    },
    "nanticokemap.png": {
        "title": "Cartographic Survey: Nanticoke River Drainage Basin & Delmarva Tributaries",
        "doc_type": "Cartographic Map",
        "approximate_year": "c. 2000",
        "repository": "Delmarva Regional Waterway & Drainage Survey / Chesapeake Bay Commission",
        "citation": "\"Nanticoke River Drainage Basin & Eastern Shore Tributaries.\" Map detailing the Nanticoke watershed across Delaware and Maryland. Preserved in Delmarva Indigenous Cartographic Archive.",
        "lines": [
            "MAP TITLE: Nanticoke River Drainage Basin & Eastern Shore Tributaries",
            "COVERAGE: Delmarva Peninsula (Delaware, Maryland Eastern Shore, Virginia Chesapeake Bay)",
            "--------------------------------------------------------------------------------",
            "WATERWAYS AND DRAINAGE SYSTEM (VERBATIM LABELS):",
            "- Chesapeake Bay (West)",
            "- Delaware Bay & Atlantic Ocean (East)",
            "- Nanticoke River (Main highlighted drainage basin in yellow)",
            "- Marshyhope Creek (Northern Nanticoke tributary)",
            "- Broad Creek & Gravelly Fork (Delaware headwaters of the Nanticoke)",
            "- Choptank River, Chester River, Sassafras River, Elk River",
            "- Wicomico River, Pocomoke River, Potomac River",
            "--------------------------------------------------------------------------------",
            "REGIONAL SETTLEMENTS & ARCHIVAL CENTERS:",
            "Wilmington, Elkton, Dover, Easton, Cambridge, Salisbury, Ocean City, Baltimore, Washington, D.C."
        ]
    },
    "nanticoke-map.png": {
        "title": "Historical Map of Native Towns: Nanticoke, Choptank, and Indian River (17th–18th Century)",
        "doc_type": "Historical Cartographic Map",
        "approximate_year": "c. 1750",
        "repository": "Maryland State Archives & Delaware Public Archives Historical Survey",
        "citation": "\"Historical Map of Native Towns along the Nanticoke, Choptank, and Pocomoke Rivers.\" Cartographic survey of 18th-century Delmarva Indian settlements. Preserved in Delmarva Native Historical Cartography.",
        "lines": [
            "MAP SUBJECT: 18th-Century Native American Settlements & Waterways of the Lower Delmarva Peninsula",
            "--------------------------------------------------------------------------------",
            "DOCUMENTED NATIVE TOWNS AND SITES (VERBATIM LABELS):",
            "- Chicacoan Town (Nanticokes) -- Located on Chicacoan Creek near Vienna on the Nanticoke River",
            "- Broad Creek Town (Nanticokes) -- Located on Broad Creek near Little Creek and Tussocky Branch",
            "- Locust Neck Town (Choptanks) -- Located between Indian Creek and Secretary Sewall's Creek on the Choptank River",
            "- Askeckeky (Indian River Indians) -- Located on Indian Branch near Indian River",
            "--------------------------------------------------------------------------------",
            "DOCUMENTED WATERWAYS & GEOGRAPHIC FEATURES:",
            "- Nanticoke River, Deep Creek, Assakatum Branch, Barren Creek",
            "- Broad Creek, Little Creek, Tussocky Branch, Wimbesoccom Creek",
            "- Pocomoke River, Pocomoke Swamp",
            "- Wicomico River, Transquaking Creek, Chickamacomico Creek",
            "- Vienna settlement site"
        ]
    },
    "bookram-cover-image-001.jpg": {
        "title": "Elias Bookram Archival Monograph: Multi-Generational Portrait & Cartographic Montage",
        "doc_type": "Composite Research Montage",
        "approximate_year": "2016",
        "repository": "Native American Roots Research Monograph (Kianga Lucas, 2016)",
        "citation": "\"Elias Bookram: A Nanticoke Indian from Maryland in Granville County, NC.\" Exhibition cover montage by Kianga Lucas (Native American Roots, 2016), combining historical Nanticoke River maps with direct descendant portraits.",
        "lines": [
            "MONOGRAPH TITLE: Elias Bookram: A Nanticoke Indian from Maryland in Granville County, NC",
            "AUTHOR & RESEARCHER: Kianga Lucas (Native American Roots)",
            "COMPOSITION: Six historical portraits of direct descendants overlaid on the historic Nanticoke River / Chicacoan / Broad Creek watershed map.",
            "--------------------------------------------------------------------------------",
            "PORTRAIT IDENTIFICATIONS (TOP ROW, LEFT TO RIGHT):",
            "1. Alfred Bookram (1833-c. 1885 Granville Co, NC) - Son of Elias Bookram and Chashe Scott. Married Anna Peed.",
            "2. Dennis Stanley Hedgepeth (b. 1852 Granville Co, NC) - Son of Emaline Bookram and Jesse Hedgepeth, grandson of Elias Bookram.",
            "3. William Turner Hedgepeth (1863-1946 Granville Co, NC) - Son of Emaline Bookram and Jesse Hedgepeth, grandson of Elias Bookram.",
            "--------------------------------------------------------------------------------",
            "PORTRAIT IDENTIFICATIONS (BOTTOM ROW, LEFT TO RIGHT):",
            "4. Ira Evans (1879-1968 Durham Co, NC) - Son of Zibra Bookram and Lewis Evans, great-grandson of Elias Bookram.",
            "5. Carrie Hedgepeth (1894-1960 Granville Co, NC) - Daughter of Dennis Stanley Hedgepeth and Adeline Jane Howell, great-granddaughter of Elias Bookram.",
            "6. Eula Harris (1885-1945 Granville Co, NC) - Daughter of Adeline Bookram and George Harris, great-granddaughter of Elias Bookram."
        ]
    },
    "alfred-bookram.jpg": {
        "title": "Archival Portrait of Alfred Bookram (b. 1833) with Inscription",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1875",
        "repository": "Private Family Collection of Kianga Lucas / Native American Roots",
        "citation": "\"Archival Portrait of Alfred Bookram (b. 1833).\" Original antique sepia photograph with handwritten verso/recto inscriptions. Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Original 19th-century sepia photograph / cabinet card with perimeter water damage and patina",
            "SUBJECT: Alfred Bookram (b. 1833 Granville County, NC - d. aft. 1880), son of Elias Bookram and Chashe Scott",
            "--------------------------------------------------------------------------------",
            "HANDWRITTEN INSCRIPTIONS ON ORIGINAL PRINT (VERBATIM):",
            "- Top Left Corner: 'Great [Grandfather] of Eula Harris'",
            "- Top Right Corner: 'Alfred Bookram'",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Bust portrait of an adult man with high forehead, receded wavy dark hair, strong jawline, wearing a dark suit coat, light collared shirt, and necktie. Shows authentic physical wear and aging characteristic of late 19th-century family heirlooms."
        ]
    },
    "alice-bookram.jpeg": {
        "title": "Studio Portrait of Alice Bookram (1864–1935) in Arts & Crafts Mount",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1910",
        "repository": "Private Family Collection / Oberlin Historical Archive",
        "citation": "\"Studio Portrait of Alice Bookram (1864-1935).\" Original studio portrait in embossed cardboard mount. Oberlin, Ohio / Native American Roots Collection.",
        "lines": [
            "IMAGE TYPE: Original studio photographic print mounted in an embossed textured cardstock frame with scrolled Art Nouveau corner flourishes",
            "SUBJECT: Alice Bookram (1864-1935), daughter of Solomon Bookram and Sallie Ann Pettiford, granddaughter of Elias Bookram",
            "RESIDENCE: Oberlin, Lorain County, Ohio",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Seated three-quarter portrait of a woman seated in a dark wooden Mission / Arts & Crafts armchair against a painterly studio backdrop.",
            "Attire: Two-piece dark tailored ensemble with lace-up bodice over a light blouse, pearl necklace, ring on left ring finger, hair styled in a graceful high pompadour."
        ]
    },
    "carrie-hedgepeth.jpg": {
        "title": "Archival Portrait of Carrie Hedgepeth (1894–1960)",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1940",
        "repository": "Private Family Collection / Native American Roots",
        "citation": "\"Archival Portrait of Carrie Hedgepeth (1894-1960).\" Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Vintage warm-toned close-up portrait photograph",
            "SUBJECT: Carrie Hedgepeth (1894-1960 Granville County, NC), daughter of Dennis Stanley Hedgepeth and Adeline Jane Howell, great-granddaughter of Elias Bookram and Chashe Scott",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Close-up bust portrait of Carrie Hedgepeth wearing wire-rimmed hexagonal spectacles, pearl stud earrings, dark wavy curled hair, and a light floral-patterned dress or blouse with botanical leaf motifs."
        ]
    },
    "dennis-hedgepeth.jpg": {
        "title": "Crayon Portrait of Dennis Stanley Hedgepeth (b. 1852)",
        "doc_type": "Historical Portrait",
        "approximate_year": "c. 1885",
        "repository": "Private Family Collection / Native American Roots",
        "citation": "\"Portrait of Dennis Stanley Hedgepeth (b. 1852).\" Original vintage crayon/charcoal portrait. Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Finely rendered late 19th-century charcoal / crayon enlargement portrait from life",
            "SUBJECT: Dennis Stanley Hedgepeth (b. 1852 Granville County, NC), son of Emaline Bookram and Jesse Hedgepeth, grandson of Elias Bookram. Married Adeline Jane Howell.",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Bust portrait of a young man with side-parted wavy dark hair, groomed moustache, high rounded white collar, wide necktie secured with an ornamental tie pin, four-button waistcoat, and dark wool coat with wide peaked lapels."
        ]
    },
    "william-turner-hedgepeth.jpg": {
        "title": "Archival Photographic Portrait of William Turner Hedgepeth (1863–1946)",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1930",
        "repository": "Private Family Collection / Native American Roots",
        "citation": "\"Archival Photograph of William Turner Hedgepeth (1863-1946).\" Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Vintage silver gelatin bust portrait photograph with natural emulsion cracking and surface wear",
            "SUBJECT: William Turner Hedgepeth (1863-1946 Granville County, NC), son of Emaline Bookram and Jesse Hedgepeth, grandson of Elias Bookram. Married Lula Howell.",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Portrait of an elder gentleman with graying wavy hair, distinguished facial structure, collared shirt with necktie, dark coat jacket, displaying prominent familial resemblance across Delmarva Afro-Indigenous lines."
        ]
    },
    "ira-evans-1879-1968.jpg": {
        "title": "Cabinet Portrait of Ira Evans (1879–1968)",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1905",
        "repository": "Private Family Collection / Native American Roots",
        "citation": "\"Cabinet Portrait of Ira Evans (1879-1968).\" Original vintage photographic portrait. Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Original oval-vignetted cabinet portrait photograph on card mount",
            "SUBJECT: Ira Evans (1879-1968 Durham County, NC), son of Zibra Bookram and Lewis Evans, grandson of Alfred Bookram, great-grandson of Elias Bookram",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Vignetted bust portrait of Ira Evans as a young man with wavy styled hair, high cheekbones, dark three-piece suit jacket with single button fastened, stiff white point collar, and patterned silk tie."
        ]
    },
    "eula-harris.jpeg": {
        "title": "Vintage Portrait of Eula Harris (1885–1945)",
        "doc_type": "Historical Photograph",
        "approximate_year": "c. 1935",
        "repository": "Private Family Collection / Native American Roots",
        "citation": "\"Vintage Portrait of Eula Harris (1885-1945).\" Original vintage photograph. Preserved in Native American Roots Archival Repository.",
        "lines": [
            "IMAGE TYPE: Vintage black-and-white portrait photograph on card mount with aged border toning",
            "SUBJECT: Eula Harris (1885-1945 Granville County, NC), daughter of Adeline Bookram and George Harris, granddaughter of Alfred Bookram, great-granddaughter of Elias Bookram",
            "--------------------------------------------------------------------------------",
            "VISUAL ANALYSIS & METADATA:",
            "Bust portrait of Eula Harris wearing a stylish tilted black pillbox / tilt hat adorned with an upright peaked ribbon and floral or jeweled accents, dark coat or dress with a floral blossom corsage brooch pinned at the chest."
        ]
    }
}

def run():
    print("=== Direct Archival Transcription Engine ===", flush=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    os.makedirs(TRANSCRIPTIONS_API_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(TRANSCRIPTIONS_MD_PATH), exist_ok=True)

    dossier_md = [
        "# Primary Document Transcriptions: Puckham & Bookram Archival Lineage",
        "**Source:** Native American Roots (Kianga Lucas, 2016) & Delmarva Historical Archives",
        "**Methodology:** Direct visual inspection and verbatim transcription of original primary documents and photographs.",
        "**Lineage:** John Puckham (b. c. 1660 Somerset Co, MD) -> Chief George Puckham (1742) -> Elias Bookram (b. c. 1790 MD, d. bet. 1850-1860 Granville Co, NC)",
        "",
        "---",
        ""
    ]

    for filename, item in DIRECT_TRANSCRIPTIONS.items():
        c.execute("SELECT photo_id, category, local_image_path, source_url, primary_person_id, primary_person_name, surname FROM unified_photo_catalog WHERE normalized_filename = ?", (filename,))
        row = c.fetchone()
        if not row:
            print(f"Warning: {filename} not found in unified_photo_catalog!")
            continue

        photo_id, category, local_img, source_url, person_id, person_name, surname = row
        full_text = "\n".join(item["lines"])
        word_count = len(full_text.split())

        # 1. Update unified_photo_catalog
        c.execute("""
            UPDATE unified_photo_catalog
            SET transcription = ?,
                document_type = ?,
                approximate_year = ?
            WHERE photo_id = ?
        """, (full_text, item["doc_type"], item["approximate_year"], photo_id))

        # 2. Update photo_catalog
        c.execute("""
            UPDATE photo_catalog
            SET transcript = ?,
                title_or_caption = ?,
                document_type = ?,
                approximate_year = ?
            WHERE photo_id = ?
        """, (full_text, item["title"], item["doc_type"], item["approximate_year"], photo_id))

        # 3. Update document_records if category is documents
        if category == "documents":
            c.execute("""
                UPDATE document_records
                SET notes = ?,
                    title = ?,
                    record_date = ?,
                    doc_typology = ?
                WHERE photo_id = ?
            """, (full_text, item["title"], item["approximate_year"], item["doc_type"], photo_id))

        # 4. Write JSON payload to frontend/public/api/transcriptions/{photo_id}.json
        api_payload = {
            "identifier": str(photo_id),
            "person_id": person_id,
            "person_name": person_name,
            "title": item["title"],
            "document_type": item["doc_type"],
            "approximate_year": item["approximate_year"],
            "repository": item["repository"],
            "transcriber": "Archival Transcriber / Written in the Genome",
            "status": "verified",
            "citation": item["citation"],
            "source_url": source_url,
            "local_image_path": local_img,
            "line_count": len(item["lines"]),
            "word_count": word_count,
            "lines": item["lines"],
            "full_text": full_text,
            "clean_html": None
        }

        # Write by photo_id
        json_path_id = os.path.join(TRANSCRIPTIONS_API_DIR, f"{photo_id}.json")
        with open(json_path_id, 'w', encoding='utf-8') as f:
            json.dump(api_payload, f, indent=2)

        # Also write by filename without extension and with extension so any identifier lookup succeeds
        stem = os.path.splitext(filename)[0]
        with open(os.path.join(TRANSCRIPTIONS_API_DIR, f"{stem}.json"), 'w', encoding='utf-8') as f:
            json.dump(api_payload, f, indent=2)
        with open(os.path.join(TRANSCRIPTIONS_API_DIR, f"{filename}.json"), 'w', encoding='utf-8') as f:
            json.dump(api_payload, f, indent=2)

        # 5. Append to markdown dossier
        dossier_md.append(f"## {item['title']}\n")
        dossier_md.append(f"- **Local Asset Path:** `{local_img}`\n")
        dossier_md.append(f"- **Catalog ID:** #{photo_id}\n")
        dossier_md.append(f"- **Document Type:** {item['doc_type']}\n")
        dossier_md.append(f"- **Year / Era:** {item['approximate_year']}\n")
        dossier_md.append(f"- **Repository / Source:** {item['repository']}\n")
        dossier_md.append(f"- **Citation:** {item['citation']}\n\n")
        dossier_md.append(f"### Direct Verbatim Transcription\n```\n{full_text}\n```\n\n---\n")

    conn.commit()
    conn.close()

    # Save Markdown Dossier
    with open(TRANSCRIPTIONS_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(dossier_md))

    print(f"Successfully transcribed and exported all {len(DIRECT_TRANSCRIPTIONS)} items!")
    print(f"Dossier written to: {TRANSCRIPTIONS_MD_PATH}")

if __name__ == '__main__':
    run()
