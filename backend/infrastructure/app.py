#!/usr/bin/env python3
"""CDK app entry point for Campaign Insight Generator.

Deploys all stacks to the target AWS environment.  The active environment
is selected via the CDK context key ``env`` (default: ``"dev"``).

Usage:
    cdk deploy --context env=prod

Requirements: 7.1
"""

from __future__ import annotations

import os

import aws_cdk as cdk
from stacks.api_stack import ApiStack
from stacks.auth_stack import AuthStack
from stacks.data_stack import DataStack

app = cdk.App()

env_name: str = app.node.try_get_context("env") or "dev"

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "ap-southeast-1"),
)

data_stack = DataStack(
    app,
    f"CampaignInsight-Data-{env_name}",
    env=env,
    env_name=env_name,
)

auth_stack = AuthStack(
    app,
    f"CampaignInsight-Auth-{env_name}",
    env=env,
    env_name=env_name,
)

api_stack = ApiStack(
    app,
    f"CampaignInsight-Api-{env_name}",
    env=env,
    env_name=env_name,
    data_stack=data_stack,
    auth_stack=auth_stack,
)

cdk.Tags.of(app).add("Project", "CampaignInsightGenerator")
cdk.Tags.of(app).add("Environment", env_name)

app.synth()
