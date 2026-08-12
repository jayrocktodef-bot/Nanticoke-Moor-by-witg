import React, { useState, useEffect } from 'react';
import { Search, HeartHandshake, Calendar, MapPin, ExternalLink, User } from 'lucide-react';

export default function ObituaryViewer({ onSelectPerson }) {
  const [obituaries, setObituaries] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedObit, setSelectedObit] = useState(null);
  const [expandedObitId, setExpandedObitId] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchObits = (q = '') => {
    setLoading(true);
    fetch('/api/obituaries.json')
      .then(r => r.json())
      .then(data => {
          data.sort((a, b) => (a.deceased_name || '').localeCompare(b.deceased_name || '', undefined, { sensitivity: 'base' }));
          if (q.trim()) {
            const lowerQ = q.toLowerCase();
            const filtered = data.filter(o => 
              o.deceased_name?.toLowerCase().includes(lowerQ) ||
              o.full_text?.toLowerCase().includes(lowerQ) ||
              o.cemetery_location?.toLowerCase().includes(lowerQ)
            );
            setObituaries(filtered);
          } else {
            setObituaries(data);
          }
          setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchObits();
  }, []);

  const handleSearch = (e) => {
    const q = e.target.value;
    setSearch(q);
    fetchObits(q);
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Preserved Obituary Collection</h2>
          <p className="text-xs text-slate-400">
            {obituaries.length} preserved obituaries and memorial records
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search deceased name, kin, cemetery..."
            value={search}
            onChange={handleSearch}
            className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-amber-500/50"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-500">
          <div className="inline-block w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-3" />
          <p className="text-sm">Loading obituaries…</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {obituaries.map(obit => (
            <div
              key={obit.id}
              onClick={() => setSelectedObit(obit)}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-amber-500/40 cursor-pointer transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <HeartHandshake className="w-4 h-4 text-amber-400 shrink-0" />
                    <h3 className="font-bold text-base text-slate-100 group-hover:text-amber-300 transition-colors">
                      {obit.deceased_name}
                    </h3>
                  </div>
                  {obit.age && (
                    <span className="text-xs bg-slate-800 text-amber-400 px-2 py-0.5 rounded font-mono shrink-0">
                      Age {obit.age}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-4 text-xs text-slate-400 mb-3">
                  {(obit.birth_date || obit.death_date) && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-sky-400" />
                      {obit.birth_date ? `${obit.birth_date} – ` : ''}{obit.death_date || 'Date N/A'}
                    </span>
                  )}
                  {obit.cemetery_location && (
                    <span className="flex items-center gap-1 truncate max-w-[200px]">
                      <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                      {obit.cemetery_location}
                    </span>
                  )}
                </div>

                {expandedObitId === obit.id ? (
                  <div className="text-xs text-slate-200 leading-relaxed bg-slate-950/80 p-3 rounded-lg border border-amber-500/30 whitespace-pre-wrap font-serif">
                    {obit.full_text}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed font-serif">
                    {obit.full_text}
                  </p>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedObitId(expandedObitId === obit.id ? null : obit.id);
                  }}
                  className="text-amber-400 hover:text-amber-300 font-mono font-medium underline"
                >
                  {expandedObitId === obit.id ? 'Collapse Text ▲' : 'Expand Text ▼'}
                </button>
                {obit.person_id ? (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectPerson && onSelectPerson(obit.person_id);
                    }}
                    className="text-amber-400 hover:text-amber-300 font-mono font-medium hover:underline flex items-center gap-1"
                  >
                    <User className="w-3 h-3 text-sky-400" />
                    View Individual Profile (#{obit.person_id}) →
                  </button>
                ) : (
                  <span className="text-amber-400 group-hover:underline font-mono">View Full Detail →</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Obituary Detail Drawer Modal */}
      {selectedObit && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedObit(null)}
        >
          <div
            className="max-w-2xl w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl relative max-h-[85vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedObit(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white text-lg font-bold"
            >
              ✕
            </button>

            <div className="flex items-center gap-2 mb-3">
              <HeartHandshake className="w-5 h-5 text-amber-400" />
              <h2 className="text-xl font-bold text-white">{selectedObit.deceased_name}</h2>
            </div>

            <div className="flex flex-wrap gap-4 text-xs text-slate-400 mb-6 bg-slate-800/50 p-3 rounded-lg border border-slate-700/40">
              {selectedObit.age && (
                <span>Age: <strong className="text-slate-200">{selectedObit.age}</strong></span>
              )}
              {selectedObit.birth_date && (
                <span>Born: <strong className="text-slate-200">{selectedObit.birth_date}</strong></span>
              )}
              {selectedObit.death_date && (
                <span>Died: <strong className="text-slate-200">{selectedObit.death_date}</strong></span>
              )}
              {selectedObit.cemetery_location && (
                <span>Burial: <strong className="text-slate-200">{selectedObit.cemetery_location}</strong></span>
              )}
            </div>

            <div className="prose prose-invert max-w-none text-xs text-slate-300 leading-relaxed whitespace-pre-wrap bg-slate-950 p-4 rounded-xl border border-slate-800 font-serif">
              {selectedObit.full_text}
            </div>

            {selectedObit.source_url && (
              <a
                href={selectedObit.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View Preserved Source URL
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
