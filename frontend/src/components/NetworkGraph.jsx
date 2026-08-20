import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { ZoomIn, ZoomOut, RotateCcw, GitBranch, Search, Users, LayoutGrid, Network as NetworkIcon, ChevronRight, User, Maximize2, Minimize2, Sparkles, X, Target, Lock } from 'lucide-react';
import GenerationalTreeView from './GenerationalTreeView';

const EDGE_STYLES = {
  child_of: { color: '#f59e0b', highlight: '#fbbf24', dashes: false, width: 2.5, label: 'Child of' },
  parent_of: { color: '#f59e0b', highlight: '#fbbf24', dashes: false, width: 2.5, label: 'Parent of' },
  spouse: { color: '#f43f5e', highlight: '#fb7185', dashes: [5, 5], width: 2, label: 'Spouse' },
  cross_dataset_match: { color: '#10b981', highlight: '#34d399', dashes: [2, 4], width: 1.5, label: 'Matched Record' },
  default: { color: '#38bdf8', highlight: '#60a5fa', dashes: false, width: 1.5, label: 'Related' }
};

export default function NetworkGraph({ graphData, onSelectNode, defaultViewFormat = 'focus' }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [viewFormat, setViewFormat] = useState(defaultViewFormat); // 'focus' | 'tree' | 'roster' | 'network'
  const [searchFilter, setSearchFilter] = useState('');
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [focalNodeId, setFocalNodeId] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [staticLayout, setStaticLayout] = useState({});

  // Fetch precomputed static generational & clan layout coordinates
  useEffect(() => {
    fetch('/api/layout.json')
      .then(res => res.json())
      .then(setStaticLayout)
      .catch(console.error);
  }, []);

  useEffect(() => {
    setViewFormat(defaultViewFormat);
  }, [defaultViewFormat]);

  // Reset focal node if graphData changes and previous focal is no longer in dataset
  useEffect(() => {
    if (focalNodeId && graphData?.nodes && !graphData.nodes.some(n => n.id === focalNodeId)) {
      setFocalNodeId(null);
    }
  }, [graphData]);

  // Default focal node to first valid node in current dataset if none selected or valid
  const isFocalValid = focalNodeId && graphData?.nodes?.some(n => n.id === focalNodeId);
  const activeFocalId = isFocalValid ? focalNodeId : (graphData?.nodes?.[0]?.id ?? null);

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
    } else if (viewFormat === 'network') {
      displayNodes = graphData.nodes;
      displayEdges = graphData.edges || [];
    }

    // Filter by Search Query if active
    if (searchFilter && !showSearchDropdown) {
      const q = searchFilter.toLowerCase();
      displayNodes = displayNodes.filter(n => n.label.toLowerCase().includes(q) || (n.group && n.group.toLowerCase().includes(q)));
      const nodeIds = new Set(displayNodes.map(n => n.id));
      displayEdges = displayEdges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
    }

    // Format Nodes with Static Layout Coordinates
    const visNodes = new DataSet(
      displayNodes.map(n => {
        const isFocal = n.id === activeFocalId;
        const coords = staticLayout[n.id];
        return {
          id: n.id,
          label: n.label,
          shape: 'box',
          x: coords ? coords.x : undefined,
          y: coords ? coords.y : undefined,
          physics: !coords, // Disable physics if static coordinates are present
          color: {
            background: isFocal ? '#C87D53' : '#171E27',
            border: isFocal ? '#D4A373' : '#2A3644',
            highlight: { background: '#212B37', border: '#D4A373' },
            hover: { background: '#212B37', border: '#C87D53' }
          },
          font: { 
            color: isFocal ? '#0F141A' : '#F3EBE3', 
            face: 'Plus Jakarta Sans, sans-serif', 
            size: isFocal ? 14 : 12, 
            bold: isFocal 
          },
          margin: { top: 10, bottom: 10, left: 14, right: 14 },
          borderWidth: isFocal ? 3 : 1.5,
          title: `Person: ${n.label}\nClan: ${coords?.clan || 'Nanticoke Lineage'}\nSource: ${n.source_page || 'Preserved Record'}`
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
          font: { color: isUncertain ? '#f87171' : style.color, size: 10, align: 'middle', background: '#0F141A' },
          color: { color: isUncertain ? '#f87171' : style.color, highlight: style.highlight, hover: style.highlight, opacity: isUncertain ? 0.7 : 1.0 },
          dashes: isUncertain ? [4, 4] : style.dashes,
          width: style.width,
          arrows: e.type === 'spouse' ? undefined : { to: { enabled: true, scaleFactor: 0.7 } },
          smooth: viewFormat === 'tree' ? { type: 'cubicBezier', forceDirection: 'vertical' } : { type: 'continuous' }
        };
      })
    );

    // Network Config (Static Precomputed vs Physics)
    const hasStaticCoords = Object.keys(staticLayout).length > 0;
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
      physics: (viewFormat === 'tree' || (viewFormat === 'network' && hasStaticCoords)) ? false : {
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
  }, [graphData, viewFormat, searchFilter, activeFocalId, staticLayout]);

  const handleZoomIn = () => networkRef.current?.moveTo({ scale: (networkRef.current.getScale() || 1) * 1.3 });
  const handleZoomOut = () => networkRef.current?.moveTo({ scale: (networkRef.current.getScale() || 1) / 1.3 });
  const handleResetZoom = () => networkRef.current?.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });

  const activeFocalNode = graphData?.nodes?.find(n => n.id === activeFocalId);

  return (
    <div className={`flex flex-col bg-[#0F141A] rounded-2xl border border-[#2A3644] overflow-hidden shadow-2xl transition-all ${isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'w-full h-[750px]'}`}>
      
      {/* GRAPH TOOLBAR & VIEW MODE SWITCHER */}
      <div className="bg-[#171E27] border-b border-[#2A3644] p-3 sm:p-4 flex flex-wrap items-center justify-between gap-3 shrink-0">
        
        {/* Format Selector */}
        <div className="flex items-center gap-1 bg-[#0F141A] p-1 rounded-xl border border-[#2A3644]">
          <button
            onClick={() => setViewFormat('focus')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewFormat === 'focus' ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow' : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            Focus View
          </button>
          
          <button
            onClick={() => setViewFormat('network')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewFormat === 'network' ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow' : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            Static Full Network
          </button>

          <button
            onClick={() => setViewFormat('tree')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewFormat === 'tree' ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow' : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            Family Tree View
          </button>

          <button
            onClick={() => setViewFormat('roster')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewFormat === 'roster' ? 'bg-[#C87D53] text-[#0F141A] font-bold shadow' : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            Organized Family Cards
          </button>
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-2">
          {/* Quick Person Search */}
          <div className="relative">
            <div className="flex items-center bg-[#0F141A] border border-[#2A3644] rounded-xl px-2.5 py-1 text-xs">
              <Search className="w-3.5 h-3.5 text-[#9EA9B6] mr-2" />
              <input
                type="text"
                placeholder="Search person to focus..."
                value={searchFilter}
                onChange={(e) => {
                  setSearchFilter(e.target.value);
                  setShowSearchDropdown(true);
                }}
                onFocus={() => setShowSearchDropdown(true)}
                className="bg-transparent text-[#F3EBE3] placeholder-[#64748B] text-xs focus:outline-none w-36 sm:w-48"
              />
              {searchFilter && (
                <button onClick={() => { setSearchFilter(''); setShowSearchDropdown(false); }} className="text-[#9EA9B6] hover:text-[#F3EBE3]">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Dropdown Suggestions */}
            {showSearchDropdown && searchFilter.trim() && (
              <div className="absolute top-full right-0 mt-1.5 w-64 bg-[#171E27] border border-[#2A3644] rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto custom-scrollbar">
                {graphData.nodes
                  .filter(n => n.label.toLowerCase().includes(searchFilter.toLowerCase()))
                  .slice(0, 15)
                  .map(node => (
                    <button
                      key={node.id}
                      onClick={() => {
                        setFocalNodeId(node.id);
                        setSearchFilter('');
                        setShowSearchDropdown(false);
                        if (onSelectNode) onSelectNode(node);
                      }}
                      className="w-full text-left px-3 py-2 text-xs hover:bg-[#212B37] text-[#F3EBE3] border-b border-[#2A3644]/50 flex items-center justify-between"
                    >
                      <span className="font-semibold truncate">{node.label}</span>
                      <span className="text-[10px] font-mono text-[#D4A373]">#{node.id}</span>
                    </button>
                  ))}
              </div>
            )}
          </div>

          {/* Canvas Controls */}
          {viewFormat !== 'roster' && (
            <div className="flex items-center gap-1 bg-[#0F141A] p-1 rounded-xl border border-[#2A3644]">
              <button onClick={handleZoomIn} className="p-1.5 text-[#9EA9B6] hover:text-[#F3EBE3] rounded-lg" title="Zoom In">
                <ZoomIn className="w-4 h-4" />
              </button>
              <button onClick={handleZoomOut} className="p-1.5 text-[#9EA9B6] hover:text-[#F3EBE3] rounded-lg" title="Zoom Out">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button onClick={handleResetZoom} className="p-1.5 text-[#9EA9B6] hover:text-[#F3EBE3] rounded-lg" title="Reset View">
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 bg-[#0F141A] border border-[#2A3644] hover:border-[#C87D53] text-[#9EA9B6] hover:text-[#F3EBE3] rounded-xl transition-all"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen View"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* GRAPH CANVAS OR ALTERNATE VIEWS */}
      <div className="flex-1 relative bg-[#0F141A] min-h-0">
        
        {/* Banner Legend */}
        {viewFormat !== 'roster' && (
          <div className="absolute top-3 left-3 z-10 bg-[#171E27]/90 backdrop-blur-md border border-[#2A3644] px-3 py-1.5 rounded-xl flex items-center gap-4 text-[11px] font-mono text-[#9EA9B6] shadow-lg">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" />
              Parent-Child
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#f43f5e]" />
              Spouse
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" />
              Matched Record
            </span>
          </div>
        )}

        {/* View Mode 1: Vis-Network Canvas */}
        {(viewFormat === 'focus' || viewFormat === 'network') && (
          <div ref={containerRef} className="w-full h-full" />
        )}

        {/* View Mode 2: Generational Tree View */}
        {viewFormat === 'tree' && (
          <GenerationalTreeView graphData={graphData} onSelectNode={onSelectNode} focalId={activeFocalId} />
        )}

        {/* View Mode 3: Roster Family Cards */}
        {viewFormat === 'roster' && (
          <div className="w-full h-full p-6 overflow-y-auto space-y-6 custom-scrollbar">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {graphData.nodes.map(n => (
                <div
                  key={n.id}
                  onClick={() => {
                    setFocalNodeId(n.id);
                    if (onSelectNode) onSelectNode(n);
                  }}
                  className="glass-panel glass-card-hover rounded-2xl p-4 cursor-pointer flex items-center gap-3 border border-[#2A3644]"
                >
                  <div className="w-10 h-10 rounded-xl bg-[#0F141A] border border-[#2A3644] flex items-center justify-center shrink-0">
                    <User className="w-5 h-5 text-[#C87D53]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-bold text-sm text-[#F3EBE3] truncate font-serif-header">{n.label}</h4>
                    <p className="text-[10px] font-mono text-[#9EA9B6] truncate mt-0.5">ID #{n.id}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
