"""Glue ETL Job: Similarity Index.

PySpark job that computes pairwise campaign similarity based on three
dimensions (media_blasting, jenis_leads, flag_program) and writes
the resulting similarity index to DynamoDB CampaignSimilarityIndex.

Each pair (A, B) where A < B is stored in both directions so that
a query by either campaign_id returns all its similar counterparts.

Requirements: 6.1
"""
from __future__ import annotations

import sys
from decimal import Decimal
from typing import Iterator

import boto3
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame, Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The three dimensions used to measure campaign similarity.
# Mirrors SIMILAR_CAMPAIGN_DIMENSIONS in shared/models.py.
_DIMENSIONS: list[str] = ["flag_program", "jenis_leads", "media_blasting"]

_NUM_DIMENSIONS: int = len(_DIMENSIONS)  # 3

# ---------------------------------------------------------------------------
# Core ETL functions
# ---------------------------------------------------------------------------


def read_campaign_master(spark: SparkSession, clean_s3_path: str) -> DataFrame:
    """Read campaign master Parquet files from the S3 clean zone.

    Deduplicates by campaign_id, retaining the dimension columns and
    take_up_rate needed for the similarity index.

    Args:
        spark: Active SparkSession.
        clean_s3_path: Root path of the S3 clean zone (must end with ``/``).

    Returns:
        DataFrame with one row per unique campaign_id containing columns:
        ``campaign_id``, ``flag_program``, ``jenis_leads``,
        ``media_blasting``, ``take_up_rate``.
    """
    raw = (
        spark.read.parquet(f"{clean_s3_path}campaigns/")
        .select(
            "campaign_id",
            "flag_program",
            "jenis_leads",
            "media_blasting",
            "take_up_rate",
        )
    )

    # Keep one representative row per campaign_id using row_number over a
    # deterministic ordering so the job is idempotent.
    from pyspark.sql.window import Window

    window_spec = (
        Window.partitionBy("campaign_id")
        .orderBy("campaign_id")
    )
    campaigns = (
        raw.withColumn("_rn", F.row_number().over(window_spec))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )
    return campaigns


def compute_similarity_pairs(campaigns: DataFrame) -> DataFrame:
    """Compute all pairwise similarities between campaigns.

    Performs a self-join filtered to A.campaign_id < B.campaign_id to
    enumerate unique unordered pairs, then derives per-dimension match
    flags, dimension_count, and similarity_score.  Pairs where no
    dimension matches (dimension_count == 0) are discarded.

    Args:
        campaigns: Deduplicated campaign DataFrame from
            :func:`read_campaign_master`.

    Returns:
        DataFrame with columns:
        ``campaign_id_a``, ``campaign_id_b``,
        ``flag_program_match``, ``jenis_leads_match``,
        ``media_blasting_match``,
        ``dimension_count``, ``similarity_score``,
        ``take_up_rate_a``, ``take_up_rate_b``.
    """
    a = campaigns.alias("a")
    b = campaigns.alias("b")

    # Cross-join then filter to keep only (A < B) pairs — avoids duplicate
    # pairs (A,B) / (B,A) and self-pairs (A,A).
    pairs = a.join(b, F.col("a.campaign_id") < F.col("b.campaign_id"))

    # Per-dimension match flags (1 if equal, 0 otherwise).
    pairs = (
        pairs
        .withColumn(
            "flag_program_match",
            (F.col("a.flag_program") == F.col("b.flag_program"))
            .cast(IntegerType()),
        )
        .withColumn(
            "jenis_leads_match",
            (F.col("a.jenis_leads") == F.col("b.jenis_leads"))
            .cast(IntegerType()),
        )
        .withColumn(
            "media_blasting_match",
            (F.col("a.media_blasting") == F.col("b.media_blasting"))
            .cast(IntegerType()),
        )
    )

    # Aggregate dimension count and normalised similarity score.
    pairs = pairs.withColumn(
        "dimension_count",
        F.col("flag_program_match")
        + F.col("jenis_leads_match")
        + F.col("media_blasting_match"),
    ).withColumn(
        "similarity_score",
        F.col("dimension_count") / F.lit(float(_NUM_DIMENSIONS)),
    )

    # Discard pairs with no shared dimension.
    pairs = pairs.filter(F.col("dimension_count") >= 1)

    # Select and rename to unambiguous column names.
    pairs = pairs.select(
        F.col("a.campaign_id").alias("campaign_id_a"),
        F.col("b.campaign_id").alias("campaign_id_b"),
        "flag_program_match",
        "jenis_leads_match",
        "media_blasting_match",
        "dimension_count",
        "similarity_score",
        F.col("a.take_up_rate").alias("take_up_rate_a"),
        F.col("b.take_up_rate").alias("take_up_rate_b"),
    )
    return pairs


