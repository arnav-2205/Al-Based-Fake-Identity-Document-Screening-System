import React, { useEffect, useState, FormEvent } from 'react';
import { api, BlacklistEntry } from '../api/client';
import { ShieldBan, Search, Plus, Trash2, X, AlertCircle, ShieldAlert } from 'lucide-react';

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
    <div className="space-y-4">
      {/* Title Header */}
      <div className="card-defense p-5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-600" />
            <h1 className="text-base font-bold text-slate-900 font-display uppercase tracking-wide">
              Surveillance Watchlist &amp; INTERPOL Red Notices
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono">
            Active border interception notices for fraudulent identities, stolen credentials, and restricted travelers.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold px-4 py-2 rounded-md shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add Watchlist Record</span>
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            className="w-full bg-white border border-slate-200 focus:border-sky-500 rounded-md pl-9 pr-3 py-2 text-xs font-mono text-slate-800 placeholder-slate-400 outline-none transition-all shadow-2xs"
            placeholder="Search by Document #, Full Name, or Intercept Reason…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-white border border-slate-200 text-xs font-mono text-slate-800 font-bold px-3 py-2 rounded-md shadow-2xs outline-none"
        >
          <option value="ALL">ALL TYPES</option>
          <option value="PASSPORT">PASSPORT</option>
          <option value="VISA">VISA</option>
          <option value="NATIONAL_ID">NATIONAL ID</option>
        </select>
      </div>

      {err && (
        <div className="flex items-center gap-2 p-3 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {/* Table */}
      <div className="card-defense rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">Loading watchlist entries…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-slate-400">No watchlist entries found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200 text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">DOCUMENT #</th>
                  <th className="py-2.5 px-4">TYPE</th>
                  <th className="py-2.5 px-4">SUBJECT NAME</th>
                  <th className="py-2.5 px-4">DOB</th>
                  <th className="py-2.5 px-4">REASON / ALERT NOTE</th>
                  <th className="py-2.5 px-4">STATUS</th>
                  <th className="py-2.5 px-4 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[11px]">
                {filtered.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-4 font-bold text-amber-700">{r.documentNumber}</td>
                    <td className="py-2.5 px-4 text-slate-500 font-medium">{r.documentType}</td>
                    <td className="py-2.5 px-4 font-bold text-slate-800">{r.name}</td>
                    <td className="py-2.5 px-4 text-slate-500">{r.dateOfBirth}</td>
                    <td className="py-2.5 px-4 text-slate-700 max-w-xs truncate">{r.reason}</td>
                    <td className="py-2.5 px-4">
                      <span className="bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button
                        onClick={() => handleDelete(r.id)}
                        className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                        title="Remove entry"
                      >
                        <Trash2 className="w-4 h-4" />
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
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="card-defense p-6 rounded-xl max-w-lg w-full shadow-2xl space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldBan className="w-5 h-5 text-amber-600" />
                <span>Add Surveillance Watchlist Record</span>
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAdd} className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1 uppercase tracking-wider">
                  Document Number
                </label>
                <input
                  required
                  value={docNum}
                  onChange={(e) => setDocNum(e.target.value)}
                  placeholder="e.g. Z9988776"
                  className="w-full bg-slate-50 border border-slate-200 rounded p-2 text-slate-900 outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1 uppercase tracking-wider">
                    Document Type
                  </label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded p-2 text-slate-900 outline-none"
                  >
                    <option value="PASSPORT">Passport</option>
                    <option value="VISA">Visa</option>
                    <option value="NATIONAL_ID">National ID</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-1 uppercase tracking-wider">
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    required
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded p-2 text-slate-900 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1 uppercase tracking-wider">
                  Subject Full Name
                </label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. JOHN FICTITIOUS"
                  className="w-full bg-slate-50 border border-slate-200 rounded p-2 text-slate-900 outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1 uppercase tracking-wider">
                  Alert Reason / Advisory Details
                </label>
                <textarea
                  required
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Reason for flagging: Red Notice, Impersonation risk, Revoked passport..."
                  className="w-full bg-slate-50 border border-slate-200 rounded p-2 text-slate-900 outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 rounded border border-slate-200 text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busyAdd}
                  className="px-4 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-white font-bold transition-colors disabled:opacity-50"
                >
                  {busyAdd ? 'Recording…' : 'Save Watchlist Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
