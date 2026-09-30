import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, LayoutGrid, List, Sparkles, Database, FileText, 
  Image as ImageIcon, GitFork, ArrowRight, Compass, ShieldCheck,
  BookOpen, ChevronDown, ChevronUp, MapPin, Landmark
} from 'lucide-react';
import SurnameCard from '../components/SurnameCard';
import { fetchCachedJson } from '../utils/apiCache';

export default function LineagesPage() {
  const [surnames, setSurnames] = useState([]);
  const [stats, setStats] = useState({ pages: 357, media_assets: 241, persons: 3783, relationships: 1576 });
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('grid');
  const [selectedLetter, setSelectedLetter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedPathway, setExpandedPathway] = useState(null);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const pageSize = 24;

  const navigate = useNavigate();

  useEffect(() => {
    fetchCachedJson('/api/stats.json')
      .then(data => {
        if (data && data.persons) setStats(data);
      })
      .catch(console.error);

    fetchCachedJson('/api/surnames.json')
      .then(data => {
        const list = Array.isArray(data) ? data : data?.surnames || [];
        setSurnames(list);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load surnames:", err);
        setLoading(false);
      });
  }, []);

  const alphabet = ['ALL', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')];
  const safeSurnames = Array.isArray(surnames) ? surnames : [];
  const filteredSurnames = safeSurnames
    .filter(s => {
      if (selectedLetter === 'ALL') return true;
      return s.surname && s.surname.toUpperCase().startsWith(selectedLetter);
    })
    .sort((a, b) => a.surname.localeCompare(b.surname, undefined, { sensitivity: 'base' }));

  const totalPages = Math.ceil(filteredSurnames.length / pageSize) || 1;
  const paginatedSurnames = filteredSurnames.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleSelectSurname = (surname) => {
    navigate(`/lineages/${encodeURIComponent(surname)}`);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* HERO ARCHIVAL BANNER & STATS */}
      <section className="bg-gradient-to-b from-[#1C1A17] to-[#141210] border border-[#2D2722] rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#C68B59]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C68B59]/15 border border-[#C68B59]/30 text-xs font-mono text-[#D4A373] mb-3">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Genealogical Proof Standard (GPS) Confirmed Archive</span>
          </div>

          <h2 className="font-serif-header text-2xl sm:text-4xl font-bold text-[#F3EBE3] tracking-tight leading-tight">
            Preserved Afro-Indigenous Lineages of Delmarva & South Jersey
          </h2>
          <p className="text-sm sm:text-base text-[#A8A096] mt-3 leading-relaxed">
            A comprehensive digital preservation catalog and primary evidence dossier tracing the remnant
            communities of the Nanticoke, Lenape (Moor), and associated colonial lineages across Delaware, Maryland Eastern Shore, and Southern New Jersey.
          </p>

          <button
            onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
            className="mt-4 inline-flex items-center gap-2 text-xs font-mono font-semibold px-3 py-1.5 rounded-lg bg-[#26221E] hover:bg-[#332D27] border border-[#3E362F] hover:border-[#C68B59]/60 text-[#D4A373] transition-all shadow-sm"
          >
            <BookOpen className="w-3.5 h-3.5 text-[#C68B59]" />
            <span>{showHistoryDrawer ? 'Hide Regional Historical Context' : 'Read Historical Overview & Regional Context'}</span>
            {showHistoryDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showHistoryDrawer && (
            <div className="mt-5 p-5 sm:p-6 rounded-xl bg-[#141210]/95 border border-[#332D27] text-xs sm:text-sm text-[#C5BCB2] space-y-4 animate-fade-in shadow-2xl">
              <div>
                <h4 className="font-serif-header text-base sm:text-lg font-bold text-[#F3EBE3] flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-[#C68B59]" /> The Historical & Ecological Landscape
                </h4>
                <p className="text-[#A8A096] text-xs leading-relaxed mt-1.5">
                  Stretching between the Chesapeake Bay to the west and the Delaware Bay and Atlantic coastline to the east, the Delmarva Peninsula and the coastal marshes of Southern New Jersey formed an interconnected geographic haven for historic remnant communities. For centuries prior to European contact, Algonquian-speaking peoples—predominantly the Nanticoke of the Nanticoke and Indian River watersheds, the Lenape (Unami and Munsee) of the Delaware River valley, the Pocomoke, and the Choptank—sustained deep maritime, hunting, and agricultural networks across these estuaries.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-2">
                <div className="bg-[#1A1815] p-3 rounded-lg border border-[#2D2722]">
                  <strong className="text-[#D4A373] text-xs font-semibold block mb-1">Delaware Settlements (Kent & Sussex):</strong>
                  <p className="text-[11px] text-[#A8A096] leading-relaxed">
                    <strong>Cheswold / Moortown:</strong> Durham, Seeney, Consellor, Carney, Morgan, Ridgeway, Greenage.<br />
                    <strong>Indian River / Millsboro:</strong> Harmon, Clark, Street, Davis, Sockum, Wright, Norwood.
                  </p>
                </div>
                <div className="bg-[#1A1815] p-3 rounded-lg border border-[#2D2722]">
                  <strong className="text-[#D4A373] text-xs font-semibold block mb-1">South Jersey & Eastern Shore MD:</strong>
                  <p className="text-[11px] text-[#A8A096] leading-relaxed">
                    <strong>Gouldtown & Salem Co. NJ:</strong> Gould, Pierce, Cuff, Murray, Stewart.<br />
                    <strong>Jackson Town & Somerset MD:</strong> Jackson, Puckham / Bookram, Cottman, Handzer.
                  </p>
                </div>
              </div>

              <div className="pt-1">
                <h4 className="font-serif-header text-base sm:text-lg font-bold text-[#F3EBE3] flex items-center gap-2">
                  <Landmark className="w-4 h-4 text-[#C68B59]" /> Cultural Invisibility & Kinship Preservation
                </h4>
                <p className="text-[#A8A096] text-xs leading-relaxed mt-1.5">
                  Facing colonial pressures and shifting racial reclassification schemes that compressed identities into binary classifications, these families preserved their heritage through endogamous cousin marriages, independent community-funded schools (such as the State-aided Nanticoke Indian School and Fork Branch School), dedicated AME/Methodist churches, and economic independence as skilled shipbuilders, oystermen, and landowners.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* METRICS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mt-6 pt-6 border-t border-[#2B2621]">
          <div className="bg-[#121110]/80 border border-[#26221E] rounded-xl p-3.5">
            <span className="text-[11px] font-mono text-[#8C8275] uppercase block">Cataloged Ancestors</span>
            <div className="text-xl sm:text-2xl font-serif-header font-bold text-[#F3EBE3] mt-0.5">
              {stats.persons.toLocaleString()}
            </div>
            <span className="text-[10px] font-mono text-emerald-400">100% Hydrated</span>
          </div>

          <div className="bg-[#121110]/80 border border-[#26221E] rounded-xl p-3.5">
            <span className="text-[11px] font-mono text-[#8C8275] uppercase block">Primary Records</span>
            <div className="text-xl sm:text-2xl font-serif-header font-bold text-[#D4A373] mt-0.5">
              {stats.pages}
            </div>
            <span className="text-[10px] font-mono text-[#8C8275]">Deeds, Bibles & Census</span>
          </div>

          <div className="bg-[#121110]/80 border border-[#26221E] rounded-xl p-3.5">
            <span className="text-[11px] font-mono text-[#8C8275] uppercase block">Preserved Portraits</span>
            <div className="text-xl sm:text-2xl font-serif-header font-bold text-purple-300 mt-0.5">
              {stats.photos ? stats.photos.toLocaleString() : (stats.media_assets || 2839).toLocaleString()}
            </div>
            <span className="text-[10px] font-mono text-purple-400">Speck & Survey Photos</span>
          </div>

          <div className="bg-[#121110]/80 border border-[#26221E] rounded-xl p-3.5">
            <span className="text-[11px] font-mono text-[#8C8275] uppercase block">Verified Kinships</span>
            <div className="text-xl sm:text-2xl font-serif-header font-bold text-cyan-300 mt-0.5">
              {stats.relationships.toLocaleString()}
            </div>
            <span className="text-[10px] font-mono text-cyan-400">Relationship Links</span>
          </div>
        </div>
      </section>

      {/* GUIDED PATHWAYS BENTO */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Pathway 1: Surnames */}
        <div className="bg-[#1C1A17] border border-[#C68B59]/40 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-3">
              <div className="w-10 h-10 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center text-xl shrink-0">
                <Users className="w-5 h-5 text-[#C68B59]" />
              </div>
              <button
                onClick={() => setExpandedPathway(expandedPathway === 'surnames' ? null : 'surnames')}
                className="text-[11px] font-mono text-[#D4A373] hover:text-[#F3EBE3] px-2 py-1 rounded bg-[#121110] border border-[#332D27] transition-all"
              >
                {expandedPathway === 'surnames' ? 'Less ▲' : 'Details ▼'}
              </button>
            </div>
            <h3 className="font-serif-header text-base font-bold text-[#F3EBE3]">
              1. Family Lineage Portals
            </h3>
            <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed">
              Explore maternal and paternal clusters (Davis, Harmon, Durham, Mosley, Carney, Clark) with portraits and pedigree trees.
            </p>
            {expandedPathway === 'surnames' && (
              <div className="mt-3 pt-3 border-t border-[#2D2722] space-y-1.5 animate-fade-in">
                <span className="text-[10px] font-mono text-[#8C8275] uppercase">Featured Clans:</span>
                <div className="flex flex-wrap gap-1.5">
                  {['Davis', 'Harmon', 'Durham', 'Mosley', 'Carney', 'Clark', 'Pierce', 'Gould'].map(sn => (
                    <button
                      key={sn}
                      onClick={() => handleSelectSurname(sn)}
                      className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#121110] text-[#D4A373] border border-[#3A322B] hover:border-[#C68B59] hover:bg-[#C68B59]/10"
                    >
                      {sn} →
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <span className="text-xs font-mono text-[#D4A373] font-semibold mt-4 block">
            {safeSurnames.length} Lineages Preserved ↓
          </span>
        </div>

        {/* Pathway 2: Atlas */}
        <div 
          onClick={() => navigate('/atlas')}
          className="bg-[#1C1A17] hover:bg-[#221F1B] border border-[#332D27] hover:border-[#C68B59]/60 rounded-2xl p-5 shadow-lg transition-all cursor-pointer flex flex-col justify-between group"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-xl shrink-0 mb-3 text-blue-400">
              <Compass className="w-5 h-5" />
            </div>
            <h3 className="font-serif-header text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors">
              2. Migration Atlas & Cemeteries
            </h3>
            <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed">
              Interactive Delmarva cartography showing 6 settlement centers, 4 maritime/overland corridors, and 13 GPS-verified cemeteries.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-mono text-[#D4A373] font-semibold mt-4 group-hover:underline">
            Open Migration Atlas →
          </span>
        </div>

        {/* Pathway 3: Primary Records */}
        <div 
          onClick={() => navigate('/records')}
          className="bg-[#1C1A17] hover:bg-[#221F1B] border border-[#332D27] hover:border-[#C68B59]/60 rounded-2xl p-5 shadow-lg transition-all cursor-pointer flex flex-col justify-between group"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-xl shrink-0 mb-3 text-amber-400">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="font-serif-header text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors">
              3. Primary Document Vault
            </h3>
            <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed">
              Access 357 transcribed historical records including family Bibles, probate wills, 1790–1930 census schedules, and PDF downloads.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-mono text-[#D4A373] font-semibold mt-4 group-hover:underline">
            Explore Document Vault →
          </span>
        </div>
      </section>

      {/* LINEAGE PORTALS CATALOG HEADER */}
      <section className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#2B2621] pb-4">
          <div>
            <h3 className="font-serif-header text-2xl font-bold text-[#F3EBE3] tracking-tight">
              Historical Lineage Portals ({filteredSurnames.length})
            </h3>
            <p className="text-xs text-[#A8A096] mt-0.5">
              Select any surname to enter its dedicated archival lineage portal with portraits, documents, and kinships.
            </p>
          </div>

          {/* View Mode Switcher */}
          <div className="flex bg-[#161412] p-1 rounded-lg border border-[#2B2621] text-xs">
            <button
              onClick={() => setViewMode('grid')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                viewMode === 'grid'
                  ? 'bg-[#C68B59] text-[#121110] shadow'
                  : 'text-[#8C8275] hover:text-[#E5E1DB]'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              Grid View
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                viewMode === 'list'
                  ? 'bg-[#C68B59] text-[#121110] shadow'
                  : 'text-[#8C8275] hover:text-[#E5E1DB]'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              Compact List
            </button>
          </div>
        </div>

        {/* Featured Quick Strip */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 bg-[#161412] p-2.5 rounded-xl border border-[#2B2621]">
          <span className="text-[11px] font-mono text-[#D4A373] px-2 font-bold uppercase shrink-0 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#C87D53]" />
            Core Lineages:
          </span>
          {[
            { name: 'Davis', count: 160 },
            { name: 'Harmon', count: 272 },
            { name: 'Durham', count: 274 },
            { name: 'Mosley', count: 193 },
            { name: 'Moore', count: 75 },
            { name: 'Carney', count: 105 },
            { name: 'Clark', count: 90 },
            { name: 'Street', count: 61 },
            { name: 'Wright', count: 115 },
            { name: 'Seeney', count: 32 },
            { name: 'Pierce', count: 76 },
            { name: 'Gould', count: 22 },
            { name: 'Cuff', count: 35 }
          ].map(item => (
            <button
              key={item.name}
              onClick={() => handleSelectSurname(item.name)}
              className="px-3 py-1 rounded-lg text-xs font-mono font-medium transition-all shrink-0 bg-[#1F1C18] border border-[#3A332B] text-[#D4A373] hover:border-[#C68B59] hover:bg-[#C68B59]/10"
            >
              <span className="font-bold">{item.name}</span>
              <span className="text-[10px] text-[#A8A096] ml-1.5">({item.count})</span>
            </button>
          ))}
        </div>

        {/* A-Z Letter Jump Ribbon */}
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {alphabet.map(letter => (
            <button
              key={letter}
              onClick={() => {
                setSelectedLetter(letter);
                setCurrentPage(1);
              }}
              className={`text-xs font-mono px-2.5 py-1 rounded-lg border transition-all shrink-0 ${
                selectedLetter === letter
                  ? 'bg-[#C68B59] text-[#121110] font-bold border-[#C68B59]'
                  : 'bg-[#1C1A17] border-[#2B2621] text-[#A8A096] hover:border-[#C68B59]/40 hover:text-[#F3EBE3]'
              }`}
            >
              {letter}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="p-12 text-center text-xs font-mono text-[#8C8275]">
            <div className="inline-block w-6 h-6 border-2 border-[#C68B59]/30 border-t-[#C68B59] rounded-full animate-spin mb-3" />
            <p>Loading lineage portals catalog...</p>
          </div>
        )}

        {/* EMPTY STATE */}
        {!loading && paginatedSurnames.length === 0 && (
          <div className="p-12 text-center bg-[#161412] border border-[#26221E] rounded-xl text-xs font-mono text-[#8C8275]">
            No lineages found under letter "{selectedLetter}". Try selecting "ALL".
          </div>
        )}

        {/* SURNAME DISPLAY: GRID VS LIST */}
        {!loading && paginatedSurnames.length > 0 && (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {paginatedSurnames.map(s => (
                <SurnameCard
                  key={s.surname}
                  surname={s.surname}
                  variants={s.variants}
                  count={s.individual_count}
                  _pages={s.associated_pages}
                  photos={s.photo_count}
                  obituaries={s.obituary_count}
                  onSelect={handleSelectSurname}
                />
              ))}
            </div>
          ) : (
            <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl overflow-hidden shadow-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#121110] border-b border-[#2D2722] text-[#8C8275] font-serif-header uppercase text-[11px] tracking-wider">
                    <th className="py-3 px-4 font-bold">Surname Lineage</th>
                    <th className="py-3 px-4 font-bold">Variant Spellings</th>
                    <th className="py-3 px-4 font-bold text-right">Persons</th>
                    <th className="py-3 px-4 font-bold text-right">Photos</th>
                    <th className="py-3 px-4 font-bold text-right">Obituaries</th>
                    <th className="py-3 px-4 font-bold text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#2B2621]">
                  {paginatedSurnames.map(s => (
                    <tr
                      key={s.surname}
                      onClick={() => handleSelectSurname(s.surname)}
                      className="hover:bg-[#24201C] cursor-pointer transition-colors group"
                    >
                      <td className="py-3 px-4 font-serif-header font-bold text-[#F3EBE3] group-hover:text-[#D4A373] text-sm">
                        {s.surname}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-[#A8A096]">
                        {s.variants || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-right font-semibold text-[#F3EBE3] tabular-nums">
                        {s.individual_count}
                      </td>
                      <td className="py-3 px-4 font-mono text-right text-purple-300 tabular-nums">
                        {s.photo_count || 0}
                      </td>
                      <td className="py-3 px-4 font-mono text-right text-amber-300 tabular-nums">
                        {s.obituary_count || 0}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-[11px] font-mono text-[#C68B59] group-hover:underline">
                          View Portal →
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* PAGINATION TOOLBAR */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-[#2B2621] pt-4 text-xs font-mono text-[#8C8275]">
            <div>
              Showing {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, filteredSurnames.length)} of {filteredSurnames.length} portals
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                className="px-3 py-1.5 rounded-lg border border-[#332D27] bg-[#1C1A17] disabled:opacity-40 hover:border-[#C68B59]/60 hover:text-[#F3EBE3] transition-all"
              >
                Previous
              </button>
              <span className="text-[#D4A373] font-bold px-2">
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                className="px-3 py-1.5 rounded-lg border border-[#332D27] bg-[#1C1A17] disabled:opacity-40 hover:border-[#C68B59]/60 hover:text-[#F3EBE3] transition-all"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
