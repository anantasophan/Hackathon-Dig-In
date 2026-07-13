"""AI Recommendation router for the Local Development Server.

Simulates an Amazon Bedrock-powered campaign recommendation engine.
In production, this endpoint would call Bedrock's Claude/Titan model
with a structured prompt containing campaign performance data.

In local dev mode, recommendations are generated deterministically
from the mock data, producing realistic outputs that mirror what a
real LLM response would look like.

Requirements: AI.1 (future)
"""

from __future__ import annotations

import textwrap
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from local_server.mock_store import store
from shared.calculations import calculate_take_up_rate

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RecommendationRequest(BaseModel):
    """Request body for POST /api/ai/recommendations."""

    campaign_id: str
    goal: str = "maximize_take_up_rate"  # or: "reduce_time_to_take_up", "expand_reach"


# ---------------------------------------------------------------------------
# Simulated Bedrock prompt builder
# ---------------------------------------------------------------------------

def _build_prompt_context(campaign_id: str) -> dict[str, Any]:
    """Build a structured context dict that mirrors what would be sent
    as a prompt to Amazon Bedrock Claude.

    In production:
        prompt = f\"\"\"
        You are a marketing campaign analyst for BNI Bank.
        Given this campaign data: {context}
        Generate 3 specific, actionable recommendations to {goal}.
        Format as JSON.
        \"\"\"
        response = bedrock_client.invoke_model(prompt=prompt, model_id="anthropic.claude-3-sonnet")

    In local dev: we compute recommendations deterministically.
    """
    campaign = store.get_campaign(campaign_id)
    if not campaign:
        return {}

    leads = store.get_leads(campaign_id=campaign_id)
    if not leads:
        return {}

    total_leads = len(leads)
    total_take_up = sum(1 for r in leads if r.get("take_up_flag") == "YES")
    take_up_rate = calculate_take_up_rate(total_leads, total_take_up)

    # Breakdown by segment_by_aum
    segment_stats: dict[str, dict[str, int]] = {}
    for lead in leads:
        seg = lead.get("segment_by_aum", "UNKNOWN")
        if seg not in segment_stats:
            segment_stats[seg] = {"leads": 0, "take_up": 0}
        segment_stats[seg]["leads"] += 1
        if lead.get("take_up_flag") == "YES":
            segment_stats[seg]["take_up"] += 1

    # Breakdown by wilayah
    wilayah_stats: dict[int, dict[str, int]] = {}
    for lead in leads:
        wil = lead.get("wilayah", 0)
        if wil not in wilayah_stats:
            wilayah_stats[wil] = {"leads": 0, "take_up": 0}
        wilayah_stats[wil]["leads"] += 1
        if lead.get("take_up_flag") == "YES":
            wilayah_stats[wil]["take_up"] += 1

    # Time-to-take-up stats
    days_list = [
        int(r["time_to_take_up_days"])
        for r in leads
        if r.get("take_up_flag") == "YES" and r.get("time_to_take_up_days") is not None
    ]
    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None

    return {
        "campaign": campaign,
        "total_leads": total_leads,
        "total_take_up": total_take_up,
        "take_up_rate": round(take_up_rate, 2),
        "avg_days_to_take_up": avg_days,
        "segment_stats": segment_stats,
        "wilayah_stats": wilayah_stats,
    }


# ---------------------------------------------------------------------------
# Simulated LLM recommendation engine
# ---------------------------------------------------------------------------

