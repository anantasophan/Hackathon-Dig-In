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
import DashboardLayout from '../components/DashboardLayout';
import { api } from '../services/api';
import type { TimeAnalysisResponse } from '../types/api';
import './TimeToTakeUpPage.css';

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
  icon: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div className="ttu-stat-card" role="region" aria-label={label}>
    <span className="ttu-stat-card__icon" aria-hidden="true">
      {icon}
    </span>
    <span className="ttu-stat-card__label">{label}</span>
    <span className="ttu-stat-card__value">{value}</span>
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
      {/* Keyframe for spinner */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div className="ttu-page">
        {/* ── Page header ─────────────────────────────────────────────── */}
        <h1 className="ttu-page__title">Time to Take Up</h1>

        {/* ── Input card ──────────────────────────────────────────────── */}
        <div className="ttu-card">
          <h2 className="ttu-card__heading">Parameter Analisis</h2>

          {/* Campaign ID row */}
          <div className="ttu-input-row">
            <label htmlFor="ttu-campaign-id" className="ttu-label">
              Campaign ID <span className="ttu-required" aria-hidden="true">*</span>
            </label>
            <input
              id="ttu-campaign-id"
              type="text"
              className="ttu-input"
              placeholder="Masukkan Campaign ID"
              value={campaignId}
              onChange={(e) => setcampaignId(e.target.value)}
              onKeyDown={handleKeyDown}
              aria-required="true"
            />
          </div>

          {/* Filters row */}
          <div className="ttu-filters-row">
            {/* Channel filter */}
            <div className="ttu-filter-group">
              <label htmlFor="ttu-channel" className="ttu-label">
                Channel (opsional)
              </label>
              <select
                id="ttu-channel"
                className="ttu-select"
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
            <div className="ttu-filter-group">
              <label htmlFor="ttu-region" className="ttu-label">
                Wilayah / Region (opsional)
              </label>
              <input
                id="ttu-region"
                type="text"
                className="ttu-input ttu-input--short"
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
          <div className="ttu-action-row">
            <button
              type="button"
              className={`ttu-btn-primary${campaignId.trim() === '' ? ' ttu-btn-primary--disabled' : ''}`}
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
          <div className="ttu-state-box ttu-state-box--info" role="status">
            <span className="ttu-state-box__icon" aria-hidden="true">📊</span>
            <p className="ttu-state-box__text">
              Masukkan campaign ID untuk melihat analisis
            </p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="ttu-state-box" role="status" aria-busy="true" aria-label="Memuat data">
            <div className="ttu-spinner" />
            <p className="ttu-state-box__text">Memuat data analisis…</p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="ttu-state-box ttu-state-box--error" role="alert">
            <span className="ttu-state-box__icon" aria-hidden="true">⚠️</span>
            <p className="ttu-state-box__text ttu-state-box__text--error">{error}</p>
            <p className="ttu-state-box__sub">Silakan periksa Campaign ID atau coba lagi.</p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && emptyMessage && (
          <div className="ttu-state-box" role="status">
            <span className="ttu-state-box__icon" aria-hidden="true">📭</span>
            <p className="ttu-state-box__text">{emptyMessage}</p>
          </div>
        )}

        {/* Data state */}
        {!loading && !error && data && (
          <>
            {/* Campaign name subtitle */}
            {data.campaign_name && (
              <p className="ttu-campaign-name">
                Kampanye: <strong>{data.campaign_name}</strong>
              </p>
            )}

            {/* Stat cards */}
            <div className="ttu-stats-row" role="list" aria-label="Statistik waktu take up">
              <StatCard
                label="Median"
                value={`${data.stats.median_days} hari`}
                icon="📊"
              />
              <StatCard
                label="Rata-rata"
                value={`${data.stats.mean_days.toFixed(1)} hari`}
                icon="📈"
              />
              <StatCard
                label="Minimum"
                value={`${data.stats.min_days} hari`}
                icon="⬇️"
              />
              <StatCard
                label="Maksimum"
                value={`${data.stats.max_days} hari`}
                icon="⬆️"
              />
              <StatCard
                label="Total Take Up"
                value={`${data.stats.total_take_up.toLocaleString('id-ID')} nasabah`}
                icon="✅"
              />
            </div>

            {/* Histogram */}
            <div className="ttu-card">
              <h2 className="ttu-card__heading">Distribusi Waktu Take Up</h2>
              <div className="ttu-chart-container" aria-label="Histogram distribusi waktu take up">
                <Bar data={buildChartData(data)} options={chartOptions} />
              </div>
              <p className="ttu-chart-note">
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
