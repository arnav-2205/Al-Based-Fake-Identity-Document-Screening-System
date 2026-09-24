import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, VerificationView } from '../api/client';
import RiskBadge from '../components/RiskBadge';
import { Search, Filter, History, ArrowRight, Fingerprint, ShieldCheck } from 'lucide-react';

export default function VerificationsList() {
  const nav = useNavigate();
  const [list, setList] = useState<VerificationView[]>([]);
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<VerificationView[]>('/verification')
      .then((r) => setList(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = list.filter((v) => {
    const q = query.toLowerCase();
    const matchQuery =
      !q ||
      String(v.verificationId).includes(q) ||
      (v.extracted?.name && v.extracted.name.toLowerCase().includes(q)) ||
      (v.extracted?.passportNumber && v.extracted.passportNumber.toLowerCase().includes(q));

    const matchRisk = riskFilter === 'ALL' || v.riskLevel === riskFilter;

    return matchQuery && matchRisk;
  });

  return (
    <div className="space-y-4">
      {/* Title Banner */}
      <div className="card-defense p-5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-sky-600" />
            <h1 className="text-base font-bold text-slate-900 font-display uppercase tracking-wide">
              Biometric Registry &amp; Verification Manifest
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono">
            Cryptographically anchored inspection logs, optical OCR extractions, and biometric scoring.
          </p>
        </div>
        <div className="text-xs text-slate-700 font-mono bg-slate-50 px-3 py-1.5 rounded border border-slate-200 font-bold">
          Total Records: {list.length}
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            className="w-full bg-white border border-slate-200 focus:border-sky-500 rounded-md pl-9 pr-3 py-2 text-xs font-mono text-slate-800 placeholder-slate-400 outline-none transition-all shadow-2xs"
            placeholder="Search by Passport #, Passenger Legal Name, or Session ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 bg-white border border-slate-200 px-3 py-2 rounded-md shadow-2xs font-mono text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-500 font-semibold">FILTER RISK:</span>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-transparent text-slate-800 font-bold outline-none cursor-pointer"
          >
            <option value="ALL">ALL RISKS</option>
            <option value="LOW">LOW RISK</option>
            <option value="MEDIUM">MEDIUM RISK</option>
            <option value="HIGH">HIGH RISK</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="card-defense rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">Loading history records…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">
            No verification records matching query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200 text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">SESSION ID</th>
                  <th className="py-2.5 px-4">PASSENGER NAME</th>
                  <th className="py-2.5 px-4">DOCUMENT #</th>
                  <th className="py-2.5 px-4">TYPE</th>
                  <th className="py-2.5 px-4">RISK LEVEL</th>
                  <th className="py-2.5 px-4">TAMPER SCORE</th>
                  <th className="py-2.5 px-4">VERDICT</th>
                  <th className="py-2.5 px-4 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[11px]">
                {filtered.map((item) => (
                  <tr key={item.verificationId} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-4 font-bold text-slate-900">
                      #{String(item.verificationId).slice(0, 10)}
                    </td>
                    <td className="py-2 px-4 font-medium text-slate-800">
                      {item.extracted?.name || (item.extracted?.visualZone?.holderName as string) || '—'}
                    </td>
                    <td className="py-2 px-4 text-sky-700 font-bold">
                      {item.extracted?.passportNumber ||
                        (item.extracted?.visualZone?.documentNumber as string) ||
                        `DOC-${item.documentId}`}
                    </td>
                    <td className="py-2 px-4 text-slate-500">{item.documentType || 'PASSPORT'}</td>
                    <td className="py-2 px-4">
                      <RiskBadge level={item.riskLevel || 'LOW'} />
                    </td>
                    <td className="py-2 px-4 font-bold text-slate-700">
                      {(item.tamperingScore ?? 0).toFixed(2)}
                    </td>
                    <td className="py-2 px-4">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          item.finalResult === 'CLEAR'
                            ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                            : item.finalResult === 'MANUAL_REVIEW'
                            ? 'text-amber-700 bg-amber-50 border border-amber-200'
                            : 'text-rose-700 bg-rose-50 border border-rose-200'
                        }`}
                      >
                        {item.finalResult || 'CLEAR'}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-right">
                      <button
                        onClick={() => nav(`/verification/${item.verificationId}`)}
                        className="px-2.5 py-1 rounded bg-slate-900 text-white hover:bg-slate-800 text-[10px] font-bold transition-colors inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
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
