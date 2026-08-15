import React, { useState } from 'react';
import { X, ExternalLink, Image as ImageIcon, FileText } from 'lucide-react';

export default function RecordDrawer({ record, onClose }) {
  const [lightboxMedia, setLightboxMedia] = useState(null);
  const [isFullScreen, setIsFullScreen] = useState(false);

  if (!record) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm animate-fade-in">
      <div className={`bg-[#1A1816] border-l border-[#332D27] h-full flex flex-col shadow-2xl transition-all duration-300 ${isFullScreen ? 'w-full max-w-none' : 'w-full max-w-3xl'}`}>
        {/* Drawer Header */}
        <div className="p-5 border-b border-[#332D27] flex justify-between items-center bg-[#161412]">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-[#C68B59] bg-[#C68B59]/10 px-2.5 py-1 rounded-md font-mono">
              Preserved Primary Record
            </span>
            <h2 className="font-serif-header text-xl font-bold text-[#F3EBE3] mt-2">
              {record.title || record.filename}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullScreen(!isFullScreen)}
              className="px-3 py-1.5 text-xs font-mono font-medium text-[#D4A373] bg-[#24201C] hover:bg-[#2E2924] border border-[#332D27] rounded-lg transition-colors flex items-center gap-1.5"
              title={isFullScreen ? 'Exit Full Screen' : 'Expand Full Screen Reader'}
            >
              {isFullScreen ? 'Collapse View ⤢' : 'Expand Full Screen ⤢'}
            </button>
            <button 
              onClick={onClose}
              className="p-2 text-[#8C8275] hover:text-[#F3EBE3] bg-[#24201C] hover:bg-[#2E2924] border border-[#332D27] rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {/* Wayback Source Citation */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-4 flex items-center justify-between text-xs">
            <div className="text-slate-300">
              <span className="text-slate-400 block">Wayback Snapshot Citation:</span>
              <span className="font-mono text-slate-200">{record.wayback_url}</span>
            </div>
            <a 
              href={record.wayback_url} 
              target="_blank" 
              rel="noreferrer"
              className="flex items-center gap-1 text-sky-400 hover:text-sky-300 font-medium ml-4 shrink-0"
            >
              Wayback <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* Media Assets Section */}
          {record.media_assets && record.media_assets.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-amber-400" /> Preserved Media Assets
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {record.media_assets.map((media, idx) => (
                  <div
                    key={idx}
                    onClick={() => setLightboxMedia(media)}
                    className="bg-slate-800 rounded-lg p-2 border border-slate-700/60 text-center cursor-pointer hover:border-amber-500/50 hover:shadow-lg transition-all group active:scale-[0.95]"
                  >
                    <img 
                      src={media.local_path.startsWith('/') ? media.local_path : '/' + media.local_path} 
                      alt={media.caption || 'Preserved asset'} 
                      className="max-h-40 mx-auto rounded object-contain mb-2 group-hover:scale-105 transition-transform"
                    />
                    {media.caption && (
                      <p className="text-xs text-slate-400 italic truncate group-hover:text-amber-300">{media.caption}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Formatted Heritage Text Document Reader */}
          <div>
            <h3 className="text-sm font-semibold text-[#D4A373] mb-3 flex items-center gap-2 font-serif-header uppercase tracking-wider">
              <FileText className="w-4 h-4 text-[#C68B59]" /> Preserved Archival Document
            </h3>
            <div 
              className="bg-[#121110] text-[#E5E1DB] p-6 rounded-xl border border-[#332D27] shadow-xl text-sm leading-relaxed overflow-x-auto selection:bg-[#C68B59] selection:text-[#121110]"
              dangerouslySetInnerHTML={{ __html: record.clean_html }}
            />
          </div>
        </div>
      </div>

      {/* Lightbox Modal */}
      {lightboxMedia && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightboxMedia(null)}
        >
          <div
            className="max-w-4xl w-full bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-slate-700 relative"
            onClick={e => e.stopPropagation()}
          >
            <div className="relative">
              <img
                src={lightboxMedia.local_path.startsWith('/') ? lightboxMedia.local_path : '/' + lightboxMedia.local_path}
                alt={lightboxMedia.caption || 'Preserved Asset'}
                className="w-full max-h-[80vh] object-contain bg-black"
              />
              <button
                onClick={() => setLightboxMedia(null)}
                className="absolute top-3 right-3 p-2 bg-black/60 hover:bg-black/80 rounded-full text-white transition-all"
              >
                ✕
              </button>
            </div>
            {lightboxMedia.caption && (
              <div className="p-4 bg-slate-900 border-t border-slate-800">
                <p className="text-xs text-slate-300 italic">{lightboxMedia.caption}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
