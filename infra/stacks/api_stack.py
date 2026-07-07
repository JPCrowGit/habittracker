from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from constructs import Construct

SSM_PREFIX = "/habittracker"


class ApiStack(Stack):
    """Defines the HTTP API and the single Lambda behind it.

    Routes: `GET /api/state` and `PUT /api/state`, both handled by one
    Lambda -- there's no per-habit or per-date granularity to route on,
    just "read the blob" and "write the blob" (see DataStack).

    Unlike workouttracker, the frontend isn't served from CloudFront on
    the same domain as this API, so:
      - CORS has to be enabled explicitly for the GitHub Pages origin.
      - Auth can't be a CloudFront Function edge gate. Instead the Lambda
        itself checks a shared-secret header (`x-habit-key`), the same
        pattern workouttracker used before it grew a CloudFront distribution
        to gate -- proportionate here since there's no plan to add one.
    """

    def __init__(
        self, scope: Construct, construct_id: str, table: dynamodb.ITable, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        state_fn = _lambda.Function(
            self,
            "StateFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambdas/api"),
            timeout=Duration.seconds(10),
            environment={"SSM_PREFIX": SSM_PREFIX, "TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(state_fn)
        self._grant_ssm_read(state_fn)

        self.http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["https://jpcrowgit.github.io"],
                allow_methods=[apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.PUT],
                allow_headers=["Content-Type", "x-habit-key"],
            ),
        )

        integration = apigwv2_integrations.HttpLambdaIntegration(
            "StateIntegration", state_fn
        )

        self.http_api.add_routes(
            path="/api/state",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.PUT],
            integration=integration,
        )

        # cdk deploy prints this as an output so we can grab the URL
        # without digging through the console.
        CfnOutput(self, "ApiUrl", value=self.http_api.api_endpoint)

    def _grant_ssm_read(self, fn: _lambda.Function) -> None:
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{SSM_PREFIX}/*"
                ],
            )
        )