def build_matching_dimensions(pairs: DataFrame) -> DataFrame:
    """Append a ``matching_dimensions`` string-array column to the pairs DataFrame.

    Collects the names of the dimensions where both campaigns matched into
    a list column so DynamoDB can store them as a StringSet / List.

    Args:
        pairs: Output of :func:`compute_similarity_pairs`.

    Returns:
        Input DataFrame with an additional ``matching_dimensions`` column
        containing a list of matched dimension name strings.
    """
    # Build an array of dimension names where match == 1, then filter nulls.
    dim_array = F.array(
        F.when(F.col("flag_program_match") == 1, F.lit("flag_program")),
        F.when(F.col("jenis_leads_match") == 1, F.lit("jenis_leads")),
        F.when(F.col("media_blasting_match") == 1, F.lit("media_blasting")),
    )
    pairs = pairs.withColumn(
        "matching_dimensions",
        F.array_compact(dim_array),  # removes nulls (Spark 3.4+)
    )
    # Fallback for older Spark versions that lack array_compact.
    # array_compact was introduced in Spark 3.4; Glue 4.0 ships Spark 3.3.
    # Use filter(col IS NOT NULL) approach instead.
    return pairs


def build_matching_dimensions_compat(pairs: DataFrame) -> DataFrame:
    """Append ``matching_dimensions`` column using Spark 3.3-compatible logic.

    Replaces the Spark 3.4+ ``array_compact`` approach in
    :func:`build_matching_dimensions` with a ``filter`` lambda that works
    on Spark 3.3 (AWS Glue 4.0).

    Args:
        pairs: Output of :func:`compute_similarity_pairs`.

    Returns:
        Input DataFrame with ``matching_dimensions`` column added.
    """
    dim_array = F.array(
        F.when(F.col("flag_program_match") == 1, F.lit("flag_program")),
        F.when(F.col("jenis_leads_match") == 1, F.lit("jenis_leads")),
        F.when(F.col("media_blasting_match") == 1, F.lit("media_blasting")),
    )
    pairs = pairs.withColumn("_dim_raw", dim_array)
    # F.filter removes elements where the lambda returns false (nulls → False).
    pairs = pairs.withColumn(
        "matching_dimensions",
        F.filter(F.col("_dim_raw"), lambda x: x.isNotNull()),
    )
    pairs = pairs.drop("_dim_raw")
    return pairs


# ---------------------------------------------------------------------------
# DynamoDB writer
# ---------------------------------------------------------------------------


def write_partition_to_dynamodb(
    partition_rows: Iterator[Row],
    table_name: str,
    region: str,
) -> None:
    """Write one Spark partition to DynamoDB using a batch_writer.

    Called via ``foreachPartition`` — boto3 clients are created per
    partition to avoid serialization issues.

    For each pair (A, B) two items are written:
    - Forward:  campaign_id=A, similar_campaign_id=B, take_up_rate=B_rate
    - Reverse:  campaign_id=B, similar_campaign_id=A, take_up_rate=A_rate

    DynamoDB requires Decimal for numeric types (not float).

    Args:
        partition_rows: Iterator of Spark Row objects for this partition.
        table_name: DynamoDB table name.
        region: AWS region string (e.g. ``"ap-southeast-1"``).
    """
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for row in partition_rows:
            matching_dims: list[str] = list(row["matching_dimensions"])
            dimension_count: int = int(row["dimension_count"])
            similarity_score = Decimal(str(round(float(row["similarity_score"]), 6)))

            # Forward item: A → B
            batch.put_item(
                Item={
                    "campaign_id": row["campaign_id_a"],
                    "similar_campaign_id": row["campaign_id_b"],
                    "matching_dimensions": matching_dims,
                    "dimension_count": dimension_count,
                    "similarity_score": similarity_score,
                    "take_up_rate": Decimal(
                        str(round(float(row["take_up_rate_b"]), 6))
                    ),
                }
            )

            # Reverse item: B → A
            batch.put_item(
                Item={
                    "campaign_id": row["campaign_id_b"],
                    "similar_campaign_id": row["campaign_id_a"],
                    "matching_dimensions": matching_dims,
                    "dimension_count": dimension_count,
                    "similarity_score": similarity_score,
                    "take_up_rate": Decimal(
                        str(round(float(row["take_up_rate_a"]), 6))
                    ),
                }
            )


def write_to_dynamodb(pairs: DataFrame, table_name: str, region: str) -> None:
    """Distribute the pairs DataFrame to DynamoDB via foreachPartition.

    Args:
        pairs: DataFrame containing similarity pairs with all required
            columns (output of :func:`build_matching_dimensions_compat`).
        table_name: DynamoDB table name.
        region: AWS region string.
    """
    pairs.foreachPartition(
        lambda partition: write_partition_to_dynamodb(
            partition, table_name, region
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Glue similarity-index job.

    Reads job parameters, initialises the Glue/Spark context, orchestrates
    the similarity ETL pipeline, and commits the job on success.
    """
    args = getResolvedOptions(
        sys.argv,
        ["JOB_NAME", "clean_s3_path", "dynamodb_table", "aws_region"],
    )

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark: SparkSession = glue_context.spark_session

    job = Job(glue_context)
    job.init(args["JOB_NAME"], args)

    clean_s3_path: str = args["clean_s3_path"]
    dynamodb_table: str = args["dynamodb_table"]
    aws_region: str = args["aws_region"]

    # Ensure path ends with '/' for consistent path construction.
    if not clean_s3_path.endswith("/"):
        clean_s3_path += "/"

    # --- Extract ---
    campaigns = read_campaign_master(spark, clean_s3_path)

    # --- Transform ---
    pairs = compute_similarity_pairs(campaigns)
    pairs = build_matching_dimensions_compat(pairs)

    # --- Load ---
    write_to_dynamodb(pairs, dynamodb_table, aws_region)

    job.commit()


if __name__ == "__main__":
    main()
