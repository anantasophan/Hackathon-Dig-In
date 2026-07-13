/**
 * RegionalPerformancePage — Regional Performance dashboard page.
 *
 * Displays a ranked table of regions sorted by take_up_rate descending,
 * with a per-region 8-week trend line chart shown when the user selects
 * a row.  Supports Campaign ID input and flag_program product filter.
 *
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 8.13
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
import { MapPin } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { EmptyState, LoadingState, ErrorState } from '../components/StateComponents';
import { api } from '../services/api';
import type {
  RegionalPerformanceResponse,
  RegionMetric,
  RegionalTrendPoint,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';

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

// ── Badge helper ──────────────────────────────────────────────────────────

/**
 * Returns a full Tailwind class string for the take-up rate badge.
 * Exported so it can be unit/property tested.
 *
 * @param rate - take-up rate percentage (e.g. 12.5 means 12.5%)
 */
export function getTakeUpBadgeClasses(rate: number): string {
  if (rate >= 10) return 'bg-emerald-100 text-emerald-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  if (rate >= 5)  return 'bg-amber-100 text-amber-700 rounded px-1.5 py-0.5 text-xs font-semibold';
  return 'bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 text-xs font-semibold';
}

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
        borderColor: '#005E6A',
        backgroundColor: 'rgba(0, 94, 106, 0.1)',
        borderWidth: 2,
        pointBackgroundColor: '#005E6A',
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
        color: '#1e293b',
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
          color: '#475569',
        },
        grid: { color: '#f1f5f9' },
      },
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: string | number) => `${value}%`,
          color: '#475569',
        },
        grid: { color: '#f1f5f9' },
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
      <div className="flex flex-col gap-4">

        {/* ── Filter card ──────────────────────────────────────────── */}
        <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Filter
          </h2>
          <div className="flex gap-4 flex-wrap items-end">

            {/* Campaign ID input */}
            <div className="flex flex-col gap-1">
              <label
                htmlFor="campaign-id-input"
                className="text-xs font-bold uppercase tracking-wider text-gray-600"
              >
                Campaign ID
              </label>
              <input
                id="campaign-id-input"
                type="text"
                className="w-60 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
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
                className="text-xs text-gray-400"
              >
                Tekan Enter atau klik Cari
              </span>
            </div>

            {/* Flag program filter */}
            <div className="flex flex-col gap-1">
              <label
                htmlFor="flag-program-select"
                className="text-xs font-bold uppercase tracking-wider text-gray-600"
              >
                Program
              </label>
              <select
                id="flag-program-select"
                className="px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none min-w-[200px]"
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
            <div className="flex flex-col gap-1">
              {/* Invisible label to vertically align button with inputs */}
              <span
                className="text-xs font-bold uppercase tracking-wider text-gray-600 invisible"
                aria-hidden="true"
              >
                &nbsp;
              </span>
              <button
                type="button"
                className={
                  canFetch && !loading
                    ? 'px-5 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
                    : 'px-5 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
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
          <LoadingState />
        )}

        {/* ── Error state ───────────────────────────────────────────── */}
        {!loading && error !== null && (
          <ErrorState message={`${error} Periksa Campaign ID dan coba lagi.`} />
        )}

        {/* ── Idle / no-search state ────────────────────────────────── */}
        {!loading && error === null && data === null && (
          <div
            className="text-center py-12 text-gray-400"
            role="status"
          >
            <MapPin className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm font-medium">Belum ada data ditampilkan</p>
            <p className="text-xs mt-1">
              Masukkan Campaign ID di atas dan tekan <strong>Cari</strong> untuk
              melihat performa regional.
            </p>
          </div>
        )}

        {/* ── Empty regional data ───────────────────────────────────── */}
        {!loading && error === null && data !== null && data.regions.length === 0 && (
          <EmptyState
            message="Tidak ada data tersedia"
            hint={`Tidak ada data wilayah yang tersedia untuk campaign ${data.campaign_name || data.campaign_id}${flagProgram ? ` dengan program ${flagProgram}` : ''}. Coba ubah filter program atau pilih campaign lain.`}
          />
        )}

        {/* ── Results ───────────────────────────────────────────────── */}
        {!loading && error === null && data !== null && data.regions.length > 0 && (
          <>
            {/* Campaign name banner */}
            <div className="flex items-center gap-2.5 px-4 py-2.5 bg-[#005E6A]/10 border border-[#005E6A]/30 rounded-lg flex-wrap">
              <span className="text-xs font-semibold text-[#005E6A]">Campaign:</span>
              <span className="text-xs font-bold text-slate-700">
                {data.campaign_name || data.campaign_id}
              </span>
              {data.flag_program && (
                <span className="bg-emerald-100 text-emerald-700 border border-emerald-200 rounded px-2 py-0.5 text-xs font-semibold">
                  {data.flag_program}
                </span>
              )}
            </div>

            {/* Region performance table */}
            <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
                Performa per Wilayah{' '}
                <span className="text-gray-300 font-normal normal-case tracking-normal">
                  — klik baris untuk melihat tren 8 minggu
                </span>
              </h2>
              <div className="overflow-x-auto">
                <table
                  className="w-full text-xs"
                  aria-label="Tabel performa regional"
                  aria-describedby="region-table-desc"
                >
                  <caption id="region-table-desc" className="sr-only">
                    Tabel wilayah diurutkan berdasarkan Take Up Rate tertinggi.
                    Klik baris untuk melihat grafik tren 8 minggu.
                  </caption>
                  <thead>
                    <tr>
                      <th className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">Rank</th>
                      <th className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">Wilayah</th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">
                        Total Leads
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">
                        Total Take Up
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">
                        Take Up Rate
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap" scope="col">
                        Avg. Transaksi
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.regions.map((region, idx) => {
                      const isSelected = selectedRegion === region.wilayah;
                      const tdBase = isSelected
                        ? 'px-3 py-2.5 bg-[#005E6A]/10 border-b border-[#005E6A]/20 text-xs'
                        : idx % 2 === 0
                        ? 'px-3 py-2.5 bg-white border-b border-gray-100 text-xs'
                        : 'px-3 py-2.5 bg-slate-50 border-b border-gray-100 text-xs';

                      return (
                        <tr
                          key={region.wilayah}
                          className={`cursor-pointer hover:bg-slate-50 transition-colors${isSelected ? ' ring-2 ring-inset ring-[#005E6A]' : ''}`}
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
                          <td className={tdBase}>{idx + 1}</td>
                          <td className={tdBase}>
                            <span className="font-semibold text-slate-700">
                              {region.region_name}
                            </span>
                            <span className="text-slate-400 text-[10px]">
                              &nbsp;(W{region.wilayah})
                            </span>
                          </td>
                          <td className={`${tdBase} text-right`}>
                            {formatNumber(region.total_leads)}
                          </td>
                          <td className={`${tdBase} text-right`}>
                            {formatNumber(region.total_take_up)}
                          </td>
                          <td className={`${tdBase} text-right`}>
                            <span className={getTakeUpBadgeClasses(region.take_up_rate)}>
                              {formatRate(region.take_up_rate)}
                            </span>
                          </td>
                          <td className={`${tdBase} text-right`}>
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
              <div
                className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm"
                aria-live="polite"
                aria-atomic="true"
              >
                <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
                  Tren 8 Minggu —{' '}
                  <span className="text-[#005E6A]">
                    {selectedRegionMetric?.region_name ?? `Wilayah ${selectedRegion}`}
                  </span>
                </h2>

                {hasTrendData ? (
                  <div className="relative" style={{ height: '340px' }}>
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
                  <EmptyState
                    message="Tidak ada data tersedia"
                    hint="Data tren tidak tersedia untuk wilayah ini."
                  />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
};

export default RegionalPerformancePage;
