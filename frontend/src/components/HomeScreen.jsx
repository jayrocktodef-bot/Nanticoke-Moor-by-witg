import React, { useState, useEffect, lazy, Suspense } from 'react';
import { createPortal } from 'react-dom';
import { Search, Database, Users, FileText, Image as ImageIcon, GitFork, BookOpen, ShieldCheck, HeartHandshake, GitCommit, Bookmark, LayoutGrid, List, Sparkles, Filter, Sun, Moon, Printer, Compass, MapPin, Dna, Volume2, Menu, X } from 'lucide-react';
import SurnameCard from './SurnameCard';
import RecordDrawer from './RecordDrawer';
import PersonProfileView from './PersonProfileView';
import SurnamePortalView from './SurnamePortalView';
import CommandPalette from './CommandPalette';
import TranscribedDocumentView from './TranscribedDocumentView';
import FacetedSearchPanel from './FacetedSearchPanel';
import KinshipPathExplorer from './KinshipPathExplorer';
import DNAMatchExplorer from './DNAMatchExplorer';
import OralHistoryPlayer from './OralHistoryPlayer';
import { trackPageView, trackEvent } from '../utils/analytics';
import { fetchCachedJson } from '../utils/apiCache';

// Lazy load heavy components for instant initial page loading & reduced JS bundle size
const NetworkGraph = lazy(() => import('./NetworkGraph'));
const PhotoGallery = lazy(() => import('./PhotoGallery'));
const ObituaryViewer = lazy(() => import('./ObituaryViewer'));
const FamilyInterconnectionMatrix = lazy(() => import('./FamilyInterconnectionMatrix'));
const SourcesCatalog = lazy(() => import('./SourcesCatalog'));
const AuditResolutionPanel = lazy(() => import('./AuditResolutionPanel'));
const HistoricalMigrationMap = lazy(() => import('./HistoricalMigrationMap'));

