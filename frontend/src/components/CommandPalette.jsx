import React, { useState, useEffect } from 'react';
import { Search, Users, Image as ImageIcon, HeartHandshake, FileText, X, ArrowRight, CornerDownLeft } from 'lucide-react';

export default function CommandPalette({ isOpen, onClose, onSelectPerson, onSelectSurname, onOpenRecord }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          setQuery('');
          setResults([]);
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (query.trim().length > 1) {
      setLoading(true);
      fetch('/api/surnames.json')
        .then(res => res.json())
        .then(data => {
          const lowerQ = query.toLowerCase();
          const filtered = data.map((s, idx) => ({
            person_id: idx + 1,
            name: `${s.surname} Family Lineage (${s.individual_count} persons)`,
            notes: `Associated variants: ${s.variants || s.surname}`
          })).filter(s => s.name.toLowerCase().includes(lowerQ) || s.notes.toLowerCase().includes(lowerQ));
          setResults(filtered);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    } else {
      setResults([]);
    }
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-start justify-center pt-20 p-4 animate-fade-in" onClick={onClose}>
      <div 
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Bar Header */}
        <div className="p-4 border-b border-slate-800 flex items-center gap-3 bg-slate-900/90">
          <Search className="w-5 h-5 text-amber-400 shrink-0" />
          <input
            type="text"
            autoFocus
            placeholder="Search individuals, surnames, Bible entries, census records... (Esc to close)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 focus:outline-none text-base font-medium"
          />
          {query && (
            <button onClick={() => setQuery('')} className="p-1 text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          )}
          <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">ESC</span>
        </div>

        {/* Search Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {loading && (
            <div className="p-6 text-center text-xs text-slate-400">
              <div className="inline-block w-5 h-5 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-2" />
              <p>Searching preserved database...</p>
            </div>
          )}

          {!loading && query && results.length === 0 && (
            <div className="p-8 text-center text-slate-400 text-xs">
              No individual records found matching <span className="text-amber-300 font-semibold">"{query}"</span>
            </div>
          )}

          {!loading && !query && (
            <div className="p-6 text-xs text-slate-400 space-y-3">
              <p className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">Quick Suggestions</p>
              <div className="flex flex-wrap gap-2">
                {['Harmon', 'Jackson', 'Durham', 'Puckham', 'Clark', 'Wright', 'Sockum', 'Norwood', 'Counselor'].map(sn => (
                  <button
                    key={sn}
                    onClick={() => {
                      onSelectSurname(sn);
                      onClose();
                    }}
                    className="bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700 px-3 py-1.5 rounded-lg font-mono flex items-center gap-1.5 transition-all"
                  >
                    <Users className="w-3.5 h-3.5" />
                    <span>{sn} Lineage</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {!loading && results.map(p => (
            <div
              key={p.person_id}
              onClick={() => {
                onSelectPerson(p.person_id);
                onClose();
              }}
              className="p-3 bg-slate-900/60 hover:bg-slate-800 border border-transparent hover:border-amber-500/30 rounded-xl cursor-pointer flex items-center justify-between transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg group-hover:bg-amber-500/20">
                  <Users className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-100 group-hover:text-amber-300 transition-colors">
                    {p.name}
                  </h4>
                  {p.notes && (
                    <p className="text-xs text-slate-400 truncate max-w-lg mt-0.5">{p.notes}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 text-xs text-slate-400 group-hover:text-amber-400 font-mono">
                <span>View Profile</span>
                <CornerDownLeft className="w-3.5 h-3.5" />
              </div>
            </div>
          ))}
        </div>

        {/* Command Palette Footer */}
        <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Tip: Press <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">Ctrl+K</kbd> anywhere to trigger</span>
          <span>Delmarva Genealogical Preservation</span>
        </div>
      </div>
    </div>
  );
}
