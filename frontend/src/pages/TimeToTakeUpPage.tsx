/**
 * TimeToTakeUpPage — Time to Take Up analysis dashboard page.
 *
 * Displays a histogram of the time-to-take-up distribution for a given
 * campaign, plus descriptive statistics (median, mean, min, max, total
 * take-up).  Supports optional channel and region filters.
 *
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
 */

import React, { useState, useCallback } from 'react';
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
import { Clock, Timer, TrendingDown, TrendingUp, Users } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { EmptyState, LoadingState, ErrorState } from '../components/StateComponents';
import { api } from '../services/api';
import type { TimeAnalysisResponse } from '../types/api';

// ---------------------------------------------------------------------------
// Chart.js registration
// ---------------------------------------------------------------------------

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CHANNEL_OPTIONS = ['wa', 'digisales', 'telesales', 'email', 'push notif', 'sms'];

/** Human-readable histogram bucket labels in the same order the API returns. */
const BUCKET_LABELS = [
  '0-7 hari',
  '7-14 hari',
  '14-21 hari',
  '21-30 hari',
  '30-60 hari',
  '60-90 hari',
  '90+ hari',
];

// ---------------------------------------------------------------------------
// Chart helpers
// ---------------------------------------------------------------------------

// Store counts separately for tooltip access
const _histogramCounts: number[] = [];

