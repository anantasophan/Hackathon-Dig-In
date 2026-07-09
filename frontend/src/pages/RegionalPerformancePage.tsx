/**
 * RegionalPerformancePage — Regional Performance dashboard page.
 *
 * Displays a ranked table of regions sorted by take_up_rate descending,
 * with a per-region 8-week trend line chart shown when the user selects
 * a row.  Supports Campaign ID input and flag_program product filter.
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import React, { useState, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import DashboardLayout from '../components/DashboardLayout';
import { api } from '../services/api';
import type {
  RegionalPerformanceResponse,
  RegionMetric,
  RegionalTrendPoint,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';
import './RegionalPerformancePage.css';

// ── Chart.js registration ─────────────────────────────────────────────────

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
);

// ── Constants ─────────────────────────────────────────────────────────────

const FLAG_PROGRAM_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Semua Program' },
  { value: 'PROGRAM QRIS', label: 'PROGRAM QRIS' },
  { value: 'PROGRAM BIAYA ADMIN', label: 'PROGRAM BIAYA ADMIN' },
];

// ── Helpers ───────────────────────────────────────────────────────────────

/** Format a number with Indonesian thousand-separator. */
function formatNumber(n: number): string {
  return n.toLocaleString('id-ID');
}

/** Format a take-up rate as a percentage string (2 decimal places). */
function formatRate(n: number): string {
  return `${n.toFixed(2)}%`;
}

/** Format currency in IDR. */
function formatCurrency(n: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(n);
}

/**
 * Filter trend points for a single region and build Chart.js data.
 * Expects points already sorted by week_start ascending from the backend.
 */
function buildTrendChartData(
  trend: RegionalTrendPoint[],
  wilayah: number,
  regionName: string,
) {
  const regionPoints = trend
    .filter((p) => p.wilayah === wilayah)
    .slice(-8); // guard: only last 8 weeks

  return {
    labels: regionPoints.map((p) => p.week_start),
    datasets: [
      {
        label: `Take-Up Rate — ${regionName}`,
        data: regionPoints.map((p) => p.take_up_rate),
        borderColor: '#3182ce',
        backgroundColor: 'rgba(49, 130, 206, 0.1)',
        borderWidth: 2,
        pointBackgroundColor: '#3182ce',
        pointRadius: 4,
        tension: 0.3,
        fill: true,
      },
    ],
  };
}

function buildTrendChartOptions(regionName: string) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
      title: {
        display: true,
        text: `Tren 8 Minggu — Wilayah ${regionName}`,
        font: { size: 14 },
        color: '#1a365d',
      },
      tooltip: {
        callbacks: {
          label: (ctx: { parsed: { y: number } }) =>
            `Take-Up Rate: ${ctx.parsed.y.toFixed(2)}%`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          maxTicksLimit: 8,
          maxRotation: 45,
          color: '#4a5568',
        },
        grid: { color: '#edf2f7' },
      },
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: string | number) => `${value}%`,
          color: '#4a5568',
        },
        grid: { color: '#edf2f7' },
      },
    },
  };
}

// ── Component ─────────────────────────────────────────────────────────────

