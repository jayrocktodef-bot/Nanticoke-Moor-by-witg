import React, { lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, GitCommit } from 'lucide-react';

const FamilyInterconnectionMatrix = lazy(() => import('../components/FamilyInterconnectionMatrix'));

export default function InterconnectionsPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-xs font-mono text-emerald-300 mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Tri-Racial & Afro-Indigenous Kinship Matrix</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Family Interconnection & Marriage Matrix
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl leading-relaxed">
            Documented intermarriages binding the Nanticoke (Millsboro), Lenape/Moor (Cheswold), and Gouldtown remnant settlements.
          </p>
        </div>
      </div>

      {/* Main Matrix Container */}
      <div className="bg-[#121110] border border-[#26221E] rounded-2xl p-4 sm:p-6 shadow-2xl">
        <Suspense fallback={
          <div className="p-24 text-center text-xs font-mono text-[#8C8275]">
            <div className="inline-block w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-400 rounded-full animate-spin mb-3" />
            <p>Computing clan interconnection matrix...</p>
          </div>
        }>
          <FamilyInterconnectionMatrix
            onSelectSurname={(sn) => navigate(`/lineages/${encodeURIComponent(sn)}`)}
            onOpenRecord={(rec) => {
              const id = rec.photo_id || rec.filename || rec.identifier;
              if (id) navigate(`/records/${id}`);
            }}
          />
        </Suspense>
      </div>
    </div>
  );
}
