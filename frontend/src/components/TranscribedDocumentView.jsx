import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, Copy, Check, Printer, Volume2, VolumeX, Search, 
  FileText, ExternalLink, Bookmark, Sliders, Eye, ArrowLeft
} from 'lucide-react';

export default function TranscribedDocumentView({ identifier, initialData, onClose }) {
  const [data, setData] = useState(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);
  
  // Reader controls
  const [searchQuery, setSearchQuery] = useState('');
  const [fontSize, setFontSize] = useState(16); // in px
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedCitation, setCopiedCitation] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showFacsimile, setShowFacsimile] = useState(false);

  const speechRef = useRef(null);

  // Fetch transcription data if not provided directly
  useEffect(() => {
    if (initialData) {
      setData(initialData);
      setLoading(false);
      return;
    }
    if (!identifier) return;

    setLoading(true);
    setError(null);
    fetch(`/api/transcriptions/${encodeURIComponent(identifier)}`)
      .then(r => {
        if (!r.ok) throw new Error('Transcription not found');
        return r.json();
      })
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [identifier, initialData]);

  // Lock background scroll & listen for Escape key
  useEffect(() => {
    const origOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (isSpeaking && window.speechSynthesis) {
          window.speechSynthesis.cancel();
        }
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = origOverflow;
      window.removeEventListener('keydown', handleKeyDown);
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [onClose, isSpeaking]);

  // Handle Speech Synthesis
  const handleToggleSpeech = () => {
    if (!window.speechSynthesis) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    if (!data?.full_text) return;

    // Filter out citation header lines for cleaner read-aloud
    const readableText = data.lines
      ? data.lines.filter(l => !l.startsWith('---') && !l.startsWith('ARCHIVAL CITATION:')).join('. ')
      : data.full_text;

    const utterance = new SpeechSynthesisUtterance(readableText);
    utterance.rate = 0.88; // Slightly slower, measured museum reading pace
    utterance.pitch = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    speechRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const handleCopyText = () => {
    if (!data?.full_text) return;
    const textToCopy = `${data.title}\n${data.citation}\n\n${data.full_text}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyCitation = () => {
    if (!data?.citation) return;
    navigator.clipboard.writeText(data.citation);
    setCopiedCitation(true);
    setTimeout(() => setCopiedCitation(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  // Keyword highlighting
  const highlightKeyTerms = (text) => {
    if (!text) return '';
    if (!searchQuery) return text;
    
    // Highlight active search query
    const parts = text.split(new RegExp(`(${searchQuery.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === searchQuery.toLowerCase() ? (
        <mark key={i} className="bg-[#C68B59] text-[#0F0E0D] px-1 rounded font-semibold">
          {part}
        </mark>
      ) : part
    );
  };

  const lines = data?.lines || (data?.full_text ? data.full_text.split('\n') : []);
  const filteredLines = searchQuery
    ? lines.filter(l => l.toLowerCase().includes(searchQuery.toLowerCase()))
    : lines;

  if (typeof document === 'undefined') return null;

  return createPortal(
    <div 
      className="fixed inset-0 z-[9999] bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div 
        className="w-full max-w-5xl h-[94vh] bg-[#141210] border border-[#3A322B] rounded-3xl shadow-2xl flex flex-col overflow-hidden text-[#E5E1DB]"
        onClick={e => e.stopPropagation()}
      >
        {/* Top App Bar */}
        <div className="p-4 sm:p-5 border-b border-[#2A241F] bg-[#1A1714] flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-[#C68B59]/15 border border-[#C68B59]/30 flex items-center justify-center text-[#C68B59] shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#C68B59] bg-[#C68B59]/10 border border-[#C68B59]/25 px-2 py-0.5 rounded">
                  {data?.document_type || 'Preserved Document'}
                </span>
                <span className="text-[10px] font-mono text-[#8C8275]">
                  • {data?.approximate_year || 'Historical Manuscript'}
                </span>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.2 rounded">
                  ✓ Text Transcription
                </span>
              </div>
              <h2 className="font-serif-header text-lg sm:text-xl font-bold text-[#F3EBE3] truncate mt-0.5">
                {data?.title || identifier}
              </h2>
            </div>
          </div>

          {/* Close and View Mode Switches */}
          <div className="flex items-center gap-2">
            {data?.local_image_path && (
              <button
                onClick={() => setShowFacsimile(!showFacsimile)}
                className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium border border-[#332D27] bg-[#121110] text-[#D4A373] hover:text-[#F3EBE3] hover:border-[#C68B59] transition-all flex items-center gap-1.5"
                title={showFacsimile ? 'Switch to text transcription' : 'View original scanned document image'}
              >
                {showFacsimile ? <ArrowLeft className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                <span>{showFacsimile ? 'Back to Text Only' : 'View Scanned Image'}</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-[#121110] border border-[#332D27] hover:border-[#C68B59] text-[#8C8275] hover:text-[#F3EBE3] transition-all"
              aria-label="Close document reader"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Reader Toolbar */}
        <div className="px-4 sm:px-6 py-2.5 bg-[#12100E] border-b border-[#24201C] flex flex-wrap items-center justify-between gap-3 text-xs shrink-0 font-mono">
          {/* Search Input */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#8C8275]" />
            <input
              type="text"
              placeholder="Search words in transcript..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-2.5 py-1.5 bg-[#1A1714] border border-[#2D2722] rounded-lg text-xs text-[#E5E1DB] placeholder-[#70675C] focus:outline-none focus:border-[#C68B59]"
            />
          </div>

          {/* Typography & Audio & Export Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Font Size Adjuster */}
            <div className="flex items-center border border-[#2D2722] rounded-lg bg-[#1A1714] overflow-hidden">
              <button
                onClick={() => setFontSize(Math.max(13, fontSize - 1))}
                className="px-2 py-1 text-[#8C8275] hover:text-[#F3EBE3] hover:bg-[#25201C] transition-colors"
                title="Decrease font size"
              >
                A-
              </button>
              <span className="px-2 text-[11px] text-[#A8A096] border-x border-[#2D2722]">{fontSize}px</span>
              <button
                onClick={() => setFontSize(Math.min(24, fontSize + 1))}
                className="px-2 py-1 text-[#8C8275] hover:text-[#F3EBE3] hover:bg-[#25201C] transition-colors"
                title="Increase font size"
              >
                A+
              </button>
            </div>

            {/* Line Numbers Toggle */}
            <button
              onClick={() => setShowLineNumbers(!showLineNumbers)}
              className={`px-2.5 py-1.5 rounded-lg border text-[11px] transition-all ${
                showLineNumbers 
                  ? 'border-[#C68B59]/40 text-[#D4A373] bg-[#C68B59]/10' 
                  : 'border-[#2D2722] text-[#8C8275] hover:text-[#E5E1DB]'
              }`}
              title="Toggle line numbers"
            >
              # Lines
            </button>

            {/* Audio Read-Aloud */}
            <button
              onClick={handleToggleSpeech}
              className={`px-2.5 py-1.5 rounded-lg border text-[11px] transition-all flex items-center gap-1.5 ${
                isSpeaking 
                  ? 'bg-[#C68B59] text-[#121110] font-bold border-[#C68B59]' 
                  : 'border-[#2D2722] text-[#D4A373] hover:border-[#C68B59]/50 hover:bg-[#1A1714]'
              }`}
              title="Read transcription aloud"
            >
              {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              <span>{isSpeaking ? 'Stop Audio' : 'Read Aloud'}</span>
            </button>

            {/* Copy Full Transcript */}
            <button
              onClick={handleCopyText}
              className="px-2.5 py-1.5 rounded-lg border border-[#2D2722] text-[#8C8275] hover:text-[#F3EBE3] hover:border-[#C68B59]/40 hover:bg-[#1A1714] transition-all flex items-center gap-1 text-[11px]"
              title="Copy entire transcribed document"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>

            {/* Print Record */}
            <button
              onClick={handlePrint}
              className="px-2.5 py-1.5 rounded-lg border border-[#2D2722] text-[#8C8275] hover:text-[#F3EBE3] hover:border-[#C68B59]/40 hover:bg-[#1A1714] transition-all flex items-center gap-1 text-[11px]"
              title="Print transcribed document"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>
          </div>
        </div>

        {/* Reader Canvas (Text Only) */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-10 custom-scrollbar bg-[#0E0C0B]">
          {loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="w-10 h-10 border-2 border-[#C68B59] border-t-transparent rounded-full animate-spin mb-4" />
              <p className="font-serif-header text-lg text-[#F3EBE3]">Loading Transcribed Manuscript...</p>
              <p className="text-xs text-[#8C8275] font-mono mt-1">Retrieving archival record & verified text lines</p>
            </div>
          )}

          {error && (
            <div className="max-w-md mx-auto my-12 p-6 rounded-2xl bg-rose-950/20 border border-rose-800/40 text-center">
              <p className="text-rose-300 font-semibold mb-2">Unable to load document transcription</p>
              <p className="text-xs text-[#8C8275] mb-4">{error}</p>
              <button 
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-[#1A1714] border border-[#332D27] text-xs font-mono text-[#F3EBE3]"
              >
                Close Reader
              </button>
            </div>
          )}

          {!loading && !error && showFacsimile && data?.local_image_path && (
            <div className="flex flex-col items-center justify-center space-y-4 animate-fade-in py-4">
              <img 
                src={data.local_image_path.startsWith('/') ? data.local_image_path : '/' + data.local_image_path}
                alt={data.title}
                className="max-h-[70vh] w-auto max-w-full rounded-2xl border border-[#3A322B] shadow-2xl object-contain bg-[#080706]"
              />
              <button
                onClick={() => setShowFacsimile(false)}
                className="px-4 py-2 rounded-xl bg-[#C68B59] text-[#0F0E0D] font-bold text-xs font-mono shadow-lg hover:bg-[#D4A373] transition-all"
              >
                ← Return to Text Transcription View
              </button>
            </div>
          )}

          {!loading && !error && !showFacsimile && (
            <div className="max-w-3xl mx-auto space-y-8 print:p-0 print:max-w-none">
              {/* Document Broadsheet Header */}
              <div className="border-b border-[#2A241F] pb-6">
                <div className="text-center space-y-2">
                  <span className="text-[11px] font-mono tracking-widest text-[#C68B59] uppercase block font-semibold">
                    {data?.repository || 'Delaware Native American Archives'}
                  </span>
                  <h1 
                    className="font-serif-header font-bold text-2xl sm:text-3xl md:text-4xl text-[#F3EBE3] tracking-tight leading-tight"
                    style={{ fontFamily: "'Cormorant Garamond', 'Cinzel', Georgia, serif" }}
                  >
                    {data?.title}
                  </h1>
                  <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-mono text-[#8C8275] pt-1">
                    <span>Classification: <strong className="text-[#D4A373]">{data?.document_type}</strong></span>
                    <span>•</span>
                    <span>Date: <strong className="text-[#E5E1DB]">{data?.approximate_year}</strong></span>
                    <span>•</span>
                    <span>Holdings: <strong className="text-[#E5E1DB]">{data?.line_count || lines.length} Lines</strong></span>
                    <span>•</span>
                    <span>Length: <strong className="text-[#E5E1DB]">{data?.word_count || 0} Words</strong></span>
                  </div>
                </div>
              </div>

              {/* Verified Text Lines */}
              <div 
                className="transcription-body space-y-2 select-text"
                style={{ 
                  fontSize: `${fontSize}px`, 
                  lineHeight: 1.85,
                  fontFamily: "'Cormorant Garamond', Georgia, serif" 
                }}
              >
                {searchQuery && (
                  <div className="p-3 bg-[#1C1712] border border-[#C68B59]/30 rounded-xl text-xs font-mono text-[#D4A373] mb-4">
                    Showing {filteredLines.length} lines matching "{searchQuery}"
                  </div>
                )}

                {filteredLines.map((line, idx) => {
                  const isDivider = line.startsWith('---') || line.startsWith('===');
                  const isHeading = line.startsWith('DOCUMENT TITLE:') || line.startsWith('RECORD CLASSIFICATION:') || line.startsWith('TRANSCRIPTION') || line.startsWith('ARCHIVAL CITATION:');
                  
                  if (isDivider) {
                    return <hr key={idx} className="my-4 border-[#2A241F]" />;
                  }

                  if (isHeading) {
                    return (
                      <div key={idx} className="font-mono text-xs uppercase tracking-wider text-[#C68B59] font-bold mt-4 mb-1">
                        {line}
                      </div>
                    );
                  }

                  return (
                    <div 
                      key={idx} 
                      className="flex items-start gap-4 group hover:bg-[#171412] px-2 py-0.5 rounded transition-colors"
                    >
                      {showLineNumbers && (
                        <span className="font-mono text-[11px] text-[#4A423B] group-hover:text-[#8C8275] select-none w-8 text-right shrink-0 pt-1">
                          {idx + 1}
                        </span>
                      )}
                      <p className="flex-1 text-[#E5E1DB] leading-relaxed break-words">
                        {highlightKeyTerms(line)}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Archival Citation Footer Box */}
              {data?.citation && (
                <div className="mt-12 p-5 rounded-2xl bg-[#141210] border border-[#2D2722] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase tracking-wider text-[#C68B59] font-semibold flex items-center gap-1.5">
                      <Bookmark className="w-3.5 h-3.5" /> Standard Genealogical Citation
                    </span>
                    <button
                      onClick={handleCopyCitation}
                      className="text-xs font-mono text-[#D4A373] hover:underline flex items-center gap-1"
                    >
                      {copiedCitation ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedCitation ? 'Copied Citation' : 'Copy Citation'}</span>
                    </button>
                  </div>
                  <p className="text-xs font-mono text-[#A8A096] leading-relaxed bg-[#0E0D0C] p-3 rounded-lg border border-[#221E1A] break-words">
                    {data.citation}
                  </p>
                  {data.source_url && (
                    <a
                      href={data.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 font-mono mt-1"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Original Archival Source URL</span>
                    </a>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
