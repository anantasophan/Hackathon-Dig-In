/**
 * CampaignOverviewPage — Campaign Overview dashboard page.
 *
 * Displays aggregate metrics (total leads, total take-up, take-up rate),
 * a time-series trend line chart, and a filter panel.  Integrates with
 * the FilterPanel component and refreshes data on every filter change.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import DashboardLayout from '../components/DashboardLayout';
import FilterPanel from '../components/FilterPanel';
import { api, ApiTimeoutError } from '../services/api';
import { FilterState } from '../types/filters';
import type { CampaignOverviewResponse, CampaignOverviewRequest, TrendDataPoint } from '../types/api';
import { useAuth } from '../hooks/useAuth';
import './CampaignOverviewPage.css';

// ── Chart.js registration ────────────────────────────────────────────────

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

// ── Helpers ──────────────────────────────────────────────────────────────

/** Map FilterState → CampaignOverviewRequest params. */
function filterStateToRequest(filters: FilterState): CampaignOverviewRequest {
  return {
    start_date: filters.dateRange.startDate,
    end_date: filters.dateRange.endDate,
    flag_program:
      filters.flagProgram.length > 0 ? filters.flagProgram : undefined,
    media_blasting:
      filters.mediaBlasting.length > 0 ? filters.mediaBlasting : undefined,
    wilayah: filters.wilayah.length > 0 ? filters.wilayah : undefined,
    jenis_leads:
      filters.jenisCleads.length > 0 ? filters.jenisCleads : undefined,
  };
}

/** Format a number with thousand-separator (comma). */
function formatNumber(n: number): string {
  return n.toLocaleString('id-ID');
}

/** Format a take-up rate to 2 decimal places. */
function formatRate(n: number): string {
  return `${n.toFixed(2)}%`;
}

// ── Sub-components ────────────────────────────────────────────────────────

interface MetricCardProps {
  label: string;
  value: string;
  icon: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon }) => (
  <div className="overview-metric-card" role="region" aria-label={label}>
    <div className="overview-metric-card__icon" aria-hidden="true">
      {icon}
    </div>
    <div className="overview-metric-card__label">{label}</div>
    <div className="overview-metric-card__value">{value}</div>
  </div>
);

const LoadingSpinner: React.FC = () => (
  <div className="overview-state overview-state--loading" aria-busy="true" aria-label="Memuat data">
    <div className="overview-spinner" role="status" />
    <p className="overview-state__text">Memuat data…</p>
  </div>
);

// ── Chart helpers ─────────────────────────────────────────────────────────

