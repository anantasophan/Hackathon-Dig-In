"""Mock data store for the Local Development Server.

Loads all five JSON data files at import time and exposes typed query
methods used by the FastAPI routers.  All query methods apply AND-logic
filtering — every provided filter must be satisfied by a record for that
record to be included in the result.

No AWS dependencies.  No PII (leads.json intentionally excludes ``cif``).

Requirements: 2.3, 2.4, 2.5, 2.6, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_DATA_DIR: Path = Path(__file__).parent / "mock_data"

_CAMPAIGNS_FILE: Path = _DATA_DIR / "campaigns.json"
_LEADS_FILE: Path = _DATA_DIR / "leads.json"
_SIMILARITY_INDEX_FILE: Path = _DATA_DIR / "similarity_index.json"
_TREND_DATA_FILE: Path = _DATA_DIR / "trend_data.json"
_REGIONAL_WEEKLY_FILE: Path = _DATA_DIR / "regional_weekly.json"


# ---------------------------------------------------------------------------
# MockDataStore
# ---------------------------------------------------------------------------


class MockDataStore:
    """In-memory data store backed by JSON fixture files.

    All JSON files are loaded once during ``__init__`` and cached as
    instance attributes.  Query methods return new lists — they never
    mutate the cached data.

    Attributes:
        _campaigns: List of campaign master-data dicts loaded from
            ``campaigns.json``.
        _leads: List of lead record dicts loaded from ``leads.json``.
        _similarity_index: List of pre-computed similarity-pair dicts
            loaded from ``similarity_index.json``.
        _trend_data: Dict keyed by ``campaign_id`` containing lists of
            weekly trend entry dicts, loaded from ``trend_data.json``.
        _regional_weekly: Dict keyed by ``campaign_id`` containing lists
            of per-region weekly entry dicts, loaded from
            ``regional_weekly.json``.
    """

    def __init__(self) -> None:
        """Load all five JSON data files into memory."""
        self._campaigns: list[dict[str, Any]] = self._load_json(_CAMPAIGNS_FILE)
        self._leads: list[dict[str, Any]] = self._load_json(_LEADS_FILE)
        self._similarity_index: list[dict[str, Any]] = self._load_json(
            _SIMILARITY_INDEX_FILE
        )
        self._trend_data: dict[str, list[dict[str, Any]]] = self._load_json(
            _TREND_DATA_FILE
        )
        self._regional_weekly: dict[str, list[dict[str, Any]]] = self._load_json(
            _REGIONAL_WEEKLY_FILE
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> Any:
        """Load and parse a JSON file.

        Args:
            path: Absolute path to the JSON file.

        Returns:
            Parsed JSON value (list or dict depending on file).

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_leads(
        self,
        campaign_id: str | None = None,
        flag_program: list[str] | None = None,
        media_blasting: list[str] | None = None,
        wilayah: list[int] | None = None,
        jenis_leads: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return lead records matching all provided filters (AND logic).

        Each keyword argument, when provided, adds an additional filter
        predicate.  Only records satisfying *all* active predicates are
        included in the result.

        Date filtering uses the ``periode_start`` field on each lead
        record.  Records whose ``periode_start`` falls outside
        ``[start_date, end_date]`` (inclusive) are excluded.

        Args:
            campaign_id: Exact-match filter on the ``campaign_id`` field.
            flag_program: Inclusion filter — the record's ``flag_program``
                value must be contained in this list.
            media_blasting: Inclusion filter — the record's
                ``media_blasting`` value must be contained in this list.
            wilayah: Inclusion filter — the record's ``wilayah`` integer
                value must be contained in this list.
            jenis_leads: Inclusion filter — the record's ``jenis_leads``
                value must be contained in this list.
            start_date: ISO 8601 date string (``yyyy-mm-dd``).  Records
                with ``periode_start`` earlier than this value are excluded.
            end_date: ISO 8601 date string (``yyyy-mm-dd``).  Records
                with ``periode_start`` later than this value are excluded.

        Returns:
            A new list of lead record dicts satisfying all active filters.
            Returns all leads when no arguments are provided.

        Examples:
            >>> store = MockDataStore()
            >>> results = store.get_leads(campaign_id="C001")
            >>> all(r["campaign_id"] == "C001" for r in results)
            True

            >>> results = store.get_leads(
            ...     flag_program=["PROGRAM QRIS"],
            ...     media_blasting=["wa"],
            ... )
            >>> all(
            ...     r["flag_program"] == "PROGRAM QRIS"
            ...     and r["media_blasting"] == "wa"
            ...     for r in results
            ... )
            True
        """
        results: list[dict[str, Any]] = []

        # Case-insensitive comparison sets, built once per call. Filtering
        # on free-text / mixed-case fields (flag_program, media_blasting,
        # jenis_leads) would otherwise silently drop everything when the
        # caller's casing does not exactly match the stored casing.
        flag_program_lower = (
            {v.lower() for v in flag_program} if flag_program is not None else None
        )
        media_blasting_lower = (
            {v.lower() for v in media_blasting} if media_blasting is not None else None
        )
        jenis_leads_lower = (
            {v.lower() for v in jenis_leads} if jenis_leads is not None else None
        )

        for lead in self._leads:
            # --- campaign_id: exact match ---
            if campaign_id is not None and lead.get("campaign_id") != campaign_id:
                continue

            # --- flag_program: value in list (case-insensitive) ---
            if flag_program_lower is not None:
                value = str(lead.get("flag_program") or "").lower()
                if value not in flag_program_lower:
                    continue

            # --- media_blasting: value in list (case-insensitive) ---
            if media_blasting_lower is not None:
                value = str(lead.get("media_blasting") or "").lower()
                if value not in media_blasting_lower:
                    continue

            # --- wilayah: value in list (int comparison) ---
            if wilayah is not None and lead.get("wilayah") not in wilayah:
                continue

            # --- jenis_leads: value in list (case-insensitive) ---
            if jenis_leads_lower is not None:
                value = str(lead.get("jenis_leads") or "").lower()
                if value not in jenis_leads_lower:
                    continue

            # --- date range: filter on periode_start (inclusive) ---
            periode = lead.get("periode_start")
            if start_date is not None and isinstance(periode, str):
                if periode < start_date:
                    continue
            if end_date is not None and isinstance(periode, str):
                if periode > end_date:
                    continue

            results.append(lead)

        return results

    def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        """Return the campaign master record for the given ID, or ``None``.

        Args:
            campaign_id: The campaign identifier to look up (e.g. ``"C001"``).

        Returns:
            The matching campaign dict, or ``None`` if not found.

        Examples:
            >>> store = MockDataStore()
            >>> camp = store.get_campaign("C001")
            >>> camp is not None and camp["campaign_id"] == "C001"
            True

            >>> store.get_campaign("DOES_NOT_EXIST") is None
            True
        """
        for campaign in self._campaigns:
            if campaign.get("campaign_id") == campaign_id:
                return campaign
        return None

    def get_all_campaigns(self) -> list[dict[str, Any]]:
        """Return a copy of all campaign master records.

        Returns:
            A new list containing all campaign dicts from
            ``campaigns.json``.

        Examples:
            >>> store = MockDataStore()
            >>> camps = store.get_all_campaigns()
            >>> len(camps) == 5
            True
        """
        return list(self._campaigns)

    def get_similarity_index(self, reference_id: str) -> list[dict[str, Any]]:
        """Return pre-computed similarity entries for a reference campaign.

        Only entries where ``campaign_id`` matches ``reference_id`` are
        returned.  The symmetric counterpart entries (where the reference
        is the *similar* campaign) are **not** included; call this method
        with the other campaign ID to retrieve those.

        Args:
            reference_id: The campaign ID to use as the reference
                (i.e. filter on the ``campaign_id`` field, not
                ``similar_campaign_id``).

        Returns:
            A new list of similarity-pair dicts whose ``campaign_id``
            equals ``reference_id``.  Returns an empty list if no entries
            are found.

        Examples:
            >>> store = MockDataStore()
            >>> pairs = store.get_similarity_index("C001")
            >>> all(p["campaign_id"] == "C001" for p in pairs)
            True
        """
        return [
            entry
            for entry in self._similarity_index
            if entry.get("campaign_id") == reference_id
        ]

    def get_trend_data(self, campaign_id: str) -> list[dict[str, Any]]:
        """Return the weekly trend entries for a campaign.

        Args:
            campaign_id: The campaign identifier to look up.

        Returns:
            A list of weekly trend dicts (with keys ``period_start``,
            ``period_end``, ``total_leads``, ``total_take_up``,
            ``take_up_rate``).  Returns an empty list when ``campaign_id``
            is not present in the trend data.

        Examples:
            >>> store = MockDataStore()
            >>> trend = store.get_trend_data("C001")
            >>> len(trend) >= 4
            True

            >>> store.get_trend_data("UNKNOWN")
            []
        """
        return list(self._trend_data.get(campaign_id, []))

    def get_regional_weekly(self, campaign_id: str) -> list[dict[str, Any]]:
        """Return per-region weekly data entries for a campaign.

        Args:
            campaign_id: The campaign identifier to look up.

        Returns:
            A list of regional weekly dicts (with keys ``wilayah``,
            ``week_start``, ``leads_count``, ``take_up_count``,
            ``take_up_rate``).  Returns an empty list when ``campaign_id``
            is not present in the regional weekly data.

        Examples:
            >>> store = MockDataStore()
            >>> rw = store.get_regional_weekly("C001")
            >>> len(rw) > 0
            True

            >>> store.get_regional_weekly("UNKNOWN")
            []
        """
        return list(self._regional_weekly.get(campaign_id, []))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

store = MockDataStore()
