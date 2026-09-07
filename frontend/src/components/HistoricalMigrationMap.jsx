import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  MapPin, 
  Compass, 
  Navigation, 
  Layers, 
  Info, 
  Camera, 
  ExternalLink, 
  Crosshair, 
  Search, 
  Sparkles, 
  SlidersHorizontal,
  X,
  ChevronRight,
  BookOpen,
  ArrowRight,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
  Landmark,
  FileText,
  Calendar,
  Shield
} from 'lucide-react';

// Bounding box for Delmarva Peninsula and South Jersey Custom Historical Map v2
const MAP_BOUNDS = {
  minLat: 37.8,
  maxLat: 40.1,
  minLon: -76.6,
  maxLon: -74.6
};

// Comprehensive Historical Settlement Centers
const HISTORICAL_SETTLEMENTS = [
  {
    id: 'mitsawoket',
    name: 'Mitsawoket & Pumpkin Neck',
    county: 'Kent Co., DE',
    lat: 39.3005,
    lon: -75.6080,
    type: 'tribal_sachemdom',
    founded: 'c. 1677',
    cultural_affiliation: 'Mitsawokett Sachemdom & Duck Creek Isolate Community',
    title: 'Ancient Mitsawokett Sachemdom & Pumpkin Neck Settlement',
    description: 'Historical records from 1677–1684 document Mitsawokett as the sovereign territory of Chief Sachem Petaquam in northern Kent County. As European colonial land patents expanded across Duck Creek Neck and Pumpkin Neck, indigenous families adapted by forming tightly knit agrarian tenant homesteads. Archaeological excavations by Heite Consulting revealed continuous contact-era occupation, worked glass scraping tools, and trade bead distribution, confirming the persistence of Native community structures well into the 18th century.',
    historical_landmarks: [
      'Pumpkin Neck Tract (Duck Creek Basin)',
      'Duck Creek Landing',
      'Bishop\'s Corner Assembly Grounds',
      'Duck Creek Friends Meeting (Historic Record Repository)'
    ],
    primary_records: [
      '1677 Petaquam Sachemdom Land Grant (Kent Co. Deed Book A)',
      '1684 Proprietor Survey of Duck Creek Neck',
      'Heite Consulting Archaeological Survey (1985)'
    ],
    archaeological_notes: 'Excavation revealed knapped bottle glass scrapers, indigenous clay pipe fragments, and pit hearths co-located with 18th-century English ceramics.',
    associated_cemeteries: ['Bethel AME Cemetery (Smyrna)'],
    surnames: ['Conselor', 'Durham', 'Sisco', 'Sammons', 'Hansor', 'Dean', 'Puckham']
  },
  {
    id: 'bloomsbury',
    name: 'Bloomsbury & St. Jones Basin',
    county: 'Kent Co., DE',
    lat: 39.1550,
    lon: -75.5350,
    type: 'tenant_homestead',
    founded: 'c. 1730',
    cultural_affiliation: 'St. Jones River Afro-Indigenous Tenant Enclave',
    title: 'Bloomsbury Tenant Farm & Afro-Indigenous Homestead Tract',
    description: 'Situated at the confluence of St. Jones River and Mudstone Branch along Denney\'s Road, Bloomsbury was a multi-generational tenant farm occupied by Afro-Native families including the Conselor and Sisco kin groups. In 1985, state highway archaeology uncovered an extraordinarily rich artifact assemblage: hand-worked glass scraper tools, gunflints, locally made coarse earthenware, and trade items dating from 1730 to 1820. The site provides irreplaceable empirical evidence of continuous cultural preservation among non-reservation Native isolates during the early federal period.',
    historical_landmarks: [
      'Bloomsbury Archaeological Site (7K-C-358)',
      'St. Jones River Navigation Basin',
      'Mudstone Branch Crossing',
      'Historic Denney\'s Road Corridor'
    ],
    primary_records: [
      '1767 Kent County Chancery Court Land Valuation',
      '1792 Allee Family Tenant Leases (Conselor & Sisco entries)',
      'Heite & Heite "Bloomsbury: A Native Community on St. Jones" (1986)'
    ],
    archaeological_notes: 'Discovered worked dark green wine glass tools crafted using traditional lithic pressure flaking techniques, proving traditional tool preservation alongside European goods.',
    associated_cemeteries: ['Christ\'s Church Cemetery', 'Evergreen Cemetery'],
    surnames: ['Conselor', 'Sisco', 'Durham', 'Cutler', 'Allee', 'Morgan']
  },
  {
    id: 'cheswold',
    name: 'Cheswold & Fork Branch',
    county: 'Kent Co., DE',
    lat: 39.2173,
    lon: -75.5864,
    type: 'tribal_community',
    founded: 'c. 1760',
    cultural_affiliation: 'Lenape / Moor Community of Kent County',
    title: 'Cheswold Lenape / Moor Core Settlement & School District',
    description: 'Cheswold (originally known as Moortown or Moortown Station along the Delaware Railroad) developed as the political, social, and spiritual center of the Kent County Lenape community. Families acquired contiguous smallholdings along Fork Branch, establishing independent institutions including Immanuel Union United Methodist Church (1880), Forest Grove SDA Church, and the Cheswold Indian School (District 143c). The community maintained strict endogamous marital patterns across generations, forming a sovereign cultural haven amidst Delaware\'s rigid 19th-century racial binaries.',
    historical_landmarks: [
      'Immanuel Union U.M. Church & Cemetery (est. 1880)',
      'Cheswold Indian School (District 143c)',
      'Forest Grove Seventh-day Adventist Church',
      'Fork Branch Burial Grounds'
    ],
    primary_records: [
      'Delaware Special Indian School Fund Acts (1921–1965)',
      '1880 Immanuel Union Church Incorporation Deed',
      'Joann Sammons "Cheswold Origins & Kinship Networks" (1998)'
    ],
    archaeological_notes: 'Preserves early 19th-century timber frame meeting houses, traditional family burial plots, and ancestral homestead foundations along Fork Branch.',
    associated_cemeteries: ['Fork Branch Cemetery', 'Immanuel Union United Methodist Cemetery', 'Forest Grove Seventh-day Adventist Cemetery'],
    surnames: ['Durham', 'Carney', 'Morgan', 'Dean', 'Seeney', 'Moseley', 'Sammons', 'Coker', 'Ridgeway']
  },
  {
    id: 'millsboro',
    name: 'Millsboro & Indian River',
    county: 'Sussex Co., DE',
    lat: 38.5915,
    lon: -75.2938,
    type: 'tribal_seat',
    founded: 'c. 1711',
    cultural_affiliation: 'Nanticoke Indian Tribe of Delaware',
    title: 'Nanticoke Tribal Seat & Indian River Hundred Homeland',
    description: 'Indian River Hundred has served as the continuous tribal seat of the Nanticoke Indian Tribe for over three centuries. Following colonial encroachment on Maryland\'s Eastern Shore, Nanticoke families consolidated along the Indian River and Hollyville corridors. In 1743, land patents were recorded for tribal leaders, and by 1881 the community chartered the Nanticoke Indian School (District 225c). In 1922, the Nanticoke Indian Association was formally incorporated under Delaware law, continuing annual powwows, cultural education, and tribal governance to the present day.',
    historical_landmarks: [
      'Nanticoke Indian Tribal Center & Cultural Museum',
      'Warwick Indian School (District 225c)',
      'Harmony United Methodist Church',
      'Indian River Landing & Winnesoccum Tract'
    ],
    primary_records: [
      '1711 Maryland Provincial Council Reservation Act',
      '1743 Delaware Indian Lands Patent Records',
      '1922 Nanticoke Indian Association Delaware State Charter',
      'Frank Speck "The Nanticoke and Lenni-Lenape Indians of Delaware" (1915)'
    ],
    archaeological_notes: 'Rich shell midden sites, traditional eel-trap weir locations along Indian River, and mid-19th century timber schoolhouses.',
    associated_cemeteries: ['Israel United Methodist Cemetery', 'Millsboro Seventh-day Adventist Cemetery', 'John Wesley United Methodist Cemetery'],
    surnames: ['Harmon', 'Street', 'Clark', 'Davis', 'Wright', 'Norwood', 'Johnson', 'Sockum']
  },
  {
    id: 'gouldtown',
    name: 'Gouldtown & Fairfield',
    county: 'Cumberland Co., NJ',
    lat: 39.4218,
    lon: -75.1874,
    type: 'triracial_settlement',
    founded: 'c. 1700',
    cultural_affiliation: 'Gouldtown Tri-Racial Free Community',
    title: 'Historic Gouldtown Sovereign Community & Regional Hub',
    description: 'Gouldtown is one of the oldest self-governing tri-racial free communities in the United States, established around 1700 through the union of Elizabeth Adams (granddaughter of Quaker Proprietor John Fenwick) and Benjamin Gould (a free man of color). The community expanded rapidly through intermarriage with neighboring Lenape, Nanticoke, and free Afro-descendant families (Pierce, Cuff, Murray). Gouldtown established its own schools, churches, and agricultural cooperatives, serving as a vital sanctuary for runaway slaves and inter-state kin packet boats traversing the Delaware Bay.',
    historical_landmarks: [
      'Gouldtown Memorial Park & Burial Grounds',
      'Gouldtown Schoolhouse (Historic District)',
      'Fairfield Township Civic Center',
      'Cohansey River Navigation Landing'
    ],
    primary_records: [
      '1700 Fenwick Colony Land Grant to Elizabeth Adams',
      'William Steward "Gouldtown: A Very Remarkable Settlement" (1913)',
      'Cumberland County Quaker Friends Deed Records (1720–1850)'
    ],
    archaeological_notes: '18th-century brick farmsteads, private burial vaults, and early agricultural tool forge remains.',
    associated_cemeteries: ['Gouldtown Memorial Park & Cemetery'],
    surnames: ['Gould', 'Pierce', 'Murray', 'Cuff', 'Bowles', 'Felts', 'Pierpont']
  },
  {
    id: 'salem',
    name: 'Salem & Woodstown',
    county: 'Salem Co., NJ',
    lat: 39.6515,
    lon: -75.3282,
    type: 'settlement',
    founded: 'c. 1720',
    cultural_affiliation: 'Salem Basin Afro-Indigenous Enclaves',
    title: 'Salem County Afro-Indigenous Enclaves & Land Patents',
    description: 'Salem County housed multiple interconnected Afro-Indigenous enclaves along the Mannington Creek, Salem River, and Woodstown corridors. Encouraged by Quaker anti-slavery sentiments and early land sales, free people of color and Native isolates purchased acreage and developed autonomous agrarian communities. Families like the Cuffs established private family burial grounds and served in colored regiments during the Civil War, maintaining active packet boat commerce across the Delaware Bay to Smyrna and Cheswold.',
    historical_landmarks: [
      'Lawnside Cemetery (Woodstown)',
      'Cuff Family Private Burial Plot (Mannington)',
      'Salem Friends Meeting House (1700)',
      'Alloway Creek Navigation Dock'
    ],
    primary_records: [
      '1740 Salem County Friends Manumission & Deed Books',
      'Civil War U.S. Colored Troops (USCT) Muster Rolls (Cuff, Pierce)',
      '1850 Salem County Agricultural Census Records'
    ],
    archaeological_notes: 'Private family cemetery markers, early 19th-century Quaker-built brick tenant homes, and river packet wharf pilings.',
    associated_cemeteries: ['Lawnside Cemetery', 'Cuff Family Cemetery'],
    surnames: ['Cuff', 'Pierce', 'Murray', 'Webster', 'Loatman', 'Dean', 'Skerrett']
  },
  {
    id: 'caroline',
    name: 'Caroline & Federalsburg',
    county: 'Caroline Co., MD',
    lat: 38.6948,
    lon: -75.7724,
    type: 'border_settlement',
    founded: 'c. 1780',
    cultural_affiliation: 'Choptank & Maryland Trans-Border Refuge',
    title: 'Upper Choptank & Maryland Trans-Border Settlement Corridor',
    description: 'Straddling the border of Caroline County, MD, and Sussex County, DE, the Federalsburg corridor along Marshyhope Creek was a crucial refuge zone. Due to harsh Maryland laws restricting free persons of color (such as mandatory registration and prohibition of firearms), families frequently relocated across the state line into Sussex and Kent counties in Delaware. This border mobility fostered resilient kin networks linking the Choptank, Marshyhope, and Nanticoke river watersheds.',
    historical_landmarks: [
      'Union Memorial Cemetery (Federalsburg)',
      'Marshyhope Creek Navigation Canal',
      'Delaware-Maryland State Boundary Stones (Mason-Dixon Line 1765)',
      'Old Bloomery Mill Site'
    ],
    primary_records: [
      'Caroline County Certificates of Freedom (1806–1864)',
      '1790–1860 Maryland Federal Census Free Population Schedules',
      'Dorchester & Caroline Land Commission Records'
    ],
    archaeological_notes: '19th-century timber mill foundations, border crossing trail alignments, and rural churchyard headstones.',
    associated_cemeteries: ['Union Memorial Cemetery'],
    surnames: ['Carty', 'Carter', 'Puckham', 'Handsor', 'Jackson', 'Cook']
  },
  {
    id: 'vienna',
    name: 'Vienna & Lower Nanticoke',
    county: 'Dorchester Co., MD',
    lat: 38.4843,
    lon: -75.8272,
    type: 'river_corridor',
    founded: 'c. 1698',
    cultural_affiliation: 'Nanticoke River Fisheries & Maritime Network',
    title: 'Lower Nanticoke River Trading Post & Maritime Corridor',
    description: 'Vienna on the lower Nanticoke River served as a primary commercial trading post, ferry crossing, and maritime hub for Nanticoke families. Following the 1698 Maryland assembly treaties establishing Nanticoke reservations at Broad Creek and Chicacoan, local native families operated river fisheries, timber logging, and packet boat transport across the Chesapeake Bay. Even after formal reservation lands were dispossessed in 1768, many ancestral families remained in the surrounding river necks.',
    historical_landmarks: [
      'Handsell Historic Site (Chicacoan Reservation Site)',
      'Vienna Nanticoke River Ferry & Waterfront Landing',
      'Chicacoan Creek Native Settlement Tract',
      'Vienna Customs House (Historic District)'
    ],
    primary_records: [
      '1698 Maryland Colonial Assembly Treaty with Nanticoke Nation',
      '1768 Maryland Act for Sale of Nanticoke Indian Lands',
      'Dorchester County Maritime Custom House Register'
    ],
    archaeological_notes: 'Sub-surface posthole patterns of traditional Nanticoke longhouses at Handsell, shell heaps, and colonial trade pipe fragments.',
    associated_cemeteries: ['Union Memorial Cemetery', 'Israel United Methodist Cemetery'],
    surnames: ['Handsor', 'Puckham', 'Jackson', 'Johnson', 'Cook', 'Ross']
  }
];

