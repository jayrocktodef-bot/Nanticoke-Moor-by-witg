import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { 
  Users, GitFork, MapPin, FileText, HeartHandshake, 
  Search, BookOpen, Volume2, Moon, Sun, Menu, X, 
  Sparkles, ShieldCheck, Bookmark, ChevronRight, Home, ScanFace
} from 'lucide-react';
import CommandPalette from '../CommandPalette';
import CitationModal from '../CitationModal';
import AncestorFaceMatcherModal from '../AncestorFaceMatcherModal';
import { fetchCachedJson } from '../../utils/apiCache';

const NAV_ITEMS = [
  { path: '/', label: 'Lineages', icon: Users, description: 'Surname Portals' },
  { path: '/ancestors', label: 'Ancestors', icon: Search, description: 'Directory & Filter' },
  { path: '/network', label: 'Kinship Graph', icon: GitFork, description: 'Family Network' },
  { path: '/atlas', label: 'Atlas & Cemeteries', icon: MapPin, description: 'Delmarva Cartography' },
  { path: '/records', label: 'Primary Records', icon: FileText, description: 'Transcriptions & Deeds' },
  { path: '/obituaries', label: 'Obituary Vault', icon: HeartHandshake, description: 'Memorial Broadsheets' },
  { path: '/interconnections', label: 'Interconnections', icon: Sparkles, description: 'Clan Intermarriages' },
  { path: '/oral-histories', label: 'Oral Histories', icon: Volume2, description: 'Elder Audio Archive' },
  { path: '/sources', label: 'Sources', icon: BookOpen, description: 'Scholarly Provenance' }
];

