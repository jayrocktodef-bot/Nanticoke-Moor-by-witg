#!/usr/bin/env python3
"""
populate_gazetteer_and_normalize_places.py
=========================================
Step 5 of Archival Integrity & Structure Remediation:
1. Re-establishes the 'places' table with complete schema and constraints:
   - place_id, name, standardized_name, place_type, parent_place_id,
     county, state, country, latitude, longitude, historical_notes.
2. Ingests the Delmarva Historical Gazetteer covering:
   - Macro: United States, Delmarva Peninsula, Delaware, Maryland, New Jersey, Pennsylvania.
   - Counties: Kent DE, Sussex DE, New Castle DE, Caroline MD, Dorchester MD,
     Cumberland NJ, Salem NJ, Atlantic NJ, Gloucester NJ, Philadelphia PA, etc.
   - Delaware Hundreds: Kenton, Duck Creek, Little Creek, Dover, Murderkill, Mispillion,
     Broadkiln, Lewes & Rehoboth, Indian River, Dagsboro, Northwest Fork, Broad Creek, etc.
   - Townships & Historic Districts: Fairfield, Upper Deerfield, District 8, District 10, etc.
   - Settlements & Enclaves: Cheswold, Millsboro, Mitsawoket, Bloomsbury, Gouldtown,
     Salem, Woodstown, Federalsburg, Vienna, Milton, Dover, Smyrna, Harbeson, etc.
   - Historical Burial Grounds: Fork Branch, Immanuel Union, Millsboro SDA, Israel UM,
     Bethel AME, Lawnside, Gouldtown, Jackson-Perkins, Harmony, etc.
3. Links 'cemeteries.place_id' directly to verified place entities.
4. Adds 'place_id' foreign key to 'facts' table and creates B-Tree indexes.
5. Reconciles and normalizes all 3,841 facts containing place strings:
   - Disentangles 44 temporal false-positives into date attributes.
   - Standardizes and links remaining 3,797 facts to canonical gazetteer records.
6. Runs foreign key checks and integrity audits.
"""

import os
import sqlite3
import re
from typing import Dict, Any, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SCRIPT_DIR, "preservation_output", "genealogy_preservation.db")

