import React, { useEffect, useState, FormEvent } from 'react';
import { api, BlacklistEntry } from '../api/client';
import { ShieldBan, Search, Plus, Trash2, X, AlertCircle } from 'lucide-react';

export default function Blacklist() {
  const [rows, setRows] = useState<BlacklistEntry[]>([]);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [docNum, setDocNum] = useState('');
  const [docType, setDocType] = useState('PASSPORT');
  const [name, setName] = useState('');
  const [dob, setDob] = useState('1990-01-01');
  const [reason, setReason] = useState('');
  const [busyAdd, setBusyAdd] = useState(false);

  useEffect(() => {
    loadList();
  }, []);

  function loadList() {
    setLoading(true);
    api
      .get<BlacklistEntry[]>('/blacklist')
      .then((r) => setRows(r.data))
      .catch((e) => setErr(e?.response?.data?.message ?? 'Failed to load watchlist entries'))
      .finally(() => setLoading(false));
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setBusyAdd(true);
    try {
      await api.post('/blacklist', {
        documentNumber: docNum,
        documentType: docType,
        name,
        dateOfBirth: dob,
        reason,
        status: 'ACTIVE',
      });
      setShowModal(false);
      setDocNum('');
      setName('');
      setReason('');
      loadList();
    } catch {
      setErr('Failed to add blacklist entry.');
    } finally {
      setBusyAdd(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Are you sure you want to remove this entry from the watchlist?')) return;
    try {
      await api.delete(`/blacklist/${id}`);
      setRows((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setRows((prev) => prev.filter((r) => r.id !== id));
    }
  }

  const filtered = rows.filter((r) => {
    const q = query.toLowerCase();
    const matchQ =
      !q ||
      r.documentNumber.toLowerCase().includes(q) ||
      r.name.toLowerCase().includes(q) ||
      r.reason.toLowerCase().includes(q);
    const matchType = typeFilter === 'ALL' || r.documentType === typeFilter;
    return matchQ && matchType;
  });

  return (
    <div className="space-y-8">
      {/* Title Header */}
      <div className="bg-slate-900/60 border border-slate-800/80 p-8 rounded-3xl shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold text-white flex items-center gap-3 tracking-tight">
            <ShieldBan className="w-7 h-7 text-amber-400" />
            <span>INTERPOL &amp; Watchlist Repository</span>
          </h1>
          <p className="text-xs text-slate-400 font-normal">
            Active watchlist records for blacklisted passports, visas, and flagged identities.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold px-5 py-3 rounded-2xl shadow-xl shadow-blue-900/40 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add Watchlist Record</span>
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            className="w-full bg-slate-900/60 border border-slate-800/80 focus:border-blue-500 rounded-2xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 outline-none transition-all"
            placeholder="Search by Document #, Name, or Watchlist Reason…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-slate-900/60 border border-slate-800/80 text-xs text-slate-200 font-bold px-4 py-3 rounded-2xl outline-none"
        >
          <option value="ALL" className="bg-slate-900">ALL TYPES</option>
          <option value="PASSPORT" className="bg-slate-900">PASSPORT</option>
          <option value="VISA" className="bg-slate-900">VISA</option>
          <option value="NATIONAL_ID" className="bg-slate-900">NATIONAL ID</option>
        </select>
      </div>

      {err && (
        <div className="flex items-center gap-2.5 p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
          <AlertCircle className="w-4.5 h-4.5" />
          <span>{err}</span>
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-3xl shadow-xl overflow-hidden backdrop-blur-md">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading watchlist entries…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">No watchlist entries found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-950/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800/80">
                <tr>
                  <th className="py-4 px-6">Document #</th>
                  <th className="py-4 px-6">Type</th>
                  <th className="py-4 px-6">Subject Name</th>
                  <th className="py-4 px-6">DOB</th>
                  <th className="py-4 px-6">Reason / Alert Note</th>
                  <th className="py-4 px-6">Status</th>
                  <th className="py-4 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition-all">
                    <td className="py-4 px-6 font-mono font-bold text-amber-400">{r.documentNumber}</td>
                    <td className="py-4 px-6 text-slate-400 font-medium">{r.documentType}</td>
                    <td className="py-4 px-6 font-bold text-slate-100">{r.name}</td>
                    <td className="py-4 px-6 text-slate-400 font-mono">{r.dateOfBirth}</td>
                    <td className="py-4 px-6 text-slate-300 max-w-xs">{r.reason}</td>
                    <td className="py-4 px-6">
                      <span className="bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 rounded-full font-bold text-[10px] tracking-wider">
                        {r.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button
                        onClick={() => handleDelete(r.id)}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all"
                        title="Remove entry"
                      >
                        <Trash2 className="w-4.5 h-4.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-slate-800/80 p-8 rounded-3xl max-w-lg w-full shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2.5">
                <ShieldBan className="w-6 h-6 text-amber-400" />
                <span>Add Watchlist Record</span>
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5 uppercase tracking-wider">
                  Document Number
                </label>
                <input
                  required
                  className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl px-4 py-3 text-xs text-slate-100 outline-none focus:border-blue-500 transition-all"
                  placeholder="e.g. P1234567"
                  value={docNum}
                  onChange={(e) => setDocNum(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5 uppercase tracking-wider">
                    Type
                  </label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl px-4 py-3 text-xs text-slate-100 outline-none"
                  >
                    <option value="PASSPORT">PASSPORT</option>
                    <option value="VISA">VISA</option>
                    <option value="NATIONAL_ID">NATIONAL ID</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5 uppercase tracking-wider">
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl px-4 py-3 text-xs text-slate-100 outline-none"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5 uppercase tracking-wider">
                  Subject Full Name
                </label>
                <input
                  required
                  className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl px-4 py-3 text-xs text-slate-100 outline-none focus:border-blue-500 transition-all"
                  placeholder="e.g. John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5 uppercase tracking-wider">
                  Watchlist Reason / INTERPOL Notice
                </label>
                <textarea
                  required
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800/80 rounded-2xl px-4 py-3 text-xs text-slate-100 outline-none focus:border-blue-500 transition-all"
                  placeholder="e.g. INTERPOL Red Notice — Identity fraud suspect"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              <button
                disabled={busyAdd}
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-xl shadow-blue-900/40 transition-all"
              >
                {busyAdd ? 'Saving Entry…' : 'Add to Watchlist Repository'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
