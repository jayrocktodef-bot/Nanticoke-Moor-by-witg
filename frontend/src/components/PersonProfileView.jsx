import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { User, Users, Camera, HeartHandshake, FileText, ExternalLink, Calendar, GitBranch, ArrowLeft, ShieldCheck, MapPin, X } from 'lucide-react';
import FanChart from './FanChart';

export default function PersonProfileView({ personId, onClose, onSelectPerson }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);

  useEffect(() => {
    if (!personId) return;
    setLoading(true);
    fetch(`/api/person/${personId}.json`)
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));

    // Disable body scroll when modal is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [personId]);

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

  if (!personId) return null;

  // Helpers for extracting events from relationships/evidence
  const primaryPhoto = profile?.photos?.[0];
  
  // Categorize relationships
  const parents = profile?.relationships?.filter(r => r.relationship_type === 'child_of') || [];
  const spouses = profile?.relationships?.filter(r => r.relationship_type === 'spouse_of') || [];
  // For children, we'd need inverse relationships which might not be readily available in the person JSON
  // Let's rely on relationships present
  const otherRels = profile?.relationships?.filter(r => !['child_of', 'spouse_of'].includes(r.relationship_type)) || [];

  return (
    <div className="fixed inset-0 z-50 bg-[#0F0E0D] text-[#E5E1DB] overflow-y-auto custom-scrollbar animate-fade-in flex flex-col font-sans">
      {/* Top Nav Bar */}
      <div className="sticky top-0 z-40 bg-[#141210]/95 backdrop-blur-md border-b border-[#26221E] px-4 py-3 flex items-center justify-between shadow-md">
        <button
          onClick={onClose}
          className="flex items-center gap-2 text-[#A8A096] hover:text-[#C68B59] transition-colors font-medium text-sm"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Directory
        </button>
        <div className="flex items-center gap-3">
          <button onClick={onClose} className="p-2 rounded-lg bg-[#1C1A17] border border-[#332D27] text-[#A8A096] hover:text-[#F3EBE3]">✕</button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center text-[#A8A096] min-h-[50vh]">
          <div className="w-8 h-8 border-2 border-[#C68B59]/30 border-t-[#C68B59] rounded-full animate-spin mb-4" />
          <p className="font-mono text-xs tracking-wider uppercase">Loading Archive Record...</p>
        </div>
      ) : profile ? (
        <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          
          {/* HERO DOSSIER HEADER */}
          <div className="relative overflow-hidden rounded-2xl bg-[#1C1A17] border border-[#332D27] p-6 sm:p-10 shadow-2xl mb-8 group flex flex-col sm:flex-row gap-6 sm:gap-10 items-start sm:items-center">
            <div className="absolute inset-0 bg-gradient-to-br from-[#C68B59]/5 to-transparent opacity-50 pointer-events-none" />
            
            {/* Avatar / Primary Photo */}
            <div className="relative shrink-0">
              {primaryPhoto ? (
                <img 
                  src={primaryPhoto.local_image_path.startsWith('/') ? primaryPhoto.local_image_path : '/' + primaryPhoto.local_image_path}
                  alt={profile.person.name}
                  className="w-32 h-32 sm:w-48 sm:h-48 rounded-full object-cover border-4 border-[#141210] shadow-xl shadow-black/50"
                />
              ) : (
                <div className="w-32 h-32 sm:w-48 sm:h-48 rounded-full bg-[#141210] border-4 border-[#26221E] shadow-xl flex items-center justify-center">
                  <User className="w-16 h-16 text-[#332D27]" />
                </div>
              )}
              {/* Evidence Level Badge */}
              <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap">
                {profile.person.evidence_level === 4 && <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-violet-900/80 text-violet-300 border border-violet-700 shadow-md flex items-center gap-1"><ShieldCheck className="w-3 h-3"/> DNA Verified</span>}
                {profile.person.evidence_level === 3 && <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-emerald-900/80 text-emerald-300 border border-emerald-700 shadow-md flex items-center gap-1"><ShieldCheck className="w-3 h-3"/> Primary Source</span>}
                {profile.person.evidence_level === 2 && <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-[#C68B59]/20 text-[#D4A373] border border-[#C68B59]/40 shadow-md flex items-center gap-1"><ShieldCheck className="w-3 h-3"/> Indexed</span>}
                {(profile.person.evidence_level === 1 || !profile.person.evidence_level) && <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-[#26221E] text-[#A8A096] border border-[#332D27] shadow-md">Unverified</span>}
              </div>
            </div>

            {/* Name and Meta */}
            <div className="flex-1 z-10">
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#D4A373] bg-[#C68B59]/10 border border-[#C68B59]/30 px-2.5 py-1 rounded-md">
                  Archive ID: #{profile.person.person_id}
                </span>
                <span className="text-[10px] font-mono uppercase tracking-widest text-[#8C8275] bg-[#141210] border border-[#26221E] px-2 py-1 rounded-md">
                  Source: {profile.person.dataset_source}
                </span>
              </div>
              
              <h1 className="font-serif-header text-4xl sm:text-5xl md:text-6xl text-[#F3EBE3] tracking-tight leading-none mb-3">
                {profile.person.first_name || profile.person.name} <span className="text-[#A8A096]">{profile.person.middle_name}</span> <span className="font-bold">{profile.person.married_last_name || profile.person.last_name}</span>
              </h1>
              {profile.person.maiden_name && (
                <p className="font-serif-header text-xl text-[#C68B59] italic mb-4">née {profile.person.maiden_name}</p>
              )}

              {profile.person.notes && (
                <p className="text-sm text-[#A8A096] max-w-3xl leading-relaxed mt-4 border-l-2 border-[#332D27] pl-4">
                  {profile.person.notes}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
            
            {/* LEFT RAIL: QUICK FACTS & CHART */}
            <aside className="lg:col-span-4 space-y-8">
              
              {/* Fan Chart Summary */}
              <section className="bg-[#1C1A17] border border-[#332D27] rounded-2xl p-5 shadow-lg">
                <h2 className="text-xs font-bold text-[#A8A096] uppercase tracking-widest mb-4 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-[#C68B59]" />
                  Ancestry Fan View
                </h2>
                <div className="bg-[#141210] rounded-xl border border-[#26221E] p-1">
                  <FanChart ancestryData={profile.ancestry} onSelectPerson={onSelectPerson} />
                </div>
              </section>

              {/* Data Quality & Audits */}
              {profile.audit_flags && profile.audit_flags.length > 0 && (
                <section className="bg-[#1C1A17] border border-[#332D27] rounded-2xl p-5 shadow-lg">
                  <h2 className="text-xs font-bold text-[#A8A096] uppercase tracking-widest mb-4 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-orange-400" />
                    Data Quality Flags
                  </h2>
                  <div className="space-y-3">
                    {profile.audit_flags.map((flag, idx) => (
                      <div key={idx} className={`p-3 rounded-lg border text-xs leading-relaxed ${flag.severity === 'critical' ? 'bg-red-900/20 border-red-900/50 text-red-300' : 'bg-orange-900/20 border-orange-900/50 text-orange-300'}`}>
                        <strong className="block mb-1 font-bold tracking-wide uppercase text-[10px]">{flag.category} Warning</strong>
                        {flag.description}
                      </div>
                    ))}
                  </div>
                </section>
              )}
              
            </aside>

            {/* MAIN CONTENT: TIMELINE, CONNECTIONS, MEDIA */}
            <main className="lg:col-span-8 space-y-12">
              
              {/* Life Events Timeline */}
              <section>
                <h2 className="font-serif-header text-3xl text-[#F3EBE3] border-b border-[#26221E] pb-4 mb-6 flex items-center gap-3">
                  <Calendar className="w-6 h-6 text-[#C68B59]" />
                  Life Events
                </h2>
                
                <div className="relative border-l border-[#332D27] ml-3 space-y-6">
                  {/* Birth Event */}
                  {(profile.person.birth_date || profile.person.birth_place) ? (
                    <div className="relative pl-8">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 bg-[#C68B59] rounded-full shadow-[0_0_10px_rgba(198,139,89,0.5)] border-2 border-[#1C1A17]" />
                      <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-4 shadow-sm hover:border-[#C68B59]/50 transition-colors">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-[#D4A373] bg-[#C68B59]/10 px-2 py-0.5 rounded mb-2 inline-block">Birth</span>
                        <p className="font-serif-header text-xl text-[#F3EBE3]">{profile.person.birth_date || 'Unknown Date'}</p>
                        {profile.person.birth_place && <p className="text-sm text-[#A8A096] mt-1 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5"/> {profile.person.birth_place}</p>}
                      </div>
                    </div>
                  ) : null}

                  {/* Interleaved Photo Events (Synthesized Timeline) */}
                  {profile.photos.filter(p => p.date_text).slice(0,3).map((photo, i) => (
                     <div key={`timeline-photo-${i}`} className="relative pl-8">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 bg-[#332D27] rounded-full border-2 border-[#1C1A17]" />
                      <div className="bg-[#141210] border border-[#26221E] rounded-xl p-4 shadow-sm flex items-start gap-4">
                        <img src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path} alt="" className="w-16 h-16 object-cover rounded-lg border border-[#332D27] shrink-0" />
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-widest text-[#8C8275] bg-[#1C1A17] px-2 py-0.5 rounded mb-1 inline-block">{photo.date_text}</span>
                          <p className="text-sm text-[#F3EBE3] line-clamp-2">{photo.subject_names}</p>
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Death Event */}
                  {(profile.person.death_date || profile.person.death_place) ? (
                    <div className="relative pl-8">
                      <div className="absolute -left-1.5 top-1 w-3 h-3 bg-slate-600 rounded-full border-2 border-[#1C1A17]" />
                      <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-4 shadow-sm hover:border-slate-500/50 transition-colors">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 bg-slate-800 px-2 py-0.5 rounded mb-2 inline-block">Death</span>
                        <p className="font-serif-header text-xl text-[#F3EBE3]">{profile.person.death_date || 'Unknown Date'}</p>
                        {profile.person.death_place && <p className="text-sm text-[#A8A096] mt-1 flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5"/> {profile.person.death_place}</p>}
                      </div>
                    </div>
                  ) : null}

                  {/* Empty state if nothing */}
                  {!(profile.person.birth_date || profile.person.birth_place || profile.person.death_date || profile.person.death_place || profile.photos.some(p => p.date_text)) && (
                    <div className="pl-8 text-sm text-[#A8A096] italic">No timeline events extracted.</div>
                  )}
                </div>
              </section>

              {/* Family Connections Directory */}
              <section>
                <h2 className="font-serif-header text-3xl text-[#F3EBE3] border-b border-[#26221E] pb-4 mb-6">Family Connections</h2>
                
                {profile.relationships.length === 0 ? (
                  <div className="bg-[#1C1A17] border border-[#332D27] rounded-2xl p-8 text-center">
                    <Users className="w-8 h-8 text-[#332D27] mx-auto mb-3" />
                    <p className="text-[#A8A096] italic text-sm">No family connections found in the preservation index.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {profile.relationships.map((rel, idx) => (
                      <button
                        key={idx}
                        onClick={() => onSelectPerson && onSelectPerson(rel.rel_id)}
                        className="group flex flex-col p-4 bg-[#1C1A17] border border-[#332D27] rounded-xl hover:border-[#C68B59] hover:bg-[#26221E] transition-all text-left"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-[#D4A373] bg-[#C68B59]/10 px-2 py-0.5 rounded">
                            {rel.relationship_type.replace(/_/g, ' ')}
                          </span>
                          {rel.certainty === 'uncertain' && (
                            <span className="text-[9px] uppercase font-bold text-red-400 bg-red-900/30 px-1.5 py-0.5 rounded">Uncertain</span>
                          )}
                        </div>
                        <span className="font-serif-header text-lg text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors line-clamp-1">
                          {rel.rel_name}
                        </span>
                        {rel.evidence_text && (
                          <span className="text-xs text-[#8C8275] mt-2 line-clamp-2 italic border-l-2 border-[#332D27] pl-2">
                            "{rel.evidence_text}"
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </section>

              {/* FACTS & EVIDENCE CITATIONS SECTION */}
              <section className="mb-12">
                <h2 className="font-serif-header text-2xl text-[#F3EBE3] mb-6 flex items-center justify-between border-b border-[#26221E] pb-3">
                  Documented Facts & Source Citations
                  <span className="text-sm font-sans font-bold text-[#A8A096] bg-[#1C1A17] px-3 py-1 rounded-full border border-[#332D27]">
                    {profile.facts ? profile.facts.length : 0} Facts
                  </span>
                </h2>

                {(!profile.facts || profile.facts.length === 0) ? (
                  <div className="bg-[#1C1A17] border border-[#332D27] rounded-2xl p-6 text-center">
                    <FileText className="w-8 h-8 text-[#332D27] mx-auto mb-2" />
                    <p className="text-[#A8A096] italic text-sm">No discrete evidence facts indexed for this profile.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {profile.facts.map((fact, idx) => (
                      <div key={idx} className="bg-[#1C1A17] border border-[#26221E] rounded-xl p-5 shadow-sm hover:border-[#332D27] transition-all">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#D4A373] bg-[#C68B59]/10 px-2.5 py-0.5 rounded-md border border-[#C68B59]/20">
                            {fact.fact_type}
                          </span>
                          {(fact.date_string || fact.place_string) && (
                            <span className="text-xs text-[#A8A096] flex items-center gap-1 font-mono">
                              <Calendar className="w-3.5 h-3.5" />
                              {fact.date_string || 'Unspecified Date'} {fact.place_string ? `• ${fact.place_string}` : ''}
                            </span>
                          )}
                        </div>
                        {fact.value_string && (
                          <p className="text-[#F3EBE3] font-medium text-base mb-3">{fact.value_string}</p>
                        )}
                        {/* Citations list for this fact */}
                        {fact.citations && fact.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-[#26221E]/80 space-y-2">
                            <span className="text-[10px] font-mono uppercase tracking-widest text-[#8C8275] font-bold block">
                              Source Citations ({fact.citations.length})
                            </span>
                            {fact.citations.map((cit, cIdx) => (
                              <div key={cIdx} className="bg-[#141210] rounded-lg p-3 border border-[#26221E] text-xs flex flex-col gap-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-[#E5E1DB] flex items-center gap-1.5">
                                    <FileText className="w-3.5 h-3.5 text-[#C68B59]" />
                                    {cit.source_title || 'Archival Record'}
                                  </span>
                                  {cit.source_url && (
                                    <a 
                                      href={cit.source_url} 
                                      target="_blank" 
                                      rel="noreferrer" 
                                      className="text-[#C68B59] hover:underline flex items-center gap-1 text-[11px]"
                                    >
                                      View Document <ExternalLink className="w-3 h-3" />
                                    </a>
                                  )}
                                </div>
                                {cit.evidence_text && (
                                  <p className="text-[#A8A096] italic text-[11px] mt-1 bg-[#1C1A17] p-2 rounded border border-[#26221E]">
                                    "{cit.evidence_text}"
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Media Archive */}
              <section>
                <h2 className="font-serif-header text-3xl text-[#F3EBE3] border-b border-[#26221E] pb-4 mb-6 flex items-center gap-3">
                  Media Archive
                  <span className="text-sm font-sans font-bold text-[#A8A096] bg-[#1C1A17] px-3 py-1 rounded-full border border-[#332D27]">{profile.photos.length}</span>
                </h2>
                
                {profile.photos.length === 0 ? (
                  <div className="bg-[#1C1A17] border border-[#332D27] rounded-2xl p-8 text-center">
                    <Camera className="w-8 h-8 text-[#332D27] mx-auto mb-3" />
                    <p className="text-[#A8A096] italic text-sm">No digitized media preserved for this individual.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {profile.photos.map(photo => (
                      <div
                        key={photo.photo_id}
                        onClick={() => setLightboxPhoto(photo)}
                        className="group relative aspect-square bg-[#141210] border border-[#26221E] rounded-xl overflow-hidden cursor-pointer shadow-md hover:shadow-xl hover:border-[#C68B59]/50 transition-all"
                      >
                        <img
                          src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path}
                          alt={photo.subject_names}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                          loading="lazy"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4">
                          <p className="text-xs font-medium text-white line-clamp-2 leading-tight">
                            {photo.subject_names || 'Untitled Record'}
                          </p>
                          {photo.date_text && <p className="text-[10px] text-[#A8A096] mt-1">{photo.date_text}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

            </main>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-[#A8A096]">
          <p>Profile not found or an error occurred.</p>
        </div>
      )}

      {/* LIGHTBOX FOR PHOTOS rendered via Portal in document.body */}
      {lightboxPhoto && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[9999] bg-black/95 backdrop-blur-md flex items-center justify-center p-4 sm:p-8"
          onClick={() => setLightboxPhoto(null)}
          role="dialog"
          aria-modal="true"
        >
          <button 
            onClick={() => setLightboxPhoto(null)}
            className="absolute top-6 right-6 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 p-2.5 rounded-full backdrop-blur-md transition-all z-[10000]"
            aria-label="Close photo preview"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="relative max-w-6xl w-full max-h-[92vh] flex flex-col lg:flex-row bg-[#141210] border border-[#26221E] rounded-2xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex-1 bg-black flex items-center justify-center p-4 min-h-[40vh]">
              <img
                src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                alt={lightboxPhoto.subject_names || 'Archival Photograph'}
                className="max-w-full max-h-[75vh] object-contain rounded-lg"
              />
            </div>
            <div className="w-full lg:w-96 bg-[#1C1A17] border-l border-[#26221E] p-6 lg:p-8 flex flex-col overflow-y-auto">
              <h3 className="font-serif-header text-2xl text-white mb-4 leading-tight">{lightboxPhoto.subject_names || 'Archival Record'}</h3>
              <div className="space-y-4">
                {lightboxPhoto.date_text && (
                  <div>
                    <label className="text-[10px] uppercase font-bold tracking-widest text-[#8C8275]">Est. Date</label>
                    <p className="text-sm text-[#F3EBE3]">{lightboxPhoto.date_text}</p>
                  </div>
                )}
                {lightboxPhoto.description && (
                  <div>
                    <label className="text-[10px] uppercase font-bold tracking-widest text-[#8C8275]">Description</label>
                    <p className="text-sm text-[#F3EBE3] leading-relaxed mt-1">{lightboxPhoto.description}</p>
                  </div>
                )}
                {lightboxPhoto.source_collection && (
                  <div>
                    <label className="text-[10px] uppercase font-bold tracking-widest text-[#8C8275]">Source Collection</label>
                    <p className="text-xs text-[#D4A373] mt-1 bg-[#C68B59]/10 px-2 py-1.5 rounded inline-block border border-[#C68B59]/20">{lightboxPhoto.source_collection}</p>
                  </div>
                )}
                <div className="pt-6 mt-6 border-t border-[#332D27]">
                  <a 
                    href={lightboxPhoto.original_source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs font-bold text-[#A8A096] hover:text-white transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" /> View Original Source
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
