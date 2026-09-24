import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import SentinelInsignia from './SentinelInsignia';
import {
  Radar,
  LayoutDashboard,
  Fingerprint,
  ShieldAlert,
  History,
  LogOut,
  Bell,
  Lock,
  Bolt,
  BadgeAlert,
  Menu,
  X,
  ShieldCheck,
} from 'lucide-react';

export default function Layout() {
  const { name, role, officerId, logout } = useAuth();
  const nav = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState<{ utc: string; local: string }>({
    utc: '',
    local: '',
  });

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime({
        utc: now.toUTCString().slice(17, 25) + ' UTC',
        local: now.toLocaleTimeString() + ' LOCAL',
      });
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-semibold transition-colors ${
      isActive
        ? 'bg-slate-900 text-white shadow-2xs'
        : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
    }`;

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased flex flex-col selection:bg-sky-100 selection:text-sky-900">
      {/* ========================================================================= */}
      {/* TOP GLOBAL MISSION HEADER (Sentinel Command Canopy)                       */}
      {/* ========================================================================= */}
      <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-[#0A192F] border-b border-[#1E2E4A] flex items-center justify-between px-4 sm:px-6 select-none shadow-sm">
        {/* Left branding & station telemetry */}
        <div className="flex items-center gap-4 sm:gap-6">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-slate-300 hover:text-white p-1"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded flex items-center justify-center p-0.5 bg-slate-900/80 border border-slate-700/60 shadow-inner">
              <SentinelInsignia size={26} />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-display text-sm font-bold tracking-wider text-white uppercase leading-none">
                  SENTINEL-ID
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800/80 leading-none">
                  MHA-SECURED
                </span>
              </div>
              <span className="text-xs text-slate-400 mt-0.5 font-medium hidden sm:inline-block">
                ICP-ATTARI // Station Terminal 04
              </span>
            </div>
          </div>

          <div className="h-4 w-px bg-slate-800 hidden md:block"></div>

          {/* Live Pipeline Indicators */}
          <div className="hidden xl:flex items-center gap-4 text-xs text-slate-300 font-medium">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 live-dot-pulse"></span>
              <span>AI Core v2.4 Active</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Blockchain Ledger Synced</span>
            </div>
            <div className="flex items-center gap-1 text-slate-400">
              <Bolt className="w-3.5 h-3.5 text-sky-400" />
              <span className="font-mono text-[11px]">14ms Latency</span>
            </div>
          </div>
        </div>

        {/* Right Operator & System Timers */}
        <div className="flex items-center gap-3 sm:gap-5">
          <div className="flex items-center gap-2 px-3 py-1 rounded bg-slate-900/90 border border-slate-800 text-slate-200">
            <div className="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-sky-400">
              <BadgeAlert className="w-3.5 h-3.5" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-xs font-semibold text-slate-200">{name || 'Insp. R. Sharma'}</span>
              <span className="text-[10px] font-mono text-slate-400 mt-0.5">
                {role || 'INSPECTOR'} #{officerId || '8841-B'}
              </span>
            </div>
          </div>

          {/* Real-time UTC / Local Clock */}
          <div className="text-right hidden sm:block border-l border-slate-800 pl-4 font-mono">
            <div className="text-xs font-bold text-slate-100 t-nums tracking-wide">
              {currentTime.utc || '14:32:09 UTC'}
            </div>
            <div className="text-[11px] text-slate-400 t-nums">
              {currentTime.local || '20:02:09 IST'}
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              className="w-8 h-8 rounded flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors relative"
              title="System Alerts"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            </button>
            <button
              onClick={() => {
                logout();
                nav('/login');
              }}
              className="w-8 h-8 rounded flex items-center justify-center text-slate-300 hover:text-red-400 hover:bg-slate-800/80 transition-colors"
              title="Sign Out / Lock Station"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* SIDEBAR NAVIGATION                                                        */}
      {/* ========================================================================= */}
      <aside
        className={`fixed left-0 top-14 bottom-0 w-60 bg-white border-r border-slate-200 flex flex-col justify-between p-3 z-40 select-none transition-transform duration-200 md:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="space-y-4">
          <div className="px-2 pt-1 pb-0.5">
            <span className="text-xs font-bold tracking-wider text-slate-400 uppercase">
              Screening Console
            </span>
          </div>
          <nav className="space-y-1">
            <NavLink
              to="/verify"
              onClick={() => setMobileMenuOpen(false)}
              className={navLinkClass}
            >
              <Radar className="w-4 h-4 text-sky-600" />
              <span>Live Screening</span>
            </NavLink>
            <NavLink
              to="/"
              end
              onClick={() => setMobileMenuOpen(false)}
              className={navLinkClass}
            >
              <LayoutDashboard className="w-4 h-4 text-slate-500" />
              <span>Border Telemetry</span>
            </NavLink>
            <NavLink
              to="/verifications"
              onClick={() => setMobileMenuOpen(false)}
              className={navLinkClass}
            >
              <Fingerprint className="w-4 h-4 text-slate-500" />
              <span>Biometric Registry</span>
            </NavLink>
            <NavLink
              to="/blacklist"
              onClick={() => setMobileMenuOpen(false)}
              className={navLinkClass}
            >
              <ShieldAlert className="w-4 h-4 text-slate-500" />
              <span>Surveillance Watchlist</span>
            </NavLink>
            <NavLink
              to="/audit"
              onClick={() => setMobileMenuOpen(false)}
              className={navLinkClass}
            >
              <History className="w-4 h-4 text-slate-500" />
              <span>Audit Telemetry</span>
            </NavLink>
          </nav>
        </div>

        {/* Lower Station Status Widget */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-600 font-bold uppercase text-[11px]">GATE 04 CAPACITY</span>
            <span className="font-mono font-bold text-slate-900 t-nums">82%</span>
          </div>
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div className="bg-sky-600 h-full w-[82%] rounded-full"></div>
          </div>
          <div className="flex justify-between items-center text-xs text-slate-600 font-medium">
            <span>Flow Rate</span>
            <span className="text-slate-900 font-bold font-mono">418 pax / hr</span>
          </div>
          <div className="pt-1.5 border-t border-slate-200/80 flex items-center justify-between text-xs text-slate-500">
            <span>Status</span>
            <span className="text-emerald-700 font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> NORMAL
            </span>
          </div>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* MAIN WORKSPACE                                                            */}
      {/* ========================================================================= */}
      <div className="md:pl-60 pt-14 min-h-screen flex flex-col justify-between">
        <main className="w-full max-w-[1720px] mx-auto p-4 sm:p-6 flex-1">
          <Outlet />
        </main>

        <footer className="border-t border-slate-200 bg-white py-3 px-6 text-center text-xs text-slate-600 flex flex-col sm:flex-row items-center justify-between gap-2 font-medium">
          <span>
            Ministry of Home Affairs — Border Patrol Information Command · SENTINEL-ID v4.2
          </span>
          <span className="text-xs text-slate-500">
            ICAO DOC 9303 &amp; ISO/IEC 30107-3 CERTIFIED INSPECTION STATION
          </span>
        </footer>
      </div>
    </div>
  );
}
