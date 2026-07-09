"""Shared data models for Campaign Insight Generator."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

PII_FIELDS: frozenset[str] = frozenset({"cif"})
VALID_MEDIA_BLASTING: frozenset[str] = frozenset({"wa", "digisales", "telesales", "email", "push notif", "sms"})
VALID_FLAG_PROGRAM: frozenset[str] = frozenset({"PROGRAM BIAYA ADMIN", "PROGRAM QRIS"})
VALID_SEGMENT_BY_AUM: frozenset[str] = frozenset({"UPPERMASS", "EMERALD", "MASS", "AFFLUENT", "PRIVATE", "HIGH AFFLUENT"})
VALID_RANGE_USIA: frozenset[str] = frozenset({"BABY BOOMER", "GEN X", "GEN Y", "GEN Z", "GEN ALPHA"})
VALID_SEGMENT_DIV_OWNER: frozenset[str] = frozenset({"CRS", "WEM (Perorangan)"})
SIMILAR_CAMPAIGN_DIMENSIONS: frozenset[str] = frozenset({"media_blasting", "jenis_leads", "flag_program"})

@dataclass
class ActiveFilter:
    field: str
    values: list[str] = field(default_factory=list)

@dataclass
class CampaignOverviewRequest:
    start_date: str
    end_date: str
    flag_program: Optional[list[str]] = None
    media_blasting: Optional[list[str]] = None
    wilayah: Optional[list[int]] = None
    jenis_leads: Optional[list[str]] = None

@dataclass
class TrendDataPoint:
    period_start: str
    period_end: str
    take_up_rate: float
    total_leads: int
    total_take_up: int

@dataclass
class CampaignOverviewResponse:
    total_leads: int
    total_take_up: int
    take_up_rate: float
    total_campaigns: int
    trend: list[TrendDataPoint] = field(default_factory=list)
    filters: list[ActiveFilter] = field(default_factory=list)

@dataclass
class CampaignComparisonRequest:
    campaign_ids: list[str]
    group_by: Optional[Literal["flag_program", "wilayah", "media_blasting"]] = None
    def __post_init__(self) -> None:
        if len(self.campaign_ids) < 2:
            raise ValueError(f"campaign_ids must contain at least 2, got {len(self.campaign_ids)}")
        if len(self.campaign_ids) > 5:
            raise ValueError(f"campaign_ids must contain at most 5, got {len(self.campaign_ids)}")

@dataclass
class CampaignMetric:
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
    campaigns: list[CampaignMetric] = field(default_factory=list)
    comparison_chart: dict = field(default_factory=dict)

@dataclass
class SimilarCampaignRequest:
    reference_campaign_id: str
    dimensions: list[Literal["media_blasting", "jenis_leads", "flag_program"]]
    limit: Optional[int] = 20

@dataclass
class SimilarCampaignResult:
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
    similar_campaigns: list[SimilarCampaignResult] = field(default_factory=list)

@dataclass
class ExportRequest:
    page: str
    format: Literal["pdf", "excel", "csv"]
    filters: list[ActiveFilter]
    time_range_start: str
    time_range_end: str

@dataclass
class ExportResponse:
    status: Literal["completed", "timeout", "error"]
    download_url: Optional[str] = None
    error_message: Optional[str] = None
