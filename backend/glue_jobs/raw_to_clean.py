"""Raw-to-clean ETL job for Campaign Insight Generator.

PySpark Glue job that reads raw lead files from S3, normalizes and
deduplicates the data, joins with monitoring reports, and writes clean
Parquet files partitioned for efficient Athena queries.

Requirements: 1.1, 3.1, 4.1, 5.1
"""
from __future__ import annotations

import re
import sys
from awsglue.transforms import *  # noqa: F401,F403
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# Schema definition (mirrors LeadRecord in shared/models.py)
# ---------------------------------------------------------------------------

LEADS_SCHEMA = StructType([
    StructField("cif", StringType(), True),
    StructField("nama_program", StringType(), True),
    StructField("jenis_leads", StringType(), True),
    StructField("media_blasting", StringType(), True),
    StructField("periode_start", StringType(), True),   # read as string, parse to date
    StructField("flag_program", StringType(), True),
    StructField("wilayah", IntegerType(), True),
    StructField("cabang", IntegerType(), True),
    StructField("outlet", IntegerType(), True),
    StructField("segment_crs", StringType(), True),
    StructField("segment_by_aum", StringType(), True),
    StructField("segment_wondr", StringType(), True),
    StructField("segment_div_owner", StringType(), True),
    StructField("range_usia", StringType(), True),
    StructField("range_saldo_tab", DoubleType(), True),
    StructField("avg_aum_3_bln", DoubleType(), True),
    StructField("potensi_money", DoubleType(), True),
])

# Monitoring report schema extends LEADS_SCHEMA with outcome fields.
MONITORING_SCHEMA = StructType(
    LEADS_SCHEMA.fields
    + [
        StructField("take_up_flag", StringType(), True),
        StructField("take_up_date", StringType(), True),
        StructField("total_transaction_value", DoubleType(), True),
    ]
)

# Join key used to match leads with monitoring outcomes.
_JOIN_KEYS: list[str] = ["cif", "nama_program", "periode_start"]

# Columns that are uppercased for consistency.
_UPPERCASE_COLS: list[str] = [
    "segment_by_aum",
    "range_usia",
    "flag_program",
    "media_blasting",
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _slugify(value: str) -> str:
    """Convert a string to a URL/filename-safe slug.

    Replaces whitespace runs with underscores and removes every character
    that is not alphanumeric or an underscore.

    Args:
        value: Input string to slugify.

    Returns:
        Slugified version of the input string.

    Examples:
        >>> _slugify("Cashback QRIS 2024-01")
        'Cashback_QRIS_2024-01'
    """
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^\w-]", "", value)
    return value


def read_leads(spark: SparkSession, raw_s3_path: str) -> DataFrame:
    """Read raw leads CSV files from S3.

    Args:
        spark: Active SparkSession.
        raw_s3_path: Root path of the S3 raw zone (must end with ``/``).

    Returns:
        DataFrame with schema matching ``LEADS_SCHEMA``.
    """
    return (
        spark.read.format("csv")
        .option("header", "true")
        .schema(LEADS_SCHEMA)
        .load(f"{raw_s3_path}leads/")
    )


def read_monitoring(spark: SparkSession, raw_s3_path: str) -> DataFrame:
    """Read raw monitoring report CSV files from S3.

    Args:
        spark: Active SparkSession.
        raw_s3_path: Root path of the S3 raw zone (must end with ``/``).

    Returns:
        DataFrame with schema matching ``MONITORING_SCHEMA``.
    """
    return (
        spark.read.format("csv")
        .option("header", "true")
        .schema(MONITORING_SCHEMA)
        .load(f"{raw_s3_path}monitoring_reports/")
    )