// Historical Migration Corridors
const MIGRATION_CORRIDORS = [
  {
    id: 'corridor_bay',
    title: 'Delaware Bay Maritime Passage',
    from: 'cheswold',
    to: 'gouldtown',
    description: 'Direct maritime and packet-boat passage across the Delaware Bay connecting Cheswold Lenape/Moor families with Gouldtown and Cumberland County, NJ. Documented extensively in marriages and oral histories.',
    category: 'maritime',
    color: '#38BDF8', // Sky Blue
    surnames: ['Durham', 'Carney', 'Gould', 'Pierce', 'Morgan']
  },
  {
    id: 'corridor_spine',
    title: 'Delmarva Kings Highway Spine',
    from: 'millsboro',
    to: 'cheswold',
    description: 'Major overland travel corridor connecting the Sussex County Nanticoke community at Indian River to the Kent County Lenape community at Cheswold via Milford and Dover.',
    category: 'overland',
    color: '#F59E0B', // Amber
    surnames: ['Harmon', 'Street', 'Clark', 'Davis', 'Durham']
  },
  {
    id: 'corridor_border',
    title: 'Maryland Eastern Shore Trans-Border Passage',
    from: 'caroline',
    to: 'millsboro',
    description: 'Western corridor spanning the Choptank and Nanticoke river headwaters into Sussex County. Historically used by families moving across colonial and state lines.',
    category: 'border',
    color: '#10B981', // Emerald
    surnames: ['Carty', 'Carter', 'Puckham', 'Hansor']
  },
  {
    id: 'corridor_jersey',
    title: 'South Jersey Inland Network',
    from: 'gouldtown',
    to: 'salem',
    description: 'Northern New Jersey corridor linking the tri-racial enclave of Gouldtown to Salem County and Woodstown communities.',
    category: 'inland',
    color: '#A855F7', // Purple
    surnames: ['Cuff', 'Gould', 'Pierce', 'Murray']
  }
];

