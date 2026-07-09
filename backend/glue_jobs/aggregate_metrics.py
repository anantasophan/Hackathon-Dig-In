"""Aggregate Metrics ETL job for Campaign Insight Generator.

PySpark Glue job that reads the clean campaigns Parquet dataset from S3,
computes pre-aggregated overview metrics grouped by time-period bucket,
product, channel, and region, then writes the results to the S3 Aggregated
Zone as Parquet for low-latency Athena queries.

Requirements: 1.1, 1.7
"""
from __future__ import annotations

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import *  # noqa: F401,F403
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Campaigns whose duration (start_date → end_date, or derived from
# periode_start) is at most this many days are bucketed weekly; longer
# campaigns are bucketed monthly.  Mirrors Requirement 1.7 ("≤3 months"
# treated as 90 days).
_WEEKLY_THRESHOLD_DAYS: int = 90

# ---------------------------------------------------------------------------
# ETL functions
# ---------------------------------------------------------------------------


def read_campaigns(spark: SparkSession, clean_s3_path: str) -> DataFrame:
    """Read the clean campaigns Parquet dataset from S3.

    The campaigns dataset is written by the ``raw_to_clean`` Glue job,
    partitioned by ``year`` and ``month``.

    Args:
        spark: Active SparkSession.
        clean_s3_path: Root path of the S3 clean zone (must end with ``/``).

    Returns:
        DataFrame containing all rows from the campaigns Parquet dataset.
    """
    return spark.read.parquet(f"{clean_s3_path}campaigns/")


def compute_granularity(df: DataFrame) -> DataFrame:
    """Derive ``granularity`` and ``period_bucket`` columns for each row.

    Granularity is determined by the campaign's total duration in days:

    - ≤ 90 days → ``"weekly"`` — ``period_bucket`` is the Monday of the
      week containing ``periode_start`` (ISO week, truncated to ``"week"``).
    - > 90 days → ``"monthly"`` — ``period_bucket`` is the first day of the
      month containing ``periode_start`` (truncated to ``"month"``).

    Campaign duration is computed as ``datediff(end_date, start_date)`` when
    both columns are present and non-null; otherwise it falls back to
    ``datediff(periode_start, periode_start)`` (i.e. 0 days, which correctly
    places single-date entries into the weekly bucket).

    Args:
        df: Clean campaigns DataFrame.

    Returns:
        DataFrame with two additional columns: ``granularity`` (STRING) and
        ``period_bucket`` (DATE).
    """
    # Compute campaign duration. Use start_date/end_date when available,
    # otherwise treat the campaign as a single-day entry (duration = 0).
    has_date_cols = "start_date" in df.columns and "end_date" in df.columns

    if has_date_cols:
        duration_expr = F.coalesce(
            F.datediff(F.col("end_date"), F.col("start_date")),
            F.lit(0),
        )
    else:
        # Fall back to duration = 0; all entries land in the weekly bucket.
        duration_expr = F.lit(0)

    df = df.withColumn("_duration_days", duration_expr)

    # Assign granularity label.
    df = df.withColumn(
        "granularity",
        F.when(
            F.col("_duration_days") <= _WEEKLY_THRESHOLD_DAYS,
            F.lit("weekly"),
        ).otherwise(F.lit("monthly")),
    )

    # Compute the period bucket (start of week or start of month).
    df = df.withColumn(
        "period_bucket",
        F.when(
            F.col("granularity") == "weekly",
            F.date_trunc("week", F.col("periode_start")),
        ).otherwise(
            F.date_trunc("month", F.col("periode_start")),
        ),
    )

    return df.drop("_duration_days")


def compute_period_end(df: DataFrame) -> DataFrame:
    """Derive a ``period_end`` column from ``period_bucket`` and ``granularity``.

    - ``"weekly"`` bucket: ``period_end`` = ``period_bucket + 6 days``
      (Sunday of the same ISO week).
    - ``"monthly"`` bucket: ``period_end`` = last day of the month
      (``next month - 1 day``).

    Args:
        df: DataFrame with ``period_bucket`` and ``granularity`` columns.

    Returns:
        DataFrame with an additional ``period_end`` (DATE) column.
    """
    df = df.withColumn(
        "period_end",
        F.when(
            F.col("granularity") == "weekly",
            F.date_add(F.col("period_bucket"), 6),
        ).otherwise(
            # First day of next month minus 1 day = last day of this month.
            F.date_add(
                F.date_trunc("month", F.add_months(F.col("period_bucket"), 1)),
                -1,
            )
        ),
    )
    return df


def aggregate_overview(df: DataFrame) -> DataFrame:
    """Aggregate campaign metrics into the ``campaign_overview_agg`` shape.

    Groups by ``(period_start, period_end, granularity, product,
    channel, region)`` and computes:

    - ``total_leads``: sum of individual ``total_leads`` values.
    - ``total_take_up``: sum of individual ``total_take_up`` values.
    - ``take_up_rate``: ``(total_take_up / total_leads) × 100``, or ``0``
      when ``total_leads = 0``.
    - ``total_transaction_value``: sum of ``total_transaction_value``.
    - ``campaign_count``: count of distinct ``campaign_id`` values.

    Args:
        df: DataFrame output of :func:`compute_period_end`.

    Returns:
        Aggregated DataFrame matching the ``campaign_overview_agg`` schema.
    """
    grouped = df.groupBy(
        F.col("period_bucket").alias("period_start"),
        F.col("period_end"),
        F.col("granularity"),
        F.col("flag_program").alias("product"),
        F.col("media_blasting").alias("channel"),
        F.col("wilayah").cast("string").alias("region"),
    ).agg(
        F.sum("total_leads").alias("total_leads"),
        F.sum("total_take_up").alias("total_take_up"),
        F.sum("total_transaction_value").alias("total_transaction_value"),
        F.countDistinct("campaign_id").alias("campaign_count"),
    )

    # Compute take_up_rate safely: avoid division by zero.
    grouped = grouped.withColumn(
        "take_up_rate",
        F.when(
            F.col("total_leads") == 0,
            F.lit(0.0),
        ).otherwise(
            (F.col("total_take_up") / F.col("total_leads")) * 100.0
        ),
    )

    # Reorder columns to match the design schema.
    return grouped.select(
        "period_start",
        "period_end",
        "granularity",
        "product",
        "channel",
        "region",
        "total_leads",
        "total_take_up",
        "take_up_rate",
        "total_transaction_value",
        "campaign_count",
    )


def write_overview_agg(agg_df: DataFrame, aggregated_s3_path: str) -> None:
    """Write the aggregated overview table to the S3 Aggregated Zone.

    Writes as Parquet in overwrite mode to
    ``{aggregated_s3_path}overview/``.

    Args:
        agg_df: Aggregated overview DataFrame.
        aggregated_s3_path: Root path of the S3 aggregated zone
            (must end with ``/``).
    """
    (
        agg_df.write.mode("overwrite")
        .parquet(f"{aggregated_s3_path}overview/")
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Glue aggregate-metrics job.

    Reads job parameters, initialises the Glue/Spark context, orchestrates
    the aggregation pipeline, and commits the job on success.
    """
    args = getResolvedOptions(
        sys.argv,
        ["JOB_NAME", "clean_s3_path", "aggregated_s3_path"],
    )

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark: SparkSession = glue_context.spark_session

    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    clean_s3_path: str = args["clean_s3_path"]
    aggregated_s3_path: str = args["aggregated_s3_path"]

    # Ensure paths end with '/' for consistent path construction.
    if not clean_s3_path.endswith("/"):
        clean_s3_path += "/"
    if not aggregated_s3_path.endswith("/"):
        aggregated_s3_path += "/"

    # --- Extract ---
    campaigns_df = read_campaigns(spark, clean_s3_path)

    # --- Transform ---
    campaigns_df = compute_granularity(campaigns_df)
    campaigns_df = compute_period_end(campaigns_df)
    overview_agg = aggregate_overview(campaigns_df)

    # --- Load ---
    write_overview_agg(overview_agg, aggregated_s3_path)

    job.commit()


if __name__ == "__main__":
    main()