def clean_leads(df: DataFrame) -> DataFrame:
    """Apply cleaning and normalization transformations to the leads DataFrame.

    Transformations applied (in order):
    1. Drop rows where ``cif`` is null or empty.
    2. Deduplicate by ``(cif, nama_program, periode_start)`` — keep first.
    3. Uppercase ``segment_by_aum``, ``range_usia``, ``flag_program``,
       ``media_blasting``.
    4. Parse ``periode_start`` to ``yyyy-MM-dd`` date string.
    5. Add ``campaign_id`` derived from ``nama_program`` and ``periode_start``.
    6. Add ``year`` and ``month`` partition columns from ``periode_start``.

    Args:
        df: Raw leads DataFrame.

    Returns:
        Cleaned and normalized leads DataFrame.
    """
    # 1. Drop rows with null or empty cif.
    df = df.filter(
        F.col("cif").isNotNull() & (F.trim(F.col("cif")) != "")
    )

    # 2. Deduplicate — keep first occurrence per natural key.
    window_spec = (
        __import__("pyspark.sql.window", fromlist=["Window"])
        .Window.partitionBy("cif", "nama_program", "periode_start")
        .orderBy(F.monotonically_increasing_id())
    )
    df = (
        df.withColumn("_row_num", F.row_number().over(window_spec))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    # 3. Normalize string columns to uppercase.
    for col_name in _UPPERCASE_COLS:
        df = df.withColumn(col_name, F.upper(F.col(col_name)))

    # 4. Standardize periode_start: parse multiple date formats → yyyy-MM-dd.
    #    F.to_date tries the formats in order; coalesce returns the first non-null.
    df = df.withColumn(
        "periode_start",
        F.coalesce(
            F.to_date(F.col("periode_start"), "yyyy-MM-dd"),
            F.to_date(F.col("periode_start"), "dd/MM/yyyy"),
            F.to_date(F.col("periode_start"), "dd-MM-yyyy"),
            F.to_date(F.col("periode_start"), "yyyy/MM/dd"),
            F.to_date(F.col("periode_start"), "MM/dd/yyyy"),
        ),
    )

    # 5. Build campaign_id: "<nama_program>_<periode_start>" slugified.
    #    Using a UDF-free approach: concat then apply regexp_replace.
    raw_campaign_id = F.concat(
        F.col("nama_program"),
        F.lit("_"),
        F.date_format(F.col("periode_start"), "yyyy-MM-dd"),
    )
    # Replace spaces with underscores, then strip non-word/dash characters.
    campaign_id = F.regexp_replace(
        F.regexp_replace(raw_campaign_id, r"\s+", "_"),
        r"[^\w\-]",
        "",
    )
    df = df.withColumn("campaign_id", campaign_id)

    # 6. Add year/month partition columns for campaign master output.
    df = df.withColumn("year", F.year(F.col("periode_start")))
    df = df.withColumn("month", F.month(F.col("periode_start")))

    return df


def join_monitoring(leads_df: DataFrame, monitoring_df: DataFrame) -> DataFrame:
    """Left join leads with monitoring report outcomes.

    Joins on ``(cif, nama_program, periode_start)`` and computes:
    - ``time_to_take_up_days``: calendar days from ``periode_start`` to
      ``take_up_date``.
    - ``take_up_flag``: defaults to ``"NO"`` when null (no take-up recorded).

    Args:
        leads_df: Cleaned leads DataFrame (output of :func:`clean_leads`).
        monitoring_df: Raw monitoring DataFrame (output of
            :func:`read_monitoring`).

    Returns:
        Enriched DataFrame with monitoring columns appended.
    """
    # Select and rename only the outcome columns from monitoring to avoid
    # duplicate column names after the join.
    monitoring_slim = monitoring_df.select(
        "cif",
        "nama_program",
        "periode_start",
        F.col("take_up_flag").alias("mon_take_up_flag"),
        F.to_date(
            F.coalesce(
                F.to_date(F.col("take_up_date"), "yyyy-MM-dd"),
                F.to_date(F.col("take_up_date"), "dd/MM/yyyy"),
                F.to_date(F.col("take_up_date"), "dd-MM-yyyy"),
                F.to_date(F.col("take_up_date"), "yyyy/MM/dd"),
                F.to_date(F.col("take_up_date"), "MM/dd/yyyy"),
            )
        ).alias("take_up_date_parsed"),
        F.col("total_transaction_value").alias("total_transaction_value"),
    )

    enriched = leads_df.join(monitoring_slim, on=_JOIN_KEYS, how="left")

    # Compute days from campaign start to take-up.
    enriched = enriched.withColumn(
        "time_to_take_up_days",
        F.datediff(F.col("take_up_date_parsed"), F.col("periode_start")),
    )

    # Rename parsed take_up_date back and default take_up_flag to "NO".
    enriched = (
        enriched.withColumnRenamed("take_up_date_parsed", "take_up_date")
        .withColumn(
            "take_up_flag",
            F.when(F.col("mon_take_up_flag").isNull(), F.lit("NO"))
            .otherwise(F.upper(F.col("mon_take_up_flag"))),
        )
        .drop("mon_take_up_flag")
    )

    return enriched


def build_campaign_master(enriched_df: DataFrame) -> DataFrame:
    """Aggregate leads data into a campaign-level master table.

    Groups by campaign dimensions and computes:
    - ``total_leads``: count of leads in the campaign group.
    - ``total_take_up``: count where ``take_up_flag == 'YES'``.
    - ``take_up_rate``: ``(total_take_up / total_leads) × 100``.
    - ``total_transaction_value``: sum of ``total_transaction_value``.
    - ``avg_time_to_take_up_days``: mean days to take-up (nulls excluded).

    Args:
        enriched_df: Enriched leads DataFrame with monitoring columns.

    Returns:
        Campaign master DataFrame partitioned by ``year`` and ``month``.
    """
    campaign_master = enriched_df.groupBy(
        "campaign_id",
        "nama_program",
        "flag_program",
        "jenis_leads",
        "media_blasting",
        "wilayah",
        "periode_start",
        "year",
        "month",
    ).agg(
        F.count("*").alias("total_leads"),
        F.sum(
            F.when(F.upper(F.col("take_up_flag")) == "YES", 1).otherwise(0)
        ).alias("total_take_up"),
        F.sum(F.col("total_transaction_value")).alias("total_transaction_value"),
        F.avg(F.col("time_to_take_up_days")).alias("avg_time_to_take_up_days"),
    )

    campaign_master = campaign_master.withColumn(
        "take_up_rate",
        F.when(
            F.col("total_leads") > 0,
            (F.col("total_take_up") / F.col("total_leads")) * 100.0,
        ).otherwise(F.lit(0.0)),
    )

    return campaign_master


def write_leads(enriched_df: DataFrame, clean_s3_path: str) -> None:
    """Write enriched leads to the S3 clean zone as Parquet.

    Partitions by ``campaign_id`` for efficient per-campaign Athena scans.

    Args:
        enriched_df: Enriched leads DataFrame.
        clean_s3_path: Root path of the S3 clean zone (must end with ``/``).
    """
    (
        enriched_df.write.mode("overwrite")
        .partitionBy("campaign_id")
        .parquet(f"{clean_s3_path}leads/")
    )


def write_campaign_master(campaign_master: DataFrame, clean_s3_path: str) -> None:
    """Write campaign master aggregates to the S3 clean zone as Parquet.

    Partitions by ``year`` and ``month`` for efficient date-range Athena scans.

    Args:
        campaign_master: Campaign master aggregated DataFrame.
        clean_s3_path: Root path of the S3 clean zone (must end with ``/``).
    """
    (
        campaign_master.write.mode("overwrite")
        .partitionBy("year", "month")
        .parquet(f"{clean_s3_path}campaigns/")
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Glue job.

    Reads job parameters, initialises the Glue/Spark context, orchestrates
    the ETL pipeline, and commits the job on success.
    """
    args = getResolvedOptions(
        sys.argv,
        ["JOB_NAME", "raw_s3_path", "clean_s3_path", "database_name"],
    )

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark: SparkSession = glue_context.spark_session

    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    raw_s3_path: str = args["raw_s3_path"]
    clean_s3_path: str = args["clean_s3_path"]

    # Ensure paths end with '/' for consistent path construction.
    if not raw_s3_path.endswith("/"):
        raw_s3_path += "/"
    if not clean_s3_path.endswith("/"):
        clean_s3_path += "/"

    # --- Extract ---
    leads_raw = read_leads(spark, raw_s3_path)
    monitoring_raw = read_monitoring(spark, raw_s3_path)

    # --- Transform ---
    leads_clean = clean_leads(leads_raw)
    enriched = join_monitoring(leads_clean, monitoring_raw)
    campaign_master = build_campaign_master(enriched)

    # --- Load ---
    write_leads(enriched, clean_s3_path)
    write_campaign_master(campaign_master, clean_s3_path)

    job.commit()


if __name__ == "__main__":
    main()
