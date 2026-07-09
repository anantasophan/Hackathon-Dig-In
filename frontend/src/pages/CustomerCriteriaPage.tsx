/**
 * CustomerCriteriaPage — Kriteria Nasabah dashboard page.
 *
 * Shows demographic (segment, age group, domicile region) and financial
 * (product holding, balance category) distribution charts for a given
 * campaign.  Each attribute is rendered as a horizontal bar chart with
 * overall percentage distribution and per-group take-up rate in the
 * tooltip.  Unavailable attributes are shown as grayed-out cards.
 *
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
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
import type {
  CustomerCriteriaResponse,
  AttributeDistribution,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';
import './CustomerCriteriaPage.css';

// ── Chart.js registration ─────────────────────────────────────────────────

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// ── Constants ─────────────────────────────────────────────────────────────

/**
 * Human-readable labels for each customer attribute key.
 * Requirements: 5.1 (demographic), 5.2 (financial)
 */
const ATTR_LABELS: Record<string, string> = {
  customer_segment: 'Segmen Nasabah',
  age_group: 'Kelompok Usia',
  domicile_region: 'Wilayah Domisili',
  product_holding: 'Produk yang Dimiliki',
  balance_category: 'Kategori Saldo',
};

/** Bar color for overall distribution. */
const BAR_COLOR = 'rgba(49, 130, 206, 0.75)';
const BAR_BORDER_COLOR = 'rgba(26, 54, 93, 1)';

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
    indexAxis: 'y' as const,           // horizontal bar chart (Req 5.3)
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
           * per group (Req 5.4).
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
      className={
        tall
          ? 'cc-dist-card__chart-wrap cc-dist-card__chart-wrap--tall'
          : 'cc-dist-card__chart-wrap'
      }
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
    // Grayed-out card with unavailable reason (Req 5.5)
    return (
      <article
        className="cc-dist-card cc-dist-card--unavailable"
        aria-label={`${title} — tidak tersedia`}
      >
        <h3 className="cc-dist-card__title">{title}</h3>
        <p className="cc-dist-card__unavailable-msg">
          <span aria-hidden="true">⚠️</span>
          {dist.unavailable_reason ??
            `Data atribut '${dist.attribute}' tidak tersedia untuk campaign ini.`}
        </p>
      </article>
    );
  }

  return (
    <article className="cc-dist-card" aria-label={`Distribusi ${title}`}>
      <h3 className="cc-dist-card__title">{title}</h3>
      <DistributionChart dist={dist} />
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
      {/* Spinner keyframe injected once */}
      <style>{`@keyframes cc-spin { to { transform: rotate(360deg); } }`}</style>

      <div className="cc-page">
        {/* ── Page header ──────────────────────────────────────────── */}
        <h1 className="cc-page__title">Kriteria Nasabah</h1>

        {/* ── Campaign ID input ─────────────────────────────────────── */}
        <div className="cc-input-card" role="search">
          <label htmlFor="cc-campaign-input">Campaign ID:</label>
          <input
            id="cc-campaign-input"
            type="text"
            placeholder="Masukkan Campaign ID"
            value={campaignId}
            onChange={(e) => setCampaignId(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Campaign ID"
            disabled={loading}
          />
          <button
            type="button"
            className="cc-btn-primary"
            onClick={handleFetch}
            disabled={!canFetch}
            aria-label="Lihat kriteria nasabah"
          >
            {loading ? 'Memuat…' : 'Lihat Kriteria'}
          </button>
        </div>

        {/* ── Loading state ─────────────────────────────────────────── */}
        {loading && (
          <div
            className="cc-state-box"
            aria-busy="true"
            aria-label="Memuat data"
          >
            <div className="cc-spinner" role="status" />
            <p className="cc-state-box__text">Memuat data kriteria nasabah…</p>
          </div>
        )}

        {/* ── Error state ───────────────────────────────────────────── */}
        {!loading && error && (
          <div className="cc-state-box cc-state-box--error" role="alert">
            <span className="cc-state-box__icon" aria-hidden="true">
              ⚠️
            </span>
            <p className="cc-state-box__title">{error}</p>
            <p className="cc-state-box__text">
              Silakan periksa Campaign ID dan coba lagi.
            </p>
          </div>
        )}

        {/* ── Data state ────────────────────────────────────────────── */}
        {!loading && !error && data && (
          <>
            {/* Campaign name (if provided by backend) */}
            {data.campaign_name && (
              <h2 className="cc-campaign-heading">
                {data.campaign_name}
                <span
                  style={{ fontWeight: 400, color: '#718096', marginLeft: '0.5rem', fontSize: '0.9rem' }}
                >
                  ({data.campaign_id})
                </span>
              </h2>
            )}

            {/* Partial data banner (Req 5.5) */}
            {data.partial_data_message && (
              <div
                className="cc-banner-info"
                role="note"
                aria-label="Informasi data parsial"
              >
                <span className="cc-banner-info__icon" aria-hidden="true">
                  ℹ️
                </span>
                <span>{data.partial_data_message}</span>
              </div>
            )}

            {/* Distribution charts grid */}
            {data.distributions && data.distributions.length > 0 ? (
              <div
                className="cc-dist-grid"
                aria-label="Distribusi karakteristik nasabah"
              >
                {data.distributions.map((dist) => (
                  <DistributionCard key={dist.attribute} dist={dist} />
                ))}
              </div>
            ) : (
              <div className="cc-state-box" role="status">
                <span className="cc-state-box__icon" aria-hidden="true">
                  📭
                </span>
                <p className="cc-state-box__title">
                  Tidak ada data yang tersedia
                </p>
                <p className="cc-state-box__text">
                  Tidak ada data karakteristik nasabah untuk campaign ini.
                </p>
              </div>
            )}
          </>
        )}

        {/* ── Initial / empty prompt ────────────────────────────────── */}
        {!loading && !error && !data && (
          <div className="cc-state-box" role="status">
            <span className="cc-state-box__icon" aria-hidden="true">
              👥
            </span>
            <p className="cc-state-box__title">Lihat Kriteria Nasabah</p>
            <p className="cc-state-box__text">
              Masukkan Campaign ID di atas, lalu tekan{' '}
              <strong>Lihat Kriteria</strong> untuk melihat distribusi
              demografis dan finansial nasabah.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CustomerCriteriaPage;
