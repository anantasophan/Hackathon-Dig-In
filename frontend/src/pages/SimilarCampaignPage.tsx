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
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8
 */

import React, { useState, useCallback } from 'react';
import {
  Search,
  SearchX,
  BarChart2,
  GitCompareArrows,
  Star,
  Info,
  TrendingUp,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { LoadingState, ErrorState } from '../components/StateComponents';
import { api } from '../services/api';
import type {
  SimilarCampaignResponse,
  SimilarCampaignResult,
} from '../types/api';
import { useAuth } from '../hooks/useAuth';

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
 * Requirements: 10.1 — dimension filter checkboxes
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
      className={
        isSelected
          ? 'bg-white p-4 border-2 border-[#005E6A] rounded-xl shadow-md cursor-pointer'
          : 'bg-white p-4 border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow cursor-pointer'
      }
      onClick={handleClick}
      onKeyDown={handleKey}
      tabIndex={0}
      role="button"
      aria-pressed={isSelected}
      aria-label={`Pilih campaign ${campaign.campaign_name}`}
    >
      {/* Campaign name + ID */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-xs font-bold text-slate-700 truncate-2-lines">
          {campaign.campaign_name}
        </span>
        <span className="text-[10px] text-slate-400 flex-shrink-0">
          {campaign.campaign_id}
        </span>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-2 gap-2 mt-2">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">
            Dimensi Cocok
          </span>
          <span className="text-sm font-bold text-slate-700">
            {campaign.dimension_count}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">
            Skor Kesamaan
          </span>
          <span className="text-sm font-bold text-[#005E6A]">
            {fmtScore(campaign.similarity_score)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">
            Take-Up Rate
          </span>
          <span className="text-sm font-bold text-slate-700">
            {fmtPct(campaign.take_up_rate)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">
            Total Leads
          </span>
          <span className="text-sm font-bold text-slate-700">
            {fmtNum(campaign.total_leads)}
          </span>
        </div>
      </div>

      {/* Similarity score badge */}
      <div className="flex flex-wrap gap-1 mt-2">
        <span className="bg-[#005E6A]/20 border border-[#005E6A] text-[#005E6A] text-xs font-semibold rounded px-1.5 py-0.5">
          {fmtScore(campaign.similarity_score)}
        </span>

        {/* Matching dimension badges */}
        {campaign.matching_dimensions.map((dim) => (
          <span
            key={dim}
            className="bg-[#005E6A]/10 border border-[#005E6A]/40 text-[#005E6A] text-[10px] font-medium rounded px-1.5 py-0.5"
          >
            {dim}
          </span>
        ))}
      </div>
    </article>
  );
};

// ── Sub-component: side-by-side detail view ───────────────────────────────

interface ComparisonViewProps {
  campaign: SimilarCampaignResult;
}

const ComparisonView: React.FC<ComparisonViewProps> = ({ campaign }) => (
  <section
    className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 flex flex-col gap-4"
    aria-label="Detail campaign terpilih"
  >
    <h2 className="text-xs font-bold text-slate-700">
      Detail Campaign:{' '}
      <span className="text-[#005E6A]">{campaign.campaign_name}</span>
    </h2>

    {/* Section 1 — Core metrics */}
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
        <BarChart2 className="w-3.5 h-3.5" />
        Metrik Utama
      </h3>
      <dl className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center text-xs">
          <dt className="text-slate-500">Total Leads</dt>
          <dd className="font-semibold text-slate-700">{fmtNum(campaign.total_leads)}</dd>
        </div>
        <div className="flex justify-between items-center text-xs">
          <dt className="text-slate-500">Total Take Up</dt>
          <dd className="font-semibold text-slate-700">{fmtNum(campaign.total_take_up)}</dd>
        </div>
        <div className="flex justify-between items-center text-xs">
          <dt className="text-slate-500">Take-Up Rate</dt>
          <dd className="font-semibold text-slate-700">{fmtPct(campaign.take_up_rate)}</dd>
        </div>
        {campaign.total_leads > 0 &&
          typeof (campaign as SimilarCampaignResult & { total_transaction_value?: number })
            .total_transaction_value === 'number' && (
            <div className="flex justify-between items-center text-xs">
              <dt className="text-slate-500">Nilai Transaksi</dt>
              <dd className="font-semibold text-slate-700">
                {fmtCurrency(
                  (campaign as SimilarCampaignResult & { total_transaction_value?: number })
                    .total_transaction_value ?? 0,
                )}
              </dd>
            </div>
          )}
      </dl>
    </div>

    {/* Section 2 — Matching dimensions */}
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
        <GitCompareArrows className="w-3.5 h-3.5" />
        Dimensi yang Cocok
      </h3>
      <div className="flex flex-wrap gap-1">
        {campaign.matching_dimensions.length > 0 ? (
          campaign.matching_dimensions.map((dim) => (
            <span
              key={dim}
              className="bg-[#005E6A]/10 border border-[#005E6A]/40 text-[#005E6A] text-[10px] font-medium rounded px-1.5 py-0.5"
            >
              {dim}
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-400">Tidak ada dimensi yang cocok.</span>
        )}
      </div>
    </div>

    {/* Section 3 — Dimension count & similarity score */}
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
        <Star className="w-3.5 h-3.5" />
        Skor Kesamaan
      </h3>
      <dl className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center text-xs">
          <dt className="text-slate-500">Jumlah Dimensi Cocok</dt>
          <dd className="font-semibold text-slate-700">{campaign.dimension_count}</dd>
        </div>
        <div className="flex justify-between items-center text-xs">
          <dt className="text-slate-500">Skor Kesamaan</dt>
          <dd className="font-semibold text-[#005E6A]">{fmtScore(campaign.similarity_score)}</dd>
        </div>
      </dl>
    </div>

    {/* Section 4 — Advanced data note */}
    <div className="flex flex-col gap-2 bg-slate-50 border border-gray-200 rounded-lg p-3">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
        <Info className="w-3.5 h-3.5" />
        Data Lanjutan
      </h3>
      <p className="text-xs text-slate-500">
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
      <div className="flex flex-col gap-4">

        {/* ── Search form card ─────────────────────────────────────── */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 flex flex-col gap-4">
          {/* Reference ID row */}
          <div className="flex flex-wrap items-center gap-2">
            <label
              htmlFor="sc-ref-input"
              className="text-xs font-bold uppercase tracking-wider text-gray-600 flex-shrink-0"
            >
              Campaign Referensi ID:
            </label>
            <input
              id="sc-ref-input"
              type="text"
              className="flex-1 min-w-[200px] px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#005E6A] bg-white text-xs"
              placeholder="Masukkan Campaign ID referensi"
              value={referenceId}
              onChange={(e) => setReferenceId(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              aria-label="Campaign ID referensi"
            />
            <button
              type="button"
              className={
                canSearch
                  ? 'flex items-center gap-2 px-4 py-2 bg-[#005E6A] hover:bg-[#004852] text-white font-semibold rounded-lg text-xs transition-colors'
                  : 'flex items-center gap-2 px-4 py-2 bg-gray-300 text-gray-500 font-semibold rounded-lg text-xs cursor-not-allowed'
              }
              onClick={handleSearch}
              disabled={!canSearch}
              aria-label="Cari campaign serupa"
            >
              <Search className="w-3.5 h-3.5" />
              {loading ? 'Mencari' : 'Cari Campaign Serupa'}
            </button>
          </div>

          {/* Dimension checkboxes */}
          <fieldset className="space-y-2">
            <legend className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">
              Dimensi Kesamaan:
            </legend>
            <div className="flex flex-wrap gap-4">
              {DIMENSION_OPTIONS.map(({ value, label }) => (
                <label key={value} className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-[#005E6A] focus:ring-[#005E6A]"
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
          <LoadingState text="Mencari" />
        )}

        {/* ── Error state ──────────────────────────────────────────── */}
        {!loading && error && (
          <ErrorState message={error} />
        )}

        {/* ── No results state ─────────────────────────────────────── */}
        {!loading && !error && data !== null && isNoResults && (
          <div className="text-center py-12 text-gray-400" role="status">
            <SearchX className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm font-medium">Tidak Ditemukan</p>
            <p className="text-xs mt-1">
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
                className="bg-white border border-gray-200 rounded-xl shadow-sm p-4"
                role="note"
                aria-label="Learning summary"
              >
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5 mb-3">
                  <TrendingUp className="w-3.5 h-3.5" />
                  Learning Summary dari Campaign Teratas
                </h3>
                <ul className="flex flex-col gap-1.5 text-xs text-slate-600">
                  <li>
                    Take Up Rate:{' '}
                    <strong className="text-slate-700">
                      {data.learning_summary.take_up_rate_formatted}
                    </strong>
                  </li>
                  <li>
                    Segmen Teratas:{' '}
                    <strong className="text-slate-700">
                      {data.learning_summary.top_segment}
                    </strong>
                  </li>
                  <li>
                    Wilayah Teratas:{' '}
                    <strong className="text-slate-700">
                      {data.learning_summary.top_region}
                    </strong>
                  </li>
                </ul>
              </div>
            )}

            {/* Results count */}
            <p className="text-xs text-slate-500">
              Ditemukan{' '}
              <strong className="text-slate-700">{campaigns.length}</strong>{' '}
              campaign serupa (diurutkan berdasarkan jumlah dimensi yang cocok)
            </p>

            {/* Results layout: list + detail side-by-side */}
            <div className="flex gap-4 items-start">
              {/* Campaign card list */}
              <div
                className="flex flex-col gap-3 flex-1 min-w-0"
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
                <div className="w-80 flex-shrink-0 sticky top-4">
                  <ComparisonView campaign={selectedCampaign} />
                </div>
              )}
            </div>

            {/* Hint when nothing is selected yet */}
            {!selectedCampaign && (
              <p className="text-xs text-slate-400 text-center">
                Klik salah satu campaign di atas untuk melihat detail
                perbandingan.
              </p>
            )}
          </>
        )}

        {/* ── Initial / idle state ─────────────────────────────────── */}
        {!loading && !error && data === null && (
          <div className="text-center py-12 text-gray-400" role="status">
            <Search className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm font-medium">Cari Campaign Serupa</p>
            <p className="text-xs mt-1">
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
