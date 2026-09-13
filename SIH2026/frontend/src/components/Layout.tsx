import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  Shield,
  LayoutDashboard,
  ScanLine,
  History,
  ShieldBan,
  FileCheck2,
  LogOut,
  User,
  Activity,
} from 'lucide-react';

export default function Layout() {
  const { name, role, officerId, logout } = useAuth();
  const nav = useNavigate();

  const getRoleBadge = (r: string | null) => {
    switch (r) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'INVESTIGATOR':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'AUDITOR':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      default:
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  const link = (to: string, label: string, Icon: React.ElementType, end = false) => (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
          isActive
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30'
            : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'
        }`
      }
    >
      <Icon className="w-4 h-4" />
      <span>{label}</span>
    </NavLink>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-500 selection:text-white">
      {/* Top Header */}
      <header className="bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-20">
          {/* Logo & Branding */}
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-2.5 rounded-2xl shadow-xl shadow-blue-900/30 border border-blue-400/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="font-extrabold tracking-tight text-xl text-white">SIH26188</span>
                <span className="bg-blue-500/10 text-blue-400 text-[10px] uppercase font-bold tracking-widest px-2.5 py-0.5 rounded-full border border-blue-500/20">
                  SSB Screening Engine
                </span>
              </div>
              <p className="text-xs text-slate-400 font-normal mt-0.5 hidden sm:block">
                AI Fake Identity &amp; Passport Forensic Screening Station
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-950/80 p-1.5 rounded-2xl border border-slate-800">
            {link('/', 'Dashboard', LayoutDashboard, true)}
            {link('/verify', 'New Screening', ScanLine)}
            {link('/verifications', 'History', History)}
            {link('/blacklist', 'Watchlist', ShieldBan)}
            {link('/audit', 'Audit Logs', FileCheck2)}
          </nav>

          {/* User Profile & Actions */}
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/40 px-3 py-1.5 rounded-full border border-emerald-800/30">
              <Activity className="w-3.5 h-3.5 animate-pulse" />
              <span className="font-medium">API Connected</span>
            </div>

            <div className="flex items-center gap-3 bg-slate-900/90 px-3.5 py-2 rounded-2xl border border-slate-800">
              <div className="w-8 h-8 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300 font-bold text-xs">
                <User className="w-4 h-4" />
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-xs font-bold text-slate-200">{name}</div>
                <div className="text-[10px] text-slate-400 font-mono">ID: {officerId}</div>
              </div>
              <span className={`text-[10px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full border ${getRoleBadge(role)}`}>
                {role}
              </span>
            </div>

            <button
              onClick={() => {
                logout();
                nav('/login');
              }}
              title="Sign out"
              className="p-2.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-2xl transition-all border border-transparent hover:border-red-500/20"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="lg:hidden flex items-center justify-around border-t border-slate-800/80 bg-slate-900/95 py-2.5 px-3">
          {link('/', 'Dashboard', LayoutDashboard, true)}
          {link('/verify', 'Screening', ScanLine)}
          {link('/verifications', 'History', History)}
          {link('/blacklist', 'Watchlist', ShieldBan)}
          {link('/audit', 'Audit', FileCheck2)}
        </div>
      </header>

      {/* Main Container with Spacious Margins */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900/80 bg-slate-950 py-6 text-center text-xs text-slate-500">
        Ministry of Home Affairs — SSB Police II Division · AI Identity Screening Engine v0.1.0
      </footer>
    </div>
  );
}
