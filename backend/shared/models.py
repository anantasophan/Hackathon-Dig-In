"""Shared data models for Campaign Insight Generator.

Contains dataclass models for request/response validation across
all Lambda handlers and the ETL pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

PII_FIELDS: frozenset[str] = frozenset({"cif"})

VALID_MEDIA_BLASTING: frozenset[str] = frozenset(
    {"wa", "digisales", "telesales", "email", "push notif", "sms"}
)
VALID_FLAG_PROGRAM: frozenset[str] = frozenset(
    {"PROGRAM BIAYA ADMIN", "PROGRAM QRIS"}
)
VALID_SEGMENT_BY_AUM: frozenset[str] = frozenset(
    {"UPPERMASS", "EMERALD", "MASS", "AFFLUENT", "PRIVATE", "HIGH AFFLUENT"}
)
VALID_RANGE_USIA: frozenset[str] = frozenset(
    {"BABY BOOMER", "GEN X", "GEN Y", "GEN Z", "GEN ALPHA"}
)
VALID_SEGMENT_DIV_OWNER: frozenset[str] = frozenset(
    {"CRS", "WEM (Perorangan)"}
)
SIMILAR_CAMPAIGN_DIMENSIONS: frozenset[str] = frozenset(
    {"media_blasting", "jenis_leads", "flag_program"}
)


# ---------------------------------------------------------------------------
# Core / shared models
# ---------------------------------------------------------------------------


@dataclass
class ActiveFilter:
    """Represents an active filter applied to a campaign dataset.

    Attributes:
        field: The dataset field to filter on.  Must be one of the supported
            filter field names: ``product``, ``sub_product``, ``channel``,
            ``region``, ``period``.
        values: Non-empty list of accepted values for this field.  An item in
            the dataset matches this filter when its value for ``field`` is
            contained in ``values``.
    """

    field: str
    values: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Lead record
# ---------------------------------------------------------------------------


@dataclass
class LeadRecord:
    """Raw lead row as loaded from the data source.

    The ``cif`` field is PII and must be stripped before any API response.
    Fields originating from the monitoring-report join (``take_up_flag``,
    ``take_up_date``, ``time_to_take_up_days``, ``total_transaction_value``)
    are optional because they are only available after the ETL join.

    Attributes:
        cif: Unique customer code (PII — strip before exposing).
        nama_program: Campaign name, e.g. ``"Cashback QRIS"``.
        jenis_leads: Leads purpose, e.g. ``"Migrasi"``.
        media_blasting: Distribution channel (wa, digisales, …).
        periode_start: Campaign blasting start date (yyyy-mm-dd string).
        flag_program: Program type, e.g. ``"PROGRAM QRIS"``.
        wilayah: Region code, integer 1–17.
        cabang: Branch code, integer 1–324.
        outlet: Outlet level: 0 = KC (follows branch), 1–99 = outlet.
        segment_crs: Segment by job type (employee, profesi, mass).
        segment_by_aum: Segment by AUM tier.
        segment_wondr: Permanent segment by age/income priority.
        segment_div_owner: Segment by managing division.
        range_usia: Age generation group.
        range_saldo_tab: Savings balance range as float.
        avg_aum_3_bln: 3-month average AUM as float.
        potensi_money: Expected maximum potential value as float.
        take_up_flag: Whether the customer took the product (YES/NO).
            Defaults to ``"NO"``.
        take_up_date: Date the customer took the product; ``None`` when no
            take-up occurred.
        time_to_take_up_days: Days from ``periode_start`` to ``take_up_date``,
            computed at ETL layer; ``None`` when no take-up.
        total_transaction_value: Actual realised value at take-up; ``None``
            when no take-up.  Distinct from ``potensi_money`` (max/expected).
    """

    # Core campaign fields
    cif: str
    nama_program: str
    jenis_leads: str
    media_blasting: str
    periode_start: str
    flag_program: str
    wilayah: int
    cabang: int
    outlet: int
    segment_crs: str
    segment_by_aum: str
    segment_wondr: str
    segment_div_owner: str
    range_usia: str
    range_saldo_tab: float
    avg_aum_3_bln: float
    potensi_money: float

    # Monitoring report fields (joined at ETL layer — optional)
    take_up_flag: str = "NO"
    take_up_date: Optional[date] = None
    time_to_take_up_days: Optional[int] = None
    total_transaction_value: Optional[float] = None


# ---------------------------------------------------------------------------
# Campaign Overview
# ---------------------------------------------------------------------------


@dataclass
class CampaignOverviewRequest:
    """Request payload for the Campaign Overview endpoint.

    Attributes:
        start_date: Inclusive start of the date range (``yyyy-mm-dd``).
        end_date: Inclusive end of the date range (``yyyy-mm-dd``).
        flag_program: Optional filter — restrict to these program types.
        media_blasting: Optional filter — restrict to these channels.
        wilayah: Optional filter — restrict to these region codes.
        jenis_leads: Optional filter — restrict to these leads purposes.
    """

    start_date: str
    end_date: str
    flag_program: Optional[list[str]] = None
    media_blasting: Optional[list[str]] = None
    wilayah: Optional[list[int]] = None
    jenis_leads: Optional[list[str]] = None


@dataclass
class TrendDataPoint:
    """A single point in a take-up rate trend series.

    Attributes:
        period_start: Start of the aggregation period (``yyyy-mm-dd``).
        period_end: End of the aggregation period (``yyyy-mm-dd``).
        take_up_rate: Take-up rate for this period as a percentage (0–100).
        total_leads: Total leads distributed in this period.
        total_take_up: Total conversions (take-ups) in this period.
    """

    period_start: str
    period_end: str
    take_up_rate: float
    total_leads: int
    total_take_up: int


@dataclass
class CampaignOverviewResponse:
    """Response payload for the Campaign Overview endpoint.

    Attributes:
        total_leads: Total leads across the requested date range and filters.
        total_take_up: Total conversions across the date range and filters.
        take_up_rate: Overall take-up rate as a percentage (0–100).
        total_campaigns: Number of distinct campaigns included.
        trend: Ordered list of :class:`TrendDataPoint` for the sparkline.
        filters: Active filters that were applied to produce this response.
    """

    total_leads: int
    total_take_up: int
    take_up_rate: float
    total_campaigns: int
    trend: list[TrendDataPoint] = field(default_factory=list)
    filters: list[ActiveFilter] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Campaign Comparison
# ---------------------------------------------------------------------------


@dataclass
class CampaignComparisonRequest:
    """Request payload for the Campaign Comparison endpoint.

    Attributes:
        campaign_ids: List of 2–5 campaign identifiers to compare.
        group_by: Optional dimension to further break down comparison charts.

    Raises:
        ValueError: If ``campaign_ids`` contains fewer than 2 or more than 5
            entries.
    """

    campaign_ids: list[str]
    group_by: Optional[Literal["flag_program", "wilayah", "media_blasting"]] = None

    def __post_init__(self) -> None:
        if len(self.campaign_ids) < 2:
            raise ValueError(
                "campaign_ids must contain at least 2 campaign identifiers, "
                f"got {len(self.campaign_ids)}"
            )
        if len(self.campaign_ids) > 5:
            raise ValueError(
                "campaign_ids must contain at most 5 campaign identifiers, "
                f"got {len(self.campaign_ids)}"
            )


@dataclass
class CampaignMetric:
    """Aggregated metrics for a single campaign.

    Attributes:
        campaign_id: Unique campaign identifier.
        campaign_name: Human-readable campaign name (``nama_program``).
        flag_program: Program type of this campaign.
        total_leads: Total leads distributed.
        total_take_up: Total conversions.
        take_up_rate: Conversion rate as a percentage (0–100).
        total_transaction_value: Sum of all realised transaction values.
        duration_days: Number of days the campaign was active.
    """

    campaign_id: str
    campaign_name: str
    flag_program: str
    total_leads: int
    total_take_up: int
    take_up_rate: float
    total_transaction_value: float
    duration_days: int


@dataclass
class CampaignComparisonResponse:
    """Response payload for the Campaign Comparison endpoint.

    Attributes:
        campaigns: Metrics for each requested campaign.
        comparison_chart: Chart-ready data structure for front-end rendering.
    """

    campaigns: list[CampaignMetric] = field(default_factory=list)
    comparison_chart: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Similar Campaign
# ---------------------------------------------------------------------------


@dataclass
class SimilarCampaignRequest:
    """Request payload for the Similar Campaign finder endpoint.

    The three supported matching dimensions correspond to
    :data:`SIMILAR_CAMPAIGN_DIMENSIONS`.

    Attributes:
        reference_campaign_id: The campaign whose similar counterparts are
            sought.
        dimensions: One or more of ``"media_blasting"``, ``"jenis_leads"``,
            ``"flag_program"`` to use as matching criteria.
        limit: Maximum number of similar campaigns to return.  Defaults to 20.
    """

    reference_campaign_id: str
    dimensions: list[Literal["media_blasting", "jenis_leads", "flag_program"]]
    limit: Optional[int] = 20


@dataclass
class SimilarCampaignResult:
    """A single similar-campaign result.

    Attributes:
        campaign_id: Unique campaign identifier.
        campaign_name: Human-readable campaign name.
        matching_dimensions: Which of the requested dimensions this campaign
            matched on.
        dimension_count: Number of matched dimensions (convenience field).
        similarity_score: Normalised similarity score in [0.0, 1.0].
        take_up_rate: Take-up rate of this campaign as a percentage (0–100).
        total_leads: Total leads distributed for this campaign.
        total_take_up: Total conversions for this campaign.
    """

    campaign_id: str
    campaign_name: str
    matching_dimensions: list[str]
    dimension_count: int
    similarity_score: float
    take_up_rate: float
    total_leads: int
    total_take_up: int


@dataclass
class SimilarCampaignResponse:
    """Response payload for the Similar Campaign finder endpoint.

    Attributes:
        similar_campaigns: Ordered list of similar campaign results,
            most similar first.
    """

    similar_campaigns: list[SimilarCampaignResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@dataclass
class ExportRequest:
    """Request payload for the Export endpoint.

    Attributes:
        page: Identifier of the page/view being exported.
        format: Output file format — one of ``"pdf"``, ``"excel"``,
            ``"csv"``.
        filters: Active filters that were applied on the exported page.
        time_range_start: Start of the exported time range (``yyyy-mm-dd``).
        time_range_end: End of the exported time range (``yyyy-mm-dd``).
    """

    page: str
    format: Literal["pdf", "excel", "csv"]
    filters: list[ActiveFilter]
    time_range_start: str
    time_range_end: str


@dataclass
class ExportResponse:
    """Response payload for the Export endpoint.

    Attributes:
        status: Terminal status of the export job.
        download_url: Pre-signed URL for downloading the export; ``None``
            when the export did not complete successfully.
        error_message: Human-readable error description; ``None`` when the
            export succeeded.
    """

    status: Literal["completed", "timeout", "error"]
    download_url: Optional[str] = None
    error_message: Optional[str] = None
