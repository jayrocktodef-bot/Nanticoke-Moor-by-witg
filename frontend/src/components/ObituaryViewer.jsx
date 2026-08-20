import React, { useState, useEffect } from 'react';
import { Search, HeartHandshake, Calendar, MapPin, ExternalLink, User, Volume2, VolumeX, BookOpen, ShieldCheck } from 'lucide-react';

export default function ObituaryViewer({ onSelectPerson }) {
  const [obituaries, setObituaries] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedObit, setSelectedObit] = useState(null);
  const [expandedObitId, setExpandedObitId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const fetchObits = (q = '') => {
    setLoading(true);
    fetch('/api/obituaries.json')
      .then(r => r.json())
      .then(data => {
          data.sort((a, b) => (a.deceased_name || '').localeCompare(b.deceased_name || '', undefined, { sensitivity: 'base' }));
          if (q.trim()) {
            const lowerQ = q.toLowerCase();
            const filtered = data.filter(o => 
              o.deceased_name?.toLowerCase().includes(lowerQ) ||
              o.full_text?.toLowerCase().includes(lowerQ) ||
              o.cemetery_location?.toLowerCase().includes(lowerQ)
            );
            setObituaries(filtered);
          } else {
            setObituaries(data);
          }
          setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchObits();
  }, []);

  const handleSearch = (e) => {
    const q = e.target.value;
    setSearch(q);
    fetchObits(q);
  };

  const handleToggleAudio = (text) => {
    if (!('speechSynthesis' in window)) return;
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
      setIsPlayingAudio(true);
    }
  };

  // Stop speech synthesis on modal close
  const handleCloseModal = () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setIsPlayingAudio(false);
    setSelectedObit(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#2A3644] pb-4">
        <div>
          <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3] tracking-tight mb-1 flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-[#C87D53]" />
            Preserved Obituary Vault
          </h2>
          <p className="text-xs text-[#9EA9B6]">
            {obituaries.length} preserved obituaries, memorials, and broadsheet death notices across Delaware & New Jersey
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#9EA9B6]" />
          <input
            type="text"
            placeholder="Search deceased name, kin, cemetery..."
            value={search}
            onChange={handleSearch}
            className="w-full pl-9 pr-3 py-2 bg-[#171E27] border border-[#2A3644] rounded-xl text-[#F3EBE3] placeholder-[#64748B] text-xs focus:outline-none focus:border-[#C87D53] transition-colors"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-[#9EA9B6]">
          <div className="inline-block w-6 h-6 border-2 border-[#C87D53]/30 border-t-[#C87D53] rounded-full animate-spin mb-3" />
          <p className="text-xs font-mono tracking-wider uppercase">Loading broadsheet vault…</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {obituaries.map(obit => (
            <div
              key={obit.id}
              onClick={() => setSelectedObit(obit)}
              className="glass-panel glass-card-hover rounded-2xl p-6 cursor-pointer flex flex-col justify-between group relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[#C87D53]/10 to-transparent pointer-events-none" />

              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5">
                    <HeartHandshake className="w-4 h-4 text-[#C87D53] shrink-0" />
                    <h3 className="font-bold text-lg text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors font-serif-header">
                      {obit.deceased_name}
                    </h3>
                  </div>
                  {obit.age && (
                    <span className="text-[11px] bg-[#1B3B2B] text-[#E5B269] border border-[#C87D53]/30 px-2.5 py-0.5 rounded-full font-mono shrink-0">
                      Age {obit.age}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-4 text-xs text-[#9EA9B6] mb-4">
                  {(obit.birth_date || obit.death_date) && (
                    <span className="flex items-center gap-1.5 font-mono text-[11px]">
                      <Calendar className="w-3.5 h-3.5 text-[#D4A373]" />
                      {obit.birth_date ? `${obit.birth_date} – ` : ''}{obit.death_date || 'Date N/A'}
                    </span>
                  )}
                  {obit.cemetery_location && (
                    <span className="flex items-center gap-1.5 truncate max-w-[220px] text-[11px]">
                      <MapPin className="w-3.5 h-3.5 text-[#C87D53]" />
                      {obit.cemetery_location}
                    </span>
                  )}
                </div>

                {expandedObitId === obit.id ? (
                  <div className="text-xs text-[#F3EBE3] leading-relaxed bg-[#0F141A]/90 p-4 rounded-xl border border-[#C87D53]/30 whitespace-pre-wrap font-editorial-body drop-cap text-base">
                    {obit.full_text}
                  </div>
                ) : (
                  <p className="text-sm text-[#9EA9B6] line-clamp-3 leading-relaxed font-editorial-body">
                    {obit.full_text}
                  </p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-[#2A3644] flex items-center justify-between text-[11px]">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedObitId(expandedObitId === obit.id ? null : obit.id);
                  }}
                  className="text-[#C87D53] hover:text-[#D4A373] font-mono font-semibold underline"
                >
                  {expandedObitId === obit.id ? 'Collapse Text ▲' : 'Expand Broadsheet ▼'}
                </button>
                {obit.person_id ? (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectPerson && onSelectPerson(obit.person_id);
                    }}
                    className="text-[#D4A373] hover:text-[#F3EBE3] font-mono font-medium hover:underline flex items-center gap-1.5"
                  >
                    <User className="w-3.5 h-3.5 text-[#C87D53]" />
                    Profile #{obit.person_id} →
                  </button>
                ) : (
                  <span className="text-[#C87D53] group-hover:underline font-mono">View Details →</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Editorial Broadsheet Lightbox Modal */}
      {selectedObit && (
        <div
          className="fixed inset-0 z-50 bg-[#0F141A]/90 backdrop-blur-xl flex items-center justify-center p-4 animate-fade-in"
          onClick={handleCloseModal}
        >
          <div
            className="max-w-2xl w-full bg-[#171E27] border border-[#C87D53]/40 rounded-3xl p-8 shadow-2xl relative max-h-[88vh] overflow-y-auto custom-scrollbar"
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={handleCloseModal}
              className="absolute top-5 right-5 p-2 bg-[#0F141A] border border-[#2A3644] hover:border-[#C87D53] text-[#9EA9B6] hover:text-[#F3EBE3] rounded-full transition-all"
            >
              ✕
            </button>

            <div className="flex items-center justify-between gap-3 mb-4 pr-10">
              <div className="flex items-center gap-2.5">
                <HeartHandshake className="w-6 h-6 text-[#C87D53]" />
                <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">{selectedObit.deceased_name}</h2>
              </div>

              {/* Text to Speech Button */}
              {'speechSynthesis' in window && (
                <button
                  onClick={() => handleToggleAudio(`${selectedObit.deceased_name}. ${selectedObit.full_text}`)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all ${
                    isPlayingAudio
                      ? 'bg-[#C87D53] text-[#0F141A] font-bold border-[#C87D53]'
                      : 'bg-[#0F141A] border-[#2A3644] text-[#D4A373] hover:border-[#C87D53]'
                  }`}
                >
                  {isPlayingAudio ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  <span>{isPlayingAudio ? 'Stop Audio' : 'Audio Reader'}</span>
                </button>
              )}
            </div>

            <div className="flex flex-wrap gap-4 text-xs text-[#9EA9B6] mb-6 bg-[#0F141A] p-4 rounded-2xl border border-[#2A3644]">
              {selectedObit.age && (
                <span>Age: <strong className="text-[#F3EBE3] font-mono">{selectedObit.age}</strong></span>
              )}
              {selectedObit.birth_date && (
                <span>Born: <strong className="text-[#F3EBE3] font-mono">{selectedObit.birth_date}</strong></span>
              )}
              {selectedObit.death_date && (
                <span>Died: <strong className="text-[#F3EBE3] font-mono">{selectedObit.death_date}</strong></span>
              )}
              {selectedObit.cemetery_location && (
                <span>Burial Site: <strong className="text-[#D4A373] font-mono">{selectedObit.cemetery_location}</strong></span>
              )}
            </div>

            <div className="bg-[#0F141A] p-6 rounded-2xl border border-[#2A3644] text-base leading-relaxed text-[#F3EBE3] font-editorial-body drop-cap whitespace-pre-wrap selection:bg-[#C87D53]/30">
              {selectedObit.full_text}
            </div>

            {selectedObit.source_url && (
              <a
                href={selectedObit.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 inline-flex items-center gap-2 text-xs font-mono text-[#D4A373] hover:text-[#F3EBE3] bg-[#0F141A] border border-[#2A3644] px-4 py-2 rounded-xl transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View Original Preserved Broadsheet Source URL
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
