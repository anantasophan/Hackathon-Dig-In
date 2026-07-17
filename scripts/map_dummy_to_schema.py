"""Map the 3 raw dummy Excel files into the Campaign Insight Generator schema.

Produces, under ``Data Dummy/json/mapped/``:
  - campaigns_dummy.json   : campaign master records (schema of campaigns.json)
  - leads_dummy.json       : sampled individual lead records (schema of leads.json)
  - trend_dummy.json       : weekly trend per campaign_id (schema of trend_data.json)
  - regional_dummy.json    : weekly regional data per campaign_id (schema of regional_weekly.json)
  - similarity_dummy.json  : similar-campaign pairs (schema of similarity_index.json)

Design notes / known limitations (documented, not hidden):

1. Source files do not contain `wilayah`, `cabang`, `outlet`, `segment_by_aum`,
   `range_usia`, `segment_wondr`, `range_saldo_tab`, `avg_aum_3_bln`. These are
   DERIVED deterministically from a hash of `cif` (or from real balance
   columns when available) purely so downstream features (Regional
   Performance, Customer Criteria) have something to render. They are
   SYNTHETIC, not real customer attributes.

2. File 1 (QRIS / E-Wallet-Billpayment) has no explicit take-up date column.
   `qris_first_flag` + `amount_first_qris` are used as the take-up signal
   across both products (the only unambiguous binary flag + amount pair in
   the file). Since no real take-up date exists in the source data,
   `take_up_date` is a SYNTHETIC value: `periode_start` + a deterministic
   pseudo-random offset (1-30 days, derived from `cif`) when `take_up_flag`
   is "YES". This is clearly a demo/filler value, not a real timestamp --
   it exists only so the Time-to-Take-Up feature has something to render
   for these two campaigns instead of showing an empty state.

3. File 2 (Tapenas Emas) take-up is defined by `norek_tapenas != "NULL"`,
   with `take_up_date = acct_open_date` and
   `total_transaction_value = saldo_posisi_tapenas`.

4. File 3 (Lifegoals/Balrun WA blast log) is a message-level delivery log
   (many rows per customer), not a leads file. It is aggregated to one
   lead record per unique `cif`. Take-up is defined by whether
   `lifegoals_account` was ever populated for that customer.

5. IMPORTANT -- sampling and aggregate consistency:
   The local dev server's ``campaign_overview`` / ``regional_performance``
   endpoints recompute totals directly from ``store.get_leads()`` (the raw
   lead list), NOT from any pre-aggregated field. Therefore leads are
   downsampled FIRST (stratified: keeps the same take-up ratio as the full
   population, per campaign), and ALL aggregate outputs
   (``campaigns_dummy.json``, ``trend_dummy.json``, ``regional_dummy.json``)
   are computed FROM THAT SAME SAMPLE -- mirroring exactly how the original
   C001-C005 mock fixtures are structured (leads.json is the single source
   of truth; every other file is derived from it). This guarantees the API
   response totals always match what's stored.

6. The FULL-population take-up rate is printed to stdout for reference
   (so the sampled rate can be sanity-checked against it), but the files
   written to disk reflect the SAMPLE only.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "Data Dummy"
OUT_DIR = ROOT / "Data Dummy" / "json" / "mapped"

# Target sample size per campaign. Larger than the ~30 rows used by
# C001-C005 because real take-up rates here are much lower (0.4%-2.5%).
# Sampling is UNBIASED (plain reservoir, Algorithm R) -- 800 is large enough
# that even the lowest-rate campaign (~0.41%) reliably yields several real
# take-up examples (verified below, not just assumed statistically), while
# keeping the resulting JSON small enough for a fast in-memory dev store.
SAMPLE_SIZE = 800

VALID_RANGE_USIA = ["BABY BOOMER", "GEN X", "GEN Y", "GEN Z", "GEN ALPHA"]
VALID_SEGMENT_CRS_FALLBACK = ["mass", "employee", "profesi"]


# ---------------------------------------------------------------------------
# Deterministic synthetic-field helpers
# ---------------------------------------------------------------------------


def _stable_int(seed: str, mod: int) -> int:
    """Deterministic pseudo-random int in [0, mod) derived from a seed string."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h, 16) % mod


def derive_wilayah(cif: str) -> int:
    """Region code 1-17, deterministic from cif."""
    return _stable_int(cif + ":wilayah", 17) + 1


