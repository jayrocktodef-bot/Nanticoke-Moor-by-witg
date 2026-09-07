import React, { useState, useEffect } from 'react';
import { GitCommit, Users, HeartHandshake, Search, Sparkles, ExternalLink, ArrowRight, ShieldCheck, MapPin, Maximize2, X, Compass, Layers } from 'lucide-react';

const CLAN_MAP_HOTSPOTS = [
  { id: 'millsboro', name: 'Millsboro & Indian River, DE', x: 80, y: 55, families: ['Davis', 'Harmon', 'Sockum', 'Street', 'Wright'], region: 'Delaware Peninsula', desc: 'Nanticoke Tribal seat & core maternal homesteads' },
  { id: 'cheswold', name: 'Cheswold & Fork Branch, DE', x: 77, y: 46, families: ['Durham', 'Ridgeway', 'Carney', 'Sammons', 'Coker'], region: 'Central Delaware', desc: 'Moor community settlement & cemetery grounds' },
  { id: 'gouldtown', name: 'Gouldtown & Bridgeton, NJ', x: 86, y: 38, families: ['Gould', 'Pierce', 'Cuff', 'Murray'], region: 'Southern New Jersey', desc: 'Colonial free person of color community hub' },
  { id: 'vienna', name: 'Vienna & Nanticoke River, MD', x: 74, y: 58, families: ['Jackson', 'Handsor', 'Johnson', 'Cook'], region: 'Eastern Shore Maryland', desc: 'Nanticoke river fishery & timber trade corridors' },
  { id: 'oak_orchard', name: 'Oak Orchard & Rehoboth, DE', x: 82, y: 56, families: ['Cook', 'Clark', 'Conselor'], region: 'Sussex Coast', desc: 'Saltmarsh farming & coastal kin networks' },
  { id: 'salem', name: 'Salem & Cumberland, NJ', x: 84, y: 34, families: ['Loatman', 'Dean', 'Skerrett'], region: 'South Jersey', desc: 'Inter-state migration & Quaker record ties' }
];

