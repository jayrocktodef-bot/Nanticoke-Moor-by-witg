import React, { useState, useEffect } from 'react';
import { Camera, Users, ChevronRight, ArrowLeft, Calendar, ExternalLink } from 'lucide-react';

export default function PhotoGallery() {
  const [surnameCounts, setSurnameCounts] = useState([]);
  const [selectedSurname, setSelectedSurname] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [categoryTab, setCategoryTab] = useState('portraits'); // 'portraits', 'trees', 'all'

  const isTreeItem = (p) => {
    if (p.media_type === 'lineage_tree') return true;
    const path = (p.local_image_path || '').toLowerCase();
    const title = (p.title_or_caption || '').toLowerCase();
    return (
      path.includes('ancestry') || path.includes('tree') || path.includes('diagram') || path.includes('chart') ||
      title.includes('ancestry') || title.includes('tree') || title.includes('diagram') || title.includes('chart') ||
      title.includes('go to') || title.includes('| d |') || title.includes('| e-l |') || title.includes('| m |') || title.includes('| n-r')
    );
  };

  useEffect(() => {
    fetch('/api/photos.json')
      .then(r => r.json())
      .then(data => {
        const countsMap = {};
        data.forEach(p => {
          if (!isTreeItem(p)) {
            const s = p.maiden_name;
            if (s && s.length > 1) {
              countsMap[s] = (countsMap[s] || 0) + 1;
            }
          }
        });
        const countsArr = Object.entries(countsMap).map(([surname, photo_count]) => ({ surname, photo_count }));
        countsArr.sort((a, b) => a.surname.localeCompare(b.surname, undefined, { sensitivity: 'base' }));
        setSurnameCounts(countsArr);
      })
      .catch(console.error);
  }, []);

  const handleSelectSurname = (surname) => {
    setSelectedSurname(surname);
    setLoading(true);
    fetch('/api/photos.json')
      .then(r => r.json())
      .then(data => {
        const lowerS = surname.toLowerCase();
        let filtered = data.filter(p => 
          p.maiden_name?.toLowerCase().includes(lowerS) ||
          p.married_surname?.toLowerCase().includes(lowerS) ||
          p.subject_names?.toLowerCase().includes(lowerS)
        );
        if (categoryTab === 'portraits') {
          filtered = filtered.filter(p => !isTreeItem(p));
        } else if (categoryTab === 'trees') {
          filtered = filtered.filter(p => isTreeItem(p));
        }
        setPhotos(filtered);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  const handleShowAll = () => {
    setSelectedSurname(null);
    setLoading(true);
    fetch('/api/photos.json')
      .then(r => r.json())
      .then(data => {
        let filtered = data;
        if (categoryTab === 'portraits') {
          filtered = data.filter(p => !isTreeItem(p));
        } else if (categoryTab === 'trees') {
          filtered = data.filter(p => isTreeItem(p));
        }
        setPhotos(filtered);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  // Color palette for surname portal cards
  const PORTAL_COLORS = [
    { from: 'from-amber-600/20', to: 'to-orange-700/10', border: 'border-amber-500/30', accent: 'text-amber-400', ring: 'ring-amber-500/20' },
    { from: 'from-sky-600/20', to: 'to-blue-700/10', border: 'border-sky-500/30', accent: 'text-sky-400', ring: 'ring-sky-500/20' },
    { from: 'from-emerald-600/20', to: 'to-teal-700/10', border: 'border-emerald-500/30', accent: 'text-emerald-400', ring: 'ring-emerald-500/20' },
    { from: 'from-purple-600/20', to: 'to-violet-700/10', border: 'border-purple-500/30', accent: 'text-purple-400', ring: 'ring-purple-500/20' },
    { from: 'from-rose-600/20', to: 'to-pink-700/10', border: 'border-rose-500/30', accent: 'text-rose-400', ring: 'ring-rose-500/20' },
    { from: 'from-cyan-600/20', to: 'to-teal-700/10', border: 'border-cyan-500/30', accent: 'text-cyan-400', ring: 'ring-cyan-500/20' },
  ];

  // Surname Portal Grid View
  if (!selectedSurname && photos.length === 0) {
    const topSurnames = surnameCounts.filter(s => s.photo_count >= 2).slice(0, 40);
    const otherSurnames = surnameCounts.filter(s => s.photo_count === 1);

    return (
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Photo Archive — Surname Portals</h2>
            <p className="text-xs text-slate-400">
              {surnameCounts.length} surname groups • {surnameCounts.reduce((a, s) => a + s.photo_count, 0)} historical portrait photos cataloged
            </p>
          </div>

          {/* Media Category Tab Selector */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
            <button
              onClick={() => setCategoryTab('portraits')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                categoryTab === 'portraits'
                  ? 'bg-amber-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              📷 People Portraits
            </button>
            <button
              onClick={() => {
                setCategoryTab('trees');
                handleShowAll();
              }}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                categoryTab === 'trees'
                  ? 'bg-amber-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🌳 Lineage Trees & Charts
            </button>
          </div>

          <button
            onClick={handleShowAll}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition-all flex items-center gap-1.5"
          >
            <Camera className="w-3.5 h-3.5" />
            Browse All Photos
          </button>
        </div>

        {/* Featured Surname Portals */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
          {topSurnames.map((s, idx) => {
            const color = PORTAL_COLORS[idx % PORTAL_COLORS.length];
            return (
              <button
                key={s.surname}
                onClick={() => handleSelectSurname(s.surname)}
                className={`group relative bg-gradient-to-br ${color.from} ${color.to} border ${color.border} rounded-xl p-5 text-left transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-black/20 active:scale-[0.98]`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white tracking-tight">{s.surname}</h3>
                    <div className="flex items-center gap-2 mt-1.5">
                      <Camera className={`w-3.5 h-3.5 ${color.accent}`} />
                      <span className="text-xs text-slate-400">
                        <strong className="text-slate-200">{s.photo_count}</strong> photo{s.photo_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className={`w-5 h-5 ${color.accent} opacity-0 group-hover:opacity-100 transition-opacity`} />
                </div>
                {/* Decorative ring */}
                <div className={`absolute -top-1 -right-1 w-8 h-8 rounded-full ring-2 ${color.ring} opacity-30`} />
              </button>
            );
          })}
        </div>

        {/* Single-photo surnames listed compactly */}
        {otherSurnames.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
              Additional Surnames ({otherSurnames.length})
            </h3>
            <div className="flex flex-wrap gap-2">
              {otherSurnames.map(s => (
                <button
                  key={s.surname}
                  onClick={() => handleSelectSurname(s.surname)}
                  className="text-xs bg-slate-800/60 border border-slate-700/50 text-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-700 hover:text-white transition-all"
                >
                  {s.surname}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Photo Grid View (filtered or all)
  return (
    <div>
      {/* Header with Back */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setSelectedSurname(null); setPhotos([]); }}
            className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="text-xl font-bold text-white">
              {selectedSurname ? `${selectedSurname} Family Photos` : 'All Photos'}
            </h2>
            <p className="text-xs text-slate-400">{photos.length} photos</p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-500">
          <div className="inline-block w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-3" />
          <p className="text-sm">Loading photos…</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {photos.map(photo => (
            <div
              key={photo.photo_id}
              onClick={() => setLightboxPhoto(photo)}
              className="group bg-slate-900 border border-slate-800 rounded-xl overflow-hidden cursor-pointer hover:border-amber-500/40 hover:shadow-lg hover:shadow-amber-500/5 transition-all"
            >
              <div className="aspect-square overflow-hidden bg-slate-800">
                <img
                  src={photo.local_image_path.startsWith('/') ? photo.local_image_path : '/' + photo.local_image_path}
                  alt={photo.subject_names || photo.title_or_caption}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  loading="lazy"
                  onError={e => { e.target.style.display = 'none'; }}
                />
              </div>
              <div className="p-2.5">
                <p className="text-xs font-medium text-slate-200 truncate">
                  {photo.subject_names || 'Unknown'}
                </p>
                <div className="flex items-center justify-between mt-1">
                  {photo.maiden_name && (
                    <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded font-mono">
                      {photo.maiden_name}
                    </span>
                  )}
                  {photo.approximate_year && (
                    <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                      <Calendar className="w-2.5 h-2.5" />
                      {photo.approximate_year}
                    </span>
                  )}
                </div>
                {photo.married_surname && (
                  <span className="text-[10px] text-slate-500 block mt-0.5">
                    née {photo.married_surname}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lightbox Modal */}
      {lightboxPhoto && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightboxPhoto(null)}
        >
          <div
            className="max-w-4xl w-full bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-slate-700"
            onClick={e => e.stopPropagation()}
          >
            <div className="relative">
              <img
                src={lightboxPhoto.local_image_path.startsWith('/') ? lightboxPhoto.local_image_path : '/' + lightboxPhoto.local_image_path}
                alt={lightboxPhoto.subject_names}
                className="w-full max-h-[70vh] object-contain bg-black"
              />
              <button
                onClick={() => setLightboxPhoto(null)}
                className="absolute top-3 right-3 p-2 bg-black/60 hover:bg-black/80 rounded-full text-white transition-all"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <h3 className="text-lg font-bold text-white mb-2">
                {lightboxPhoto.subject_names || 'Unknown Individual'}
              </h3>
              <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                {lightboxPhoto.maiden_name && (
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5 text-amber-400" />
                    Surname: <strong className="text-slate-200">{lightboxPhoto.maiden_name}</strong>
                  </span>
                )}
                {lightboxPhoto.married_surname && (
                  <span>Married: <strong className="text-slate-200">{lightboxPhoto.married_surname}</strong></span>
                )}
                {lightboxPhoto.approximate_year && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-sky-400" />
                    <strong className="text-slate-200">c. {lightboxPhoto.approximate_year}</strong>
                  </span>
                )}
              </div>
              {lightboxPhoto.title_or_caption && (
                <p className="mt-3 text-xs text-slate-400 leading-relaxed line-clamp-3">
                  {lightboxPhoto.title_or_caption}
                </p>
              )}
              {lightboxPhoto.source_url && (
                <a
                  href={lightboxPhoto.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300"
                >
                  <ExternalLink className="w-3 h-3" />
                  Original Source
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
