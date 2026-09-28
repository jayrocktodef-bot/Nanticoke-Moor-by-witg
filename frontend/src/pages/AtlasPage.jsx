import React, { lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Compass, ShieldCheck } from 'lucide-react';

const HistoricalMigrationMap = lazy(() => import('../components/HistoricalMigrationMap'));

export default function AtlasPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-xs font-mono text-blue-300 mb-2">
            <Compass className="w-3.5 h-3.5" />
            <span>Delmarva & South Jersey Historical Cartography</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Historical Settlement & Cemetery Atlas
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-3xl leading-relaxed">
            Trace the 6 sovereign settlement hubs (Millsboro, Cheswold, Gouldtown, Woodstown, Caroline, Woodland), 
            the 4 historic waterways/overland migration routes, and 13 GPS-verified burial grounds with tombstone records.
          </p>
        </div>
      </div>

      {/* Map Viewport Container */}
      <div className="bg-[#121110] border border-[#26221E] rounded-2xl overflow-hidden shadow-2xl">
        <Suspense fallback={
          <div className="p-24 text-center text-xs font-mono text-[#8C8275]">
            <div className="inline-block w-8 h-8 border-2 border-blue-500/30 border-t-blue-400 rounded-full animate-spin mb-3" />
            <p>Loading Delmarva cartographic atlas...</p>
          </div>
        }>
          <HistoricalMigrationMap 
            onSelectPerson={(id) => navigate(`/ancestors/${id}`)}
          />
        </Suspense>
      </div>
    </div>
  );
}
