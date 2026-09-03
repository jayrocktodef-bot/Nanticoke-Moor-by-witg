import React, { useState } from 'react';
import { Users, Image as ImageIcon, HeartHandshake, ChevronRight, Bookmark } from 'lucide-react';

export default function SurnameCard({ surname, variants, count, pages, photos, obituaries, onSelect }) {
  const [expandedVariants, setExpandedVariants] = useState(false);

  // Parse variant spellings into clean array
  const variantList = variants ? variants.split(',').map(v => v.strip ? v.strip() : v.trim()).filter(Boolean) : [];
  const displayedVariants = expandedVariants ? variantList : variantList.slice(0, 4);

  return (
    <div 
      onClick={() => onSelect(surname)}
      className="bento-card group relative bg-[#1C1A17] hover:bg-[#24201C] border border-[#332D27] hover:border-[#C68B59]/60 rounded-xl p-5 transition-all duration-200 cursor-pointer shadow-lg hover:shadow-[0_0_25px_rgba(198,139,89,0.12)] flex flex-col justify-between active:scale-[0.98] min-w-0"
    >
      <div className="min-w-0 w-full">
        {/* Top Header Row: Primary Surname & Action Arrow */}
        <div className="flex justify-between items-start gap-3 mb-3">
          <div className="min-w-0">
            <h3 className="font-serif-header text-xl font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors tracking-tight truncate">
              {surname}
            </h3>
            <span className="text-[11px] font-mono text-[#8C8275] block mt-0.5">
              Lineage Portal
            </span>
          </div>

          <span className="p-2 bg-[#121110] border border-[#2D2722] rounded-lg text-[#8C8275] group-hover:text-[#D4A373] group-hover:border-[#C68B59]/40 group-hover:bg-[#C68B59]/10 transition-all shrink-0">
            <ChevronRight className="w-4 h-4" />
          </span>
        </div>

        {/* Historical Variant Spelling Pills (Expandable) */}
        {variantList.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4 items-center">
            <span className="text-[10px] text-[#8C8275] font-mono self-center mr-1">variants:</span>
            {displayedVariants.map((varName, idx) => (
              <span
                key={idx}
                className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#121110] text-[#D4A373]/90 border border-[#332D27] group-hover:border-[#C68B59]/30 break-words"
              >
                {varName}
              </span>
            ))}
            {variantList.length > 4 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedVariants(!expandedVariants);
                }}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#121110] border border-[#C68B59]/40 text-[#D4A373] hover:text-[#F3EBE3] transition-colors"
                title="Toggle all spelling variants"
              >
                {expandedVariants ? 'show less' : `+${variantList.length - 4} more`}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Compact Micro-Dashboard Stats Footer (No boilerplate text!) */}
      <div className="flex items-center justify-between text-xs border-t border-[#2B2621] pt-3 text-[#A8A096]">
        <div className="flex items-center gap-1.5 font-medium">
          <Users className="w-3.5 h-3.5 text-[#C68B59]" />
          <span className="tabular-nums font-semibold text-[#F3EBE3]">{count}</span>
          <span className="text-[11px] text-[#8C8275]">Persons</span>
        </div>

        <div className="flex items-center gap-3">
          {photos > 0 && (
            <div className="flex items-center gap-1 text-[11px] font-mono text-purple-300 bg-purple-950/40 border border-purple-800/40 px-2 py-0.5 rounded">
              <ImageIcon className="w-3 h-3 text-purple-400" />
              <span className="tabular-nums">{photos}</span>
            </div>
          )}
          {obituaries > 0 && (
            <div className="flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded">
              <HeartHandshake className="w-3 h-3 text-amber-400" />
              <span className="tabular-nums">{obituaries}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
