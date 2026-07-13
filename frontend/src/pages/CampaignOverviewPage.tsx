/**
 * CampaignOverviewPage — Campaign Overview dashboard page.
 *
 * Displays aggregate metrics (total leads, total take-up, take-up rate),
 * a time-series trend line chart, and a filter panel. Integrates with
 * the FilterPanel component and refreshes data on every filter change.
 *
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11
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
import {
  Users,
  TrendingUp,
  BarChart2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import FilterPanel from '../components/FilterPanel';
import { EmptyState, LoadingState, ErrorState } from '../components/StateComponents';
import { api, ApiTimeoutError } from '../services/api';
import { FilterState } from '../types/filters';
import type { CampaignOverviewResponse, CampaignOverviewRequest, TrendDataPoint } from '../types/api';
import { useAuth } from '../hooks/useAuth';

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

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon }) => (
  <div
    className="bg-white p-4 border border-gray-200 rounded-xl shadow-sm flex items-start gap-3"
    role="region"
    aria-label={label}
  >
    <div className="flex-shrink-0 text-[#005E6A]" aria-hidden="true">
      {icon}
    </div>
    <div>
      <span className="text-xs font-medium text-slate-400 block">{label}</span>
      <span className="text-2xl font-bold text-slate-700">{value}</span>
    </div>
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
      <div className="flex flex-col gap-4">
        {/* ── Page header ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <h1 className="text-md font-bold text-gray-700">Campaign Overview</h1>
          {responseMs !== null && (
            <span
              className={
                responseMs < 5000
                  ? 'inline-flex items-center gap-1 text-xs font-medium text-emerald-600'
                  : 'inline-flex items-center gap-1 text-xs font-medium text-amber-600'
              }
              aria-live="polite"
              title={`Response time: ${(responseMs / 1000).toFixed(2)}s`}
            >
              {responseMs < 5000 ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
                  Respons cepat
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
                  {`${(responseMs / 1000).toFixed(1)}s`}
                </>
              )}
            </span>
          )}
        </div>

        {/* ── Body: filter sidebar + main content ────────────────────── */}
        <div className="flex gap-4">
          {/* Filter sidebar */}
          <aside className="w-72 flex-shrink-0">
            <FilterPanel onFilterChange={fetchOverview} />
          </aside>

          {/* Main content */}
          <section
            className="flex-1 min-w-0 space-y-4"
            aria-label="Overview metrics and chart"
          >
            {/* ── Loading state ───────────────────────────────────── */}
            {loading && (
              <LoadingState />
            )}

            {/* ── Error state ─────────────────────────────────────── */}
            {!loading && error && (
              <ErrorState message={error} />
            )}

            {/* ── Empty state ─────────────────────────────────────── */}
            {isEmpty && (
              <EmptyState
                message="Tidak ada data yang cocok"
                hint={emptyMessage ?? 'Tidak ada kampanye yang sesuai dengan filter yang dipilih. Coba ubah rentang tanggal atau filter lainnya.'}
              />
            )}

            {/* ── Data state ──────────────────────────────────────── */}
            {!loading && !error && !isEmpty && data && (
              <>
                {/* Metric cards — 3 cards side by side */}
                <div
                  className="grid grid-cols-3 gap-4"
                  role="list"
                  aria-label="Metrik ringkasan"
                >
                  <StatCard
                    label="Total Leads"
                    value={formatNumber(data.total_leads)}
                    icon={<Users className="w-5 h-5" />}
                  />
                  <StatCard
                    label="Total Take Up"
                    value={formatNumber(data.total_take_up)}
                    icon={<TrendingUp className="w-5 h-5" />}
                  />
                  <StatCard
                    label="Take Up Rate"
                    value={formatRate(data.take_up_rate)}
                    icon={<BarChart2 className="w-5 h-5" />}
                  />
                </div>

                {/* Trend line chart */}
                {data.trend.length > 0 ? (
                  <div
                    className="bg-white border border-gray-200 rounded-xl shadow-sm p-4"
                    aria-label="Grafik tren take-up rate"
                  >
                    {/* Inline style is the sole permitted exception — Chart.js requires explicit height */}
                    <div style={{ height: '320px' }}>
                      <Line
                        data={buildChartData(data.trend)}
                        options={chartOptions}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4">
                    <p className="text-xs text-gray-500">
                      Tidak ada data tren untuk periode yang dipilih.
                    </p>
                  </div>
                )}

                {/* Active filters summary */}
                {data.filters.length > 0 && (
                  <div
                    className="flex flex-wrap items-center gap-2 text-xs text-gray-500"
                    aria-label="Filter aktif"
                  >
                    <span className="font-medium">Filter aktif:</span>
                    {data.filters.map((f) => (
                      <span
                        key={f.field}
                        className="bg-[#005E6A]/10 border border-[#005E6A]/30 text-[#005E6A] rounded px-2 py-0.5 text-xs font-medium"
                      >
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
