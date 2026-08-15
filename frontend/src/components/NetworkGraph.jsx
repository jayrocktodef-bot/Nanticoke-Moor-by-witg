import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { ZoomIn, ZoomOut, RotateCcw, GitBranch, Search, Users, LayoutGrid, Network as NetworkIcon, ChevronRight, User, Maximize2, Minimize2, Sparkles, X, Target } from 'lucide-react';
import GenerationalTreeView from './GenerationalTreeView';

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
  const [viewFormat, setViewFormat] = useState('focus'); // 'focus' | 'tree' | 'roster'
  const [searchFilter, setSearchFilter] = useState('');
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [focalNodeId, setFocalNodeId] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Default focal node to first node if none selected
  const activeFocalId = focalNodeId || (graphData?.nodes?.[0]?.id ?? null);

  // 1. Render vis-network canvas
  useEffect(() => {
    if (viewFormat === 'roster' || !containerRef.current || !graphData || !graphData.nodes || graphData.nodes.length === 0) return;

    let displayNodes = graphData.nodes;
    let displayEdges = graphData.edges || [];

    // Focus View: Ego-centric 1-to-2 degree immediate family graph
    if (viewFormat === 'focus') {
      const centerId = activeFocalId;
      if (centerId) {
        const degree1 = new Set([centerId]);
        displayEdges.forEach(e => {
          if (e.from === centerId) degree1.add(e.to);
          if (e.to === centerId) degree1.add(e.from);
        });

        // Add 2nd degree if 1st degree is very small (< 4 nodes)
        const neighborIds = new Set(degree1);
        if (degree1.size < 4) {
          displayEdges.forEach(e => {
            if (degree1.has(e.from)) neighborIds.add(e.to);
            if (degree1.has(e.to)) neighborIds.add(e.from);
          });
        }

        displayNodes = graphData.nodes.filter(n => neighborIds.has(n.id));
        displayEdges = graphData.edges.filter(e => neighborIds.has(e.from) && neighborIds.has(e.to));
      }
    }

    // Filter by Search Query if active
    if (searchFilter && !showSearchDropdown) {
      const q = searchFilter.toLowerCase();
      displayNodes = displayNodes.filter(n => n.label.toLowerCase().includes(q) || (n.group && n.group.toLowerCase().includes(q)));
      const nodeIds = new Set(displayNodes.map(n => n.id));
      displayEdges = displayEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
    }

    // Format Nodes
    const visNodes = new DataSet(
      displayNodes.map(n => {
        const isFocal = n.id === activeFocalId;
        return {
          id: n.id,
          label: n.label,
          shape: 'box',
          color: {
            background: isFocal ? '#c68b59' : '#0f172a',
            border: isFocal ? '#f59e0b' : '#334155',
            highlight: { background: '#1e293b', border: '#f59e0b' },
            hover: { background: '#1e293b', border: '#38bdf8' }
          },
          font: { 
            color: isFocal ? '#ffffff' : '#f8fafc', 
            face: 'ui-sans-serif, system-ui', 
            size: isFocal ? 14 : 12, 
            bold: isFocal 
          },
          margin: { top: 10, bottom: 10, left: 14, right: 14 },
          borderWidth: isFocal ? 3 : 1.5,
          title: `Person: ${n.label}\nSource: ${n.source_page || 'Preserved Record'}`
        };
      })
    );

    // Format Edges
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

    // Network Config
    const options = {
      nodes: { shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 6 } },
      edges: { shadow: false },
      layout: viewFormat === 'tree' ? {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 160,
          levelSeparation: 120,
          treeSpacing: 180,
          blockShifting: true,
          edgeMinimization: true,
          parentCentralization: true
        }
      } : {
        hierarchical: { enabled: false }
      },
      physics: viewFormat === 'tree' ? false : {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -3500,
          centralGravity: 0.3,
          springLength: 130,
          springConstant: 0.04,
          damping: 0.1
        },
        stabilization: {
          enabled: true,
          iterations: 150,
          updateInterval: 25
        }
      },
      interaction: {
        dragNodes: true,
        dragView: true,
        zoomView: true,
        hover: true,
        tooltipDelay: 100
      }
    };

    networkRef.current = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);

    // Freeze physics once stabilized to ensure static readable layout
    if (viewFormat === 'focus') {
      networkRef.current.once('stabilized', () => {
        if (networkRef.current) {
          networkRef.current.setOptions({ physics: { enabled: false } });
        }
      });
    }

    // Node Selection Event
    networkRef.current.on('selectNode', (params) => {
      if (params.nodes.length > 0) {
        const selectedId = params.nodes[0];
        setFocalNodeId(selectedId);
        const nodeObj = graphData.nodes.find(n => n.id === selectedId);
        if (nodeObj && onSelectNode) {
          onSelectNode(nodeObj);
        }
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [graphData, viewFormat, searchFilter, activeFocalId]);

  // Controls Handlers
  const handleZoomIn = () => networkRef.current && networkRef.current.zoomIn();
  const handleZoomOut = () => networkRef.current && networkRef.current.zoomOut();
  const handleReset = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }
  };

  // Search Results Matching
  const searchResults = searchFilter.trim() && graphData?.nodes
    ? graphData.nodes.filter(n => n.label.toLowerCase().includes(searchFilter.toLowerCase())).slice(0, 8)
    : [];

  const handleSelectSearchResult = (node) => {
    setFocalNodeId(node.id);
    setSearchFilter('');
    setShowSearchDropdown(false);
    if (onSelectNode) onSelectNode(node);
  };

  // Group nodes by surname for Roster View
  const familyGroups = {};
  if (graphData && graphData.nodes) {
    graphData.nodes.forEach(n => {
      const surname = n.group || (n.label.split(' ').pop()) || 'Other';
      if (!familyGroups[surname]) familyGroups[surname] = [];
      familyGroups[surname].push(n);
    });
  }

  // Active focal person details
  const currentFocalPerson = graphData?.nodes?.find(n => n.id === activeFocalId);

  return (
    <div 
      className={`bg-slate-950 transition-all duration-300 flex flex-col ${
        isFullscreen 
          ? 'fixed inset-0 z-50 w-screen h-screen p-4' 
          : 'w-full h-[680px] rounded-xl border border-slate-800 relative overflow-hidden'
      }`}
    >
      {/* Top Controls Toolbar */}
      <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 z-20">
        
        {/* View Format Switcher */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider hidden sm:inline">
            Format:
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
              Focus Network (Ego View)
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

        {/* Search & Canvas Tools */}
        <div className="flex items-center gap-2">
          
          {/* Instant Search to Focus */}
          <div className="relative w-48 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search person to focus..."
              value={searchFilter}
              onFocus={() => setShowSearchDropdown(true)}
              onChange={e => {
                setSearchFilter(e.target.value);
                setShowSearchDropdown(true);
              }}
              className="w-full pl-8 pr-8 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
            />
            {searchFilter && (
              <button 
                onClick={() => setSearchFilter('')}
                className="absolute right-2.5 top-2 text-slate-500 hover:text-slate-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Dropdown Results */}
            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden max-h-60 overflow-y-auto">
                {searchResults.map(n => (
                  <button
                    key={n.id}
                    onClick={() => handleSelectSearchResult(n)}
                    className="w-full px-3 py-2 text-left hover:bg-slate-800 flex items-center justify-between border-b border-slate-800/50 last:border-0"
                  >
                    <span className="text-xs font-semibold text-slate-200">{n.label}</span>
                    <span className="text-[10px] text-amber-400 font-mono">Focus</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Zoom / Reset / Fullscreen Controls */}
          {viewFormat !== 'roster' && (
            <div className="flex items-center gap-1">
              <button onClick={handleZoomIn} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Zoom In">
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button onClick={handleZoomOut} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Zoom Out">
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button onClick={handleReset} className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg" title="Reset View & Center">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>

              {/* Fullscreen Toggle */}
              <button 
                onClick={() => setIsFullscreen(!isFullscreen)} 
                className="p-1.5 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg transition-colors ml-1"
                title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Expanded View"}
              >
                {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Sub-Header Status & Focal Information */}
      <div className="px-4 py-2 bg-slate-900/80 border-b border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2 z-10">
        <div className="flex items-center gap-2">
          {viewFormat === 'focus' && currentFocalPerson && (
            <span className="flex items-center gap-1.5 text-xs text-amber-300 font-semibold bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 rounded-md">
              <Target className="w-3.5 h-3.5 text-amber-400" />
              Focused Node: {currentFocalPerson.label}
            </span>
          )}
          <span className="text-[11px] italic text-slate-400 hidden md:inline">
            {viewFormat === 'tree' && '🌲 Top-Down Generational Tree — Hierarchical structure from ancestors to descendants.'}
            {viewFormat === 'roster' && '🗂️ Organized Family Cards — Lineages grouped into clean rosters.'}
            {viewFormat === 'focus' && '🎯 Ego-Centric Focus View — Showing immediate family network. Click nodes to pivot focus.'}
          </span>
        </div>

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

      {/* Main Content Display */}
      {viewFormat === 'tree' ? (
        <GenerationalTreeView 
          graphData={graphData} 
          onSelectNode={onSelectNode}
          focalId={activeFocalId}
        />
      ) : viewFormat === 'roster' ? (
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
        /* Vis-Network Canvas */
        <div className="flex-1 relative w-full h-full min-h-[450px] bg-slate-950">
          <div ref={containerRef} className="w-full h-full min-h-[450px]" />
        </div>
      )}
    </div>
  );
}
