/**
 * DashboardLayout — main application shell.
 *
 * Renders a two-column layout (sidebar-left, content-right):
 *   Sidebar  — logo header, user session info, nav links, logout button
 *   Content  — top header bar + children in scrollable view container
 *
 * Styling: Tailwind CSS utility classes only (no DashboardLayout.css).
 * Icons:   Lucide React — LayoutGrid, GitCompareArrows, Clock, MapPin,
 *          Users, Search, LogOut.
 *
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  GitCompareArrows,
  Clock,
  MapPin,
  Users,
  Search,
  LogOut,
  Sparkles,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────

interface NavItem {
  path: string;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
}

export interface DashboardLayoutProps {
  children: React.ReactNode;
  username?: string;
  onSignOut?: () => void;
}

// ── Navigation items ─────────────────────────────────────────────

const navItems: NavItem[] = [
  { path: '/overview', label: 'Campaign Overview', Icon: LayoutGrid },
  { path: '/comparison', label: 'Perbandingan Campaign', Icon: GitCompareArrows },
  { path: '/time-analysis', label: 'Time to Take Up', Icon: Clock },
  { path: '/regional', label: 'Performa Regional', Icon: MapPin },
  { path: '/customer-criteria', label: 'Kriteria Nasabah', Icon: Users },
  { path: '/similar-campaigns', label: 'Campaign Serupa', Icon: Search },
  { path: '/ai-recommendations', label: 'AI Recommendations', Icon: Sparkles },
];

// ── Component ────────────────────────────────────────────────────

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  username,
  onSignOut,
}) => {
  return (
    <div className="h-screen flex bg-gray-50 overflow-hidden">

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 bg-slate-900 flex flex-col">

        {/* Logo header */}
        <div className="bg-slate-950 px-5 py-4 border-b border-slate-800">
          <span className="text-sm font-bold text-white">
            Campaign Insight Generator
          </span>
          <div className="text-[10px] text-[#F15A24] font-semibold uppercase tracking-wider">
            BNI
          </div>
        </div>

        {/* User session info */}
        {username && (
          <div className="bg-slate-800/50 px-4 py-2.5">
            <span className="text-xs text-slate-400">Pengguna</span>
            <div className="text-xs font-medium text-slate-300">{username}</div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1" aria-label="Main navigation">
          {navItems.map(({ path, label, Icon }) => (
            <NavLink key={path} to={path}>
              {({ isActive }) => (
                <span
                  className={
                    isActive
                      ? 'w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-semibold bg-[#005E6A] text-white'
                      : 'w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors'
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{label}</span>
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Logout */}
        {onSignOut && (
          <div className="bg-slate-950 p-4 border-t border-slate-800">
            <button
              onClick={onSignOut}
              type="button"
              className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              <span>Logout</span>
            </button>
          </div>
        )}
      </aside>

      {/* ── Content area ────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col bg-slate-50 overflow-hidden">

        {/* Top Header Bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0 shadow-sm z-30">
          <h1 className="text-md font-bold text-gray-700">
            Campaign Insight Generator
          </h1>
        </header>

        {/* View container */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default DashboardLayout;
