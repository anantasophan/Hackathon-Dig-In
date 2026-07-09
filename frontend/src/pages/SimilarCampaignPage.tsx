/**
 * SimilarCampaignPage — Campaign Serupa dashboard page.
 *
 * Allows the user to enter a reference campaign ID, select similarity
 * dimensions, and view campaigns that match those dimensions.  Results
 * are shown in a sortable card list (max 20, sorted by dimension_count
 * DESC).  Clicking a card opens a side-by-side detail comparison view.
 * A learning summary box is shown at the top of the results when the
 * API returns `learning_summary` data.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 */

import React, { useState, useCallback } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import { api } from '../services/api';
import type {
  SimilarCampaignResponse,
  SimilarCampaignResult,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';
import './SimilarCampaignPage.css';

// ── Local types ───────────────────────────────────────────────────────────

interface LearningSum {
  take_up_rate_formatted: string;
  top_segment: string;
  top_region: string;
}

/**
 * Extends the base API response to carry the optional learning summary
 * that the backend may return alongside similar campaign results.
 */
type SimilarCampaignData = SimilarCampaignResponse & {
  learning_summary?: LearningSum;
  message?: string;
};

// ── Constants ─────────────────────────────────────────────────────────────

/**
 * The three valid dimensions for similarity matching.
 * Requirements: 6.1 — dimension filter checkboxes
 */
const DIMENSION_OPTIONS: Array<{
  value: 'flag_program' | 'media_blasting' | 'jenis_leads';
  label: string;
}> = [
  { value: 'flag_program', label: 'Jenis Program (flag_program)' },
  { value: 'media_blasting', label: 'Channel (media_blasting)' },
  { value: 'jenis_leads', label: 'Jenis Leads (jenis_leads)' },
];

// ── Helpers ───────────────────────────────────────────────────────────────

/** Format a 0–100 percentage with 2 decimal places. */
function fmtPct(n: number): string {
  return `${n.toFixed(2)}%`;
}

/** Format a 0–1 similarity score as a percentage. */
function fmtScore(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

/** Format integer with Indonesian thousand separator. */
function fmtNum(n: number): string {
  return n.toLocaleString('id-ID');
}

/** Format optional currency (IDR). */
function fmtCurrency(n: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(n);
}

// ── Sub-component: campaign result card ───────────────────────────────────

interface CampaignCardProps {
  campaign: SimilarCampaignResult;
  isSelected: boolean;
  onClick: (c: SimilarCampaignResult) => void;
}

const CampaignCard: React.FC<CampaignCardProps> = ({
  campaign,
  isSelected,
  onClick,
}) => {
  const handleClick = useCallback(() => onClick(campaign), [campaign, onClick]);
  const handleKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick(campaign);
      }
    },
    [campaign, onClick],
  );

  return (
    <article
      className={`sc-card${isSelected ? ' sc-card--selected' : ''}`}
      onClick={handleClick}
      onKeyDown={handleKey}
      tabIndex={0}
      role="button"
      aria-pressed={isSelected}
      aria-label={`Pilih campaign ${campaign.campaign_name}`}
    >
      {/* Campaign name + ID */}
      <div className="sc-card__header">
        <span className="sc-card__name">{campaign.campaign_name}</span>
        <span className="sc-card__id">{campaign.campaign_id}</span>
      </div>

      {/* Key metrics row */}
      <div className="sc-card__metrics">
        <div className="sc-card__metric">
          <span className="sc-card__metric-label">Dimensi Cocok</span>
          <span className="sc-card__metric-value sc-card__metric-value--bold">
            {campaign.dimension_count}
          </span>
        </div>
        <div className="sc-card__metric">
          <span className="sc-card__metric-label">Skor Kesamaan</span>
          <span className="sc-card__metric-value sc-card__metric-value--score">
            {fmtScore(campaign.similarity_score)}
          </span>
        </div>
        <div className="sc-card__metric">
          <span className="sc-card__metric-label">Take-Up Rate</span>
          <span className="sc-card__metric-value">
            {fmtPct(campaign.take_up_rate)}
          </span>
        </div>
        <div className="sc-card__metric">
          <span className="sc-card__metric-label">Total Leads</span>
          <span className="sc-card__metric-value">{fmtNum(campaign.total_leads)}</span>
        </div>
      </div>

      {/* Matching dimension badges */}
      {campaign.matching_dimensions.length > 0 && (
        <div className="sc-card__badges" aria-label="Dimensi yang cocok">
          {campaign.matching_dimensions.map((dim) => (
            <span key={dim} className="sc-badge">
              {dim}
            </span>
          ))}
        </div>
      )}
    </article>
  );
};

