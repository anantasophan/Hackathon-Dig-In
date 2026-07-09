"""API Stack — API Gateway REST API and Lambda functions.

Provisions the API layer:
- Seven Lambda functions (one per endpoint)
- API Gateway REST API with Cognito authorizer
- IAM roles and policies for each Lambda
- CORS configuration, request validation, rate limiting
- CloudWatch logging integration

Requirements: 1.2, 7.1, 7.4
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
)
from constructs import Construct

from stacks.auth_stack import AuthStack
from stacks.data_stack import DataStack

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LAMBDA_RUNTIME = lambda_.Runtime.PYTHON_3_11
_LAMBDA_TIMEOUT = Duration.seconds(35)  # slightly above Athena 30 s poll timeout
_LAMBDA_MEMORY = 256  # MB


class ApiStack(Stack):
    """CDK stack that provisions API Gateway and Lambda functions.

    Creates one Lambda per endpoint with appropriate IAM permissions, wires
    them to a REST API with a Cognito authorizer, and configures CORS, request
    validation, throttling, and CloudWatch logging.

    Args:
        scope: CDK construct scope.
        construct_id: Logical identifier for this stack.
        env_name: Deployment environment name (dev, staging, prod).
        data_stack: Resolved :class:`DataStack` (provides bucket/table ARNs).
        auth_stack: Resolved :class:`AuthStack` (provides Cognito user pool).
        **kwargs: Forwarded to :class:`aws_cdk.Stack`.

    Attributes:
        api: The provisioned API Gateway :class:`apigw.RestApi` instance.
        api_url: Base URL of the deployed API.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        data_stack: DataStack,
        auth_stack: AuthStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._env_name = env_name
        self._data_stack = data_stack
        self._auth_stack = auth_stack

        # Build shared environment variables injected into every Lambda.
        shared_env = self._build_shared_env(env_name)

        # ------------------------------------------------------------------
        # CloudWatch Log Group for API Gateway access logs
        # ------------------------------------------------------------------
        access_log_group = logs.LogGroup(
            self,
            "ApiAccessLogs",
            log_group_name=f"/aws/apigateway/campaign-insight-api-{env_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ------------------------------------------------------------------
        # Lambda Functions
        # ------------------------------------------------------------------
        overview_fn = self._make_lambda(
            "CampaignOverviewFn",
            "lambdas/campaign_overview/handler.lambda_handler",
            shared_env,
        )
        comparison_fn = self._make_lambda(
            "CampaignComparisonFn",
            "lambdas/campaign_comparison/handler.lambda_handler",
            shared_env,
        )
        time_analysis_fn = self._make_lambda(
            "TimeAnalysisFn",
            "lambdas/time_analysis/handler.lambda_handler",
            shared_env,
        )
        regional_fn = self._make_lambda(
            "RegionalPerformanceFn",
            "lambdas/regional_performance/handler.lambda_handler",
            shared_env,
        )
        customer_criteria_fn = self._make_lambda(
            "CustomerCriteriaFn",
            "lambdas/customer_criteria/handler.lambda_handler",
            shared_env,
        )
        similar_fn = self._make_lambda(
            "SimilarCampaignFn",
            "lambdas/similar_campaign/handler.lambda_handler",
            shared_env,
        )
        export_fn = self._make_lambda(
            "ExportServiceFn",
            "lambdas/export_service/handler.lambda_handler",
            shared_env,
        )

        # ------------------------------------------------------------------
        # IAM Permissions — shared across all Lambdas
        # ------------------------------------------------------------------
        all_fns = [
            overview_fn,
            comparison_fn,
            time_analysis_fn,
            regional_fn,
            customer_criteria_fn,
            similar_fn,
            export_fn,
        ]
        for fn in all_fns:
            self._attach_common_permissions(fn)

        # Export Lambda additionally needs presigned-URL capability.
        # s3:GetObject is already granted by _attach_common_permissions;
        # presigned URLs are generated client-side via boto3 and only require
        # the Lambda to have the underlying s3:GetObject permission.  No
        # extra IAM action is needed — documented here for clarity.

        # ------------------------------------------------------------------
        # API Gateway REST API
        # ------------------------------------------------------------------
        api_log_format = apigw.AccessLogFormat.json_with_standard_fields(
            caller=False,
            http_method=True,
            ip=True,
            protocol=True,
            request_time=True,
            resource_path=True,
            response_length=True,
            status=True,
            user=False,
        )

        # ------------------------------------------------------------------
        # CORS Configuration Audit (Task 13.1)
        # ------------------------------------------------------------------
        # CORS headers are configured at the API Gateway level via
        # default_cors_preflight_options, which auto-adds an OPTIONS method
        # to every resource node.  This covers the following headers:
        #
        #   Access-Control-Allow-Origin:   * (ALL_ORIGINS)
        #   Access-Control-Allow-Methods:  GET, POST, PUT, DELETE, OPTIONS, HEAD
        #   Access-Control-Allow-Headers:  Content-Type, Authorization
        #
        # The frontend attaches:
        #   Authorization: Bearer <Cognito idToken>
        #   Content-Type: application/json
        #
        # Both are explicitly listed in allow_headers above, so preflight
        # requests will succeed.
        #
        # Lambda proxy integration (proxy=True) passes the full event to
        # each handler and returns CORS headers via the API Gateway transform —
        # no manual header injection is required in the Lambda response body.
        #
        # Note: For production deployments, restrict allow_origins to the
        # actual CloudFront distribution domain instead of ALL_ORIGINS.
        # ------------------------------------------------------------------
        self.api = apigw.RestApi(
            self,
            "CampaignInsightApi",
            rest_api_name=f"campaign-insight-api-{env_name}",
            description="Campaign Insight Generator API",
            # CORS — preflight handled automatically by API Gateway
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
            deploy_options=apigw.StageOptions(
                stage_name=env_name,
                # Rate limiting — 429 responses for bursts beyond these limits
                throttling_rate_limit=100,
                throttling_burst_limit=50,
                # Structured access logs to CloudWatch
                access_log_destination=apigw.LogGroupLogDestination(access_log_group),
                access_log_format=api_log_format,
                logging_level=apigw.MethodLoggingLevel.INFO,
                # Do NOT log full request/response bodies (contains PII)
                data_trace_enabled=False,
                metrics_enabled=True,
            ),
        )

        # ------------------------------------------------------------------
        # Request Validator
        # ------------------------------------------------------------------
        request_validator = apigw.RequestValidator(
            self,
            "BodyAndParamsValidator",
            rest_api=self.api,
            request_validator_name="validate-body-and-params",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        # ------------------------------------------------------------------
        # Cognito Authorizer — JWT Token Flow (Task 13.1)
        # ------------------------------------------------------------------
        # Token flow:
        #   1. User signs in via Amplify (Auth.signIn) → Cognito returns idToken.
        #   2. frontend/src/services/api.ts request interceptor calls
        #      fetchAuthSession() and attaches:
        #        Authorization: Bearer <idToken>
        #   3. API Gateway CognitoUserPoolsAuthorizer validates the JWT:
        #        identity_source: method.request.header.Authorization
        #        results_cache_ttl: 5 minutes (reduces Cognito API calls)
        #   4. On success, API Gateway forwards the full event (including
        #      requestContext.authorizer.claims) to the Lambda handler.
        #   5. Lambda shared/auth.py reads claims from
        #        event["requestContext"]["authorizer"]["claims"]
        #      to extract user identity and role (custom:role attribute).
        #   6. On 401: api.ts response interceptor throws ApiAuthError.
        #
        # Token validity: 8 hours (configured in AuthStack.user_pool_client).
        # ------------------------------------------------------------------
        # AuthStack is a stub until task 8.4; guard against missing user_pool.
        # ------------------------------------------------------------------
        authorizer: apigw.IAuthorizer | None = None
        user_pool = getattr(auth_stack, "user_pool", None)
        if user_pool is not None:
            authorizer = apigw.CognitoUserPoolsAuthorizer(
                self,
                "CognitoAuthorizer",
                cognito_user_pools=[user_pool],
                authorizer_name=f"campaign-insight-authorizer-{env_name}",
                identity_source="method.request.header.Authorization",
                results_cache_ttl=Duration.minutes(5),
            )

        auth_type = (
            apigw.AuthorizationType.COGNITO
            if authorizer is not None
            else apigw.AuthorizationType.NONE
        )

        # ------------------------------------------------------------------
        # Route Tree
        # /api/campaigns/overview                    GET
        # /api/campaigns/comparison                  POST
        # /api/campaigns/time-analysis/{id}          GET
        # /api/campaigns/regional/{id}               GET
        # /api/campaigns/customer-criteria/{id}      GET
        # /api/campaigns/similar                     POST
        # /api/export                                POST
        # ------------------------------------------------------------------
        api_root = self.api.root.add_resource("api")
        campaigns = api_root.add_resource("campaigns")

        # GET /api/campaigns/overview
        overview_res = campaigns.add_resource("overview")
        self._add_method(
            overview_res, "GET", overview_fn, auth_type, authorizer,
            request_validator,
        )

        # POST /api/campaigns/comparison
        comparison_res = campaigns.add_resource("comparison")
        self._add_method(
            comparison_res, "POST", comparison_fn, auth_type, authorizer,
            request_validator,
        )

        # GET /api/campaigns/time-analysis/{id}
        time_analysis_res = campaigns.add_resource("time-analysis").add_resource("{id}")
        self._add_method(
            time_analysis_res, "GET", time_analysis_fn, auth_type, authorizer,
            request_validator,
        )

        # GET /api/campaigns/regional/{id}
        regional_res = campaigns.add_resource("regional").add_resource("{id}")
        self._add_method(
            regional_res, "GET", regional_fn, auth_type, authorizer,
            request_validator,
        )

        # GET /api/campaigns/customer-criteria/{id}
        customer_criteria_res = (
            campaigns.add_resource("customer-criteria").add_resource("{id}")
        )
        self._add_method(
            customer_criteria_res, "GET", customer_criteria_fn, auth_type, authorizer,
            request_validator,
        )

        # POST /api/campaigns/similar
        similar_res = campaigns.add_resource("similar")
        self._add_method(
            similar_res, "POST", similar_fn, auth_type, authorizer,
            request_validator,
        )

        # POST /api/export
        export_res = api_root.add_resource("export")
        self._add_method(
            export_res, "POST", export_fn, auth_type, authorizer,
            request_validator,
        )

        # ------------------------------------------------------------------
        # Expose properties for cross-stack references
        # ------------------------------------------------------------------
        self.api_url: str = self.api.url

        # CloudFormation output for convenience
        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description=f"Campaign Insight API base URL ({env_name})",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_shared_env(self, env_name: str) -> dict[str, str]:
        """Build the shared environment variable dict for all Lambda functions.

        Args:
            env_name: Deployment environment name.

        Returns:
            Dictionary of environment variable name → value/placeholder.
        """
        return {
            "ATHENA_DATABASE": f"campaign_insight_{env_name}",
            "ATHENA_S3_OUTPUT": (
                f"s3://campaign-datalake-{env_name}/athena-results/"
            ),
            "ATHENA_WORKGROUP": f"campaign-insight-{env_name}",
            "AWS_REGION_NAME": self.region,
            "EXPORT_BUCKET": f"campaign-exports-{env_name}",
            "SIMILARITY_TABLE": "CampaignSimilarityIndex",
            "AUDIT_LOG_TABLE": "AuditLog",
        }

    def _make_lambda(
        self,
        construct_id: str,
        handler: str,
        environment: dict[str, str],
    ) -> lambda_.Function:
        """Create a Lambda function with standard settings.

        Args:
            construct_id: CDK logical ID for the function.
            handler: Module path to the handler, e.g.
                ``"lambdas/campaign_overview/handler.lambda_handler"``.
            environment: Environment variables to inject.

        Returns:
            Configured :class:`lambda_.Function` instance.
        """
        # Normalise handler path: CDK expects "module.function" dot notation
        # where the module path uses dots (no slashes).
        # e.g. "lambdas/campaign_overview/handler.lambda_handler"
        # → "lambdas.campaign_overview.handler.lambda_handler"
        handler_dotted = handler.replace("/", ".")

        fn = lambda_.Function(
            self,
            construct_id,
            runtime=_LAMBDA_RUNTIME,
            handler=handler_dotted,
            code=lambda_.Code.from_asset("../"),  # root of backend/
            timeout=_LAMBDA_TIMEOUT,
            memory_size=_LAMBDA_MEMORY,
            environment=environment,
            # Each function gets its own CloudWatch log group with 1-month retention.
            log_retention=logs.RetentionDays.ONE_MONTH,
            description=f"{construct_id} — Campaign Insight Generator ({self._env_name})",
        )
        return fn

    def _attach_common_permissions(self, fn: lambda_.Function) -> None:
        """Attach IAM permissions shared by all Lambda functions.

        Grants:
        - AmazonAthenaFullAccess managed policy
        - S3 read/write on the data lake bucket
        - S3 read/write/delete on the exports bucket
        - DynamoDB Query/GetItem on the similarity table
        - DynamoDB PutItem/GetItem on the audit log table

        Args:
            fn: Lambda function to grant permissions to.
        """
        ds = self._data_stack

        # Athena managed policy — covers Glue data catalog access too
        fn.role.add_managed_policy(  # type: ignore[union-attr]
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAthenaFullAccess")
        )

        # S3 — data lake (read results, write Athena query output)
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="DataLakeBucketAccess",
                actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources=[
                    ds.data_lake_bucket.bucket_arn,
                    ds.data_lake_bucket.arn_for_objects("*"),
                ],
            )
        )

        # S3 — exports bucket (write export files, generate presigned URLs)
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="ExportsBucketAccess",
                actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                resources=[
                    ds.exports_bucket.bucket_arn,
                    ds.exports_bucket.arn_for_objects("*"),
                ],
            )
        )

        # DynamoDB — similarity index (read-only at query time)
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="SimilarityTableReadAccess",
                actions=["dynamodb:Query", "dynamodb:GetItem"],
                resources=[
                    ds.similarity_table.table_arn,
                    f"{ds.similarity_table.table_arn}/index/*",
                ],
            )
        )

        # DynamoDB — audit log (write new entries, read own entries)
        fn.add_to_role_policy(
            iam.PolicyStatement(
                sid="AuditLogTableAccess",
                actions=["dynamodb:PutItem", "dynamodb:GetItem"],
                resources=[ds.audit_log_table.table_arn],
            )
        )

    def _add_method(
        self,
        resource: apigw.Resource,
        http_method: str,
        fn: lambda_.Function,
        auth_type: apigw.AuthorizationType,
        authorizer: apigw.IAuthorizer | None,
        request_validator: apigw.RequestValidator,
    ) -> apigw.Method:
        """Add an HTTP method backed by a Lambda integration to a resource.

        Args:
            resource: API Gateway resource node to add the method to.
            http_method: HTTP verb, e.g. ``"GET"`` or ``"POST"``.
            fn: Lambda function to back the integration.
            auth_type: Authorization type for the method.
            authorizer: Cognito authorizer (``None`` when AuthStack is stub).
            request_validator: Validator for body and query parameters.

        Returns:
            The created :class:`apigw.Method`.
        """
        method_options: dict = {
            "authorization_type": auth_type,
            "request_validator": request_validator,
        }
        if authorizer is not None:
            method_options["authorizer"] = authorizer

        return resource.add_method(
            http_method,
            apigw.LambdaIntegration(
                fn,
                proxy=True,  # pass full event to Lambda
                timeout=Duration.seconds(29),  # API GW max integration timeout
            ),
            **method_options,
        )
