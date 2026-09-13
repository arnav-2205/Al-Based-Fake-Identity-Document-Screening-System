import React, { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Shield, Lock, User, Eye, EyeOff, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [officerId, setOfficerId] = useState('officer1');
  const [password, setPassword] = useState('officer123');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const demoAccounts = [
    { role: 'OFFICER', id: 'officer1', pass: 'officer123', name: 'Officer R. Sharma', label: 'Border Control' },
    { role: 'ADMIN', id: 'admin', pass: 'admin123', name: 'System Admin', label: 'System Admin' },
    { role: 'INVESTIGATOR', id: 'investigator1', pass: 'invest123', name: 'Investigator Nair', label: 'Forensic Analyst' },
    { role: 'AUDITOR', id: 'auditor1', pass: 'audit123', name: 'Auditor S. Rao', label: 'Compliance Auditor' },
  ];

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(officerId, password);
      nav('/');
    } catch {
      setError('Invalid officer ID or password. Please check credentials.');
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6 relative overflow-hidden font-sans">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Glassmorphic Card */}
      <div className="w-full max-w-lg bg-slate-900/70 backdrop-blur-2xl border border-slate-800/80 p-8 sm:p-10 rounded-3xl shadow-2xl shadow-blue-950/50 relative z-10 space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex p-3.5 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 shadow-xl shadow-blue-900/40 border border-blue-400/20">
            <Shield className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">SIH26188</h1>
          <p className="text-xs sm:text-sm text-slate-400 font-medium max-w-xs mx-auto">
            AI-Based Fake Identity &amp; Document Screening System
          </p>
          <div className="inline-block px-3.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            SSB / Police II Division · Security Authentication Portal
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Officer ID
            </label>
            <div className="relative">
              <User className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-2xl pl-11 pr-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all"
                placeholder="Enter Officer ID (e.g. officer1)"
                value={officerId}
                onChange={(e) => setOfficerId(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4.5 h-4.5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type={showPw ? 'text' : 'password'}
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-blue-500 rounded-2xl pl-11 pr-11 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none transition-all"
                placeholder="Enter Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                {showPw ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2.5 p-3.5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            disabled={busy}
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 rounded-2xl shadow-xl shadow-blue-900/40 disabled:opacity-60 transition-all text-sm flex items-center justify-center gap-2"
          >
            {busy ? (
              <span>Authenticating…</span>
            ) : (
              <>
                <span>Sign In to Screening Station</span>
                <CheckCircle2 className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* 1-Click Quick Fill Cards */}
        <div className="space-y-3 pt-4 border-t border-slate-800/80">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-bold uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span>1-Click Demo Accounts</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {demoAccounts.map((acc) => (
              <button
                key={acc.id}
                type="button"
                onClick={() => fillDemo(acc.id, acc.pass)}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  officerId === acc.id
                    ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div className="text-xs font-extrabold tracking-wider text-slate-200">{acc.role}</div>
                <div className="text-[11px] text-slate-400 truncate mt-0.5">{acc.name}</div>
                <div className="text-[10px] font-mono text-blue-400 mt-1">{acc.id} / {acc.pass}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 text-slate-500 text-xs text-center">
        Restricted Government System · All operations logged &amp; blockchain recorded
      </div>
    </div>
  );
}
