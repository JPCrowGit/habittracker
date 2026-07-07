"""GET/PUT /api/state -- reads and writes the single synced state blob.

No per-field structure on the DynamoDB side: the item's `data` attribute
is just the same JSON string the PWA already keeps in `localStorage`
under `habit-tracker-v1` (see index.html). This Lambda is a dumb
pass-through so the client's existing {habits, completions} shape never
has to be duplicated or re-validated server-side.
"""

import json
import os

import boto3

_ssm = boto3.client("ssm")


def _get_secret(name: str) -> str:
    return _ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]


_SSM_PREFIX = os.environ["SSM_PREFIX"]
API_KEY = _get_secret(f"{_SSM_PREFIX}/api_key")

_dynamodb = boto3.resource("dynamodb")
TABLE = _dynamodb.Table(os.environ["TABLE_NAME"])

# Single-user app -- no login flow, just one fixed partition.
PK = "USER#jp"
SK = "STATE"


def handler(event, context):
    headers = event.get("headers") or {}
    if headers.get("x-habit-key") != API_KEY:
        return {"statusCode": 401, "body": "Unauthorized"}

    method = event.get("requestContext", {}).get("http", {}).get("method")

    if method == "GET":
        response = TABLE.get_item(Key={"PK": PK, "SK": SK})
        data = response.get("Item", {}).get("data", "null")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": data,
        }

    if method == "PUT":
        body = event.get("body") or "null"
        # Round-trip through json.loads/dumps to reject a malformed body
        # before it gets persisted, rather than storing garbage verbatim.
        json.loads(body)
        TABLE.put_item(Item={"PK": PK, "SK": SK, "data": body})
        return {"statusCode": 204}

    return {"statusCode": 405, "body": "Method Not Allowed"}
