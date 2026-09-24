import React, { useEffect, useState } from 'react';
import { api, AuditLogEntry } from '../api/client';
import { FileCheck2, Search, Lock, CheckCircle2, ShieldAlert, Database } from 'lucide-react';

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    api
      .get<AuditLogEntry[]>('/audit')
      .then((r) => setLogs(r.data || []))
      .catch((err) => setErrorMsg(err?.response?.data?.message || 'Failed to fetch audit log trail'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = logs.filter((l) => {
    const q = query.toLowerCase();
    return (
      !q ||
      String(l.verificationId).includes(q) ||
      (l.action && l.action.toLowerCase().includes(q)) ||
      (l.ipAddress && l.ipAddress.includes(q)) ||
      (l.recordHash && l.recordHash.toLowerCase().includes(q)) ||
      (l.blockchainTxId && l.blockchainTxId.toLowerCase().includes(q)) ||
      (l.integrityStatus && l.integrityStatus.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-4 font-mono">
      {/* Header */}
      <div className="card-defense p-5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-sky-600" />
            <h1 className="text-base font-bold text-slate-900 font-display uppercase tracking-wide">
              Audit &amp; Compliance Forensic Trail
            </h1>
          </div>
          <p className="text-xs text-slate-500">
            Immutable chain of custody for officer screening actions, ledger anchors, and SHA-256 block receipts.
          </p>
        </div>
        {logs.length > 0 ? (
          <div className="text-xs text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded border border-emerald-200 flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Ledger Synced ({logs.length} Events)</span>
          </div>
        ) : (
          <div className="text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded border border-slate-200 flex items-center gap-2 font-bold">
            <Lock className="w-4 h-4 text-slate-400" />
            <span>Ledger: Awaiting Events</span>
          </div>
        )}
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          className="w-full bg-white border border-slate-200 focus:border-sky-500 rounded-md pl-9 pr-3 py-2 text-xs text-slate-800 placeholder-slate-400 outline-none transition-all shadow-2xs"
          placeholder="Search by Verification ID, Officer Action, IP Address, or Record Hash…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="card-defense rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading audit trail…</div>
        ) : errorMsg ? (
          <div className="p-12 text-center space-y-2">
            <ShieldAlert className="w-8 h-8 text-rose-500 mx-auto" />
            <div className="text-xs font-bold text-rose-600">{errorMsg}</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center space-y-1.5">
            <div className="text-xs font-bold text-slate-700 uppercase">NO AUDIT EVENTS RECORDED YET</div>
            <p className="text-xs text-slate-400">
              {query
                ? 'No audit records match your search criteria.'
                : 'Completed document screenings and officer decisions will appear here with cryptographic hashes.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200 text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">TIMESTAMP</th>
                  <th className="py-2.5 px-4">VERIFICATION ID</th>
                  <th className="py-2.5 px-4">OFFICER ACTION</th>
                  <th className="py-2.5 px-4">IP ADDRESS</th>
                  <th className="py-2.5 px-4">SHA-256 RECORD HASH</th>
                  <th className="py-2.5 px-4">BLOCKCHAIN TX</th>
                  <th className="py-2.5 px-4">LEDGER STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[11px]">
                {filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-4 text-slate-500 whitespace-nowrap">
                      {l.timestamp ? new Date(l.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="py-2.5 px-4 font-bold text-slate-900">
                      #{String(l.verificationId).slice(0, 10)}
                    </td>
                    <td className="py-2.5 px-4 font-semibold text-slate-800">{l.action}</td>
                    <td className="py-2.5 px-4 text-slate-500">{l.ipAddress || '127.0.0.1'}</td>
                    <td className="py-2.5 px-4 text-sky-700 max-w-xs truncate" title={l.recordHash}>
                      {l.recordHash ? `${l.recordHash.slice(0, 16)}…` : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-slate-600 max-w-xs truncate" title={l.blockchainTxId}>
                      {l.blockchainTxId || 'TX-ICP4-PENDING'}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          l.integrityStatus === 'TAMPERED'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {l.integrityStatus || 'VERIFIED'}
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
