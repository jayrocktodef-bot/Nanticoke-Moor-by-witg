import React, { useState } from 'react';
import { User, Users, ChevronDown, ChevronUp, GitBranch, ArrowUpRight, ShieldCheck, Heart, Sparkles, Target, Eye, EyeOff } from 'lucide-react';

export default function GenerationalTreeView({ graphData, onSelectNode, focalId: propFocalId }) {
  const defaultFocal = graphData?.nodes?.[0]?.id ?? null;
  const [currentFocalId, setCurrentFocalId] = useState(propFocalId || defaultFocal);
  const [isFocusMode, setIsFocusMode] = useState(false);

  const focalNodeId = propFocalId || currentFocalId || defaultFocal;

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="p-8 text-center text-[#9EA9B6] italic font-mono text-xs">
        No lineage data available for Generational Tree View.
      </div>
    );
  }

  const nodesById = {};
  graphData.nodes.forEach(n => { nodesById[n.id] = n; });

  const focalPerson = nodesById[focalNodeId] || graphData.nodes[0];
  const actualFocalId = focalPerson?.id;

  // Find Parents (Gen 2)
  const parentIds = new Set();
  (graphData.edges || []).forEach(e => {
    if (e.to === actualFocalId && (e.type === 'child_of' || e.type === 'parent_of')) parentIds.add(e.from);
    if (e.from === actualFocalId && e.type === 'parent_of') parentIds.add(e.to);
  });
  const parents = Array.from(parentIds).map(id => nodesById[id]).filter(Boolean);

  // Find Grandparents (Gen 1)
  const grandparentIds = new Set();
  (graphData.edges || []).forEach(e => {
    if (parentIds.has(e.to) && (e.type === 'child_of' || e.type === 'parent_of')) grandparentIds.add(e.from);
    if (parentIds.has(e.from) && e.type === 'parent_of') grandparentIds.add(e.to);
  });
  const grandparents = Array.from(grandparentIds).map(id => nodesById[id]).filter(Boolean);

  // Find Spouses (Gen 3)
  const spouseIds = new Set();
  (graphData.edges || []).forEach(e => {
    if (e.from === actualFocalId && e.type === 'spouse') spouseIds.add(e.to);
    if (e.to === actualFocalId && e.type === 'spouse') spouseIds.add(e.from);
  });
  const spouses = Array.from(spouseIds).map(id => nodesById[id]).filter(Boolean);

  // Find Children (Gen 4)
  const childrenIds = new Set();
  (graphData.edges || []).forEach(e => {
    if (e.from === actualFocalId && (e.type === 'child_of' || e.type === 'parent_of')) childrenIds.add(e.to);
    if (e.to === actualFocalId && e.type === 'child_of') childrenIds.add(e.from);
  });
  const children = Array.from(childrenIds).map(id => nodesById[id]).filter(Boolean);

  const handleReRoot = (e, personId) => {
    e.stopPropagation();
    setCurrentFocalId(personId);
  };

  const handleCardClick = (person) => {
    if (onSelectNode) onSelectNode(person);
  };

  const PersonCard = ({ person, roleTag, badgeColor }) => {
    const isFocal = person.id === actualFocalId;

    return (
      <div
        onClick={() => handleCardClick(person)}
        className={`group relative flex items-center gap-3 p-3.5 rounded-2xl border transition-all cursor-pointer shadow-md glass-card-hover ${
          isFocal
            ? 'bg-[#171E27] border-[#C87D53] ring-2 ring-[#C87D53]/40 scale-[1.02]'
            : isFocusMode
            ? 'bg-[#0F141A]/50 border-[#2A3644]/50 opacity-40 hover:opacity-100'
            : 'bg-[#171E27]/90 border-[#2A3644] hover:border-[#C87D53]'
        }`}
      >
        <div className="w-10 h-10 rounded-full bg-[#0F141A] border border-[#2A3644] flex items-center justify-center shrink-0 overflow-hidden group-hover:border-[#C87D53]">
          <User className="w-5 h-5 text-[#9EA9B6] group-hover:text-[#D4A373] transition-colors" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full font-mono ${badgeColor || 'bg-[#2A3644] text-[#9EA9B6]'}`}>
              {roleTag}
            </span>
          </div>
          <h4 className="font-serif-header text-sm text-[#F3EBE3] group-hover:text-[#D4A373] font-bold truncate leading-tight">
            {person.label}
          </h4>
          <p className="text-[10px] text-[#9EA9B6] font-mono truncate mt-0.5">
            {person.source_page || 'Preserved Record'}
          </p>
        </div>

        {!isFocal && (
          <button
            onClick={(e) => handleReRoot(e, person.id)}
            className="p-1.5 rounded-xl bg-[#0F141A] border border-[#2A3644] text-[#9EA9B6] hover:text-[#C87D53] hover:border-[#C87D53] transition-all opacity-0 group-hover:opacity-100"
            title="Re-root tree view on this person"
          >
            <Target className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-full p-4 sm:p-6 bg-[#0F141A] text-[#F3EBE3] overflow-y-auto space-y-6 custom-scrollbar">
      
      {/* Active Focus Header */}
      <div className="glass-panel rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-[#C87D53]/10 border border-[#C87D53]/30 text-[#C87D53] rounded-2xl">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#D4A373]">
              Generational Tree Root
            </span>
            <h3 className="font-serif-header text-2xl text-[#F3EBE3] font-bold">
              {focalPerson?.label}
            </h3>
          </div>
        </div>

        {/* Focus Mode Toggle */}
        <button
          onClick={() => setIsFocusMode(!isFocusMode)}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl border text-xs font-mono transition-all ${
            isFocusMode
              ? 'bg-[#C87D53] text-[#0F141A] font-bold border-[#C87D53]'
              : 'bg-[#171E27] border-[#2A3644] text-[#9EA9B6] hover:border-[#C87D53]'
          }`}
        >
          {isFocusMode ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          <span>{isFocusMode ? 'Focus Mode Active' : 'Enable Focus Mode'}</span>
        </button>
      </div>

      {/* GENERATION 1: GRANDPARENTS */}
      <div className="glass-panel rounded-2xl p-5 relative">
        <div className="flex items-center justify-between border-b border-[#2A3644] pb-3 mb-4">
          <span className="text-xs font-bold text-[#E5B269] uppercase tracking-widest flex items-center gap-2 font-mono">
            <Sparkles className="w-3.5 h-3.5 text-[#C87D53]" />
            Generation I — Grandparents & Ancestors ({grandparents.length})
          </span>
        </div>

        {grandparents.length === 0 ? (
          <div className="text-xs text-[#9EA9B6] italic font-mono py-2">No preceding ancestors linked in index.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {grandparents.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Grandparent" badgeColor="bg-[#1B3B2B] text-[#E5B269] border border-[#C87D53]/30" />
            ))}
          </div>
        )}
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-[#C87D53] to-[#D4A373]" />
      </div>

      {/* GENERATION 2: PARENTS */}
      <div className="glass-panel rounded-2xl p-5 relative">
        <div className="flex items-center justify-between border-b border-[#2A3644] pb-3 mb-4">
          <span className="text-xs font-bold text-[#D4A373] uppercase tracking-widest flex items-center gap-2 font-mono">
            <Users className="w-3.5 h-3.5 text-[#C87D53]" />
            Generation II — Parents ({parents.length})
          </span>
        </div>

        {parents.length === 0 ? (
          <div className="text-xs text-[#9EA9B6] italic font-mono py-2">No parent records directly indexed.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {parents.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Parent" badgeColor="bg-[#1B3B2B] text-[#E5B269] border border-[#C87D53]/30" />
            ))}
          </div>
        )}
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-[#D4A373] to-[#C87D53]" />
      </div>

      {/* GENERATION 3: FOCAL PERSON & SPOUSES */}
      <div className="glass-panel rounded-2xl p-5 border-[#C87D53]/50 ring-1 ring-[#C87D53]/20 relative">
        <div className="flex items-center justify-between border-b border-[#2A3644] pb-3 mb-4">
          <span className="text-xs font-bold text-[#C87D53] uppercase tracking-widest flex items-center gap-2 font-mono">
            <Target className="w-3.5 h-3.5 text-[#C87D53]" />
            Generation III — Primary Subject & Spouses
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          <PersonCard person={focalPerson} roleTag="Primary Subject" badgeColor="bg-[#C87D53] text-[#0F141A] font-bold" />
          {spouses.map(p => (
            <PersonCard key={p.id} person={p} roleTag="Spouse" badgeColor="bg-[#171E27] text-[#D4A373] border border-[#C87D53]/40" />
          ))}
        </div>
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-[#C87D53] to-[#E5B269]" />
      </div>

      {/* GENERATION 4: CHILDREN & DESCENDANTS */}
      <div className="glass-panel rounded-2xl p-5 relative">
        <div className="flex items-center justify-between border-b border-[#2A3644] pb-3 mb-4">
          <span className="text-xs font-bold text-[#E5B269] uppercase tracking-widest flex items-center gap-2 font-mono">
            <GitBranch className="w-3.5 h-3.5 text-[#C87D53]" />
            Generation IV — Children & Offspring ({children.length})
          </span>
        </div>

        {children.length === 0 ? (
          <div className="text-xs text-[#9EA9B6] italic font-mono py-2">No child records indexed for this individual.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {children.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Child" badgeColor="bg-[#1B3B2B] text-[#E5B269] border border-[#C87D53]/30" />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
