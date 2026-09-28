import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Search, Filter, BookOpen, ExternalLink, Calendar, ShieldCheck, ArrowRight } from 'lucide-react';
import { fetchCachedJson } from '../utils/apiCache';

export default function RecordsPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 24;

  const navigate = useNavigate();

  useEffect(() => {
    fetchCachedJson('/api/records_catalog.json')
      .then(data => {
        const list = Array.isArray(data) ? data : [];
        setRecords(list);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load records catalog:", err);
        setLoading(false);
      });
  }, []);

  const categories = useMemo(() => {
    const cats = new Set(records.map(r => r.category).filter(Boolean));
    return ['ALL', ...Array.from(cats).sort()];
  }, [records]);

  const filteredRecords = useMemo(() => {
    return records.filter(r => {
      if (selectedCategory !== 'ALL' && r.category !== selectedCategory) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        return (r.title && r.title.toLowerCase().includes(q)) ||
               (r.snippet && r.snippet.toLowerCase().includes(q)) ||
               (r.filename && r.filename.toLowerCase().includes(q));
      }
      return true;
    });
  }, [records, selectedCategory, searchQuery]);

  const totalPages = Math.ceil(filteredRecords.length / pageSize) || 1;
  const paginatedRecords = filteredRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleOpenRecord = (id) => {
    navigate(`/records/${encodeURIComponent(id)}`);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-[#1C1A17] border border-[#2D2722] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-xs font-mono text-amber-300 mb-2">
            <FileText className="w-3.5 h-3.5" />
            <span>357 Preserved Primary Documents</span>
          </div>
          <h2 className="font-serif-header text-2xl sm:text-3xl font-bold text-[#F3EBE3]">
            Primary Document & Deed Vault
          </h2>
          <p className="text-xs sm:text-sm text-[#A8A096] mt-1 max-w-2xl leading-relaxed">
            Delmarva court records, family Bible registers, probate wills, apprenticeship indentures, and census schedules.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#161412] border border-[#2B2621] p-4 rounded-xl flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:max-w-md">
          <Search className="w-4 h-4 text-[#C68B59] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search records by title, surname, will, or Bible..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#1C1A17] border border-[#332D27] text-xs font-mono text-[#E5E1DB] placeholder-[#8C8275] focus:outline-none focus:border-[#C68B59]"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => {
                setSelectedCategory(cat);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all shrink-0 ${
                selectedCategory === cat
                  ? 'bg-[#C68B59] text-[#121110] font-bold shadow'
                  : 'bg-[#1C1A17] text-[#A8A096] border border-[#332D27] hover:border-[#C68B59]/40 hover:text-[#F3EBE3]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="p-16 text-center text-xs font-mono text-[#8C8275]">
          <div className="inline-block w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mb-3" />
          <p>Loading historical primary records vault...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && paginatedRecords.length === 0 && (
        <div className="p-16 text-center bg-[#161412] border border-[#26221E] rounded-xl text-xs font-mono text-[#8C8275]">
          No documents found matching "{searchQuery}".
        </div>
      )}

      {/* Records Grid */}
      {!loading && paginatedRecords.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginatedRecords.map(doc => (
            <div
              key={doc.id}
              onClick={() => handleOpenRecord(doc.id)}
              className="bg-[#1C1A17] hover:bg-[#221F1B] border border-[#332D27] hover:border-[#C68B59]/60 rounded-xl p-4 shadow-lg transition-all cursor-pointer flex flex-col justify-between group active:scale-[0.99]"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-black/60 text-[#D4A373] border border-[#C68B59]/30">
                    {doc.category}
                  </span>
                  <span className="text-[10px] font-mono text-[#8C8275]">
                    {doc.line_count} lines
                  </span>
                </div>

                <h3 className="font-serif-header text-sm sm:text-base font-bold text-[#F3EBE3] group-hover:text-[#D4A373] transition-colors leading-snug line-clamp-2">
                  {doc.title}
                </h3>

                {doc.snippet && (
                  <p className="text-xs text-[#A8A096] mt-2 line-clamp-3 leading-relaxed">
                    {doc.snippet}
                  </p>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-[#26221E] flex items-center justify-between text-xs font-mono text-[#D4A373]">
                <span className="text-[11px] text-[#8C8275] truncate max-w-[180px]">{doc.filename}</span>
                <span className="inline-flex items-center gap-1 group-hover:underline">
                  Read Record <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-[#2B2621] pt-4 text-xs font-mono text-[#8C8275]">
          <div>
            Showing {((currentPage - 1) * pageSize) + 1}–{Math.min(currentPage * pageSize, filteredRecords.length)} of {filteredRecords.length} documents
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              className="px-3 py-1.5 rounded-lg border border-[#332D27] bg-[#1C1A17] disabled:opacity-40 hover:border-[#C68B59]/60 hover:text-[#F3EBE3]"
            >
              Previous
            </button>
            <span className="text-[#D4A373] font-bold px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              className="px-3 py-1.5 rounded-lg border border-[#332D27] bg-[#1C1A17] disabled:opacity-40 hover:border-[#C68B59]/60 hover:text-[#F3EBE3]"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