// All 13 Core Historical Cemeteries of Delmarva and South Jersey
export const DEFAULT_CEMETERIES = [
  { cemetery_id: 1, name: "Fork Branch Cemetery", locality: "Dover", county: "Kent", state: "DE", latitude: 39.1912, longitude: -75.5681, affiliation: "Nanticoke & Moor Community", historical_notes: "Primary historical burial ground for the Cheswold Moor community dating back to the 18th century.", tombstone_count: 95 },
  { cemetery_id: 2, name: "Immanuel Union United Methodist Cemetery", locality: "Cheswold", county: "Kent", state: "DE", latitude: 39.2173, longitude: -75.5864, affiliation: "Moor Community Church", historical_notes: "Central church and burial ground for the Cheswold community, founded in 1880.", tombstone_count: 0 },
  { cemetery_id: 3, name: "Forest Grove Seventh-day Adventist Cemetery", locality: "Dinahs Corner / Dover", county: "Kent", state: "DE", latitude: 39.1834, longitude: -75.6125, affiliation: "Moor Community SDA", historical_notes: "Burial site for Moor families who established the Forest Grove SDA Church in the late 19th century.", tombstone_count: 0 },
  { cemetery_id: 4, name: "Millsboro Seventh-day Adventist Cemetery", locality: "Millsboro", county: "Sussex", state: "DE", latitude: 38.5898, longitude: -75.2924, affiliation: "Nanticoke Community SDA", historical_notes: "Major burial site for Nanticoke Indian families in Sussex County (Harmon, Street, Clark, Davis).", tombstone_count: 1 },
  { cemetery_id: 5, name: "Israel United Methodist Cemetery", locality: "Millsboro / Indian River Hundred", county: "Sussex", state: "DE", latitude: 38.6189, longitude: -75.2285, affiliation: "Nanticoke Indian Community", historical_notes: "Established by Nanticoke families in the Indian River area; historic church and cemetery.", tombstone_count: 5 },
  { cemetery_id: 6, name: "John Wesley United Methodist Cemetery", locality: "Milford / River Road", county: "Sussex", state: "DE", latitude: 38.8954, longitude: -75.3852, affiliation: "African American & Moor", historical_notes: "Historic African American and Moor congregation cemetery.", tombstone_count: 2 },
  { cemetery_id: 7, name: "Bethel AME Cemetery", locality: "Smyrna / Centreville", county: "Kent", state: "DE", latitude: 39.2998, longitude: -75.6044, affiliation: "African Methodist Episcopal", historical_notes: "Historic AME burial ground serving Kent County families.", tombstone_count: 2 },
  { cemetery_id: 8, name: "Lawnside Cemetery", locality: "Woodstown", county: "Salem", state: "NJ", latitude: 39.6515, longitude: -75.3282, affiliation: "Historic Black Community", historical_notes: "Primary burial ground for South Jersey Native/Black tri-racial families in Salem County.", tombstone_count: 2 },
  { cemetery_id: 9, name: "Gouldtown Memorial Park & Cemetery", locality: "Gouldtown / Fairfield", county: "Cumberland", state: "NJ", latitude: 39.4218, longitude: -75.1874, affiliation: "Gouldtown Tri-Racial Settlement", historical_notes: "Dating from the early 1700s, legendary settlement founded by Benjamin Gould and Elizabeth Adams.", tombstone_count: 1 },
  { cemetery_id: 10, name: "Union Memorial Cemetery", locality: "Federalsburg", county: "Caroline", state: "MD", latitude: 38.6948, longitude: -75.7724, affiliation: "Eastern Shore Community", historical_notes: "Burial site for Delmarva peninsula families straddling Delaware and Maryland borders.", tombstone_count: 0 },
  { cemetery_id: 11, name: "Christ's Church Cemetery", locality: "Dover", county: "Kent", state: "DE", latitude: 39.1582, longitude: -75.5244, affiliation: "Episcopal / Historic", historical_notes: "Historic cemetery in Dover containing early community burials.", tombstone_count: 1 },
  { cemetery_id: 12, name: "Evergreen Cemetery", locality: "Camden", county: "Kent", state: "DE", latitude: 39.1176, longitude: -75.5413, affiliation: "Public / Historic", historical_notes: "Historic cemetery serving Kent County families.", tombstone_count: 1 },
  { cemetery_id: 13, name: "Cuff Family Cemetery", locality: "Salem County", county: "Salem", state: "NJ", latitude: 39.5667, longitude: -75.4667, affiliation: "Cuff Family Private Cemetery", historical_notes: "Private burial plot for the Cuff family of Salem County, NJ.", tombstone_count: 1 }
];

