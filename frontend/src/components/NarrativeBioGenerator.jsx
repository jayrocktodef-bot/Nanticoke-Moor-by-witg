import React, { useState } from 'react';
import { BookOpen, Copy, Check, Quote, ShieldCheck, Share2, ExternalLink } from 'lucide-react';

export default function NarrativeBioGenerator({ person, onSelectPerson }) {
  const [copiedFormat, setCopiedFormat] = useState(null);

  if (!person) return null;

  // Build prose paragraph chunks from structured facts
  const birthPart = person.birth_date || person.birth_place
    ? `${person.name} was born ${person.birth_date ? `on ${person.birth_date}` : ''} ${person.birth_place ? `in ${person.birth_place}` : ''}.`
    : `${person.name} was a member of the Delmarva regional family lines.`;

  const parentsPart = person.parents && person.parents.length > 0
    ? ` Child of ${person.parents.map(p => p.name).join(' and ')}.`
    : '';

  const marriagePart = person.spouses && person.spouses.length > 0
    ? ` Married ${person.spouses.map(s => s.name).join(', ')}.`
    : '';

  const deathPart = person.death_date || person.death_place
    ? ` Passed away ${person.death_date ? `on ${person.death_date}` : ''} ${person.death_place ? `in ${person.death_place}` : ''}.`
    : '';

  const bioProse = `${birthPart}${parentsPart}${marriagePart}${deathPart}`;

  // Formatted citations
  const chicagoCitation = `Delmarva Genealogy Preservation Archive, s.v. "${person.name}," accessed ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}, https://genealogy.writteninthegenome.blog/person/${person.id}.`;
  
  const ngsqCitation = `Delmarva & Nanticoke Archive, "${person.name}" profile ID ${person.id}, Written In The Genome Collection, 2026.`;

  const copyCitation = (text, formatKey) => {
    navigator.clipboard.writeText(text);
    setCopiedFormat(formatKey);
    setTimeout(() => setCopiedFormat(null), 2000);
  };

  return (
    <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#26221E] pb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-[#C68B59]" />
          <h3 className="font-serif-header font-bold text-lg text-[#F3EBE3]">
            Narrative Historical Biography
          </h3>
        </div>
        <span className="text-[10px] font-mono text-[#8C8275] bg-[#1C1A17] border border-[#332D27] px-2.5 py-1 rounded-lg">
          Genealogy Standards Compliant
        </span>
      </div>

      {/* Generated Narrative Prose */}
      <div className="bg-[#181614] border border-[#26221E] rounded-xl p-5 font-serif text-sm leading-relaxed text-[#E5E1DB] space-y-3 relative">
        <Quote className="w-6 h-6 text-[#C68B59]/20 absolute right-4 top-4" />
        <p className="relative z-10">
          {bioProse}
          <sup className="text-[#C68B59] font-sans font-bold cursor-pointer hover:underline ml-0.5" title="Primary Vital Record Citation">[1]</sup>
        </p>

        {person.notes && (
          <p className="text-xs text-[#A8A096] italic font-sans border-t border-[#26221E] pt-3">
            "{person.notes}"
            <sup className="text-[#C68B59] font-sans font-bold cursor-pointer hover:underline ml-0.5" title="Historical Document Note">[2]</sup>
          </p>
        )}
      </div>

      {/* Citation Engine Accordion */}
      <div className="space-y-3 border-t border-[#26221E] pt-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono text-[#D4A373] uppercase font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-[#C68B59]" />
            <span>Academic Citation Formats</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Chicago Style */}
          <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-[#F3EBE3] font-sans">Chicago Manual of Style</span>
              <button
                onClick={() => copyCitation(chicagoCitation, 'chicago')}
                className="text-[10px] text-[#C68B59] hover:text-[#D4A373] flex items-center gap-1 font-mono"
              >
                {copiedFormat === 'chicago' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedFormat === 'chicago' ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <p className="text-[11px] text-[#A8A096] font-mono leading-tight break-all">
              {chicagoCitation}
            </p>
          </div>

          {/* NGSQ Style */}
          <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-[#F3EBE3] font-sans">NGSQ / Evidence Explained</span>
              <button
                onClick={() => copyCitation(ngsqCitation, 'ngsq')}
                className="text-[10px] text-[#C68B59] hover:text-[#D4A373] flex items-center gap-1 font-mono"
              >
                {copiedFormat === 'ngsq' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedFormat === 'ngsq' ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <p className="text-[11px] text-[#A8A096] font-mono leading-tight break-all">
              {ngsqCitation}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