def _generate_recommendations(
    ctx: dict[str, Any],
    goal: str,
) -> list[dict[str, Any]]:
    """Generate 3 structured recommendations from campaign context.

    This function simulates what Amazon Bedrock Claude would return.
    The logic is deterministic but produces output in the same format
    as a real LLM JSON response.
    """
    campaign = ctx["campaign"]
    take_up_rate = ctx["take_up_rate"]
    segment_stats = ctx["segment_stats"]
    wilayah_stats = ctx["wilayah_stats"]
    avg_days = ctx["avg_days_to_take_up"]
    total_leads = ctx["total_leads"]

    recommendations: list[dict[str, Any]] = []

    # --- Recommendation 1: Best performing segment ---
    best_segment = None
    best_segment_rate = 0.0
    worst_segment = None
    worst_segment_rate = 100.0

    for seg, stats in segment_stats.items():
        if stats["leads"] > 0:
            rate = (stats["take_up"] / stats["leads"]) * 100
            if rate > best_segment_rate:
                best_segment_rate = rate
                best_segment = seg
            if rate < worst_segment_rate:
                worst_segment_rate = rate
                worst_segment = seg

    if best_segment:
        recommendations.append({
            "id": "REC-001",
            "priority": "HIGH",
            "category": "Segmentasi Nasabah",
            "title": f"Fokuskan leads pada segmen {best_segment}",
            "insight": (
                f"Segmen {best_segment} menunjukkan take up rate tertinggi sebesar "
                f"{best_segment_rate:.1f}% — "
                f"{best_segment_rate - take_up_rate:.1f} poin persentase di atas rata-rata campaign "
                f"({take_up_rate:.1f}%). "
                f"Sementara segmen {worst_segment} hanya mencapai {worst_segment_rate:.1f}%."
            ),
            "action": (
                f"Pada campaign berikutnya, alokasikan minimal 60% dari total leads ke segmen "
                f"{best_segment}. Pertimbangkan untuk mengurangi alokasi ke segmen "
                f"{worst_segment} atau menggunakan pendekatan channel yang berbeda untuk segmen tersebut."
            ),
            "expected_impact": f"Estimasi peningkatan take up rate: +{min(best_segment_rate - take_up_rate, 8):.1f} poin persentase",
            "confidence": "HIGH" if best_segment_rate > take_up_rate * 1.5 else "MEDIUM",
            "data_source": f"Analisis {total_leads} leads dari campaign {campaign['campaign_id']}",
        })

    # --- Recommendation 2: Best performing region ---
    best_wilayah = None
    best_wilayah_rate = 0.0
    low_wilayah_list = []

    for wil, stats in wilayah_stats.items():
        if stats["leads"] >= 2:  # min threshold
            rate = (stats["take_up"] / stats["leads"]) * 100
            if rate > best_wilayah_rate:
                best_wilayah_rate = rate
                best_wilayah = wil
            if rate < take_up_rate * 0.5:
                low_wilayah_list.append(wil)

    if best_wilayah:
        low_wil_str = (
            f"Wilayah {', '.join(str(w) for w in sorted(low_wilayah_list))}"
            if low_wilayah_list
            else "beberapa wilayah performa rendah"
        )
        recommendations.append({
            "id": "REC-002",
            "priority": "MEDIUM",
            "category": "Distribusi Regional",
            "title": f"Perluas distribusi ke Wilayah {best_wilayah} dan wilayah serupa",
            "insight": (
                f"Wilayah {best_wilayah} mencapai take up rate {best_wilayah_rate:.1f}%, "
                f"tertinggi di antara semua wilayah yang aktif. "
                f"{low_wil_str} menunjukkan performa di bawah setengah rata-rata campaign."
            ),
            "action": (
                f"Tingkatkan kuota leads di Wilayah {best_wilayah} sebesar 20-30% pada campaign berikutnya. "
                f"Lakukan analisis lebih lanjut terhadap {low_wil_str} — "
                f"pertimbangkan penggantian channel distribusi atau penyesuaian kriteria nasabah di wilayah tersebut."
            ),
            "expected_impact": "Estimasi peningkatan total take up: +8-12 nasabah per 100 leads",
            "confidence": "MEDIUM",
            "data_source": f"Data regional {len(wilayah_stats)} wilayah aktif",
        })

    # --- Recommendation 3: Timing / duration optimization ---
    current_channel = campaign.get("media_blasting", "")
    current_duration = campaign.get("duration_days", 30)

    if goal == "reduce_time_to_take_up" and avg_days:
        timing_rec = {
            "id": "REC-003",
            "priority": "HIGH",
            "category": "Optimasi Waktu",
            "title": f"Persingkat durasi follow-up menjadi {max(7, int(avg_days * 0.7))} hari",
            "insight": (
                f"Rata-rata waktu dari distribusi leads hingga take up adalah {avg_days} hari. "
                f"Data menunjukkan majority take up terjadi dalam {int(avg_days * 0.7)} hari pertama. "
                f"Durasi campaign saat ini {current_duration} hari kemungkinan terlalu panjang."
            ),
            "action": (
                f"Rancang campaign dengan durasi {max(14, int(avg_days * 0.7) + 3)} hari "
                f"dan fokuskan intensitas kontak via {current_channel} pada minggu pertama. "
                f"Jadwalkan reminder otomatis di hari ke-{max(3, int(avg_days * 0.3))} "
                f"untuk leads yang belum merespons."
            ),
            "expected_impact": f"Estimasi pengurangan rata-rata waktu take up: -{avg_days - max(7, int(avg_days * 0.7)):.0f} hari",
            "confidence": "MEDIUM" if avg_days > 10 else "LOW",
            "data_source": f"Distribusi waktu dari {ctx['total_take_up']} take up events",
        }
    elif goal == "expand_reach":
        # Suggest untried channels
        all_channels = ["wa", "digisales", "telesales", "email", "sms", "push notif"]
        unused_channels = [c for c in all_channels if c != current_channel][:2]
        timing_rec = {
            "id": "REC-003",
            "priority": "MEDIUM",
            "category": "Ekspansi Channel",
            "title": f"Uji coba channel {' dan '.join(unused_channels)} untuk memperluas jangkauan",
            "insight": (
                f"Campaign ini hanya menggunakan channel {current_channel}. "
                f"Data historis menunjukkan channel {unused_channels[0]} memiliki performa "
                f"kompetitif untuk program {campaign.get('flag_program', '')}."
            ),
            "action": (
                f"Alokasikan 15-20% leads ke channel {unused_channels[0]} sebagai A/B test "
                f"pada campaign berikutnya. Bandingkan take up rate setelah 2 minggu "
                f"sebelum memutuskan alokasi final."
            ),
            "expected_impact": "Estimasi peningkatan jangkauan: +15-25% total leads yang dapat dikontak",
            "confidence": "MEDIUM",
            "data_source": "Benchmark performa channel lintas campaign",
        }
    else:  # maximize_take_up_rate (default)
        similar = store.get_similarity_index(campaign["campaign_id"])
        best_similar = None
        if similar:
            best_similar = max(similar, key=lambda s: s.get("take_up_rate", 0))

        if best_similar and best_similar.get("take_up_rate", 0) > take_up_rate:
            diff = best_similar["take_up_rate"] - take_up_rate
            timing_rec = {
                "id": "REC-003",
                "priority": "HIGH",
                "category": "Pembelajaran dari Campaign Serupa",
                "title": f"Adopsi strategi dari \"{best_similar['campaign_name']}\"",
                "insight": (
                    f"Campaign \"{best_similar['campaign_name']}\" (ID: {best_similar['similar_campaign_id']}) "
                    f"memiliki kesamaan dimensi {', '.join(best_similar['matching_dimensions'])} "
                    f"dengan campaign ini, namun mencapai take up rate {best_similar['take_up_rate']:.1f}% — "
                    f"{diff:.1f} poin persentase lebih tinggi dari campaign ini ({take_up_rate:.1f}%)."
                ),
                "action": (
                    f"Review kriteria nasabah dan strategi pendekatan yang digunakan oleh "
                    f"campaign \"{best_similar['campaign_name']}\". "
                    f"Identifikasi perbedaan spesifik pada segment targeting atau timing distribusi "
                    f"yang mungkin berkontribusi pada perbedaan performa sebesar {diff:.1f}%."
                ),
                "expected_impact": f"Potensi peningkatan take up rate: +{min(diff, 10):.1f} poin persentase",
                "confidence": "HIGH" if best_similar["similarity_score"] >= 0.8 else "MEDIUM",
                "data_source": f"Similarity score: {best_similar['similarity_score']:.2f} (dari {len(similar)} campaign serupa)",
            }
        else:
            timing_rec = {
                "id": "REC-003",
                "priority": "LOW",
                "category": "Peningkatan Data Kualitas",
                "title": "Tingkatkan kelengkapan data monitoring untuk analisis lebih akurat",
                "insight": (
                    f"Dari {total_leads} leads, hanya {ctx['total_take_up']} yang memiliki "
                    f"data take up lengkap. Data yang lebih lengkap memungkinkan model AI "
                    f"memberikan rekomendasi dengan confidence lebih tinggi."
                ),
                "action": (
                    "Pastikan Monitoring Report disubmit dalam 7 hari setelah campaign selesai. "
                    "Lengkapi field take_up_date dan total_transaction_value untuk semua "
                    "leads yang melakukan take up."
                ),
                "expected_impact": "Peningkatan akurasi rekomendasi AI di iterasi berikutnya",
                "confidence": "HIGH",
                "data_source": "Analisis kelengkapan data campaign",
            }

    recommendations.append(timing_rec)
    return recommendations


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/ai/recommendations")
async def get_ai_recommendations(body: RecommendationRequest) -> JSONResponse:
    """Generate AI-powered campaign improvement recommendations.

    Simulates an Amazon Bedrock Claude call with campaign performance data.
    In production, this would call:
        bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps({"prompt": structured_prompt, "max_tokens": 1500})
        )

    Request body:
        campaign_id: Target campaign to analyze.
        goal: Optimization objective.
            - "maximize_take_up_rate" (default)
            - "reduce_time_to_take_up"
            - "expand_reach"

    Returns:
        200 with recommendations list, campaign summary, and metadata.
        400 if campaign_id is invalid.
        404 if campaign not found.
    """
    campaign_id = (body.campaign_id or "").strip()
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id is required.")

    valid_goals = {"maximize_take_up_rate", "reduce_time_to_take_up", "expand_reach"}
    if body.goal not in valid_goals:
        raise HTTPException(
            status_code=400,
            detail=f"goal must be one of: {sorted(valid_goals)}",
        )

    ctx = _build_prompt_context(campaign_id)
    if not ctx:
        raise HTTPException(
            status_code=404,
            detail=f"Campaign '{campaign_id}' tidak ditemukan atau tidak memiliki data leads.",
        )

    recommendations = _generate_recommendations(ctx, body.goal)

    campaign = ctx["campaign"]
    goal_labels = {
        "maximize_take_up_rate": "Maksimalkan Take Up Rate",
        "reduce_time_to_take_up": "Percepat Waktu Take Up",
        "expand_reach": "Perluas Jangkauan Campaign",
    }

    return JSONResponse(
        status_code=200,
        content={
            "model": "[SIMULASI] amazon.bedrock.claude-3-sonnet",
            "campaign_summary": {
                "campaign_id": campaign_id,
                "nama_program": campaign.get("nama_program"),
                "flag_program": campaign.get("flag_program"),
                "media_blasting": campaign.get("media_blasting"),
                "total_leads": ctx["total_leads"],
                "total_take_up": ctx["total_take_up"],
                "take_up_rate": ctx["take_up_rate"],
                "avg_days_to_take_up": ctx["avg_days_to_take_up"],
            },
            "goal": body.goal,
            "goal_label": goal_labels[body.goal],
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "disclaimer": (
                "Rekomendasi ini dihasilkan oleh simulasi lokal yang merepresentasikan "
                "output dari Amazon Bedrock Claude. Pada deployment production, "
                "analisis dilakukan oleh model LLM dengan data historis yang lebih luas."
            ),
        },
    )
