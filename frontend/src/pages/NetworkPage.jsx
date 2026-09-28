import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { GitFork, Sparkles, Filter, RefreshCw } from 'lucide-react';
import { fetchCachedJson } from '../utils/apiCache';

const NetworkGraph = lazy(() => import('../components/NetworkGraph'));

export default function NetworkPage() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const queryParams = new URLSearchParams(location.search);
  const surnameFilter = queryParams.get('surname') || null;

  useEffect(() => {
    setLoading(true);
    fetchCachedJson('/api/graph.json')
      .then(data => {
        if (surnameFilter && data.nodes) {
          const lowerS = surnameFilter.toLowerCase();
          const surnameNodeIds = new Set(
            data.nodes
              .filter(n => n.label?.toLowerCase().includes(lowerS) || n.group?.toLowerCase().includes(lowerS))
              .map(n => n.id)
          );

          const familyNodeIds = new Set(surnameNodeIds);
          (data.edges || []).forEach(e => {
            if (surnameNodeIds.has(e.from)) familyNodeIds.add(e.to);
            if (surnameNodeIds.has(e.to)) familyNodeIds.add(e.from);
          });

          const filteredNodes = data.nodes.filter(n => familyNodeIds.has(n.id));
          const filteredEdges = (data.edges || []).filter(e => familyNodeIds.has(e.from) && familyNodeIds.has(e.to));

          setGraphData({ nodes: filteredNodes, edges: filteredEdges });
        } else {
          setGraphData(data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load graph data:", err);
        setLoading(false);
      });
  }, [surnameFilter]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header toolbar */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-xs font-mono text-cyan-300 mb-2">
            <GitFork className="w-3.5 h-3.5" />
            <span>Interactive Kinship Network</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Multi-Generational Kinship Graph
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl">
            {surnameFilter 
              ? `Filtered view for ${surnameFilter} lineage and 1st-degree connected kin.`
              : 'Explore verified parent-child and spousal ties across the Delmarva Afro-Indigenous remnant lineages.'
            }
          </p>
        </div>

        {surnameFilter && (
          <button
            onClick={() => navigate('/network')}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-[#141210] border border-[#3A322B] text-xs font-mono text-[#D4A373] hover:text-[#F3EBE3] self-start"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Clan Filter</span>
          </button>
        )}
      </div>

      {/* Main Graph Canvas */}
      <div className="bg-[#121110] border border-[#26221E] rounded-2xl overflow-hidden shadow-2xl min-h-[650px] relative">
        {loading ? (
          <div className="p-24 text-center text-xs font-mono text-[#8C8275]">
            <div className="inline-block w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin mb-3" />
            <p>Constructing kinship force graph...</p>
          </div>
        ) : (
          <Suspense fallback={
            <div className="p-24 text-center text-xs font-mono text-[#8C8275]">
              <div className="inline-block w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin mb-3" />
              <p>Mounting vis-network physics engine...</p>
            </div>
          }>
            <NetworkGraph
              graphData={graphData}
              onSelectPerson={(id) => navigate(`/ancestors/${id}`)}
              onSelectNode={(node) => navigate(`/ancestors/${node.id}`)}
              selectedSurname={surnameFilter}
            />
          </Suspense>
        )}
      </div>
    </div>
  );
}
