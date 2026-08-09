import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, XCircle, GitMerge, Trash2, Eye, ChevronDown, Filter } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: '🔴', label: 'Critical' },
  warning: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: '🟡', label: 'Warning' },
  info: { bg: 'bg-sky-500/10', border: 'border-sky-500/30', text: 'text-sky-400', icon: '🔵', label: 'Info' },
};

const CATEGORY_LABELS = {
  duplicate_exact: 'Exact Duplicate',
  duplicate_fuzzy: 'Fuzzy Match',
  non_person: 'Non-Person Entity',
  lifespan: 'Lifespan Anomaly',
  age_gap: 'Age Gap Violation',
  circular: 'Circular Relationship',
  contradictory: 'Contradictory Data',
  orphaned: 'Orphaned Reference',
  orphaned_media: 'Missing Media',
  merge_quality: 'Merge Quality',
};

export default function AuditResolutionPanel() {
  const [flags, setFlags] = useState([]);
  const [summary, setSummary] = useState([]);
  const [filter, setFilter] = useState({ category: '', severity: '', showResolved: false });
  const [resolving, setResolving] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const fetchFlags = () => {
    fetch('/api/audit/flags.json')
      .then(r => r.json())
      .then(setFlags)
      .catch(() => setFlags([]));
  };

  const fetchSummary = () => {
    fetch('/api/audit/summary.json')
      .then(r => r.json())
      .then(setSummary)
      .catch(() => setSummary([]));
  };

  useEffect(() => { fetchFlags(); fetchSummary(); }, [filter]);

  const handleResolve = async (flagId, action, resolution) => {
    setResolving(flagId);
    try {
      await fetch(`/api/audit/resolve/${flagId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, resolution }),
      });
      fetchFlags();
      fetchSummary();
    } catch (e) {
      console.error('Failed to resolve:', e);
    } finally {
      setResolving(null);
    }
  };

  const totalUnresolved = summary.reduce((acc, s) => acc + (s.count - (s.resolved || 0)), 0);
  const totalResolved = summary.reduce((acc, s) => acc + (s.resolved || 0), 0);

  return (
    <div>
      {/* Summary Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Audit & Conflict Resolution</h2>
            <p className="text-xs text-slate-400">
              Review flagged discrepancies across merged datasets. Merge duplicates or dismiss false positives.
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="bg-amber-500/10 border border-amber-500/30 text-amber-400 px-3 py-1.5 rounded-lg font-mono">
              {totalUnresolved} unresolved
            </span>
            <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-lg font-mono">
              {totalResolved} resolved
            </span>
          </div>
        </div>

        {/* Category Summary Chips */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => setFilter(f => ({ ...f, category: '' }))}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              !filter.category
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            All
          </button>
          {summary.map(s => {
            const style = SEVERITY_STYLES[s.severity] || SEVERITY_STYLES.info;
            const unresolvedCount = s.count - (s.resolved || 0);
            if (unresolvedCount === 0) return null;
            return (
              <button
                key={`${s.category}-${s.severity}`}
                onClick={() => setFilter(f => ({ ...f, category: s.category }))}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 ${
                  filter.category === s.category
                    ? `${style.bg} ${style.border} ${style.text}`
                    : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>{style.icon}</span>
                <span>{CATEGORY_LABELS[s.category] || s.category}</span>
                <span className="font-mono font-bold">{unresolvedCount}</span>
              </button>
            );
          })}
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          {['', 'critical', 'warning', 'info'].map(sev => (
            <button
              key={sev}
              onClick={() => setFilter(f => ({ ...f, severity: sev }))}
              className={`px-2.5 py-1 rounded-md transition-all ${
                filter.severity === sev
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {sev || 'All Severities'}
            </button>
          ))}
          <label className="ml-4 flex items-center gap-1.5 text-slate-500 cursor-pointer">
            <input
              type="checkbox"
              checked={filter.showResolved}
              onChange={e => setFilter(f => ({ ...f, showResolved: e.target.checked }))}
              className="rounded border-slate-600"
            />
            Show resolved
          </label>
        </div>
      </div>

      {/* Flags List */}
      <div className="space-y-2">
        {flags.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-emerald-500/50" />
            <p className="text-sm font-medium">No unresolved flags match your filters</p>
          </div>
        )}

        {flags.map(flag => {
          const style = SEVERITY_STYLES[flag.severity] || SEVERITY_STYLES.info;
          const isExpanded = expandedId === flag.flag_id;
          const isDuplicate = flag.category === 'duplicate_exact' || flag.category === 'duplicate_fuzzy';
          const isResolved = !!flag.resolved_at;

          return (
            <div
              key={flag.flag_id}
              className={`rounded-xl border p-4 transition-all ${
                isResolved
                  ? 'bg-slate-900/30 border-slate-800/50 opacity-60'
                  : `${style.bg} ${style.border}`
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm">{style.icon}</span>
                    <span className={`text-[10px] uppercase font-bold tracking-wider ${style.text}`}>
                      {CATEGORY_LABELS[flag.category] || flag.category}
                    </span>
                    {isResolved && (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono">
                        ✓ Resolved
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-200 leading-snug">{flag.description}</p>
                  {flag.person_name && (
                    <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400">
                      <span className="bg-slate-800 px-2 py-0.5 rounded font-mono">#{flag.person_id}</span>
                      <span>{flag.person_name}</span>
                      {flag.person_secondary_name && (
                        <>
                          <span className="text-slate-600">↔</span>
                          <span className="bg-slate-800 px-2 py-0.5 rounded font-mono">#{flag.person_id_secondary}</span>
                          <span>{flag.person_secondary_name}</span>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                {!isResolved && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    {isDuplicate && (
                      <button
                        onClick={() => handleResolve(flag.flag_id, 'merge', 'Merged duplicate')}
                        disabled={resolving === flag.flag_id}
                        className="flex items-center gap-1 text-xs px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-all disabled:opacity-50"
                        title="Merge records (keep lower ID)"
                      >
                        <GitMerge className="w-3.5 h-3.5" />
                        Merge
                      </button>
                    )}
                    <button
                      onClick={() => handleResolve(flag.flag_id, 'dismiss', 'Dismissed — no action needed')}
                      disabled={resolving === flag.flag_id}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 bg-slate-700/50 border border-slate-600/40 text-slate-300 rounded-lg hover:bg-slate-600/50 transition-all disabled:opacity-50"
                      title="Dismiss this flag"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Dismiss
                    </button>
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : flag.flag_id)}
                      className="text-xs p-1.5 text-slate-500 hover:text-slate-300 transition-all"
                    >
                      <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>
                  </div>
                )}
              </div>

              {/* Expanded Evidence */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-700/50">
                  <p className="text-xs text-slate-500 mb-1 uppercase font-bold tracking-wider">Evidence</p>
                  <pre className="text-xs text-slate-400 whitespace-pre-wrap bg-slate-900/50 rounded-lg p-3 font-mono overflow-x-auto">
                    {flag.evidence || 'No additional evidence recorded'}
                  </pre>
                  {flag.resolution && (
                    <div className="mt-2">
                      <p className="text-xs text-emerald-500 mb-1 uppercase font-bold tracking-wider">Resolution</p>
                      <p className="text-xs text-slate-400">{flag.resolution}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
