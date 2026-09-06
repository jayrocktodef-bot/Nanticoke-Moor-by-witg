import React, { useState } from 'react';
import { BookOpen, Copy, Check, Download, ShieldCheck, X, FileText, Share2 } from 'lucide-react';
import { 
  generateEvidenceExplainedCitation, 
  generateChicagoCitation, 
  generateBibTeX, 
  downloadGedcomFile 
} from '../utils/citationGenerator';

export default function CitationModal({ isOpen, onClose, data, type = 'person' }) {
  if (!isOpen || !data) return null;

  const [activeTab, setActiveTab] = useState('ee'); // 'ee', 'chicago', 'plain', 'bibtex', 'gedcom'
  const [copiedKey, setCopiedKey] = useState(null);

  const ee = generateEvidenceExplainedCitation(data, type);
  const chicago = generateChicagoCitation(data, type);
  const bibtex = generateBibTeX(data, type);
  const plain = ee.referenceNote;

  const handleCopy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const title = type === 'person' 
    ? (data.person?.name || data.name || 'Individual Profile')
    : (data.deceased_name || data.title || 'Historical Archive Record');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div 
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-xl">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Cite & Export Record
              </h3>
              <p className="text-xs text-slate-400 truncate max-w-md">
                {title}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-xl bg-slate-800/80 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-800 bg-slate-950/30 px-6 gap-2 pt-3 overflow-x-auto">
          <button
            onClick={() => setActiveTab('ee')}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'ee'
                ? 'border-amber-400 text-amber-400 bg-slate-800/50'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Evidence Explained (GPS)
          </button>
          <button
            onClick={() => setActiveTab('chicago')}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'chicago'
                ? 'border-amber-400 text-amber-400 bg-slate-800/50'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Chicago (17th ed.)
          </button>
          <button
            onClick={() => setActiveTab('bibtex')}
            className={`px-3 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 whitespace-nowrap ${
              activeTab === 'bibtex'
                ? 'border-amber-400 text-amber-400 bg-slate-800/50'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            BibTeX
          </button>
          {type === 'person' && (
            <button
              onClick={() => setActiveTab('gedcom')}
              className={`px-3 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'gedcom'
                  ? 'border-amber-400 text-amber-400 bg-slate-800/50'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Download className="w-3.5 h-3.5" />
              GEDCOM 5.5.1 Excerpt
            </button>
          )}
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {activeTab === 'ee' && (
            <div className="space-y-4 text-xs">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono uppercase text-[10px] tracking-wider text-amber-400/90 font-bold">
                    Full Reference Note (First Citation)
                  </span>
                  <button
                    onClick={() => handleCopy(ee.referenceNote, 'ee-full')}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                  >
                    {copiedKey === 'ee-full' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedKey === 'ee-full' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-200 leading-relaxed font-serif">
                  {ee.referenceNote}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono uppercase text-[10px] tracking-wider text-slate-400 font-bold">
                    Subsequent Reference Note
                  </span>
                  <button
                    onClick={() => handleCopy(ee.subsequentNote, 'ee-sub')}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                  >
                    {copiedKey === 'ee-sub' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedKey === 'ee-sub' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-200 leading-relaxed font-serif">
                  {ee.subsequentNote}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono uppercase text-[10px] tracking-wider text-slate-400 font-bold">
                    Source List Entry (Bibliography)
                  </span>
                  <button
                    onClick={() => handleCopy(ee.sourceListEntry, 'ee-bib')}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                  >
                    {copiedKey === 'ee-bib' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedKey === 'ee-bib' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-200 leading-relaxed font-serif">
                  {ee.sourceListEntry}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'chicago' && (
            <div className="space-y-4 text-xs">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono uppercase text-[10px] tracking-wider text-amber-400/90 font-bold">
                    Footnote / Endnote Format
                  </span>
                  <button
                    onClick={() => handleCopy(chicago.footnote, 'chi-fn')}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                  >
                    {copiedKey === 'chi-fn' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedKey === 'chi-fn' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-200 leading-relaxed font-serif">
                  {chicago.footnote}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="font-mono uppercase text-[10px] tracking-wider text-slate-400 font-bold">
                    Bibliography Format
                  </span>
                  <button
                    onClick={() => handleCopy(chicago.bibliography, 'chi-bib')}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                  >
                    {copiedKey === 'chi-bib' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedKey === 'chi-bib' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-200 leading-relaxed font-serif">
                  {chicago.bibliography}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'bibtex' && (
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="font-mono uppercase text-[10px] tracking-wider text-slate-400 font-bold">
                  BibTeX Record
                </span>
                <button
                  onClick={() => handleCopy(bibtex, 'bibtex')}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-md transition-colors"
                >
                  {copiedKey === 'bibtex' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedKey === 'bibtex' ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-slate-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
                {bibtex}
              </pre>
            </div>
          )}

          {activeTab === 'gedcom' && type === 'person' && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-slate-300 text-xs leading-relaxed">
                <p className="font-semibold text-amber-400 mb-1">Standard Genealogical Data Interchange (GEDCOM 5.5.1)</p>
                Download a validated lineage extract for <strong>{title}</strong>. Compatible with Ancestry, FamilySearch, Gramps, RootsMagic, and Family Tree Maker. Includes all verified birth/death events, notes, and family connections.
              </div>

              <div className="flex justify-center pt-2">
                <button
                  onClick={() => downloadGedcomFile(data)}
                  className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg flex items-center gap-2 transition-all active:scale-[0.98]"
                >
                  <Download className="w-4 h-4" />
                  Download Lineage File (.ged)
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-slate-950/40 flex justify-between items-center text-[11px] text-slate-500">
          <span>Adheres to Genealogical Proof Standard (GPS) Evidence Models</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
