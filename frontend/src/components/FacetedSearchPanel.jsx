import React, { useState, useEffect, useMemo } from 'react';
import { Search, Filter, Calendar, MapPin, Tag, User, RotateCcw, ChevronRight, Sparkles, BookOpen, Layers } from 'lucide-react';

export default function FacetedSearchPanel({ onSelectPerson }) {
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Search filter states
  const [query, setQuery] = useState('');
  const [minYear, setMinYear] = useState('');
  const [maxYear, setMaxYear] = useState('');
  const [selectedState, setSelectedState] = useState('ALL');
  const [selectedSurname, setSelectedSurname] = useState('ALL');
  const [hasPhotosOnly, setHasPhotosOnly] = useState(false);
  const [hasObituaryOnly, setHasObituaryOnly] = useState(false);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    fetch('/api/graph.json')
      .then(res => res.json())
      .then(data => {
        const nodeList = (data.nodes || []).map(n => ({
          id: n.id,
          name: n.label || 'Unknown',
          surname: n.group || 'Other',
          birth_year: n.birth_date ? parseInt(n.birth_date.match(/\b\d{4}\b/)?.[0] || 0) : null,
          death_year: n.death_date ? parseInt(n.death_date.match(/\b\d{4}\b/)?.[0] || 0) : null,
          birth_place: n.birth_place || '',
          death_place: n.death_place || '',
          aliases: n.aliases || [],
          has_photo: !!n.photo,
          has_obituary: !!n.obituary
        }));
        setPersons(nodeList);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load search data:", err);
        setLoading(false);
      });
  }, []);

  const uniqueSurnames = useMemo(() => {
    const set = new Set(persons.map(p => p.surname).filter(Boolean));
    return ['ALL', ...Array.from(set).sort()];
  }, [persons]);

  const filteredPersons = useMemo(() => {
    return persons.filter(p => {
      // Text query match (Name or Alias)
      if (query.trim()) {
        const q = query.toLowerCase().trim();
        const nameMatch = p.name.toLowerCase().includes(q);
        const aliasMatch = p.aliases.some(a => a.toLowerCase().includes(q));
        if (!nameMatch && !aliasMatch) return false;
      }

      // Surname filter
      if (selectedSurname !== 'ALL' && p.surname !== selectedSurname) {
        return false;
      }

      // Date range filter
      const pYear = p.birth_year || p.death_year;
      if (minYear && pYear && pYear < parseInt(minYear)) return false;
      if (maxYear && pYear && pYear > parseInt(maxYear)) return false;

      // Location state filter
      if (selectedState !== 'ALL') {
        const locStr = `${p.birth_place} ${p.death_place}`.toLowerCase();
        if (selectedState === 'DE' && !locStr.includes('delaware') && !locStr.includes(', de')) return false;
        if (selectedState === 'MD' && !locStr.includes('maryland') && !locStr.includes(', md')) return false;
        if (selectedState === 'VA' && !locStr.includes('virginia') && !locStr.includes(', va')) return false;
        if (selectedState === 'NJ' && !locStr.includes('new jersey') && !locStr.includes(', nj')) return false;
      }

      // Media filters
      if (hasPhotosOnly && !p.has_photo) return false;
      if (hasObituaryOnly && !p.has_obituary) return false;

      return true;
    });
  }, [persons, query, minYear, maxYear, selectedState, selectedSurname, hasPhotosOnly, hasObituaryOnly]);

  const paginatedPersons = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredPersons.slice(start, start + pageSize);
  }, [filteredPersons, currentPage]);

  const totalPages = Math.ceil(filteredPersons.length / pageSize) || 1;

  const resetFilters = () => {
    setQuery('');
    setMinYear('');
    setMaxYear('');
    setSelectedState('ALL');
    setSelectedSurname('ALL');
    setHasPhotosOnly(false);
    setHasObituaryOnly(false);
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[#C68B59]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[#C68B59] font-mono text-xs font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Advanced Discovery Engine</span>
            </div>
            <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
              Faceted Multi-Attribute Search
            </h2>
            <p className="text-xs text-[#A8A096] mt-1 max-w-xl">
              Cross-filter across 4,800+ individuals by surname, historical era, geographic state, media coverage, and alternative spelling aliases.
            </p>
          </div>
          <div className="bg-[#1C1A17] border border-[#332D27] px-4 py-2.5 rounded-xl text-right shrink-0">
            <span className="text-[10px] uppercase font-mono text-[#8C8275] block">Matching Records</span>
            <span className="text-xl font-bold font-mono text-[#D4A373]">{filteredPersons.length}</span>
            <span className="text-xs text-[#8C8275] ml-1">/ {persons.length}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1 bg-[#141210] border border-[#26221E] rounded-2xl p-5 space-y-5 h-fit shadow-xl">
          <div className="flex items-center justify-between border-b border-[#26221E] pb-3">
            <div className="flex items-center gap-2 font-semibold text-xs text-[#F3EBE3]">
              <Filter className="w-4 h-4 text-[#C68B59]" />
              <span>Filter Criteria</span>
            </div>
            <button
              onClick={resetFilters}
              className="text-[11px] text-[#A8A096] hover:text-[#C68B59] flex items-center gap-1 transition-colors"
              title="Reset all filters"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>

          {/* Search Box */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-[#8C8275] uppercase font-semibold block">
              Name or Alias
            </label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8C8275]" />
              <input
                type="text"
                value={query}
                onChange={e => { setQuery(e.target.value); setCurrentPage(1); }}
                placeholder="e.g. Levin Davis, Jackson..."
                className="w-full bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl pl-9 pr-3 py-2 text-xs text-[#F3EBE3] placeholder-[#6E665B] outline-none transition-colors"
              />
            </div>
          </div>

          {/* Surname Select */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-[#8C8275] uppercase font-semibold block">
              Maternal Lineage Surname
            </label>
            <select
              value={selectedSurname}
              onChange={e => { setSelectedSurname(e.target.value); setCurrentPage(1); }}
              className="w-full bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl px-3 py-2 text-xs text-[#F3EBE3] outline-none transition-colors"
            >
              {uniqueSurnames.map(s => (
                <option key={s} value={s}>{s === 'ALL' ? 'All Surnames' : s}</option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-[#8C8275] uppercase font-semibold block">
              Historical Era (Year)
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                value={minYear}
                onChange={e => { setMinYear(e.target.value); setCurrentPage(1); }}
                placeholder="From (1700)"
                className="bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl px-3 py-1.5 text-xs text-[#F3EBE3] placeholder-[#6E665B] outline-none font-mono"
              />
              <input
                type="number"
                value={maxYear}
                onChange={e => { setMaxYear(e.target.value); setCurrentPage(1); }}
                placeholder="To (1950)"
                className="bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl px-3 py-1.5 text-xs text-[#F3EBE3] placeholder-[#6E665B] outline-none font-mono"
              />
            </div>
          </div>

          {/* Location State */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-mono text-[#8C8275] uppercase font-semibold block">
              Delmarva Region State
            </label>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { id: 'ALL', label: 'All Regions' },
                { id: 'DE', label: 'Delaware' },
                { id: 'MD', label: 'Maryland' },
                { id: 'VA', label: 'Virginia' },
                { id: 'NJ', label: 'New Jersey' }
              ].map(st => (
                <button
                  key={st.id}
                  onClick={() => { setSelectedState(st.id); setCurrentPage(1); }}
                  className={`py-1.5 px-2 rounded-lg text-xs font-medium transition-all ${
                    selectedState === st.id
                      ? 'bg-[#C68B59] text-[#121110] font-bold'
                      : 'bg-[#1C1A17] text-[#A8A096] hover:bg-[#26221E]'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>

          {/* Media Badges */}
          <div className="space-y-2 border-t border-[#26221E] pt-3">
            <label className="text-[11px] font-mono text-[#8C8275] uppercase font-semibold block">
              Media Holdings
            </label>
            <label className="flex items-center gap-2 text-xs text-[#E5E1DB] cursor-pointer">
              <input
                type="checkbox"
                checked={hasPhotosOnly}
                onChange={e => { setHasPhotosOnly(e.target.checked); setCurrentPage(1); }}
                className="rounded border-[#332D27] bg-[#1C1A17] text-[#C68B59] focus:ring-0"
              />
              <span>Has Archival Portrait</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-[#E5E1DB] cursor-pointer">
              <input
                type="checkbox"
                checked={hasObituaryOnly}
                onChange={e => { setHasObituaryOnly(e.target.checked); setCurrentPage(1); }}
                className="rounded border-[#332D27] bg-[#1C1A17] text-[#C68B59] focus:ring-0"
              />
              <span>Has Obituary Record</span>
            </label>
          </div>
        </div>

        {/* Search Results Grid */}
        <div className="lg:col-span-3 space-y-4">
          {loading ? (
            <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-12 text-center text-[#A8A096]">
              <div className="animate-spin w-8 h-8 border-2 border-[#C68B59] border-t-transparent rounded-full mx-auto mb-3" />
              <p className="text-xs">Indexing genealogical attributes...</p>
            </div>
          ) : paginatedPersons.length === 0 ? (
            <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-12 text-center text-[#A8A096]">
              <Search className="w-10 h-10 text-[#6E665B] mx-auto mb-3" />
              <h3 className="text-base font-semibold text-[#F3EBE3]">No Matching Individuals Found</h3>
              <p className="text-xs text-[#8C8275] mt-1 max-w-sm mx-auto">
                Try widening your date range or removing location filters to see related clan members.
              </p>
              <button
                onClick={resetFilters}
                className="mt-4 px-4 py-2 bg-[#C68B59] text-[#121110] font-bold text-xs rounded-xl hover:bg-[#D4A373] transition-colors"
              >
                Reset Search Filters
              </button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {paginatedPersons.map(person => (
                  <div
                    key={person.id}
                    onClick={() => onSelectPerson && onSelectPerson(person.id)}
                    className="bg-[#141210] border border-[#26221E] hover:border-[#C68B59]/60 rounded-xl p-4 transition-all hover:scale-[1.01] cursor-pointer group shadow-lg flex items-start justify-between gap-3"
                  >
                    <div className="space-y-1.5 min-w-0">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-[#C68B59] shrink-0" />
                        <h4 className="font-semibold text-sm text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors truncate">
                          {person.name}
                        </h4>
                      </div>
                      
                      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#A8A096] font-mono">
                        {person.birth_year || person.death_year ? (
                          <span className="flex items-center gap-1 text-[#D4A373]">
                            <Calendar className="w-3 h-3 text-[#8C8275]" />
                            {person.birth_year || '?'} – {person.death_year || '?'}
                          </span>
                        ) : null}
                        
                        {(person.birth_place || person.death_place) && (
                          <span className="flex items-center gap-1 text-[#A8A096] truncate max-w-[180px]">
                            <MapPin className="w-3 h-3 text-[#8C8275] shrink-0" />
                            {person.birth_place || person.death_place}
                          </span>
                        )}
                      </div>

                      {person.aliases && person.aliases.length > 0 && (
                        <p className="text-[10px] text-[#8C8275] italic truncate">
                          Also known as: {person.aliases.join(', ')}
                        </p>
                      )}
                    </div>

                    <ChevronRight className="w-4 h-4 text-[#6E665B] group-hover:text-[#C68B59] transition-colors shrink-0 mt-1" />
                  </div>
                ))}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-[#26221E] pt-4">
                  <span className="text-xs text-[#8C8275] font-mono">
                    Page {currentPage} of {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      className="px-3 py-1.5 bg-[#1C1A17] border border-[#332D27] text-xs text-[#E5E1DB] rounded-lg disabled:opacity-40 hover:border-[#C68B59] transition-colors"
                    >
                      Previous
                    </button>
                    <button
                      disabled={currentPage === totalPages}
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      className="px-3 py-1.5 bg-[#1C1A17] border border-[#332D27] text-xs text-[#E5E1DB] rounded-lg disabled:opacity-40 hover:border-[#C68B59] transition-colors"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
