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
  Minimize2
} from 'lucide-react';

// Bounding box for Delmarva Peninsula and South Jersey Custom Historical Map v2
const MAP_BOUNDS = {
  minLat: 37.8,
  maxLat: 40.1,
  minLon: -76.6,
  maxLon: -74.6
};

// Historical Settlement Centers
const HISTORICAL_SETTLEMENTS = [
  {
    id: 'millsboro',
    name: 'Millsboro & Indian River',
    county: 'Sussex Co., DE',
    lat: 38.5915,
    lon: -75.2938,
    type: 'tribal_seat',
    title: 'Nanticoke Tribal Seat & Indian River Hundred',
    description: 'Ancient homeland of the Nanticoke Indian Tribe. Site of the 1711 Maryland reservation, Indian Lands tract (1736-1743), and Nanticoke Indian Association headquarters.',
    surnames: ['Harmon', 'Street', 'Clark', 'Davis', 'Wright', 'Norwood', 'Johnson']
  },
  {
    id: 'cheswold',
    name: 'Cheswold & Fork Branch',
    county: 'Kent Co., DE',
    lat: 39.2173,
    lon: -75.5864,
    type: 'tribal_community',
    title: 'Lenape / Moor Settlement of Kent County',
    description: 'Ancestral isolate settlement centering on Fork Branch and Cheswold. Site of Immanuel Union Church, Forest Grove, and the Cheswold Indian School.',
    surnames: ['Durham', 'Carney', 'Morgan', 'Dean', 'Seeney', 'Moseley', 'Puckham']
  },
  {
    id: 'gouldtown',
    name: 'Gouldtown & Fairfield',
    county: 'Cumberland Co., NJ',
    lat: 39.4218,
    lon: -75.1874,
    type: 'triracial_settlement',
    title: 'Historic Gouldtown Tri-Racial Settlement',
    description: 'Historic sovereign community founded circa 1700 by Benjamin Gould and Elizabeth Adams. Deep marital and economic ties across the Delaware Bay to Cheswold.',
    surnames: ['Gould', 'Pierce', 'Murray', 'Cuff', 'Bowles']
  },
  {
    id: 'salem',
    name: 'Salem & Woodstown',
    county: 'Salem Co., NJ',
    lat: 39.6515,
    lon: -75.3282,
    type: 'settlement',
    title: 'Salem County Afro-Indigenous Enclaves',
    description: 'Historic settlement areas along the Mannington and Salem river basins with prominent Cuff, Pierce, and Murray ancestral land patents and cemeteries.',
    surnames: ['Cuff', 'Pierce', 'Murray', 'Webster']
  },
  {
    id: 'caroline',
    name: 'Caroline & Federalsburg',
    county: 'Caroline Co., MD',
    lat: 38.6948,
    lon: -75.7724,
    type: 'border_settlement',
    title: 'Upper Choptank & Maryland Trans-Border Settlements',
    description: 'Boundary border corridor where free families of color and Native isolates moved between Maryland and Delaware jurisdictions to preserve freedom and kinship.',
    surnames: ['Carty', 'Carter', 'Puckham', 'Hansor', 'Jackson']
  },
  {
    id: 'woodland',
    name: 'Woodland & Seaford',
    county: 'Sussex Co., DE',
    lat: 38.6015,
    lon: -75.6652,
    type: 'river_corridor',
    title: 'Nanticoke River Headwaters Corridor',
    description: 'Historic ferry and river crossing connecting inland Nanticoke settlements across the upper tidal reaches of the Nanticoke River basin.',
    surnames: ['Cannon', 'Ross', 'Harmon', 'Coker']
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

export default function HistoricalMigrationMap({ onSelectPerson }) {
  const [cemeteries, setCemeteries] = useState([]);
  const [loading, setLoading] = useState(true);
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

  // Load Cemeteries from API
  useEffect(() => {
    fetch('/api/cemeteries.json')
      .then(res => res.json())
      .then(data => {
        if (data?.cemeteries) {
          setCemeteries(data.cemeteries);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load cemeteries:', err);
        setLoading(false);
      });
  }, []);

  // Map coordinate projection to SVG viewBox (0,0 to 1000, 800) based on new Delmarva Historical Map v2
  const project = (lat, lon) => {
    if (!lat || !lon) return { x: 0, y: 0 };
    const absLon = Math.abs(lon);
    const x = ((absLon - Math.abs(MAP_BOUNDS.maxLon)) / (Math.abs(MAP_BOUNDS.minLon) - Math.abs(MAP_BOUNDS.maxLon))) * 860 + 70;
    const y = ((MAP_BOUNDS.maxLat - lat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat)) * 680 + 60;
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

              {/* Affiliation / Community Notes */}
              {selectedItem.affiliation && (
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