export default function HistoricalMigrationMap({ onSelectPerson }) {
  const [cemeteries, setCemeteries] = useState(DEFAULT_CEMETERIES);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null); // cemetery or settlement
  const [activeCorridorFilter, setActiveCorridorFilter] = useState('all'); // 'all', 'maritime', 'overland', 'border', 'cemeteries_only'
  const [searchQuery, setSearchQuery] = useState('');
  const [lightboxTombstone, setLightboxTombstone] = useState(null);
  
  // Interactive Map Zoom & Pan State
  const [zoomLevel, setZoomLevel] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isFullscreenMap, setIsFullscreenMap] = useState(false);

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.35, 4));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.35, 0.8));
  const handleResetZoom = () => { setZoomLevel(1); setPan({ x: 0, y: 0 }); };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      setZoomLevel(prev => Math.min(prev + 0.15, 4));
    } else {
      setZoomLevel(prev => Math.max(prev - 0.15, 0.8));
    }
  };

  // Load Cemeteries from API (updates with rich tombstones if available)
  useEffect(() => {
    fetch('/api/cemeteries.json')
      .then(res => res.json())
      .then(data => {
        if (data?.cemeteries && data.cemeteries.length > 0) {
          setCemeteries(data.cemeteries);
        }
      })
      .catch(err => {
        console.warn('Using default bundled cemeteries:', err);
      });
  }, []);

  // Map coordinate projection to SVG viewBox (0,0 to 1000, 800) based on calibrated Delmarva Map v2
  const project = (lat, lon) => {
    if (!lat || !lon) return { x: 0, y: 0 };
    const absLon = Math.abs(lon);
    
    // Longitude maps -76.6 to -74.6 => image x: 80 to 940 px
    const imgX = 80 + ((76.6 - absLon) / (76.6 - 74.6)) * (940 - 80);
    
    // Latitude maps 39.85 to 37.90 => image y: 120 to 780 px
    const imgY = 120 + ((39.85 - lat) / (39.85 - 37.90)) * (780 - 120);
    
    // Scale 1200 x 896 image coords to 1000 x 800 SVG viewBox
    const x = (imgX / 1200.0) * 1000.0;
    const y = (imgY / 896.0) * 800.0;
    return { x, y };
  };

  // Node lookup for drawing paths
  const settlementCoords = useMemo(() => {
    const map = {};
    HISTORICAL_SETTLEMENTS.forEach(s => {
      map[s.id] = project(s.lat, s.lon);
    });
    return map;
  }, []);

  // Filtered cemeteries based on search
  const filteredCemeteries = useMemo(() => {
    if (!searchQuery.trim()) return cemeteries;
    const q = searchQuery.toLowerCase();
    return cemeteries.filter(c => 
      c.name.toLowerCase().includes(q) ||
      c.locality.toLowerCase().includes(q) ||
      c.county.toLowerCase().includes(q) ||
      c.affiliation.toLowerCase().includes(q)
    );
  }, [cemeteries, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header & Controls Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#2A3644] pb-5">
        <div>
          <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3] tracking-tight flex items-center gap-2.5">
            <Compass className="w-6 h-6 text-[#C87D53]" />
            Historical Migration Corridors & Cemetery Atlas
          </h2>
          <p className="text-xs text-[#9EA9B6] mt-1 max-w-2xl leading-relaxed">
            Cartographic model of the Delmarva Peninsula & South Jersey tri-racial isolate communities.
            Track 18th–20th century maritime crossings, overland family corridors, and GPS-verified cemetery plots.
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: 'all', label: 'All Corridors & Sites' },
            { id: 'maritime', label: 'Delaware Bay Crossings' },
            { id: 'overland', label: 'Kings Highway Spine' },
            { id: 'border', label: 'MD Trans-Border' },
            { id: 'cemeteries_only', label: 'Cemeteries Only' }
          ].map(btn => (
            <button
              key={btn.id}
              onClick={() => setActiveCorridorFilter(btn.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all ${
                activeCorridorFilter === btn.id
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md shadow-[#C87D53]/20'
                  : 'bg-[#171E27] text-[#9EA9B6] hover:bg-[#202936] hover:text-[#F3EBE3] border border-[#2A3644]'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Interactive Map (8 cols) + Detail Drawer (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* MAP CANVAS CONTAINER */}
        <div className="lg:col-span-8 bg-[#131921] border border-[#2A3644] rounded-3xl p-4 sm:p-6 shadow-2xl relative overflow-hidden flex flex-col">
          {/* Top Map Overlay Banner */}
          <div className="flex items-center justify-between gap-4 mb-4 z-10">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-widest text-[#C87D53] bg-[#C87D53]/10 border border-[#C87D53]/30 px-2 py-0.5 rounded-md flex items-center gap-1">
                <Navigation className="w-3 h-3" /> Delmarva Cartographic Model
              </span>
              <span className="text-[10px] font-mono text-[#9EA9B6]">
                13 Historic Cemeteries • 6 Core Settlements
              </span>
            </div>

            {/* Quick Search */}
            <div className="relative w-48 sm:w-64">
              <Search className="w-3.5 h-3.5 text-[#9EA9B6] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search cemeteries..."
                className="w-full bg-[#0F141A] border border-[#2A3644] rounded-xl pl-8 pr-3 py-1 text-xs text-[#F3EBE3] placeholder-[#606E7F] focus:outline-none focus:border-[#C87D53]"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9EA9B6] hover:text-[#F3EBE3]"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* SVG MAP & CONTROLS CONTAINER */}
          <div 
            className="relative w-full aspect-[4/3] bg-[#0C1015] rounded-2xl border border-[#1F2733] overflow-hidden shadow-inner flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            {/* Interactive Zoom Toolbar Overlay */}
            <div className="absolute top-3 right-3 z-30 flex items-center gap-1.5 bg-[#141210]/90 backdrop-blur-md border border-[#332D27] p-1.5 rounded-xl shadow-xl">
              <button
                onClick={handleZoomIn}
                className="p-1.5 bg-[#1C1A17] hover:bg-[#C68B59] text-[#E5E1DB] hover:text-[#121110] rounded-lg transition-colors"
                title="Zoom In (+)"
                aria-label="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-1.5 bg-[#1C1A17] hover:bg-[#C68B59] text-[#E5E1DB] hover:text-[#121110] rounded-lg transition-colors"
                title="Zoom Out (-)"
                aria-label="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleResetZoom}
                className="p-1.5 bg-[#1C1A17] hover:bg-[#C68B59] text-[#E5E1DB] hover:text-[#121110] rounded-lg transition-colors font-mono text-[10px] font-bold px-2"
                title="Reset Zoom & Pan"
              >
                {Math.round(zoomLevel * 100)}%
              </button>
              <div className="w-[1px] h-4 bg-[#332D27] mx-0.5" />
              <button
                onClick={() => setIsFullscreenMap(true)}
                className="p-1.5 bg-[#1C1A17] hover:bg-[#C68B59] text-[#D4A373] hover:text-[#121110] rounded-lg transition-colors"
                title="Expand Map Full-Screen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>

            <svg 
              viewBox="0 0 1000 800" 
              className="w-full h-full select-none transition-transform duration-75 ease-out"
              style={{ 
                transform: `scale(${zoomLevel}) translate(${pan.x / zoomLevel}px, ${pan.y / zoomLevel}px)`,
                transformOrigin: 'center center',
                filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.5))' 
              }}
            >
              <defs>
                {/* Glowing effects for corridors */}
                <filter id="glow-gold" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-blue" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>

                {/* Animated dash markers */}
                <linearGradient id="gradient-bay" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#818CF8" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* NEW DELMARVA HISTORICAL MAP V2 BACKDROP */}
              <image
                href="/assets/delmarva_historical_map_v2.jpg"
                x="0"
                y="0"
                width="1000"
                height="800"
                preserveAspectRatio="none"
                opacity="0.9"
                style={{
                  filter: 'contrast(1.1) sepia(0.15) brightness(0.95)'
                }}
              />

              {/* MIGRATION CORRIDORS (Arcs with animated stroke) */}
              {activeCorridorFilter !== 'cemeteries_only' && (
                <g className="migration-corridors">
                  {MIGRATION_CORRIDORS.map(corridor => {
                    if (activeCorridorFilter !== 'all' && corridor.category !== activeCorridorFilter) {
                      return null;
                    }
                    const fromPt = settlementCoords[corridor.from];
                    const toPt = settlementCoords[corridor.to];
                    if (!fromPt || !toPt) return null;

                    // Compute curved control point
                    const dx = toPt.x - fromPt.x;
                    const dy = toPt.y - fromPt.y;
                    const cx = (fromPt.x + toPt.x) / 2 - dy * 0.25;
                    const cy = (fromPt.y + toPt.y) / 2 + dx * 0.25;

                    const isSelected = selectedItem?.id === corridor.id;

                    return (
                      <g 
                        key={corridor.id}
                        className="cursor-pointer group"
                        onClick={() => setSelectedItem(corridor)}
                      >
                        {/* Glow halo */}
                        <path
                          d={`M ${fromPt.x},${fromPt.y} Q ${cx},${cy} ${toPt.x},${toPt.y}`}
                          fill="none"
                          stroke={corridor.color}
                          strokeWidth={isSelected ? "8" : "5"}
                          strokeOpacity={isSelected ? "0.6" : "0.25"}
                        />
                        {/* Main dashed flow line */}
                        <path
                          d={`M ${fromPt.x},${fromPt.y} Q ${cx},${cy} ${toPt.x},${toPt.y}`}
                          fill="none"
                          stroke={corridor.color}
                          strokeWidth="2.5"
                          strokeDasharray="6 4"
                          strokeLinecap="round"
                        />
                        {/* Corridor label */}
                        <text
                          x={cx}
                          y={cy - 6}
                          fill={corridor.color}
                          fontSize="10"
                          fontFamily="monospace"
                          fontWeight="bold"
                          textAnchor="middle"
                          className="drop-shadow-md"
                        >
                          {corridor.title}
                        </text>
                      </g>
                    );
                  })}
                </g>
              )}

              {/* HISTORICAL SETTLEMENT CENTERS */}
              {activeCorridorFilter !== 'cemeteries_only' && (
                <g className="settlement-nodes">
                  {HISTORICAL_SETTLEMENTS.map(settlement => {
                    const pt = settlementCoords[settlement.id];
                    if (!pt) return null;
                    const isSelected = selectedItem?.id === settlement.id;

                    return (
                      <g
                        key={settlement.id}
                        transform={`translate(${pt.x}, ${pt.y})`}
                        className="cursor-pointer group"
                        onClick={() => setSelectedItem(settlement)}
                      >
                        {/* Pulse Ring */}
                        <circle
                          r={isSelected ? "22" : "16"}
                          fill="#C87D53"
                          fillOpacity={isSelected ? "0.3" : "0.12"}
                          stroke="#C87D53"
                          strokeWidth="1.5"
                          strokeDasharray="3 3"
                          className="transition-all"
                        />
                        {/* Inner Node */}
                        <circle
                          r={isSelected ? "8" : "6"}
                          fill="#C87D53"
                          stroke="#0F141A"
                          strokeWidth="2"
                        />
                        {/* Settlement Name */}
                        <text
                          x="0"
                          y={pt.y > 600 ? -22 : 24}
                          textAnchor="middle"
                          fill="#F3EBE3"
                          fontSize="11"
                          fontWeight="bold"
                          fontFamily="sans-serif"
                          className="drop-shadow-md"
                        >
                          {settlement.name}
                        </text>
                        <text
                          x="0"
                          y={pt.y > 600 ? -12 : 35}
                          textAnchor="middle"
                          fill="#9EA9B6"
                          fontSize="9"
                          fontFamily="monospace"
                        >
                          {settlement.county}
                        </text>
                      </g>
                    );
                  })}
                </g>
              )}

              {/* PROMINENT HIGH-VISIBILITY CEMETERY PINS (Plotted by exact GPS Coordinates) */}
              <g className="cemetery-markers">
                {filteredCemeteries.map(cem => {
                  const lat = cem.latitude || cem.lat;
                  const lon = cem.longitude || cem.lon;
                  if (!lat || !lon) return null;
                  const pt = project(lat, lon);
                  const isSelected = selectedItem?.cemetery_id === cem.cemetery_id;

                  return (
                    <g
                      key={cem.cemetery_id}
                      transform={`translate(${pt.x}, ${pt.y})`}
                      className="cursor-pointer group"
                      onClick={(e) => { e.stopPropagation(); setSelectedItem(cem); }}
                    >
                      {/* Outer Glowing Halo */}
                      <circle
                        r={isSelected ? "18" : "12"}
                        fill="#F59E0B"
                        fillOpacity={isSelected ? "0.45" : "0.22"}
                        stroke="#F59E0B"
                        strokeWidth="1.5"
                        className={isSelected ? "animate-ping" : ""}
                      />

                      {/* Prominent Golden Tombstone Badge Marker */}
                      <circle
                        r={isSelected ? "9" : "7"}
                        fill={isSelected ? "#F59E0B" : "#D4A373"}
                        stroke="#141210"
                        strokeWidth="2.5"
                        className="transition-transform group-hover:scale-125 shadow-lg"
                      />

                      {/* Center Cross / Grave Symbol Dot */}
                      <circle
                        r="2.5"
                        fill="#141210"
                      />

                      {/* Always-Visible High-Contrast Cemetery Name Pill Badge */}
                      <g transform="translate(0, -14)">
                        <rect
                          x={-cem.name.length * 3.4 - 8}
                          y="-15"
                          width={cem.name.length * 6.8 + 16}
                          height="19"
                          rx="5"
                          fill="#141210"
                          fillOpacity="0.92"
                          stroke={isSelected ? "#F59E0B" : "#C68B59"}
                          strokeWidth={isSelected ? "2" : "1.2"}
                          className="shadow-md"
                        />
                        <text
                          x="0"
                          y="-3"
                          textAnchor="middle"
                          fill={isSelected ? "#F3EBE3" : "#E5E1DB"}
                          fontSize="9.5"
                          fontFamily="sans-serif"
                          fontWeight="bold"
                        >
                          🪦 {cem.name}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* Map Legend */}
            <div className="absolute bottom-3 left-3 bg-[#0F141A]/90 backdrop-blur-md border border-[#2A3644] rounded-xl p-3 text-[10px] font-mono text-[#9EA9B6] space-y-1.5 pointer-events-none shadow-lg">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#C87D53]" />
                <span className="text-[#F3EBE3]">Core Settlement Centers</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E2E8F0]" />
                <span className="text-[#F3EBE3]">Preserved Cemeteries ({filteredCemeteries.length})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 border-t-2 border-dashed border-[#F59E0B]" />
                <span className="text-[#F3EBE3]">Migration Flow Corridors</span>
              </div>
            </div>
          </div>
        </div>

        {/* DETAIL INSPECTION DRAWER */}
        <div className="lg:col-span-4 bg-[#171E27] border border-[#2A3644] rounded-3xl p-6 shadow-2xl space-y-5">
          {selectedItem ? (
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-start justify-between gap-3 border-b border-[#2A3644] pb-4">
                <div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#C87D53] bg-[#C87D53]/10 px-2 py-0.5 rounded border border-[#C87D53]/25 inline-block mb-1.5">
                    {selectedItem.cemetery_id ? 'Historical Cemetery Plot' : (selectedItem.category ? 'Migration Corridor' : 'Settlement Center')}
                  </span>
                  <h3 className="text-xl font-bold font-serif-header text-[#F3EBE3]">
                    {selectedItem.name || selectedItem.title}
                  </h3>
                  <p className="text-xs text-[#9EA9B6] font-mono">
                    {selectedItem.locality ? `${selectedItem.locality}, ${selectedItem.county}, ${selectedItem.state}` : (selectedItem.county || selectedItem.category)}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="p-1.5 rounded-lg bg-[#0F141A] border border-[#2A3644] text-[#9EA9B6] hover:text-[#F3EBE3]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* GPS Coordinates Badge (if Cemetery) */}
              {selectedItem.latitude && (
                <div className="flex items-center justify-between bg-[#0F141A] p-3 rounded-2xl border border-[#2A3644] text-xs font-mono">
                  <div className="flex items-center gap-2 text-[#9EA9B6]">
                    <Crosshair className="w-4 h-4 text-[#C87D53]" />
                    <span>GPS Coordinates:</span>
                  </div>
                  <span className="text-[#F3EBE3] font-bold">
                    {selectedItem.latitude.toFixed(4)}° N, {Math.abs(selectedItem.longitude).toFixed(4)}° W
                  </span>
                </div>
              )}

              {/* Founding Era & Cultural Affiliation */}
              {selectedItem.founded && (
                <div className="flex items-center justify-between bg-[#0F141A] p-2.5 rounded-xl border border-[#2A3644] text-xs font-mono">
                  <span className="text-[#9EA9B6] flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-[#C87D53]" /> Founding Era:
                  </span>
                  <span className="text-[#F3EBE3] font-bold">{selectedItem.founded}</span>
                </div>
              )}

              {selectedItem.cultural_affiliation && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold block mb-1">
                    Cultural & Tribal Affiliation
                  </label>
                  <p className="text-xs text-[#D4A373] bg-[#C87D53]/10 border border-[#C87D53]/25 p-2.5 rounded-xl font-mono">
                    {selectedItem.cultural_affiliation}
                  </p>
                </div>
              )}

              {/* Affiliation / Community Notes */}
              {selectedItem.affiliation && !selectedItem.cultural_affiliation && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold block mb-1">
                    Community Affiliation
                  </label>
                  <p className="text-xs text-[#D4A373] bg-[#C87D53]/10 border border-[#C87D53]/20 p-2.5 rounded-xl font-mono">
                    {selectedItem.affiliation}
                  </p>
                </div>
              )}

              {/* Historical Significance Notes */}
              <div>
                <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold block mb-1">
                  Historical Background & Evidence
                </label>
                <p className="text-xs text-[#E5E1DB] leading-relaxed bg-[#0F141A] p-3.5 rounded-xl border border-[#2A3644]">
                  {selectedItem.historical_notes || selectedItem.description}
                </p>
              </div>

              {/* Historical Landmarks */}
              {selectedItem.historical_landmarks && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold mb-1.5 flex items-center gap-1">
                    <Landmark className="w-3.5 h-3.5 text-[#C87D53]" /> Key Historical Landmarks & Institutions
                  </label>
                  <ul className="space-y-1 text-xs text-[#E5E1DB]">
                    {selectedItem.historical_landmarks.map((lm, idx) => (
                      <li key={idx} className="bg-[#0F141A] p-2 rounded-lg border border-[#2A3644] flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#C87D53] shrink-0" />
                        <span>{lm}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Primary Records & Citations */}
              {selectedItem.primary_records && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold mb-1.5 flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-[#38BDF8]" /> Archival Evidence & Primary Documents
                  </label>
                  <ul className="space-y-1 text-xs text-[#9EA9B6] font-mono">
                    {selectedItem.primary_records.map((rec, idx) => (
                      <li key={idx} className="bg-[#0F141A] p-2 rounded-lg border border-[#2A3644] flex items-start gap-2">
                        <span className="text-[#38BDF8] font-bold shrink-0">📜</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Archaeological Notes */}
              {selectedItem.archaeological_notes && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold mb-1 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-[#F59E0B]" /> Archaeological Artifact Findings
                  </label>
                  <p className="text-xs text-[#D4A373] bg-[#0F141A] p-2.5 rounded-xl border border-[#F59E0B]/30 leading-relaxed font-sans">
                    {selectedItem.archaeological_notes}
                  </p>
                </div>
              )}

              {/* Associated Cemeteries */}
              {selectedItem.associated_cemeteries && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold block mb-1">
                    Linked Historical Burial Grounds
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedItem.associated_cemeteries.map((ac, idx) => (
                      <span key={idx} className="text-xs font-mono text-[#F3EBE3] bg-[#0F141A] border border-[#C87D53]/40 px-2.5 py-1 rounded-lg flex items-center gap-1">
                        🪦 {ac}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Associated Lineages */}
              {selectedItem.surnames && (
                <div>
                  <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold block mb-1.5">
                    Associated Family Lineages
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedItem.surnames.map(s => (
                      <span key={s} className="text-xs font-mono text-[#F3EBE3] bg-[#0F141A] border border-[#2A3644] px-2.5 py-1 rounded-lg">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Tombstone Photo Previews */}
              {selectedItem.tombstones && selectedItem.tombstones.length > 0 && (
                <div className="pt-2 border-t border-[#2A3644]">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-mono uppercase text-[#8C8275] font-bold flex items-center gap-1.5">
                      <Camera className="w-3.5 h-3.5 text-[#C87D53]" />
                      Preserved Tombstone Photos ({selectedItem.tombstone_count || selectedItem.tombstones.length})
                    </label>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {selectedItem.tombstones.map((t, idx) => (
                      <div 
                        key={idx}
                        onClick={() => setLightboxTombstone(t)}
                        className="group relative aspect-square bg-[#0F141A] rounded-xl border border-[#2A3644] overflow-hidden cursor-pointer hover:border-[#C87D53] transition-all"
                      >
                        <img
                          src={t.local_image_path.startsWith('/') ? t.local_image_path : '/' + t.local_image_path}
                          alt={t.subject_names || 'Tombstone'}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                        />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-1.5">
                          <span className="text-[9px] font-mono text-white truncate">
                            {t.subject_names || 'Tombstone'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-10 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-[#C87D53]/10 border border-[#C87D53]/30 flex items-center justify-center mx-auto text-[#C87D53]">
                <MapPin className="w-6 h-6" />
              </div>
              <h4 className="text-base font-bold font-serif-header text-[#F3EBE3]">
                Explore Historical Delmarva
              </h4>
              <p className="text-xs text-[#9EA9B6] leading-relaxed max-w-xs mx-auto">
                Click on any settlement center, cemetery marker, or migration flow line to inspect verified archival background, GPS coordinates, and preserved tombstones.
              </p>
              <div className="pt-4 border-t border-[#2A3644] text-left space-y-2 text-xs font-mono text-[#9EA9B6]">
                <p className="text-[#C87D53] font-bold">Quick Cemetery Access:</p>
                <div className="space-y-1 max-h-56 overflow-y-auto custom-scrollbar pr-1">
                  {cemeteries.slice(0, 7).map(c => (
                    <button
                      key={c.cemetery_id}
                      onClick={() => setSelectedItem(c)}
                      className="w-full text-left p-2 rounded-lg bg-[#0F141A] hover:bg-[#202936] hover:text-[#F3EBE3] border border-[#2A3644] flex items-center justify-between transition-all"
                    >
                      <span className="truncate">{c.name}</span>
                      <span className="text-[10px] text-[#C87D53] font-bold shrink-0">{c.tombstone_count} 🪦</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Lightbox for Tombstone Image Preview */}
      {lightboxTombstone && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setLightboxTombstone(null)}
        >
          <div
            className="max-w-3xl w-full bg-[#171E27] border border-[#C87D53]/40 rounded-3xl p-6 shadow-2xl relative"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setLightboxTombstone(null)}
              className="absolute top-4 right-4 p-2 bg-[#0F141A] border border-[#2A3644] hover:border-[#C87D53] text-[#9EA9B6] hover:text-[#F3EBE3] rounded-full"
            >
              <X className="w-4 h-4" />
            </button>
            <img
              src={lightboxTombstone.local_image_path.startsWith('/') ? lightboxTombstone.local_image_path : '/' + lightboxTombstone.local_image_path}
              alt={lightboxTombstone.subject_names}
              className="w-full max-h-[70vh] object-contain rounded-2xl mb-4 bg-black"
            />
            <h4 className="text-lg font-bold font-serif-header text-[#F3EBE3]">
              {lightboxTombstone.subject_names || 'Preserved Tombstone Artifact'}
            </h4>
            {lightboxTombstone.title_or_caption && (
              <p className="text-xs text-[#9EA9B6] mt-1 leading-relaxed">
                {lightboxTombstone.title_or_caption}
              </p>
            )}
          </div>
        </div>
      )}
      {/* Full-Screen Interactive Expandable Map Modal */}
      {isFullscreenMap && (
        <div
          className="fixed inset-0 z-50 bg-[#0F0E0D]/95 backdrop-blur-xl flex flex-col p-4 sm:p-6 animate-fade-in"
          onClick={() => setIsFullscreenMap(false)}
        >
          {/* Modal Toolbar */}
          <div className="flex items-center justify-between border-b border-[#26221E] pb-3 mb-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <Compass className="w-6 h-6 text-[#C68B59]" />
              <div>
                <h3 className="text-lg font-bold text-[#F3EBE3] font-serif-header">
                  Delmarva & Mid-Atlantic Historical Cartographic Model
                </h3>
                <p className="text-xs text-[#8C8275] font-mono">
                  1800s Historical Regional Map • 13 Preserved Cemeteries • Interactive Pinch/Scroll & Pan
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleZoomIn}
                className="p-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#F3EBE3] rounded-xl font-bold transition-all text-xs"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#F3EBE3] rounded-xl font-bold transition-all text-xs"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleResetZoom}
                className="px-3 py-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#D4A373] rounded-xl font-mono text-xs font-bold transition-all"
              >
                Reset ({Math.round(zoomLevel * 100)}%)
              </button>
              <button
                onClick={() => setIsFullscreenMap(false)}
                className="p-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#F3EBE3] rounded-xl transition-all ml-2"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Expanded Canvas Body */}
          <div 
            className="flex-1 relative rounded-2xl overflow-hidden border border-[#26221E] bg-[#0C1015] cursor-grab active:cursor-grabbing flex items-center justify-center"
            onClick={e => e.stopPropagation()}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            <svg 
              viewBox="0 0 1000 800" 
              className="w-full h-full select-none transition-transform duration-75 ease-out"
              style={{ 
                transform: `scale(${zoomLevel}) translate(${pan.x / zoomLevel}px, ${pan.y / zoomLevel}px)`,
                transformOrigin: 'center center'
              }}
            >
              {/* Historical Map Backdrop */}
              <image
                href="/assets/delmarva_historical_map_v2.jpg"
                x="0"
                y="0"
                width="1000"
                height="800"
                preserveAspectRatio="none"
                opacity="0.95"
                style={{
                  filter: 'contrast(1.1) sepia(0.1) brightness(0.95)'
                }}
              />

              {/* MIGRATION CORRIDORS */}
              {MIGRATION_CORRIDORS.map(corridor => {
                const fromPt = settlementCoords[corridor.from];
                const toPt = settlementCoords[corridor.to];
                if (!fromPt || !toPt) return null;
                const dx = toPt.x - fromPt.x;
                const dy = toPt.y - fromPt.y;
                const cx = (fromPt.x + toPt.x) / 2 - dy * 0.25;
                const cy = (fromPt.y + toPt.y) / 2 + dx * 0.25;

                return (
                  <g key={`fs-${corridor.id}`}>
                    <path
                      d={`M ${fromPt.x},${fromPt.y} Q ${cx},${cy} ${toPt.x},${toPt.y}`}
                      fill="none"
                      stroke={corridor.color}
                      strokeWidth="6"
                      strokeOpacity="0.35"
                    />
                    <path
                      d={`M ${fromPt.x},${fromPt.y} Q ${cx},${cy} ${toPt.x},${toPt.y}`}
                      fill="none"
                      stroke={corridor.color}
                      strokeWidth="2.5"
                      strokeDasharray="6 4"
                    />
                  </g>
                );
              })}

              {/* CEMETERY PINS IN FULL-SCREEN MODAL */}
              <g className="cemetery-markers-fs">
                {filteredCemeteries.map(cem => {
                  const lat = cem.latitude || cem.lat;
                  const lon = cem.longitude || cem.lon;
                  if (!lat || !lon) return null;
                  const pt = project(lat, lon);
                  const isSelected = selectedItem?.cemetery_id === cem.cemetery_id;

                  return (
                    <g
                      key={`fs-${cem.cemetery_id}`}
                      transform={`translate(${pt.x}, ${pt.y})`}
                      className="cursor-pointer group"
                      onClick={() => { setSelectedItem(cem); setIsFullscreenMap(false); }}
                    >
                      <circle
                        r={isSelected ? "20" : "14"}
                        fill="#F59E0B"
                        fillOpacity={isSelected ? "0.5" : "0.25"}
                        stroke="#F59E0B"
                        strokeWidth="1.5"
                      />
                      <circle
                        r={isSelected ? "10" : "8"}
                        fill={isSelected ? "#F59E0B" : "#D4A373"}
                        stroke="#141210"
                        strokeWidth="2.5"
                      />
                      <g transform="translate(0, -16)">
                        <rect
                          x={-cem.name.length * 3.6 - 10}
                          y="-16"
                          width={cem.name.length * 7.2 + 20}
                          height="22"
                          rx="6"
                          fill="#141210"
                          fillOpacity="0.95"
                          stroke={isSelected ? "#F59E0B" : "#C68B59"}
                          strokeWidth="1.5"
                        />
                        <text
                          x="0"
                          y="-3"
                          textAnchor="middle"
                          fill="#F3EBE3"
                          fontSize="10.5"
                          fontFamily="sans-serif"
                          fontWeight="bold"
                        >
                          🪦 {cem.name}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