// ── Sub-component: side-by-side detail view ───────────────────────────────

interface ComparisonViewProps {
  campaign: SimilarCampaignResult;
}

const ComparisonView: React.FC<ComparisonViewProps> = ({ campaign }) => (
  <section className="sc-comparison" aria-label="Detail campaign terpilih">
    <h2 className="sc-comparison__title">
      Detail Campaign:{' '}
      <span className="sc-comparison__campaign-name">{campaign.campaign_name}</span>
    </h2>

    {/* Section 1 — Core metrics */}
    <div className="sc-comparison__section">
      <h3 className="sc-comparison__section-title">📊 Metrik Utama</h3>
      <dl className="sc-comparison__dl">
        <div className="sc-comparison__row">
          <dt>Total Leads</dt>
          <dd>{fmtNum(campaign.total_leads)}</dd>
        </div>
        <div className="sc-comparison__row">
          <dt>Total Take Up</dt>
          <dd>{fmtNum(campaign.total_take_up)}</dd>
        </div>
        <div className="sc-comparison__row">
          <dt>Take-Up Rate</dt>
          <dd>{fmtPct(campaign.take_up_rate)}</dd>
        </div>
        {campaign.total_leads > 0 && (
          /* total_transaction_value is an optional field — show only if non-zero */
          <div className="sc-comparison__row">
            <dt>Nilai Transaksi</dt>
            <dd>
              {typeof (campaign as SimilarCampaignResult & { total_transaction_value?: number })
                .total_transaction_value === 'number'
                ? fmtCurrency(
                    (campaign as SimilarCampaignResult & { total_transaction_value?: number })
                      .total_transaction_value ?? 0,
                  )
                : '—'}
            </dd>
          </div>
        )}
      </dl>
    </div>

    {/* Section 2 — Matching dimensions */}
    <div className="sc-comparison__section">
      <h3 className="sc-comparison__section-title">🔗 Dimensi yang Cocok</h3>
      <div className="sc-comparison__badges">
        {campaign.matching_dimensions.length > 0 ? (
          campaign.matching_dimensions.map((dim) => (
            <span key={dim} className="sc-badge sc-badge--large">
              {dim}
            </span>
          ))
        ) : (
          <span className="sc-comparison__empty">Tidak ada dimensi yang cocok.</span>
        )}
      </div>
    </div>

    {/* Section 3 — Dimension count & similarity score */}
    <div className="sc-comparison__section">
      <h3 className="sc-comparison__section-title">📐 Skor Kesamaan</h3>
      <dl className="sc-comparison__dl">
        <div className="sc-comparison__row">
          <dt>Jumlah Dimensi Cocok</dt>
          <dd>{campaign.dimension_count}</dd>
        </div>
        <div className="sc-comparison__row">
          <dt>Skor Kesamaan</dt>
          <dd>{fmtScore(campaign.similarity_score)}</dd>
        </div>
      </dl>
    </div>

    {/* Section 4 — Customer / regional / time note (post-MVP) */}
    <div className="sc-comparison__section sc-comparison__section--note">
      <h3 className="sc-comparison__section-title">ℹ️ Data Lanjutan</h3>
      <p className="sc-comparison__note">
        Data detail segmen/regional/waktu memerlukan query lanjutan ke Athena
        (post-MVP)
      </p>
    </div>
  </section>
);

