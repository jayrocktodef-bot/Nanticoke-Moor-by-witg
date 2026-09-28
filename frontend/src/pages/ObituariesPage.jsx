import React, { lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { HeartHandshake, Volume2, ShieldCheck } from 'lucide-react';

const ObituaryViewer = lazy(() => import('../components/ObituaryViewer'));

export default function ObituariesPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-xs font-mono text-purple-300 mb-2">
            <HeartHandshake className="w-3.5 h-3.5" />
            <span>364 Preserved Historical Memorials</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Historical Obituary & Memorial Broadsheet Vault
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl leading-relaxed">
            Preserved funeral programs, newspaper clippings, surviving kin relations, and cemetery locations with audio read-aloud playback.
          </p>
        </div>
      </div>

      {/* Obituary Viewer Container */}
      <Suspense fallback={
        <div className="p-24 text-center text-xs font-mono text-[#8C8275]">
          <div className="inline-block w-8 h-8 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin mb-3" />
          <p>Opening historical obituary vault...</p>
        </div>
      }>
        <ObituaryViewer 
          onSelectPerson={(personId) => navigate(`/ancestors/${personId}`)} 
        />
      </Suspense>
    </div>
  );
}