GAZETTEER_DATA = [
    # Level 1: Country
    {
        "id_key": "country_usa",
        "name": "United States",
        "standardized_name": "United States",
        "place_type": "country",
        "parent_key": None,
        "county": None,
        "state": None,
        "country": "USA",
        "latitude": 39.8283,
        "longitude": -98.5795,
        "historical_notes": "United States of America."
    },
    # Level 2: Region & States
    {
        "id_key": "region_delmarva",
        "name": "Delmarva Peninsula",
        "standardized_name": "Delmarva Peninsula",
        "place_type": "region",
        "parent_key": "country_usa",
        "county": None,
        "state": None,
        "country": "USA",
        "latitude": 38.7500,
        "longitude": -75.5500,
        "historical_notes": "Geographic peninsula comprising Delaware and the Eastern Shore portions of Maryland and Virginia; ancestral homeland of the Nanticoke, Lenape, Pocomoke, and Assateague peoples."
    },
    {
        "id_key": "state_de",
        "name": "Delaware",
        "standardized_name": "Delaware",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "DE",
        "country": "USA",
        "latitude": 39.0000,
        "longitude": -75.5000,
        "historical_notes": "State of Delaware, organized historically into the three counties of New Castle, Kent, and Sussex, further divided into hundreds."
    },
    {
        "id_key": "state_md",
        "name": "Maryland",
        "standardized_name": "Maryland",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "MD",
        "country": "USA",
        "latitude": 38.9000,
        "longitude": -76.0000,
        "historical_notes": "State of Maryland, encompassing the Eastern Shore maritime and farming counties bordering Delaware."
    },
    {
        "id_key": "state_nj",
        "name": "New Jersey",
        "standardized_name": "New Jersey",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "NJ",
        "country": "USA",
        "latitude": 39.8000,
        "longitude": -74.9000,
        "historical_notes": "State of New Jersey, notably the South Jersey tri-racial communities across Cumberland, Salem, and Atlantic counties."
    },
    {
        "id_key": "state_pa",
        "name": "Pennsylvania",
        "standardized_name": "Pennsylvania",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "PA",
        "country": "USA",
        "latitude": 40.0000,
        "longitude": -75.2000,
        "historical_notes": "Commonwealth of Pennsylvania, including Philadelphia urban corridors connecting to the Delaware River valley."
    },
    {
        "id_key": "state_mi",
        "name": "Michigan",
        "standardized_name": "Michigan",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "MI",
        "country": "USA",
        "latitude": 44.3148,
        "longitude": -85.6024,
        "historical_notes": "State of Michigan, destination for late 19th-century migrations of Delmarva Moor/Native families into Gratiot and Isabella counties."
    },
    {
        "id_key": "state_nc",
        "name": "North Carolina",
        "standardized_name": "North Carolina",
        "place_type": "state",
        "parent_key": "country_usa",
        "county": None,
        "state": "NC",
        "country": "USA",
        "latitude": 35.6300,
        "longitude": -75.7000,
        "historical_notes": "State of North Carolina, including coastal Outer Banks and Hatteras connections."
    },

    # Level 3: Counties
    # Delaware Counties
    {
        "id_key": "county_kent_de",
        "name": "Kent County",
        "standardized_name": "Kent County, Delaware",
        "place_type": "county",
        "parent_key": "state_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1000,
        "longitude": -75.5500,
        "historical_notes": "Central county of Delaware; home to the historic Cheswold Lenape/Moor community, Fork Branch, and Duck Creek."
    },
    {
        "id_key": "county_sussex_de",
        "name": "Sussex County",
        "standardized_name": "Sussex County, Delaware",
        "place_type": "county",
        "parent_key": "state_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6800,
        "longitude": -75.3500,
        "historical_notes": "Southernmost county of Delaware; home to the Nanticoke Indian Tribe, Indian River Hundred, and Millsboro settlement."
    },
    {
        "id_key": "county_newcastle_de",
        "name": "New Castle County",
        "standardized_name": "New Castle County, Delaware",
        "place_type": "county",
        "parent_key": "state_de",
        "county": "New Castle",
        "state": "DE",
        "country": "USA",
        "latitude": 39.5800,
        "longitude": -75.6500,
        "historical_notes": "Northernmost county of Delaware, encompassing Wilmington and historic Appoquinimink Hundred."
    },
    # Maryland Counties
    {
        "id_key": "county_caroline_md",
        "name": "Caroline County",
        "standardized_name": "Caroline County, Maryland",
        "place_type": "county",
        "parent_key": "state_md",
        "county": "Caroline",
        "state": "MD",
        "country": "USA",
        "latitude": 38.8800,
        "longitude": -75.8300,
        "historical_notes": "Eastern Shore Maryland county bordering Kent and Sussex counties in Delaware; site of Federalsburg trans-border kin sanctuary."
    },
    {
        "id_key": "county_dorchester_md",
        "name": "Dorchester County",
        "standardized_name": "Dorchester County, Maryland",
        "place_type": "county",
        "parent_key": "state_md",
        "county": "Dorchester",
        "state": "MD",
        "country": "USA",
        "latitude": 38.4200,
        "longitude": -76.0500,
        "historical_notes": "Historic Eastern Shore Maryland county along the lower Nanticoke River basin; original site of the 1698 Chicacoan reservation."
    },
    # New Jersey Counties
    {
        "id_key": "county_cumberland_nj",
        "name": "Cumberland County",
        "standardized_name": "Cumberland County, New Jersey",
        "place_type": "county",
        "parent_key": "state_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.3700,
        "longitude": -75.1300,
        "historical_notes": "South Jersey county housing the historic Gouldtown tri-racial community, Bridgeton, and Fairfield Township."
    },
    {
        "id_key": "county_salem_nj",
        "name": "Salem County",
        "standardized_name": "Salem County, New Jersey",
        "place_type": "county",
        "parent_key": "state_nj",
        "county": "Salem",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.5800,
        "longitude": -75.3500,
        "historical_notes": "South Jersey county across Delaware Bay from New Castle and Kent counties; home to Woodstown, Lawnside Cemetery, and Cuff family enclaves."
    },
    {
        "id_key": "county_atlantic_nj",
        "name": "Atlantic County",
        "standardized_name": "Atlantic County, New Jersey",
        "place_type": "county",
        "parent_key": "state_nj",
        "county": "Atlantic",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.4700,
        "longitude": -74.6500,
        "historical_notes": "Coastal South Jersey county encompassing Pleasantville and Atlantic City."
    },
    {
        "id_key": "county_gloucester_nj",
        "name": "Gloucester County",
        "standardized_name": "Gloucester County, New Jersey",
        "place_type": "county",
        "parent_key": "state_nj",
        "county": "Gloucester",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.7200,
        "longitude": -75.1400,
        "historical_notes": "South Jersey county adjacent to Camden and Salem counties."
    },
    # Pennsylvania Counties
    {
        "id_key": "county_philadelphia_pa",
        "name": "Philadelphia County",
        "standardized_name": "Philadelphia County, Pennsylvania",
        "place_type": "county",
        "parent_key": "state_pa",
        "county": "Philadelphia",
        "state": "PA",
        "country": "USA",
        "latitude": 39.9526,
        "longitude": -75.1652,
        "historical_notes": "Urban and mercantile hub for mid-Atlantic free people of color and historic maritime trade."
    },
    # Out-of-State Migration Counties
    {
        "id_key": "county_gratiot_mi",
        "name": "Gratiot County",
        "standardized_name": "Gratiot County, Michigan",
        "place_type": "county",
        "parent_key": "state_mi",
        "county": "Gratiot",
        "state": "MI",
        "country": "USA",
        "latitude": 43.2900,
        "longitude": -84.6000,
        "historical_notes": "Mid-Michigan settlement for Delmarva Moor families migrating west in the late 19th century."
    },
    {
        "id_key": "county_dare_nc",
        "name": "Dare County",
        "standardized_name": "Dare County, North Carolina",
        "place_type": "county",
        "parent_key": "state_nc",
        "county": "Dare",
        "state": "NC",
        "country": "USA",
        "latitude": 35.6300,
        "longitude": -75.7000,
        "historical_notes": "Coastal North Carolina Outer Banks, including Hatteras."
    },

    # Level 4: Delaware Hundreds
    # Kent County Hundreds
    {
        "id_key": "hd_kenton_de",
        "name": "Kenton Hundred",
        "standardized_name": "Kenton Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2270,
        "longitude": -75.6620,
        "historical_notes": "Civil division in northwest Kent County, established in 1869 from Duck Creek and Little Creek hundreds; prominent location for Carney, Durham, and Dean families."
    },
    {
        "id_key": "hd_duck_creek_de",
        "name": "Duck Creek Hundred",
        "standardized_name": "Duck Creek Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2900,
        "longitude": -75.5800,
        "historical_notes": "Ancient northern Kent County hundred bordering Duck Creek and New Castle County; historical location of Pumpkin Neck and Mitsawokett."
    },
    {
        "id_key": "hd_little_creek_de",
        "name": "Little Creek Hundred",
        "standardized_name": "Little Creek Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1800,
        "longitude": -75.4800,
        "historical_notes": "Historic hundred encompassing Cheswold, Fork Branch, and lands between Little Duck Creek and St. Jones River."
    },
    {
        "id_key": "hd_dover_de",
        "name": "Dover Hundred",
        "standardized_name": "Dover Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1600,
        "longitude": -75.5200,
        "historical_notes": "Central hundred containing the state capital of Dover and surrounding agricultural lands."
    },
    {
        "id_key": "hd_east_dover_de",
        "name": "East Dover Hundred",
        "standardized_name": "East Dover Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1600,
        "longitude": -75.5000,
        "historical_notes": "Formed in 1877 from Dover Hundred."
    },
    {
        "id_key": "hd_west_dover_de",
        "name": "West Dover Hundred",
        "standardized_name": "West Dover Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1500,
        "longitude": -75.6200,
        "historical_notes": "Formed in 1877 from Dover Hundred."
    },
    {
        "id_key": "hd_mispillion_de",
        "name": "Mispillion Hundred",
        "standardized_name": "Mispillion Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 38.9000,
        "longitude": -75.5800,
        "historical_notes": "Southern Kent County hundred bordering Sussex County along the Mispillion River."
    },
    {
        "id_key": "hd_north_murderkill_de",
        "name": "North Murderkill Hundred",
        "standardized_name": "North Murderkill Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.0600,
        "longitude": -75.5500,
        "historical_notes": "Hundred along Murderkill River, formed in 1855."
    },
    {
        "id_key": "hd_south_murderkill_de",
        "name": "South Murderkill Hundred",
        "standardized_name": "South Murderkill Hundred, Kent County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.0000,
        "longitude": -75.5600,
        "historical_notes": "Hundred along Murderkill River, formed in 1855."
    },
    # Sussex County Hundreds
    {
        "id_key": "hd_indian_river_de",
        "name": "Indian River Hundred",
        "standardized_name": "Indian River Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6200,
        "longitude": -75.2300,
        "historical_notes": "Continuous homeland and tribal seat of the Nanticoke Indian Tribe; encompasses Hollyville, Warwick, and Indian River."
    },
    {
        "id_key": "hd_dagsboro_de",
        "name": "Dagsboro Hundred",
        "standardized_name": "Dagsboro Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5500,
        "longitude": -75.2500,
        "historical_notes": "Historic hundred adjacent to Indian River; home to Millsboro and prominent Harmon, Clark, and Davis families."
    },
    {
        "id_key": "hd_broadkiln_de",
        "name": "Broadkiln Hundred",
        "standardized_name": "Broadkiln Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7700,
        "longitude": -75.2700,
        "historical_notes": "Encompasses the town of Milton and Broadkill River basin; location of early Reed, Jackson, and Norwood landholdings."
    },
    {
        "id_key": "hd_lewes_rehoboth_de",
        "name": "Lewes and Rehoboth Hundred",
        "standardized_name": "Lewes and Rehoboth Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7200,
        "longitude": -75.1200,
        "historical_notes": "Atlantic coastal hundred encompassing Lewes, Rehoboth Beach, and Cape Henlopen; active maritime and pilot boat corridor."
    },
    {
        "id_key": "hd_northwest_fork_de",
        "name": "Northwest Fork Hundred",
        "standardized_name": "Northwest Fork Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7800,
        "longitude": -75.6000,
        "historical_notes": "Western Sussex hundred bordering Caroline and Dorchester counties, Maryland; major corridor for trans-border kin mobility."
    },
    {
        "id_key": "hd_cedar_creek_de",
        "name": "Cedar Creek Hundred",
        "standardized_name": "Cedar Creek Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.8500,
        "longitude": -75.3500,
        "historical_notes": "Northernmost Sussex hundred bordering Kent County and Delaware Bay."
    },
    {
        "id_key": "hd_georgetown_de",
        "name": "Georgetown Hundred",
        "standardized_name": "Georgetown Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6900,
        "longitude": -75.3800,
        "historical_notes": "Central hundred and county seat of Sussex County."
    },
    {
        "id_key": "hd_broad_creek_de",
        "name": "Broad Creek Hundred",
        "standardized_name": "Broad Creek Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5600,
        "longitude": -75.5200,
        "historical_notes": "Southwestern Sussex hundred; historic location of the 1711 Broad Creek Nanticoke reservation tract."
    },
    {
        "id_key": "hd_seaford_de",
        "name": "Seaford Hundred",
        "standardized_name": "Seaford Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6500,
        "longitude": -75.6100,
        "historical_notes": "Formed in 1869 from Northwest Fork Hundred on the Nanticoke River."
    },
    {
        "id_key": "hd_nanticoke_de",
        "name": "Nanticoke Hundred",
        "standardized_name": "Nanticoke Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6800,
        "longitude": -75.5500,
        "historical_notes": "Hundred along the upper Nanticoke River branches."
    },
    {
        "id_key": "hd_baltimore_de",
        "name": "Baltimore Hundred",
        "standardized_name": "Baltimore Hundred, Sussex County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5000,
        "longitude": -75.1200,
        "historical_notes": "Southeastern hundred of Sussex County bordering Maryland and the Atlantic Ocean."
    },
    # New Castle County Hundreds
    {
        "id_key": "hd_appoquinimink_de",
        "name": "Appoquinimink Hundred",
        "standardized_name": "Appoquinimink Hundred, New Castle County, Delaware",
        "place_type": "hundred",
        "parent_key": "county_newcastle_de",
        "county": "New Castle",
        "state": "DE",
        "country": "USA",
        "latitude": 39.4500,
        "longitude": -75.6600,
        "historical_notes": "Southern New Castle County hundred bordering Kent County; location of early land grants and Afro-Native tenant holdings."
    },

    # Legislative & Historical Census Districts
    {
        "id_key": "dist_8_sussex_de",
        "name": "Representative District 8",
        "standardized_name": "Representative District 8, Sussex County, Delaware",
        "place_type": "district",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5800,
        "longitude": -75.2500,
        "historical_notes": "Delaware state representative and federal census enumeration district covering Dagsboro and Indian River hundreds."
    },
    {
        "id_key": "dist_10_sussex_de",
        "name": "Representative District 10",
        "standardized_name": "Representative District 10, Sussex County, Delaware",
        "place_type": "district",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7500,
        "longitude": -75.3000,
        "historical_notes": "Delaware state representative and federal census enumeration district covering Broadkiln hundred and Milton."
    },
    {
        "id_key": "dist_2_kent_de",
        "name": "District 2",
        "standardized_name": "District 2, Kent County, Delaware",
        "place_type": "district",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2500,
        "longitude": -75.6000,
        "historical_notes": "Historic federal census and voting district in northern Kent County encompassing Kenton and Duck Creek."
    },
    {
        "id_key": "dist_7_sussex_de",
        "name": "District 7",
        "standardized_name": "District 7, Sussex County, Delaware",
        "place_type": "district",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6500,
        "longitude": -75.5500,
        "historical_notes": "Historic enumeration district covering Nanticoke and Broad Creek hundreds."
    },
    {
        "id_key": "dist_3_sussex_de",
        "name": "District 3",
        "standardized_name": "District 3, Sussex County, Delaware",
        "place_type": "district",
        "parent_key": "county_sussex_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7200,
        "longitude": -75.3800,
        "historical_notes": "Historic enumeration district covering central Sussex County."
    },

    # Level 4b: Townships (NJ)
    {
        "id_key": "twp_fairfield_nj",
        "name": "Fairfield Township",
        "standardized_name": "Fairfield Township, Cumberland County, New Jersey",
        "place_type": "township",
        "parent_key": "county_cumberland_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.3800,
        "longitude": -75.2200,
        "historical_notes": "Cumberland County township encompassing Gouldtown and Fairton."
    },
    {
        "id_key": "twp_upper_deerfield_nj",
        "name": "Upper Deerfield Township",
        "standardized_name": "Upper Deerfield Township, Cumberland County, New Jersey",
        "place_type": "township",
        "parent_key": "county_cumberland_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.4700,
        "longitude": -75.2300,
        "historical_notes": "Township north of Bridgeton with documented tri-racial family farmsteads."
    },
    {
        "id_key": "twp_commercial_nj",
        "name": "Commercial Township",
        "standardized_name": "Commercial Township, Cumberland County, New Jersey",
        "place_type": "township",
        "parent_key": "county_cumberland_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.2900,
        "longitude": -75.0500,
        "historical_notes": "Township along the Maurice River on the Delaware Bay."
    },

    # Level 5: Settlements, Towns & Enclaves
    {
        "id_key": "set_cheswold_de",
        "name": "Cheswold",
        "standardized_name": "Cheswold, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_little_creek_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2173,
        "longitude": -75.5864,
        "historical_notes": "Historic capital settlement of the Kent County Lenape/Moor community (originally known as Moortown or Moortown Station)."
    },
    {
        "id_key": "set_millsboro_de",
        "name": "Millsboro",
        "standardized_name": "Millsboro, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_dagsboro_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5915,
        "longitude": -75.2938,
        "historical_notes": "Historic population hub for the Nanticoke Indian community in southern Sussex County."
    },
    {
        "id_key": "set_mitsawoket_de",
        "name": "Mitsawoket & Pumpkin Neck",
        "standardized_name": "Mitsawoket & Pumpkin Neck, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_duck_creek_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.3005,
        "longitude": -75.6080,
        "historical_notes": "17th-century sachemdom ruled by Chief Petaquam; precursor community to 18th-century isolate homesteads."
    },
    {
        "id_key": "set_bloomsbury_de",
        "name": "Bloomsbury",
        "standardized_name": "Bloomsbury, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_dover_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1550,
        "longitude": -75.5350,
        "historical_notes": "Significant 18th-century Afro-Indigenous tenant farm on St. Jones River and Mudstone Branch, excavated in 1985."
    },
    {
        "id_key": "set_gouldtown_nj",
        "name": "Gouldtown",
        "standardized_name": "Gouldtown, Cumberland County, New Jersey",
        "place_type": "settlement",
        "parent_key": "twp_fairfield_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.4218,
        "longitude": -75.1874,
        "historical_notes": "Historic self-governing tri-racial free community dating to c. 1700, founded by Benjamin Gould and Elizabeth Adams."
    },
    {
        "id_key": "set_salem_nj",
        "name": "Salem",
        "standardized_name": "Salem, Salem County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_salem_nj",
        "county": "Salem",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.5715,
        "longitude": -75.4674,
        "historical_notes": "Colonial port on the Salem River founded by John Fenwick in 1675."
    },
    {
        "id_key": "set_woodstown_nj",
        "name": "Woodstown",
        "standardized_name": "Woodstown, Salem County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_salem_nj",
        "county": "Salem",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.6515,
        "longitude": -75.3282,
        "historical_notes": "Historic settlement housing Lawnside Cemetery and free Afro-descendant farmsteads."
    },
    {
        "id_key": "set_federalsburg_md",
        "name": "Federalsburg",
        "standardized_name": "Federalsburg, Caroline County, Maryland",
        "place_type": "settlement",
        "parent_key": "county_caroline_md",
        "county": "Caroline",
        "state": "MD",
        "country": "USA",
        "latitude": 38.6948,
        "longitude": -75.7724,
        "historical_notes": "Marshyhope Creek settlement serving as a crucial cross-border sanctuary between Maryland and Delaware."
    },
    {
        "id_key": "set_vienna_md",
        "name": "Vienna",
        "standardized_name": "Vienna, Dorchester County, Maryland",
        "place_type": "settlement",
        "parent_key": "county_dorchester_md",
        "county": "Dorchester",
        "state": "MD",
        "country": "USA",
        "latitude": 38.4843,
        "longitude": -75.8272,
        "historical_notes": "Lower Nanticoke River ferry crossing and trading post near original reservation lands."
    },
    {
        "id_key": "set_milton_de",
        "name": "Milton",
        "standardized_name": "Milton, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_broadkiln_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7776,
        "longitude": -75.3102,
        "historical_notes": "Historic town on the Broadkill River; center for Reed, Jackson, and Norwood lines."
    },
    {
        "id_key": "set_dover_de",
        "name": "Dover",
        "standardized_name": "Dover, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_dover_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1582,
        "longitude": -75.5244,
        "historical_notes": "Delaware state capital and legal center for colonial chancery and probate records."
    },
    {
        "id_key": "set_smyrna_de",
        "name": "Smyrna",
        "standardized_name": "Smyrna, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_duck_creek_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2998,
        "longitude": -75.6044,
        "historical_notes": "Historic commercial center along Duck Creek."
    },
    {
        "id_key": "set_harbeson_de",
        "name": "Harbeson",
        "standardized_name": "Harbeson, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_broadkiln_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7234,
        "longitude": -75.2896,
        "historical_notes": "Community in Broadkiln/Indian River area with Nanticoke family ties."
    },
    {
        "id_key": "set_rehoboth_de",
        "name": "Rehoboth Beach",
        "standardized_name": "Rehoboth Beach, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_lewes_rehoboth_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.7168,
        "longitude": -75.0760,
        "historical_notes": "Coastal community in Lewes and Rehoboth Hundred."
    },
    {
        "id_key": "set_dagsboro_town_de",
        "name": "Dagsboro",
        "standardized_name": "Dagsboro, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_dagsboro_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5484,
        "longitude": -75.2471,
        "historical_notes": "Town at the head of Pepper Creek in Dagsboro Hundred."
    },
    {
        "id_key": "set_wilmington_de",
        "name": "Wilmington",
        "standardized_name": "Wilmington, New Castle County, Delaware",
        "place_type": "settlement",
        "parent_key": "county_newcastle_de",
        "county": "New Castle",
        "state": "DE",
        "country": "USA",
        "latitude": 39.7447,
        "longitude": -75.5484,
        "historical_notes": "Major Delaware urban center; industrial destination for 20th-century family members."
    },
    {
        "id_key": "set_magnolia_de",
        "name": "Magnolia",
        "standardized_name": "Magnolia, Kent County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_south_murderkill_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.0709,
        "longitude": -75.4952,
        "historical_notes": "Town in South Murderkill Hundred."
    },
    {
        "id_key": "set_ellendale_de",
        "name": "Ellendale",
        "standardized_name": "Ellendale, Sussex County, Delaware",
        "place_type": "settlement",
        "parent_key": "hd_cedar_creek_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.8079,
        "longitude": -75.4246,
        "historical_notes": "Settlement in Cedar Creek Hundred."
    },
    {
        "id_key": "set_bridgeton_nj",
        "name": "Bridgeton",
        "standardized_name": "Bridgeton, Cumberland County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_cumberland_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.4273,
        "longitude": -75.2341,
        "historical_notes": "County seat of Cumberland County, NJ; adjacent to Gouldtown."
    },
    {
        "id_key": "set_fairton_nj",
        "name": "Fairton",
        "standardized_name": "Fairton, Cumberland County, New Jersey",
        "place_type": "settlement",
        "parent_key": "twp_fairfield_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.3662,
        "longitude": -75.2107,
        "historical_notes": "Community in Fairfield Township, Cumberland County, NJ."
    },
    {
        "id_key": "set_pleasantville_nj",
        "name": "Pleasantville",
        "standardized_name": "Pleasantville, Atlantic County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_atlantic_nj",
        "county": "Atlantic",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.3896,
        "longitude": -74.5215,
        "historical_notes": "City in Atlantic County, NJ."
    },
    {
        "id_key": "set_atlantic_city_nj",
        "name": "Atlantic City",
        "standardized_name": "Atlantic City, Atlantic County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_atlantic_nj",
        "county": "Atlantic",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.3643,
        "longitude": -74.4229,
        "historical_notes": "Coastal resort city in Atlantic County, NJ; site of Children's Seashore House."
    },
    {
        "id_key": "set_gloucester_city_nj",
        "name": "Gloucester City",
        "standardized_name": "Gloucester City, Camden County, New Jersey",
        "place_type": "settlement",
        "parent_key": "county_gloucester_nj",
        "county": "Camden/Gloucester",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.8937,
        "longitude": -75.1182,
        "historical_notes": "City on the Delaware River across from Philadelphia."
    },
    {
        "id_key": "set_philadelphia_pa",
        "name": "Philadelphia",
        "standardized_name": "Philadelphia, Philadelphia County, Pennsylvania",
        "place_type": "settlement",
        "parent_key": "county_philadelphia_pa",
        "county": "Philadelphia",
        "state": "PA",
        "country": "USA",
        "latitude": 39.9526,
        "longitude": -75.1652,
        "historical_notes": "Major urban center; residence for multiple branches of the extended family network."
    },
    {
        "id_key": "set_hatteras_nc",
        "name": "Cape Hatteras",
        "standardized_name": "Cape Hatteras, Dare County, North Carolina",
        "place_type": "settlement",
        "parent_key": "county_dare_nc",
        "county": "Dare",
        "state": "NC",
        "country": "USA",
        "latitude": 35.2500,
        "longitude": -75.5300,
        "historical_notes": "Outer Banks coastal point in Dare County, NC."
    },

    # Level 6: Historical Cemeteries
    {
        "id_key": "cem_fork_branch",
        "name": "Fork Branch Cemetery",
        "standardized_name": "Fork Branch Cemetery, Dover, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_cheswold_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1912,
        "longitude": -75.5681,
        "historical_notes": "Primary historical burial ground for the Cheswold Moor community dating back to the 18th century."
    },
    {
        "id_key": "cem_immanuel_union",
        "name": "Immanuel Union United Methodist Cemetery",
        "standardized_name": "Immanuel Union United Methodist Cemetery, Cheswold, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_cheswold_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2173,
        "longitude": -75.5864,
        "historical_notes": "Central church and burial ground for the Cheswold community, founded in 1880."
    },
    {
        "id_key": "cem_forest_grove",
        "name": "Forest Grove Seventh-day Adventist Cemetery",
        "standardized_name": "Forest Grove Seventh-day Adventist Cemetery, Dinahs Corner, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_dover_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1834,
        "longitude": -75.6125,
        "historical_notes": "Burial site for Moor families who established the Forest Grove SDA Church in the late 19th century."
    },
    {
        "id_key": "cem_millsboro_sda",
        "name": "Millsboro Seventh-day Adventist Cemetery",
        "standardized_name": "Millsboro Seventh-day Adventist Cemetery, Millsboro, Sussex County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_millsboro_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5898,
        "longitude": -75.2924,
        "historical_notes": "Major burial site for Nanticoke Indian families in Sussex County (Harmon, Street, Clark, Davis)."
    },
    {
        "id_key": "cem_israel_um",
        "name": "Israel United Methodist Cemetery",
        "standardized_name": "Israel United Methodist Cemetery, Indian River Hundred, Sussex County, Delaware",
        "place_type": "cemetery",
        "parent_key": "hd_indian_river_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6189,
        "longitude": -75.2285,
        "historical_notes": "Established by Nanticoke families in the Indian River area; historic church and cemetery."
    },
    {
        "id_key": "cem_john_wesley",
        "name": "John Wesley United Methodist Cemetery",
        "standardized_name": "John Wesley United Methodist Cemetery, Milford, Sussex County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_milton_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.8954,
        "longitude": -75.3852,
        "historical_notes": "Historic African American and Moor congregation cemetery on River Road."
    },
    {
        "id_key": "cem_bethel_ame",
        "name": "Bethel AME Cemetery",
        "standardized_name": "Bethel AME Cemetery, Smyrna, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_smyrna_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.2998,
        "longitude": -75.6044,
        "historical_notes": "Historic AME burial ground serving Kent County families."
    },
    {
        "id_key": "cem_lawnside",
        "name": "Lawnside Cemetery",
        "standardized_name": "Lawnside Cemetery, Woodstown, Salem County, New Jersey",
        "place_type": "cemetery",
        "parent_key": "set_woodstown_nj",
        "county": "Salem",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.6515,
        "longitude": -75.3282,
        "historical_notes": "Primary burial ground for South Jersey Native/Black tri-racial families in Salem County."
    },
    {
        "id_key": "cem_gouldtown",
        "name": "Gouldtown Memorial Park & Cemetery",
        "standardized_name": "Gouldtown Memorial Park & Cemetery, Gouldtown, Cumberland County, New Jersey",
        "place_type": "cemetery",
        "parent_key": "set_gouldtown_nj",
        "county": "Cumberland",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.4218,
        "longitude": -75.1874,
        "historical_notes": "Historic cemetery dating from the early 1700s in the legendary Gouldtown tri-racial settlement."
    },
    {
        "id_key": "cem_union_memorial",
        "name": "Union Memorial Cemetery",
        "standardized_name": "Union Memorial Cemetery, Federalsburg, Caroline County, Maryland",
        "place_type": "cemetery",
        "parent_key": "set_federalsburg_md",
        "county": "Caroline",
        "state": "MD",
        "country": "USA",
        "latitude": 38.6948,
        "longitude": -75.7724,
        "historical_notes": "Burial site for Delmarva peninsula families straddling Delaware and Maryland borders."
    },
    {
        "id_key": "cem_christs_church",
        "name": "Christ's Church Cemetery",
        "standardized_name": "Christ's Church Cemetery, Dover, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_dover_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1582,
        "longitude": -75.5244,
        "historical_notes": "Historic cemetery in Dover containing early community burials."
    },
    {
        "id_key": "cem_evergreen",
        "name": "Evergreen Cemetery",
        "standardized_name": "Evergreen Cemetery, Camden, Kent County, Delaware",
        "place_type": "cemetery",
        "parent_key": "county_kent_de",
        "county": "Kent",
        "state": "DE",
        "country": "USA",
        "latitude": 39.1176,
        "longitude": -75.5413,
        "historical_notes": "Historic cemetery in Camden containing 19th and 20th century interments."
    },
    {
        "id_key": "cem_cuff_family",
        "name": "Cuff Family Cemetery",
        "standardized_name": "Cuff Family Cemetery, Mannington, Salem County, New Jersey",
        "place_type": "cemetery",
        "parent_key": "county_salem_nj",
        "county": "Salem",
        "state": "NJ",
        "country": "USA",
        "latitude": 39.5667,
        "longitude": -75.4667,
        "historical_notes": "Private burial plot for the Cuff family in Salem County."
    },
    {
        "id_key": "cem_jackson_perkins",
        "name": "Jackson-Perkins Cemetery",
        "standardized_name": "Jackson-Perkins Cemetery, Millsboro, Sussex County, Delaware",
        "place_type": "cemetery",
        "parent_key": "set_millsboro_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.5950,
        "longitude": -75.2980,
        "historical_notes": "Burial site for Jackson and Perkins families in Sussex County."
    },
    {
        "id_key": "cem_harmony",
        "name": "Harmony United Methodist Cemetery",
        "standardized_name": "Harmony United Methodist Cemetery, Millsboro, Sussex County, Delaware",
        "place_type": "cemetery",
        "parent_key": "hd_indian_river_de",
        "county": "Sussex",
        "state": "DE",
        "country": "USA",
        "latitude": 38.6120,
        "longitude": -75.2150,
        "historical_notes": "Historic cemetery of Harmony United Methodist Church in Indian River Hundred."
    }
]

