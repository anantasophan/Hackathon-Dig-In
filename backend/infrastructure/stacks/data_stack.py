"""Data Stack — S3, DynamoDB, Athena, and Glue for Campaign Insight Generator.

Provisions the full storage and ETL infrastructure layer:
- Two S3 buckets (data lake and exports)
- Three DynamoDB tables (similarity index, audit log, user sessions)
- Athena workgroup for campaign analytics queries
- Four Glue ETL jobs with scheduled triggers

Requirements: 6.1, 7.4
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_athena as athena,
    aws_dynamodb as dynamodb,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct


class DataStack(Stack):
    """CDK stack that provisions all persistent storage and ETL resources.

    Args:
        scope: CDK construct scope.
        construct_id: Logical identifier for this stack.
        env_name: Deployment environment name (dev, staging, prod).
        **kwargs: Forwarded to :class:`aws_cdk.Stack`.

    Attributes:
        data_lake_bucket: Main S3 data lake bucket (raw / clean / aggregated zones).
        exports_bucket: S3 bucket for generated export files (1-day lifecycle).
        similarity_table: DynamoDB table for the campaign similarity index.
        audit_log_table: DynamoDB table for user audit log entries.
        sessions_table: DynamoDB table for active user sessions.
        athena_workgroup_name: Name of the Athena workgroup for query isolation.
        glue_role: IAM role assumed by all Glue ETL jobs.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._env_name = env_name

        # ------------------------------------------------------------------
        # S3 Buckets
        # ------------------------------------------------------------------
        self.data_lake_bucket = s3.Bucket(
            self,
            "DataLakeBucket",
            bucket_name=f"campaign-datalake-{env_name}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.exports_bucket = s3.Bucket(
            self,
            "ExportsBucket",
            bucket_name=f"campaign-exports-{env_name}",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-exports-after-1-day",
                    enabled=True,
                    expiration=Duration.days(1),
                )
            ],
        )

        # ------------------------------------------------------------------
        # DynamoDB: Campaign Similarity Index
        # ------------------------------------------------------------------
        self.similarity_table = dynamodb.Table(
            self,
            "CampaignSimilarityIndex",
            table_name="CampaignSimilarityIndex",
            partition_key=dynamodb.Attribute(
                name="campaign_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="similar_campaign_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # GSI: query by campaign_id ordered by dimension_count
        self.similarity_table.add_global_secondary_index(
            index_name="DimensionCountIndex",
            partition_key=dynamodb.Attribute(
                name="campaign_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="dimension_count",
                type=dynamodb.AttributeType.NUMBER,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # ------------------------------------------------------------------
        # DynamoDB: Audit Log
        # ------------------------------------------------------------------
        self.audit_log_table = dynamodb.Table(
            self,
            "AuditLog",
            table_name="AuditLog",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expiry_timestamp",
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ------------------------------------------------------------------
        # DynamoDB: User Sessions
        # ------------------------------------------------------------------
        self.sessions_table = dynamodb.Table(
            self,
            "UserSessions",
            table_name="UserSessions",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expiry_timestamp",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ------------------------------------------------------------------
        # Athena Workgroup
        # ------------------------------------------------------------------
        athena_workgroup = athena.CfnWorkGroup(
            self,
            "AthenaWorkgroup",
            name=f"campaign-insight-{env_name}",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{self.data_lake_bucket.bucket_name}/athena-results/",
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
            ),
            description="Athena workgroup for Campaign Insight Generator queries",
            state="ENABLED",
        )

        # Expose workgroup name so other stacks (ApiStack) can reference it
        self.athena_workgroup_name: str = athena_workgroup.name

        # ------------------------------------------------------------------
        # IAM Role for Glue Jobs
        # ------------------------------------------------------------------
        self.glue_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
            ],
        )

        # Grant Glue jobs read/write access to the data lake bucket
        self.data_lake_bucket.grant_read_write(self.glue_role)

        # ------------------------------------------------------------------
        # Glue Jobs
        # ------------------------------------------------------------------
        # Common default arguments shared by all Glue jobs
        _default_glue_args: dict[str, str] = {
            "--job-language": "python",
            "--TempDir": f"s3://{self.data_lake_bucket.bucket_name}/glue-temp/",
        }

        def _create_glue_job(
            job_id: str,
            script_path: str,
            description: str,
            default_args: dict[str, str] | None = None,
        ) -> glue.CfnJob:
            """Create a Glue ETL job backed by a script in the data lake bucket.

            Args:
                job_id: CDK logical ID (also used to derive the job name).
                script_path: Filename of the PySpark script under
                    ``s3://<datalake>/glue-scripts/``.
                description: Human-readable description of the job's purpose.
                default_args: Optional override for Glue job default arguments.
                    Falls back to ``_default_glue_args`` when ``None``.

            Returns:
                The :class:`aws_cdk.aws_glue.CfnJob` construct.
            """
            # Derive a consistent job name: strip "Job" suffix, lowercase
            job_name_suffix = job_id.lower().replace("job", "")
            return glue.CfnJob(
                self,
                job_id,
                name=f"campaign-{job_name_suffix}-{env_name}",
                role=self.glue_role.role_arn,
                command=glue.CfnJob.JobCommandProperty(
                    name="glueetl",
                    python_version="3",
                    script_location=(
                        f"s3://{self.data_lake_bucket.bucket_name}"
                        f"/glue-scripts/{script_path}"
                    ),
                ),
                glue_version="4.0",
                max_retries=1,
                timeout=60,
                description=description,
                default_arguments=default_args or _default_glue_args,
            )

        raw_to_clean_job = _create_glue_job(
            job_id="RawToCleanJob",
            script_path="raw_to_clean.py",
            description="Transform raw CSV/JSON campaign data into clean Parquet files.",
        )

        aggregate_metrics_job = _create_glue_job(
            job_id="AggregateMetricsJob",
            script_path="aggregate_metrics.py",
            description="Compute pre-aggregated campaign overview metrics from clean zone.",
        )

        similarity_index_job = _create_glue_job(
            job_id="SimilarityIndexJob",
            script_path="similarity_index.py",
            description="Build campaign similarity index and write results to DynamoDB.",
        )

        regional_rollup_job = _create_glue_job(
            job_id="RegionalRollupJob",
            script_path="regional_rollup.py",
            description="Compute regional performance aggregates from clean zone.",
        )

        # ------------------------------------------------------------------
        # Glue Triggers (Schedules)
        # ------------------------------------------------------------------
        # Daily 02:00 UTC — raw CSV/JSON → clean Parquet
        glue.CfnTrigger(
            self,
            "RawToCleanTrigger",
            name=f"campaign-raw-to-clean-trigger-{env_name}",
            type="SCHEDULED",
            schedule="cron(0 2 * * ? *)",
            start_on_creation=True,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=raw_to_clean_job.name,
                )
            ],
        )

        # Daily 03:00 UTC — aggregate metrics from clean zone
        glue.CfnTrigger(
            self,
            "AggregateMetricsTrigger",
            name=f"campaign-aggregate-metrics-trigger-{env_name}",
            type="SCHEDULED",
            schedule="cron(0 3 * * ? *)",
            start_on_creation=True,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=aggregate_metrics_job.name,
                )
            ],
        )

        # Daily 03:30 UTC — regional rollup from clean zone
        glue.CfnTrigger(
            self,
            "RegionalRollupTrigger",
            name=f"campaign-regional-rollup-trigger-{env_name}",
            type="SCHEDULED",
            schedule="cron(30 3 * * ? *)",
            start_on_creation=True,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=regional_rollup_job.name,
                )
            ],
        )

        # Weekly Sunday 04:00 UTC — rebuild similarity index
        glue.CfnTrigger(
            self,
            "SimilarityIndexTrigger",
            name=f"campaign-similarity-index-trigger-{env_name}",
            type="SCHEDULED",
            schedule="cron(0 4 ? * SUN *)",
            start_on_creation=True,
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=similarity_index_job.name,
                )
            ],
        )
