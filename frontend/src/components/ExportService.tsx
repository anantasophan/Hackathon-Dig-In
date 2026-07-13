/**
 * ExportService — reusable export button group for any dashboard page.
 *
 * Renders an inline button group: [Export] [▼ format selector].
 * On trigger, calls `api.exportData()` with the current page and active
 * filters, handles the presigned-URL download on success, and displays
 * contextual notifications for timeout and error states.
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, CheckCircle, AlertCircle, XCircle, X } from 'lucide-react';
import { api, ApiTimeoutError } from '../services/api';
import type { ActiveFilter, ExportRequest } from '../types/api';

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
  const bgClass =
    type === 'success' ? 'bg-emerald-600' :
    type === 'warning' ? 'bg-amber-500' :
    'bg-rose-600';

  const Icon = type === 'success' ? CheckCircle : type === 'warning' ? AlertCircle : XCircle;

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white text-xs font-medium ${bgClass}`}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      <div className="flex items-center gap-2 flex-shrink-0">
        {onRetry && (
          <button
            type="button"
            className="text-xs underline opacity-90 hover:opacity-100 whitespace-nowrap"
            onClick={onRetry}
          >
            Coba Lagi
          </button>
        )}
        <button
          type="button"
          className="flex-shrink-0 opacity-80 hover:opacity-100 transition-opacity"
          aria-label="Tutup notifikasi"
          onClick={onDismiss}
        >
          <X className="w-3.5 h-3.5" />
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
          message: 'File siap diunduh',
          type: 'success',
        });
      } else if (response.status === 'timeout') {
        setToast({
          message:
            'Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi',
          type: 'warning',
        });
      } else {
        // status === 'error' or unexpected status
        const cause = response.error_message ?? 'Terjadi kesalahan tidak terduga.';
        setToast({
          message: `Ekspor gagal: ${cause}. Coba lagi`,
          type: 'error',
        });
      }
    } catch (err: unknown) {
      if (err instanceof ApiTimeoutError) {
        setToast({
          message:
            'Ekspor timeout (>30 detik). Coba kurangi rentang data atau coba lagi',
          type: 'warning',
        });
      } else {
        const message =
          err instanceof Error ? err.message : 'Terjadi kesalahan tidak terduga.';
        setToast({
          message: `Ekspor gagal: ${message}. Coba lagi`,
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
    <div className="flex items-center gap-2">
      {/* Button group */}
      <div className="flex items-center gap-2" role="group" aria-label="Ekspor data">
        <button
          type="button"
          className={isButtonDisabled
            ? (disabled
              ? 'flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
              : 'flex items-center gap-2 px-4 py-2 bg-[#005E6A]/70 text-white font-semibold rounded-lg text-xs cursor-not-allowed')
            : 'flex items-center gap-2 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
          }
          onClick={() => void handleExport()}
          disabled={isButtonDisabled}
          aria-busy={exporting}
          aria-label={exporting ? 'Sedang mengekspor...' : `Ekspor sebagai ${format.toUpperCase()}`}
        >
          {exporting
            ? <><Loader2 className="w-4 h-4 animate-spin" /><span>Mengekspor</span></>
            : <><Download className="w-4 h-4" /><span>Export</span></>
          }
        </button>

        <label htmlFor="export-format-select" className="sr-only">
          Format ekspor
        </label>
        <select
          id="export-format-select"
          className="px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none"
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

      {/* Toast notification — positioned fixed */}
      {toast !== null && (
        <div className="fixed bottom-5 right-5 max-w-sm space-y-2 z-50">
          <Toast
            message={toast.message}
            type={toast.type}
            onDismiss={handleDismiss}
            onRetry={toast.type !== 'success' ? handleRetry : undefined}
          />
        </div>
      )}
    </div>
  );
};

export default ExportService;