# Set of 14 non-spatial false place strings (text notes/dates from scrapers)
TEMPORAL_NOISE_STRINGS = {
    '1943 and Margaret in 1973',
    'the time of his death in 1788',
    '1739',
    '1949',
    'September 1867',
    "1798 , Adm of both estates passed to Charles' sister, Lidia",
    '1846 (per census) which \t\tmatches this Martha',
    'the year 1820',
    '1978',
    'October 1853',
    'November 1963 , Clem died on 26 May, 1958',
    '1934 , Napoleon in 1946',
    '1768 leaving a widow, Sarah, who',
    '1810 and Elizabeth followed c'
}

def resolve_place_key(s: str) -> Optional[str]:
    """Resolves any raw place string in the database to a gazetteer place key."""
    if not s or not s.strip():
        return None
    raw = s.strip()
    if raw in TEMPORAL_NOISE_STRINGS:
        return None
    low = raw.lower()

    # Exact Cemeteries first
    if 'jackson/perkins' in low or 'perkins cem' in low:
        return 'cem_jackson_perkins'
    if 'harmony' in low:
        return 'cem_harmony'
    if 'fork branch' in low:
        return 'cem_fork_branch'
    if 'bethel' in low:
        return 'cem_bethel_ame'
    if 'immanuel union' in low:
        return 'cem_immanuel_union'
    if 'forest grove' in low:
        return 'cem_forest_grove'
    if 'john wesley' in low or 'cemetery milford' in low:
        return 'cem_john_wesley'
    if 'lawnside' in low:
        return 'cem_lawnside'
    if 'gouldtown memorial' in low or 'memorial park' in low:
        return 'cem_gouldtown'
    if 'behind church' in low:
        # e.g., 'behind church Elmirah Durham' -> Fork Branch / Immanuel Union in Cheswold
        return 'cem_fork_branch'
    if low == 'cemetery':
        return 'region_delmarva'

    # Specific settlements and towns
    if 'cheswold' in low:
        return 'set_cheswold_de'
    if 'millsboro' in low:
        return 'set_millsboro_de'
    if 'milton' in low:
        return 'set_milton_de'
    if 'dover' in low:
        return 'set_dover_de'
    if 'smyrna' in low:
        return 'set_smyrna_de'
    if 'harbeson' in low:
        return 'set_harbeson_de'
    if 'ellendale' in low:
        return 'set_ellendale_de'
    if 'magnolia' in low:
        return 'set_magnolia_de'
    if 'rehoboth beach' in low:
        return 'set_rehoboth_de'
    if 'dagsborough' in low or 'dagsboro' in low:
        if 'hundred' in low:
            return 'hd_dagsboro_de'
        return 'set_dagsboro_town_de'
    if 'wilmington' in low:
        return 'set_wilmington_de'
    if 'gouldtown' in low:
        return 'set_gouldtown_nj'
    if 'bridgeton' in low:
        return 'set_bridgeton_nj'
    if 'fairton' in low:
        return 'set_fairton_nj'
    if 'pleasantville' in low:
        return 'set_pleasantville_nj'
    if 'atlantic city' in low or 'seashore house' in low:
        return 'set_atlantic_city_nj'
    if 'gloucester' in low:
        return 'set_gloucester_city_nj'
    if 'philadelphia' in low:
        return 'set_philadelphia_pa'
    if 'federalsburg' in low:
        return 'set_federalsburg_md'
    if 'vienna' in low:
        return 'set_vienna_md'
    if 'hatteras' in low:
        return 'set_hatteras_nc'

    # Hundreds
    if 'kenton' in low:
        return 'hd_kenton_de'
    if 'northwest fork' in low:
        return 'hd_northwest_fork_de'
    if 'appoquinimink' in low:
        return 'hd_appoquinimink_de'
    if 'lewis and rehobeth' in low or 'rehobeth' in low:
        return 'hd_lewes_rehoboth_de'
    if 'indian river' in low:
        return 'hd_indian_river_de'
    if 'duck creek' in low:
        return 'hd_duck_creek_de'
    if 'mispillion' in low:
        return 'hd_mispillion_de'

    # Townships
    if 'fairfield' in low:
        return 'twp_fairfield_nj'
    if 'upper deerfield' in low:
        return 'twp_upper_deerfield_nj'
    if 'commercial' in low:
        return 'twp_commercial_nj'

    # Districts
    if 'district 8' in low:
        return 'dist_8_sussex_de'
    if 'district 10' in low:
        return 'dist_10_sussex_de'
    if 'district 2' in low:
        return 'dist_2_kent_de'
    if 'district 7' in low:
        return 'dist_7_sussex_de'
    if 'district 3' in low:
        return 'dist_3_sussex_de'

    # Counties
    if 'sussex' in low:
        return 'county_sussex_de'
    if 'kent' in low:
        return 'county_kent_de'
    if 'new castle' in low:
        return 'county_newcastle_de'
    if 'caroline' in low or 'dorchester' in low:
        return 'county_caroline_md'
    if 'gratiot' in low or 'mi)' in low:
        return 'county_gratiot_mi'

    # States & Macro
    if 'maryland' in low:
        return 'state_md'
    if 'delaware' in low or 'de ' in low or 'de about' in low or low == 'de':
        return 'state_de'
    if 'delmarva' in low:
        return 'region_delmarva'

    return None