function buildChartData(trend: TrendDataPoint[]) {
  return {
    labels: trend.map((p) => p.period_start),
    datasets: [
      {
        label: 'Take-Up Rate (%)',
        data: trend.map((p) => p.take_up_rate),
        borderColor: '#2b6cb0',
        backgroundColor: 'rgba(43, 108, 176, 0.08)',
        borderWidth: 2,
        pointBackgroundColor: '#2b6cb0',
        pointRadius: 4,
        tension: 0.3,
        fill: true,
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
      text: 'Tren Take-Up Rate',
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
        maxTicksLimit: 10,
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

// ── Main component ────────────────────────────────────────────────────────

const CampaignOverviewPage: React.FC = () => {
  const { user, signOut } = useAuth();

  const [data, setData] = useState<CampaignOverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);
  /** Milliseconds the last successful request took (for ≤5 s indicator). */
  const [responseMs, setResponseMs] = useState<number | null>(null);

  // ── Fetch ────────────────────────────────────────────────────────────

  const fetchOverview = useCallback(async (filters: FilterState) => {
    setLoading(true);
    setError(null);
    setEmptyMessage(null);
    setResponseMs(null);

    const params = filterStateToRequest(filters);
    const t0 = performance.now();

    try {
      const response = await api.getCampaignOverview(params);
      const elapsed = performance.now() - t0;
      setResponseMs(elapsed);

      // Backend may return a message field when no data matches filters.
      const maybeEmpty = response as CampaignOverviewResponse & {
        message?: string;
      };
      if (maybeEmpty.message) {
        setEmptyMessage(maybeEmpty.message);
        setData(null);
      } else {
        setData(response);
        setEmptyMessage(null);
      }
    } catch (err: unknown) {
      setData(null);
      if (err instanceof ApiTimeoutError) {
        setError(
          'Query membutuhkan waktu terlalu lama. Coba persempit filter atau coba kembali.',
        );
      } else {
        const msg =
          err instanceof Error
            ? err.message
            : 'Terjadi kesalahan jaringan. Periksa koneksi internet dan coba lagi.';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Initial load with default filters ────────────────────────────────

  useEffect(() => {
    const today = new Date();
    const threeMonthsAgo = new Date(today);
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

    const defaultFilters: FilterState = {
      dateRange: {
        startDate: threeMonthsAgo.toISOString().slice(0, 10),
        endDate: today.toISOString().slice(0, 10),
      },
      flagProgram: [],
      jenisCleads: [],
      mediaBlasting: [],
      wilayah: [],
    };

    fetchOverview(defaultFilters);
  }, [fetchOverview]);

  // ── Derived ───────────────────────────────────────────────────────────

  const isEmpty = emptyMessage !== null && data === null && !loading && !error;

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <DashboardLayout username={user?.username} onSignOut={signOut}>
      <div className="overview-page">
        {/* ── Page header ────────────────────────────────────────────── */}
        <div className="overview-page__header">
          <h1 className="overview-page__title">Campaign Overview</h1>
          {responseMs !== null && (
            <span
              className={
                responseMs < 5000
                  ? 'overview-response-badge overview-response-badge--good'
                  : 'overview-response-badge overview-response-badge--slow'
              }
              aria-live="polite"
              title={`Response time: ${(responseMs / 1000).toFixed(2)}s`}
            >
              {responseMs < 5000
                ? `✓ <5s`
                : `⚠ ${(responseMs / 1000).toFixed(1)}s`}
            </span>
          )}
        </div>

        {/* ── Body: filter sidebar + main content ────────────────────── */}
        <div className="overview-page__content">
          {/* Filter sidebar */}
          <aside className="overview-page__filter">
            <FilterPanel onFilterChange={fetchOverview} />
          </aside>

          {/* Main content */}
          <section
            className="overview-page__main"
            aria-label="Overview metrics and chart"
          >
            {/* ── Loading state ───────────────────────────────────── */}
            {loading && <LoadingSpinner />}

            {/* ── Error state ─────────────────────────────────────── */}
            {!loading && error && (
              <div className="overview-state overview-state--error" role="alert">
                <span className="overview-state__icon" aria-hidden="true">
                  ⚠️
                </span>
                <p className="overview-state__message">{error}</p>
                <p className="overview-state__hint">
                  Silakan coba lagi atau ubah filter.
                </p>
              </div>
            )}

            {/* ── Empty state ─────────────────────────────────────── */}
            {isEmpty && (
              <div className="overview-state overview-state--empty" role="status">
                <span className="overview-state__icon" aria-hidden="true">
                  📭
                </span>
                <p className="overview-state__title">Tidak ada data yang cocok</p>
                <p className="overview-state__hint">
                  {emptyMessage ??
                    'Tidak ada kampanye yang sesuai dengan filter yang dipilih. Coba ubah rentang tanggal atau filter lainnya.'}
                </p>
              </div>
            )}

            {/* ── Data state ──────────────────────────────────────── */}
            {!loading && !error && !isEmpty && data && (
              <>
                {/* Metric cards — 3 cards side by side */}
                <div
                  className="overview-metrics"
                  role="list"
                  aria-label="Metrik ringkasan"
                >
                  <MetricCard
                    label="Total Leads"
                    value={formatNumber(data.total_leads)}
                    icon="👥"
                  />
                  <MetricCard
                    label="Total Take Up"
                    value={formatNumber(data.total_take_up)}
                    icon="✅"
                  />
                  <MetricCard
                    label="Take Up Rate"
                    value={formatRate(data.take_up_rate)}
                    icon="📈"
                  />
                </div>

                {/* Trend line chart */}
                {data.trend.length > 0 ? (
                  <div
                    className="overview-chart"
                    aria-label="Grafik tren take-up rate"
                  >
                    <Line
                      data={buildChartData(data.trend)}
                      options={chartOptions}
                    />
                  </div>
                ) : (
                  <div className="overview-chart-empty">
                    <p className="overview-state__hint">
                      Tidak ada data tren untuk periode yang dipilih.
                    </p>
                  </div>
                )}

                {/* Active filters summary */}
                {data.filters.length > 0 && (
                  <div
                    className="overview-filter-summary"
                    aria-label="Filter aktif"
                  >
                    <span className="overview-filter-summary__label">
                      Filter aktif:{' '}
                    </span>
                    {data.filters.map((f) => (
                      <span key={f.field} className="overview-filter-tag">
                        {f.field}: {f.values.join(', ')}
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default CampaignOverviewPage;
