"""Athena query helper for Campaign Insight Generator.

Wraps boto3 Athena client with parameterized query execution, poll-until-done
logic, and query-builder methods for each analytical view.

Requirements: 1.2, 2.1, 3.1, 4.1, 5.1
"""

from __future__ import annotations

import time
from typing import Any

import boto3

from shared.models import CampaignOverviewRequest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POLL_INTERVAL_SECONDS: float = 1.0
_QUERY_TIMEOUT_SECONDS: int = 30

# Terminal query-execution states reported by Athena.
_SUCCEEDED: str = "SUCCEEDED"
_FAILED: str = "FAILED"
_CANCELLED: str = "CANCELLED"
_TERMINAL_STATES: frozenset[str] = frozenset({_SUCCEEDED, _FAILED, _CANCELLED})


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class QueryTimeoutError(Exception):
    """Raised when an Athena query does not complete within the timeout window.

    Attributes:
        query_execution_id: The Athena query execution ID that timed out.
        timeout_seconds: The timeout limit that was exceeded.
    """

    def __init__(self, query_execution_id: str, timeout_seconds: int) -> None:
        self.query_execution_id = query_execution_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Athena query {query_execution_id!r} did not complete within "
            f"{timeout_seconds} seconds."
        )


class QueryExecutionError(Exception):
    """Raised when Athena reports a FAILED or CANCELLED query state.

    Attributes:
        query_execution_id: The Athena query execution ID that failed.
        state: The terminal Athena state (``"FAILED"`` or ``"CANCELLED"``).
        reason: Human-readable reason returned by Athena, if available.
    """

    def __init__(
        self,
        query_execution_id: str,
        state: str,
        reason: str = "",
    ) -> None:
        self.query_execution_id = query_execution_id
        self.state = state
        self.reason = reason
        super().__init__(
            f"Athena query {query_execution_id!r} ended with state {state!r}"
            + (f": {reason}" if reason else "")
        )


# ---------------------------------------------------------------------------
# AthenaClient
# ---------------------------------------------------------------------------