export default function HomeScreen() {
  const [activeTab, setActiveTab] = useState('surnames');
  const [visitedTabs, setVisitedTabs] = useState(() => new Set(['surnames']));
  const [stats, setStats] = useState({ pages: 0, media_assets: 0, persons: 0, relationships: 0 });
  const [surnames, setSurnames] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [selectedSurname, setSelectedSurname] = useState(null);
  const [activeSurnamePortal, setActiveSurnamePortal] = useState(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [selectedLetter, setSelectedLetter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [isParchmentMode, setIsParchmentMode] = useState(() => {
    return localStorage.getItem('archive_theme') === 'parchment';
  });
  const [expandedPathway, setExpandedPathway] = useState(null);
  const pageSize = 24;

  useEffect(() => {
    if (isParchmentMode) {
      document.documentElement.classList.add('theme-parchment');
      localStorage.setItem('archive_theme', 'parchment');
    } else {
      document.documentElement.classList.remove('theme-parchment');
      localStorage.setItem('archive_theme', 'dark');
    }
  }, [isParchmentMode]);

  // Track tab changes in Google Analytics & close mobile drawer
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setVisitedTabs(prev => new Set(prev).add(tabId));
    setIsMobileMenuOpen(false);
    trackPageView(`/${tabId}`, `Tab: ${tabId}`);
    trackEvent('switch_tab', 'navigation', tabId);
  };

  // Lock body scroll when mobile drawer is active
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else if (!selectedPersonId && !activeSurnamePortal && !selectedRecord) {
      document.body.style.overflow = 'auto';
    }
  }, [isMobileMenuOpen, selectedPersonId, activeSurnamePortal, selectedRecord]);

  // Ensure any change to activeTab (direct click, bento pathway, quick-filter, or deep link) marks the tab visited so lazy modules mount correctly
  useEffect(() => {
    setVisitedTabs(prev => new Set(prev).add(activeTab));
  }, [activeTab]);

  useEffect(() => {
    fetchCachedJson('/api/stats.json').then(setStats).catch(console.error);
    fetchCachedJson('/api/surnames.json').then(setSurnames).catch(console.error);

    // Idle-preload graph data in background so initial paint is instant
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      window.requestIdleCallback(() => {
        fetchCachedJson('/api/graph.json').then(setGraphData).catch(console.error);
      });
    } else {
      setTimeout(() => {
        fetchCachedJson('/api/graph.json').then(setGraphData).catch(console.error);
      }, 1000);
    }

    // Deep link support for surname portals: ?portal=Davis or ?surname=Davis
    const params = new URLSearchParams(window.location.search);
    const portalParam = params.get('portal') || params.get('surname');
    if (portalParam) {
      setActiveSurnamePortal(portalParam);
    }
  }, []);

  const handleOpenSurnamePortal = (surname) => {
    setActiveSurnamePortal(surname);
    trackEvent('open_portal', 'surname_portal', surname);
  };

  const handleSelectSurname = (surname) => {
    setSelectedSurname(surname);
    setActiveTab('graph');
    setVisitedTabs(prev => new Set(prev).add('graph'));
    fetchCachedJson('/api/graph.json')
      .then(data => {
        if (surname && data.nodes) {
          const lowerS = surname.toLowerCase();
          // Find primary matching surname nodes
          const surnameNodeIds = new Set(
            data.nodes
              .filter(n => n.label?.toLowerCase().includes(lowerS) || n.group?.toLowerCase().includes(lowerS))
              .map(n => n.id)
          );

          // Include 1-degree family members (spouses, parents, children with different surnames)
          const familyNodeIds = new Set(surnameNodeIds);
          (data.edges || []).forEach(e => {
            if (surnameNodeIds.has(e.from)) familyNodeIds.add(e.to);
            if (surnameNodeIds.has(e.to)) familyNodeIds.add(e.from);
          });

          const filteredNodes = data.nodes.filter(n => familyNodeIds.has(n.id));
          const filteredEdges = (data.edges || []).filter(e => familyNodeIds.has(e.from) && familyNodeIds.has(e.to));

          setGraphData({ nodes: filteredNodes, edges: filteredEdges });
        } else {
          setGraphData(data);
        }
      })
      .catch(console.error);
  };

  const handleOpenRecord = (filename) => {
    setSelectedRecord(filename);
  };

  // Filter surnames by A-Z letter ribbon & apply windowed pagination
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

  return (
    <div className="min-h-screen bg-[#0F0E0D] text-[#E5E1DB] flex flex-col md:flex-row font-sans selection:bg-[#C68B59]/30 overflow-x-hidden">
      
      {/* MOBILE TOP APP BAR (VISIBLE ON < md) */}
      <header className="md:hidden sticky top-0 z-30 bg-[#141210]/95 backdrop-blur-md border-b border-[#26221E] px-4 py-2.5 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 -ml-1 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors active:scale-95"
            aria-label="Open Archive Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <a href="https://writteninthegenome.blog" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
            <img src="/logo.webp" alt="Logo" className="w-7 h-7 rounded-lg border border-[#C68B59]/40 object-cover" onError={e => { e.target.style.display = 'none'; }} />
            <span className="font-serif-header font-bold text-sm text-[#F3EBE3]">Genetic Archive</span>
          </a>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsParchmentMode(prev => !prev)}
            className="p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
            title="Toggle theme"
            aria-label="Toggle Parchment or Dark Theme"
          >
            {isParchmentMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
            aria-label="Search Database (Ctrl+K)"
          >
            <Search className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* MOBILE NAVIGATION DRAWER (SLIDE-OVER FOR < md) */}
      {isMobileMenuOpen && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] md:hidden flex" role="dialog" aria-modal="true">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity" 
            onClick={() => setIsMobileMenuOpen(false)} 
          />
          
          {/* Drawer Surface */}
          <aside className="relative w-4/5 max-w-xs bg-[#141210] border-r border-[#26221E] flex flex-col h-full z-10 shadow-2xl overflow-y-auto custom-scrollbar animate-fade-in">
            <div className="p-4 border-b border-[#26221E] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <img src="/logo.webp" alt="Logo" className="w-8 h-8 rounded-lg border border-[#C68B59]/40 object-cover" onError={e => { e.target.style.display = 'none'; }} />
                <div>
                  <h2 className="font-serif-header font-bold text-sm text-[#F3EBE3]">Genetic Archive</h2>
                  <p className="text-[10px] text-[#A8A096]">Written In The Genome</p>
                </div>
              </div>
              <button 
                onClick={() => setIsMobileMenuOpen(false)}
                className="p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#A8A096] hover:text-white"
                aria-label="Close navigation menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Navigation Lists in Drawer */}
            <div className="p-3 flex-1 space-y-6 overflow-y-auto custom-scrollbar">
              <div>
                <span className="text-[10px] font-bold text-[#8C8275] uppercase tracking-wider px-3 mb-2 block font-mono">
                  Views & Charts
                </span>
                <nav className="space-y-1">
                  {[
                    { id: 'surnames', label: 'Family Portals', icon: Users },
                    { id: 'graph', label: 'Family Tree & Network', icon: GitFork },
                    { id: 'migration_map', label: 'Migration & Cemeteries', icon: Compass },
                    { id: 'interconnections', label: 'Clan Interconnections', icon: GitCommit },
                    { id: 'gallery', label: 'Photographs & Media', icon: ImageIcon },
                    { id: 'obituaries', label: 'Memorials & Obituaries', icon: HeartHandshake },
                    { id: 'records', label: 'Historical Records', icon: FileText },
                  ].map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl font-medium text-xs transition-all active:scale-[0.98] ${
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

              <div>
                <span className="text-[10px] font-bold text-[#8C8275] uppercase tracking-wider px-3 mb-2 block font-mono">
                  Research & Advanced Tools
                </span>
                <nav className="space-y-1">
                  {[
                    { id: 'faceted_search', label: 'Faceted Search', icon: Filter },
                    { id: 'kinship', label: 'Kinship Path Finder', icon: GitCommit },
                    { id: 'dna_matches', label: 'DNA Cousin Browser', icon: Dna },
                    { id: 'oral_history', label: 'Oral History Vault', icon: Volume2 },
                    { id: 'sources', label: 'Sources & Archives', icon: Bookmark },
                    { id: 'audit', label: 'Integrity Review', icon: ShieldCheck }
                  ].map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleTabChange(tab.id)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl font-medium text-xs transition-all active:scale-[0.98] ${
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

            <div className="p-3 border-t border-[#26221E] space-y-2">
              <a
                href="https://writteninthegenome.blog"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full bg-[#1C1A17] hover:bg-[#26221E] border border-[#332D27] text-[#A8A096] hover:text-[#F3EBE3] px-3 py-2 rounded-xl transition-all flex items-center justify-center gap-1.5 text-xs font-medium"
              >
                <Sparkles className="w-3.5 h-3.5 text-[#D4A373]" />
                <span>Written In The Genome Blog</span>
              </a>
            </div>
          </aside>
        </div>,
        document.body
      )}

      {/* DESKTOP SIDEBAR NAVIGATION (PERSISTENT ON md: AND ABOVE) */}
      <aside className="hidden md:flex md:w-64 bg-[#141210] border-r border-[#26221E] flex-col shrink-0 z-30 shadow-2xl h-screen sticky top-0" role="navigation" aria-label="Archive navigation">
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
            aria-label="Search persons and records (Ctrl+K)"
          >
            <Search className="w-4 h-4" aria-hidden="true" />
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
                { id: 'surnames', label: 'Family Portals', icon: Users },
                { id: 'graph', label: 'Family Tree & Network', icon: GitFork },
                { id: 'migration_map', label: 'Migration & Cemeteries', icon: Compass },
                { id: 'interconnections', label: 'Clan Interconnections', icon: GitCommit },
                { id: 'gallery', label: 'Photographs & Media', icon: ImageIcon },
                { id: 'obituaries', label: 'Memorials & Obituaries', icon: HeartHandshake },
                { id: 'records', label: 'Historical Records', icon: FileText },
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
              Research & Advanced Tools
            </span>
            <nav className="space-y-1">
              {[
                { id: 'faceted_search', label: 'Faceted Search', icon: Filter },
                { id: 'kinship', label: 'Kinship Path Finder', icon: GitCommit },
                { id: 'dna_matches', label: 'DNA Cousin Browser', icon: Dna },
                { id: 'oral_history', label: 'Oral History Vault', icon: Volume2 },
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

      {/* MOBILE STICKY BOTTOM NAVIGATION BAR (VISIBLE ON < md) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-[#141210]/95 backdrop-blur-md border-t border-[#26221E] px-1 py-1 flex items-center justify-around shadow-2xl" aria-label="Mobile quick navigation">
        {[
          { id: 'surnames', label: 'Portals', icon: Users },
          { id: 'graph', label: 'Tree', icon: GitFork },
          { id: 'gallery', label: 'Photos', icon: ImageIcon },
          { id: 'migration_map', label: 'Atlas', icon: Compass },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                handleTabChange(tab.id);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className={`flex flex-col items-center justify-center py-1.5 px-2 rounded-xl transition-all min-w-[54px] min-h-[44px] ${
                isActive ? 'text-[#C68B59] font-bold' : 'text-[#8C8275] hover:text-[#E5E1DB]'
              }`}
            >
              <Icon className={`w-4 h-4 mb-0.5 ${isActive ? 'text-[#C68B59]' : 'text-[#8C8275]'}`} />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
        
        <button
          onClick={() => setIsCommandPaletteOpen(true)}
          className="flex flex-col items-center justify-center py-1.5 px-2 rounded-xl text-[#8C8275] hover:text-[#E5E1DB] transition-all min-w-[54px] min-h-[44px]"
          aria-label="Search Database"
        >
          <Search className="w-4 h-4 mb-0.5 text-[#C68B59]" />
          <span className="text-[10px] font-medium">Search</span>
        </button>

        <button
          onClick={() => setIsMobileMenuOpen(true)}
          className="flex flex-col items-center justify-center py-1.5 px-2 rounded-xl text-[#8C8275] hover:text-[#E5E1DB] transition-all min-w-[54px] min-h-[44px]"
          aria-label="Open Full Archive Menu"
        >
          <Menu className="w-4 h-4 mb-0.5" />
          <span className="text-[10px] font-medium">All (13)</span>
        </button>
      </nav>

      {/* MAIN WORKSPACE CANVAS */}
      <main id="main-content" className="flex-1 flex flex-col min-w-0 bg-[#0F0E0D] overflow-y-auto custom-scrollbar pb-24 md:pb-8" role="main" aria-label="Archive content">
        {/* Workspace Toolbar */}
        <div className="sticky top-0 z-20 bg-[#141210]/90 backdrop-blur-md border-b border-[#26221E] px-4 md:px-6 py-3 flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm sm:text-base md:text-lg font-bold text-[#F3EBE3] font-serif-header truncate flex items-center gap-2">
              {activeTab === 'surnames' && 'Delmarva & Nanticoke Maternal Surnames'}
              {activeTab === 'graph' && 'Interactive Lineage Tree & Network'}
              {activeTab === 'migration_map' && 'Historical Migration Corridors & Cemetery Atlas'}
              {activeTab === 'interconnections' && 'Family Interconnections Matrix'}
              {activeTab === 'gallery' && 'Photo & Media Document Archive'}
              {activeTab === 'obituaries' && 'Historical Obituary Vault'}
              {activeTab === 'records' && 'Family Bible & Primary Records'}
              {activeTab === 'sources' && 'Source Repositories & Archives'}
              {activeTab === 'audit' && 'System Integrity Review'}
              {activeTab === 'faceted_search' && 'Faceted Search & Multi-Field Filter'}
              {activeTab === 'kinship' && 'Kinship Path Finder & Lineage Steps'}
              {activeTab === 'dna_matches' && 'DNA Match & Segment Explorer'}
              {activeTab === 'oral_history' && 'Oral History Vault & Elder Recordings'}
            </h2>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setIsParchmentMode(prev => !prev)}
              className="hidden sm:flex bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#A8A096] hover:text-[#F3EBE3] px-3.5 py-1.5 rounded-xl transition-all text-xs font-semibold items-center gap-2 shadow-sm"
              title="Toggle Parchment Historical Paper / Archive Night theme"
            >
              {isParchmentMode ? (
                <>
                  <Moon className="w-3.5 h-3.5 text-[#C68B59]" />
                  <span>Archive Night</span>
                </>
              ) : (
                <>
                  <Sun className="w-3.5 h-3.5 text-[#C68B59]" />
                  <span>Parchment Paper</span>
                </>
              )}
            </button>

            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#A8A096] hover:text-[#F3EBE3] px-3 py-1.5 sm:px-3.5 sm:py-1.5 rounded-xl transition-all text-xs font-semibold flex items-center gap-2 shadow-sm"
            >
              <Search className="w-3.5 h-3.5 text-[#C68B59]" />
              <span className="hidden sm:inline">Search Database...</span>
              <span className="sm:hidden text-xs">Search</span>
              <kbd className="hidden md:inline bg-[#121110] px-1.5 py-0.5 rounded text-[10px] font-mono border border-[#332D27] text-[#D4A373]">⌘K</kbd>
            </button>
          </div>
        </div>

        {/* Main Canvas View Body */}
        <div className="p-4 sm:p-6 space-y-6 flex-1">
        {/* Integrated Record Repositories Banner */}
        <div className="p-3.5 sm:p-4 bg-[#1C1A17] border border-[#332D27] rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
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
              { label: 'Bible Records', action: () => handleTabChange('records') },
              { label: 'Photo Archive', action: () => handleTabChange('gallery') },
              { label: 'Obituaries', action: () => handleTabChange('obituaries') }
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

        {/* Guided Pathways: Start Here for Elders, Families & Visitors (Expandable Bento System) */}
        <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-1 w-full">
          {/* Pathway Bento 1: Family Lines */}
          <div
            className={`bento-card group text-left bg-[#1C1A17] border rounded-2xl p-5 shadow-lg transition-all flex flex-col justify-between ${
              activeTab === 'surnames' ? 'border-[#C68B59] ring-1 ring-[#C68B59]/40' : 'border-[#332D27] hover:border-[#C68B59]/60'
            }`}
          >
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="w-10 h-10 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center text-xl shrink-0">
                  🌳
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedPathway(expandedPathway === 'surnames' ? null : 'surnames');
                  }}
                  className="text-[11px] font-mono text-[#D4A373] hover:text-[#F3EBE3] px-2 py-1 rounded bg-[#121110] border border-[#332D27] transition-all"
                  title="Expand or collapse featured lineages"
                >
                  {expandedPathway === 'surnames' ? 'Less ▲' : 'Details ▼'}
                </button>
              </div>

              <h3 
                onClick={() => handleTabChange('surnames')}
                className="font-serif-header text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors cursor-pointer"
              >
                1. Explore Family Lines
              </h3>
              <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed break-words">
                Browse preserved family portals (Davis, Harmon, Durham, Mosley, Carney...) with portraits & pedigree trees.
              </p>

              {/* Expandable Lineage Chips */}
              {expandedPathway === 'surnames' && (
                <div className="mt-3 pt-3 border-t border-[#2D2722] space-y-2 animate-fade-in">
                  <p className="text-[11px] font-mono text-[#8C8275] uppercase tracking-wider">Featured Lineage Portals:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {['Davis', 'Harmon', 'Durham', 'Mosley', 'Carney', 'Clark', 'Pierce', 'Gould'].map(sn => (
                      <button
                        key={sn}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenSurnamePortal(sn);
                        }}
                        className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#121110] text-[#D4A373] border border-[#3A322B] hover:border-[#C68B59] hover:bg-[#C68B59]/10 transition-all"
                      >
                        {sn} →
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => handleTabChange('surnames')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#D4A373] mt-4 font-mono hover:underline self-start"
            >
              Browse 50+ Portals →
            </button>
          </div>

          {/* Pathway Bento 2: Historic Photos */}
          <div
            className={`bento-card group text-left bg-[#1C1A17] border rounded-2xl p-5 shadow-lg transition-all flex flex-col justify-between ${
              activeTab === 'gallery' ? 'border-[#C68B59] ring-1 ring-[#C68B59]/40' : 'border-[#332D27] hover:border-[#C68B59]/60'
            }`}
          >
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="w-10 h-10 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center text-xl shrink-0">
                  📸
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedPathway(expandedPathway === 'gallery' ? null : 'gallery');
                  }}
                  className="text-[11px] font-mono text-[#D4A373] hover:text-[#F3EBE3] px-2 py-1 rounded bg-[#121110] border border-[#332D27] transition-all"
                  title="Expand or collapse media breakdown"
                >
                  {expandedPathway === 'gallery' ? 'Less ▲' : 'Details ▼'}
                </button>
              </div>

              <h3 
                onClick={() => handleTabChange('gallery')}
                className="font-serif-header text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors cursor-pointer"
              >
                2. See Historic Photos
              </h3>
              <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed break-words">
                Over 2,600 restored ancestor portraits, reunion photos, 5-generation pedigree charts, and cemetery tombstones.
              </p>

              {/* Expandable Category Chips */}
              {expandedPathway === 'gallery' && (
                <div className="mt-3 pt-3 border-t border-[#2D2722] space-y-2 animate-fade-in">
                  <p className="text-[11px] font-mono text-[#8C8275] uppercase tracking-wider">Catalog Holdings:</p>
                  <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono">
                    <span className="text-[#C5BCB2] bg-[#121110] px-2 py-1 rounded border border-[#2B2520]">👤 1,647 People</span>
                    <span className="text-[#C5BCB2] bg-[#121110] px-2 py-1 rounded border border-[#2B2520]">📜 461 Documents</span>
                    <span className="text-[#C5BCB2] bg-[#121110] px-2 py-1 rounded border border-[#2B2520]">🌳 392 Family Trees</span>
                    <span className="text-[#C5BCB2] bg-[#121110] px-2 py-1 rounded border border-[#2B2520]">🪦 111 Tombstones</span>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => handleTabChange('gallery')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#D4A373] mt-4 font-mono hover:underline self-start"
            >
              Open Media Archive →
            </button>
          </div>

          {/* Pathway Bento 3: Find Relative */}
          <div
            className="bento-card group text-left bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59]/60 rounded-2xl p-5 shadow-lg transition-all flex flex-col justify-between"
          >
            <div className="min-w-0 w-full">
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="w-10 h-10 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center text-xl shrink-0">
                  🔍
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedPathway(expandedPathway === 'search' ? null : 'search');
                  }}
                  className="text-[11px] font-mono text-[#D4A373] hover:text-[#F3EBE3] px-2 py-1 rounded bg-[#121110] border border-[#332D27] transition-all"
                  title="Expand or collapse search tips"
                >
                  {expandedPathway === 'search' ? 'Less ▲' : 'Details ▼'}
                </button>
              </div>

              <h3 
                onClick={() => setIsCommandPaletteOpen(true)}
                className="font-serif-header text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors cursor-pointer"
              >
                3. Find a Relative
              </h3>
              <p className="text-xs text-[#A8A096] mt-1.5 leading-relaxed break-words">
                Type any name, birth year, or Delmarva cemetery to search through 3,820 ancestor records instantly.
              </p>

              {/* Expandable Search Tips */}
              {expandedPathway === 'search' && (
                <div className="mt-3 pt-3 border-t border-[#2D2722] space-y-1.5 text-xs text-[#C5BCB2] animate-fade-in">
                  <p className="text-[11px] font-mono text-[#8C8275] uppercase tracking-wider">Search Tips:</p>
                  <p className="text-[11px] leading-relaxed">
                    • Try maiden names or alternative spellings (e.g., <em>Mosely, Caray</em>).
                  </p>
                  <p className="text-[11px] leading-relaxed">
                    • Search by cemetery name (e.g., <em>Immanuel Union, Fork Branch</em>).
                  </p>
                </div>
              )}
            </div>

            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#D4A373] mt-4 font-mono hover:underline self-start"
            >
              Search Database (⌘K) →
            </button>
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

            {/* Featured Lineage Portals Quick Strip */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2 custom-scrollbar bg-[#161412] p-2.5 rounded-xl border border-[#2B2621]">
              <span className="text-[11px] font-mono text-[#D4A373] px-2 font-bold uppercase shrink-0 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#C87D53]" />
                Featured Portals:
              </span>
              {[
                { name: 'Davis', count: 161, photos: 94, highlight: true },
                { name: 'Harmon', count: 274, photos: 121 },
                { name: 'Durham', count: 272, photos: 222 },
                { name: 'Mosley', count: 191, photos: 174 },
                { name: 'Carney', count: 106, photos: 114 },
                { name: 'Clark', count: 145, photos: 58 },
                { name: 'Pierce', count: 77, photos: 80 },
                { name: 'Sammons', count: 97, photos: 91 },
                { name: 'Wright', count: 115, photos: 87 },
                { name: 'Jackson', count: 122, photos: 85 }
              ].map(item => (
                <button
                  key={item.name}
                  onClick={() => handleOpenSurnamePortal(item.name)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all shrink-0 ${
                    item.highlight
                      ? 'bg-[#C68B59] text-[#121110] font-bold shadow-md shadow-[#C68B59]/25 hover:brightness-110'
                      : 'bg-[#1F1B17] hover:bg-[#2A241F] border border-[#332D27] hover:border-[#C68B59]/40 text-[#E5E1DB]'
                  }`}
                >
                  <span>{item.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${item.highlight ? 'bg-black/25 text-white font-bold' : 'bg-[#141210] text-[#A8A096]'}`}>
                    {item.photos} 📸
                  </span>
                </button>
              ))}
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
                    onSelect={handleOpenSurnamePortal}
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
                        onClick={() => handleOpenSurnamePortal(s.surname)}
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
          <div
            className={activeTab === 'interconnections' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'interconnections' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('interconnections') && (
              <FamilyInterconnectionMatrix onSelectSurname={handleSelectSurname} />
            )}
          </div>

          {/* Tab: Historical Migration Corridors & Cemetery Atlas */}
          <div
            className={activeTab === 'migration_map' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'migration_map' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('migration_map') && (
              <HistoricalMigrationMap onSelectPerson={(pid) => setSelectedPersonId(pid)} />
            )}
          </div>

          {/* Tab 3: Lineage Graph */}
          <div
            className={activeTab === 'graph' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'graph' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('graph') && (
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
                        fetchCachedJson('/api/graph.json').then(setGraphData);
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
                    defaultViewFormat={selectedSurname ? 'network' : 'focus'}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Tab 4: Bible & Records */}
          <div
            className={activeTab === 'records' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'records' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('records') && (
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
          </div>

          {/* Tab 5: Photo Gallery */}
          <div
            className={activeTab === 'gallery' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'gallery' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('gallery') && (
              <PhotoGallery />
            )}
          </div>

          {/* Tab 6: Obituary Viewer */}
          <div
            className={activeTab === 'obituaries' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'obituaries' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('obituaries') && (
              <ObituaryViewer onSelectPerson={(pid) => setSelectedPersonId(pid)} />
            )}
          </div>

          {/* Tab 8: Faceted Search */}
          <div
            className={activeTab === 'faceted_search' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'faceted_search' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('faceted_search') && (
              <FacetedSearchPanel onSelectPerson={(pid) => setSelectedPersonId(pid)} />
            )}
          </div>

          {/* Tab 9: Kinship Finder */}
          <div
            className={activeTab === 'kinship' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'kinship' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('kinship') && (
              <KinshipPathExplorer onSelectPerson={(pid) => setSelectedPersonId(pid)} />
            )}
          </div>

          {/* Tab 10: DNA Cousin Browser */}
          <div
            className={activeTab === 'dna_matches' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'dna_matches' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('dna_matches') && (
              <DNAMatchExplorer onSelectPerson={(pid) => setSelectedPersonId(pid)} />
            )}
          </div>

          {/* Tab 11: Oral History Vault */}
          <div
            className={activeTab === 'oral_history' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'oral_history' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('oral_history') && (
              <OralHistoryPlayer />
            )}
          </div>

          {/* Tab 7: Sources Catalog */}
          <div
            className={activeTab === 'sources' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'sources' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('sources') && (
              <SourcesCatalog onOpenRecord={handleOpenRecord} />
            )}
          </div>

          {/* Tab 8: Audit Review */}
          <div
            className={activeTab === 'audit' ? 'block' : 'hidden'}
            style={{ contentVisibility: activeTab === 'audit' ? 'visible' : 'hidden' }}
          >
            {visitedTabs.has('audit') && (
              <AuditResolutionPanel />
            )}
          </div>
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
                    target="_blank"
                    rel="noopener noreferrer"
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

      {/* Surname Portal View Modal */}
      {activeSurnamePortal && (
        <SurnamePortalView
          surname={activeSurnamePortal}
          onClose={() => setActiveSurnamePortal(null)}
          onSelectPerson={(pid) => setSelectedPersonId(pid)}
          onOpenGraph={(sn) => handleSelectSurname(sn)}
        />
      )}

      {/* Person Profile Drawer Modal */}
      {/* Selected Person Overlay */}
      {selectedPersonId && (
        <PersonProfileView
          personId={selectedPersonId}
          onClose={() => setSelectedPersonId(null)}
          onSelectPerson={setSelectedPersonId}
        />
      )}

      {/* Text-Only Transcribed Document Reader Modal */}
      {selectedRecord && (
        <TranscribedDocumentView
          identifier={typeof selectedRecord === 'string' ? selectedRecord : selectedRecord.filename}
          initialData={typeof selectedRecord === 'object' && selectedRecord.lines ? selectedRecord : null}
          onClose={() => setSelectedRecord(null)}
          onSelectPerson={(pid) => setSelectedPersonId(pid)}
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
