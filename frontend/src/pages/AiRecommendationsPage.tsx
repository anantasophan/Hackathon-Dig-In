import React, { useState } from 'react';
import axios from 'axios';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Loader2,
  TrendingUp,
  Target,
  Zap,
  BookOpen,
  BarChart2,
  MapPin,
  Clock,
  Radio,
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useAuth } from '../hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Recommendation {
  id: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  title: string;
  insight: string;
  action: string;
  expected_impact: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  data_source: string;
}

interface CampaignSummary {
  campaign_id: string;
  nama_program: string;
  flag_program: string;
  media_blasting: string;
  total_leads: number;
  total_take_up: number;
  take_up_rate: number;
  avg_days_to_take_up: number | null;
}

interface RecommendationResponse {
  model: string;
  campaign_summary: CampaignSummary;
  goal: string;
  goal_label: string;
  recommendations: Recommendation[];
  total_recommendations: number;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CAMPAIGN_OPTIONS = [
  { id: 'C001', label: 'C001 — Cashback QRIS Batch 1 2026' },
  { id: 'C002', label: 'C002 — Migrasi Biaya Admin Batch 1 2026' },
  { id: 'C003', label: 'C003 — Digisales QRIS Nasabah Mass' },
  { id: 'C004', label: 'C004 — WA Blast Biaya Admin Emerald' },
  { id: 'C005', label: 'C005 — Email QRIS Nasabah Affluent' },
  { id: 'C006', label: 'C006 — Cashback QRIS 2026' },
  { id: 'C007', label: 'C007 — E-Wallet / Billpayment 2026' },
  { id: 'C008', label: 'C008 — Tapenas Emas 2026' },
  { id: 'C009', label: 'C009 — Lifegoals Balrun Payroll Jan 2026' },
];

const GOAL_OPTIONS = [
  {
    id: 'maximize_take_up_rate',
    label: 'Maksimalkan Take Up Rate',
    icon: TrendingUp,
    desc: 'Dapatkan rekomendasi untuk meningkatkan persentase konversi leads',
  },
  {
    id: 'reduce_time_to_take_up',
    label: 'Percepat Waktu Take Up',
    icon: Clock,
    desc: 'Optimalkan timing campaign agar nasabah lebih cepat melakukan take up',
  },
  {
    id: 'expand_reach',
    label: 'Perluas Jangkauan',
    icon: Radio,
    desc: 'Eksplorasi channel dan segmen baru untuk menjangkau lebih banyak nasabah',
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const classes: Record<string, string> = {
    HIGH: 'bg-rose-100 text-rose-700 border border-rose-200',
    MEDIUM: 'bg-amber-100 text-amber-700 border border-amber-200',
    LOW: 'bg-slate-100 text-slate-600 border border-slate-200',
  };
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${classes[priority] ?? classes.LOW}`}>
      {priority}
    </span>
  );
};

const ConfidenceBadge: React.FC<{ confidence: string }> = ({ confidence }) => {
  const classes: Record<string, string> = {
    HIGH: 'text-emerald-600',
    MEDIUM: 'text-amber-600',
    LOW: 'text-slate-400',
  };
  const dots = confidence === 'HIGH' ? 3 : confidence === 'MEDIUM' ? 2 : 1;
  return (
    <span className={`text-xs font-medium flex items-center gap-1 ${classes[confidence] ?? classes.LOW}`}>
      {'●'.repeat(dots)}{'○'.repeat(3 - dots)} Confidence {confidence}
    </span>
  );
};

const CategoryIcon: React.FC<{ category: string }> = ({ category }) => {
  if (category.includes('Segmen')) return <Target className="w-4 h-4 text-[#005E6A]" />;
  if (category.includes('Regional')) return <MapPin className="w-4 h-4 text-[#005E6A]" />;
  if (category.includes('Waktu')) return <Clock className="w-4 h-4 text-[#005E6A]" />;
  if (category.includes('Channel')) return <Radio className="w-4 h-4 text-[#005E6A]" />;
  if (category.includes('Pembelajaran')) return <BookOpen className="w-4 h-4 text-[#005E6A]" />;
  if (category.includes('Data')) return <BarChart2 className="w-4 h-4 text-[#005E6A]" />;
  return <Zap className="w-4 h-4 text-[#005E6A]" />;
};

const RecommendationCard: React.FC<{ rec: Recommendation; index: number }> = ({ rec, index }) => {
  const [expanded, setExpanded] = useState(index === 0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-shrink-0 mt-0.5 w-7 h-7 rounded-full bg-[#005E6A]/10 flex items-center justify-center">
          <CategoryIcon category={rec.category} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <PriorityBadge priority={rec.priority} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{rec.category}</span>
          </div>
          <p className="text-xs font-semibold text-slate-700 leading-snug">{rec.title}</p>
        </div>
        <div className="flex-shrink-0 mt-1">
          {expanded
            ? <ChevronUp className="w-4 h-4 text-gray-400" />
            : <ChevronDown className="w-4 h-4 text-gray-400" />
          }
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
          {/* Insight */}
          <div className="pt-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">Insight</p>
            <p className="text-xs text-slate-600 leading-relaxed">{rec.insight}</p>
          </div>

          {/* Action */}
          <div className="bg-[#005E6A]/5 border border-[#005E6A]/20 rounded-lg p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#005E6A] mb-1">Rekomendasi Tindakan</p>
            <p className="text-xs text-slate-700 leading-relaxed">{rec.action}</p>
          </div>

          {/* Impact & Confidence row */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-0.5">Estimasi Dampak</p>
              <p className="text-xs font-semibold text-emerald-700">{rec.expected_impact}</p>
            </div>
            <ConfidenceBadge confidence={rec.confidence} />
          </div>

          {/* Data source */}
          <p className="text-[10px] text-gray-400 italic">{rec.data_source}</p>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

const AiRecommendationsPage: React.FC = () => {
  const { user, signOut } = useAuth();
  const [selectedCampaign, setSelectedCampaign] = useState('C001');
  const [selectedGoal, setSelectedGoal] = useState('maximize_take_up_rate');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_BASE_URL ?? 'http://localhost:8000'}/api/ai/recommendations`,
        { campaign_id: selectedCampaign, goal: selectedGoal }
      );
      setResult(response.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Terjadi kesalahan saat menghubungi AI engine';
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError?.response?.data?.detail ?? message);
    } finally {
      setLoading(false);
    }
  };

  const summary = result?.campaign_summary;

  return (
    <DashboardLayout username={user?.username} onSignOut={signOut}>
    <div className="flex flex-col gap-4">

      {/* Config panel */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-[#005E6A]" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-600">
            Konfigurasi AI Recommendation
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Campaign selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1.5">
              Campaign
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-[#005E6A] focus:outline-none"
              value={selectedCampaign}
              onChange={(e) => setSelectedCampaign(e.target.value)}
            >
              {CAMPAIGN_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Goal selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1.5">
              Tujuan Optimasi
            </label>
            <div className="space-y-1.5">
              {GOAL_OPTIONS.map((goal) => {
                const Icon = goal.icon;
                const active = selectedGoal === goal.id;
                return (
                  <button
                    key={goal.id}
                    onClick={() => setSelectedGoal(goal.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border text-left transition-colors ${
                      active
                        ? 'border-[#005E6A] bg-[#005E6A]/5 text-[#005E6A]'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    <div>
                      <p className={`text-xs font-semibold ${active ? 'text-[#005E6A]' : 'text-slate-700'}`}>
                        {goal.label}
                      </p>
                      <p className="text-[10px] text-gray-400 leading-tight">{goal.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold transition-colors ${
              loading
                ? 'bg-[#005E6A]/60 text-white cursor-not-allowed'
                : 'bg-[#005E6A] hover:bg-[#004852] text-white'
            }`}
          >
            {loading
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Menganalisis data...</>
              : <><Sparkles className="w-4 h-4" /> Generate Rekomendasi AI</>
            }
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Campaign summary bar */}
          {summary && (
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                Analisis Campaign
              </p>
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="text-sm font-bold text-slate-700">{summary.nama_program}</span>
                <span className="text-[10px] bg-[#005E6A]/10 border border-[#005E6A]/30 text-[#005E6A] rounded px-1.5 py-0.5 font-medium">
                  {summary.flag_program}
                </span>
                <span className="text-[10px] bg-slate-100 border border-slate-200 text-slate-600 rounded px-1.5 py-0.5 font-medium uppercase">
                  via {summary.media_blasting}
                </span>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: 'Total Leads', value: summary.total_leads.toLocaleString() },
                  { label: 'Total Take Up', value: summary.total_take_up.toLocaleString() },
                  { label: 'Take Up Rate', value: `${summary.take_up_rate.toFixed(1)}%` },
                  { label: 'Rata-rata Hari', value: summary.avg_days_to_take_up ? `${summary.avg_days_to_take_up} hari` : '-' },
                ].map((stat) => (
                  <div key={stat.label} className="bg-slate-50 rounded-lg p-2.5">
                    <p className="text-[10px] text-slate-400 font-medium mb-0.5">{stat.label}</p>
                    <p className="text-sm font-bold text-slate-700">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations list */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold uppercase tracking-wider text-gray-400">
                {result.total_recommendations} Rekomendasi — {result.goal_label}
              </p>
              <span className="text-[10px] text-gray-400 font-mono bg-slate-100 rounded px-1.5 py-0.5">
                {result.model}
              </span>
            </div>

            <div className="space-y-2">
              {result.recommendations.map((rec, i) => (
                <RecommendationCard key={rec.id} rec={rec} index={i} />
              ))}
            </div>

            {/* Disclaimer */}
            <p className="mt-3 text-[10px] text-gray-400 italic text-center">
              {result.disclaimer}
            </p>
          </div>
        </>
      )}

      {/* Empty initial state */}
      {!result && !loading && !error && (
        <div className="text-center py-16 text-gray-400">
          <Sparkles className="w-10 h-10 mx-auto mb-3 text-gray-300" />
          <p className="text-sm font-medium">Pilih campaign dan tujuan, lalu klik Generate</p>
          <p className="text-xs mt-1">AI akan menganalisis data historis dan memberikan 3 rekomendasi konkret</p>
        </div>
      )}
    </div>
    </DashboardLayout>
  );
};

export default AiRecommendationsPage;
