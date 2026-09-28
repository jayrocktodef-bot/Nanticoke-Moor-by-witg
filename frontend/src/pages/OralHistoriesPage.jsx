import React from 'react';
import { Volume2, Mic } from 'lucide-react';
import OralHistoryPlayer from '../components/OralHistoryPlayer';

export default function OralHistoriesPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/15 border border-red-500/30 text-xs font-mono text-red-300 mb-2">
            <Mic className="w-3.5 h-3.5" />
            <span>Spoken Memory & Elder Audio Archive</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Oral History Vault & Voice Recordings
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl leading-relaxed">
            Preserved historical interviews, community recollections, and elder accounts from Delaware and South Jersey descendants.
          </p>
        </div>
      </div>

      {/* Main Player Component */}
      <OralHistoryPlayer />
    </div>
  );
}
