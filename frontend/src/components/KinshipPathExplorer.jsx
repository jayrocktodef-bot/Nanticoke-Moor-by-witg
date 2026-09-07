import React, { useState, useEffect, useMemo } from 'react';
import { GitCommit, User, ArrowRight, Sparkles, Copy, Check, Search, Share2 } from 'lucide-react';

export default function KinshipPathExplorer({ onSelectPerson }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  
  const [personA, setPersonA] = useState('');
  const [personB, setPersonB] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch('/api/graph.json')
      .then(res => res.json())
      .then(data => {
        setGraphData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load graph for kinship:", err);
        setLoading(false);
      });
  }, []);

  const personOptions = useMemo(() => {
    return (graphData.nodes || [])
      .map(n => ({ id: n.id, name: n.label || 'Unknown', group: n.group }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [graphData.nodes]);

  // BFS Shortest Path Finder
  const pathResult = useMemo(() => {
    if (!personA || !personB || personA === personB) return null;

    const adj = new Map();
    (graphData.edges || []).forEach(e => {
      if (!adj.has(e.from)) adj.set(e.from, []);
      if (!adj.has(e.to)) adj.set(e.to, []);
      adj.get(e.from).push({ target: e.to, label: e.label || 'relative' });
      adj.get(e.to).push({ target: e.from, label: e.label || 'relative' });
    });

    const queue = [[personA]];
    const visited = new Set([personA]);

    while (queue.length > 0) {
      const path = queue.shift();
      const curr = path[path.length - 1];

      if (curr === personB) {
        return path.map(id => {
          const node = graphData.nodes.find(n => n.id === id);
          return { id, name: node?.label || id, group: node?.group };
        });
      }

      const neighbors = adj.get(curr) || [];
      for (const edge of neighbors) {
        if (!visited.has(edge.target)) {
          visited.add(edge.target);
          queue.push([...path, edge.target]);
        }
      }
    }

    return null; // No path found
  }, [personA, personB, graphData]);

  const pathCitation = useMemo(() => {
    if (!pathResult) return '';
    return pathResult.map(p => p.name).join(' ⟶ ');
  }, [pathResult]);

  const handleCopyCitation = () => {
    if (!pathCitation) return;
    navigator.clipboard.writeText(`Kinship Path: ${pathCitation} (Source: Delmarva Genealogy Archive)`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[#C68B59]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[#C68B59] font-mono text-xs font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Genealogical Lineage Calculator</span>
            </div>
            <h2 className="text-2xl font-bold font-serif-header text-[#F3EBE3]">
              Kinship Path Explorer
            </h2>
            <p className="text-xs text-[#A8A096] mt-1 max-w-xl">
              Trace the exact intergenerational kinship chain connecting any two individuals across Nanticoke and Delmarva family lines.
            </p>
          </div>
        </div>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl">
        <div className="space-y-2">
          <label className="text-xs font-mono text-[#D4A373] uppercase font-semibold block flex items-center gap-1.5">
            <User className="w-3.5 h-3.5" />
            <span>First Individual (Ancestor or Kin)</span>
          </label>
          <select
            value={personA}
            onChange={e => setPersonA(e.target.value)}
            className="w-full bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl p-3 text-xs text-[#F3EBE3] outline-none transition-colors"
          >
            <option value="">Select First Person...</option>
            {personOptions.map(p => (
              <option key={`a-${p.id}`} value={p.id}>{p.name} ({p.group || 'Family'})</option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-mono text-[#D4A373] uppercase font-semibold block flex items-center gap-1.5">
            <User className="w-3.5 h-3.5" />
            <span>Second Individual (Target Kin)</span>
          </label>
          <select
            value={personB}
            onChange={e => setPersonB(e.target.value)}
            className="w-full bg-[#1C1A17] border border-[#332D27] focus:border-[#C68B59] rounded-xl p-3 text-xs text-[#F3EBE3] outline-none transition-colors"
          >
            <option value="">Select Second Person...</option>
            {personOptions.map(p => (
              <option key={`b-${p.id}`} value={p.id}>{p.name} ({p.group || 'Family'})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results Display */}
      {personA && personB && (
        <div className="bg-[#141210] border border-[#26221E] rounded-2xl p-6 shadow-xl space-y-6">
          {!pathResult ? (
            <div className="text-center py-8 text-[#A8A096] space-y-2">
              <GitCommit className="w-8 h-8 mx-auto text-[#6E665B]" />
              <p className="text-sm font-semibold text-[#F3EBE3]">No Direct Kinship Connection Recorded</p>
              <p className="text-xs text-[#8C8275] max-w-md mx-auto">
                These individuals do not share a recorded familial edge in the current holdings.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-[#26221E] pb-4">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#8C8275]">Degree of Separation</span>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-[#F3EBE3]">
                      {pathResult.length - 1} Generation / Relation Step{pathResult.length - 1 > 1 ? 's' : ''}
                    </h3>
                  </div>
                </div>

                <button
                  onClick={handleCopyCitation}
                  className="px-3.5 py-2 bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] text-[#D4A373] hover:text-[#F3EBE3] rounded-xl text-xs font-semibold flex items-center gap-2 transition-all active:scale-[0.98]"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Citation Copied!' : 'Copy Kinship Path'}</span>
                </button>
              </div>

              {/* Visual Path Flow */}
              <div className="flex flex-wrap items-center gap-3 py-4">
                {pathResult.map((node, index) => (
                  <React.Fragment key={node.id}>
                    <div
                      onClick={() => onSelectPerson && onSelectPerson(node.id)}
                      className="bg-[#1C1A17] border border-[#332D27] hover:border-[#C68B59] px-4 py-3 rounded-xl transition-all cursor-pointer group shadow-md"
                    >
                      <span className="text-[10px] font-mono text-[#8C8275] block">
                        Step {index + 1}
                      </span>
                      <strong className="text-xs font-semibold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors block">
                        {node.name}
                      </strong>
                      <span className="text-[10px] text-[#A8A096] font-mono">
                        {node.group || 'Family'}
                      </span>
                    </div>

                    {index < pathResult.length - 1 && (
                      <ArrowRight className="w-4 h-4 text-[#C68B59] shrink-0" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