const RegionalPerformancePage: React.FC = () => {
  const { user, signOut } = useAuth();

  // ── State ─────────────────────────────────────────────────────────────

  const [campaignId, setCampaignId] = useState('');
  const [flagProgram, setFlagProgram] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<number | null>(null);
  const [data, setData] = useState<RegionalPerformanceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Derived ───────────────────────────────────────────────────────────

  const canFetch = campaignId.trim().length > 0;

  /** The RegionMetric row for the currently selected wilayah. */
  const selectedRegionMetric: RegionMetric | undefined =
    selectedRegion !== null
      ? data?.regions.find((r) => r.wilayah === selectedRegion)
      : undefined;

  /** Trend points that exist for the selected region. */
  const hasTrendData =
    selectedRegion !== null &&
    (data?.trend ?? []).some((p) => p.wilayah === selectedRegion);

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleFetch = useCallback(async () => {
    const trimmedId = campaignId.trim();
    if (!trimmedId) return;

    setLoading(true);
    setError(null);
    setData(null);
    setSelectedRegion(null);

    try {
      const response = await api.getRegionalPerformance(
        trimmedId,
        flagProgram || undefined,
      );
      setData(response);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Terjadi kesalahan saat memuat data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [campaignId, flagProgram]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleFetch();
      }
    },
    [handleFetch],
  );

  const handleRowClick = useCallback((wilayah: number) => {
    setSelectedRegion((prev) => (prev === wilayah ? null : wilayah));
  }, []);

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <DashboardLayout username={user?.username} onSignOut={signOut}>
      {/* Spinner animation is declared in RegionalPerformancePage.css */}

      <div style={styles.pageRoot}>
        {/* ── Page heading ─────────────────────────────────────────── */}
        <h1 style={styles.pageTitle}>Performa Regional</h1>

        {/* ── Filter card ──────────────────────────────────────────── */}
        <div style={styles.card}>
          <h2 style={styles.sectionTitle}>Filter</h2>
          <div style={styles.filterRow}>
            {/* Campaign ID input */}
            <div style={styles.filterGroup}>
              <label htmlFor="campaign-id-input" style={styles.label}>
                Campaign ID
              </label>
              <input
                id="campaign-id-input"
                type="text"
                style={styles.input}
                placeholder="Masukkan Campaign ID"
                value={campaignId}
                onChange={(e) => {
                  setCampaignId(e.target.value);
                  setError(null);
                }}
                onKeyDown={handleKeyDown}
                aria-describedby="regional-input-hint"
                disabled={loading}
              />
              <span
                id="regional-input-hint"
                style={styles.hintText}
              >
                Tekan Enter atau klik Cari
              </span>
            </div>

            {/* Flag program filter */}
            <div style={styles.filterGroup}>
              <label htmlFor="flag-program-select" style={styles.label}>
                Program
              </label>
              <select
                id="flag-program-select"
                style={styles.select}
                value={flagProgram}
                onChange={(e) => setFlagProgram(e.target.value)}
                disabled={loading}
              >
                {FLAG_PROGRAM_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Fetch button */}
            <div style={styles.filterGroup}>
              {/* Invisible label to align button with inputs */}
              <span style={{ ...styles.label, visibility: 'hidden' }}>
                &nbsp;
              </span>
              <button
                type="button"
                style={
                  canFetch && !loading
                    ? styles.primaryButton
                    : styles.primaryButtonDisabled
                }
                onClick={handleFetch}
                disabled={!canFetch || loading}
                aria-busy={loading}
              >
                {loading ? 'Memuat…' : 'Cari'}
              </button>
            </div>
          </div>
        </div>

        {/* ── Loading state ─────────────────────────────────────────── */}
        {loading && (
          <div style={styles.centerState} role="status" aria-label="Memuat data">
            <div style={styles.spinner} aria-hidden="true" />
            <p style={styles.statusText}>Memuat data regional…</p>
          </div>
        )}

        {/* ── Error state ───────────────────────────────────────────── */}
        {!loading && error !== null && (
          <div style={styles.errorState} role="alert">
            <span style={styles.stateIcon} aria-hidden="true">⚠️</span>
            <p style={styles.errorText}>{error}</p>
            <p style={styles.statusText}>Periksa Campaign ID dan coba lagi.</p>
          </div>
        )}

        {/* ── Idle / no-search state ────────────────────────────────── */}
        {!loading && error === null && data === null && (
          <div style={styles.centerState} role="status">
            <span style={styles.stateIcon} aria-hidden="true">🗺️</span>
            <p style={styles.idleTitle}>Belum ada data ditampilkan</p>
            <p style={styles.statusText}>
              Masukkan Campaign ID di atas dan tekan <strong>Cari</strong> untuk
              melihat performa regional.
            </p>
          </div>
        )}

        {/* ── Empty regional data ───────────────────────────────────── */}
        {!loading && error === null && data !== null && data.regions.length === 0 && (
          <div style={styles.centerState} role="status">
            <span style={styles.stateIcon} aria-hidden="true">📭</span>
            <p style={styles.idleTitle}>Tidak ada data regional</p>
            <p style={styles.statusText}>
              Tidak ada data wilayah yang tersedia untuk campaign{' '}
              <strong>{data.campaign_name || data.campaign_id}</strong>
              {flagProgram ? ` dengan program ${flagProgram}` : ''}.
              Coba ubah filter program atau pilih campaign lain.
            </p>
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────────── */}
        {!loading && error === null && data !== null && data.regions.length > 0 && (
          <>
            {/* Campaign name banner */}
            <div style={styles.campaignBanner}>
              <span style={styles.campaignBannerLabel}>Campaign:</span>
              <span style={styles.campaignBannerValue}>
                {data.campaign_name || data.campaign_id}
              </span>
              {data.flag_program && (
                <span style={styles.programTag}>{data.flag_program}</span>
              )}
            </div>

            {/* Region performance table */}
            <div style={styles.card}>
              <h2 style={styles.sectionTitle}>
                Performa per Wilayah{' '}
                <span style={styles.subtleNote}>
                  — klik baris untuk melihat tren 8 minggu
                </span>
              </h2>
              <div style={{ overflowX: 'auto' }}>
                <table
                  style={styles.table}
                  aria-label="Tabel performa regional"
                  aria-describedby="region-table-desc"
                >
                  <caption id="region-table-desc" style={styles.visuallyHidden}>
                    Tabel wilayah diurutkan berdasarkan Take Up Rate tertinggi.
                    Klik baris untuk melihat grafik tren 8 minggu.
                  </caption>
                  <thead>
                    <tr>
                      <th style={styles.thCell} scope="col">Rank</th>
                      <th style={styles.thCell} scope="col">Wilayah</th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }} scope="col">
                        Total Leads
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }} scope="col">
                        Total Take Up
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }} scope="col">
                        Take Up Rate
                      </th>
                      <th style={{ ...styles.thCell, textAlign: 'right' }} scope="col">
                        Avg. Transaksi
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.regions.map((region, idx) => {
                      const isSelected = selectedRegion === region.wilayah;
                      const baseRow = idx % 2 === 0 ? styles.tdEven : styles.tdOdd;
                      const tdStyle = isSelected
                        ? styles.tdSelected
                        : baseRow;

                      return (
                        <tr
                          key={region.wilayah}
                          style={{
                            ...styles.tableRow,
                            ...(isSelected ? styles.tableRowSelected : {}),
                          }}
                          onClick={() => handleRowClick(region.wilayah)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleRowClick(region.wilayah);
                            }
                          }}
                          tabIndex={0}
                          role="row"
                          aria-selected={isSelected}
                          aria-label={`Wilayah ${region.region_name}, Take Up Rate ${formatRate(region.take_up_rate)}`}
                        >
                          <td style={tdStyle}>{idx + 1}</td>
                          <td style={tdStyle}>
                            <span style={styles.regionName}>
                              {region.region_name}
                            </span>
                            <span style={styles.regionCode}>
                              &nbsp;(W{region.wilayah})
                            </span>
                          </td>
                          <td style={{ ...tdStyle, textAlign: 'right' }}>
                            {formatNumber(region.total_leads)}
                          </td>
                          <td style={{ ...tdStyle, textAlign: 'right' }}>
                            {formatNumber(region.total_take_up)}
                          </td>
                          <td style={{ ...tdStyle, textAlign: 'right' }}>
                            <span
                              style={
                                region.take_up_rate >= 10
                                  ? styles.rateHigh
                                  : region.take_up_rate >= 5
                                  ? styles.rateMid
                                  : styles.rateLow
                              }
                            >
                              {formatRate(region.take_up_rate)}
                            </span>
                          </td>
                          <td style={{ ...tdStyle, textAlign: 'right' }}>
                            {formatCurrency(region.avg_transaction_value)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* ── 8-week trend chart ────────────────────────────────── */}
            {selectedRegion !== null && (
              <div style={styles.card} aria-live="polite" aria-atomic="true">
                <h2 style={styles.sectionTitle}>
                  Tren 8 Minggu —{' '}
                  <span style={{ color: '#3182ce' }}>
                    {selectedRegionMetric?.region_name ?? `Wilayah ${selectedRegion}`}
                  </span>
                </h2>

                {hasTrendData ? (
                  <div style={styles.chartContainer}>
                    <Line
                      data={buildTrendChartData(
                        data.trend,
                        selectedRegion,
                        selectedRegionMetric?.region_name ??
                          `W${selectedRegion}`,
                      )}
                      options={buildTrendChartOptions(
                        selectedRegionMetric?.region_name ??
                          `W${selectedRegion}`,
                      )}
                      aria-label={`Grafik tren 8 minggu untuk wilayah ${
                        selectedRegionMetric?.region_name ?? selectedRegion
                      }`}
                    />
                  </div>
                ) : (
                  <div style={styles.trendEmpty} role="status">
                    <span style={styles.stateIcon} aria-hidden="true">📉</span>
                    <p style={styles.statusText}>
                      Data tren tidak tersedia untuk wilayah ini.
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  pageRoot: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    minHeight: '100%',
  },
  pageTitle: {
    margin: 0,
    fontSize: '1.75rem',
    fontWeight: 700,
    color: '#1a365d',
  },

  // ── Filter card
  card: {
    background: '#f7fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '16px',
  },
  sectionTitle: {
    margin: '0 0 12px 0',
    fontSize: '1rem',
    fontWeight: 600,
    color: '#1a365d',
  },
  subtleNote: {
    fontSize: '0.8rem',
    fontWeight: 400,
    color: '#718096',
  },
  filterRow: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap' as const,
    alignItems: 'flex-end',
  },
  filterGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  },
  label: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#4a5568',
  },
  hintText: {
    fontSize: '0.75rem',
    color: '#a0aec0',
  },
  input: {
    padding: '0.5rem 0.75rem',
    border: '1px solid #cbd5e0',
    borderRadius: '4px',
    fontSize: '0.9rem',
    width: '240px',
    outline: 'none',
    background: '#fff',
  },
  select: {
    padding: '0.5rem 0.75rem',
    border: '1px solid #cbd5e0',
    borderRadius: '4px',
    fontSize: '0.9rem',
    background: '#fff',
    cursor: 'pointer',
    minWidth: '200px',
  },
  primaryButton: {
    padding: '0.5rem 1.25rem',
    background: '#1a365d',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  primaryButtonDisabled: {
    padding: '0.5rem 1.25rem',
    background: '#a0aec0',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'not-allowed',
  },

  // ── States
  centerState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 16px',
    gap: '12px',
    background: '#f7fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    textAlign: 'center' as const,
  },
  errorState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    padding: '32px 16px',
    gap: '10px',
    background: '#fff5f5',
    border: '1px solid #feb2b2',
    borderRadius: '8px',
    textAlign: 'center' as const,
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #e2e8f0',
    borderTopColor: '#3182ce',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  stateIcon: {
    fontSize: '2.5rem',
  },
  idleTitle: {
    margin: 0,
    color: '#1a365d',
    fontSize: '1.1rem',
    fontWeight: 700,
  },
  statusText: {
    margin: 0,
    color: '#4a5568',
    fontSize: '0.9rem',
  },
  errorText: {
    margin: 0,
    color: '#c53030',
    fontSize: '1rem',
    fontWeight: 600,
  },

  // ── Campaign banner
  campaignBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    background: '#ebf8ff',
    border: '1px solid #bee3f8',
    borderRadius: '6px',
    flexWrap: 'wrap' as const,
  },
  campaignBannerLabel: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#2b6cb0',
  },
  campaignBannerValue: {
    fontSize: '0.875rem',
    color: '#1a365d',
    fontWeight: 700,
  },
  programTag: {
    background: '#c6f6d5',
    border: '1px solid #9ae6b4',
    color: '#276749',
    borderRadius: '4px',
    padding: '2px 8px',
    fontSize: '0.8rem',
    fontWeight: 600,
  },

  // ── Table
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '0.875rem',
  },
  thCell: {
    padding: '0.6rem 0.75rem',
    textAlign: 'left' as const,
    background: '#1a365d',
    color: '#fff',
    fontWeight: 600,
    whiteSpace: 'nowrap' as const,
  },
  tableRow: {
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  tableRowSelected: {
    outline: '2px solid #3182ce',
    outlineOffset: '-2px',
  },
  tdEven: {
    padding: '0.6rem 0.75rem',
    background: '#fff',
    borderBottom: '1px solid #e2e8f0',
  },
  tdOdd: {
    padding: '0.6rem 0.75rem',
    background: '#f7fafc',
    borderBottom: '1px solid #e2e8f0',
  },
  tdSelected: {
    padding: '0.6rem 0.75rem',
    background: '#ebf8ff',
    borderBottom: '1px solid #bee3f8',
  },
  regionName: {
    fontWeight: 600,
    color: '#2d3748',
  },
  regionCode: {
    color: '#718096',
    fontSize: '0.8rem',
  },

  // ── Rate badges
  rateHigh: {
    background: '#c6f6d5',
    color: '#276749',
    borderRadius: '4px',
    padding: '2px 7px',
    fontWeight: 600,
    fontSize: '0.85rem',
  },
  rateMid: {
    background: '#fefcbf',
    color: '#744210',
    borderRadius: '4px',
    padding: '2px 7px',
    fontWeight: 600,
    fontSize: '0.85rem',
  },
  rateLow: {
    background: '#fff5f5',
    color: '#c53030',
    borderRadius: '4px',
    padding: '2px 7px',
    fontWeight: 600,
    fontSize: '0.85rem',
  },

  // ── Trend chart
  chartContainer: {
    height: '340px',
  },
  trendEmpty: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    padding: '32px 16px',
    gap: '10px',
    textAlign: 'center' as const,
  },

  // ── Accessibility
  visuallyHidden: {
    position: 'absolute' as const,
    width: '1px',
    height: '1px',
    padding: '0',
    margin: '-1px',
    overflow: 'hidden' as const,
    clip: 'rect(0,0,0,0)',
    whiteSpace: 'nowrap' as const,
    border: '0',
  },
};

export default RegionalPerformancePage;
