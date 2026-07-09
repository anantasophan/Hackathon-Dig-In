/**
 * DashboardLayout — main application shell.
 *
 * Renders a three-region layout:
 *   Header  — app title, username, logout button
 *   Sidebar — navigation links to all six pages
 *   Content — renders `children` in the main area
 *
 * Requirements: 1.1
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import './DashboardLayout.css';

// ── Types ────────────────────────────────────────────────────────

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

export interface DashboardLayoutProps {
  children: React.ReactNode;
  username?: string;
  onSignOut?: () => void;
}

// ── Navigation items ─────────────────────────────────────────────

const navItems: NavItem[] = [
  { path: '/overview', label: 'Campaign Overview', icon: '📊' },
  { path: '/comparison', label: 'Perbandingan Campaign', icon: '⚖️' },
  { path: '/time-analysis', label: 'Time to Take Up', icon: '⏱️' },
  { path: '/regional', label: 'Performa Regional', icon: '🗺️' },
  { path: '/customer-criteria', label: 'Kriteria Nasabah', icon: '👥' },
  { path: '/similar-campaigns', label: 'Campaign Serupa', icon: '🔍' },
];

// ── Component ────────────────────────────────────────────────────

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  username,
  onSignOut,
}) => {
  return (
    <div className="dashboard-root">
      {/* ── Header ────────────────────────────────────────────── */}
      <header className="dashboard-header">
        <span className="dashboard-header__title">
          Campaign Insight Generator
        </span>

        <div className="dashboard-header__right">
          {username && (
            <span className="dashboard-header__username">{username}</span>
          )}
          {onSignOut && (
            <button
              className="dashboard-header__logout"
              onClick={onSignOut}
              type="button"
            >
              Logout
            </button>
          )}
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────── */}
      <div className="dashboard-body">
        {/* ── Sidebar ─────────────────────────────────────────── */}
        <nav className="dashboard-sidebar" aria-label="Main navigation">
          <ul className="dashboard-sidebar__nav" role="list">
            {navItems.map(({ path, label, icon }) => (
              <li key={path} className="dashboard-sidebar__item">
                <NavLink
                  to={path}
                  className={({ isActive }) =>
                    isActive
                      ? 'dashboard-sidebar__link active'
                      : 'dashboard-sidebar__link'
                  }
                  aria-current={undefined}
                >
                  <span className="dashboard-sidebar__icon" aria-hidden="true">
                    {icon}
                  </span>
                  <span className="dashboard-sidebar__label">{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* ── Content ─────────────────────────────────────────── */}
        <main className="dashboard-content">{children}</main>
      </div>
    </div>
  );
};

export default DashboardLayout;
