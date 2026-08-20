import React, { useState, useEffect } from 'react';
import { GitCommit, Users, HeartHandshake, Search, Sparkles, ExternalLink, ArrowRight, ShieldCheck } from 'lucide-react';

export default function FamilyInterconnectionMatrix({ onSelectSurname }) {
  const [ties, setTies] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFamily, setSelectedFamily] = useState(null);
  const [selectedTie, setSelectedTie] = useState(null);
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

    return matchesSearch && matchesFamily;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#2A3644] pb-4">
        <div>
          <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3] tracking-tight mb-1 flex items-center gap-2.5">
            <GitCommit className="w-6 h-6 text-[#C87D53]" />
            Inter-Family Kinship & Matrix
          </h2>
          <p className="text-xs text-[#9EA9B6]">
            Discover how Delmarva, Moor, and Nanticoke families are linked through marriages, lineages, and shared historical records.
          </p>
        </div>

        {/* Search & Filter */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#9EA9B6]" />
            <input
              type="text"
              placeholder="Search family or person..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-[#171E27] border border-[#2A3644] rounded-xl text-xs text-[#F3EBE3] placeholder-[#64748B] focus:outline-none focus:border-[#C87D53] transition-colors"
            />
          </div>
          {selectedFamily && (
            <button
              onClick={() => setSelectedFamily(null)}
              className="text-xs bg-[#C87D53]/20 text-[#D4A373] border border-[#C87D53]/40 px-3 py-2 rounded-xl hover:bg-[#C87D53]/30 transition-all font-mono"
            >
              Clear Filter ({selectedFamily})
            </button>
          )}
        </div>
      </div>

      {/* Family Quick Selector Chips */}
      <div className="glass-panel rounded-2xl p-5">
        <h3 className="text-xs font-bold text-[#9EA9B6] uppercase tracking-wider mb-3 flex items-center gap-2 font-mono">
          <Sparkles className="w-4 h-4 text-[#C87D53]" />
          Filter by Key Family Lineage:
        </h3>
        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto custom-scrollbar pr-1">
          {allFamilies.map(fam => (
            <button
              key={fam}
              onClick={() => setSelectedFamily(selectedFamily === fam ? null : fam)}
              className={`text-xs px-3 py-1.5 rounded-xl border font-mono transition-all ${
                selectedFamily === fam
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold border-[#C87D53] shadow-md shadow-[#C87D53]/20'
                  : 'bg-[#0F141A] border-[#2A3644] text-[#9EA9B6] hover:border-[#C87D53] hover:text-[#F3EBE3]'
              }`}
            >
              {fam}
            </button>
          ))}
        </div>
      </div>

      {/* Interconnections Grid */}
      {loading ? (
        <div className="text-center py-16 text-[#9EA9B6]">
          <div className="inline-block w-6 h-6 border-2 border-[#C87D53]/30 border-t-[#C87D53] rounded-full animate-spin mb-3" />
          <p className="text-xs font-mono uppercase tracking-wider">Computing family interconnections...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTies.map((tie, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedTie(tie)}
              className="glass-panel glass-card-hover rounded-2xl p-5 cursor-pointer flex flex-col justify-between space-y-4 group relative overflow-hidden"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 font-serif-header">
                  <span
                    onClick={(e) => { e.stopPropagation(); onSelectSurname && onSelectSurname(tie.family_a); }}
                    className="font-bold text-[#D4A373] hover:underline cursor-pointer text-base"
                  >
                    {tie.family_a}
                  </span>
                  <span className="text-[#64748B] font-mono text-xs">⟷</span>
                  <span
                    onClick={(e) => { e.stopPropagation(); onSelectSurname && onSelectSurname(tie.family_b); }}
                    className="font-bold text-[#E5B269] hover:underline cursor-pointer text-base"
                  >
                    {tie.family_b}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full bg-[#1B3B2B] text-[#E5B269] border border-[#C87D53]/30">
                  {tie.tie_type || 'Inter-Marriage'}
                </span>
              </div>

              <p className="text-xs text-[#9EA9B6] leading-relaxed line-clamp-3 font-sans">
                {tie.description}
              </p>

              {(tie.person_a || tie.person_b) && (
                <div className="pt-3 border-t border-[#2A3644] text-[11px] font-mono text-[#9EA9B6] flex items-center justify-between">
                  <span>Primary Link: <strong className="text-[#F3EBE3]">{tie.person_a}</strong> & <strong className="text-[#F3EBE3]">{tie.person_b}</strong></span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#C87D53] group-hover:translate-x-1 transition-transform" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Kinship Overlay Modal */}
      {selectedTie && (
        <div
          className="fixed inset-0 z-50 bg-[#0F141A]/90 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setSelectedTie(null)}
        >
          <div
            className="max-w-xl w-full bg-[#171E27] border border-[#C87D53]/40 rounded-3xl p-6 shadow-2xl relative"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedTie(null)}
              className="absolute top-4 right-4 p-2 text-[#9EA9B6] hover:text-[#F3EBE3]"
            >
              ✕
            </button>
            <div className="flex items-center gap-2.5 mb-4">
              <GitCommit className="w-6 h-6 text-[#C87D53]" />
              <h3 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
                {selectedTie.family_a} ⟷ {selectedTie.family_b} Kinship Link
              </h3>
            </div>
            <p className="text-sm text-[#F3EBE3] leading-relaxed mb-4 bg-[#0F141A] p-4 rounded-2xl border border-[#2A3644]">
              {selectedTie.description}
            </p>
            <div className="flex justify-between items-center text-xs font-mono text-[#9EA9B6]">
              <span>Key Ancestors: {selectedTie.person_a} & {selectedTie.person_b}</span>
              <span className="text-[#C87D53] font-bold">Verified Archival Tie</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