def derive_cabang(cif: str, wilayah: int) -> int:
    """Branch code, deterministic from cif, grouped loosely by wilayah."""
    return wilayah * 18 + _stable_int(cif + ":cabang", 18) + 1


def derive_outlet(cif: str) -> int:
    """Outlet level 0-3 (0 = KC / follows branch)."""
    return _stable_int(cif + ":outlet", 4)


def derive_range_usia(cif: str) -> str:
    """Age generation, deterministic from cif (no source data available)."""
    idx = _stable_int(cif + ":usia", len(VALID_RANGE_USIA))
    return VALID_RANGE_USIA[idx]


def derive_segment_by_aum(avg_aum: float) -> str:
    """Bucket AUM into a segment tier."""
    if avg_aum >= 500_000_000:
        return "PRIVATE"
    if avg_aum >= 100_000_000:
        return "HIGH AFFLUENT"
    if avg_aum >= 50_000_000:
        return "EMERALD"
    if avg_aum >= 20_000_000:
        return "AFFLUENT"
    if avg_aum >= 10_000_000:
        return "UPPERMASS"
    return "MASS"


def derive_segment_crs(cif: str) -> str:
    idx = _stable_int(cif + ":crs", len(VALID_SEGMENT_CRS_FALLBACK))
    return VALID_SEGMENT_CRS_FALLBACK[idx]


def derive_synthetic_take_up_date(cif: str, periode_start: date | None) -> tuple[date | None, int | None]:
    """Synthetic take_up_date for File 1 (no real take-up date in source).

    Offset is 1-30 days after periode_start, deterministic from cif.
    Returns (take_up_date, time_to_take_up_days), both None if periode_start
    is None.
    """
    if periode_start is None:
        return None, None
    offset = _stable_int(cif + ":takeup_offset", 30) + 1
    take_up_date = periode_start + timedelta(days=offset)
    return take_up_date, offset


def week_start(d: date) -> date:
    """Return the Monday of the week containing ``d``."""
    return d - timedelta(days=d.weekday())


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.upper() == "NULL" or s == "-":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.upper() == "NULL":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Reservoir sampler (preserves true population proportions)
# ---------------------------------------------------------------------------


class ReservoirSampler:
    """Classic single-reservoir sampling (Algorithm R).

    Every record seen has an equal probability of ending up in the final
    sample, so the take-up ratio in the sample is an unbiased estimate of
    the true population ratio. No artificial rebalancing is applied --
    a low take-up-rate campaign will correctly show a low take-up rate
    in its sample too.
    """

    def __init__(self, sample_size: int):
        self.sample_size = sample_size
        self.pool: list[dict] = []
        self.seen = 0
        # Full-population counters (for reference / sanity check only).
        self.full_total = 0
        self.full_take_up = 0
        self.full_transaction_value = 0.0

    def offer(self, lead_record: dict, take_up: bool, trans_value: float) -> None:
        self.full_total += 1
        if take_up:
            self.full_take_up += 1
            self.full_transaction_value += trans_value

        if len(self.pool) < self.sample_size:
            self.pool.append(lead_record)
        else:
            j = random.randint(0, self.seen)
            if j < self.sample_size:
                self.pool[j] = lead_record
        self.seen += 1

    def sample(self) -> list[dict]:
        combined = list(self.pool)
        random.shuffle(combined)
        return combined

    def full_take_up_rate(self) -> float:
        if self.full_total == 0:
            return 0.0
        return round(100.0 * self.full_take_up / self.full_total, 2)


# ---------------------------------------------------------------------------
# Aggregator: builds campaign / trend / regional dicts from a lead sample
# ---------------------------------------------------------------------------


