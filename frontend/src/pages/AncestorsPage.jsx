import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Search, Sparkles, ScanFace } from 'lucide-react';
import FacetedSearchPanel from '../components/FacetedSearchPanel';
import AncestorFaceMatcherModal from '../components/AncestorFaceMatcherModal';

export default function AncestorsPage() {
  const navigate = useNavigate();
  const [isFaceMatcherOpen, setIsFaceMatcherOpen] = useState(false);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C68B59]/15 border border-[#C68B59]/30 text-xs font-mono text-[#D4A373] mb-2">
            <Users className="w-3.5 h-3.5 text-[#C68B59]" />
            <span>3,783 Documented Ancestors</span>
          </div>
          <h1 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Ancestor Directory & Faceted Explorer
          </h1>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl">
            Search, filter by birth/death era, surname lineage, state of residency, and media evidence.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setIsFaceMatcherOpen(true)}
            className="px-4 py-2 rounded-xl bg-[#141210] border border-[#332D27] hover:border-cyan-500/60 text-xs font-mono text-cyan-300 hover:text-[#F3EBE3] transition-all flex items-center gap-2 shadow-sm"
          >
            <ScanFace className="w-3.5 h-3.5 text-cyan-400" />
            <span>Face Matcher (ONNX)</span>
          </button>

          <button
            onClick={() => navigate('/network')}
            className="px-4 py-2 rounded-xl bg-[#141210] border border-[#332D27] hover:border-[#C68B59]/60 text-xs font-mono text-[#D4A373] hover:text-[#F3EBE3] transition-all"
          >
            Explore Kinship Graph →
          </button>
        </div>
      </div>

      {/* Main Faceted Search Panel */}
      <FacetedSearchPanel 
        onSelectPerson={(personId) => navigate(`/ancestors/${personId}`)} 
      />

      {/* Biometric Face Matcher Modal */}
      <AncestorFaceMatcherModal
        isOpen={isFaceMatcherOpen}
        onClose={() => setIsFaceMatcherOpen(false)}
      />
    </div>
  );
}