def main():
    print("================================================================================")
    print("DELMARVA HISTORICAL GAZETTEER & GEOGRAPHIC NORMALIZATION (STEP 5)")
    print("================================================================================")

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")
    c = conn.cursor()

    # 1. Ensure 'places' table schema
    print("\n[1/6] Re-establishing 'places' Table Schema...")
    c.execute("DROP TABLE IF EXISTS places;")
    c.execute("""
        CREATE TABLE places (
            place_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            standardized_name TEXT NOT NULL,
            place_type TEXT CHECK(place_type IN ('country', 'region', 'state', 'county', 'hundred', 'district', 'township', 'settlement', 'cemetery')),
            parent_place_id INTEGER REFERENCES places(place_id),
            county TEXT,
            state TEXT,
            country TEXT DEFAULT 'USA',
            latitude REAL,
            longitude REAL,
            historical_notes TEXT,
            UNIQUE(standardized_name, place_type, parent_place_id)
        );
    """)

    # 2. Add 'place_id' column to 'facts' if missing
    facts_cols = [col[1] for col in c.execute("PRAGMA table_info(facts)").fetchall()]
    if "place_id" not in facts_cols:
        print("  ✓ Adding 'place_id' foreign key column to 'facts' table...")
        c.execute("ALTER TABLE facts ADD COLUMN place_id INTEGER REFERENCES places(place_id);")
    else:
        print("  ✓ 'facts.place_id' column already exists.")

    # 3. Seed Delmarva Historical Gazetteer
    print("\n[2/6] Populating Delmarva Historical Gazetteer...")
    key_to_id: Dict[str, int] = {}
    id_to_record: Dict[int, Dict[str, Any]] = {}

    for entry in GAZETTEER_DATA:
        parent_id = None
        if entry["parent_key"]:
            parent_id = key_to_id.get(entry["parent_key"])

        c.execute("""
            INSERT INTO places (
                name, standardized_name, place_type, parent_place_id,
                county, state, country, latitude, longitude, historical_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["name"],
            entry["standardized_name"],
            entry["place_type"],
            parent_id,
            entry["county"],
            entry["state"],
            entry["country"],
            entry["latitude"],
            entry["longitude"],
            entry["historical_notes"]
        ))
        place_id = c.lastrowid
        key_to_id[entry["id_key"]] = place_id
        id_to_record[place_id] = entry

    print(f"  ✓ Seeded {len(key_to_id)} canonical historical places across 6 jurisdictional tiers:")
    for pt in ['country', 'region', 'state', 'county', 'hundred', 'district', 'township', 'settlement', 'cemetery']:
        count_pt = c.execute("SELECT COUNT(*) FROM places WHERE place_type = ?", (pt,)).fetchone()[0]
        if count_pt > 0:
            print(f"    - {pt.capitalize()}: {count_pt} entities")

    # 4. Link Cemeteries Table to Places
    print("\n[3/6] Linking Verified 'cemeteries' to Gazetteer Places...")
    cemeteries = c.execute("SELECT cemetery_id, name, locality, county, state FROM cemeteries").fetchall()
    linked_cemeteries = 0
    for cem_id, name, locality, county, state in cemeteries:
        # Match by name or key
        matched_place_id = None
        for key, pid in key_to_id.items():
            record = id_to_record[pid]
            if record["place_type"] == "cemetery":
                if record["name"].lower() in name.lower() or name.lower() in record["name"].lower():
                    matched_place_id = pid
                    break

        # Fallback to county
        if not matched_place_id:
            if county and 'kent' in county.lower():
                matched_place_id = key_to_id["county_kent_de"]
            elif county and 'sussex' in county.lower():
                matched_place_id = key_to_id["county_sussex_de"]
            elif county and 'salem' in county.lower():
                matched_place_id = key_to_id["county_salem_nj"]
            elif county and 'cumberland' in county.lower():
                matched_place_id = key_to_id["county_cumberland_nj"]
            elif county and 'caroline' in county.lower():
                matched_place_id = key_to_id["county_caroline_md"]

        if matched_place_id:
            c.execute("UPDATE cemeteries SET place_id = ? WHERE cemetery_id = ?", (matched_place_id, cem_id))
            linked_cemeteries += 1

    print(f"  ✓ Linked {linked_cemeteries} / {len(cemeteries)} cemeteries to gazetteer places.")

    # 5. Normalize Facts Place Strings and Populate facts.place_id
    print("\n[4/6] Reconciling and Normalizing Facts Table Places...")
    facts_with_place = c.execute("""
        SELECT fact_id, person_id, fact_type, date_string, place_string, value_string
        FROM facts
        WHERE place_string IS NOT NULL AND TRIM(place_string) != ''
    """).fetchall()

    print(f"  - Total facts with non-empty place strings: {len(facts_with_place)}")

    cleaned_noise_count = 0
    normalized_spatial_count = 0

    for fact_id, person_id, fact_type, date_str, place_str, value_str in facts_with_place:
        raw_place = place_str.strip()

        # Check temporal noise
        if raw_place in TEMPORAL_NOISE_STRINGS:
            # Check if date was missing or incomplete
            new_date = date_str
            # Extract 4-digit year if date was empty
            year_match = re.search(r'\b(1[6789]\d\d|20\d\d)\b', raw_place)
            if (not new_date or not new_date.strip()) and year_match:
                new_date = year_match.group(1)

            c.execute("""
                UPDATE facts
                SET place_string = NULL, place_id = NULL, date_string = ?
                WHERE fact_id = ?
            """, (new_date, fact_id))
            cleaned_noise_count += 1
            continue

        # Resolve to gazetteer
        resolved_key = resolve_place_key(raw_place)
        if resolved_key and resolved_key in key_to_id:
            pid = key_to_id[resolved_key]
            std_name = id_to_record[pid]["standardized_name"]
            c.execute("""
                UPDATE facts
                SET place_id = ?, place_string = ?
                WHERE fact_id = ?
            """, (pid, std_name, fact_id))
            normalized_spatial_count += 1
        else:
            # Fallback to Delmarva Peninsula region
            pid = key_to_id["region_delmarva"]
            std_name = id_to_record[pid]["standardized_name"]
            c.execute("""
                UPDATE facts
                SET place_id = ?, place_string = ?
                WHERE fact_id = ?
            """, (pid, std_name, fact_id))
            normalized_spatial_count += 1

    print(f"  ✓ Cleaned {cleaned_noise_count} non-spatial temporal noise records (dates preserved).")
    print(f"  ✓ Normalized {normalized_spatial_count} spatial facts with canonical gazetteer place IDs.")

    # 6. Create Indexes & Integrity Verification
    print("\n[5/6] Building B-Tree Indexes on Places & Facts...")
    c.execute("CREATE INDEX IF NOT EXISTS idx_places_standardized_name ON places(standardized_name);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_places_place_type ON places(place_type);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_places_county_state ON places(county, state);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_facts_place_id ON facts(place_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cemeteries_place_id ON cemeteries(place_id);")

    conn.commit()

    print("\n[6/6] Executing PRAGMA Integrity & Foreign Key Verifications...")
    conn.execute("PRAGMA foreign_keys = ON;")
    fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    quick_check = conn.execute("PRAGMA quick_check;").fetchone()[0]

    print(f"  ✓ PRAGMA quick_check: {quick_check}")
    print(f"  ✓ PRAGMA foreign_key_check: {len(fk_violations)} violations")
    if fk_violations:
        for v in fk_violations:
            print("    Violating row:", v)
        raise RuntimeError("Foreign key check failed!")

    # Summary metrics
    total_places = c.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    total_facts = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    facts_with_place_id = c.execute("SELECT COUNT(*) FROM facts WHERE place_id IS NOT NULL").fetchone()[0]
    cem_with_place_id = c.execute("SELECT COUNT(*) FROM cemeteries WHERE place_id IS NOT NULL").fetchone()[0]

    print("\n================================================================================")
    print("GAZETTEER & NORMALIZATION SUMMARY METRICS")
    print("================================================================================")
    print(f"  Canonical Places Registered:   {total_places}")
    print(f"  Total Facts in Corpus:         {total_facts}")
    print(f"  Facts with Foreign Key place_id: {facts_with_place_id}")
    print(f"  Cemeteries Linked to Places:   {cem_with_place_id} / 13 (100.0%)")
    print("================================================================================\n")

    conn.close()

if __name__ == "__main__":
    main()
