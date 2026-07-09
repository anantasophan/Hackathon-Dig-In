/**
 * ExportService — reusable export button group for any dashboard page.
 *
 * Renders an inline button group: [📥 Export] [▼ format selector].
 * On trigger, calls `api.exportData()` with the current page and active
 * filters, handles the presigned-URL download on success, and displays
 * contextual notifications for timeout and error states.
 *
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */

import React, { useState, useEffect, useCallback } from 'react';
import { api, ApiTimeoutError } from '../services/api';
import type { ActiveFilter, ExportRequest } from '../types/api';
import './ExportService.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExportServiceProps {
  /** Page identifier sent to the export API, e.g. "campaign_overview". */
  page: string;
  /** Active filters currently applied on the parent page. */
  filters: ActiveFilter[];
  /** Start of the selected time range, yyyy-mm-dd. */
  timeRangeStart: string;
  /** End of the selected time range, yyyy-mm-dd. */
  timeRangeEnd: string;
  /** When true, the export button is rendered in a disabled state. */
  disabled?: boolean;
}

type ExportFormat = 'pdf' | 'excel' | 'csv';

interface ToastState {
  message: string;
  type: 'success' | 'warning' | 'error';
}

// ---------------------------------------------------------------------------
// Toast sub-component
// ---------------------------------------------------------------------------

interface ToastProps {
  message: string;
  type: 'success' | 'warning' | 'error';
  onDismiss: () => void;
  /** When provided, renders a retry button that calls this callback. */
  onRetry?: () => void;
}

const Toast: React.FC<ToastProps> = ({ message, type, onDismiss, onRetry }) => {
  return (
    <div
      className={`export-toast export-toast--${type}`}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <span className="export-toast__message">{message}</span>
      <div className="export-toast__actions">
        {onRetry && (
          <button
            type="button"
            className="export-toast__retry"
            onClick={onRetry}
          >
            Coba Lagi
          </button>
        )}
        <button
          type="button"
          className="export-toast__dismiss"
          aria-label="Tutup notifikasi"
          onClick={onDismiss}
        >
          ✕
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// ExportService component
// ---------------------------------------------------------------------------

const ExportService: React.FC<ExportServiceProps> = ({
  page,
  filters,
  timeRangeStart,
  timeRangeEnd,
  disabled = false,
}) => {
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  // Auto-dismiss success toast after 5 seconds.
  useEffect(() => {
    if (toast?.type === 'success') {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // ── Export handler ────────────────────────────────────────────

  const handleExport = useCallback(async () => {
    if (exporting || disabled) return;

    setExporting(true);
    setToast(null);

    const request: ExportRequest = {
      page,
      format,
      filters,
      time_range_start: timeRangeStart,
      time_range_end: timeRangeEnd,
    };

    try {
      const response = await api.exportData(request);

      if (response.status === 'completed' && response.download_url) {
        // Trigger auto-download via presigned URL in a new tab.
        window.open(response.download_url, '_blank');
        setToast({
          message: '✅ File siap diunduh!',
          type: 'success',
        });
      } else if (response.status === 'timeout') {
        setToast({
          message:
            '⚠️ Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi.',
          type: 'warning',
        });
      } else {
        // status === 'error' or unexpected status
        const cause = response.error_message ?? 'Terjadi kesalahan tidak terduga.';
        setToast({
          message: `❌ Ekspor gagal: ${cause}. Coba lagi.`,
          type: 'error',
        });
      }
    } catch (err: unknown) {
      if (err instanceof ApiTimeoutError) {
        setToast({
          message:
            '⚠️ Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi.',
          type: 'warning',
        });
      } else {
        const message =
          err instanceof Error ? err.message : 'Terjadi kesalahan tidak terduga.';
        setToast({
          message: `❌ Ekspor gagal: ${message}. Coba lagi.`,
          type: 'error',
        });
      }
    } finally {
      setExporting(false);
    }
  }, [exporting, disabled, page, format, filters, timeRangeStart, timeRangeEnd]);

  const handleRetry = useCallback(() => {
    void handleExport();
  }, [handleExport]);

  const handleDismiss = useCallback(() => {
    setToast(null);
  }, []);

  // ── Render ────────────────────────────────────────────────────

  const isButtonDisabled = disabled || exporting;

  return (
    <div className="export-service">
      {/* ── Button group ─────────────────────────────────────── */}
      <div className="export-service__group" role="group" aria-label="Ekspor data">
        {/* Export trigger button */}
        <button
          type="button"
          className="export-service__btn"
          onClick={() => void handleExport()}
          disabled={isButtonDisabled}
          aria-busy={exporting}
          aria-label={exporting ? 'Sedang mengekspor...' : `Ekspor sebagai ${format.toUpperCase()}`}
        >
          {exporting ? '⏳ Mengekspor...' : '📥 Export'}
        </button>

        {/* Format selector */}
        <label htmlFor="export-format-select" className="export-service__sr-only">
          Format ekspor
        </label>
        <select
          id="export-format-select"
          className="export-service__select"
          value={format}
          onChange={(e) => setFormat(e.target.value as ExportFormat)}
          disabled={isButtonDisabled}
          aria-label="Pilih format ekspor"
        >
          <option value="csv">CSV</option>
          <option value="excel">Excel</option>
          <option value="pdf">PDF</option>
        </select>
      </div>

      {/* ── Toast notification ───────────────────────────────── */}
      {toast !== null && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={handleDismiss}
          onRetry={toast.type !== 'success' ? handleRetry : undefined}
        />
      )}
    </div>
  );
};

export default ExportService;