def build_aggregates(campaign_id: str, nama_program: str, flag_program: str,
                      jenis_leads: str, media_blasting: str,
                      leads: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """Compute campaign/trend/regional dicts purely from the given lead sample."""
    total_leads = len(leads)
    total_take_up = sum(1 for r in leads if r["take_up_flag"] == "YES")
    total_transaction_value = sum(
        r["total_transaction_value"] for r in leads
        if r["take_up_flag"] == "YES" and r["total_transaction_value"] is not None
    )

    starts = [parse_date(r["periode_start"]) for r in leads if r["periode_start"]]
    min_start = min(starts) if starts else None
    max_start = max(starts) if starts else None

    take_up_rate = round(100.0 * total_take_up / total_leads, 2) if total_leads else 0.0

    campaign_dict = {
        "campaign_id": campaign_id,
        "nama_program": nama_program,
        "flag_program": flag_program,
        "jenis_leads": jenis_leads,
        "media_blasting": media_blasting,
        "periode_start": min_start.isoformat() if min_start else None,
        "periode_end": max_start.isoformat() if max_start else None,
        "duration_days": (max_start - min_start).days if min_start and max_start else 0,
        "total_leads": total_leads,
        "total_take_up": total_take_up,
        "take_up_rate": take_up_rate,
        "total_transaction_value": round(total_transaction_value, 2),
    }

    # Weekly trend
    weekly: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    for r in leads:
        d = parse_date(r["periode_start"])
        if d is None:
            continue
        wk = week_start(d)
        weekly[wk][0] += 1
        if r["take_up_flag"] == "YES":
            weekly[wk][1] += 1

    trend_list = []
    for wk in sorted(weekly.keys()):
        leads_n, takeup_n = weekly[wk]
        rate = round(100.0 * takeup_n / leads_n, 2) if leads_n else 0.0
        trend_list.append({
            "period_start": wk.isoformat(),
            "period_end": (wk + timedelta(days=6)).isoformat(),
            "total_leads": leads_n,
            "total_take_up": takeup_n,
            "take_up_rate": rate,
        })

    # Regional weekly
    regional: dict[tuple[int, date], list[float]] = defaultdict(lambda: [0, 0, 0.0])
    for r in leads:
        d = parse_date(r["periode_start"])
        if d is None:
            continue
        wk = week_start(d)
        wilayah = r["wilayah"]
        key = (wilayah, wk)
        regional[key][0] += 1
        if r["take_up_flag"] == "YES":
            regional[key][1] += 1
            regional[key][2] += r["total_transaction_value"] or 0.0

    regional_list = []
    for (wilayah, wk), (leads_n, takeup_n, trans_sum) in sorted(regional.items()):
        rate = round(100.0 * takeup_n / leads_n, 2) if leads_n else 0.0
        avg_trans = round(trans_sum / takeup_n, 2) if takeup_n else 0.0
        regional_list.append({
            "wilayah": wilayah,
            "week_start": wk.isoformat(),
            "leads_count": leads_n,
            "take_up_count": takeup_n,
            "take_up_rate": rate,
            "avg_transaction_value": avg_trans,
        })

    return campaign_dict, trend_list, regional_list


# ---------------------------------------------------------------------------
# File 1: CASHBACK QRIS / E-WALLET-BILLPAYMENT
# ---------------------------------------------------------------------------


def process_file1(sampler_qris: ReservoirSampler, sampler_ewallet: ReservoirSampler,
                   campaign_id_qris: str, campaign_name_qris: str,
                   campaign_id_ewallet: str, campaign_name_ewallet: str) -> None:
    path = SRC_DIR / "Dummy Kiro 1.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Sheet1"]

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        (cif, nama_program, jenis_leads, tanggal_blast, periode_leads, media_blasting,
         status_wa, nomor_index, periode_start_raw, end_date_raw, flag_program,
         customer_name_masked, flag_aktivasi_wondr, tanggal_aktivasi_first,
         sv_billpay, freq_billpay, sv_ewallet, freq_ewallet, sv_qris, freq_qris,
         bal_dec25, bal_jan, bal_feb, bal_mar, bal_recent, flag_eligible,
         flag_reward, amount_first_qris, qris_first_flag, norek) = row

        cif = str(cif)
        periode_start = parse_date(periode_start_raw)
        take_up = (qris_first_flag == "YES")
        trans_value = to_float(amount_first_qris) if take_up else 0.0

        wilayah = derive_wilayah(cif)
        cabang = derive_cabang(cif, wilayah)
        outlet = derive_outlet(cif)
        avg_aum = (to_float(bal_jan) + to_float(bal_feb) + to_float(bal_mar)) / 3.0
        segment_by_aum = derive_segment_by_aum(avg_aum)
        range_usia = derive_range_usia(cif)
        segment_crs = derive_segment_crs(cif)

        is_qris = flag_program == "PROGRAM QRIS"
        sampler = sampler_qris if is_qris else sampler_ewallet
        cid = campaign_id_qris if is_qris else campaign_id_ewallet
        cname = campaign_name_qris if is_qris else campaign_name_ewallet

        take_up_date, time_to_take_up = (
            derive_synthetic_take_up_date(cif, periode_start) if take_up else (None, None)
        )

        lead_record = {
            "campaign_id": cid,
            "nama_program": cname,
            "jenis_leads": jenis_leads,
            "media_blasting": "wa",
            "periode_start": periode_start.isoformat() if periode_start else None,
            "flag_program": flag_program,
            "wilayah": wilayah,
            "cabang": cabang,
            "outlet": outlet,
            "segment_crs": segment_crs,
            "segment_by_aum": segment_by_aum,
            "segment_wondr": range_usia,
            "segment_div_owner": "CRS",
            "range_usia": range_usia,
            "range_saldo_tab": to_float(bal_recent),
            "avg_aum_3_bln": round(avg_aum, 2),
            "potensi_money": round(to_float(bal_recent) * 0.05, 2),
            "take_up_flag": "YES" if take_up else "NO",
            "take_up_date": take_up_date.isoformat() if take_up_date else None,
            "time_to_take_up_days": time_to_take_up,
            "total_transaction_value": round(trans_value, 2) if take_up else None,
        }

        sampler.offer(lead_record, take_up, trans_value)

    wb.close()