export default function AppLayout() {
  const [stats, setStats] = useState({ pages: 357, media_assets: 241, persons: 3783, relationships: 1576 });
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCitationOpen, setIsCitationOpen] = useState(false);
  const [isFaceMatcherOpen, setIsFaceMatcherOpen] = useState(false);
  const [isParchmentMode, setIsParchmentMode] = useState(() => {
    return localStorage.getItem('archive_theme') === 'parchment';
  });

  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCachedJson('/api/stats.json')
      .then(data => {
        if (data && data.persons) setStats(data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (isParchmentMode) {
      document.documentElement.classList.add('theme-parchment');
      localStorage.setItem('archive_theme', 'parchment');
    } else {
      document.documentElement.classList.remove('theme-parchment');
      localStorage.setItem('archive_theme', 'dark');
    }
  }, [isParchmentMode]);

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // Compute dynamic breadcrumbs
  const getBreadcrumbs = () => {
    const parts = location.pathname.split('/').filter(Boolean);
    if (parts.length === 0) return [{ label: 'Lineage Portals', path: '/' }];

    const crumbs = [{ label: 'Archive', path: '/' }];
    let currentPath = '';

    parts.forEach((part, idx) => {
      currentPath += `/${part}`;
      let label = decodeURIComponent(part);
      if (idx === 0) {
        const match = NAV_ITEMS.find(n => n.path === currentPath);
        label = match ? match.label : part.charAt(0).toUpperCase() + part.slice(1);
      } else if (parts[0] === 'ancestors') {
        label = `Ancestor #${part}`;
      } else if (parts[0] === 'lineages') {
        label = `${part} Family`;
      } else if (parts[0] === 'records') {
        label = `Record #${part}`;
      }
      crumbs.push({ label, path: currentPath });
    });

    return crumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <div className="min-h-screen bg-[#0F0E0D] text-[#E5E1DB] flex flex-col font-sans selection:bg-[#C68B59]/30">
      {/* Skip to Main Content Link for A11y */}
      <a 
        href="#main-content" 
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[9999] focus:px-4 focus:py-2 focus:bg-[#C68B59] focus:text-black focus:font-bold focus:rounded-xl focus:shadow-2xl focus:outline-none"
      >
        Skip to main content
      </a>
      
      {/* TOP HEADER */}
      <header className="sticky top-0 z-40 bg-[#141210]/95 backdrop-blur-md border-b border-[#26221E] shadow-xl">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2.5 flex items-center justify-between gap-3">
          
          {/* Brand & Title */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors active:scale-95"
              aria-label="Open Navigation Menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            <NavLink to="/" className="flex items-center gap-2.5 group">
              <img 
                src="/logo.webp" 
                alt="Logo" 
                className="w-8 h-8 rounded-lg border border-[#C68B59]/40 object-cover shadow-sm group-hover:border-[#C68B59] transition-all"
                onError={e => { e.currentTarget.style.display = 'none'; }}
              />
              <div>
                <h1 className="font-serif-header text-sm sm:text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors tracking-tight leading-none">
                  Lynn C. Jackson & Mitsawokett
                </h1>
                <p className="text-[10px] font-mono text-[#8C8275] tracking-wider uppercase mt-0.5">
                  Delmarva Afro-Indigenous Family Archive
                </p>
              </div>
            </NavLink>
          </div>

          {/* Center Search Trigger */}
          <div className="hidden sm:flex flex-1 max-w-md mx-4">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-xl bg-[#1A1815] border border-[#2D2722] text-[#8C8275] hover:border-[#C68B59]/50 hover:text-[#E5E1DB] transition-all text-xs font-mono group shadow-inner"
            >
              <span className="flex items-center gap-2">
                <Search className="w-3.5 h-3.5 text-[#C68B59] group-hover:scale-110 transition-transform" />
                <span className="text-[#A8A096]">Search 3,800+ ancestors, records, deeds...</span>
              </span>
              <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[10px] bg-[#26221E] border border-[#3A332C] rounded text-[#A8A096]">
                ⌘K
              </kbd>
            </button>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="sm:hidden p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
              aria-label="Search Archive"
            >
              <Search className="w-4 h-4" />
            </button>

            <button
              onClick={() => setIsFaceMatcherOpen(true)}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1C1A17] border border-[#332D27] hover:border-cyan-500/60 text-xs font-mono text-cyan-300 hover:text-white transition-all shadow-sm"
              title="Biometric Facial Matcher (ONNX)"
            >
              <ScanFace className="w-3.5 h-3.5 text-cyan-400" />
              <span>Face Matcher</span>
            </button>

            <button
              onClick={() => setIsCitationOpen(true)}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59]/50 text-xs font-mono text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
              title="Scholarly Citation & Provenance"
            >
              <Bookmark className="w-3.5 h-3.5 text-[#C68B59]" />
              <span>Cite Archive</span>
            </button>

            <button
              onClick={() => setIsParchmentMode(prev => !prev)}
              className="p-2 rounded-xl bg-[#1C1A17] border border-[#332D27] text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
              title="Toggle theme"
              aria-label="Toggle Parchment or Dark Theme"
            >
              {isParchmentMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* PRIMARY DESKTOP HORIZONTAL NAVIGATION BAR */}
        <nav className="hidden lg:block border-t border-[#211E1A] bg-[#100F0D]">
          <div className="max-w-7xl mx-auto px-6 flex items-center gap-1 overflow-x-auto py-1">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) => `
                    flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all whitespace-nowrap
                    ${isActive 
                      ? 'bg-[#C68B59]/15 text-[#D4A373] border border-[#C68B59]/40 font-bold shadow-sm' 
                      : 'text-[#8C8275] hover:text-[#E5E1DB] hover:bg-[#1A1815] border border-transparent'
                    }
                  `}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>

        {/* BREADCRUMBS BAR */}
        <div className="bg-[#12100E] border-t border-[#1C1A17] px-4 sm:px-6 py-1.5 text-[11px] font-mono text-[#8C8275]">
          <div className="max-w-7xl mx-auto flex items-center gap-1.5 overflow-x-auto">
            <Home className="w-3 h-3 text-[#A8A096] shrink-0" />
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.path}>
                <ChevronRight className="w-3 h-3 text-[#3A332C] shrink-0" />
                {idx === breadcrumbs.length - 1 ? (
                  <span className="text-[#D4A373] font-semibold truncate max-w-[200px] sm:max-w-none">
                    {crumb.label}
                  </span>
                ) : (
                  <NavLink to={crumb.path} className="hover:text-[#E5E1DB] transition-colors truncate">
                    {crumb.label}
                  </NavLink>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </header>

      {/* MOBILE DRAWER NAVIGATION */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm lg:hidden flex" onClick={() => setIsMobileMenuOpen(false)}>
          <div 
            className="w-72 max-w-[85vw] bg-[#141210] border-r border-[#2B2621] p-5 flex flex-col justify-between shadow-2xl h-full animate-fade-in"
            onClick={e => e.stopPropagation()}
          >
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-[#26221E] mb-4">
                <div className="flex items-center gap-2.5">
                  <img src="/logo.webp" alt="Logo" className="w-7 h-7 rounded-lg border border-[#C68B59]/40 object-cover" onError={e => { e.currentTarget.style.display = 'none'; }} />
                  <span className="font-serif-header font-bold text-sm text-[#F3EBE3]">Archive Menu</span>
                </div>
                <button 
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg bg-[#1C1A17] text-[#8C8275] hover:text-[#F3EBE3]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Mobile Nav Links */}
              <div className="space-y-1">
                {NAV_ITEMS.map(item => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === '/'}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={({ isActive }) => `
                        flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all
                        ${isActive 
                          ? 'bg-[#C68B59]/20 text-[#D4A373] border border-[#C68B59]/50' 
                          : 'text-[#A8A096] hover:bg-[#1C1A17] hover:text-[#F3EBE3]'
                        }
                      `}
                    >
                      <Icon className="w-4 h-4 shrink-0 text-[#C68B59]" />
                      <div>
                        <div className="leading-tight">{item.label}</div>
                        <div className="text-[10px] font-mono text-[#8C8275] font-normal">{item.description}</div>
                      </div>
                    </NavLink>
                  );
                })}
              </div>
            </div>

            {/* Drawer Footer Metrics */}
            <div className="pt-4 border-t border-[#26221E] text-[11px] font-mono text-[#8C8275] space-y-1">
              <div>Ancestors: <span className="text-[#F3EBE3]">{stats.persons.toLocaleString()}</span></div>
              <div>Primary Records: <span className="text-[#F3EBE3]">{stats.pages}</span></div>
              <div>Genealogical Proof: <span className="text-emerald-400">Level 3 (GPS)</span></div>
            </div>
          </div>
        </div>
      )}

      {/* MAIN VIEWPORT OUTLET */}
      <main id="main-content" tabIndex="-1" className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 pb-24 lg:pb-12 focus:outline-none">
        <Outlet />
      </main>

      {/* MOBILE BOTTOM NAVIGATION BAR */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-30 bg-[#141210]/95 backdrop-blur-md border-t border-[#26221E] px-2 py-1.5 flex items-center justify-around shadow-2xl">
        <NavLink 
          to="/" 
          end
          className={({ isActive }) => `flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] font-mono ${isActive ? 'text-[#D4A373]' : 'text-[#8C8275]'}`}
        >
          <Users className="w-4 h-4" />
          <span>Lineages</span>
        </NavLink>
        <NavLink 
          to="/ancestors" 
          className={({ isActive }) => `flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] font-mono ${isActive ? 'text-[#D4A373]' : 'text-[#8C8275]'}`}
        >
          <Search className="w-4 h-4" />
          <span>Ancestors</span>
        </NavLink>
        <NavLink 
          to="/atlas" 
          className={({ isActive }) => `flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] font-mono ${isActive ? 'text-[#D4A373]' : 'text-[#8C8275]'}`}
        >
          <MapPin className="w-4 h-4" />
          <span>Atlas</span>
        </NavLink>
        <NavLink 
          to="/obituaries" 
          className={({ isActive }) => `flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] font-mono ${isActive ? 'text-[#D4A373]' : 'text-[#8C8275]'}`}
        >
          <HeartHandshake className="w-4 h-4" />
          <span>Vault</span>
        </NavLink>
        <button 
          onClick={() => setIsCommandPaletteOpen(true)}
          className="flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] font-mono text-[#8C8275]"
        >
          <kbd className="px-1 py-0.2 bg-[#26221E] border border-[#3A332C] rounded text-[#D4A373] text-[9px]">⌘K</kbd>
          <span>Search</span>
        </button>
      </nav>

      {/* FOOTER */}
      <footer className="border-t border-[#211E1A] bg-[#0C0B0A] text-[#8C8275] text-xs py-8 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <p className="font-serif-header text-sm text-[#E5E1DB] font-semibold">
              Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Preservation Project
            </p>
            <p className="text-[11px] font-mono text-[#8C8275] mt-1">
              Scholarly citations adhering to Elizabeth Shown Mills (Evidence Explained) & Chicago Manual of Style (17th ed.)
            </p>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono">
            <a 
              href="https://writteninthegenome.blog" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-[#D4A373] hover:underline"
            >
              Written in the Genome Blog ↗
            </a>
            <button 
              onClick={() => setIsCitationOpen(true)}
              className="hover:text-[#E5E1DB] transition-colors"
            >
              Citation Guide
            </button>
          </div>
        </div>
      </footer>

      {/* GLOBAL SEARCH COMMAND PALETTE */}
      <CommandPalette 
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectPerson={(id) => navigate(`/ancestors/${id}`)}
        onSelectSurname={(sn) => navigate(`/lineages/${sn}`)}
        onOpenRecord={(rec) => {
          const recId = rec.photo_id || rec.filename || rec.identifier;
          navigate(`/records/${recId}`);
        }}
      />

      {/* GLOBAL ARCHIVE CITATION MODAL */}
      {isCitationOpen && (
        <CitationModal 
          isOpen={isCitationOpen}
          onClose={() => setIsCitationOpen(false)}
          item={{
            name: "Lynn C. Jackson & Mitsawokett Family Preservation Archive",
            person_id: "DELMARVA-ARCHIVE-MAIN",
            source_page: "Delmarva Afro-Indigenous Digital Repository"
          }}
          type="person"
        />
      )}

      {/* GLOBAL BIOMETRIC FACE MATCHER MODAL */}
      <AncestorFaceMatcherModal
        isOpen={isFaceMatcherOpen}
        onClose={() => setIsFaceMatcherOpen(false)}
      />
    </div>
  );
}
