import React, { useState, useEffect } from 'react';
import { ShieldCheck, RefreshCw, CheckCircle2, AlertCircle, Database, Hash, FileCheck, X, HardDrive, Shield } from 'lucide-react';

export default function ArchivalIntegrityModal({ isOpen, onClose }) {
  const [fixityData, setFixityData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchFixityStatus();
    }
  }, [isOpen]);

  const fetchFixityStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      let res = await fetch('/api/fixity/status');
      if (!res.ok) {
        res = await fetch('/api/fixity_status.json');
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFixityData(data);
    } catch (err) {
      console.error('Failed to fetch fixity status:', err);
      setError('Unable to retrieve fixity audit status from backend.');
    } finally {
      setLoading(false);
    }
  };

  const runVerification = async () => {
    setVerifying(true);
    setVerifyResult(null);
    setError(null);
    try {
      const res = await fetch('/api/fixity/verify', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setVerifyResult({ success: true, message: data.message });
        await fetchFixityStatus();
      } else {
        setVerifyResult({ success: false, message: data.message || 'Fixity discrepancies detected.' });
      }
    } catch (err) {
      setVerifyResult({ success: false, message: 'Verification process failed: ' + err.message });
    } finally {
      setVerifying(false);
    }
  };

  if (!isOpen) return null;

  const latest = fixityData?.latest_audit;
  const bagInfo = fixityData?.bag_info || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-2xl bg-[#141210] border border-[#2D2722] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#26221E] flex items-center justify-between bg-[#191714]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-serif font-bold text-[#F3EBE3] tracking-tight">
                Digital Preservation & Fixity Integrity
              </h2>
              <p className="text-xs font-mono text-[#8C8275]">
                OAIS ISO 14721 & RFC 8493 BagIt 1.0 Specification
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8C8275] hover:text-[#F3EBE3] hover:bg-[#26221E] transition-colors"
            aria-label="Close Modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-5 text-xs font-mono">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-[#A8A096]">
              <RefreshCw className="w-6 h-6 animate-spin text-[#C68B59]" />
              <p>Reading BagIt manifests and fixity records...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-red-950/30 border border-red-900/50 text-red-300 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
              <div>
                <p className="font-bold">Audit Service Notice</p>
                <p className="text-[11px] mt-1 text-red-200">{error}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Fixity Status Card */}
              <div className="p-4 rounded-xl bg-[#1C1A17] border border-[#2D2722] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[#8C8275] uppercase text-[10px] tracking-wider">Overall Fixity Status</span>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                    latest?.status === 'PASSED' 
                      ? 'bg-emerald-950/60 border border-emerald-500/40 text-emerald-400'
                      : 'bg-amber-950/60 border border-amber-500/40 text-amber-300'
                  }`}>
                    {latest?.status === 'PASSED' ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>100% Cryptographic Fixity Verified</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>{latest?.status || 'Pending Initial Audit'}</span>
                      </>
                    )}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
                  <div className="p-2.5 rounded-lg bg-[#141210] border border-[#26221E]">
                    <div className="text-[10px] text-[#8C8275]">Checked Files</div>
                    <div className="text-sm font-bold text-[#F3EBE3] mt-0.5">
                      {latest?.total_files_checked?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#141210] border border-[#26221E]">
                    <div className="text-[10px] text-[#8C8275]">Payload Size</div>
                    <div className="text-sm font-bold text-[#F3EBE3] mt-0.5">
                      {bagInfo['Bag-Size'] || `${((latest?.total_bytes_checked || 0) / (1024 * 1024)).toFixed(1)} MB`}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#141210] border border-[#26221E]">
                    <div className="text-[10px] text-emerald-500/80">Valid Assets</div>
                    <div className="text-sm font-bold text-emerald-400 mt-0.5">
                      {latest?.passed_count?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#141210] border border-[#26221E]">
                    <div className="text-[10px] text-red-400/80">Corrupt / Missing</div>
                    <div className="text-sm font-bold text-[#F3EBE3] mt-0.5">
                      {(latest?.failed_count || 0) + (latest?.missing_count || 0)}
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-[#8C8275] pt-1">
                  Last verified: <span className="text-[#C68B59]">{latest?.audit_timestamp ? new Date(latest.audit_timestamp).toLocaleString() : 'N/A'}</span>
                </div>
              </div>

              {/* RFC 8493 BagIt Specifications */}
              <div className="p-4 rounded-xl bg-[#1C1A17] border border-[#2D2722] space-y-2">
                <div className="flex items-center gap-2 text-[#D4A373] font-semibold text-xs border-b border-[#26221E] pb-2">
                  <FileCheck className="w-4 h-4 text-[#C68B59]" />
                  <span>RFC 8493 Package Manifest Metadata</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-[11px] pt-1">
                  <div>
                    <span className="text-[#8C8275]">Payload Oxum: </span>
                    <span className="text-[#E5E1DB]">{bagInfo['Payload-Oxum'] || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-[#8C8275]">Hash Standard: </span>
                    <span className="text-[#E5E1DB]">SHA-256 (64-byte hex digest)</span>
                  </div>
                  <div>
                    <span className="text-[#8C8275]">Source Organization: </span>
                    <span className="text-[#E5E1DB]">{bagInfo['Source-Organization'] || 'Lynn Jackson Archive'}</span>
                  </div>
                  <div>
                    <span className="text-[#8C8275]">Bagging Agent: </span>
                    <span className="text-[#E5E1DB]">{bagInfo['Bag-Software-Agent'] || 'Antigravity OAIS Engine'}</span>
                  </div>
                </div>
              </div>

              {/* Action status message */}
              {verifyResult && (
                <div className={`p-3 rounded-xl border flex items-start gap-2.5 ${
                  verifyResult.success 
                    ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' 
                    : 'bg-red-950/40 border-red-500/40 text-red-300'
                }`}>
                  {verifyResult.success ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                  )}
                  <div className="text-[11px]">
                    <span className="font-semibold">{verifyResult.success ? 'Integrity Confirmed' : 'Verification Alert'}: </span>
                    <span>{verifyResult.message}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-5 border-t border-[#26221E] bg-[#191714] flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[11px] text-[#8C8275]">
            <HardDrive className="w-3.5 h-3.5 text-[#C68B59]" />
            <span>Immutable Canonical Snapshot Synced</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-xl border border-[#332D27] text-xs font-mono text-[#A8A096] hover:text-[#F3EBE3] hover:bg-[#26221E] transition-colors"
            >
              Close
            </button>
            <button
              onClick={runVerification}
              disabled={verifying}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-mono text-xs font-medium shadow-md hover:shadow-emerald-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${verifying ? 'animate-spin' : ''}`} />
              <span>{verifying ? 'Verifying Hashes...' : 'Re-verify Fixity'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
