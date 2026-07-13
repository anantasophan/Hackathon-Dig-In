/**
 * CustomerCriteriaPage — Kriteria Nasabah dashboard page.
 *
 * Shows demographic (segment, age group, domicile region) and financial
 * (product holding, balance category) distribution charts for a given
 * campaign.  Each attribute is rendered as a horizontal bar chart with
 * overall percentage distribution and per-group take-up rate in the
 * tooltip.  Unavailable attributes are shown as grayed-out cards.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8
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
import {
  Users,
  Filter,
  AlertCircle,
  Info,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { EmptyState, LoadingState, ErrorState } from '../components/StateComponents';
import { api } from '../services/api';
import type {
  CustomerCriteriaResponse,
  AttributeDistribution,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';

// ── Chart.js registration ─────────────────────────────────────────────────

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// ── Constants ─────────────────────────────────────────────────────────────

/**
 * Human-readable labels for each customer attribute key.
 * Requirements: 9.1 (demographic), 9.2 (financial)
 */
const ATTR_LABELS: Record<string, string> = {
  customer_segment: 'Segmen Nasabah',
  age_group: 'Kelompok Usia',
  domicile_region: 'Wilayah Domisili',
  product_holding: 'Produk yang Dimiliki',
  balance_category: 'Kategori Saldo',
};

/** Bar color for overall distribution. */
const BAR_COLOR = 'rgba(0, 94, 106, 0.75)';
const BAR_BORDER_COLOR = 'rgba(0, 72, 82, 1)';

// ── Helpers ───────────────────────────────────────────────────────────────

/** Return human-readable attribute label (fallback: title-case the key). */
function humanizeAttr(attribute: string): string {
  if (attribute in ATTR_LABELS) {
    return ATTR_LABELS[attribute];
  }
  return attribute.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format a percentage to 2 decimal places with % suffix. */
function fmtPct(n: number): string {
  return `${n.toFixed(2)}%`;
}

/** Format a number with Indonesian thousand separator. */
function fmtNum(n: number): string {
  return n.toLocaleString('id-ID');
}

/**
 * Whether a distribution has many labels (domicile_region tends to have
 * many values — use a taller chart so labels don't overlap).
 */
function isTall(dist: AttributeDistribution): boolean {
  return dist.items.length > 6;
}

// ── Sub-component: horizontal bar chart for one distribution ──────────────

interface DistributionChartProps {
  dist: AttributeDistribution;
}

const DistributionChart: React.FC<DistributionChartProps> = ({ dist }) => {
  const labels = dist.items.map((item) => item.label);

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Distribusi (%)',
        data: dist.items.map((item) => item.percentage),
        backgroundColor: BAR_COLOR,
        borderColor: BAR_BORDER_COLOR,
        borderWidth: 1,
      },
    ],
  };

  const options = {
    indexAxis: 'y' as const,           // horizontal bar chart (Req 9.3)
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          /**
           * Tooltip shows count, percentage, take_up_count, take_up_percentage
           * per group (Req 9.4).
           */
          label: (ctx: { dataIndex: number }) => {
            const item = dist.items[ctx.dataIndex];
            if (!item) return '';
            return [
              `  Jumlah: ${fmtNum(item.count)}`,
              `  Distribusi: ${fmtPct(item.percentage)}`,
              `  Take Up: ${fmtNum(item.take_up_count)}`,
              `  Take-Up Rate: ${fmtPct(item.take_up_percentage)}`,
            ];
          },
          title: (items: Array<{ label: string }>) => items[0]?.label ?? '',
        },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: string | number) => `${value}%`,
          color: '#4a5568',
        },
        grid: { color: '#edf2f7' },
      },
      y: {
        ticks: {
          color: '#4a5568',
          font: { size: 12 },
        },
        grid: { display: false },
      },
    },
  };

  const tall = isTall(dist);

  return (
    <div
      className="relative"
      style={{ height: tall ? '340px' : '240px' }}
      aria-label={`Grafik distribusi ${humanizeAttr(dist.attribute)}`}
    >
      <Bar data={chartData} options={options} />
    </div>
  );
};

// ── Sub-component: one distribution card ─────────────────────────────────

interface DistributionCardProps {
  dist: AttributeDistribution;
}

