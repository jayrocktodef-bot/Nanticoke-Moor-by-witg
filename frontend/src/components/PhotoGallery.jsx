import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Camera, Users, ChevronRight, ArrowLeft, Calendar, ExternalLink, Play, Square, Sparkles, X } from 'lucide-react';

export default function PhotoGallery() {
  const [surnameCounts, setSurnameCounts] = useState([]);
  const [selectedSurname, setSelectedSurname] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [categoryTab, setCategoryTab] = useState('all'); // 'all', 'people', 'documents', 'family_trees', 'tombstones'
  const [isStoryMode, setIsStoryMode] = useState(false);
  const [storyIndex, setStoryIndex] = useState(0);

  // Lock background scroll and handle Escape key when lightbox is open
  useEffect(() => {
    if (!lightboxPhoto) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setLightboxPhoto(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [lightboxPhoto]);

  const matchCategory = (p, tab) => {
    if (!tab || tab === 'all') return true;
    if (p.category) return p.category === tab;
    // Fallbacks
    if (tab === 'family_trees') {
      const path = (p.local_image_path || '').toLowerCase();
      const title = (p.title_or_caption || '').toLowerCase();
      return path.includes('ancestry') || path.includes('tree') || title.includes('ancestry') || title.includes('tree');
    }
    if (tab === 'tombstones') {
      const path = (p.local_image_path || '').toLowerCase();
      return path.includes('tombstone') || path.includes('cemetery') || p.document_type === 'tombstone';
    }
    if (tab === 'documents') {
      const path = (p.local_image_path || '').toLowerCase();
      return path.includes('certificate') || path.includes('census') || path.includes('will') || path.includes('deed');
    }
    if (tab === 'people') {
      return !matchCategory(p, 'family_trees') && !matchCategory(p, 'tombstones') && !matchCategory(p, 'documents');
    }
    return true;
  };

  useEffect(() => {
    fetch('/api/surnames.json')
      .then(r => r.json())
      .then(data => {
        const countsArr = data
          .filter(s => s.photo_count > 0)
          .map(s => ({
            surname: s.surname,
            photo_count: s.photo_count,
            category_counts: s.category_counts
          }));
        setSurnameCounts(countsArr);
      })
      .catch(() => {
        fetch('/api/photos.json')
          .then(r => r.json())
          .then(data => {
            const countsMap = {};
            data.forEach(p => {
              const s = p.married_surname || p.maiden_name;
              if (s && s.length > 1) {
                countsMap[s] = (countsMap[s] || 0) + 1;
              }
            });
            const countsArr = Object.entries(countsMap).map(([surname, photo_count]) => ({ surname, photo_count }));
            countsArr.sort((a, b) => a.surname.localeCompare(b.surname));
            setSurnameCounts(countsArr);
          });
      });
  }, []);

  const handleSelectSurname = (surname) => {
    setSelectedSurname(surname);
    setLoading(true);
    fetch(`/api/surnames/${surname}.json`)
      .then(r => r.json())
      .then(data => {
        let list = data.photos || [];
        if (categoryTab !== 'all') {
          list = list.filter(p => matchCategory(p, categoryTab));
        }
        setPhotos(list);
        setLoading(false);
      })
      .catch(() => {
        fetch('/api/photos.json')
          .then(r => r.json())
          .then(data => {
            const lowerS = surname.toLowerCase();
            let filtered = data.filter(p => 
              p.maiden_name?.toLowerCase().includes(lowerS) ||
              p.married_surname?.toLowerCase().includes(lowerS) ||
              p.subject_names?.toLowerCase().includes(lowerS) ||
              p.title_or_caption?.toLowerCase().includes(lowerS)
            );
            if (categoryTab !== 'all') {
              filtered = filtered.filter(p => matchCategory(p, categoryTab));
            }
            setPhotos(filtered);
            setLoading(false);
          });
      });
  };

  const handleShowAll = (tabOverride) => {
    const tab = tabOverride !== undefined ? tabOverride : categoryTab;
    setSelectedSurname(null);
    setLoading(true);
    fetch('/api/photos.json')
      .then(r => r.json())
      .then(data => {
        let filtered = data;
        if (tab !== 'all') {
          filtered = data.filter(p => matchCategory(p, tab));
        }
        setPhotos(filtered);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  // Automatic Story Mode Interval
  useEffect(() => {
    let timer;
    if (isStoryMode && photos.length > 0) {
      timer = setInterval(() => {
        setStoryIndex(prev => (prev + 1) % photos.length);
      }, 5000);
    }
    return () => clearInterval(timer);
  }, [isStoryMode, photos]);

  const PORTAL_COLORS = [
    { from: 'from-[#C87D53]/20', to: 'to-[#171E27]/40', border: 'border-[#C87D53]/40', accent: 'text-[#D4A373]' },
    { from: 'from-[#1B3B2B]/40', to: 'to-[#171E27]/40', border: 'border-[#1B3B2B]', accent: 'text-[#E5B269]' },
    { from: 'from-[#2A3644]/40', to: 'to-[#171E27]/40', border: 'border-[#2A3644]', accent: 'text-[#F3EBE3]' }
  ];

  // Surname Portal Grid View
  if (!selectedSurname && photos.length === 0) {
    const topSurnames = surnameCounts.filter(s => s.photo_count >= 2).slice(0, 40);
    const otherSurnames = surnameCounts.filter(s => s.photo_count === 1);

    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#2A3644] pb-4">
          <div>
            <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3] tracking-tight mb-1">
              Historical Photo & Document Archive
            </h2>
            <p className="text-xs text-[#9EA9B6]">
              {surnameCounts.length} surname groups • {surnameCounts.reduce((a, s) => a + s.photo_count, 0)} historical photographs cataloged
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 bg-[#171E27] border border-[#2A3644] p-1.5 rounded-2xl text-xs">
            <button
              onClick={() => {
                setCategoryTab('all');
                handleShowAll('all');
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all ${
                categoryTab === 'all'
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md'
                  : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
              }`}
            >
              All Media
            </button>
            <button
              onClick={() => {
                setCategoryTab('people');
                handleShowAll('people');
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all ${
                categoryTab === 'people'
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md'
                  : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
              }`}
            >
              👥 People
            </button>
            <button
              onClick={() => {
                setCategoryTab('documents');
                handleShowAll('documents');
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all ${
                categoryTab === 'documents'
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md'
                  : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
              }`}
            >
              📜 Documents
            </button>
            <button
              onClick={() => {
                setCategoryTab('family_trees');
                handleShowAll('family_trees');
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all ${
                categoryTab === 'family_trees'
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md'
                  : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
              }`}
            >
              🌳 Trees
            </button>
            <button
              onClick={() => {
                setCategoryTab('tombstones');
                handleShowAll('tombstones');
              }}
              className={`px-3.5 py-1.5 rounded-xl font-semibold transition-all ${
                categoryTab === 'tombstones'
                  ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow-md'
                  : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
              }`}
            >
              🪦 Tombstones
            </button>
          </div>

          <button
            onClick={handleShowAll}
            className="text-xs bg-[#171E27] border border-[#2A3644] hover:border-[#C87D53] text-[#D4A373] px-4 py-2 rounded-xl transition-all flex items-center gap-2 font-mono"
          >
            <Camera className="w-3.5 h-3.5 text-[#C87D53]" />
            Browse All Photos
          </button>
        </div>

        {/* Featured Surname Portals */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {topSurnames.map((s, idx) => {
            const color = PORTAL_COLORS[idx % PORTAL_COLORS.length];
            return (
              <button
                key={s.surname}
                onClick={() => handleSelectSurname(s.surname)}
                className={`group relative glass-panel glass-card-hover rounded-2xl p-5 text-left transition-all active:scale-[0.98] overflow-hidden`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-bold font-serif-header text-[#F3EBE3] tracking-tight">{s.surname}</h3>
                    <div className="flex items-center gap-2 mt-2 font-mono">
                      <Camera className={`w-3.5 h-3.5 ${color.accent}`} />
                      <span className="text-xs text-[#9EA9B6]">
                        <strong className="text-[#F3EBE3]">{s.photo_count}</strong> cataloged
                      </span>
                    </div>
                  </div>
                  <ChevronRight className={`w-5 h-5 ${color.accent} opacity-40 group-hover:opacity-100 transition-opacity`} />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // Photo Grid View with Ken Burns Story Mode Slideshow
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#2A3644] pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setSelectedSurname(null); setPhotos([]); setIsStoryMode(false); }}
            className="p-2 bg-[#171E27] border border-[#2A3644] hover:border-[#C87D53] rounded-xl text-[#9EA9B6] hover:text-[#F3EBE3] transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="text-xl font-bold font-serif-header text-[#F3EBE3]">
              {selectedSurname ? `${selectedSurname} Family Photos` : 'All Photo Holdings'}
            </h2>
            <p className="text-xs font-mono text-[#9EA9B6]">{photos.length} historical image assets</p>
          </div>
        </div>

        {/* Ken Burns Story Mode Button */}
        {photos.length > 0 && (
          <button
            onClick={() => {
              setIsStoryMode(!isStoryMode);
              setStoryIndex(0);
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all border ${
              isStoryMode
                ? 'bg-[#C87D53] text-[#0F141A] border-[#C87D53] shadow-lg shadow-[#C87D53]/20'
                : 'bg-[#171E27] border-[#2A3644] text-[#D4A373] hover:border-[#C87D53]'
            }`}
          >
            {isStoryMode ? <Square className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isStoryMode ? 'Exit Story Mode' : 'Ken Burns Story Mode'}</span>
          </button>
        )}
      </div>

      {/* Story Mode Featured Banner */}
      {isStoryMode && photos.length > 0 && (
        <div className="relative rounded-3xl overflow-hidden bg-[#0F141A] border border-[#C87D53]/40 aspect-video max-h-[60vh] flex items-center justify-center shadow-2xl">
          <img
            key={photos[storyIndex]?.photo_id}
            src={photos[storyIndex]?.local_image_path.startsWith('/') ? photos[storyIndex]?.local_image_path : '/' + photos[storyIndex]?.local_image_path}
            alt={photos[storyIndex]?.subject_names}
            className="w-full h-full object-contain animate-ken-burns"
          />
          <div className="absolute bottom-0 inset-x-0 p-6 bg-gradient-to-t from-[#0F141A] via-[#0F141A]/80 to-transparent flex items-end justify-between">
            <div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#C87D53] bg-[#C87D53]/10 border border-[#C87D53]/30 px-2.5 py-1 rounded-md mb-2 inline-block">
                Story Mode ({storyIndex + 1} / {photos.length})
              </span>
              <h3 className="font-serif-header text-2xl font-bold text-[#F3EBE3]">
                {photos[storyIndex]?.subject_names || 'Historical Photo'}
              </h3>
              {photos[storyIndex]?.title_or_caption && (
                <p className="text-xs text-[#9EA9B6] mt-1 max-w-xl truncate">{photos[storyIndex]?.title_or_caption}</p>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={() => setStoryIndex(prev => (prev - 1 + photos.length) % photos.length)} className="px-3 py-1.5 bg-[#171E27] border border-[#2A3644] text-[#F3EBE3] rounded-lg text-xs font-mono">Prev</button>
              <button onClick={() => setStoryIndex(prev => (prev + 1) % photos.length)} className="px-3 py-1.5 bg-[#C87D53] text-[#0F141A] font-bold rounded-lg text-xs font-mono">Next</button>
            </div>
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {photos.map(photo => (
          <div
            key={photo.photo_id}
            onClick={() => setLightboxPhoto(photo)}
            className="group glass-panel glass-card-hover rounded-2xl overflow-hidden cursor-pointer flex flex-col justify-between"
          >
            <div className="aspect-square overflow-hidden bg-[#0F141A] relative">
              <img
                src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path}
                alt={photo.subject_names || photo.title_or_caption}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                loading="lazy"
                onError={e => { e.target.style.display = 'none'; }}
              />
              {/* Face Tag Pulse Indicator */}
              {photo.subject_names && (
                <div className="absolute top-2 right-2 w-3 h-3 rounded-full bg-[#C87D53] face-tag-pulse" title="Tagged Face Profile" />
              )}
            </div>
            <div className="p-3">
              <p className="text-xs font-semibold text-[#F3EBE3] truncate font-serif-header">
                {photo.subject_names || 'Unknown'}
              </p>
              <div className="flex items-center justify-between mt-1">
                {photo.maiden_name && (
                  <span className="text-[10px] text-[#D4A373] font-mono">
                    {photo.maiden_name}
                  </span>
                )}
                {photo.approximate_year && (
                  <span className="text-[10px] text-[#9EA9B6] font-mono">
                    c. {photo.approximate_year}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox Modal rendered via Portal in document.body */}
      {lightboxPhoto && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-[#0F141A]/95 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setLightboxPhoto(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="max-w-4xl max-h-[92vh] w-full bg-[#171E27] rounded-3xl overflow-hidden shadow-2xl border border-[#C87D53]/40 flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="relative flex-1 min-h-0 bg-[#0F141A] flex items-center justify-center p-2">
              <img
                src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                alt={lightboxPhoto.subject_names || 'Historical Photograph'}
                className="max-h-[68vh] w-auto max-w-full object-contain mx-auto"
              />
              <button
                onClick={() => setLightboxPhoto(null)}
                className="absolute top-4 right-4 p-2.5 bg-[#0F141A]/80 hover:bg-[#0F141A] rounded-full text-[#F3EBE3] transition-all border border-[#2A3644] hover:border-[#C87D53]"
                aria-label="Close photo preview"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 bg-[#171E27] border-t border-[#2A3644]">
              <h3 className="text-xl sm:text-2xl font-bold font-serif-header text-[#F3EBE3] mb-2">
                {lightboxPhoto.subject_names || 'Unknown Individual'}
              </h3>
              <div className="flex flex-wrap gap-4 text-xs font-mono text-[#9EA9B6] mb-3">
                {lightboxPhoto.maiden_name && (
                  <span>Surname: <strong className="text-[#D4A373]">{lightboxPhoto.maiden_name}</strong></span>
                )}
                {lightboxPhoto.approximate_year && (
                  <span>Approximate Year: <strong className="text-[#F3EBE3]">{lightboxPhoto.approximate_year}</strong></span>
                )}
                {lightboxPhoto.category && (
                  <span>Category: <strong className="text-[#C87D53] uppercase">{lightboxPhoto.category}</strong></span>
                )}
              </div>
              {lightboxPhoto.title_or_caption && (
                <p className="text-xs text-[#9EA9B6] leading-relaxed">
                  {lightboxPhoto.title_or_caption}
                </p>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
