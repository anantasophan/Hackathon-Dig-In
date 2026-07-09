"""Auth Stack — Cognito User Pool and API Gateway authorizer.

Provisions the authentication layer:
- Cognito User Pool with custom role attribute (divisi_bisnis | divisi_data)
- User Pool Client for the SPA frontend (public client, no secret)
- Token validity: 8 hours access token (Requirement 7.2)

Requirements: 7.1, 7.2, 7.3
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_cognito as cognito,
)
from constructs import Construct


class AuthStack(Stack):
    """CDK stack that provisions Cognito authentication resources.

    Args:
        scope: CDK construct scope.
        construct_id: Logical identifier for this stack.
        env_name: Deployment environment name (dev, staging, prod).
        **kwargs: Forwarded to :class:`aws_cdk.Stack`.

    Attributes:
        user_pool: Cognito User Pool for campaign insight users.
        user_pool_client: User Pool Client configured for SPA (no secret).
        user_pool_id: The User Pool identifier string.
        user_pool_client_id: The User Pool Client identifier string.
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
        # Cognito User Pool
        # ------------------------------------------------------------------
        # self_sign_up_enabled=False: only admins create accounts (Req 7.1)
        # custom_attributes: role field distinguishes divisi_bisnis vs divisi_data
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"campaign-insight-users-{env_name}",
            self_sign_up_enabled=False,  # Admin creates users only (Req 7.1)
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
            ),
            custom_attributes={
                "role": cognito.StringAttribute(
                    min_len=1,
                    max_len=50,
                    mutable=True,
                ),
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=(
                RemovalPolicy.RETAIN
                if env_name == "prod"
                else RemovalPolicy.DESTROY
            ),
        )

        # ------------------------------------------------------------------
        # User Pool Client (SPA frontend — public client, no secret)
        # ------------------------------------------------------------------
        # access_token_validity=8h: enforces the 8-hour session requirement (Req 7.2)
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name=f"campaign-insight-client-{env_name}",
            generate_secret=False,  # Public client (SPA frontend)
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False,
                ),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=[
                    f"https://campaign-insight-{env_name}.example.com/callback",
                    "http://localhost:3000/callback",  # Dev/local
                ],
                logout_urls=[
                    f"https://campaign-insight-{env_name}.example.com/logout",
                    "http://localhost:3000/logout",
                ],
            ),
            access_token_validity=Duration.hours(8),   # Req 7.2: 8-hour session
            id_token_validity=Duration.hours(8),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )

        # ------------------------------------------------------------------
        # Expose properties (used by ApiStack for Cognito authorizer)
        # ------------------------------------------------------------------
        self.user_pool_id = self.user_pool.user_pool_id
        self.user_pool_client_id = self.user_pool_client.user_pool_client_id

        # ------------------------------------------------------------------
        # CDK Outputs
        # ------------------------------------------------------------------
        cdk.CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name=f"UserPoolId-{env_name}",
        )
        cdk.CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name=f"UserPoolClientId-{env_name}",
        )