const DistributionCard: React.FC<DistributionCardProps> = ({ dist }) => {
  const title = humanizeAttr(dist.attribute);

  if (!dist.available) {
    // Grayed-out card with unavailable reason (Req 9.5)
    return (
      <article
        className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden opacity-60"
        aria-label={`${title} — tidak tersedia`}
      >
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
            {title}
          </h3>
        </div>
        <div className="p-4">
          <p className="flex items-center gap-2 text-xs text-gray-500">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            {dist.unavailable_reason ??
              `Data atribut '${dist.attribute}' tidak tersedia untuk campaign ini.`}
          </p>
        </div>
      </article>
    );
  }

  return (
    <article
      className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
      aria-label={`Distribusi ${title}`}
    >
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
          {title}
        </h3>
      </div>
      <div className="p-4">
        <DistributionChart dist={dist} />
      </div>
    </article>
  );
};

// ── Main component ────────────────────────────────────────────────────────

const CustomerCriteriaPage: React.FC = () => {
  const { user, signOut } = useAuth();

  const [campaignId, setCampaignId] = useState('');
  const [data, setData] = useState<CustomerCriteriaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Fetch ─────────────────────────────────────────────────────────────

  const handleFetch = useCallback(async () => {
    const trimmed = campaignId.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await api.getCustomerCriteria(trimmed);
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
  }, [campaignId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleFetch();
      }
    },
    [handleFetch],
  );

  // ── Derived ───────────────────────────────────────────────────────────

  const canFetch = campaignId.trim().length > 0 && !loading;

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <DashboardLayout username={user?.username} onSignOut={signOut}>
      <div className="flex flex-col gap-4">

        {/* ── Campaign ID input card ─────────────────────────────────── */}
        <div
          className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
          role="search"
        >
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#005E6A]" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400">
              Filter Campaign
            </h2>
          </div>
          <div className="p-4 flex flex-wrap items-center gap-3">
            <label
              htmlFor="cc-campaign-input"
              className="text-xs font-bold uppercase tracking-wider text-gray-600 whitespace-nowrap"
            >
              Campaign ID
            </label>
            <input
              id="cc-campaign-input"
              type="text"
              placeholder="Masukkan Campaign ID"
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              onKeyDown={handleKeyDown}
              aria-label="Campaign ID"
              disabled={loading}
              className="w-64 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs disabled:opacity-50"
            />
            <button
              type="button"
              onClick={handleFetch}
              disabled={!canFetch}
              aria-label="Lihat kriteria nasabah"
              className={
                canFetch
                  ? 'flex items-center gap-2 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
                  : 'flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
              }
            >
              <Users className="w-4 h-4" />
              {loading ? 'Memuat' : 'Lihat Kriteria'}
            </button>
          </div>
        </div>

        {/* ── Loading state ─────────────────────────────────────────── */}
        {loading && (
          <div
            className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
            aria-busy="true"
            aria-label="Memuat data"
          >
            <LoadingState />
          </div>
        )}

        {/* ── Error state ───────────────────────────────────────────── */}
        {!loading && error && (
          <div
            className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
            role="alert"
          >
            <ErrorState message={error} />
          </div>
        )}

        {/* ── Data state ────────────────────────────────────────────── */}
        {!loading && !error && data && (
          <>
            {/* Campaign name (if provided by backend) */}
            {data.campaign_name && (
              <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-4 py-3 flex items-center gap-3 flex-wrap">
                  <Users className="w-4 h-4 text-[#005E6A] flex-shrink-0" />
                  <span className="text-xs font-bold text-slate-700">
                    {data.campaign_name}
                  </span>
                  <span className="text-xs text-gray-400">
                    ({data.campaign_id})
                  </span>
                </div>
              </div>
            )}

            {/* Partial data banner (Req 9.5) */}
            {data.partial_data_message && (
              <div
                className="flex items-start gap-2 bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3 text-xs text-slate-600"
                role="note"
                aria-label="Informasi data parsial"
              >
                <Info className="w-4 h-4 text-[#005E6A] flex-shrink-0 mt-0.5" />
                <span>{data.partial_data_message}</span>
              </div>
            )}

            {/* Distribution charts grid */}
            {data.distributions && data.distributions.length > 0 ? (
              <div
                className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(420px,1fr))]"
                aria-label="Distribusi karakteristik nasabah"
              >
                {data.distributions.map((dist) => (
                  <DistributionCard key={dist.attribute} dist={dist} />
                ))}
              </div>
            ) : (
              <div
                className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
                role="status"
              >
                <EmptyState />
              </div>
            )}
          </>
        )}

        {/* ── Initial prompt ────────────────────────────────────────── */}
        {!loading && !error && !data && (
          <div
            className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden"
            role="status"
          >
            <EmptyState
              message="Lihat Kriteria Nasabah"
              hint="Masukkan Campaign ID di atas, lalu tekan Lihat Kriteria untuk melihat distribusi demografis dan finansial nasabah."
            />
          </div>
        )}

      </div>
    </DashboardLayout>
  );
};

export default CustomerCriteriaPage;
