from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DataStack(Stack):
    """Owns the single DynamoDB table that stores the synced habit state.

    Unlike workouttracker's one-item-per-exercise design (needed for date
    range queries feeding charts), this app only ever needs to read/write
    one whole blob per user -- there's no server-side querying to support,
    just "give me the JSON" and "save this JSON". So the table holds a
    single item per user: PK=USER#<id>, SK=STATE, with the entire
    {habits, completions} object serialized into one attribute.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = dynamodb.Table(
            self,
            "HabitStateTable",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            # PROVISIONED (not on-demand) is deliberate -- only provisioned
            # capacity carries DynamoDB's "Always Free" allowance (25 RCU /
            # 25 WCU) forever, not just an account's first 12 months. 5/5
            # sits comfortably inside that for single-user, low-volume
            # traffic.
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            # This is the only copy of your habit history -- don't let
            # deleting the stack silently delete the data too.
            removal_policy=RemovalPolicy.RETAIN,
        )

        CfnOutput(self, "TableName", value=self.table.table_name)
