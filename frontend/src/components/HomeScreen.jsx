import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Search, Database, Users, FileText, Image as ImageIcon, GitFork, BookOpen, ShieldCheck, HeartHandshake, GitCommit, Bookmark, LayoutGrid, List, Sparkles, Filter } from 'lucide-react';
import SurnameCard from './SurnameCard';
import RecordDrawer from './RecordDrawer';
import PersonProfileDrawer from './PersonProfileDrawer';
import CommandPalette from './CommandPalette';
import { trackPageView, trackEvent } from '../utils/analytics';

// Lazy load heavy components for instant initial page loading & reduced JS bundle size
const NetworkGraph = lazy(() => import('./NetworkGraph'));
const PhotoGallery = lazy(() => import('./PhotoGallery'));
const ObituaryViewer = lazy(() => import('./ObituaryViewer'));
const FamilyInterconnectionMatrix = lazy(() => import('./FamilyInterconnectionMatrix'));
const SourcesCatalog = lazy(() => import('./SourcesCatalog'));
const AuditResolutionPanel = lazy(() => import('./AuditResolutionPanel'));

export default function HomeScreen() {
  const [activeTab, setActiveTab] = useState('surnames');
  const [stats, setStats] = useState({ pages: 0, media_assets: 0, persons: 0, relationships: 0 });
  const [surnames, setSurnames] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [selectedSurname, setSelectedSurname] = useState(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [selectedLetter, setSelectedLetter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 24;

  // Track tab changes in Google Analytics
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    trackPageView(`/${tabId}`, `Tab: ${tabId}`);
    trackEvent('switch_tab', 'navigation', tabId);
  };

  useEffect(() => {
    fetch('/api/stats.json').then(res => res.json()).then(setStats).catch(console.error);
    fetch('/api/surnames.json').then(res => res.json()).then(setSurnames).catch(console.error);
    fetch('/api/graph.json').then(res => res.json()).then(setGraphData).catch(console.error);
  }, []);

  const handleSelectSurname = (surname) => {
    setSelectedSurname(surname);
    setActiveTab('graph');
    fetch('/api/graph.json')
      .then(res => res.json())
      .then(data => {
        if (surname && data.nodes) {
          const lowerS = surname.toLowerCase();
          const filteredNodes = data.nodes.filter(n => n.label?.toLowerCase().includes(lowerS) || n.group?.toLowerCase().includes(lowerS));
          const nodeIds = new Set(filteredNodes.map(n => n.id));
          const filteredEdges = data.edges.filter(e => nodeIds.has(e.from) || nodeIds.has(e.to));
          setGraphData({ nodes: filteredNodes, edges: filteredEdges });
        } else {
          setGraphData(data);
        }
      })
      .catch(console.error);
  };

  const handleOpenRecord = (filename) => {
    fetch(`/api/records/${encodeURIComponent(filename)}.json`)
      .then(res => res.json())
      .then(setSelectedRecord)
      .catch(console.error);
  };

  // Filter surnames by A-Z letter ribbon & apply windowed pagination
  const alphabet = ['ALL', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')];
  const filteredSurnames = surnames
    .filter(s => {
      if (selectedLetter === 'ALL') return true;
      return s.surname.toUpperCase().startsWith(selectedLetter);
    })
    .sort((a, b) => a.surname.localeCompare(b.surname, undefined, { sensitivity: 'base' }));

  const totalPages = Math.ceil(filteredSurnames.length / pageSize) || 1;
  const paginatedSurnames = filteredSurnames.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="min-h-screen bg-[#0F0E0D] text-[#E5E1DB] flex flex-col md:flex-row font-sans selection:bg-[#C68B59]/30 overflow-x-hidden">
      
      {/* MACFAMILYTREE-STYLE VERTICAL SIDEBAR NAVIGATION */}
      <aside className="w-full md:w-64 bg-[#141210] border-r border-[#26221E] flex flex-col shrink-0 z-30 shadow-2xl">
        {/* Top App Header & Brand */}
        <div className="p-4 border-b border-[#26221E] flex items-center justify-between">
          <a
            href="https://writteninthegenome.blog"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3"
          >
            <img
              src="/logo.webp"
              alt="Written In The Genome Official Logo"
              className="w-10 h-10 rounded-xl border border-[#C68B59]/50 group-hover:border-[#D4A373] object-cover shadow-lg shadow-[#C68B59]/20 transition-all duration-300 group-hover:scale-105"
              onError={e => { e.target.style.display = 'none'; }}
            />
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="font-serif-header font-bold text-base leading-tight text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors">
                  Genetic Archive
                </h1>
              </div>
              <p className="text-[10px] text-[#A8A096] font-sans font-medium tracking-wide">
                Written In The Genome
              </p>
            </div>
          </a>

          {/* Quick Search trigger */}
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="p-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#D4A373] rounded-lg transition-all active:scale-[0.98]"
            title="Search Person or Record (Cmd+K)"
          >
            <Search className="w-4 h-4" />
          </button>
        </div>

        {/* Primary Navigation Menu Categories */}
        <div className="p-3 flex-1 space-y-6 overflow-y-auto custom-scrollbar">
          {/* Main Navigation Section */}
          <div>
            <span className="text-[10px] font-bold text-[#8C8275] uppercase tracking-wider px-3 mb-2 block font-mono">
              Views & Charts
            </span>
            <nav className="space-y-1">
              {[
                { id: 'surnames', label: 'Surname Portals', icon: Users },
                { id: 'graph', label: 'Interactive Lineage Tree', icon: GitFork },
                { id: 'interconnections', label: 'Family Interconnections', icon: GitCommit },
                { id: 'gallery', label: 'Photo & Document Archive', icon: ImageIcon },
                { id: 'obituaries', label: 'Obituary Vault', icon: HeartHandshake },
                { id: 'records', label: 'Family Bible & Records', icon: FileText },
              ].map(tab => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-xs transition-all active:scale-[0.98] ${
                      isActive
                        ? 'bg-[#C68B59] text-[#121110] font-bold shadow-md shadow-[#C68B59]/20'
                        : 'text-[#A8A096] hover:bg-[#1C1A17] hover:text-[#F3EBE3]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#121110]' : 'text-[#8C8275]'}`} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Research & Integrity Section */}
          <div>
            <span className="text-[10px] font-bold text-[#8C8275] uppercase tracking-wider px-3 mb-2 block font-mono">
              Research & Audit
            </span>
            <nav className="space-y-1">
              {[
                { id: 'sources', label: 'Sources & Archives', icon: Bookmark },
                { id: 'audit', label: 'Integrity Review', icon: ShieldCheck }
              ].map(tab => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-xs transition-all active:scale-[0.98] ${
                      isActive
                        ? 'bg-[#C68B59] text-[#121110] font-bold shadow-md shadow-[#C68B59]/20'
                        : 'text-[#A8A096] hover:bg-[#1C1A17] hover:text-[#F3EBE3]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#121110]' : 'text-[#8C8275]'}`} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Repositories Quick Badge */}
          <div className="pt-2">
            <div className="p-3 bg-[#1C1A17] border border-[#332D27] rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#D4A373]">
                <Database className="w-3.5 h-3.5 text-[#C68B59]" />
                <span>Preserved Holdings</span>
              </div>
              <div className="text-[11px] text-[#A8A096] space-y-1 font-mono">
                <div className="flex justify-between"><span>Persons:</span><strong className="text-[#F3EBE3]">{stats.persons || 4887}</strong></div>
                <div className="flex justify-between"><span>Media Assets:</span><strong className="text-[#F3EBE3]">{stats.media_assets || 1971}</strong></div>
                <div className="flex justify-between"><span>Obituaries:</span><strong className="text-[#F3EBE3]">68</strong></div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Footer Links */}
        <div className="p-3 border-t border-[#26221E] space-y-2">
          <a
            href="https://writteninthegenome.blog"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full bg-[#1C1A17] hover:bg-[#26221E] border border-[#332D27] text-[#A8A096] hover:text-[#F3EBE3] px-3 py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5 text-[11px] font-medium"
          >
            <Sparkles className="w-3 h-3 text-[#D4A373]" />
            <span>Written In The Genome</span>
          </a>
        </div>
      </aside>

      {/* MAIN WORKSPACE CANVAS (MacFamilyTree Canvas Area) */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0F0E0D] overflow-y-auto custom-scrollbar">
        {/* Workspace Toolbar */}
        <div className="sticky top-0 z-20 bg-[#141210]/90 backdrop-blur-md border-b border-[#26221E] px-6 py-3.5 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-[#F3EBE3] font-serif-header capitalize flex items-center gap-2">
              {activeTab === 'surnames' && 'Delmarva & Nanticoke Maternal Surnames'}
              {activeTab === 'graph' && 'Interactive Lineage Tree & Network'}
              {activeTab === 'interconnections' && 'Family Interconnections Matrix'}
              {activeTab === 'gallery' && 'Photo & Media Document Archive'}
              {activeTab === 'obituaries' && 'Historical Obituary Vault'}
              {activeTab === 'records' && 'Family Bible & Primary Records'}
              {activeTab === 'sources' && 'Source Repositories & Archives'}
              {activeTab === 'audit' && 'System Integrity Review'}
            </h2>

          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#A8A096] hover:text-[#F3EBE3] px-3 py-1.5 rounded-xl transition-all text-xs font-semibold flex items-center gap-2"
            >
              <Search className="w-3.5 h-3.5 text-[#C68B59]" />
              <span>Search Database...</span>
              <kbd className="hidden sm:inline bg-[#121110] px-1.5 py-0.5 rounded text-[10px] font-mono border border-[#332D27] text-[#D4A373]">⌘K</kbd>
            </button>
          </div>
        </div>

        {/* Main Canvas View Body */}
        <div className="p-6 space-y-6 flex-1">
        {/* Integrated Record Repositories Banner */}
        <div className="p-4 bg-[#1C1A17] border border-[#332D27] rounded-xl flex flex-wrap items-center justify-between gap-4 shadow-md">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-[#C68B59]" />
            <span className="text-xs font-serif-header font-bold text-[#F3EBE3] tracking-wide uppercase">Integrated Record Repositories</span>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
            <a
              href="https://lynncjackson.com"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-[#121110] border border-[#332D27] hover:border-[#C68B59]/50 text-[#D4A373] px-3 py-1 rounded-lg transition-all flex items-center gap-1.5"
            >
              <span className="font-semibold">lynncjackson.com</span>
              <span className="text-[10px] text-[#8C8275]">(534 records)</span>
            </a>
            <a
              href="http://moors-delaware.com"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-[#121110] border border-[#332D27] hover:border-sky-500/50 text-sky-300 px-3 py-1 rounded-lg transition-all flex items-center gap-1.5"
            >
              <span className="font-semibold">moors-delaware.com</span>
              <span className="text-[10px] text-sky-400/70">(101 records)</span>
            </a>
            <a
              href="https://nativeamericansofdelawarestate.com"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-[#121110] border border-[#332D27] hover:border-emerald-500/50 text-emerald-300 px-3 py-1 rounded-lg transition-all flex items-center gap-1.5"
            >
              <span className="font-semibold">nativeamericansofdelawarestate.com</span>
              <span className="text-[10px] text-emerald-400/70">(1,945 photos / 364 obits)</span>
            </a>
            <a
              href="https://americanindian.si.edu/collections-search/search/archives"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-[#121110] border border-[#332D27] hover:border-purple-500/50 text-purple-300 px-3 py-1 rounded-lg transition-all flex items-center gap-1.5"
            >
              <span className="font-semibold">Smithsonian NMAI Speck Archive</span>
              <span className="text-[10px] text-purple-400/70">(Series 8 Nanticoke)</span>
            </a>
          </div>
        </div>

        {/* Central Search Focal Point & Quick Filters */}
        <div className="max-w-3xl mx-auto text-center space-y-4">
          <div className="relative">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="w-full flex items-center justify-between px-5 py-3.5 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59]/70 rounded-2xl text-[#F3EBE3] shadow-xl transition-all group active:scale-[0.98]"
            >
              <div className="flex items-center gap-3.5">
                <Search className="w-5 h-5 text-[#C68B59] group-hover:scale-110 transition-transform" />
                <span className="text-[#A8A096] text-sm font-normal">
                  Search individuals, surnames, Bible entries, probate wills, or census records...
                </span>
              </div>
              <span className="text-xs text-[#D4A373] font-mono bg-[#121110] border border-[#3A332B] px-2.5 py-1 rounded-lg group-hover:border-[#C68B59]/50">
                Ctrl + K
              </span>
            </button>
          </div>

          {/* Quick-Filter Tags */}
          <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono text-[#8C8275]">
            <span className="text-[#A8A096] font-semibold text-[11px] uppercase tracking-wider mr-1">Quick Filters:</span>
            {[
              { label: 'Harmon Lineage', action: () => handleSelectSurname('Harmon') },
              { label: 'Jackson Lineage', action: () => handleSelectSurname('Jackson') },
              { label: 'Durham Lineage', action: () => handleSelectSurname('Durham') },
              { label: 'Bible Records', action: () => setActiveTab('records') },
              { label: 'Photo Archive', action: () => setActiveTab('gallery') },
              { label: 'Obituaries', action: () => setActiveTab('obituaries') }
            ].map((tag, idx) => (
              <button
                key={idx}
                onClick={tag.action}
                className="bg-[#1C1A17] border border-[#2B2621] hover:border-[#C68B59]/40 hover:text-[#D4A373] px-2.5 py-1 rounded-lg transition-all"
              >
                [{tag.label}]
              </button>
            ))}
          </div>
        </div>

        {/* Tab 1: Surname Portals */}
        {activeTab === 'surnames' && (
          <div className="space-y-6">
            {/* Header & Controls Toolbar: A-Z Ribbon & View Mode Switcher */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#2B2621] pb-4">
              <div>
                <h2 className="font-serif-header text-2xl font-bold text-[#F3EBE3] tracking-tight">
                  Historical Lineage Portals ({filteredSurnames.length})
                </h2>
                <p className="text-xs text-[#A8A096] mt-0.5">
                  Explore preserved family surname clusters across Delaware, Maryland, New Jersey, and Virginia.
                </p>
              </div>

              {/* View Mode Switcher (Grid vs List) */}
              <div className="flex items-center gap-2">
                <div className="flex bg-[#161412] p-1 rounded-lg border border-[#2B2621] text-xs">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                      viewMode === 'grid'
                        ? 'bg-[#C68B59] text-[#121110] shadow'
                        : 'text-[#8C8275] hover:text-[#E5E1DB]'
                    }`}
                    title="3-Column Grid View"
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
                    title="Compact Table List View"
                  >
                    <List className="w-3.5 h-3.5" />
                    Compact List
                  </button>
                </div>
              </div>
            </div>

            {/* A–Z Alphabetical Quick-Jump Ribbon */}
            <div className="flex items-center gap-1 overflow-x-auto pb-2 custom-scrollbar bg-[#161412] p-2 rounded-xl border border-[#2B2621]">
              <span className="text-[11px] font-mono text-[#8C8275] px-2 font-semibold uppercase">Jump:</span>
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

            {/* Surname Display: Grid vs List (Windowed DOM rendering: max 24 cards/rows) */}
            {viewMode === 'grid' ? (
              /* 3-Column Grid View */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {paginatedSurnames.map(s => (
                  <SurnameCard
                    key={s.surname}
                    surname={s.surname}
                    variants={s.variants}
                    count={s.individual_count}
                    pages={s.associated_pages}
                    photos={s.photo_count}
                    obituaries={s.obituary_count}
                    onSelect={handleSelectSurname}
                  />
                ))}
              </div>
            ) : (
              /* Compact Table / List View */
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
                            View Lineage →
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* DOM Windowing Pagination Toolbar */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-[#2B2621] pt-4 text-xs font-mono text-[#8C8275]">
                <span>Showing page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({filteredSurnames.length} portals)</span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    className="bg-[#1C1A17] hover:bg-[#26221E] disabled:opacity-40 text-[#D4A373] border border-[#332D27] px-3 py-1.5 rounded-lg transition-all"
                  >
                    ← Previous
                  </button>
                  <button
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    className="bg-[#1C1A17] hover:bg-[#26221E] disabled:opacity-40 text-[#D4A373] border border-[#332D27] px-3 py-1.5 rounded-lg transition-all"
                  >
                    Next Page →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Lazy Loaded Tab Contents with Suspense Fallback */}
        <Suspense fallback={
          <div className="flex flex-col items-center justify-center py-20 text-[#8C8275]">
            <div className="w-8 h-8 border-2 border-[#C68B59]/30 border-t-[#C68B59] rounded-full animate-spin mb-3" />
            <p className="text-xs font-mono">Loading archive module...</p>
          </div>
        }>
          {/* Tab 2: Interconnections */}
          {activeTab === 'interconnections' && (
            <FamilyInterconnectionMatrix onSelectSurname={handleSelectSurname} />
          )}

          {/* Tab 3: Lineage Graph */}
          {activeTab === 'graph' && (
            <div className="h-[620px] flex flex-col">
              <div className="mb-4 flex justify-between items-center">
                <div>
                  <h2 className="font-serif-header text-xl font-bold text-[#F3EBE3]">
                    {selectedSurname ? `${selectedSurname} Lineage Graph` : 'Interactive Family Tree & Network'}
                  </h2>
                  <p className="text-xs text-[#A8A096]">Click any individual node to inspect their preserved source record.</p>
                </div>
                {selectedSurname && (
                  <button
                    onClick={() => {
                      setSelectedSurname(null);
                      fetch('/api/graph.json').then(res => res.json()).then(setGraphData);
                    }}
                    className="text-xs bg-[#1C1A17] hover:bg-[#26221E] text-[#D4A373] border border-[#332D27] px-3 py-1.5 rounded-lg"
                  >
                    Clear Filter
                  </button>
                )}
              </div>
              <div className="flex-1">
                <NetworkGraph
                  graphData={graphData}
                  onSelectNode={(node) => setSelectedPersonId(node.id)}
                />
              </div>
            </div>
          )}

          {/* Tab 4: Bible & Records */}
          {activeTab === 'records' && (
            <div className="space-y-4">
              <h2 className="font-serif-header text-xl font-bold text-[#F3EBE3]">Preserved Family Bibles & Historical Records</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {['Change_of_Race.htm', 'Winnesoccum.htm', 'bible-c.htm', 'bible-c1.htm', 'bible-j.htm', 'bible-r.htm', 'census.htm', 'census01.htm', 'taxlist.htm', 'probate.htm'].map((file, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleOpenRecord(file)}
                    className="p-4 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59]/60 rounded-xl cursor-pointer flex justify-between items-center transition-all group shadow-md"
                  >
                    <div className="flex items-center gap-3.5">
                      <div className="p-2 bg-[#121110] border border-[#2D2722] text-[#C68B59] rounded-lg group-hover:border-[#C68B59]/40">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <span className="font-serif-header font-bold text-[#F3EBE3] group-hover:text-[#D4A373] text-sm block">
                          {file}
                        </span>
                        <span className="text-xs text-[#8C8275] font-mono">Historical primary document record</span>
                      </div>
                    </div>
                    <span className="text-xs text-[#C68B59] font-mono font-medium group-hover:underline">View Record →</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 5: Photo Gallery */}
          {activeTab === 'gallery' && (
            <PhotoGallery />
          )}

          {/* Tab 6: Obituary Viewer */}
          {activeTab === 'obituaries' && (
            <ObituaryViewer onSelectPerson={(pid) => setSelectedPersonId(pid)} />
          )}

          {/* Tab 7: Sources Catalog */}
          {activeTab === 'sources' && (
            <SourcesCatalog onOpenRecord={handleOpenRecord} />
          )}

          {/* Tab 8: Audit Review */}
          {activeTab === 'audit' && (
            <AuditResolutionPanel />
          )}
        </Suspense>
        </div>

        {/* Official Written In The Genome Footer */}
        <footer className="border-t border-[#2D2722] bg-[#141210] mt-16 text-[#A8A096]">
          <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
            {/* Column 1: Brand & Tagline */}
            <div className="space-y-3.5 md:col-span-2">
              <div className="flex items-center gap-3">
                <img
                  src="/logo.webp"
                  alt="Written In The Genome Official Logo"
                  className="w-10 h-10 rounded-full border border-[#C68B59]/40 object-cover"
                />
                <div>
                  <h3 className="font-serif-header font-bold text-lg text-[#F3EBE3]">Written In The Genome</h3>
                  <p className="text-xs text-[#C68B59] font-mono">African American Genealogy & DNA Ancestry</p>
                </div>
              </div>
              <p className="text-xs text-[#8C8275] leading-relaxed max-w-md">
                Preserving African American & Native American genealogies, oral histories, family Bibles, probate wills, and genomic ancestry records across Central Delaware and the Delmarva Peninsula.
              </p>
            </div>

            {/* Column 2: Official Websites */}
            <div className="space-y-2.5">
              <h4 className="text-xs font-serif-header font-bold text-[#F3EBE3] uppercase tracking-wider">Official Websites</h4>
              <ul className="space-y-2 text-xs">
                <li>
                  <a
                    href="https://writteninthegenome.blog"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[#D4A373] transition-colors flex items-center gap-1.5"
                  >
                    <span>🌐 Main Blog & Research</span>
                  </a>
                </li>
                <li>
                  <a
                    href="https://writteninthegenome.blog"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[#D4A373] transition-colors flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3 h-3 text-[#C68B59]" />
                    <span>Genotype Scout Tool</span>
                  </a>
                </li>
                <li>
                  <a
                    href="https://familyarchive.writteninthegenome.blog"
                    className="text-[#D4A373] hover:underline font-semibold flex items-center gap-1.5"
                  >
                    <span>🧬 Genetic Archive</span>
                  </a>
                </li>
              </ul>
            </div>

            {/* Column 3: Repositories & Open Source */}
            <div className="space-y-2.5">
              <h4 className="text-xs font-serif-header font-bold text-[#F3EBE3] uppercase tracking-wider">Repositories & Code</h4>
              <ul className="space-y-2 text-xs">
                <li>
                  <a
                    href="https://github.com/jayrocktodef-bot/Nanticoke-Moor-by-witg"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[#D4A373] transition-colors"
                  >
                    GitHub Source Repository
                  </a>
                </li>
                <li>
                  <a
                    href="https://nativeamericansofdelawarestate.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[#D4A373] transition-colors"
                  >
                    Mitsawokett Photo Archive
                  </a>
                </li>
                <li>
                  <a
                    href="https://americanindian.si.edu/collections-search/search/archives"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-[#D4A373] transition-colors"
                  >
                    Smithsonian NMAI Archives
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t border-[#26221E] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[#665E54]">
            <p>© 2026 Written In The Genome. All Rights Reserved.</p>
            <p>Genetic Archive v3.0 • MacFamilyTree Workspace • {stats.persons || 4887} Preserved Profiles</p>
          </div>
        </div>
      </footer>
    </main>

      {/* Person Profile Drawer Modal */}
      {selectedPersonId && (
        <PersonProfileDrawer
          personId={selectedPersonId}
          onClose={() => setSelectedPersonId(null)}
          onSelectPerson={(pid) => setSelectedPersonId(pid)}
        />
      )}

      {/* Record Side Drawer Modal */}
      {selectedRecord && (
        <RecordDrawer
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}

      {/* Spotlight Command Palette (Ctrl+K) Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectPerson={(pid) => setSelectedPersonId(pid)}
        onSelectSurname={handleSelectSurname}
        onOpenRecord={handleOpenRecord}
      />
    </div>
  );
}