function buildChartData(data: TimeAnalysisResponse) {
  const percentages = data.histogram.map((b) => b.percentage);
  // Populate the module-level array so the tooltip callback can access it
  _histogramCounts.splice(0, _histogramCounts.length, ...data.histogram.map((b) => b.count));

  return {
    labels: BUCKET_LABELS.slice(0, data.histogram.length),
    datasets: [
      {
        label: 'Persentase Take Up (%)',
        data: percentages,
        backgroundColor: '#2b6cb0',
        borderColor: '#1a365d',
        borderWidth: 1,
      },
    ],
  };
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' as const },
    title: {
      display: true,
      text: 'Distribusi Waktu Take Up',
      font: { size: 14 },
      color: '#1a365d',
    },
    tooltip: {
      callbacks: {
        label: (ctx: { parsed: { y: number }; dataIndex: number }) => {
          const pct = ctx.parsed.y.toFixed(1);
          const count = _histogramCounts[ctx.dataIndex];
          return count !== undefined
            ? [`${pct}%`, `Jumlah: ${count} nasabah`]
            : `${pct}%`;
        },
      },
    },
  },
  scales: {
    x: {
      ticks: { color: '#4a5568' },
      grid: { color: '#edf2f7' },
    },
    y: {
      beginAtZero: true,
      max: 100,
      ticks: {
        callback: (value: string | number) => `${value}%`,
        color: '#4a5568',
      },
      grid: { color: '#edf2f7' },
    },
  },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3">
    <div className="flex-shrink-0 text-[#005E6A]">{icon}</div>
    <div>
      <span className="text-xs font-medium text-slate-400 block">{label}</span>
      <span className="text-2xl font-bold text-slate-700">{value}</span>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const TimeToTakeUpPage: React.FC = () => {
  // ── State ─────────────────────────────────────────────────────────────────

  const [campaignId, setcampaignId] = useState('');
  const [channel, setChannel] = useState('');
  const [region, setRegion] = useState('');
  const [data, setData] = useState<TimeAnalysisResponse | null>(null);
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Derived: has the user ever triggered a fetch?
  const [hasFetched, setHasFetched] = useState(false);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleFetch = useCallback(async () => {
    const trimmedId = campaignId.trim();
    if (trimmedId === '') return;

    setLoading(true);
    setError(null);
    setData(null);
    setEmptyMessage(null);
    setHasFetched(true);

    try {
      const response = await api.getTimeAnalysis(
        trimmedId,
        channel !== '' ? channel : undefined,
        region !== '' ? region : undefined,
      );

      // Backend may return a `message` field when no data matches
      const maybeEmpty = response as TimeAnalysisResponse & { message?: string };
      if (maybeEmpty.message) {
        setEmptyMessage(maybeEmpty.message);
      } else if (!response.histogram || response.histogram.length === 0) {
        setEmptyMessage('Tidak ada data take up untuk filter tersebut');
      } else {
        setData(response);
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Terjadi kesalahan saat memuat data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [campaignId, channel, region]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        void handleFetch();
      }
    },
    [handleFetch],
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-4">
        {/* ── Page header ─────────────────────────────────────────────── */}
        <h1 className="text-md font-bold text-gray-700">Time to Take Up</h1>

        {/* ── Input card ──────────────────────────────────────────────── */}
        <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Parameter Analisis</h2>

          {/* Campaign ID row */}
          <div className="flex flex-col gap-1">
            <label htmlFor="ttu-campaign-id" className="text-xs font-bold uppercase tracking-wider text-gray-600">
              Campaign ID <span className="text-rose-500" aria-hidden="true">*</span>
            </label>
            <input
              id="ttu-campaign-id"
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
              placeholder="Masukkan Campaign ID"
              value={campaignId}
              onChange={(e) => setcampaignId(e.target.value)}
              onKeyDown={handleKeyDown}
              aria-required="true"
            />
          </div>

          {/* Filters row */}
          <div className="flex gap-4 flex-wrap mt-3">
            {/* Channel filter */}
            <div className="flex flex-col gap-1">
              <label htmlFor="ttu-channel" className="text-xs font-bold uppercase tracking-wider text-gray-600">
                Channel (opsional)
              </label>
              <select
                id="ttu-channel"
                className="px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                aria-label="Filter channel"
              >
                <option value="">Semua channel</option>
                {CHANNEL_OPTIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Region filter */}
            <div className="flex flex-col gap-1">
              <label htmlFor="ttu-region" className="text-xs font-bold uppercase tracking-wider text-gray-600">
                Wilayah / Region (opsional)
              </label>
              <input
                id="ttu-region"
                type="text"
                className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
                placeholder="1–17"
                value={region}
                onChange={(e) => {
                  // Allow only digits 0-9 or empty
                  const val = e.target.value;
                  if (val === '' || /^\d{1,2}$/.test(val)) {
                    setRegion(val);
                  }
                }}
                aria-label="Filter wilayah (1-17)"
                inputMode="numeric"
                maxLength={2}
              />
            </div>
          </div>

          {/* Action button */}
          <div className="mt-4">
            <button
              type="button"
              className={campaignId.trim() === '' || loading
                ? 'px-5 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
                : 'px-5 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
              }
              onClick={() => void handleFetch()}
              disabled={campaignId.trim() === '' || loading}
              aria-disabled={campaignId.trim() === '' || loading}
            >
              {loading ? 'Memuat…' : 'Lihat Analisis'}
            </button>
          </div>
        </div>

        {/* ── Result area ─────────────────────────────────────────────── */}

        {/* Pre-fetch prompt */}
        {!hasFetched && !loading && (
          <div className="text-center py-12 text-gray-400" role="status">
            <Clock className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm font-medium">Masukkan campaign ID untuk melihat analisis</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <LoadingState />
        )}

        {/* Error */}
        {!loading && error && (
          <ErrorState message={error} />
        )}

        {/* Empty state */}
        {!loading && !error && emptyMessage && (
          <EmptyState message={emptyMessage} />
        )}

        {/* Data state */}
        {!loading && !error && data && (
          <>
            {/* Campaign name subtitle */}
            {data.campaign_name && (
              <p className="text-sm text-gray-600">
                Kampanye: <strong>{data.campaign_name}</strong>
              </p>
            )}

            {/* Stat cards */}
            <div className="grid grid-cols-2 gap-4" role="list" aria-label="Statistik waktu take up">
              <StatCard
                label="Median"
                value={`${data.stats.median_days} hari`}
                icon={<Timer className="w-5 h-5" />}
              />
              <StatCard
                label="Rata-rata"
                value={`${data.stats.mean_days.toFixed(1)} hari`}
                icon={<Clock className="w-5 h-5" />}
              />
              <StatCard
                label="Minimum"
                value={`${data.stats.min_days} hari`}
                icon={<TrendingDown className="w-5 h-5" />}
              />
              <StatCard
                label="Maksimum"
                value={`${data.stats.max_days} hari`}
                icon={<TrendingUp className="w-5 h-5" />}
              />
              <StatCard
                label="Total Take Up"
                value={`${data.stats.total_take_up.toLocaleString('id-ID')} nasabah`}
                icon={<Users className="w-5 h-5" />}
              />
            </div>

            {/* Histogram */}
            <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Distribusi Waktu Take Up</h2>
              <div style={{ height: '320px' }} aria-label="Histogram distribusi waktu take up">
                <Bar data={buildChartData(data)} options={chartOptions} />
              </div>
              <p className="text-[10px] text-gray-400 mt-2">
                * Sumbu Y menunjukkan persentase nasabah yang melakukan take up dalam rentang waktu tersebut.
                Hover pada bar untuk melihat jumlah nasabah.
              </p>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
};

export default TimeToTakeUpPage;