export default function FamilyInterconnectionMatrix({ onSelectSurname }) {
  const [ties, setTies] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFamily, setSelectedFamily] = useState(null);
  const [selectedHotspot, setSelectedHotspot] = useState(null);
  const [selectedTie, setSelectedTie] = useState(null);
  const [isMapModalOpen, setIsMapModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/family-interconnections.json')
      .then(r => r.json())
      .then(data => {
        setTies(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const INVALID_FAMILY_CHIPS = new Set([
    'their', 'Wilmington', 'Agness', 'Angelina', 'Ann', 'Apole', 'Archer', 
    'Esther', 'Hannah', 'Bridgeton', 'Delaware', 'Church', 'Friend', 'Tribe'
  ]);

  const familySet = new Set();
  ties.forEach(t => {
    [t.family_a, t.family_b].forEach(fam => {
      if (
        fam && 
        fam.length >= 3 && 
        !/\d/.test(fam) && 
        !/[()\/]/.test(fam) && 
        !INVALID_FAMILY_CHIPS.has(fam)
      ) {
        familySet.add(fam);
      }
    });
  });
  const allFamilies = Array.from(familySet).sort((a, b) => a.localeCompare(b));

  const filteredTies = ties.filter(t => {
    const matchesSearch = !searchQuery || 
      t.family_a.toLowerCase().includes(searchQuery.toLowerCase()) || 
      t.family_b.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.person_a && t.person_a.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (t.person_b && t.person_b.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFamily = !selectedFamily || 
      t.family_a.toLowerCase() === selectedFamily.toLowerCase() || 
      t.family_b.toLowerCase() === selectedFamily.toLowerCase();

    const matchesHotspot = !selectedHotspot || 
      selectedHotspot.families.some(f => 
        f.toLowerCase() === t.family_a.toLowerCase() || f.toLowerCase() === t.family_b.toLowerCase()
      );

    return matchesSearch && matchesFamily && matchesHotspot;
  });

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#26221E] pb-4">
        <div>
          <div className="flex items-center gap-2 text-[#C68B59] font-mono text-xs font-semibold uppercase tracking-wider mb-1">
            <Compass className="w-3.5 h-3.5" />
            <span>Delmarva & Mid-Atlantic Clan Geography</span>
          </div>
          <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3] tracking-tight flex items-center gap-2.5">
            <GitCommit className="w-6 h-6 text-[#C68B59]" />
            Inter-Family Kinship & Spatial Matrix
          </h2>
          <p className="text-xs text-[#A8A096]">
            Discover how Nanticoke, Moor, and Delmarva families are linked geographically across Pennsylvania, Maryland, Delaware, Virginia, and New Jersey.
          </p>
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8C8275]" />
            <input
              type="text"
              placeholder="Search family or person..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-[#1C1A17] border border-[#332D27] rounded-xl text-xs text-[#F3EBE3] placeholder-[#6E665B] focus:outline-none focus:border-[#C68B59] transition-colors"
            />
          </div>
          {(selectedFamily || selectedHotspot) && (
            <button
              onClick={() => { setSelectedFamily(null); setSelectedHotspot(null); }}
              className="text-xs bg-[#C68B59]/20 text-[#D4A373] border border-[#C68B59]/40 px-3 py-2 rounded-xl hover:bg-[#C68B59]/30 transition-all font-mono"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* HISTORICAL VINTAGE CLAN MAP HERO CANVAS */}
      <div className="bg-[#141210] border border-[#26221E] rounded-3xl p-4 shadow-2xl relative overflow-hidden group">
        <div className="flex items-center justify-between px-3 py-2 border-b border-[#26221E] mb-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#F3EBE3] font-mono">
            <Layers className="w-4 h-4 text-[#C68B59]" />
            <span>1800s Mid-Atlantic Historical Atlas (PA, NJ, DE, MD, VA)</span>
          </div>
          <button
            onClick={() => setIsMapModalOpen(true)}
            className="text-xs bg-[#1C1A17] hover:bg-[#26221E] border border-[#332D27] text-[#D4A373] px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 font-mono"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Full-Screen Map View</span>
          </button>
        </div>

        {/* Map Container */}
        <div className="relative w-full h-[360px] sm:h-[450px] rounded-2xl overflow-hidden border border-[#26221E] bg-[#0F0E0D]">
          {/* Stylized Historical Map Backdrop */}
          <img
            src="/assets/delmarva_historical_map_v2.jpg"
            alt="1800s Historical Map of Pennsylvania, New Jersey, Maryland, Delaware, and Virginia"
            className="w-full h-full object-cover opacity-80 mix-blend-luminosity filter contrast-125 sepia-[0.35] brightness-90 group-hover:scale-105 transition-transform duration-700"
          />

          {/* Dark Vignette and Parchment Overlay Gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#0F0E0D] via-transparent to-[#0F0E0D]/60 pointer-events-none" />

          {/* Interactive Clan Hotspot Pins */}
          {CLAN_MAP_HOTSPOTS.map(spot => {
            const isSelected = selectedHotspot?.id === spot.id;
            return (
              <div
                key={spot.id}
                style={{ left: `${spot.x}%`, top: `${spot.y}%` }}
                onClick={() => setSelectedHotspot(isSelected ? null : spot)}
                className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer z-20 group/pin"
              >
                {/* Pulsing ring */}
                <div className={`w-6 h-6 rounded-full border-2 transition-all animate-ping absolute -inset-0 ${
                  isSelected ? 'border-[#C68B59] bg-[#C68B59]/30' : 'border-[#D4A373]/60 bg-[#D4A373]/10'
                }`} />

                {/* Main pin marker */}
                <div className={`relative w-7 h-7 rounded-full flex items-center justify-center border shadow-xl transition-all ${
                  isSelected
                    ? 'bg-[#C68B59] text-[#121110] border-white scale-125'
                    : 'bg-[#141210]/90 text-[#D4A373] border-[#C68B59] hover:scale-110 hover:bg-[#C68B59] hover:text-[#121110]'
                }`}>
                  <MapPin className="w-4 h-4" />
                </div>

                {/* Floating tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-[#141210]/95 backdrop-blur-md border border-[#C68B59]/50 rounded-xl p-2.5 shadow-2xl pointer-events-none opacity-0 group-hover/pin:opacity-100 transition-opacity z-30 space-y-1">
                  <span className="text-[10px] font-mono text-[#D4A373] uppercase block font-bold">{spot.region}</span>
                  <h4 className="font-bold text-xs text-[#F3EBE3]">{spot.name}</h4>
                  <p className="text-[10px] text-[#A8A096] leading-tight">{spot.desc}</p>
                  <div className="text-[9px] font-mono text-[#C68B59] pt-1 border-t border-[#26221E]">
                    Clans: {spot.families.join(', ')}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Hotspot Bar */}
        {selectedHotspot && (
          <div className="mt-3 bg-[#1C1A17] border border-[#C68B59]/50 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in font-mono text-xs">
            <div className="flex items-center gap-2 text-[#F3EBE3]">
              <MapPin className="w-4 h-4 text-[#C68B59]" />
              <span>Active Map Region: <strong className="text-[#D4A373]">{selectedHotspot.name}</strong></span>
              <span className="text-[10px] text-[#8C8275]">({selectedHotspot.region})</span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-[#8C8275]">Associated Clans:</span>
              {selectedHotspot.families.map(f => (
                <span key={f} className="px-2 py-0.5 rounded bg-[#C68B59]/20 border border-[#C68B59]/40 text-[#D4A373] font-bold text-[10px]">
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Family Quick Selector Chips */}
      <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-5 shadow-xl">
        <h3 className="text-xs font-bold text-[#8C8275] uppercase tracking-wider mb-3 flex items-center gap-2 font-mono">
          <Sparkles className="w-4 h-4 text-[#C68B59]" />
          Filter Matrix by Clan Lineage:
        </h3>
        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto custom-scrollbar pr-1">
          {allFamilies.map(fam => (
            <button
              key={fam}
              onClick={() => setSelectedFamily(selectedFamily === fam ? null : fam)}
              className={`text-xs px-3 py-1.5 rounded-xl border font-mono transition-all ${
                selectedFamily === fam
                  ? 'bg-[#C68B59] text-[#121110] font-bold border-[#C68B59] shadow-md shadow-[#C68B59]/20'
                  : 'bg-[#1C1A17] border-[#332D27] text-[#A8A096] hover:border-[#C68B59] hover:text-[#F3EBE3]'
              }`}
            >
              {fam}
            </button>
          ))}
        </div>
      </div>

      {/* Interconnections Grid */}
      {loading ? (
        <div className="text-center py-16 text-[#A8A096]">
          <div className="inline-block w-6 h-6 border-2 border-[#C68B59]/30 border-t-[#C68B59] rounded-full animate-spin mb-3" />
          <p className="text-xs font-mono uppercase tracking-wider">Computing clan interconnections & historical links...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTies.map((tie, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedTie(tie)}
              className="bg-[#141210] border border-[#26221E] hover:border-[#C68B59]/60 rounded-2xl p-5 cursor-pointer flex flex-col justify-between space-y-4 group relative overflow-hidden shadow-lg transition-all hover:scale-[1.01]"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 font-serif-header">
                  <span
                    onClick={(e) => { e.stopPropagation(); onSelectSurname && onSelectSurname(tie.family_a); }}
                    className="font-bold text-[#D4A373] hover:underline cursor-pointer text-base"
                  >
                    {tie.family_a}
                  </span>
                  <span className="text-[#8C8275] font-mono text-xs">⟷</span>
                  <span
                    onClick={(e) => { e.stopPropagation(); onSelectSurname && onSelectSurname(tie.family_b); }}
                    className="font-bold text-[#E5E1DB] hover:underline cursor-pointer text-base"
                  >
                    {tie.family_b}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full bg-[#1C1A17] text-[#C68B59] border border-[#C68B59]/30">
                  {tie.tie_type || 'Inter-Marriage'}
                </span>
              </div>

              <p className="text-xs text-[#A8A096] leading-relaxed line-clamp-3 font-sans">
                {tie.description}
              </p>

              {(tie.person_a || tie.person_b) && (
                <div className="pt-3 border-t border-[#26221E] text-[11px] font-mono text-[#8C8275] flex items-center justify-between">
                  <span>Primary Link: <strong className="text-[#F3EBE3]">{tie.person_a}</strong> & <strong className="text-[#F3EBE3]">{tie.person_b}</strong></span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#C68B59] group-hover:translate-x-1 transition-transform" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Kinship Overlay Modal */}
      {selectedTie && (
        <div
          className="fixed inset-0 z-50 bg-[#0F0E0D]/90 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setSelectedTie(null)}
        >
          <div
            className="max-w-xl w-full bg-[#141210] border border-[#C68B59]/40 rounded-3xl p-6 shadow-2xl relative"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedTie(null)}
              className="absolute top-4 right-4 p-2 text-[#8C8275] hover:text-[#F3EBE3]"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2.5 mb-4">
              <GitCommit className="w-6 h-6 text-[#C68B59]" />
              <h3 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
                {selectedTie.family_a} ⟷ {selectedTie.family_b} Kinship Link
              </h3>
            </div>
            <p className="text-sm text-[#F3EBE3] leading-relaxed mb-4 bg-[#1C1A17] p-4 rounded-2xl border border-[#26221E] font-serif">
              {selectedTie.description}
            </p>
            <div className="flex justify-between items-center text-xs font-mono text-[#8C8275]">
              <span>Key Ancestors: {selectedTie.person_a} & {selectedTie.person_b}</span>
              <span className="text-[#C68B59] font-bold">Verified Archival Tie</span>
            </div>
          </div>
        </div>
      )}

      {/* Full-Screen Antique Map Modal */}
      {isMapModalOpen && (
        <div
          className="fixed inset-0 z-50 bg-[#0F0E0D]/95 backdrop-blur-xl flex flex-col p-4 sm:p-6 animate-fade-in"
          onClick={() => setIsMapModalOpen(false)}
        >
          <div className="flex items-center justify-between border-b border-[#26221E] pb-3 mb-4">
            <div className="flex items-center gap-3">
              <Compass className="w-6 h-6 text-[#C68B59]" />
              <div>
                <h3 className="text-lg font-bold text-[#F3EBE3] font-serif-header">
                  1800s Mid-Atlantic Historical Map & Clan Geography Atlas
                </h3>
                <p className="text-xs text-[#8C8275] font-mono">
                  High-Resolution Regional Map: Pennsylvania, New Jersey, Maryland, Delaware & Virginia
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsMapModalOpen(false)}
              className="p-2 bg-[#1C1A17] border border-[#332D27] text-[#F3EBE3] hover:border-[#C68B59] rounded-xl transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 relative rounded-2xl overflow-hidden border border-[#26221E] bg-[#141210]" onClick={e => e.stopPropagation()}>
            <img
              src="/assets/historical_clan_map.jpg"
              alt="1800s High Resolution Historical Map"
              className="w-full h-full object-contain filter contrast-125 sepia-[0.25]"
            />
          </div>
        </div>
      )}
    </div>
  );
}
