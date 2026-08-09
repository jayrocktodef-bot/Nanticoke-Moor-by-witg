import React, { useEffect, useState } from 'react';
import { User, Users, Camera, HeartHandshake, FileText, ExternalLink, Calendar, GitBranch } from 'lucide-react';

export default function PersonProfileDrawer({ personId, onClose, onSelectPerson }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);

  useEffect(() => {
    if (!personId) return;
    setLoading(true);
    fetch(`/api/person/${personId}`)
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [personId]);

  if (!personId) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex justify-end transition-opacity"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full p-6 overflow-y-auto flex flex-col shadow-2xl relative"
        onClick={e => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800 transition-all"
        >
          ✕
        </button>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-3" />
          </div>
        ) : profile ? (
          <div className="space-y-6">
            {/* Person Header */}
            <div className="flex items-start gap-4 pb-4 border-b border-slate-800">
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-2xl">
                <User className="w-8 h-8" />
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded font-mono">
                  ID #{profile.person.person_id} • {profile.person.dataset_source}
                </span>
                <h2 className="text-2xl font-bold text-white mt-1">{profile.person.name}</h2>
                {profile.person.notes && (
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{profile.person.notes}</p>
                )}
              </div>
            </div>

            {/* Immediate Relationships */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <GitBranch className="w-4 h-4 text-emerald-400" />
                Kinship & Family Connections ({profile.relationships.length})
              </h3>
              {profile.relationships.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No family relationships explicitly linked.</p>
              ) : (
                <div className="space-y-2">
                  {profile.relationships.map((rel, idx) => (
                    <div
                      key={idx}
                      onClick={() => onSelectPerson && onSelectPerson(rel.rel_id)}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-xl hover:border-amber-500/40 cursor-pointer flex justify-between items-center transition-all group"
                    >
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-sky-400" />
                        <div>
                          <span className="font-semibold text-xs text-slate-200 group-hover:text-amber-300">
                            {rel.rel_name}
                          </span>
                          <span className="text-[11px] text-slate-500 block truncate max-w-xs">
                            {rel.evidence_text}
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-amber-400">
                        {rel.relationship_type}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Attached Photos */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Camera className="w-4 h-4 text-purple-400" />
                Preserved Photographs ({profile.photos.length})
              </h3>
              {profile.photos.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No photos cataloged for this individual.</p>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {profile.photos.map(photo => (
                    <div
                      key={photo.photo_id}
                      onClick={() => setLightboxPhoto(photo)}
                      className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden p-2 cursor-pointer hover:border-amber-500/50 hover:shadow-lg transition-all group"
                    >
                      <img
                        src={`http://localhost:8000/${photo.local_image_path}`}
                        alt={photo.subject_names}
                        className="w-full h-28 object-cover rounded-lg mb-1.5 group-hover:scale-105 transition-transform"
                      />
                      <span className="text-[11px] font-medium text-slate-300 block truncate group-hover:text-amber-300">
                        {photo.subject_names}
                      </span>
                      {photo.maiden_name && (
                        <span className="text-[10px] text-amber-400 block font-mono">
                          {photo.maiden_name}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Attached Obituaries */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <HeartHandshake className="w-4 h-4 text-rose-400" />
                Obituaries & Funeral Notices ({profile.obituaries.length})
              </h3>
              {profile.obituaries.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No obituaries linked to this individual.</p>
              ) : (
                <div className="space-y-2">
                  {profile.obituaries.map(obit => (
                    <div key={obit.id} className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs">
                      <h4 className="font-bold text-slate-200 mb-1">{obit.deceased_name}</h4>
                      <p className="text-slate-400 line-clamp-2 leading-relaxed">{obit.full_text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Preserved Source Record Link */}
            {profile.person.source_page && (
              <div className="pt-4 border-t border-slate-800 flex justify-between items-center text-xs">
                <span className="text-slate-500">Source Document: <strong className="text-slate-300">{profile.person.source_page}</strong></span>
                <a
                  href={`/api/records/${profile.person.source_page}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-400 hover:underline flex items-center gap-1 font-medium"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  View Original Page
                </a>
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">Failed to load person profile.</p>
        )}
      </div>

      {/* Lightbox Modal */}
      {lightboxPhoto && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={e => { e.stopPropagation(); setLightboxPhoto(null); }}
        >
          <div
            className="max-w-4xl w-full bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-slate-700 relative"
            onClick={e => e.stopPropagation()}
          >
            <div className="relative">
              <img
                src={`http://localhost:8000/${lightboxPhoto.local_image_path}`}
                alt={lightboxPhoto.subject_names}
                className="w-full max-h-[75vh] object-contain bg-black"
              />
              <button
                onClick={() => setLightboxPhoto(null)}
                className="absolute top-3 right-3 p-2 bg-black/60 hover:bg-black/80 rounded-full text-white transition-all"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <h3 className="text-lg font-bold text-white mb-1">
                {lightboxPhoto.subject_names || 'Preserved Photograph'}
              </h3>
              {lightboxPhoto.maiden_name && (
                <span className="text-xs text-amber-400 font-mono block mb-2">
                  Maiden Surname: {lightboxPhoto.maiden_name}
                </span>
              )}
              {lightboxPhoto.title_or_caption && (
                <p className="text-xs text-slate-400 leading-relaxed max-h-24 overflow-y-auto">
                  {lightboxPhoto.title_or_caption}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
