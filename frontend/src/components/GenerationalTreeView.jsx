import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  User, Users, GitBranch, ArrowUpRight, ShieldCheck, Heart, 
  Sparkles, Target, Eye, EyeOff, Download, Copy, Check, ZoomIn, 
  ZoomOut, RotateCcw, Maximize2, Move, ExternalLink, ChevronRight,
  Layers, Search
} from 'lucide-react';
import { 
  buildGenealogicalHierarchy, 
  computePedigreeLayout, 
  generateDrawioXml, 
  downloadDrawioFile, 
  copyDrawioToClipboard 
} from '../utils/drawioPedigreeGenerator';
import { fetchCachedJson } from '../utils/apiCache';

export default function GenerationalTreeView({ 
  graphData: propGraphData, 
  initialGraphData, 
  rootPersonId, 
  focalId: propFocalId, 
  onSelectPerson, 
  onSelectNode 
}) {
  const containerRef = useRef(null);
  const [internalGraphData, setInternalGraphData] = useState(null);
  
  const rawGraph = propGraphData || initialGraphData || internalGraphData;

  useEffect(() => {
    if (!propGraphData && !initialGraphData && !internalGraphData) {
      fetchCachedJson('/api/graph.json')
        .then(res => {
          if (res && res.nodes) setInternalGraphData(res);
        })
        .catch(console.error);
    }
  }, [propGraphData, initialGraphData, internalGraphData]);

  const targetFocalProp = rootPersonId || propFocalId;
  const defaultFocal = rawGraph?.nodes?.[0]?.id ?? null;
  const [currentFocalId, setCurrentFocalId] = useState(targetFocalProp || defaultFocal);
  const [maxGenerations, setMaxGenerations] = useState(4);
  const [treeMode, setTreeMode] = useState('descendancy'); // 'descendancy' or 'ancestors'
  const [copiedXml, setCopiedXml] = useState(false);
  const [showDrawioInfo, setShowDrawioInfo] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  // Pan and Zoom State
  const [zoom, setZoom] = useState(0.9);
  const [pan, setPan] = useState({ x: 40, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const focalNodeId = currentFocalId || targetFocalProp || defaultFocal;

  // Sync if prop changes
  useEffect(() => {
    if (targetFocalProp) {
      setCurrentFocalId(targetFocalProp);
    }
  }, [targetFocalProp]);

  const handleSelect = (p) => {
    if (!p) return;
    if (onSelectPerson) {
      onSelectPerson(p.id ?? p.person_id ?? p);
    } else if (onSelectNode) {
      onSelectNode(p);
    }
  };

  const graphData = rawGraph;

  // Index nodes by ID
  const nodesById = useMemo(() => {
    const map = {};
    (graphData?.nodes || []).forEach(n => {
      map[Number(n.id)] = n;
    });
    return map;
  }, [graphData]);

  // Compute Layout via drawio-genetic-pedigree geometry engine
  const layout = useMemo(() => {
    if (!graphData || !nodesById[focalNodeId]) {
      return { nodes: [], edges: [], busBars: [], bounds: { width: 800, height: 600 } };
    }

    const model = buildGenealogicalHierarchy(focalNodeId, nodesById, graphData.edges || [], {
      mode: treeMode,
      maxGenerations
    });

    return computePedigreeLayout(model);
  }, [graphData, nodesById, focalNodeId, treeMode, maxGenerations]);

  const focalPerson = nodesById[focalNodeId] || graphData?.nodes?.[0];

  // Mouse pan handlers
  const handleMouseDown = (e) => {
    // Only drag on canvas background, not on buttons or cards
    if (e.target.closest('.pedigree-node-card') || e.target.closest('button') || e.target.closest('input')) {
      return;
    }
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    setZoom(prev => Math.min(Math.max(prev * zoomFactor, 0.35), 2.2));
  };

  // Attach non-passive wheel event
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, []);

  const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.2, 2.2));
  const handleZoomOut = () => setZoom(prev => Math.max(prev * 0.8, 0.35));
  const handleResetView = () => {
    setZoom(0.9);
    setPan({ x: 40, y: 30 });
  };

  const handleReRoot = (e, personId) => {
    e.stopPropagation();
    setCurrentFocalId(personId);
  };

  // Draw.io Export Handlers
  const handleDownloadDrawio = () => {
    const title = `${focalPerson?.label || 'Lineage'}_Genetic_Pedigree`;
    const xml = generateDrawioXml(layout, { title });
    downloadDrawioFile(xml, `${title}.drawio`);
  };

  const handleCopyDrawioXml = async () => {
    const title = `${focalPerson?.label || 'Lineage'}_Genetic_Pedigree`;
    const xml = generateDrawioXml(layout, { title });
    const ok = await copyDrawioToClipboard(xml);
    if (ok) {
      setCopiedXml(true);
      setTimeout(() => setCopiedXml(false), 2500);
    }
  };

  // Ancestor Search candidates
  const searchResults = useMemo(() => {
    if (!searchQuery.trim() || !graphData?.nodes) return [];
    const q = searchQuery.toLowerCase();
    return graphData.nodes
      .filter(n => (n.label || '').toLowerCase().includes(q))
      .slice(0, 8);
  }, [searchQuery, graphData]);

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center p-8 text-center text-[#9EA9B6] italic font-mono text-xs">
        No lineage data available for Generational Tree View.
      </div>
    );
  }

  return (
    <div className="w-full h-full relative bg-[#0B0F14] text-[#F3EBE3] flex flex-col overflow-hidden select-none">
      
      {/* TOP CONTROL TOOLBAR */}
      <div className="bg-[#121820]/95 backdrop-blur-md border-b border-[#243040] p-3 px-4 sm:px-6 flex flex-wrap items-center justify-between gap-3 z-30 shadow-md">
        
        {/* Left: Active Root Indicator & Search */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#C87D53]/15 border border-[#C87D53]/40 text-[#D4A373] rounded-xl shrink-0">
            <GitBranch className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#D4A373]">
                Pedigree Root:
              </span>
              <span className="text-xs font-serif-header font-bold text-[#F3EBE3] truncate max-w-[200px]">
                {focalPerson?.label || 'Unknown Progenitor'}
              </span>
            </div>
            <p className="text-[10px] text-[#9EA9B6] font-mono">
              {layout.nodes.length} individuals in {maxGenerations} generations
            </p>
          </div>

          {/* Quick-Jump Search */}
          <div className="relative ml-2 hidden md:block">
            <div className="flex items-center bg-[#0F141A] border border-[#243040] rounded-xl px-2.5 py-1 text-xs text-[#F3EBE3] focus-within:border-[#C87D53]">
              <Search className="w-3.5 h-3.5 text-[#9EA9B6] mr-1.5 shrink-0" />
              <input
                type="text"
                placeholder="Jump to ancestor..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSearchDropdown(true);
                }}
                onFocus={() => setShowSearchDropdown(true)}
                className="bg-transparent border-none outline-none text-xs text-[#F3EBE3] w-36 placeholder:text-[#64748B]"
              />
            </div>

            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 mt-1 w-64 bg-[#171E27] border border-[#243040] rounded-xl shadow-2xl overflow-hidden z-50">
                {searchResults.map(n => (
                  <button
                    key={n.id}
                    onClick={() => {
                      setCurrentFocalId(n.id);
                      setSearchQuery('');
                      setShowSearchDropdown(false);
                    }}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-[#C87D53]/20 hover:text-[#D4A373] flex items-center justify-between border-b border-[#243040]/50 last:border-none"
                  >
                    <span className="font-semibold truncate">{n.label}</span>
                    <span className="text-[10px] font-mono text-[#9EA9B6]">ID #{n.id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Generations & Draw.io Actions */}
        <div className="flex items-center gap-2">
          
          {/* Generation Depth Selector */}
          <div className="flex items-center gap-1 bg-[#171E27] border border-[#243040] rounded-xl p-0.5 text-xs font-mono">
            <span className="px-2 text-[10px] text-[#9EA9B6] font-bold">DEPTH:</span>
            {[2, 3, 4, 5].map(gen => (
              <button
                key={gen}
                onClick={() => setMaxGenerations(gen)}
                className={`px-2 py-0.5 rounded-lg transition-all ${
                  maxGenerations === gen
                    ? 'bg-[#C87D53] text-[#0F141A] font-bold'
                    : 'text-[#9EA9B6] hover:text-[#F3EBE3]'
                }`}
              >
                {gen}G
              </button>
            ))}
          </div>

          {/* Draw.io Export Action Group */}
          <div className="flex items-center gap-1.5 ml-1">
            <button
              onClick={handleDownloadDrawio}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#26221E] hover:bg-[#332D27] border border-[#C87D53]/50 hover:border-[#C87D53] text-[#D4A373] text-xs font-mono font-bold transition-all shadow-sm"
              title="Download uncompressed Draw.io / diagrams.net XML"
            >
              <Download className="w-3.5 h-3.5 text-[#C87D53]" />
              <span className="hidden sm:inline">Export Draw.io</span>
            </button>

            <button
              onClick={handleCopyDrawioXml}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[#171E27] hover:bg-[#202936] border border-[#243040] text-xs font-mono text-[#F3EBE3] transition-all shadow-sm"
              title="Copy Draw.io XML to clipboard for direct pasting into diagrams.net"
            >
              {copiedXml ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-[#9EA9B6]" />}
              <span className="hidden sm:inline">{copiedXml ? 'Copied XML!' : 'Copy XML'}</span>
            </button>

            <button
              onClick={() => setShowDrawioInfo(!showDrawioInfo)}
              className="p-1.5 rounded-xl bg-[#171E27] border border-[#243040] text-[#9EA9B6] hover:text-[#D4A373] text-xs transition-all"
              title="Draw.io Genetic Pedigree Instructions"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

      </div>

      {/* DRAW.IO INTEGRATION MODAL / DRAWER */}
      {showDrawioInfo && (
        <div className="bg-[#141A22] border-b border-[#243040] p-4 px-6 text-xs text-[#C5BCB2] space-y-2 z-20 animate-fade-in shadow-xl">
          <div className="flex items-center justify-between">
            <h4 className="font-serif-header text-sm font-bold text-[#E5B269] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> Draw.io / diagrams.net Standardized Pedigree Integration
            </h4>
            <button
              onClick={() => setShowDrawioInfo(false)}
              className="text-[#9EA9B6] hover:text-[#F3EBE3] text-xs font-mono"
            >
              Close
            </button>
          </div>
          <p className="text-[11px] leading-relaxed text-[#9EA9B6]">
            This lineage diagram adheres strictly to the <strong>drawio-genetic-pedigree</strong> specification. It uses mathematical coordinate indexing (60px height, 100px row delta), orthogonal bus-bar routing with 20px junction drops, and distinct vertex styling for ancestral unions and genetic matches.
          </p>
          <div className="flex flex-wrap items-center gap-4 pt-1 text-[11px] font-mono">
            <span className="text-[#D4A373]">1. Click &quot;Export Draw.io&quot; or &quot;Copy XML&quot;</span>
            <span className="text-slate-400">→</span>
            <a
              href="https://app.diagrams.net/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-400 hover:underline flex items-center gap-1 font-bold"
            >
              <span>2. Open app.diagrams.net</span>
              <ExternalLink className="w-3 h-3" />
            </a>
            <span className="text-slate-400">→</span>
            <span className="text-[#D4A373]">3. Choose &quot;Open Existing Diagram&quot; or paste XML via Arrange &gt; Insert &gt; Advanced</span>
          </div>
        </div>
      )}

      {/* FLOATING ZOOM / CANVAS CONTROLS */}
      <div className="absolute bottom-5 right-5 z-20 flex items-center gap-1 bg-[#171E27]/90 backdrop-blur-md border border-[#243040] p-1.5 rounded-2xl shadow-2xl">
        <button
          onClick={handleZoomIn}
          className="p-2 hover:bg-[#243040] text-[#F3EBE3] rounded-xl transition-all"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 hover:bg-[#243040] text-[#F3EBE3] rounded-xl transition-all"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleResetView}
          className="p-2 hover:bg-[#243040] text-[#F3EBE3] rounded-xl transition-all"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <div className="px-2 text-[10px] font-mono text-[#9EA9B6]">
          {Math.round(zoom * 100)}%
        </div>
      </div>

      {/* INTERACTIVE PEDIGREE CANVAS */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`flex-1 w-full h-full overflow-hidden relative cursor-grab ${
          isDragging ? 'cursor-grabbing' : ''
        }`}
        style={{
          backgroundImage: `
            radial-gradient(circle at 1px 1px, rgba(42, 54, 68, 0.45) 1px, transparent 0)
          `,
          backgroundSize: '24px 24px'
        }}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
            width: `${layout.bounds.width}px`,
            height: `${layout.bounds.height}px`,
            position: 'absolute',
            top: 0,
            left: 0
          }}
        >
          {/* SVG LAYER: ORTHOGONAL BUS-BAR CONNECTORS */}
          <svg
            className="absolute top-0 left-0 pointer-events-none"
            width={layout.bounds.width}
            height={layout.bounds.height}
            style={{ overflow: 'visible' }}
          >
            <defs>
              <linearGradient id="edgeGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#C87D53" />
                <stop offset="100%" stopColor="#E5B269" />
              </linearGradient>
            </defs>

            {/* Render Orthogonal Bus-Bar Systems */}
            {layout.busBars.map((bus) => (
              <g key={bus.id} className="transition-opacity duration-300">
                {/* 1. Parent drop line to bus */}
                <line
                  x1={bus.parentX}
                  y1={bus.yParentBottom}
                  x2={bus.parentX}
                  y2={bus.yBus}
                  stroke="#C87D53"
                  strokeWidth="2"
                  strokeLinecap="round"
                />

                {/* 2. Horizontal bus bar spanning children */}
                <line
                  x1={bus.minChildX}
                  y1={bus.yBus}
                  x2={bus.maxChildX}
                  y2={bus.yBus}
                  stroke="#D4A373"
                  strokeWidth="2"
                  strokeLinecap="round"
                />

                {/* Parent drop junction point */}
                <circle
                  cx={bus.parentX}
                  cy={bus.yBus}
                  r="3.5"
                  fill="#D4A373"
                  stroke="#0F141A"
                  strokeWidth="1.5"
                />

                {/* 3. Drops to individual children */}
                {bus.childDrops.map((drop) => (
                  <g key={`${bus.id}_drop_${drop.childId}`}>
                    <line
                      x1={drop.x}
                      y1={bus.yBus}
                      x2={drop.x}
                      y2={drop.yTop}
                      stroke="#C87D53"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <circle
                      cx={drop.x}
                      cy={drop.yTop}
                      r="3"
                      fill="#C87D53"
                      stroke="#0F141A"
                      strokeWidth="1.5"
                    />
                  </g>
                ))}
              </g>
            ))}
          </svg>

          {/* HTML LAYER: MATHEMATICALLY INDEXED VERTEX NODES */}
          {layout.nodes.map((node) => {
            const p1 = node.primaryPerson;
            const p2 = node.spousePerson;
            const isFocal = p1.id === focalNodeId;
            const isRootGen = node.genIndex === 1;

            return (
              <div
                key={`node_${node.genIndex}_${node.id}`}
                style={{
                  position: 'absolute',
                  left: `${node.x}px`,
                  top: `${node.y}px`,
                  width: `${node.width}px`,
                  height: `${node.height}px`
                }}
                onClick={() => handleSelect(p1)}
                className={`pedigree-node-card group rounded-2xl border transition-all cursor-pointer shadow-lg p-2.5 flex items-center justify-between ${
                  isFocal
                    ? 'bg-[#1C2633] border-[#C87D53] ring-2 ring-[#C87D53]/50 scale-[1.02] z-10'
                    : isRootGen
                    ? 'bg-[#18212D] border-[#D4A373]/60 hover:border-[#C87D53]'
                    : 'bg-[#121820]/95 border-[#243040] hover:border-[#C87D53] hover:bg-[#18212D]'
                }`}
              >
                {/* Node Content */}
                <div className="flex-1 min-w-0 pr-1">
                  
                  {/* Top Badge: Gen & Type */}
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[8px] font-mono font-bold uppercase px-1.5 py-0.2 rounded bg-[#243040] text-[#9EA9B6]">
                      GEN {node.genIndex}
                    </span>
                    {node.isCouple && (
                      <span className="text-[8px] font-mono font-semibold px-1.5 py-0.2 rounded bg-[#C87D53]/20 text-[#D4A373] flex items-center gap-0.5">
                        <Heart className="w-2.5 h-2.5 text-[#C87D53]" /> Union
                      </span>
                    )}
                    {isFocal && (
                      <span className="text-[8px] font-mono font-bold px-1.5 py-0.2 rounded bg-[#C87D53] text-[#0F141A]">
                        ROOT
                      </span>
                    )}
                  </div>

                  {/* Names Display */}
                  {node.isCouple && p2 ? (
                    <div className="space-y-0.5">
                      <h4 
                        onClick={(e) => { e.stopPropagation(); handleSelect(p1); }}
                        className="font-serif-header text-[11px] font-bold text-[#F3EBE3] hover:text-[#D4A373] truncate leading-tight"
                        title={`View profile for ${p1.label || p1.name}`}
                      >
                        {p1.label || p1.name}
                      </h4>
                      <h4 
                        onClick={(e) => { e.stopPropagation(); handleSelect(p2); }}
                        className="font-serif-header text-[11px] font-semibold text-[#D4A373] hover:text-[#F3EBE3] truncate leading-tight"
                        title={`View profile for ${p2.label || p2.name}`}
                      >
                        & {p2.label || p2.name}
                      </h4>
                    </div>
                  ) : (
                    <div>
                      <h4 className="font-serif-header text-xs font-bold text-[#F3EBE3] group-hover:text-[#D4A373] truncate leading-tight">
                        {p1.label || p1.name}
                      </h4>
                      <p className="text-[9px] text-[#9EA9B6] font-mono truncate mt-0.5">
                        {p1.birth_info || p1.source_page || 'Historical Ancestor'}
                      </p>
                    </div>
                  )}
                </div>

                {/* Right Action: Re-Root Button */}
                {!isFocal && (
                  <button
                    onClick={(e) => handleReRoot(e, p1.id)}
                    className="p-1.5 rounded-lg bg-[#0F141A] border border-[#243040] text-[#9EA9B6] hover:text-[#C87D53] hover:border-[#C87D53] transition-all opacity-0 group-hover:opacity-100 shrink-0 ml-1"
                    title="Re-root pedigree tree on this ancestor"
                  >
                    <Target className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
