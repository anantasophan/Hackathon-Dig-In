/**
 * CampaignComparisonPage — side-by-side campaign comparison dashboard.
 *
 * Allows the user to select 2–5 campaign IDs and compare them across
 * five key metrics: Total Leads, Total Take Up, Take-Up Rate,
 * Nilai Transaksi, and Durasi (hari).  Results are displayed in both
 * a comparison table and a grouped bar chart.
 *
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
 */

import React, { useState, useCallback, useRef } from 'react';
import './CampaignComparisonPage.css';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import DashboardLayout from '../components/DashboardLayout';
import { api } from '../services/api';
import type { CampaignMetric, CampaignComparisonResponse } from '../types/api';

// ---------------------------------------------------------------------------
// Chart.js registration
// ---------------------------------------------------------------------------

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_CAMPAIGNS = 5;
const MIN_CAMPAIGNS = 2;

/** Group-by options aligned with CampaignComparisonRequest.group_by */
const GROUP_BY_OPTIONS = [
  { value: '', label: '-- Tidak ada --' },
  { value: 'flag_program', label: 'Jenis Program' },
  { value: 'wilayah', label: 'Wilayah' },
  { value: 'media_blasting', label: 'Channel' },
] as const;

type GroupByValue = '' | 'flag_program' | 'wilayah' | 'media_blasting';

/**
 * Chart.js dataset colors — one per metric, cycling if needed.
 * Five distinct colors matching the five comparison metrics.
 */
const METRIC_COLORS = [
  'rgba(26, 54, 93, 0.8)',    // Total Leads — dark navy
  'rgba(49, 130, 206, 0.8)',  // Total Take Up — medium blue
  'rgba(72, 187, 120, 0.8)',  // Take-Up Rate — green
  'rgba(237, 137, 54, 0.8)',  // Nilai Transaksi — orange
  'rgba(159, 122, 234, 0.8)', // Durasi — purple
];

const METRIC_BORDER_COLORS = [
  'rgba(26, 54, 93, 1)',
  'rgba(49, 130, 206, 1)',
  'rgba(72, 187, 120, 1)',
  'rgba(237, 137, 54, 1)',
  'rgba(159, 122, 234, 1)',
];

// ---------------------------------------------------------------------------
// Helper: format numbers
// ---------------------------------------------------------------------------

