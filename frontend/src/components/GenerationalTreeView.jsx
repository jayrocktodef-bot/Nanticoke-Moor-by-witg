import React, { useState } from 'react';
import { User, Users, ChevronDown, ChevronUp, GitBranch, ArrowUpRight, ShieldCheck, Heart, Sparkles, Target } from 'lucide-react';

export default function GenerationalTreeView({ graphData, onSelectNode, focalId: propFocalId }) {
  const defaultFocal = graphData?.nodes?.[0]?.id ?? null;
  const [currentFocalId, setCurrentFocalId] = useState(propFocalId || defaultFocal);

  const focalNodeId = propFocalId || currentFocalId || defaultFocal;

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 italic">
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
        className={`group relative flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer shadow-md hover:shadow-xl ${
          isFocal
            ? 'bg-[#1C1A17] border-amber-500 ring-2 ring-amber-500/30 scale-[1.02]'
            : 'bg-slate-900/90 border-slate-800 hover:border-amber-500/50 hover:bg-slate-800/90'
        }`}
      >
        <div className="w-10 h-10 rounded-full bg-slate-950 border border-slate-700 flex items-center justify-center shrink-0 overflow-hidden group-hover:border-amber-500/50">
          <User className="w-5 h-5 text-slate-400 group-hover:text-amber-400 transition-colors" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${badgeColor || 'bg-slate-800 text-slate-400'}`}>
              {roleTag}
            </span>
          </div>
          <h4 className="font-serif-header text-sm text-[#F3EBE3] group-hover:text-amber-300 font-bold truncate leading-tight">
            {person.label}
          </h4>
          <p className="text-[10px] text-slate-400 truncate mt-0.5">
            {person.source_page || 'Preserved Record'}
          </p>
        </div>

        {!isFocal && (
          <button
            onClick={(e) => handleReRoot(e, person.id)}
            className="p-1.5 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-400 hover:text-amber-400 hover:border-amber-500/50 transition-all opacity-0 group-hover:opacity-100"
            title="Re-root tree view on this person"
          >
            <Target className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-full p-4 sm:p-6 bg-slate-950 text-[#E5E1DB] overflow-y-auto space-y-6 custom-scrollbar">
      
      {/* Active Focus Header */}
      <div className="bg-[#1C1A17] border border-[#332D27] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-xl">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#D4A373]">
              Generational Tree Root
            </span>
            <h3 className="font-serif-header text-xl text-[#F3EBE3] font-bold">
              {focalPerson?.label}
            </h3>
          </div>
        </div>

        <div className="text-xs text-slate-400 font-medium">
          Showing 4-Generation Lineage View
        </div>
      </div>

      {/* GENERATION 1: GRANDPARENTS */}
      <div className="rounded-2xl border border-purple-900/40 bg-gradient-to-r from-purple-950/20 via-slate-900/40 to-purple-950/20 p-5 shadow-lg relative">
        <div className="flex items-center justify-between border-b border-purple-900/30 pb-3 mb-4">
          <span className="text-xs font-bold text-purple-300 uppercase tracking-widest flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            Generation I — Grandparents & Ancestors ({grandparents.length})
          </span>
        </div>

        {grandparents.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-2">No preceding ancestors linked in index.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {grandparents.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Grandparent" badgeColor="bg-purple-900/40 text-purple-300 border border-purple-700/50" />
            ))}
          </div>
        )}
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-purple-500/50 to-amber-500/50" />
      </div>

      {/* GENERATION 2: PARENTS */}
      <div className="rounded-2xl border border-amber-900/40 bg-gradient-to-r from-amber-950/20 via-slate-900/40 to-amber-950/20 p-5 shadow-lg relative">
        <div className="flex items-center justify-between border-b border-amber-900/30 pb-3 mb-4">
          <span className="text-xs font-bold text-amber-300 uppercase tracking-widest flex items-center gap-2">
            <Users className="w-3.5 h-3.5 text-amber-400" />
            Generation II — Parents ({parents.length})
          </span>
        </div>

        {parents.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-2">No parent records directly indexed.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {parents.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Parent" badgeColor="bg-amber-900/40 text-amber-300 border border-amber-700/50" />
            ))}
          </div>
        )}
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-amber-500/50 to-yellow-500/50" />
      </div>

      {/* GENERATION 3: FOCAL PERSON & SPOUSES */}
      <div className="rounded-2xl border border-amber-500/50 bg-gradient-to-r from-amber-500/10 via-[#1C1A17] to-amber-500/10 p-5 shadow-xl relative ring-1 ring-amber-500/20">
        <div className="flex items-center justify-between border-b border-amber-500/20 pb-3 mb-4">
          <span className="text-xs font-bold text-amber-400 uppercase tracking-widest flex items-center gap-2">
            <Target className="w-3.5 h-3.5 text-amber-400" />
            Generation III — Primary Subject & Spouses
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          <PersonCard person={focalPerson} roleTag="Primary Subject" badgeColor="bg-amber-500 text-slate-950 font-bold" />
          {spouses.map(p => (
            <PersonCard key={p.id} person={p} roleTag="Spouse" badgeColor="bg-rose-900/40 text-rose-300 border border-rose-700/50" />
          ))}
        </div>
      </div>

      {/* GENERATION CONNECTOR BAR */}
      <div className="flex justify-center -my-2 z-10 relative">
        <div className="w-0.5 h-6 bg-gradient-to-b from-yellow-500/50 to-emerald-500/50" />
      </div>

      {/* GENERATION 4: CHILDREN & DESCENDANTS */}
      <div className="rounded-2xl border border-emerald-900/40 bg-gradient-to-r from-emerald-950/20 via-slate-900/40 to-emerald-950/20 p-5 shadow-lg relative">
        <div className="flex items-center justify-between border-b border-emerald-900/30 pb-3 mb-4">
          <span className="text-xs font-bold text-emerald-300 uppercase tracking-widest flex items-center gap-2">
            <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
            Generation IV — Children & Immediate Offspring ({children.length})
          </span>
        </div>

        {children.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-2">No child records indexed for this individual.</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {children.map(p => (
              <PersonCard key={p.id} person={p} roleTag="Child" badgeColor="bg-emerald-900/40 text-emerald-300 border border-emerald-700/50" />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