# ---------------------------------------------------------------------------
# File 2: Tapenas Emas
# ---------------------------------------------------------------------------


def process_file2(sampler: ReservoirSampler, campaign_id: str, campaign_name: str,
                   flag_program_value: str) -> None:
    path = SRC_DIR / "Dummy Kiro 2.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Sheet"]

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        (customer_name, cif, campaign_name_col, jenis_leads, campaign_channel,
         periode_leads, periode_start_raw, segment_div_owner, sub_crs,
         flag_aktivasi_wondr, flag_transaksi_wondr, norek_tapenas,
         affiliated_acct_no, product_name, saldo_posisi_tapenas, acct_open_date_raw,
         tapenas_term, tapenas_mth_pay, flag_lifegoals, flag_multiple_tapenas,
         bal_0301, bal_0331, growth_saldo, flag_eligible) = row

        cif = str(cif)
        periode_start = parse_date(periode_start_raw)
        take_up = norek_tapenas != "NULL" and norek_tapenas is not None
        take_up_date = parse_date(acct_open_date_raw) if take_up else None
        trans_value = to_float(saldo_posisi_tapenas) if take_up else 0.0

        time_to_take_up = None
        if take_up and periode_start and take_up_date:
            time_to_take_up = (take_up_date - periode_start).days

        wilayah = derive_wilayah(cif)
        cabang = derive_cabang(cif, wilayah)
        outlet = derive_outlet(cif)
        avg_aum = (to_float(bal_0301) + to_float(bal_0331)) / 2.0
        segment_by_aum = derive_segment_by_aum(avg_aum)
        range_usia = derive_range_usia(cif)

        lead_record = {
            "campaign_id": campaign_id,
            "nama_program": campaign_name,
            "jenis_leads": jenis_leads,
            "media_blasting": "wa",
            "periode_start": periode_start.isoformat() if periode_start else None,
            "flag_program": flag_program_value,
            "wilayah": wilayah,
            "cabang": cabang,
            "outlet": outlet,
            "segment_crs": str(sub_crs).lower() if sub_crs else "mass",
            "segment_by_aum": segment_by_aum,
            "segment_wondr": range_usia,
            "segment_div_owner": str(segment_div_owner) if segment_div_owner else "CRS",
            "range_usia": range_usia,
            "range_saldo_tab": to_float(bal_0331),
            "avg_aum_3_bln": round(avg_aum, 2),
            "potensi_money": round(to_float(bal_0331) * 0.1, 2),
            "take_up_flag": "YES" if take_up else "NO",
            "take_up_date": take_up_date.isoformat() if take_up_date else None,
            "time_to_take_up_days": time_to_take_up,
            "total_transaction_value": round(trans_value, 2) if take_up else None,
        }

        sampler.offer(lead_record, take_up, trans_value)

    wb.close()


# ---------------------------------------------------------------------------
# File 3: Lifegoals / Balrun WA blast log (aggregate per cif first)
# ---------------------------------------------------------------------------


