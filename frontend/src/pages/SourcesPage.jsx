import React from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, ShieldCheck } from 'lucide-react';
import SourcesCatalog from '../components/SourcesCatalog';

export default function SourcesPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-xs font-mono text-blue-300 mb-2">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Archival Provenance & Repositories</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Scholarly Citations & Primary Sources Catalog
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl leading-relaxed">
            Detailed citations conforming to Elizabeth Shown Mills (Evidence Explained) and Chicago Manual of Style.
          </p>
        </div>
      </div>

      {/* Main Catalog */}
      <SourcesCatalog
        onOpenRecord={(rec) => {
          const id = rec.photo_id || rec.filename || rec.identifier;
          if (id) navigate(`/records/${id}`);
        }}
      />
    </div>
  );
}