class AthenaClient:
    """Wrapper around the boto3 Athena client for the Campaign Insight Generator.

    Usage::

        client = AthenaClient(
            database="campaign_db",
            s3_output_location="s3://my-bucket/athena-results/",
        )
        rows = client.execute_query("SELECT * FROM campaign WHERE campaign_id = :id",
                                    {"id": "C001"})

    Args:
        database: Athena database name to run queries against.
        s3_output_location: S3 URI where Athena writes query results.
        region_name: AWS region for the boto3 session.  Defaults to the
            environment / instance-profile region when ``None``.
        workgroup: Athena workgroup name.  Defaults to ``"primary"``.
    """

    def __init__(
        self,
        database: str,
        s3_output_location: str,
        region_name: str | None = None,
        workgroup: str = "primary",
    ) -> None:
        self._database = database
        self._s3_output_location = s3_output_location
        self._workgroup = workgroup

        session_kwargs: dict[str, Any] = {}
        if region_name is not None:
            session_kwargs["region_name"] = region_name

        self._client = boto3.client("athena", **session_kwargs)

    # ------------------------------------------------------------------
    # Public: query execution
    # ------------------------------------------------------------------

    def execute_query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a parameterized Athena SQL query and return the result rows.

        Parameter substitution uses a simple named-placeholder scheme: every
        occurrence of ``:name`` in *sql* is replaced by the corresponding
        value from *params* after safe quoting.  This avoids f-string
        injection while remaining compatible with Athena's standard SQL
        syntax (which does not support native bind parameters).

        Args:
            sql: SQL statement, optionally containing ``:param_name``
                placeholders.
            params: Dictionary of parameter names to values.  String values
                are single-quoted and escaped; numeric values are inlined
                as-is.

        Returns:
            A list of dicts mapping column name → value for each result row.

        Raises:
            QueryTimeoutError: If the query does not reach a terminal state
                within :data:`_QUERY_TIMEOUT_SECONDS` seconds.
            QueryExecutionError: If Athena reports ``FAILED`` or
                ``CANCELLED`` for the query.
        """
        final_sql = _bind_params(sql, params or {})

        start_response = self._client.start_query_execution(
            QueryString=final_sql,
            QueryExecutionContext={"Database": self._database},
            ResultConfiguration={"OutputLocation": self._s3_output_location},
            WorkGroup=self._workgroup,
        )
        execution_id: str = start_response["QueryExecutionId"]

        self._wait_for_completion(execution_id)
        return self._fetch_results(execution_id)

    # ------------------------------------------------------------------
    # Public: query builders
    # ------------------------------------------------------------------

    def build_campaign_overview_query(
        self, request: CampaignOverviewRequest
    ) -> str:
        """Build a parameterized SQL query for the Campaign Overview endpoint.

        Queries the ``campaign_overview_agg`` pre-computed aggregate table,
        filtering by the mandatory date range and any optional
        product/channel/region filters present in *request*.

        Args:
            request: A :class:`~shared.models.CampaignOverviewRequest`
                instance with the desired filter criteria.

        Returns:
            A fully-formed SQL string (values already inlined safely) ready
            to be passed to :meth:`execute_query` without further params.
        """
        conditions: list[str] = [
            f"period_start >= {_quote(request.start_date)}",
            f"period_end <= {_quote(request.end_date)}",
        ]

        if request.flag_program:
            conditions.append(_in_clause("product", request.flag_program))

        if request.media_blasting:
            conditions.append(_in_clause("channel", request.media_blasting))

        if request.wilayah:
            # wilayah is a list of ints — convert to strings for the IN clause
            conditions.append(
                _in_clause("region", [str(w) for w in request.wilayah])
            )

        if request.jenis_leads:
            # jenis_leads doesn't map to a column in campaign_overview_agg;
            # include as a sub_product filter for forward compatibility.
            conditions.append(_in_clause("sub_product", request.jenis_leads))

        where_clause = " AND ".join(conditions)

        return (
            "SELECT\n"
            "    period_start,\n"
            "    period_end,\n"
            "    granularity,\n"
            "    product,\n"
            "    channel,\n"
            "    region,\n"
            "    total_leads,\n"
            "    total_take_up,\n"
            "    take_up_rate,\n"
            "    total_transaction_value,\n"
            "    campaign_count\n"
            "FROM campaign_overview_agg\n"
            f"WHERE {where_clause}\n"
            "ORDER BY period_start ASC"
        )

    def build_comparison_query(self, campaign_ids: list[str]) -> str:
        """Build SQL to fetch the 5 comparison metrics for the given campaigns.

        Queries the ``campaign`` table and returns one row per campaign with
        the five metrics required by Requirement 2.1:

        - ``total_leads``
        - ``total_take_up``
        - ``take_up_rate``
        - ``total_transaction_value``
        - ``duration_days`` (derived from ``start_date``/``end_date``)

        Args:
            campaign_ids: List of campaign ID strings to include.

        Returns:
            SQL string with campaign IDs safely inlined.
        """
        in_clause = _in_clause("campaign_id", campaign_ids)

        return (
            "SELECT\n"
            "    campaign_id,\n"
            "    campaign_name,\n"
            "    total_leads,\n"
            "    total_take_up,\n"
            "    take_up_rate,\n"
            "    total_transaction_value,\n"
            "    date_diff('day', start_date, end_date) AS duration_days\n"
            "FROM campaign\n"
            f"WHERE {in_clause}\n"
            "ORDER BY campaign_id ASC"
        )

    def build_regional_query(self, campaign_id: str) -> str:
        """Build SQL for regional performance metrics for a given campaign.

        Queries the ``regional_performance_agg`` pre-computed aggregate table,
        returning per-region metrics as required by Requirement 4.1:
        ``leads_count``, ``take_up_count``, ``take_up_rate``.

        Args:
            campaign_id: Campaign identifier to filter by.

        Returns:
            SQL string with campaign_id safely inlined.
        """
        return (
            "SELECT\n"
            "    campaign_id,\n"
            "    region,\n"
            "    SUM(leads_count) AS leads_count,\n"
            "    SUM(take_up_count) AS take_up_count,\n"
            "    CAST(\n"
            "        CASE\n"
            "            WHEN SUM(leads_count) = 0 THEN 0.0\n"
            "            ELSE SUM(take_up_count) * 100.0 / SUM(leads_count)\n"
            "        END AS DOUBLE\n"
            "    ) AS take_up_rate,\n"
            "    AVG(avg_transaction_value) AS avg_transaction_value\n"
            "FROM regional_performance_agg\n"
            f"WHERE campaign_id = {_quote(campaign_id)}\n"
            "GROUP BY campaign_id, region\n"
            "ORDER BY take_up_rate DESC"
        )

    def build_time_analysis_query(self, campaign_id: str) -> str:
        """Build SQL for time-to-take-up analysis for a given campaign.

        Queries the ``leads`` table and returns the raw fields needed to build
        the take-up timing histogram (Requirement 3.1):
        ``distribution_date``, ``take_up_date``, ``channel``, ``region``,
        ``time_to_take_up_days``.

        Only rows where ``take_up_flag = true`` are included so that
        histogram computation only considers actual conversions.

        Args:
            campaign_id: Campaign identifier to filter by.

        Returns:
            SQL string with campaign_id safely inlined.
        """
        return (
            "SELECT\n"
            "    distribution_date,\n"
            "    take_up_date,\n"
            "    channel,\n"
            "    region,\n"
            "    time_to_take_up_days\n"
            "FROM leads\n"
            f"WHERE campaign_id = {_quote(campaign_id)}\n"
            "  AND take_up_flag = true\n"
            "  AND take_up_date IS NOT NULL\n"
            "ORDER BY distribution_date ASC"
        )

    def build_customer_criteria_query(self, campaign_id: str) -> str:
        """Build SQL for customer criteria / demographic analysis.

        Queries the ``leads`` table and returns the customer attribute columns
        needed for Requirement 5.1:
        ``customer_segment``, ``age_group``, ``domicile_region``,
        ``product_holding``, ``balance_category``, ``take_up_flag``,
        ``transaction_value``.

        Args:
            campaign_id: Campaign identifier to filter by.

        Returns:
            SQL string with campaign_id safely inlined.
        """
        return (
            "SELECT\n"
            "    customer_segment,\n"
            "    age_group,\n"
            "    domicile_region,\n"
            "    product_holding,\n"
            "    balance_category,\n"
            "    take_up_flag,\n"
            "    transaction_value\n"
            "FROM leads\n"
            f"WHERE campaign_id = {_quote(campaign_id)}\n"
            "ORDER BY customer_segment ASC"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wait_for_completion(self, execution_id: str) -> None:
        """Poll Athena until the query reaches a terminal state or times out.

        Args:
            execution_id: The Athena query execution ID to monitor.

        Raises:
            QueryTimeoutError: If the query is still running after
                :data:`_QUERY_TIMEOUT_SECONDS` seconds.
            QueryExecutionError: If Athena reports ``FAILED`` or
                ``CANCELLED``.
        """
        elapsed: float = 0.0

        while elapsed < _QUERY_TIMEOUT_SECONDS:
            response = self._client.get_query_execution(
                QueryExecutionId=execution_id
            )
            state: str = (
                response["QueryExecution"]["Status"]["State"]
            )

            if state == _SUCCEEDED:
                return

            if state in (_FAILED, _CANCELLED):
                reason: str = (
                    response["QueryExecution"]["Status"]
                    .get("StateChangeReason", "")
                )
                raise QueryExecutionError(execution_id, state, reason)

            # Still running — wait before polling again.
            time.sleep(_POLL_INTERVAL_SECONDS)
            elapsed += _POLL_INTERVAL_SECONDS

        # Timed out — attempt to cancel the query to avoid orphaned runs.
        try:
            self._client.stop_query_execution(QueryExecutionId=execution_id)
        except Exception:  # noqa: BLE001
            pass  # Best-effort cancellation; timeout error is primary concern.

        raise QueryTimeoutError(execution_id, _QUERY_TIMEOUT_SECONDS)

    def _fetch_results(self, execution_id: str) -> list[dict[str, Any]]:
        """Retrieve query results and convert them to a list of row dicts.

        Paginates through all result pages using the ``NextToken`` mechanism
        so that large result sets are fully retrieved.

        Args:
            execution_id: The Athena query execution ID whose results to fetch.

        Returns:
            A list of dicts mapping each column name to its string value for
            that row.  The header row is excluded from the returned data.
        """
        rows: list[dict[str, Any]] = []
        next_token: str | None = None
        column_names: list[str] = []

        while True:
            kwargs: dict[str, Any] = {"QueryExecutionId": execution_id}
            if next_token is not None:
                kwargs["NextToken"] = next_token

            response = self._client.get_query_results(**kwargs)
            result_set = response["ResultSet"]
            result_rows = result_set["Rows"]

            if not column_names:
                # The first row of the very first page is always the column header.
                column_names = [
                    col["VarCharValue"]
                    for col in result_rows[0]["Data"]
                ]
                data_rows = result_rows[1:]
            else:
                data_rows = result_rows

            for row in data_rows:
                cell_values = [
                    cell.get("VarCharValue", None) for cell in row["Data"]
                ]
                rows.append(dict(zip(column_names, cell_values)))

            next_token = response.get("NextToken")
            if next_token is None:
                break

        return rows


# ---------------------------------------------------------------------------
# Module-level helpers (private)
# ---------------------------------------------------------------------------


def _quote(value: str) -> str:
    """Return *value* as a safely single-quoted SQL string literal.

    Single-quotes inside the value are escaped by doubling them, which is
    the standard SQL escaping mechanism supported by Athena / Presto.

    Args:
        value: Raw string value to quote.

    Returns:
        Single-quoted SQL string, e.g. ``"'O''Brien'"`` for input
        ``"O'Brien"``.
    """
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _in_clause(column: str, values: list[str]) -> str:
    """Build a SQL ``IN (…)`` condition for *column* from a list of string values.

    Each value is individually single-quoted via :func:`_quote`.

    Args:
        column: Column name (already trusted — comes from internal callers only).
        values: List of string values.  An empty list produces a tautologically
            false condition ``(1 = 0)`` so that queries with empty IN lists do
            not inadvertently return all rows.

    Returns:
        SQL snippet, e.g. ``"channel IN ('sms', 'email')"``.
    """
    if not values:
        return "(1 = 0)"  # Always-false: empty IN list matches nothing

    quoted_values = ", ".join(_quote(v) for v in values)
    return f"{column} IN ({quoted_values})"


def _bind_params(sql: str, params: dict[str, Any]) -> str:
    """Replace ``:name`` placeholders in *sql* with safely-quoted values.

    Replacement is performed longest-key-first to avoid a shorter key
    (e.g. ``:id``) accidentally matching the prefix of a longer key
    (e.g. ``:id_list``).

    String values are single-quoted and escaped; numeric values (``int``,
    ``float``) are inlined as-is.

    Args:
        sql: SQL template containing ``:name`` placeholders.
        params: Mapping of placeholder names to replacement values.

    Returns:
        SQL string with all placeholders substituted.
    """
    if not params:
        return sql

    result = sql
    # Process keys from longest to shortest to prevent prefix collisions.
    for key in sorted(params.keys(), key=len, reverse=True):
        value = params[key]
        if isinstance(value, bool):
            replacement = "true" if value else "false"
        elif isinstance(value, (int, float)):
            replacement = str(value)
        else:
            replacement = _quote(str(value))
        result = result.replace(f":{key}", replacement)

    return result
