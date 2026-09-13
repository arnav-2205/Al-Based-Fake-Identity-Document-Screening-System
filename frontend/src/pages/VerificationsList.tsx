import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, VerificationView } from '../api/client';
import RiskBadge from '../components/RiskBadge';
import { Search, Filter, History, ArrowRight } from 'lucide-react';

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
    <div className="space-y-8">
      {/* Title */}
      <div className="bg-slate-900/60 border border-slate-800/80 p-8 rounded-3xl shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-3 tracking-tight">
            <History className="w-7 h-7 text-blue-400" />
            <span>Screening Verifications History</span>
          </h1>
          <p className="text-xs text-slate-400 font-normal">
            Complete searchable repository of all border screening records and forensic evaluations.
          </p>
        </div>
        <div className="text-xs text-slate-300 font-mono bg-slate-950 px-4 py-2 rounded-2xl border border-slate-800 font-bold">
          Total Records: {list.length}
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            className="w-full bg-slate-900/60 border border-slate-800/80 focus:border-blue-500 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 outline-none transition-all"
            placeholder="Search by Passport #, Subject Name, or Verification ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-3 bg-slate-900/60 border border-slate-800/80 px-4 py-2 rounded-2xl">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs text-slate-400 font-bold">Filter Risk:</span>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-bold outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-slate-900">ALL RISKS</option>
            <option value="LOW" className="bg-slate-900">LOW</option>
            <option value="MEDIUM" className="bg-slate-900">MEDIUM</option>
            <option value="HIGH" className="bg-slate-900">HIGH</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-3xl shadow-xl overflow-hidden backdrop-blur-md">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading history records…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">No verification records matching query.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800/80">
                <tr>
                  <th className="py-4 px-6">ID</th>
                  <th className="py-4 px-6">Subject Name</th>
                  <th className="py-4 px-6">Document #</th>
                  <th className="py-4 px-6">Type</th>
                  <th className="py-4 px-6">Risk Level</th>
                  <th className="py-4 px-6">Tamper Score</th>
                  <th className="py-4 px-6">Verdict</th>
                  <th className="py-4 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((v) => (
                  <tr key={v.verificationId} className="hover:bg-slate-800/40 transition-all">
                    <td className="py-4 px-6 font-mono text-slate-400 font-medium">#{v.verificationId}</td>
                    <td className="py-4 px-6 font-bold text-slate-100">{v.extracted?.name || 'Unknown'}</td>
                    <td className="py-4 px-6 font-mono text-blue-400 font-semibold">{v.extracted?.passportNumber || '—'}</td>
                    <td className="py-4 px-6 text-slate-400">{v.documentType}</td>
                    <td className="py-4 px-6">
                      <RiskBadge level={v.riskLevel} score={v.riskScore} />
                    </td>
                    <td className="py-4 px-6 font-mono text-slate-300 font-medium">
                      {(v.tamperingScore * 100).toFixed(0)}%
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-block px-3 py-1 rounded-full font-bold text-[10px] tracking-wider ${
                          v.finalResult === 'CLEAR'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : v.finalResult === 'MANUAL_REVIEW'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}
                      >
                        {v.finalResult}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => nav(`/verification/${v.verificationId}`)}
                        className="text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3.5 py-1.5 rounded-xl border border-blue-500/20 transition-all inline-flex items-center gap-1.5 font-bold"
                      >
                        <span>Details</span>
                        <ArrowRight className="w-3.5 h-3.5" />
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
