#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.api_stack import ApiStack
from stacks.data_stack import DataStack


app = cdk.App()

# Pinning env to the account/region implied by your AWS CLI config (the
# same one we ran `cdk bootstrap` against) rather than leaving the stack
# environment-agnostic.
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)

# No FrontendStack here -- the PWA is already hosted free on GitHub Pages
# (jpcrowgit.github.io/habittracker), so this app only needs somewhere to
# read/write the synced state.
data_stack = DataStack(app, "HabitDataStack", env=env)
ApiStack(app, "HabitApiStack", env=env, table=data_stack.table)

app.synth()