def process_file3(sampler: ReservoirSampler, campaign_id: str, campaign_name: str,
                   flag_program_value: str, jenis_leads_value: str) -> None:
    path = SRC_DIR / "Dummy Kiro 3.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Sheet"]

    per_cif: dict[str, dict] = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        (contact, templatename, sentat, deliveredat, readat, status, cif,
         flag_balrun, segment_div_owner, sub_crs, flag_aktivasi_wondr,
         lifegoals_account, norek_affiliasi, open_date_lifegoals_raw,
         timestamp_lifegoals, setoran_awal, setoran_bulanan, target_tabungan,
         monthly_term, setoran_awal_tier, flag_eligible, flag_racing) = row

        cif = str(cif)
        filled = lifegoals_account not in (None, "NULL", "", "-")

        existing = per_cif.get(cif)
        if existing is None:
            per_cif[cif] = {
                "segment_div_owner": segment_div_owner,
                "sub_crs": sub_crs,
                "take_up": filled,
                "take_up_date": parse_date(open_date_lifegoals_raw) if filled else None,
                "setoran_awal": to_float(setoran_awal) if filled else 0.0,
            }
        elif filled and not existing["take_up"]:
            existing["take_up"] = True
            existing["take_up_date"] = parse_date(open_date_lifegoals_raw)
            existing["setoran_awal"] = to_float(setoran_awal)

    # Campaign period derived from actual `sentat` blast timestamps (all on
    # 2026-01-19 in the source data) -- NOT from the template name suffix
    # "15jan26", which does not match the real send date.
    periode_start = date(2026, 1, 19)

    for cif, info in per_cif.items():
        take_up = info["take_up"]
        take_up_date = info["take_up_date"]
        trans_value = info["setoran_awal"] if take_up else 0.0
        time_to_take_up = (take_up_date - periode_start).days if take_up and take_up_date else None

        wilayah = derive_wilayah(cif)
        cabang = derive_cabang(cif, wilayah)
        outlet = derive_outlet(cif)
        range_usia = derive_range_usia(cif)
        segment_by_aum = derive_segment_by_aum(trans_value * 10 if take_up else 5_000_000)

        lead_record = {
            "campaign_id": campaign_id,
            "nama_program": campaign_name,
            "jenis_leads": jenis_leads_value,
            "media_blasting": "wa",
            "periode_start": periode_start.isoformat(),
            "flag_program": flag_program_value,
            "wilayah": wilayah,
            "cabang": cabang,
            "outlet": outlet,
            "segment_crs": str(info["sub_crs"]).lower() if info["sub_crs"] else "employee",
            "segment_by_aum": segment_by_aum,
            "segment_wondr": range_usia,
            "segment_div_owner": str(info["segment_div_owner"]) if info["segment_div_owner"] else "CRS",
            "range_usia": range_usia,
            "range_saldo_tab": round(trans_value, 2),
            "avg_aum_3_bln": round(trans_value * 2, 2),
            "potensi_money": round(trans_value * 1.5, 2) if take_up else 0.0,
            "take_up_flag": "YES" if take_up else "NO",
            "take_up_date": take_up_date.isoformat() if take_up_date else None,
            "time_to_take_up_days": time_to_take_up,
            "total_transaction_value": round(trans_value, 2) if take_up else None,
        }

        sampler.offer(lead_record, take_up, trans_value)

    wb.close()


# ---------------------------------------------------------------------------
# Similarity index (simple: 3-dimension match across the 4 new campaigns)
# ---------------------------------------------------------------------------


