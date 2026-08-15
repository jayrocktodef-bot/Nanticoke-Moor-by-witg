import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { ZoomIn, ZoomOut, RotateCcw, GitBranch, Layers, Search, Users, LayoutGrid, Network as NetworkIcon, ChevronRight, User } from 'lucide-react';

const EDGE_STYLES = {
  child_of: { color: '#f59e0b', highlight: '#fbbf24', dashes: false, width: 2.5, label: 'Child of' },
  parent_of: { color: '#f59e0b', highlight: '#fbbf24', dashes: false, width: 2.5, label: 'Parent of' },
  spouse: { color: '#f43f5e', highlight: '#fb7185', dashes: [5, 5], width: 2, label: 'Spouse' },
  cross_dataset_match: { color: '#10b981', highlight: '#34d399', dashes: [2, 4], width: 1.5, label: 'Matched Record' },
  default: { color: '#38bdf8', highlight: '#60a5fa', dashes: false, width: 1.5, label: 'Related' }
};

export default function NetworkGraph({ graphData, onSelectNode }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [viewFormat, setViewFormat] = useState('focus'); // Default to high-performance Focus Network
  const [searchFilter, setSearchFilter] = useState('');
  const [focalNodeId, setFocalNodeId] = useState(null); // Person focused on in network view

  // 1. Render vis-network when in 'tree' or 'focus' view format
  useEffect(() => {
    if (viewFormat === 'roster' || !containerRef.current || !graphData || !graphData.nodes) return;

    let displayNodes = graphData.nodes;
    let displayEdges = graphData.edges;

    // In Focus mode, if a focal person is set, filter to 2-degree immediate relatives for ultra 60FPS performance
    if (viewFormat === 'focus' && focalNodeId) {
      const neighborIds = new Set([focalNodeId]);
      // Degree 1
      graphData.edges.forEach(e => {
        if (e.from === focalNodeId) neighborIds.add(e.to);
        if (e.to === focalNodeId) neighborIds.add(e.from);
      });
      // Degree 2
      graphData.edges.forEach(e => {
        if (neighborIds.has(e.from)) neighborIds.add(e.to);
        if (neighborIds.has(e.to)) neighborIds.add(e.from);
      });
      displayNodes = graphData.nodes.filter(n => neighborIds.has(n.id));
      displayEdges = graphData.edges.filter(e => neighborIds.has(e.from) && neighborIds.has(e.to));
    }

    // Filter nodes if search query present
    if (searchFilter) {
      const q = searchFilter.toLowerCase();
      displayNodes = displayNodes.filter(n => n.label.toLowerCase().includes(q) || (n.group && n.group.toLowerCase().includes(q)));
      const nodeIds = new Set(displayNodes.map(n => n.id));
      displayEdges = displayEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
    }

    // Process Nodes
    const visNodes = new DataSet(
      displayNodes.map(n => ({
        id: n.id,
        label: n.label,
        shape: 'box',
        color: {
          background: n.id === focalNodeId ? '#c68b59' : '#0f172a',
          border: n.id === focalNodeId ? '#f59e0b' : '#334155',
          highlight: { background: '#1e293b', border: '#f59e0b' },
          hover: { background: '#1e293b', border: '#38bdf8' }
        },
        font: { color: '#f8fafc', face: 'ui-sans-serif, system-ui', size: 12, bold: true },
        margin: { top: 10, bottom: 10, left: 14, right: 14 },
        borderWidth: n.id === focalNodeId ? 2.5 : 1.5,
        title: `Person: ${n.label}\nSource: ${n.source_page || 'Preserved Record'}`
      }))
    );

    // Process Edges
    const visEdges = new DataSet(
      displayEdges.map((e, idx) => {
        const style = EDGE_STYLES[e.type] || EDGE_STYLES.default;
        const isUncertain = e.certainty === 'uncertain';
        return {
          id: idx,
          from: e.from,
          to: e.to,
          label: isUncertain ? `? ${style.label}` : style.label,
          font: { color: isUncertain ? '#f87171' : style.color, size: 10, align: 'middle', background: '#090d16' },
          color: { color: isUncertain ? '#f87171' : style.color, highlight: style.highlight, hover: style.highlight, opacity: isUncertain ? 0.7 : 1.0 },
          dashes: isUncertain ? [4, 4] : style.dashes,
          width: style.width,
          arrows: e.type === 'spouse' ? undefined : { to: { enabled: true, scaleFactor: 0.7 } },
          smooth: viewFormat === 'tree' ? { type: 'cubicBezier', forceDirection: 'vertical' } : { type: 'continuous' }
        };
      })
    );

    // Options for Clean Layout
    const options = {
      nodes: { shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 6 } },
      edges: { shadow: false },
      layout: viewFormat === 'tree' ? {
        hierarchical: {
          enabled: true,
          direction: 'UD', // Up-Down top-down family tree
          sortMethod: 'directed',
          nodeSpacing: 180,
          levelSeparation: 140,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true,
          parentCentralization: true
        }
      } : {
        hierarchical: { enabled: false }
      },
      physics: viewFormat === 'tree' ? false : {
        barnesHut: {
          gravitationalConstant: -6000,
          centralGravity: 0.15,
          springLength: 160,
          springConstant: 0.03,
          damping: 0.09
        },
        maxVelocity: 30,
        minVelocity: 0.75,
        solver: 'barnesHut'
      },
      interaction: {
        dragNodes: viewFormat === 'focus',
        dragView: true,
        zoomView: true,
        hover: true,
        tooltipDelay: 100
      }
    };

    networkRef.current = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);

    // Select Node Event
    networkRef.current.on('selectNode', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        setFocalNodeId(nodeId);
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (node && onSelectNode) {
          onSelectNode(node);
        }
        setTimeout(() => {
          if (networkRef.current) {
            networkRef.current.unselectAll();
          }
        }, 150);
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [graphData, viewFormat, searchFilter, focalNodeId]);

  const handleZoomIn = () => networkRef.current && networkRef.current.zoomIn();
  const handleZoomOut = () => networkRef.current && networkRef.current.zoomOut();
  const handleReset = () => networkRef.current && networkRef.current.fit({ animation: true });

  // Group nodes by surname for Roster View
  const familyGroups = {};
  if (graphData && graphData.nodes) {
    graphData.nodes.forEach(n => {
      const surname = n.group || (n.label.split(' ').pop()) || 'Other';
      if (!familyGroups[surname]) familyGroups[surname] = [];
      familyGroups[surname].push(n);
    });
  }

  return (
    <div className="w-full h-[580px] max-h-[580px] bg-slate-950 rounded-xl border border-slate-800 relative overflow-hidden flex flex-col">
      {/* Top Controls Toolbar */}
      <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 z-10">
        {/* View Format Switcher Buttons */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider hidden sm:inline">
            Display Format:
          </span>
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs gap-1">
            <button
              onClick={() => setViewFormat('focus')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                viewFormat === 'focus'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <NetworkIcon className="w-3.5 h-3.5" />
              Focus Network (Interactive)
            </button>

            <button
              onClick={() => setViewFormat('tree')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                viewFormat === 'tree'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              Family Tree View
            </button>

            <button
              onClick={() => setViewFormat('roster')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-all ${
                viewFormat === 'roster'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              Organized Family Cards
            </button>
          </div>
        </div>

        {/* Filter Input */}
        <div className="flex items-center gap-2">
          <div className="relative w-48 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by person name..."
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
              className="w-full pl-8 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
            />
          </div>

          {viewFormat !== 'roster' && (
            <div className="flex items-center gap-1">
              <button onClick={handleZoomIn} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Zoom In">
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button onClick={handleZoomOut} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Zoom Out">
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button onClick={handleReset} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Fit to Screen">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Legend & Instructions Bar */}
      <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
        <span className="text-[11px] italic">
          {viewFormat === 'tree' && '🌲 Top-Down Generational Tree Layout — Nodes arranged hierarchically from ancestors to descendants.'}
          {viewFormat === 'roster' && '🗂️ Organized Family Cards Layout — Lineages grouped neatly into structured family rosters.'}
          {viewFormat === 'focus' && '🕸️ Focus Network Layout — Interactive force graph. Drag or click nodes to open profile cards.'}
        </span>

        <div className="flex items-center gap-3 font-medium text-[11px]">
          <span className="flex items-center gap-1 text-amber-400">
            <span className="w-2.5 h-1 bg-amber-400 rounded" /> Parent-Child
          </span>
          <span className="flex items-center gap-1 text-rose-400">
            <span className="w-2.5 h-1 bg-rose-400 rounded" /> Spouse
          </span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-2.5 h-1 bg-emerald-400 rounded" /> Matched Record
          </span>
        </div>
      </div>

      {/* Main View Display */}
      {viewFormat === 'roster' ? (
        /* Organized Family Cards View */
        <div className="flex-1 p-6 overflow-y-auto bg-slate-950 space-y-6">
          {Object.keys(familyGroups).sort().map(surname => {
            const members = familyGroups[surname].filter(n =>
              !searchFilter || n.label.toLowerCase().includes(searchFilter.toLowerCase())
            );
            if (members.length === 0) return null;

            return (
              <div key={surname} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
                  <h3 className="text-base font-bold text-amber-400 flex items-center gap-2">
                    <Users className="w-4 h-4 text-amber-400" />
                    The {surname} Lineage ({members.length} members)
                  </h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {members.map(member => (
                    <div
                      key={member.id}
                      onClick={() => onSelectNode && onSelectNode(member)}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-lg hover:border-amber-500/50 cursor-pointer flex items-center justify-between transition-all group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 bg-slate-800 text-slate-300 rounded-lg group-hover:bg-amber-500/20 group-hover:text-amber-400 transition-colors">
                          <User className="w-4 h-4" />
                        </div>
                        <div>
                          <span className="font-semibold text-xs text-slate-200 group-hover:text-amber-300 block">
                            {member.label}
                          </span>
                          <span className="text-[10px] text-slate-500 block truncate max-w-[160px]">
                            {member.source_page}
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-amber-400 transition-colors" />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Vis-Network Canvas (Tree & Focus Modes) */
        <div className="flex-1 relative w-full h-full min-h-[500px] bg-slate-950">
          <div ref={containerRef} className="w-full h-full min-h-[500px]" />
        </div>
      )}
    </div>
  );
}
