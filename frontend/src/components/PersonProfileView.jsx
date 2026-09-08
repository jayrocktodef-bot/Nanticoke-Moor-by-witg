import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { User, Users, Camera, HeartHandshake, FileText, ExternalLink, Calendar, GitBranch, ArrowLeft, ShieldCheck, MapPin, X, BookOpen, Clock, ChevronRight } from 'lucide-react';
import CitationModal from './CitationModal';
import NarrativeBioGenerator from './NarrativeBioGenerator';
import { fetchCachedJson } from '../utils/apiCache';

export default function PersonProfileView({ personId, onClose, onSelectPerson }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [isCitationOpen, setIsCitationOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('facts');

  useEffect(() => {
    if (!personId) return;
    setLoading(true);
    const cleanId = String(personId).replace('.json', '');
    fetchCachedJson(`/api/person/${cleanId}`)
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(() => {
        fetchCachedJson(`/api/person/${cleanId}.json`)
          .then(data => {
            setProfile(data);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });

    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [personId]);

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

  if (!personId) return null;

  const primaryPhoto = profile?.photos?.[0];
  const parents = profile?.relationships?.filter(r => r.role === 'parent' || r.relationship_type === 'parent' || r.relationship_type === 'child_of') || [];
  const spouses = profile?.relationships?.filter(r => r.role === 'spouse' || r.relationship_type === 'spouse' || r.relationship_type === 'spouse_of') || [];
  const siblings = profile?.relationships?.filter(r => r.role === 'sibling' || r.relationship_type === 'sibling' || r.relationship_type === 'sibling_of') || [];
  const children = profile?.relationships?.filter(r => r.role === 'child' || r.relationship_type === 'child' || r.relationship_type === 'parent_of') || [];
  
  // Create timeline events array
  const timelineEvents = [];
  if (profile?.person?.birth_date || profile?.person?.birth_place) {
    timelineEvents.push({ type: 'Birth', year: profile.person.birth_date?.match(/\d{4}/)?.[0] || 'Unknown', date: profile.person.birth_date, place: profile.person.birth_place, isMajor: true });
  }
  
  profile?.photos?.filter(p => p.date_text).forEach(photo => {
    timelineEvents.push({ type: 'Media', year: photo.date_text?.match(/\d{4}/)?.[0] || photo.date_text, date: photo.date_text, description: photo.subject_names, photo, isMajor: false });
  });

  if (profile?.person?.death_date || profile?.person?.death_place) {
    timelineEvents.push({ type: 'Death', year: profile.person.death_date?.match(/\d{4}/)?.[0] || 'Unknown', date: profile.person.death_date, place: profile.person.death_place, isMajor: true });
  }
  
  // Sort timeline events by year loosely
  timelineEvents.sort((a, b) => {
    const yearA = parseInt(a.year) || 0;
    const yearB = parseInt(b.year) || 0;
    if (a.type === 'Birth') return -1;
    if (b.type === 'Birth') return 1;
    if (a.type === 'Death') return 1;
    if (b.type === 'Death') return -1;
    return yearA - yearB;
  });

  return (
    <div className="fixed inset-0 z-50 bg-gray-50 text-gray-900 overflow-y-auto custom-scrollbar animate-fade-in flex flex-col font-sans">
      
      {/* Top Header (Dark) */}
      {/* Top Header (Dark) */}
      <header className="bg-[#414243] text-white shadow-md relative sm:sticky sm:top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Back Nav */}
          <div className="py-2.5 flex items-center justify-between border-b border-gray-600/70">
            {onClose ? (
              <button 
                onClick={onClose} 
                className="flex items-center gap-1.5 min-h-[44px] text-sm text-gray-300 hover:text-white transition-colors"
                aria-label="Back to tree or previous view"
              >
                <ArrowLeft className="w-4 h-4" /> <span>Back to Tree</span>
              </button>
            ) : <div />}
            <div className="flex items-center gap-2 sm:gap-3">
              <button 
                onClick={() => setIsCitationOpen(true)} 
                className="flex items-center gap-1.5 min-h-[44px] px-2 py-1 text-xs text-blue-300 hover:text-blue-100 transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" /> <span>Cite & Export</span>
              </button>
              {onClose && (
                <button 
                  onClick={onClose} 
                  className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:text-white" 
                  aria-label="Close profile"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>

          {loading ? (
            <div className="py-12 flex justify-center"><div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" /></div>
          ) : profile ? (
            <div className="py-5 sm:py-6 flex flex-col sm:flex-row gap-5 sm:gap-6 items-center sm:items-start text-center sm:text-left">
              {/* Profile Pic */}
              <div className="shrink-0 relative">
                {primaryPhoto ? (
                  <img 
                    src={primaryPhoto.local_image_path.startsWith('/') ? primaryPhoto.local_image_path : '/' + primaryPhoto.local_image_path} 
                    alt={`Portrait of ${profile.person?.first_name || profile.person?.name || ''} ${profile.person?.married_last_name || profile.person?.last_name || ''}`.trim() || 'Profile portrait'} 
                    style={{
                      objectPosition: primaryPhoto.face_x ? `${primaryPhoto.face_x * 100}% ${primaryPhoto.face_y * 100}%` : '50% 22%'
                    }}
                    className="w-28 h-28 sm:w-40 sm:h-40 rounded-xl object-cover border-4 border-white/10 shadow-lg" 
                  />
                ) : (
                  <div className="w-28 h-28 sm:w-40 sm:h-40 rounded-xl bg-gray-600 border-4 border-white/10 flex items-center justify-center shadow-lg">
                    <User className="w-14 h-14 sm:w-16 sm:h-16 text-gray-400" />
                  </div>
                )}
              </div>

              {/* Identity Block */}
              <div className="flex-1 mt-1 sm:mt-2 min-w-0">
                <h1 className="font-serif text-2xl sm:text-4xl lg:text-5xl tracking-tight font-medium break-words">
                  {profile.person.first_name || profile.person.name} <span className="font-bold">{profile.person.married_last_name || profile.person.last_name}</span>
                </h1>
                
                <div className="mt-3 space-y-1.5 text-gray-300 text-xs sm:text-sm">
                  {(profile.person.birth_date || profile.person.birth_place) && (
                    <p className="flex items-center justify-center sm:justify-start flex-wrap gap-x-2">
                      <span className="font-bold text-gray-400 uppercase tracking-wider text-[11px]">BIRTH</span>
                      <span className="text-white font-medium">{profile.person.birth_date || 'Unknown'}</span>
                      {profile.person.birth_place && <span className="text-gray-400">• {profile.person.birth_place}</span>}
                    </p>
                  )}
                  {(profile.person.death_date || profile.person.death_place) && (
                    <p className="flex items-center justify-center sm:justify-start flex-wrap gap-x-2">
                      <span className="font-bold text-gray-400 uppercase tracking-wider text-[11px]">DEATH</span>
                      <span className="text-white font-medium">{profile.person.death_date || 'Unknown'}</span>
                      {profile.person.death_place && <span className="text-gray-400">• {profile.person.death_place}</span>}
                    </p>
                  )}
                </div>

                <div className="mt-4 flex gap-2 flex-wrap justify-center sm:justify-start">
                  {profile.person.evidence_level === 4 && <span className="px-2.5 py-1 rounded bg-purple-900/50 text-purple-200 text-xs flex items-center gap-1 border border-purple-700/50"><ShieldCheck className="w-3 h-3"/> DNA Verified</span>}
                  {profile.person.evidence_level === 3 && <span className="px-2.5 py-1 rounded bg-emerald-900/50 text-emerald-200 text-xs flex items-center gap-1 border border-emerald-700/50"><ShieldCheck className="w-3 h-3"/> Primary Source</span>}
                  {profile.person.evidence_level === 2 && <span className="px-2.5 py-1 rounded bg-blue-900/50 text-blue-200 text-xs flex items-center gap-1 border border-blue-700/50"><ShieldCheck className="w-3 h-3"/> Indexed</span>}
                  <span className="px-2.5 py-1 rounded bg-gray-700/50 text-gray-300 text-xs border border-gray-600/50 font-mono">#{profile.person.person_id}</span>
                </div>
              </div>
            </div>
          ) : null}

          {/* Tabs */}
          {profile && (
            <div className="flex space-x-4 sm:space-x-8 mt-2 overflow-x-auto no-scrollbar border-t border-gray-600/40 sm:border-t-0" role="tablist" aria-label="Profile Sections">
              {['Facts', 'Gallery', 'LifeStory'].map(tab => (
                <button
                  key={tab}
                  role="tab"
                  aria-selected={activeTab === tab.toLowerCase()}
                  onClick={() => setActiveTab(tab.toLowerCase())}
                  className={`py-3 px-2 sm:px-1 min-h-[44px] border-b-4 transition-colors font-semibold text-sm cursor-pointer whitespace-nowrap ${
                    activeTab === tab.toLowerCase() ? 'border-[#8eb19d] text-white' : 'border-transparent text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area (Light) */}
      {!loading && profile && (
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
          
          {activeTab === 'facts' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
              
              {/* Left Column - Timeline */}
              <div className="lg:col-span-3">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
                  <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 className="font-bold text-gray-800">Timeline</h2>
                  </div>
                  <div className="p-4">
                    <div className="relative border-l-2 border-gray-200 ml-4 space-y-6">
                      {timelineEvents.map((evt, idx) => (
                        <div key={idx} className="relative pl-6">
                          {evt.isMajor ? (
                            <div className="absolute -left-[11px] top-1 w-5 h-5 bg-white rounded-full border-4 border-gray-400" />
                          ) : (
                            <div className="absolute -left-1.5 top-2 w-2.5 h-2.5 bg-gray-400 rounded-full" />
                          )}
                          <div className="flex gap-4">
                            <div className="w-10 pt-1 shrink-0">
                              <span className="text-xs font-bold text-gray-500">{evt.year}</span>
                            </div>
                            <div className="flex-1">
                              <span className="font-semibold text-gray-800 block">{evt.type}</span>
                              {(evt.date || evt.place) && (
                                <p className="text-sm text-gray-600 mt-0.5">
                                  {evt.date} {evt.place && <span className="block">{evt.place}</span>}
                                </p>
                              )}
                              {evt.description && <p className="text-sm text-gray-600 mt-0.5">{evt.description}</p>}
                              {evt.photo && (
                                <img 
                                  src={evt.photo.local_image_path.startsWith('/') ? evt.photo.local_image_path : '/' + evt.photo.local_image_path} 
                                  alt={evt.description || "Preserved timeline record"} 
                                  className="mt-2 w-16 h-16 object-cover rounded border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity" 
                                  onClick={() => setLightboxPhoto(evt.photo)} 
                                />
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                      {timelineEvents.length === 0 && <p className="text-sm text-gray-500 ml-4">No events found.</p>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Middle Column - Sources */}
              <div className="lg:col-span-5 space-y-6">
                
                {/* Audit Flags injected here if any */}
                {profile.audit_flags && profile.audit_flags.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 shadow-sm">
                    <h3 className="font-bold text-yellow-800 text-sm mb-2 flex items-center gap-2"><ShieldCheck className="w-4 h-4"/> Quality Flags</h3>
                    <div className="space-y-2">
                      {profile.audit_flags.map((flag, idx) => (
                        <p key={idx} className="text-xs text-yellow-700 leading-snug"><strong>{flag.category}:</strong> {flag.description}</p>
                      ))}
                    </div>
                  </div>
                )}

                <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
                  <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 className="font-bold text-gray-800 flex items-center gap-2"><FileText className="w-5 h-5 text-gray-400"/> Archive Sources</h2>
                    <span className="text-xs font-bold bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{profile.facts?.length || 0}</span>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {(!profile.facts || profile.facts.length === 0) ? (
                      <div className="p-6 text-center text-gray-500 text-sm">No documented facts available.</div>
                    ) : (
                      profile.facts.map((fact, idx) => (
                        <div key={idx} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-sm font-semibold text-blue-700">{fact.fact_type}</span>
                            {(fact.date_string || fact.place_string) && (
                              <span className="text-xs text-gray-500">{fact.date_string} {fact.place_string}</span>
                            )}
                          </div>
                          {fact.value_string && <p className="text-sm text-gray-800 mb-2">{fact.value_string}</p>}
                          
                          {fact.citations && fact.citations.map((cit, cIdx) => (
                            <div key={cIdx} className="mt-2 pl-3 border-l-2 border-gray-200">
                              {cit.source_url && cit.source_url !== '#' ? (
                                <a 
                                  href={cit.source_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className="text-xs font-semibold text-blue-700 hover:text-blue-900 hover:underline inline-flex items-center gap-1"
                                >
                                  {cit.source_title || 'Archival Document'} <ExternalLink className="w-3 h-3"/>
                                </a>
                              ) : (
                                <span className="text-xs font-semibold text-gray-700 inline-flex items-center gap-1">
                                  {cit.source_title || 'Archival Document'}
                                </span>
                              )}
                              {cit.evidence_text && <p className="text-xs text-gray-500 mt-1 italic">"{cit.evidence_text}"</p>}
                            </div>
                          ))}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column - Relationships */}
              <div className="lg:col-span-4 space-y-6">
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50">
                    <h2 className="font-bold text-gray-800 flex items-center gap-2"><Users className="w-5 h-5 text-gray-400"/> Family</h2>
                  </div>
                  
                  {/* Parents */}
                  <div className="p-4 border-b border-gray-100">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Parents</h3>
                    {parents.length > 0 ? parents.map((rel, i) => (
                      <button 
                        key={i} 
                        type="button"
                        onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)} 
                        disabled={!rel.rel_id}
                        className={`w-full flex items-center gap-3 mb-2 p-2 -mx-2 rounded text-left transition-colors ${
                          rel.rel_id ? 'hover:bg-gray-100 cursor-pointer' : 'cursor-default opacity-75'
                        }`}
                        title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                      >
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 shrink-0"><User className="w-4 h-4"/></div>
                        <div className="min-w-0">
                          <p className={`text-sm font-semibold truncate ${rel.rel_id ? 'text-blue-700 hover:underline' : 'text-gray-800'}`}>{rel.rel_name}</p>
                        </div>
                      </button>
                    )) : <p className="text-sm text-gray-400 italic">Unknown</p>}
                  </div>

                  {/* Spouses */}
                  <div className="p-4 border-b border-gray-100">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Spouse</h3>
                    {spouses.length > 0 ? spouses.map((rel, i) => (
                      <button 
                        key={i} 
                        type="button"
                        onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)} 
                        disabled={!rel.rel_id}
                        className={`w-full flex items-center gap-3 mb-2 p-2 -mx-2 rounded text-left transition-colors ${
                          rel.rel_id ? 'hover:bg-gray-100 cursor-pointer' : 'cursor-default opacity-75'
                        }`}
                        title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                      >
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 shrink-0"><User className="w-4 h-4"/></div>
                        <div className="min-w-0">
                          <p className={`text-sm font-semibold truncate ${rel.rel_id ? 'text-blue-700 hover:underline' : 'text-gray-800'}`}>{rel.rel_name}</p>
                        </div>
                      </button>
                    )) : <p className="text-sm text-gray-400 italic">Unknown</p>}
                  </div>

                  {/* Siblings */}
                  <div className="p-4 border-b border-gray-100">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Siblings</h3>
                    {siblings.length > 0 ? siblings.map((rel, i) => (
                      <button 
                        key={i} 
                        type="button"
                        onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)} 
                        disabled={!rel.rel_id}
                        className={`w-full flex items-center gap-3 mb-2 p-2 -mx-2 rounded text-left transition-colors ${
                          rel.rel_id ? 'hover:bg-gray-100 cursor-pointer' : 'cursor-default opacity-75'
                        }`}
                        title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                      >
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 shrink-0"><User className="w-4 h-4"/></div>
                        <div className="min-w-0">
                          <p className={`text-sm font-semibold truncate ${rel.rel_id ? 'text-blue-700 hover:underline' : 'text-gray-800'}`}>{rel.rel_name}</p>
                        </div>
                      </button>
                    )) : <p className="text-sm text-gray-400 italic">Unknown</p>}
                  </div>

                  {/* Children */}
                  <div className="p-4">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Children</h3>
                    {children.length > 0 ? children.map((rel, i) => (
                      <button 
                        key={i} 
                        type="button"
                        onClick={() => onSelectPerson && rel.rel_id && onSelectPerson(rel.rel_id)} 
                        disabled={!rel.rel_id}
                        className={`w-full flex items-center gap-3 mb-2 p-2 -mx-2 rounded text-left transition-colors ${
                          rel.rel_id ? 'hover:bg-gray-100 cursor-pointer' : 'cursor-default opacity-75'
                        }`}
                        title={rel.rel_id ? `View ${rel.rel_name}` : undefined}
                      >
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 shrink-0"><User className="w-4 h-4"/></div>
                        <div className="min-w-0">
                          <p className={`text-sm font-semibold truncate ${rel.rel_id ? 'text-blue-700 hover:underline' : 'text-gray-800'}`}>{rel.rel_name}</p>
                        </div>
                      </button>
                    )) : <p className="text-sm text-gray-400 italic">Unknown</p>}
                  </div>
                </div>

              </div>

            </div>
          )}

          {activeTab === 'gallery' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <h2 className="font-serif text-3xl text-gray-800 mb-6 flex items-center gap-3">
                Media Gallery <span className="text-sm font-sans bg-gray-100 text-gray-600 px-3 py-1 rounded-full">{(profile.photos || []).length}</span>
              </h2>
              {(!profile.photos || profile.photos.length === 0) ? (
                <div className="text-center py-12"><Camera className="w-12 h-12 text-gray-300 mx-auto mb-4"/><p className="text-gray-500">No media preserved for this person.</p></div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {profile.photos.map(photo => (
                    <div key={photo.photo_id} onClick={() => setLightboxPhoto(photo)} className="group relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer shadow-sm hover:shadow-md hover:ring-2 hover:ring-blue-400 transition-all">
                      <img 
                        src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path} 
                        alt={photo.subject_names || "Preserved family photograph"} 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
                        loading="lazy" 
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'lifestory' && (
            <div className="max-w-4xl mx-auto">
              <NarrativeBioGenerator person={profile.person} onSelectPerson={onSelectPerson} />
            </div>
          )}

        </main>
      )}

      {/* Lightbox Portal */}
      {lightboxPhoto && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] bg-black/95 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 md:p-8" onClick={() => setLightboxPhoto(null)}>
          <button 
            onClick={() => setLightboxPhoto(null)} 
            className="absolute top-4 right-4 sm:top-6 sm:right-6 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 p-2.5 rounded-full transition-all z-[10000] min-w-[44px] min-h-[44px] flex items-center justify-center" 
            aria-label="Close media preview"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="relative max-w-6xl w-full max-h-[92vh] flex flex-col lg:flex-row bg-[#141210] border border-gray-800 rounded-2xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex-1 bg-black flex items-center justify-center p-2 sm:p-4 min-h-[30vh]">
              <img 
                src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path} 
                alt={lightboxPhoto.subject_names || "High-resolution archival record"} 
                className="max-w-full max-h-[45vh] lg:max-h-[75vh] object-contain rounded-lg" 
              />
            </div>
            <div className="w-full lg:w-96 bg-gray-900 border-t lg:border-t-0 lg:border-l border-gray-800 p-5 sm:p-6 lg:p-8 flex flex-col overflow-y-auto text-white">
              <h3 className="font-serif text-xl sm:text-2xl mb-3 sm:mb-4 leading-tight">{lightboxPhoto.subject_names || 'Archival Record'}</h3>
              <div className="space-y-3 sm:space-y-4 text-xs sm:text-sm">
                {lightboxPhoto.date_text && <div><span className="text-gray-500 uppercase text-[11px] font-bold block mb-0.5">Est. Date</span>{lightboxPhoto.date_text}</div>}
                {lightboxPhoto.description && <div><span className="text-gray-500 uppercase text-[11px] font-bold block mb-0.5">Description</span>{lightboxPhoto.description}</div>}
                {lightboxPhoto.source_collection && <div><span className="text-gray-500 uppercase text-[11px] font-bold block mb-0.5">Collection</span>{lightboxPhoto.source_collection}</div>}
                {lightboxPhoto.original_source_url && (
                  <div className="pt-4 sm:pt-6 mt-4 sm:mt-6 border-t border-gray-800">
                    <a 
                      href={lightboxPhoto.original_source_url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="inline-flex items-center gap-2 font-bold text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4"/> View Original Archival Source
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Citation Modal */}
      <CitationModal isOpen={isCitationOpen} onClose={() => setIsCitationOpen(false)} data={profile} type="person" />
    </div>
  );
}
