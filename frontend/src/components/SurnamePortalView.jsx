import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { 
  Users, Camera, GitFork, ArrowLeft, Search, HeartHandshake, 
  FileText, ExternalLink, Calendar, MapPin, ChevronRight, X, Sparkles, Filter, Printer
} from 'lucide-react';

export default function SurnamePortalView({ surname, onClose, onSelectPerson, onOpenGraph }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('photos'); // 'photos', 'members', 'trees', 'obituaries'
  const [photoFilter, setPhotoFilter] = useState('all'); // 'all', 'people', 'family_trees', 'documents', 'tombstones'
  const [memberSearch, setMemberSearch] = useState('');
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [expandedNotes, setExpandedNotes] = useState({});

  const toggleNote = (id) => {
    setExpandedNotes(prev => ({ ...prev, [id]: !prev[id] }));
  };

  useEffect(() => {
    if (!surname) return;
    setLoading(true);
    fetch(`/api/surnames/${surname}.json`)
      .then(r => r.json())
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load surname portal data:", err);
        setLoading(false);
      });

    // Prevent body scroll when portal view is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [surname]);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (lightboxPhoto) {
          setLightboxPhoto(null);
        } else if (onClose) {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxPhoto, onClose]);

  if (!surname) return null;

  const photos = data?.photos || [];
  const individuals = data?.individuals || [];
  const obituaries = data?.obituaries || [];
  const categoryCounts = data?.category_counts || {};

  // Filter photos
  const filteredPhotos = photos.filter(p => {
    if (photoFilter === 'all') return true;
    return p.category === photoFilter;
  });

  // Dedicated family trees
  const familyTrees = photos.filter(p => p.category === 'family_trees');

  // Filter individuals by search
  const filteredMembers = individuals.filter(m => {
    if (!memberSearch.trim()) return true;
    const q = memberSearch.toLowerCase();
    return (
      (m.name && m.name.toLowerCase().includes(q)) ||
      (m.birth_info && m.birth_info.toLowerCase().includes(q)) ||
      (m.death_info && m.death_info.toLowerCase().includes(q)) ||
      (m.notes && m.notes.toLowerCase().includes(q))
    );
  });

  return (
    <div className="fixed inset-0 z-50 bg-[#0C0F12] text-[#E5E1DB] overflow-y-auto custom-scrollbar flex flex-col font-sans animate-fade-in">
      {/* Sticky Top Navigation Bar */}
      <div className="sticky top-0 z-40 bg-[#12161D]/95 backdrop-blur-md border-b border-[#222B38] px-4 sm:px-8 py-3.5 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-[#9EA9B6] hover:text-[#C87D53] transition-colors font-medium text-sm px-3 py-1.5 rounded-xl hover:bg-[#1A222E]"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>All Surnames</span>
          </button>
          <span className="text-[#3A4759]">/</span>
          <span className="font-serif-header text-lg font-bold text-[#F3EBE3] tracking-wide">
            {surname} Portal
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 bg-[#171E27] hover:bg-[#222C38] border border-[#2B3848] text-[#D8D1C7] text-xs font-mono px-3 py-1.5 rounded-xl transition-all"
            title="Print Family Record"
          >
            <Printer className="w-3.5 h-3.5 text-[#C87D53]" />
            <span className="hidden sm:inline">Print Record</span>
          </button>

          {onOpenGraph && (
            <button
              onClick={() => {
                onClose();
                onOpenGraph(surname);
              }}
              className="flex items-center gap-2 bg-[#1B2430] hover:bg-[#253243] border border-[#2F3D50] text-[#D4A373] text-xs font-mono font-medium px-3.5 py-2 rounded-xl transition-all"
            >
              <GitFork className="w-3.5 h-3.5 text-[#C87D53]" />
              <span>Interactive Lineage Tree</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-[#171E27] border border-[#2B3746] text-[#9EA9B6] hover:text-[#F3EBE3] hover:border-[#C87D53]/50 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center text-[#9EA9B6] min-h-[60vh]">
          <div className="w-9 h-9 border-2 border-[#C87D53]/30 border-t-[#C87D53] rounded-full animate-spin mb-4" />
          <p className="font-mono text-xs tracking-wider uppercase">Loading {surname} Lineage Portal...</p>
        </div>
      ) : data ? (
        <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-8 space-y-8">
          {/* Hero Banner */}
          <div className="relative bg-gradient-to-br from-[#151C24] via-[#10151B] to-[#0A0D11] border border-[#24303F] rounded-3xl p-6 sm:p-10 shadow-2xl overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-[#C87D53]/5 rounded-full blur-3xl pointer-events-none" />
            
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C87D53]/10 border border-[#C87D53]/25 text-[#D4A373] text-xs font-mono">
                  <Sparkles className="w-3.5 h-3.5 text-[#C87D53]" />
                  <span>Delmarva & Nanticoke Preserved Lineage</span>
                </div>
                <h1 className="font-serif-header text-4xl sm:text-5xl font-bold text-[#F3EBE3] tracking-tight">
                  {surname} Family Lineage
                </h1>
                <p className="text-[#9EA9B6] text-sm max-w-2xl leading-relaxed">
                  Documented historical branch of the {surname} family spanning Kent & Sussex Counties (Delaware), 
                  Cumberland & Salem Counties (New Jersey), and the Chesapeake Bay region.
                </p>
                {data.variants && (
                  <p className="text-xs font-mono text-[#7D8B9B]">
                    Historical Variant Spellings: <span className="text-[#D4A373]">{data.variants}</span>
                  </p>
                )}
              </div>

              {/* Statistics Micro-Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#17202B]/80 border border-[#2A3748] rounded-2xl p-4 text-center">
                  <span className="block text-2xl font-bold font-serif-header text-[#F3EBE3]">
                    {data.individual_count}
                  </span>
                  <span className="text-[11px] font-mono text-[#8C9AA9] uppercase tracking-wider">Individuals</span>
                </div>
                <div className="bg-[#17202B]/80 border border-[#2A3748] rounded-2xl p-4 text-center">
                  <span className="block text-2xl font-bold font-serif-header text-[#C87D53]">
                    {data.photo_count}
                  </span>
                  <span className="text-[11px] font-mono text-[#8C9AA9] uppercase tracking-wider">Preserved Media</span>
                </div>
                <div className="bg-[#17202B]/80 border border-[#2A3748] rounded-2xl p-4 text-center">
                  <span className="block text-2xl font-bold font-serif-header text-[#619B8A]">
                    {familyTrees.length}
                  </span>
                  <span className="text-[11px] font-mono text-[#8C9AA9] uppercase tracking-wider">Pedigree Trees</span>
                </div>
                <div className="bg-[#17202B]/80 border border-[#2A3748] rounded-2xl p-4 text-center">
                  <span className="block text-2xl font-bold font-serif-header text-[#A37081]">
                    {data.obituary_count}
                  </span>
                  <span className="text-[11px] font-mono text-[#8C9AA9] uppercase tracking-wider">Memorials</span>
                </div>
              </div>
            </div>
          </div>

          {/* "What am I seeing?" Elder Guidance Banner */}
          <div className="bg-[#141A22] border border-[#263342] rounded-2xl p-4 sm:p-5 flex items-start gap-3.5 text-xs text-[#D8D1C7]">
            <span className="text-xl shrink-0">💡</span>
            <div>
              <p className="font-semibold text-[#F3EBE3] text-sm mb-1">Understanding the {surname} Family Portal:</p>
              <p className="text-[#A8A096] text-xs leading-relaxed">
                This dedicated portal connects all <strong>{data.individual_count} documented {surname} family members</strong>, their <strong>{data.photo_count} preserved photographs & documents</strong>, <strong>{familyTrees.length} multi-generation family trees</strong>, and cemetery memorials in one place. Click any photograph to view in high resolution, or click any family member to open their complete life story and family tree.
              </p>
            </div>
          </div>

          {/* Sub-Navigation Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#222B38] pb-4">
            <div className="flex flex-wrap items-center gap-2 bg-[#141A22] border border-[#263342] p-1.5 rounded-2xl">
              <button
                onClick={() => setActiveTab('photos')}
                className={`flex items-center gap-2.5 px-4 py-2.5 min-h-[44px] rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                  activeTab === 'photos'
                    ? 'bg-[#C87D53] text-[#0C0F12] font-bold shadow-md'
                    : 'text-[#D8D1C7] hover:text-[#F3EBE3]'
                }`}
              >
                <Camera className="w-4 h-4" />
                <span>Photographs ({photos.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('members')}
                className={`flex items-center gap-2.5 px-4 py-2.5 min-h-[44px] rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                  activeTab === 'members'
                    ? 'bg-[#C87D53] text-[#0C0F12] font-bold shadow-md'
                    : 'text-[#D8D1C7] hover:text-[#F3EBE3]'
                }`}
              >
                <Users className="w-4 h-4" />
                <span>Family Members ({individuals.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('trees')}
                className={`flex items-center gap-2.5 px-4 py-2.5 min-h-[44px] rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                  activeTab === 'trees'
                    ? 'bg-[#C87D53] text-[#0C0F12] font-bold shadow-md'
                    : 'text-[#D8D1C7] hover:text-[#F3EBE3]'
                }`}
              >
                <GitFork className="w-4 h-4" />
                <span>Family Trees ({familyTrees.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('obituaries')}
                className={`flex items-center gap-2.5 px-4 py-2.5 min-h-[44px] rounded-xl text-xs sm:text-sm font-semibold transition-all ${
                  activeTab === 'obituaries'
                    ? 'bg-[#C87D53] text-[#0C0F12] font-bold shadow-md'
                    : 'text-[#D8D1C7] hover:text-[#F3EBE3]'
                }`}
              >
                <HeartHandshake className="w-4 h-4" />
                <span>Memorials ({obituaries.length})</span>
              </button>
            </div>

            {activeTab === 'members' && (
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 text-[#7D8B9B] absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder={`Search ${surname} members...`}
                  value={memberSearch}
                  onChange={e => setMemberSearch(e.target.value)}
                  className="w-full bg-[#141A22] border border-[#263342] focus:border-[#C87D53] text-xs text-[#E5E1DB] pl-9 pr-3 py-2 rounded-xl outline-none"
                />
              </div>
            )}
          </div>

          {/* TAB CONTENT: 1. PHOTOS & MEDIA */}
          {activeTab === 'photos' && (
            <div className="space-y-6">
              {/* Photo Category Filter Pills */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-[#7D8B9B] font-mono mr-2 flex items-center gap-1">
                  <Filter className="w-3 h-3" /> Filter:
                </span>
                {[
                  { id: 'all', label: `All (${photos.length})` },
                  { id: 'people', label: `👥 People (${categoryCounts.people || 0})` },
                  { id: 'family_trees', label: `🌳 Trees (${categoryCounts.family_trees || 0})` },
                  { id: 'documents', label: `📜 Documents (${categoryCounts.documents || 0})` },
                  { id: 'tombstones', label: `🪦 Tombstones (${categoryCounts.tombstones || 0})` }
                ].map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setPhotoFilter(cat.id)}
                    className={`px-3 py-1.5 rounded-lg border font-mono transition-all ${
                      photoFilter === cat.id
                        ? 'bg-[#C87D53]/20 border-[#C87D53] text-[#D4A373] font-bold'
                        : 'bg-[#141A22] border-[#263342] text-[#9EA9B6] hover:border-[#384A5F]'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {filteredPhotos.length === 0 ? (
                <div className="bg-[#141A22] border border-[#263342] rounded-2xl p-12 text-center text-[#7D8B9B]">
                  <Camera className="w-10 h-10 text-[#263342] mx-auto mb-3" />
                  <p className="text-sm">No media records matching this category filter.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredPhotos.map(photo => (
                    <div
                      key={photo.photo_id}
                      onClick={() => setLightboxPhoto(photo)}
                      className="group relative aspect-square bg-[#12161E] border border-[#24303F] rounded-2xl overflow-hidden cursor-pointer shadow-md hover:shadow-2xl hover:border-[#C87D53]/60 transition-all"
                    >
                      <img
                        src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path}
                        alt={photo.subject_names || photo.normalized_filename}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                        loading="lazy"
                      />
                      
                      {/* Top Category Badge */}
                      <div className="absolute top-2 left-2 z-10">
                        <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-black/75 backdrop-blur-md text-[#D4A373] border border-[#C87D53]/30">
                          {photo.category}
                        </span>
                      </div>

                      {/* Hover Info Overlay */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4">
                        <p className="text-xs font-semibold text-white line-clamp-2 leading-tight">
                          {photo.subject_names || photo.normalized_filename.replace(/_/g, ' ').replace(/\.jpg|\.png|\.gif/g, '')}
                        </p>
                        {photo.approximate_year && (
                          <p className="text-[10px] font-mono text-[#D4A373] mt-1">
                            Year: {photo.approximate_year}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB CONTENT: 2. FAMILY MEMBERS */}
          {activeTab === 'members' && (
            <div className="space-y-4">
              <div className="text-xs text-[#7D8B9B] font-mono">
                Showing {filteredMembers.length} of {individuals.length} documented individuals
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredMembers.map(person => {
                  const isNoteExpanded = !!expandedNotes[person.person_id];
                  const hasLongNotes = person.notes && person.notes.length > 80;

                  return (
                    <div
                      key={person.person_id}
                      onClick={() => onSelectPerson && onSelectPerson(person.person_id)}
                      className="bento-card group bg-[#141A22] hover:bg-[#1C2430] border border-[#263342] hover:border-[#C87D53]/50 rounded-2xl p-5 transition-all cursor-pointer shadow-md hover:shadow-xl flex flex-col justify-between active:scale-[0.99] min-w-0"
                    >
                      <div className="min-w-0 w-full">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h3 className="font-serif-header text-lg font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors leading-tight break-words min-w-0">
                            {person.name}
                          </h3>
                          <span className="p-1.5 rounded-lg bg-[#12161D] border border-[#2B3848] text-[#7D8B9B] group-hover:text-[#D4A373] transition-colors shrink-0">
                            <ChevronRight className="w-3.5 h-3.5" />
                          </span>
                        </div>

                        {(person.birth_info || person.death_info) && (
                          <div className="flex items-center gap-1.5 text-xs text-[#9EA9B6] font-mono mb-2 flex-wrap">
                            <Calendar className="w-3.5 h-3.5 text-[#C87D53] shrink-0" />
                            <span className="break-words">
                              {person.birth_info ? `b. ${person.birth_info}` : ''}
                              {person.birth_info && person.death_info ? ' • ' : ''}
                              {person.death_info ? `d. ${person.death_info}` : ''}
                            </span>
                          </div>
                        )}

                        {person.notes && (
                          <div className="mt-2 text-xs text-[#7D8B9B]">
                            <p className={`${isNoteExpanded ? '' : 'line-clamp-2'} italic break-words leading-relaxed`}>
                              "{person.notes}"
                            </p>
                            {hasLongNotes && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleNote(person.person_id);
                                }}
                                className="text-[11px] font-mono text-[#D4A373] hover:underline mt-1 block"
                              >
                                {isNoteExpanded ? 'Collapse note ▲' : 'Read full note ▼'}
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="mt-4 pt-3 border-t border-[#222C3A] flex items-center justify-between text-[11px] font-mono">
                        <span className="text-[#7D8B9B]">Profile #{person.person_id}</span>
                        {person.photo_count > 0 && (
                          <span className="text-[#D4A373] bg-[#C87D53]/10 border border-[#C87D53]/20 px-2 py-0.5 rounded flex items-center gap-1">
                            <Camera className="w-3 h-3 text-[#C87D53]" />
                            {person.photo_count} {person.photo_count === 1 ? 'photo' : 'photos'}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB CONTENT: 3. PEDIGREE TREES */}
          {activeTab === 'trees' && (
            <div className="space-y-6">
              <div className="bg-[#141A22] border border-[#263342] rounded-2xl p-6">
                <h3 className="font-serif-header text-xl font-bold text-[#F3EBE3] mb-2 flex items-center gap-2">
                  <GitFork className="w-5 h-5 text-[#C87D53]" />
                  {surname} Pedigree & Descent Charts ({familyTrees.length})
                </h3>
                <p className="text-sm text-[#9EA9B6]">
                  Preserved multi-generation lineage charts compiled by Lynn C. Jackson and Delmarva genealogists.
                  Click on any chart to open full-resolution zoom.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {familyTrees.map(tree => (
                  <div
                    key={tree.photo_id}
                    onClick={() => setLightboxPhoto(tree)}
                    className="group bg-[#12161E] border border-[#24303F] hover:border-[#C87D53]/60 rounded-2xl overflow-hidden shadow-lg cursor-pointer transition-all"
                  >
                    <div className="aspect-[4/3] bg-[#0A0D11] relative overflow-hidden">
                      <img
                        src={tree.local_image_path.startsWith('/') ? tree.local_image_path : '/' + tree.local_image_path}
                        alt={tree.normalized_filename}
                        className="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    </div>
                    <div className="p-4 border-t border-[#222C3A]">
                      <h4 className="font-serif-header font-bold text-[#F3EBE3] group-hover:text-[#D4A373] text-sm truncate">
                        {tree.normalized_filename.replace(/_/g, ' ').replace(/\.jpg|\.gif|\.png/g, '')}
                      </h4>
                      {tree.subject_names && (
                        <p className="text-xs text-[#7D8B9B] mt-1 truncate">
                          Focus: {tree.subject_names}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB CONTENT: 4. OBITUARIES */}
          {activeTab === 'obituaries' && (
            <div className="space-y-6">
              {obituaries.length === 0 ? (
                <div className="bg-[#141A22] border border-[#263342] rounded-2xl p-12 text-center text-[#7D8B9B]">
                  <HeartHandshake className="w-10 h-10 text-[#263342] mx-auto mb-3" />
                  <p className="text-sm">No dedicated obituary records indexed for this surname branch.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {obituaries.map(obit => (
                    <div
                      key={obit.id}
                      className="bg-[#141A22] border border-[#263342] rounded-2xl p-6 shadow-md space-y-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-serif-header text-xl font-bold text-[#F3EBE3]">
                          {obit.deceased_name}
                        </h3>
                        {(obit.birth_date || obit.death_date) && (
                          <span className="text-xs font-mono text-[#D4A373] bg-[#C87D53]/10 border border-[#C87D53]/20 px-2.5 py-1 rounded-lg">
                            {obit.birth_date || ''} - {obit.death_date || ''}
                          </span>
                        )}
                      </div>

                      {obit.cemetery_location && (
                        <div className="flex items-center gap-1.5 text-xs text-[#8C9AA9] font-mono">
                          <MapPin className="w-3.5 h-3.5 text-[#C87D53]" />
                          <span>Burial: {obit.cemetery_location}</span>
                        </div>
                      )}

                      {obit.full_text && (
                        <div className="bg-[#0E1217] border border-[#1E2632] rounded-xl p-4 text-xs text-[#C5BDB5] leading-relaxed max-h-48 overflow-y-auto custom-scrollbar">
                          {obit.full_text}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-[#9EA9B6]">
          <p>Unable to load portal for {surname}.</p>
        </div>
      )}

      {/* LIGHTBOX MODAL rendered via Portal in document.body */}
      {lightboxPhoto && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-black/95 backdrop-blur-md flex items-center justify-center p-4 sm:p-8"
          onClick={() => setLightboxPhoto(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="relative max-w-5xl max-h-[92vh] w-full flex flex-col items-center"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setLightboxPhoto(null)}
              className="absolute -top-12 right-0 text-white/80 hover:text-white p-2.5 rounded-full bg-white/10 hover:bg-white/20 transition-all"
              aria-label="Close photo preview"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="bg-[#12161D] border border-[#2B3848] rounded-2xl overflow-hidden shadow-2xl max-h-[85vh] flex flex-col">
              <div className="flex-1 min-h-0 bg-[#0A0D11] flex items-center justify-center p-2">
                <img
                  src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                  alt={lightboxPhoto.normalized_filename}
                  className="max-h-[70vh] w-auto max-w-full object-contain mx-auto"
                />
              </div>
              <div className="p-4 bg-[#0F131A] border-t border-[#222C3A] text-left">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h4 className="font-serif-header text-lg font-bold text-[#F3EBE3]">
                      {lightboxPhoto.subject_names || lightboxPhoto.normalized_filename}
                    </h4>
                    <p className="text-xs text-[#8C9AA9] font-mono mt-0.5">
                      Category: <span className="text-[#D4A373] uppercase">{lightboxPhoto.category}</span>
                      {lightboxPhoto.approximate_year ? ` • Year: ${lightboxPhoto.approximate_year}` : ''}
                    </p>
                  </div>
                  <a
                    href={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1B2430] border border-[#2E3C4E] text-[#D4A373] hover:text-white text-xs font-mono transition-all"
                  >
                    <span>Full File</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
