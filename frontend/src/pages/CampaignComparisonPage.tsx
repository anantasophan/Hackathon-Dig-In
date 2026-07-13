/**
 * CampaignComparisonPage — side-by-side campaign comparison dashboard.
 *
 * Allows the user to select 2–5 campaign IDs and compare them across
 * five key metrics: Total Leads, Total Take Up, Take-Up Rate,
 * Nilai Transaksi, and Durasi (hari).  Results are displayed in both
 * a comparison table and a grouped bar chart.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11
 */

import React, { useState, useCallback, useRef } from 'react';
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
import { EmptyState, LoadingState, ErrorState } from '../components/StateComponents';
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
      <div className="p-6 max-w-[1200px]">
        {/* ── Campaign ID input card ────────────────────────────────────── */}
        <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm mb-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Pilih Campaign (2–5 campaign)
          </h2>

          {/* Input row */}
          <div className="flex items-center gap-2 flex-wrap">
            <label
              htmlFor="campaign-id-input"
              className="text-xs font-bold uppercase tracking-wider text-gray-600"
            >
              Campaign ID:
            </label>
            <input
              id="campaign-id-input"
              ref={inputRef}
              type="text"
              className="w-56 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
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
              className={
                canAdd
                  ? 'px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
                  : 'px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
              }
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
              <p className="text-rose-600 text-xs mt-1">
                Maksimal 5 campaign dapat dipilih.
              </p>
            )}
            {duplicateError && (
              <p className="text-rose-600 text-xs mt-1">
                Campaign ID ini sudah ditambahkan.
              </p>
            )}
            {emptyError && (
              <p className="text-rose-600 text-xs mt-1">
                Masukkan Campaign ID terlebih dahulu.
              </p>
            )}
          </div>

          {/* Selected campaign chips */}
          {selectedIds.length > 0 && (
            <div
              className="flex flex-wrap gap-2 mt-3"
              role="list"
              aria-label="Campaign terpilih"
            >
              {selectedIds.map((id) => (
                <span
                  key={id}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] rounded-full text-xs font-medium"
                  role="listitem"
                >
                  {id}
                  <button
                    type="button"
                    className="hover:text-rose-600 transition-colors"
                    onClick={() => handleRemoveCampaign(id)}
                    aria-label={`Hapus campaign ${id}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* ── Group-by & Compare controls ───────────────────────────────── */}
        <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <label
              htmlFor="group-by-select"
              className="text-xs font-bold uppercase tracking-wider text-gray-600"
            >
              Kelompokkan berdasarkan:
            </label>
            <select
              id="group-by-select"
              className="px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none"
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
              className={
                canCompare
                  ? 'px-6 py-2.5 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
                  : 'px-6 py-2.5 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
              }
              onClick={handleCompare}
              disabled={!canCompare || isLoading}
              aria-disabled={!canCompare || isLoading}
            >
              {isLoading ? 'Memuat' : 'Bandingkan'}
            </button>

            {!canCompare && (
              <span className="text-xs text-gray-400">
                Pilih minimal 2 campaign untuk membandingkan.
              </span>
            )}
          </div>
        </div>

        {/* ── Loading state ─────────────────────────────────────────────── */}
        {isLoading && (
          <LoadingState />
        )}

        {/* ── Error state ───────────────────────────────────────────────── */}
        {apiError && !isLoading && (
          <ErrorState message={apiError} />
        )}

        {/* ── Empty / idle state ────────────────────────────────────────── */}
        {!isLoading && !apiError && result === null && (
          <EmptyState
            message="Tidak ada data tersedia"
            hint="Pilih 2–5 campaign dan tekan Bandingkan untuk melihat hasil perbandingan."
          />
        )}

        {/* ── Results ───────────────────────────────────────────────────── */}
        {!isLoading && result !== null && (
          <>
            {/* Comparison table */}
            <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
                Tabel Perbandingan
              </h2>
              <div className="overflow-x-auto">
                <table
                  className="w-full border-collapse text-xs"
                  aria-label="Tabel perbandingan campaign"
                >
                  <thead>
                    <tr>
                      <th className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Campaign ID
                      </th>
                      <th className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Nama Campaign
                      </th>
                      <th className="px-3 py-2.5 text-left bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Flag Program
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Total Leads
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Total Take Up
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Take-Up Rate (%)
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Nilai Transaksi (Rp)
                      </th>
                      <th className="px-3 py-2.5 text-right bg-slate-900 text-white text-xs font-semibold whitespace-nowrap">
                        Durasi (hari)
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.campaigns.map((c, idx) => {
                      const tdBase =
                        idx % 2 === 0
                          ? 'px-3 py-2.5 bg-white border-b border-gray-100 text-xs'
                          : 'px-3 py-2.5 bg-slate-50 border-b border-gray-100 text-xs';
                      return (
                        <tr key={c.campaign_id}>
                          <td className={tdBase}>{c.campaign_id}</td>
                          <td className={tdBase}>{c.campaign_name}</td>
                          <td className={tdBase}>{c.flag_program}</td>
                          <td className={`${tdBase} text-right`}>
                            {formatNumber(c.total_leads)}
                          </td>
                          <td className={`${tdBase} text-right`}>
                            {formatNumber(c.total_take_up)}
                          </td>
                          <td className={`${tdBase} text-right`}>
                            {formatPercent(c.take_up_rate)}
                          </td>
                          <td className={`${tdBase} text-right`}>
                            {formatCurrency(c.total_transaction_value)}
                          </td>
                          <td className={`${tdBase} text-right`}>
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
            <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm mb-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
                Grafik Perbandingan
              </h2>
              {/* Chart.js requires explicit pixel height — inline style exception */}
              <div className="relative" style={{ height: '420px' }}>
                <Bar
                  data={buildChartData(result.campaigns)}
                  options={chartOptions}
                  aria-label="Grafik perbandingan metrik campaign"
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">
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
