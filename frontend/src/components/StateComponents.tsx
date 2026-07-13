/**
 * StateComponents — Shared empty, loading, and error state components.
 *
 * Provides three standardised state display components used across all
 * dashboard pages for consistent UX when data is absent, loading, or
 * when an error has occurred.
 *
 * Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
 */

import React from 'react';
import { Inbox, Loader2, AlertCircle } from 'lucide-react';

// ── EmptyState ────────────────────────────────────────────────────────────

interface EmptyStateProps {
  message?: string;
  hint?: string;
}

/**
 * EmptyState — shown when a query returns no data.
 *
 * Displays an Inbox icon, a primary message, and an optional hint line.
 * Default text follows the formal Bahasa Indonesia tone used throughout
 * the application (no emoji, no exclamation marks).
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  message = 'Tidak ada data tersedia',
  hint = 'Silakan sesuaikan filter untuk menampilkan data',
}) => (
  <div className="text-center py-12 text-gray-400">
    <Inbox className="w-8 h-8 mx-auto mb-2 text-gray-300" />
    <p className="text-sm font-medium">{message}</p>
    <p className="text-xs mt-1">{hint}</p>
  </div>
);

// ── LoadingState ──────────────────────────────────────────────────────────

interface LoadingStateProps {
  text?: string;
}

/**
 * LoadingState — shown while an API request is in flight.
 *
 * Uses the BNI Teal spinning `Loader2` icon with a configurable label.
 * Pass `text` to override the default "Memuat data" copy (e.g. "Mencari"
 * for the SimilarCampaignPage search operation).
 */
export const LoadingState: React.FC<LoadingStateProps> = ({
  text = 'Memuat data',
}) => (
  <div className="text-center py-12 text-gray-400">
    <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin text-[#005E6A]" />
    <p className="text-sm font-medium">{text}</p>
  </div>
);

// ── ErrorState ────────────────────────────────────────────────────────────

interface ErrorStateProps {
  message: string;
}

/**
 * ErrorState — shown when an API call fails.
 *
 * Displays an AlertCircle icon in rose, a fixed "Terjadi kesalahan" heading,
 * and the error message passed via the `message` prop.
 */
export const ErrorState: React.FC<ErrorStateProps> = ({ message }) => (
  <div className="text-center py-12">
    <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
    <p className="text-sm font-medium text-rose-600">Terjadi kesalahan</p>
    <p className="text-xs mt-1 text-gray-500">{message}</p>
  </div>
);