// ── Main component ────────────────────────────────────────────────────────

const SimilarCampaignPage: React.FC = () => {
  const { user, signOut } = useAuth();

  // ── State ─────────────────────────────────────────────────────────────

  const [referenceId, setReferenceId] = useState('');
  const [dimensions, setDimensions] = useState<
    Array<'media_blasting' | 'jenis_leads' | 'flag_program'>
  >(['flag_program', 'media_blasting']);
  const [data, setData] = useState<SimilarCampaignData | null>(null);
  const [selectedCampaign, setSelectedCampaign] =
    useState<SimilarCampaignResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleDimensionChange = useCallback(
    (value: 'media_blasting' | 'jenis_leads' | 'flag_program') => {
      setDimensions((prev) =>
        prev.includes(value)
          ? prev.filter((d) => d !== value)
          : [...prev, value],
      );
    },
    [],
  );

  const handleSearch = useCallback(async () => {
    const trimmed = referenceId.trim();
    if (!trimmed || dimensions.length === 0) return;

    setLoading(true);
    setError(null);
    setData(null);
    setSelectedCampaign(null);

    try {
      const response = await api.getSimilarCampaigns({
        reference_campaign_id: trimmed,
        dimensions,
        limit: 20,
      });

      setData(response as SimilarCampaignData);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Terjadi kesalahan saat memuat data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [referenceId, dimensions]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSearch();
      }
    },
    [handleSearch],
  );

  const handleSelectCampaign = useCallback(
    (campaign: SimilarCampaignResult) => {
      setSelectedCampaign((prev) =>
        prev?.campaign_id === campaign.campaign_id ? null : campaign,
      );
    },
    [],
  );

  // ── Derived ───────────────────────────────────────────────────────────

  const canSearch =
    referenceId.trim().length > 0 && dimensions.length > 0 && !loading;

  const isNoResults =
    data !== null &&
    (data.similar_campaigns.length === 0 ||
      (typeof data.message === 'string' &&
        data.message.includes('Tidak ada campaign serupa')));

  const campaigns = data?.similar_campaigns ?? [];

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <DashboardLayout username={user?.username} onSignOut={signOut}>
      {/* Spinner keyframe — injected once */}
      <style>{`@keyframes sc-spin { to { transform: rotate(360deg); } }`}</style>

      <div className="sc-page">
        {/* ── Page header ─────────────────────────────────────────── */}
        <h1 className="sc-page__title">Campaign Serupa</h1>

        {/* ── Search form card ─────────────────────────────────────── */}
        <div className="sc-form-card">
          {/* Reference ID row */}
          <div className="sc-form-row">
            <label htmlFor="sc-ref-input" className="sc-form-label">
              Campaign Referensi ID:
            </label>
            <input
              id="sc-ref-input"
              type="text"
              className="sc-input"
              placeholder="Masukkan Campaign ID referensi"
              value={referenceId}
              onChange={(e) => setReferenceId(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              aria-label="Campaign ID referensi"
            />
            <button
              type="button"
              className="sc-btn-primary"
              onClick={handleSearch}
              disabled={!canSearch}
              aria-label="Cari campaign serupa"
            >
              {loading ? 'Mencari…' : 'Cari Campaign Serupa'}
            </button>
          </div>

          {/* Dimension checkboxes */}
          <fieldset className="sc-fieldset">
            <legend className="sc-fieldset__legend">
              Dimensi Kesamaan:
            </legend>
            <div className="sc-checkbox-group">
              {DIMENSION_OPTIONS.map(({ value, label }) => (
                <label key={value} className="sc-checkbox-label">
                  <input
                    type="checkbox"
                    className="sc-checkbox"
                    checked={dimensions.includes(value)}
                    onChange={() => handleDimensionChange(value)}
                    disabled={loading}
                    aria-label={label}
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        {/* ── Loading state ────────────────────────────────────────── */}
        {loading && (
          <div className="sc-state-box" aria-busy="true" aria-label="Mencari">
            <div className="sc-spinner" role="status" />
            <p className="sc-state-box__text">Mencari campaign serupa…</p>
          </div>
        )}

        {/* ── Error state ──────────────────────────────────────────── */}
        {!loading && error && (
          <div className="sc-state-box sc-state-box--error" role="alert">
            <span className="sc-state-box__icon" aria-hidden="true">⚠️</span>
            <p className="sc-state-box__title">Gagal Memuat Data</p>
            <p className="sc-state-box__text">{error}</p>
          </div>
        )}

        {/* ── No results state ─────────────────────────────────────── */}
        {!loading && !error && data !== null && isNoResults && (
          <div className="sc-state-box" role="status">
            <span className="sc-state-box__icon" aria-hidden="true">🔍</span>
            <p className="sc-state-box__title">Tidak Ditemukan</p>
            <p className="sc-state-box__text">
              Tidak ada campaign serupa ditemukan. Coba perluas dimensi
              pencarian.
            </p>
          </div>
        )}

        {/* ── Results ──────────────────────────────────────────────── */}
        {!loading && !error && data !== null && !isNoResults && (
          <>
            {/* Learning summary box */}
            {data.learning_summary && (
              <div
                className="sc-learning-summary"
                role="note"
                aria-label="Learning summary"
              >
                <p className="sc-learning-summary__heading">
                  🏆 Learning Summary dari Campaign Teratas:
                </p>
                <ul className="sc-learning-summary__list">
                  <li>
                    Take Up Rate:{' '}
                    <strong>
                      {data.learning_summary.take_up_rate_formatted}
                    </strong>
                  </li>
                  <li>
                    Segmen Teratas:{' '}
                    <strong>{data.learning_summary.top_segment}</strong>
                  </li>
                  <li>
                    Wilayah Teratas:{' '}
                    <strong>{data.learning_summary.top_region}</strong>
                  </li>
                </ul>
              </div>
            )}

            {/* Results count */}
            <p className="sc-results-count">
              Ditemukan{' '}
              <strong>{campaigns.length}</strong> campaign serupa
              (diurutkan berdasarkan jumlah dimensi yang cocok)
            </p>

            {/* Results layout: list + detail side-by-side */}
            <div className="sc-results-layout">
              {/* Campaign card list */}
              <div
                className="sc-card-list"
                role="list"
                aria-label="Daftar campaign serupa"
              >
                {campaigns.map((campaign) => (
                  <div key={campaign.campaign_id} role="listitem">
                    <CampaignCard
                      campaign={campaign}
                      isSelected={
                        selectedCampaign?.campaign_id === campaign.campaign_id
                      }
                      onClick={handleSelectCampaign}
                    />
                  </div>
                ))}
              </div>

              {/* Side-by-side detail pane */}
              {selectedCampaign && (
                <div className="sc-detail-pane">
                  <ComparisonView campaign={selectedCampaign} />
                </div>
              )}
            </div>

            {/* Hint when nothing is selected yet */}
            {!selectedCampaign && (
              <p className="sc-hint">
                Klik salah satu campaign di atas untuk melihat detail
                perbandingan.
              </p>
            )}
          </>
        )}

        {/* ── Initial / idle state ─────────────────────────────────── */}
        {!loading && !error && data === null && (
          <div className="sc-state-box" role="status">
            <span className="sc-state-box__icon" aria-hidden="true">🔍</span>
            <p className="sc-state-box__title">Cari Campaign Serupa</p>
            <p className="sc-state-box__text">
              Masukkan Campaign ID referensi, pilih dimensi kesamaan, lalu
              tekan <strong>Cari Campaign Serupa</strong>.
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default SimilarCampaignPage;
