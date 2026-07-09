"""Regional Rollup ETL job for Campaign Insight Generator.

PySpark Glue job that reads enriched leads from the clean S3 zone,
aggregates performance metrics per campaign, per region, and per week,
and writes the results to the S3 Aggregated Zone as Parquet.

The output feeds the ``regional_performance_agg`` Athena table which
powers the Regional Performance dashboard feature.

Requirements: 4.1, 4.3
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
# Helper functions
# ---------------------------------------------------------------------------


def read_enriched_leads(spark: SparkSession, clean_s3_path: str) -> DataFrame:
    """Read enriched leads Parquet files from the S3 clean zone.

    The leads directory is partitioned by ``campaign_id`` as written by the
    ``raw_to_clean`` Glue job.

    Args:
        spark: Active SparkSession.
        clean_s3_path: Root path of the S3 clean zone (must end with ``/``).

    Returns:
        DataFrame containing all enriched lead records with monitoring
        outcome columns (``take_up_flag``, ``total_transaction_value``, …).
    """
    return spark.read.parquet(f"{clean_s3_path}leads/")


def compute_regional_rollup(leads_df: DataFrame) -> DataFrame:
    """Compute per-campaign, per-region, per-week performance aggregates.

    Transformation steps:

    1. Truncate ``periode_start`` to the Monday of its ISO week using
       ``date_trunc("week", ...)``.
    2. Group by ``(campaign_id, wilayah, week_start)``.
    3. Aggregate:
       - ``leads_count``  — total row count.
       - ``take_up_count`` — rows where ``take_up_flag == 'YES'``.
       - ``avg_transaction_value`` — mean of ``total_transaction_value``.
    4. Derive ``take_up_rate = (take_up_count / leads_count) × 100``,
       defaulting to ``0.0`` when ``leads_count == 0``.
    5. Rename ``wilayah`` to ``region`` for consistency with the Athena
       ``regional_performance_agg`` table schema.

    Args:
        leads_df: Enriched leads DataFrame (output of
            :func:`read_enriched_leads`).

    Returns:
        Aggregated DataFrame with schema matching ``regional_performance_agg``:
        ``campaign_id``, ``region``, ``week_start``, ``leads_count``,
        ``take_up_count``, ``take_up_rate``, ``avg_transaction_value``.
    """
    # Step 1: Derive week_start by truncating periode_start to week boundary.
    leads_with_week = leads_df.withColumn(
        "week_start",
        F.date_trunc("week", F.col("periode_start")),
    )

    # Steps 2–3: Group and aggregate.
    aggregated = leads_with_week.groupBy(
        "campaign_id",
        "wilayah",
        "week_start",
    ).agg(
        F.count("*").alias("leads_count"),
        F.sum(
            F.when(F.upper(F.col("take_up_flag")) == "YES", 1).otherwise(0)
        ).alias("take_up_count"),
        F.avg(F.col("total_transaction_value")).alias("avg_transaction_value"),
    )

    # Step 4: Derive take_up_rate, guarding against zero division.
    aggregated = aggregated.withColumn(
        "take_up_rate",
        F.when(
            F.col("leads_count") > 0,
            (F.col("take_up_count") / F.col("leads_count")) * 100.0,
        ).otherwise(F.lit(0.0)),
    )

    # Step 5: Rename wilayah → region for Athena schema alignment.
    aggregated = aggregated.withColumnRenamed("wilayah", "region")

    return aggregated


def write_regional_rollup(rollup_df: DataFrame, aggregated_s3_path: str) -> None:
    """Write regional rollup aggregates to the S3 Aggregated Zone as Parquet.

    Writes with overwrite mode to replace the full snapshot on each run.

    Args:
        rollup_df: Aggregated regional performance DataFrame.
        aggregated_s3_path: Root path of the S3 Aggregated Zone
            (must end with ``/``).
    """
    (
        rollup_df.write.mode("overwrite")
        .parquet(f"{aggregated_s3_path}regional/")
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the regional rollup Glue job.

    Reads job parameters, initialises the Glue/Spark context, orchestrates
    the ETL pipeline, and commits the job on success.

    Job parameters (resolved via ``getResolvedOptions``):
        JOB_NAME: Glue job name (required by the Glue framework).
        clean_s3_path: S3 path to the clean zone root, e.g.
            ``s3://campaign-datalake/clean/``.
        aggregated_s3_path: S3 path to the aggregated zone root, e.g.
            ``s3://campaign-datalake/aggregated/``.
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
    leads_df = read_enriched_leads(spark, clean_s3_path)

    # --- Transform ---
    rollup_df = compute_regional_rollup(leads_df)

    # --- Load ---
    write_regional_rollup(rollup_df, aggregated_s3_path)

    job.commit()


if __name__ == "__main__":
    main()