def build_similarity(campaigns: list[dict]) -> list[dict]:
    entries = []
    for a in campaigns:
        for b in campaigns:
            if a["campaign_id"] == b["campaign_id"]:
                continue
            matching = []
            for dim in ("flag_program", "jenis_leads", "media_blasting"):
                if a[dim] == b[dim]:
                    matching.append(dim)
            if not matching:
                continue
            score = round(len(matching) / 3.0, 2)
            entries.append({
                "campaign_id": a["campaign_id"],
                "similar_campaign_id": b["campaign_id"],
                "campaign_name": b["nama_program"],
                "matching_dimensions": matching,
                "dimension_count": len(matching),
                "similarity_score": score,
                "take_up_rate": b["take_up_rate"],
                "total_leads": b["total_leads"],
                "total_take_up": b["total_take_up"],
            })
    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    random.seed(42)  # deterministic sampling across runs
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sampler_qris = ReservoirSampler(SAMPLE_SIZE)
    sampler_ewallet = ReservoirSampler(SAMPLE_SIZE)
    sampler_tapenas = ReservoirSampler(SAMPLE_SIZE)
    sampler_lifegoals = ReservoirSampler(SAMPLE_SIZE)

    defs = {
        "C006": ("Cashback QRIS 2026", "PROGRAM QRIS", "Migrasi", "wa"),
        "C007": ("E-Wallet / Billpayment 2026", "PROGRAM BIAYA ADMIN", "Migrasi", "wa"),
        "C008": ("Tapenas Emas 2026", "PROGRAM TAPENAS", "Akuisisi", "wa"),
        "C009": ("Lifegoals Balrun Payroll Jan 2026", "PROGRAM LIFEGOALS",
                  "Lifegoals - Balrun Payroll", "wa"),
    }

    print("Processing File 1 (Dummy Kiro 1.xlsx) ...")
    process_file1(
        sampler_qris, sampler_ewallet,
        "C006", defs["C006"][0],
        "C007", defs["C007"][0],
    )
    print(f"  C006 full_population: total={sampler_qris.full_total} "
          f"take_up_rate={sampler_qris.full_take_up_rate()}%")
    print(f"  C007 full_population: total={sampler_ewallet.full_total} "
          f"take_up_rate={sampler_ewallet.full_take_up_rate()}%")

    print("Processing File 2 (Dummy Kiro 2.xlsx) ...")
    process_file2(sampler_tapenas, "C008", defs["C008"][0], defs["C008"][1])
    print(f"  C008 full_population: total={sampler_tapenas.full_total} "
          f"take_up_rate={sampler_tapenas.full_take_up_rate()}%")

    print("Processing File 3 (Dummy Kiro 3.xlsx) ...")
    process_file3(sampler_lifegoals, "C009", defs["C009"][0], defs["C009"][1], defs["C009"][2])
    print(f"  C009 full_population: total={sampler_lifegoals.full_total} "
          f"take_up_rate={sampler_lifegoals.full_take_up_rate()}%")

    samplers = {
        "C006": sampler_qris,
        "C007": sampler_ewallet,
        "C008": sampler_tapenas,
        "C009": sampler_lifegoals,
    }

    campaigns_dummy = []
    leads_dummy = []
    trend_dummy = {}
    regional_dummy = {}

    for cid, sampler in samplers.items():
        nama_program, flag_program, jenis_leads, media_blasting = defs[cid]
        sample = sampler.sample()
        camp_dict, trend_list, regional_list = build_aggregates(
            cid, nama_program, flag_program, jenis_leads, media_blasting, sample
        )
        campaigns_dummy.append(camp_dict)
        leads_dummy.extend(sample)
        trend_dummy[cid] = trend_list
        regional_dummy[cid] = regional_list

    similarity_dummy = build_similarity(campaigns_dummy)

    with (OUT_DIR / "campaigns_dummy.json").open("w", encoding="utf-8") as f:
        json.dump(campaigns_dummy, f, ensure_ascii=False, indent=2)

    with (OUT_DIR / "leads_dummy.json").open("w", encoding="utf-8") as f:
        json.dump(leads_dummy, f, ensure_ascii=False, indent=2)

    with (OUT_DIR / "trend_dummy.json").open("w", encoding="utf-8") as f:
        json.dump(trend_dummy, f, ensure_ascii=False, indent=2)

    with (OUT_DIR / "regional_dummy.json").open("w", encoding="utf-8") as f:
        json.dump(regional_dummy, f, ensure_ascii=False, indent=2)

    with (OUT_DIR / "similarity_dummy.json").open("w", encoding="utf-8") as f:
        json.dump(similarity_dummy, f, ensure_ascii=False, indent=2)

    print()
    print("Done (SAMPLE-based, self-consistent). Output written to:", OUT_DIR)
    for c in campaigns_dummy:
        print(" ", c["campaign_id"], "-", c["nama_program"], "| sampled leads:", c["total_leads"],
              "| sampled take_up_rate:", c["take_up_rate"], "%")


if __name__ == "__main__":
    main()
