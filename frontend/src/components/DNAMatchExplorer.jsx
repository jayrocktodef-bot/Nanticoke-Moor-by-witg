import React, { useState } from 'react';
import { Dna, Sparkles, Filter, Info, ShieldCheck, ChevronRight, User } from 'lucide-react';

// Sample curated DNA segment match data across Delmarva maternal lineages
const SAMPLE_DNA_MATCHES = [
  { id: 'dna-1', name: 'Elder Levin Davis Lineage', surname: 'Davis', shared_cm: 284, segments: 12, longest_cm: 45, predicted: '2nd Cousin 1x Removed', chromosomes: [1, 4, 9, 14] },
  { id: 'dna-2', name: 'Mary Cook descendant kit', surname: 'Cook', shared_cm: 142, segments: 8, longest_cm: 28, predicted: '3rd Cousin', chromosomes: [2, 7, 18] },
  { id: 'dna-3', name: 'Samuel Jackson Delaware Branch', surname: 'Jackson', shared_cm: 98, segments: 5, longest_cm: 22, predicted: '3rd Cousin 1x Removed', chromosomes: [3, 11] },
  { id: 'dna-4', name: 'Nanticoke Tribal Ancestry Kit', surname: 'Handsor', shared_cm: 412, segments: 16, longest_cm: 64, predicted: '1st Cousin 2x Removed / Half 1st Cousin', chromosomes: [1, 5, 8, 12, 15, 20] },
  { id: 'dna-5', name: 'Morris & Wright Cross-Match', surname: 'Morris', shared_cm: 76, segments: 4, longest_cm: 19, predicted: '4th Cousin', chromosomes: [6, 17] },
];

export default function DNAMatchExplorer({ onSelectPerson }) {
  const [selectedSurname, setSelectedSurname] = useState('ALL');
  const [selectedKit, setSelectedKit] = useState(SAMPLE_DNA_MATCHES[0]);

  const filteredMatches = selectedSurname === 'ALL'
    ? SAMPLE_DNA_MATCHES
    : SAMPLE_DNA_MATCHES.filter(m => m.surname === selectedSurname);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[#C68B59]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[#C68B59] font-mono text-xs font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Genetic Genealogy Integration</span>
            </div>
            <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
              DNA Cousin Match & Segment Browser
            </h2>
            <p className="text-xs text-[#A8A096] mt-1 max-w-xl">
              Inspect shared Centimorgan (cM) DNA segment overlaps, chromosome mapping visualizers, and estimated kinship tiers for Delmarva kits.
            </p>
          </div>
          <div className="bg-[#1C1A17] border border-[#332D27] px-4 py-2.5 rounded-xl text-right shrink-0">
            <span className="text-[10px] uppercase font-mono text-[#8C8275] block">GEDmatch & FTDNA Ready</span>
            <span className="text-sm font-bold font-mono text-[#D4A373]">Autosomal & mtDNA</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Kit Matches List */}
        <div className="lg:col-span-1 bg-[#141210] border border-[#26221E] rounded-2xl p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#26221E] pb-3">
            <div className="flex items-center gap-2 font-semibold text-xs text-[#F3EBE3]">
              <Dna className="w-4 h-4 text-[#C68B59]" />
              <span>DNA Match Kits</span>
            </div>
            <select
              value={selectedSurname}
              onChange={e => setSelectedSurname(e.target.value)}
              className="bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-lg px-2.5 py-1 text-xs text-[#F3EBE3] outline-none"
            >
              <option value="ALL">All Lines</option>
              <option value="Davis">Davis</option>
              <option value="Cook">Cook</option>
              <option value="Jackson">Jackson</option>
              <option value="Handsor">Handsor</option>
              <option value="Morris">Morris</option>
            </select>
          </div>

          <div className="space-y-2">
            {filteredMatches.map(kit => {
              const isSelected = selectedKit.id === kit.id;
              return (
                <div
                  key={kit.id}
                  onClick={() => setSelectedKit(kit)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-1.5 ${
                    isSelected
                      ? 'bg-[#C68B59]/15 border-[#C68B59] text-[#F3EBE3]'
                      : 'bg-[#1C1A17] border-[#332D27] hover:border-[#6E665B] text-[#A8A096]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-xs text-[#F3EBE3]">{kit.name}</h4>
                    <span className="text-[10px] font-mono text-[#D4A373] font-bold">{kit.shared_cm} cM</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-[#8C8275]">
                    <span>{kit.predicted}</span>
                    <span>{kit.segments} Segments</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chromosome Browser & Detailed Kit Stats */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-[#26221E] pb-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#8C8275]">Selected Kit Profile</span>
                <h3 className="text-lg font-bold text-[#F3EBE3]">{selectedKit.name}</h3>
              </div>
              <div className="text-right font-mono">
                <span className="text-[10px] uppercase text-[#8C8275] block">Predicted Relationship</span>
                <span className="text-sm font-bold text-[#C68B59]">{selectedKit.predicted}</span>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 font-mono">
              <div className="bg-[#1C1A17] border border-[#332D27] p-3 rounded-xl">
                <span className="text-[10px] text-[#8C8275] block">Total Shared DNA</span>
                <strong className="text-base text-[#F3EBE3]">{selectedKit.shared_cm} cM</strong>
              </div>
              <div className="bg-[#1C1A17] border border-[#332D27] p-3 rounded-xl">
                <span className="text-[10px] text-[#8C8275] block">Longest Block</span>
                <strong className="text-base text-[#F3EBE3]">{selectedKit.longest_cm} cM</strong>
              </div>
              <div className="bg-[#1C1A17] border border-[#332D27] p-3 rounded-xl">
                <span className="text-[10px] text-[#8C8275] block">Matching Segments</span>
                <strong className="text-base text-[#F3EBE3]">{selectedKit.segments}</strong>
              </div>
            </div>

            {/* Simulated 22 Chromosome Pair Map */}
            <div className="space-y-3">
              <span className="text-xs font-mono text-[#D4A373] uppercase font-semibold block flex items-center gap-1.5">
                <Dna className="w-3.5 h-3.5" />
                <span>Autosomal Chromosome Painting (Chr 1 – 22)</span>
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[10px]">
                {Array.from({ length: 22 }, (_, i) => i + 1).map(chrNum => {
                  const isMatch = selectedKit.chromosomes.includes(chrNum);
                  return (
                    <div
                      key={chrNum}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isMatch
                          ? 'bg-[#C68B59]/20 border-[#C68B59] text-[#F3EBE3]'
                          : 'bg-[#1C1A17] border-[#26221E] text-[#8C8275] opacity-50'
                      }`}
                    >
                      <span className="w-10 font-bold shrink-0">Chr {chrNum}</span>
                      <div className="flex-1 h-2 bg-[#26221E] rounded-full overflow-hidden relative">
                        {isMatch && (
                          <div
                            className="h-full bg-gradient-to-r from-[#C68B59] to-[#D4A373] rounded-full animate-pulse"
                            style={{
                              width: `${Math.min(90, Math.max(30, (selectedKit.shared_cm * chrNum) % 80))}%`,
                              marginLeft: `${(chrNum * 7) % 30}%`
                            }}
                          />
                        )}
                      </div>
                      <span className="w-12 text-right shrink-0">{isMatch ? 'Match' : '—'}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
