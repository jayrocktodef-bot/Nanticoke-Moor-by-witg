import React, { useState, useEffect } from 'react';
import { GitCommit, Users, HeartHandshake, Search, Sparkles, ExternalLink } from 'lucide-react';

export default function FamilyInterconnectionMatrix({ onSelectSurname }) {
  const [ties, setTies] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFamily, setSelectedFamily] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/family-interconnections')
      .then(r => r.json())
      .then(data => {
        setTies(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Unique family surnames participating in inter-family ties
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

  // Filter ties by selected family or search query
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <GitCommit className="w-5 h-5 text-amber-400" />
            Inter-Family Kinship & Marriage Connections
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Discover how Delmarva, Moor, and Nanticoke families are linked through inter-marriages, parent-child lineages, and shared documents.
          </p>
        </div>

        {/* Filter Chips / Search */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search family name..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
            />
          </div>
          {selectedFamily && (
            <button
              onClick={() => setSelectedFamily(null)}
              className="text-xs bg-amber-500/20 text-amber-300 border border-amber-500/40 px-3 py-1.5 rounded-lg hover:bg-amber-500/30 transition-all font-mono"
            >
              Clear Filter ({selectedFamily})
            </button>
          )}
        </div>
      </div>

      {/* Family Quick Selector Chips */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          Filter by Key Family Lineage:
        </h3>
        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
          {allFamilies.map(fam => (
            <button
              key={fam}
              onClick={() => setSelectedFamily(selectedFamily === fam ? null : fam)}
              className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                selectedFamily === fam
                  ? 'bg-amber-500 text-slate-950 font-bold border-amber-400 shadow-md shadow-amber-500/20'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 hover:text-white'
              }`}
            >
              {fam}
            </button>
          ))}
        </div>
      </div>

      {/* Interconnections Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">
          <div className="inline-block w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-3" />
          <p className="text-xs">Computing family interconnections...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTies.map((tie, idx) => (
            <div
              key={idx}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-amber-500/40 transition-all flex flex-col justify-between space-y-3 group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span
                    onClick={() => onSelectSurname && onSelectSurname(tie.family_a)}
                    className="font-bold text-amber-400 hover:underline cursor-pointer text-sm"
                  >
                    {tie.family_a}
                  </span>
                  <span className="text-slate-600 font-mono text-xs">⟷</span>
                  <span
                    onClick={() => onSelectSurname && onSelectSurname(tie.family_b)}
                    className="font-bold text-sky-400 hover:underline cursor-pointer text-sm"
                  >
                    {tie.family_b}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-emerald-500/20">
                  {tie.tie_type}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {tie.description}
              </p>

              {(tie.person_a || tie.person_b) && (
                <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Linked: <strong className="text-slate-200">{tie.person_a}</strong> & <strong className="text-slate-200">{tie.person_b}</strong></span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
