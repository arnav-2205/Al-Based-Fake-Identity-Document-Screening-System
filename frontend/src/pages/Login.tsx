import React, { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import SentinelInsignia from '../components/SentinelInsignia';
import { Lock, User, Eye, EyeOff, AlertCircle, ShieldCheck } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [officerId, setOfficerId] = useState('officer1');
  const [password, setPassword] = useState('officer123');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const demoAccounts = [
    { role: 'OFFICER', id: 'officer1', pass: 'officer123', name: 'Insp. R. Sharma', label: 'Gate Officer' },
    { role: 'ADMIN', id: 'admin', pass: 'admin123', name: 'System Admin', label: 'Command Admin' },
    { role: 'INVESTIGATOR', id: 'investigator1', pass: 'invest123', name: 'Analyst Nair', label: 'Forensics' },
    { role: 'AUDITOR', id: 'auditor1', pass: 'audit123', name: 'Auditor Rao', label: 'Audit Trail' },
  ];

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(officerId, password);
      nav('/');
    } catch (err: any) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          'Invalid officer ID or access credentials. Please verify authorization.'
      );
    } finally {
      setBusy(false);
    }
  }

  function fillDemo(id: string, pass: string) {
    setOfficerId(id);
    setPassword(pass);
    setError('');
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 relative overflow-hidden font-sans">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-900/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Command Card */}
      <div className="w-full max-w-md bg-[#0A192F] border border-[#1E2E4A] p-7 sm:p-8 rounded-2xl shadow-2xl relative z-10 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2.5">
          <div className="inline-flex p-2 rounded-xl bg-slate-900/90 border border-slate-700/80 shadow-inner">
            <SentinelInsignia size={42} />
          </div>
          <div>
            <h1 className="text-2xl font-bold font-display uppercase tracking-wider text-white">
              SENTINEL-ID
            </h1>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              Border Automated Screening Station // ICP-ATTARI
            </p>
          </div>
          <div className="inline-block px-2.5 py-0.5 rounded font-mono text-[10px] font-bold bg-sky-950 text-sky-300 border border-sky-800/80 uppercase tracking-wider">
            MHA-SECURED · ACCESS CONTROL PORTAL
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={submit} className="space-y-4 font-mono text-xs">
          <div>
            <label className="block font-semibold text-slate-300 uppercase tracking-wider mb-1.5 text-[11px]">
              Officer / Terminal Identifier
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                className="w-full bg-slate-900 border border-slate-700/80 focus:border-sky-500 rounded-md pl-9 pr-3 py-2 text-slate-100 placeholder-slate-500 outline-none transition-all"
                placeholder="Officer ID (e.g. officer1)"
                value={officerId}
                onChange={(e) => setOfficerId(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 uppercase tracking-wider mb-1.5 text-[11px]">
              Security Access Credential
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPw ? 'text' : 'password'}
                className="w-full bg-slate-900 border border-slate-700/80 focus:border-sky-500 rounded-md pl-9 pr-9 py-2 text-slate-100 placeholder-slate-500 outline-none transition-all"
                placeholder="Access Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-2.5 rounded bg-rose-950/80 border border-rose-500/40 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white font-bold transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
          >
            {busy ? (
              <span>Authenticating Officer…</span>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Sign In to Terminal</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Access Bar */}
        <div className="border-t border-slate-800/80 pt-4 space-y-2 font-mono">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block text-center">
            Quick Station Roster Presets
          </span>
          <div className="grid grid-cols-2 gap-2">
            {demoAccounts.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => fillDemo(d.id, d.pass)}
                className={`p-2 rounded text-left border transition-all text-[11px] ${
                  officerId === d.id
                    ? 'bg-sky-950/80 border-sky-600 text-white'
                    : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-white leading-tight">{d.name}</div>
                <div className="text-[9px] text-sky-400">{d.label}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="text-center font-mono text-[10px] text-slate-500 pt-1">
          Checkpoint ICP-ATTARI · Secure TLS 1.3 · ICAO Doc 9303 Node
        </div>
      </div>
    </div>
  );
}