function formatNumber(value: number): string {
  return value.toLocaleString('id-ID');
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

// ---------------------------------------------------------------------------
// Helper: build Chart.js data
// ---------------------------------------------------------------------------

/**
 * Builds Chart.js `data` prop from the campaigns list.
 *
 * Layout: one bar group per metric, one bar per campaign.
 * This makes cross-campaign comparison obvious for each metric.
 */
function buildChartData(campaigns: CampaignMetric[]) {
  const labels = [
    'Total Leads',
    'Total Take Up',
    'Take-Up Rate (%)',
    'Nilai Transaksi (Rp juta)',
    'Durasi (hari)',
  ];

  const datasets = campaigns.map((c, idx) => ({
    label: c.campaign_name || c.campaign_id,
    data: [
      c.total_leads,
      c.total_take_up,
      c.take_up_rate,
      // Scale to millions for readability on chart
      Math.round(c.total_transaction_value / 1_000_000),
      c.duration_days,
    ],
    backgroundColor: METRIC_COLORS[idx % METRIC_COLORS.length],
    borderColor: METRIC_BORDER_COLORS[idx % METRIC_BORDER_COLORS.length],
    borderWidth: 1,
  }));

  return { labels, datasets };
}

const chartOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' as const },
    title: {
      display: true,
      text: 'Perbandingan Metrik Campaign',
      font: { size: 16 },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
    },
  },
};

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = {
  container: {
    padding: '1.5rem',
    maxWidth: '1200px',
  } as React.CSSProperties,

  heading: {
    fontSize: '1.5rem',
    fontWeight: 700 as const,
    color: '#1a365d',
    marginBottom: '1.5rem',
    marginTop: 0,
  } as React.CSSProperties,

  card: {
    backgroundColor: '#f7fafc',
    borderRadius: '8px',
    padding: '1.25rem',
    marginBottom: '1.5rem',
    border: '1px solid #e2e8f0',
  } as React.CSSProperties,

  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 600 as const,
    color: '#1a365d',
    marginBottom: '0.75rem',
    marginTop: 0,
  } as React.CSSProperties,

  inputRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    flexWrap: 'wrap' as const,
  } as React.CSSProperties,

  input: {
    padding: '0.5rem 0.75rem',
    border: '1px solid #cbd5e0',
    borderRadius: '4px',
    fontSize: '0.9rem',
    width: '220px',
    outline: 'none',
  } as React.CSSProperties,

  addButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#1a365d',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.9rem',
    cursor: 'pointer',
  } as React.CSSProperties,

  addButtonDisabled: {
    padding: '0.5rem 1rem',
    backgroundColor: '#a0aec0',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.9rem',
    cursor: 'not-allowed',
  } as React.CSSProperties,

  chipRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '0.5rem',
    marginTop: '0.75rem',
  } as React.CSSProperties,

  chip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    padding: '0.3rem 0.6rem',
    backgroundColor: '#bee3f8',
    color: '#1a365d',
    borderRadius: '12px',
    fontSize: '0.85rem',
    fontWeight: 500 as const,
  } as React.CSSProperties,

  chipRemove: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#1a365d',
    fontSize: '0.85rem',
    padding: '0',
    lineHeight: 1,
    fontWeight: 700 as const,
  } as React.CSSProperties,

  errorText: {
    color: '#c53030',
    fontSize: '0.85rem',
    marginTop: '0.5rem',
  } as React.CSSProperties,

  select: {
    padding: '0.5rem 0.75rem',
    border: '1px solid #cbd5e0',
    borderRadius: '4px',
    fontSize: '0.9rem',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
  } as React.CSSProperties,

  compareButton: {
    padding: '0.6rem 1.5rem',
    backgroundColor: '#1a365d',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    fontWeight: 600 as const,
    cursor: 'pointer',
  } as React.CSSProperties,

  compareButtonDisabled: {
    padding: '0.6rem 1.5rem',
    backgroundColor: '#a0aec0',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    fontWeight: 600 as const,
    cursor: 'not-allowed',
  } as React.CSSProperties,

  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '0.875rem',
  } as React.CSSProperties,

  thCell: {
    padding: '0.6rem 0.75rem',
    textAlign: 'left' as const,
    backgroundColor: '#1a365d',
    color: '#ffffff',
    fontWeight: 600 as const,
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,

  tdEven: {
    padding: '0.6rem 0.75rem',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
  } as React.CSSProperties,

  tdOdd: {
    padding: '0.6rem 0.75rem',
    backgroundColor: '#f7fafc',
    borderBottom: '1px solid #e2e8f0',
  } as React.CSSProperties,

  spinnerContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '3rem',
    gap: '0.75rem',
  } as React.CSSProperties,

  spinner: {
    width: 36,
    height: 36,
    border: '4px solid #e2e8f0',
    borderTopColor: '#1a365d',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as React.CSSProperties,

  emptyState: {
    textAlign: 'center' as const,
    padding: '3rem',
    color: '#718096',
    fontSize: '0.95rem',
  } as React.CSSProperties,

  errorState: {
    padding: '1rem',
    backgroundColor: '#fff5f5',
    border: '1px solid #feb2b2',
    borderRadius: '6px',
    color: '#c53030',
    fontSize: '0.9rem',
  } as React.CSSProperties,

  groupByRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flexWrap: 'wrap' as const,
  } as React.CSSProperties,

  label: {
    fontSize: '0.9rem',
    color: '#4a5568',
    fontWeight: 500 as const,
  } as React.CSSProperties,

  chartWrapper: {
    maxHeight: '420px',
    position: 'relative' as const,
  } as React.CSSProperties,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CampaignComparisonPage: React.FC = () => {
  // ── State ─────────────────────────────────────────────────────────────────

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [maxLimitError, setMaxLimitError] = useState(false);
  const [duplicateError, setDuplicateError] = useState(false);
  const [emptyError, setEmptyError] = useState(false);

  const [groupBy, setGroupBy] = useState<GroupByValue>('');

  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<CampaignComparisonResponse | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleAddCampaign = useCallback(() => {
    const trimmed = inputValue.trim();

    // Reset inline errors
    setMaxLimitError(false);
    setDuplicateError(false);
    setEmptyError(false);

    if (!trimmed) {
      setEmptyError(true);
      return;
    }

    if (selectedIds.length >= MAX_CAMPAIGNS) {
      setMaxLimitError(true);
      return;
    }

    if (selectedIds.includes(trimmed)) {
      setDuplicateError(true);
      return;
    }

    setSelectedIds((prev) => [...prev, trimmed]);
    setInputValue('');
    inputRef.current?.focus();
  }, [inputValue, selectedIds]);

  const handleRemoveCampaign = useCallback((id: string) => {
    setSelectedIds((prev) => prev.filter((s) => s !== id));
    setMaxLimitError(false);
  }, []);

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleAddCampaign();
      }
    },
    [handleAddCampaign],
  );

  const handleCompare = useCallback(async () => {
    if (selectedIds.length < MIN_CAMPAIGNS) return;

    setIsLoading(true);
    setApiError(null);
    setResult(null);

    try {
      const response = await api.compareCampaigns({
        campaign_ids: selectedIds,
        group_by: groupBy !== '' ? groupBy : undefined,
      });

      // Sort campaigns ascending by campaign_id (requirement: ascending sort)
      const sorted: CampaignComparisonResponse = {
        ...response,
        campaigns: [...response.campaigns].sort((a, b) =>
          a.campaign_id.localeCompare(b.campaign_id),
        ),
      };

      setResult(sorted);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Terjadi kesalahan saat memuat data.';
      setApiError(message);
    } finally {
      setIsLoading(false);
    }
  }, [selectedIds, groupBy]);

  // ── Derived ───────────────────────────────────────────────────────────────

  const canCompare = selectedIds.length >= MIN_CAMPAIGNS;
  const canAdd = selectedIds.length < MAX_CAMPAIGNS;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <DashboardLayout>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div style={styles.container}>
        {/* ── Page heading ─────────────────────────────────────────────── */}
        <h1 style={styles.heading}>Perbandingan Campaign</h1>

        {/* ── Campaign ID input card ────────────────────────────────────── */}
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Pilih Campaign (2–5 campaign)</h2>

          {/* Input row */}
          <div style={styles.inputRow}>
            <label htmlFor="campaign-id-input" style={styles.label}>
              Campaign ID:
            </label>
            <input
              id="campaign-id-input"
              ref={inputRef}
              type="text"
              style={styles.input}
              placeholder="Masukkan Campaign ID"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                setEmptyError(false);
                setDuplicateError(false);
                setMaxLimitError(false);
              }}
              onKeyDown={handleInputKeyDown}
              aria-describedby="campaign-input-error"
              disabled={!canAdd}
            />
            <button
              type="button"
              style={canAdd ? styles.addButton : styles.addButtonDisabled}
              onClick={handleAddCampaign}
              disabled={!canAdd}
              aria-label="Tambah campaign"
            >
              Tambah
            </button>
          </div>

          {/* Inline error messages */}
          <div id="campaign-input-error" role="alert" aria-live="polite">
            {maxLimitError && (
              <p style={styles.errorText}>
                Maksimal 5 campaign dapat dipilih.
              </p>
            )}
            {duplicateError && (
              <p style={styles.errorText}>
                Campaign ID ini sudah ditambahkan.
              </p>
            )}
            {emptyError && (
              <p style={styles.errorText}>
                Masukkan Campaign ID terlebih dahulu.
              </p>
            )}
          </div>

          {/* Selected campaign chips */}
          {selectedIds.length > 0 && (
            <div style={styles.chipRow} role="list" aria-label="Campaign terpilih">
              {selectedIds.map((id) => (
                <span key={id} style={styles.chip} role="listitem">
                  {id}
                  <button
                    type="button"
                    style={styles.chipRemove}
                    onClick={() => handleRemoveCampaign(id)}
                    aria-label={`Hapus campaign ${id}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* ── Group-by & Compare controls ───────────────────────────────── */}
        <div style={styles.card}>
          <div style={styles.groupByRow}>
            <label htmlFor="group-by-select" style={styles.label}>
              Kelompokkan berdasarkan:
            </label>
            <select
              id="group-by-select"
              style={styles.select}
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupByValue)}
            >
              {GROUP_BY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <button
              type="button"
              style={canCompare ? styles.compareButton : styles.compareButtonDisabled}
              onClick={handleCompare}
              disabled={!canCompare || isLoading}
              aria-disabled={!canCompare || isLoading}
            >
              {isLoading ? 'Memuat…' : 'Bandingkan'}
            </button>

            {!canCompare && (
              <span style={{ fontSize: '0.85rem', color: '#718096' }}>
                Pilih minimal 2 campaign untuk membandingkan.
              </span>
            )}
          </div>
        </div>

        {/* ── Loading state ─────────────────────────────────────────────── */}
        {isLoading && (
          <div style={styles.spinnerContainer} role="status" aria-label="Memuat data">
            <div style={styles.spinner} />
            <span style={{ color: '#4a5568' }}>Memuat data perbandingan…</span>
          </div>
        )}

        {/* ── Error state ───────────────────────────────────────────────── */}
        {apiError && !isLoading && (
          <div style={styles.errorState} role="alert">
            <strong>Gagal memuat data:</strong> {apiError}
          </div>
        )}

        {/* ── Empty state ───────────────────────────────────────────────── */}
        {!isLoading && !apiError && result === null && (
          <div style={styles.emptyState}>
            <p>Pilih 2–5 campaign dan tekan <strong>Bandingkan</strong> untuk melihat hasil perbandingan.</p>
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────────────── */}
        {!isLoading && result !== null && (
          <>
            {/* Comparison table */}
            <div style={styles.card}>
              <h2 style={styles.sectionTitle}>Tabel Perbandingan</h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={styles.table} aria-label="Tabel perbandingan campaign">
                  <thead>
                    <tr>
                      <th style={styles.thCell}>Campaign ID</th>
                      <th style={styles.thCell}>Nama Campaign</th>
                      <th style={styles.thCell}>Flag Program</th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }}>
                        Total Leads
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }}>
                        Total Take Up
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }}>
                        Take-Up Rate (%)
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }}>
                        Nilai Transaksi (Rp)
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }}>
                        Durasi (hari)
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.campaigns.map((c, idx) => {
                      const td = idx % 2 === 0 ? styles.tdEven : styles.tdOdd;
                      return (
                        <tr key={c.campaign_id}>
                          <td style={td}>{c.campaign_id}</td>
                          <td style={td}>{c.campaign_name}</td>
                          <td style={td}>{c.flag_program}</td>
                          <td style={{ ...td, textAlign: 'right' }}>
                            {formatNumber(c.total_leads)}
                          </td>
                          <td style={{ ...td, textAlign: 'right' }}>
                            {formatNumber(c.total_take_up)}
                          </td>
                          <td style={{ ...td, textAlign: 'right' }}>
                            {formatPercent(c.take_up_rate)}
                          </td>
                          <td style={{ ...td, textAlign: 'right' }}>
                            {formatCurrency(c.total_transaction_value)}
                          </td>
                          <td style={{ ...td, textAlign: 'right' }}>
                            {formatNumber(c.duration_days)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Bar chart */}
            <div style={styles.card}>
              <h2 style={styles.sectionTitle}>Grafik Perbandingan</h2>
              <div style={styles.chartWrapper}>
                <Bar
                  data={buildChartData(result.campaigns)}
                  options={chartOptions}
                  aria-label="Grafik perbandingan metrik campaign"
                />
              </div>
              <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '0.5rem' }}>
                * Nilai Transaksi diskalakan ke jutaan Rupiah (Rp juta) untuk keterbacaan grafik.
              </p>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CampaignComparisonPage;
