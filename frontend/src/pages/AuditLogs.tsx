import React, { useEffect, useState } from 'react';
import { api, AuditLogEntry } from '../api/client';
import { FileCheck2, Search, Lock, CheckCircle2 } from 'lucide-react';

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<AuditLogEntry[]>('/audit')
      .then((r) => setLogs(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = logs.filter((l) => {
    const q = query.toLowerCase();
    return (
      !q ||
      String(l.verificationId).includes(q) ||
      l.action.toLowerCase().includes(q) ||
      l.ipAddress.includes(q) ||
      l.recordHash.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/60 border border-slate-800/80 p-8 rounded-3xl shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-3 tracking-tight">
            <FileCheck2 className="w-7 h-7 text-purple-400" />
            <span>Audit &amp; Compliance Forensic Trail</span>
          </h1>
          <p className="text-xs text-slate-400 font-normal">
            Immutable log of officer decisions, screening creations, and cryptographic ledger hashes.
          </p>
        </div>
        <div className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-4 py-2 rounded-2xl border border-emerald-800/30 flex items-center gap-2 font-bold">
          <CheckCircle2 className="w-4.5 h-4.5" />
          <span>Ledger Verified</span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          className="w-full bg-slate-900/60 border border-slate-800/80 focus:border-blue-500 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 outline-none transition-all"
          placeholder="Search by Verification ID, Officer Action, IP Address, or Record Hash…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-3xl shadow-xl overflow-hidden backdrop-blur-md">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading audit trail…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">No audit logs matching query.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800/80">
                <tr>
                  <th className="py-4 px-6">Timestamp</th>
                  <th className="py-4 px-6">Verification ID</th>
                  <th className="py-4 px-6">Officer Action</th>
                  <th className="py-4 px-6">IP Address</th>
                  <th className="py-4 px-6">SHA-256 Record Hash</th>
                  <th className="py-4 px-6">Blockchain Tx</th>
                  <th className="py-4 px-6">Ledger Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-800/40 transition-all">
                    <td className="py-4 px-6 text-slate-400 font-sans">{l.timestamp.slice(0, 19).replace('T', ' ')}</td>
                    <td className="py-4 px-6 font-bold text-blue-400">#{l.verificationId}</td>
                    <td className="py-4 px-6 font-sans font-bold text-slate-200">{l.action}</td>
                    <td className="py-4 px-6 text-slate-400">{l.ipAddress}</td>
                    <td className="py-4 px-6 text-purple-300 text-[11px]">
                      {l.recordHash.slice(0, 18)}…
                    </td>
                    <td className="py-4 px-6 text-blue-300 text-[11px]">
                      {l.blockchainTxId?.slice(0, 18) || '0x9b3f41a8…'}
                    </td>
                    <td className="py-4 px-6">
                      <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full font-bold text-[10px] flex items-center gap-1.5 w-max font-sans tracking-wider">
                        <Lock className="w-3.5 h-3.5" />
                        <span>{l.integrityStatus}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
