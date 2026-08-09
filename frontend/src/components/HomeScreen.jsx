import React, { useState, useEffect } from 'react';
import { Search, Database, Users, FileText, Image as ImageIcon, GitFork, BookOpen, ShieldCheck, HeartHandshake, Download, GitCommit, Bookmark, LayoutGrid, List, Sparkles, Filter } from 'lucide-react';
import SurnameCard from './SurnameCard';
import NetworkGraph from './NetworkGraph';
import RecordDrawer from './RecordDrawer';
import AuditResolutionPanel from './AuditResolutionPanel';
import PhotoGallery from './PhotoGallery';
import ObituaryViewer from './ObituaryViewer';
import PersonProfileDrawer from './PersonProfileDrawer';
import FamilyInterconnectionMatrix from './FamilyInterconnectionMatrix';
import SourcesCatalog from './SourcesCatalog';
import CommandPalette from './CommandPalette';

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

  useEffect(() => {
    fetch('/api/stats').then(res => res.json()).then(setStats).catch(console.error);
    fetch('/api/surnames').then(res => res.json()).then(setSurnames).catch(console.error);
    fetch('/api/graph').then(res => res.json()).then(setGraphData).catch(console.error);
  }, []);

  const handleSelectSurname = (surname) => {
    setSelectedSurname(surname);
    setActiveTab('graph');
    fetch(`/api/graph?surname=${encodeURIComponent(surname)}`)
      .then(res => res.json())
      .then(setGraphData)
      .catch(console.error);
  };

  const handleOpenRecord = (filename) => {
    fetch(`/api/records/${encodeURIComponent(filename)}`)
      .then(res => res.json())
      .then(setSelectedRecord)
      .catch(console.error);
  };

  // Filter surnames by A-Z letter ribbon
  const alphabet = ['ALL', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')];
  const filteredSurnames = surnames.filter(s => {
    if (selectedLetter === 'ALL') return true;
    return s.surname.toUpperCase().startsWith(selectedLetter);
  });

  return (
    <div className="min-h-screen bg-[#121110] text-[#E5E1DB] flex flex-col font-sans selection:bg-[#C68B59]/30">
      {/* Header & Navigation Toolbar */}
      <header className="border-b border-[#2D2722] bg-[#161412]/95 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-gradient-to-br from-[#C68B59] to-[#9E6437] rounded-lg text-[#121110] shadow-md shadow-[#C68B59]/20">
              <BookOpen className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div>
              <h1 className="font-serif-header font-bold text-lg leading-tight tracking-tight text-[#F3EBE3]">
                Genetic Archive
              </h1>
              <span className="text-xs text-[#A8A096] font-mono tracking-wide">writteninthegenome.blog</span>
            </div>
          </div>

          {/* Persistent Heritage Stats & GEDCOM Export */}
          <div className="hidden md:flex items-center gap-6 text-xs text-[#A8A096] font-mono">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-sky-400" />
              <span><strong className="text-[#F3EBE3] tabular-nums">{stats.pages}</strong> Pages</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-[#C68B59]" />
              <span><strong className="text-[#F3EBE3] tabular-nums">{stats.persons}</strong> Persons</span>
            </div>
            <div className="flex items-center gap-2">
              <GitFork className="w-4 h-4 text-emerald-400" />
              <span><strong className="text-[#F3EBE3] tabular-nums">{stats.relationships}</strong> Lineages</span>
            </div>
            <div className="flex items-center gap-2">
              <ImageIcon className="w-4 h-4 text-purple-400" />
              <span><strong className="text-[#F3EBE3] tabular-nums">{stats.photos || stats.media_assets}</strong> Photos</span>
            </div>
            <a
              href="/api/export/gedcom"
              download="delmarva_genealogy_preservation.ged"
              className="bg-[#C68B59]/15 border border-[#C68B59]/40 text-[#D4A373] px-3.5 py-1.5 rounded-lg hover:bg-[#C68B59]/25 hover:border-[#C68B59]/60 transition-all flex items-center gap-1.5 font-semibold text-xs shadow-sm"
              title="Export complete lineage database in standard GEDCOM format"
            >
              <Download className="w-3.5 h-3.5" />
              Export GEDCOM
            </a>
          </div>
        </div>

        {/* Global Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-8 text-sm font-medium border-t border-[#26221E] overflow-x-auto custom-scrollbar">
          {[
            { id: 'surnames', label: 'Surname Portals', icon: Users },
            { id: 'interconnections', label: 'Interconnections', icon: GitCommit },
            { id: 'graph', label: 'Lineage Graph', icon: GitFork },
            { id: 'records', label: 'Bible & Records', icon: FileText },
            { id: 'gallery', label: 'Photo Archive', icon: ImageIcon },
            { id: 'obituaries', label: 'Obituaries', icon: HeartHandshake },
            { id: 'sources', label: 'Sources & Archives', icon: Bookmark },
            { id: 'audit', label: 'Audit Review', icon: ShieldCheck }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-3.5 border-b-2 transition-all shrink-0 ${
                  isActive
                    ? 'border-[#C68B59] text-[#D4A373] font-semibold'
                    : 'border-transparent text-[#A8A096] hover:text-[#F3EBE3]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-[#C68B59]' : 'text-[#8C8275]'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-8">
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
              className="w-full flex items-center justify-between px-5 py-3.5 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59]/70 rounded-2xl text-[#F3EBE3] shadow-xl transition-all group"
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
                  onClick={() => setSelectedLetter(letter)}
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

            {/* Surname Display: Grid vs List */}
            {viewMode === 'grid' ? (
              /* 3-Column Grid View */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredSurnames.map(s => (
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
                    {filteredSurnames.map(s => (
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
          </div>
        )}

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
                    fetch('/api/graph').then(res => res.json()).then(setGraphData);
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
          <ObituaryViewer />
        )}

        {/* Tab 7: Sources Catalog */}
        {activeTab === 'sources' && (
          <SourcesCatalog onOpenRecord={handleOpenRecord} />
        )}

        {/* Tab 8: Audit Review */}
        {activeTab === 'audit' && (
          <AuditResolutionPanel />
        )}
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
