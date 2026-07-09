# Domain Data Model — Ground Truth

This document captures the **actual field names and valid values** from `backend/shared/models.py`. These take precedence over the design document when there are discrepancies.

## Key Terminology Mapping

| Design Doc Term | Actual Code Field | Notes |
|-----------------|-------------------|-------|
| product | `flag_program` | Program type, not a generic product |
| sub_product | `jenis_leads` | Purpose of leads (e.g. "Migrasi") |
| channel | `media_blasting` | Distribution channel |
| region | `wilayah` | Integer 1–17 (region code) |
| customer_id | `cif` | PII — must be stripped from all responses |
| campaign_name | `nama_program` | Human-readable name |
| segment | `segment_by_aum` | Primary AUM-based segment |

## Valid Enum Values

```python
VALID_MEDIA_BLASTING = {"wa", "digisales", "telesales", "email", "push notif", "sms"}

VALID_FLAG_PROGRAM = {"PROGRAM BIAYA ADMIN", "PROGRAM QRIS"}

VALID_SEGMENT_BY_AUM = {"UPPERMASS", "EMERALD", "MASS", "AFFLUENT", "PRIVATE", "HIGH AFFLUENT"}

VALID_RANGE_USIA = {"BABY BOOMER", "GEN X", "GEN Y", "GEN Z", "GEN ALPHA"}

VALID_SEGMENT_DIV_OWNER = {"CRS", "WEM (Perorangan)"}

SIMILAR_CAMPAIGN_DIMENSIONS = {"media_blasting", "jenis_leads", "flag_program"}
```

## PII Fields

**Only one PII field exists in the actual data model**: `cif` (customer identifier).

The design document mentions 4 PII fields (nama_lengkap, nomor_rekening, nomor_identitas, alamat_lengkap) but these do not exist in the `LeadRecord` dataclass. The `pii_filter.py` module handles `cif` removal.

`PII_FIELDS: frozenset[str] = frozenset({"cif"})`

## LeadRecord Fields

```python
# Core campaign fields (always present)
cif: str                    # PII — strip before any API response
nama_program: str           # Campaign name
jenis_leads: str            # Leads purpose (sub_product)
media_blasting: str         # Distribution channel
periode_start: str          # Blasting start date (yyyy-mm-dd)
flag_program: str           # Program type (product)
wilayah: int                # Region code 1–17
cabang: int                 # Branch code 1–324
outlet: int                 # 0 = KC (follows branch), 1–99 = outlet
segment_crs: str            # Segment by job type
segment_by_aum: str         # Segment by AUM tier
segment_wondr: str          # Permanent segment by age/income priority
segment_div_owner: str      # Segment by managing division
range_usia: str             # Age generation group
range_saldo_tab: float      # Savings balance range
avg_aum_3_bln: float        # 3-month average AUM
potensi_money: float        # Expected maximum potential value

# Monitoring report fields (optional — joined at ETL layer)
take_up_flag: str           # "YES" or "NO" (default "NO")
take_up_date: Optional[date]
time_to_take_up_days: Optional[int]
total_transaction_value: Optional[float]
```

## CampaignOverviewRequest

```python
start_date: str             # yyyy-mm-dd
end_date: str               # yyyy-mm-dd
flag_program: Optional[list[str]]    # filter by program type
media_blasting: Optional[list[str]]  # filter by channel
wilayah: Optional[list[int]]         # filter by region codes
jenis_leads: Optional[list[str]]     # filter by leads purpose
```

## CampaignComparisonRequest

```python
campaign_ids: list[str]     # 2–5 IDs; __post_init__ raises ValueError otherwise
group_by: Optional[Literal["flag_program", "wilayah", "media_blasting"]]
```

## SimilarCampaignRequest

```python
reference_campaign_id: str
dimensions: list[Literal["media_blasting", "jenis_leads", "flag_program"]]
limit: Optional[int] = 20  # max 20 results
```

## Athena Table Names

| Table | Usage |
|-------|-------|
| `campaign_overview_agg` | Pre-computed overview aggregates |
| `campaign` | Campaign master data with 5 comparison metrics |
| `regional_performance_agg` | Per-region weekly aggregates |
| `leads` | Raw lead records with customer attributes |

## wilayah (Region) Codes

`wilayah` is an integer (1–17), not a string. When used in SQL IN clauses, convert to string: `[str(w) for w in wilayah]`.
