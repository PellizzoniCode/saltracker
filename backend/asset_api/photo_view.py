"""Generate a short-lived, permission-checked URL to view an asset's photo."""

import json
import logging
import os

import boto3

from domain import can_read, parse_groups


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

S3 = boto3.client("s3")
TABLE = boto3.resource("dynamodb").Table(os.environ["ASSET_TABLE_NAME"])
PHOTO_BUCKET = os.environ["ASSET_PHOTO_BUCKET"]

URL_TTL_SECONDS = 300


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def _asset_key(asset_id):
    return {"PK": f"ASSET#{asset_id}", "SK": "METADATA"}


def lambda_handler(event, _context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims") or {}
    subject = claims.get("sub")

    if not subject:
        return _response(401, {"message": "Sign in to view this photograph."})

    asset_id = (event.get("pathParameters") or {}).get("assetId")
    groups = parse_groups(claims.get("cognito:groups"))

    item = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")

    if not item:
        return _response(404, {"message": "Asset was not found."})

    if not can_read(groups, claims, item):
        return _response(403, {"message": "You do not have permission to view this photograph."})

    image_key = item.get("imageKey")

    if not image_key:
        return _response(404, {"message": "This asset has no photograph."})

    try:
        url = S3.generate_presigned_url(
            "get_object",
            Params={"Bucket": PHOTO_BUCKET, "Key": image_key},
            ExpiresIn=URL_TTL_SECONDS,
        )
    except Exception:
        LOGGER.exception("Unable to sign asset photo view URL")
        return _response(500, {"message": "Could not prepare the photograph. Try again."})

    return _response(200, {"url": url, "expiresIn": URL_TTL_SECONDS})
