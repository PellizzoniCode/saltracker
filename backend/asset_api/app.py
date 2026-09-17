import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from domain import (
    ValidationError,
    can_create,
    can_read,
    parse_groups,
    validate_asset,
    validate_create_permissions,
    validate_update_permissions,
)


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
TABLE_NAME = os.environ["ASSET_TABLE_NAME"]
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
_SERIALIZER = TypeSerializer()


def _serialize(item):
    return {key: _SERIALIZER.serialize(value) for key, value in item.items()}


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=_json_default),
    }


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)}")


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError("Request body contains invalid JSON.") from exc


def _identity(event):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims") or {}
    return claims, parse_groups(claims.get("cognito:groups"))


def _asset_key(asset_id):
    return {"PK": f"ASSET#{asset_id}", "SK": "METADATA"}


def _asset_tag_key(asset_tag):
    return {"PK": f"ASSETTAG#{asset_tag}", "SK": "UNIQUE"}


def _tag_conflict(exc):
    reasons = exc.response.get("CancellationReasons", [])
    return len(reasons) > 1 and reasons[1].get("Code") == "ConditionalCheckFailed"


def _clean_asset(item):
    if not item:
        return None
    return {key: value for key, value in item.items() if key not in {"PK", "SK"}}


def _create(event, claims, groups):
    if not can_create(groups):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to create assets."})

    payload = _body(event)
    validate_asset(payload)
    if not validate_create_permissions(groups, payload):
        return response(
            403,
            {
                "error": "Forbidden",
                "message": "Only an Administrator can set assignment fields on a new asset.",
            },
        )

    asset_id = f"AST-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    item = {
        **payload,
        **_asset_key(asset_id),
        "assetId": asset_id,
        "depreciationMethod": payload.get("depreciationMethod", "straight-line"),
        "reviewStatus": payload.get("reviewStatus", "ManualEntry"),
        "createdBy": claims.get("sub"),
        "createdAt": now,
        "updatedAt": now,
    }
    item["purchaseValue"] = Decimal(str(item["purchaseValue"]))
    item["salvageValue"] = Decimal(str(item["salvageValue"]))
    lock_item = {**_asset_tag_key(payload["assetTag"]), "assetId": asset_id}

    try:
        TABLE.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": _serialize(item),
                        "ConditionExpression": "attribute_not_exists(PK)",
                    }
                },
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": _serialize(lock_item),
                        "ConditionExpression": "attribute_not_exists(PK)",
                    }
                },
            ]
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "TransactionCanceledException":
            raise
        if _tag_conflict(exc):
            return response(409, {"error": "Conflict", "message": "An asset with this asset tag already exists."})
        return response(409, {"error": "Conflict", "message": "Asset ID already exists."})

    LOGGER.info("Asset created assetId=%s actorSub=%s", asset_id, claims.get("sub"))
    return response(201, {"assetId": asset_id, "message": "Asset created successfully."})


def _get(asset_id, claims, groups):
    item = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")
    if not item:
        return response(404, {"error": "NotFound", "message": "Asset was not found."})
    if not can_read(groups, claims, item):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to view this asset."})
    return response(200, _clean_asset(item))


def _list(event, claims, groups):
    params = event.get("queryStringParameters") or {}
    filters = Attr("SK").eq("METADATA")
    if params.get("status"):
        filters &= Attr("status").eq(params["status"])
    if params.get("category"):
        filters &= Attr("category").eq(params["category"])
    if params.get("q"):
        query = params["q"]
        filters &= (
            Attr("assetTag").contains(query)
            | Attr("description").contains(query)
            | Attr("manufacturer").contains(query)
        )

    result = TABLE.scan(FilterExpression=filters, Limit=100)
    permitted = [_clean_asset(item) for item in result.get("Items", []) if can_read(groups, claims, item)]
    return response(200, {"items": permitted, "count": len(permitted)})


def _update(event, asset_id, claims, groups):
    existing = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")
    if not existing:
        return response(404, {"error": "NotFound", "message": "Asset was not found."})

    payload = _body(event)
    immutable = {"assetId", "PK", "SK", "createdAt", "createdBy"}
    changed_fields = set(payload) - immutable
    if not changed_fields:
        raise ValidationError("No editable fields were supplied.")
    if not validate_update_permissions(groups, changed_fields):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to update these asset fields."})

    candidate = {**_clean_asset(existing), **{k: v for k, v in payload.items() if k not in immutable}}
    validate_asset(candidate)
    candidate["purchaseValue"] = Decimal(str(candidate["purchaseValue"]))
    candidate["salvageValue"] = Decimal(str(candidate["salvageValue"]))
    candidate["updatedAt"] = datetime.now(timezone.utc).isoformat()
    candidate["updatedBy"] = claims.get("sub")

    old_tag = existing.get("assetTag")
    new_tag = candidate.get("assetTag")

    if new_tag != old_tag:
        try:
            TABLE.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": TABLE_NAME,
                            "Item": _serialize({**candidate, **_asset_key(asset_id)}),
                            "ConditionExpression": "attribute_exists(PK)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": TABLE_NAME,
                            "Item": _serialize({**_asset_tag_key(new_tag), "assetId": asset_id}),
                            "ConditionExpression": "attribute_not_exists(PK)",
                        }
                    },
                    {
                        "Delete": {
                            "TableName": TABLE_NAME,
                            "Key": _serialize(_asset_tag_key(old_tag)),
                        }
                    },
                ]
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            if _tag_conflict(exc):
                return response(409, {"error": "Conflict", "message": "An asset with this asset tag already exists."})
            return response(404, {"error": "NotFound", "message": "Asset was not found."})
    else:
        TABLE.put_item(Item={**candidate, **_asset_key(asset_id)}, ConditionExpression="attribute_exists(PK)")

    LOGGER.info("Asset updated assetId=%s actorSub=%s fields=%s", asset_id, claims.get("sub"), sorted(changed_fields))
    return response(200, {"assetId": asset_id, "message": "Asset updated successfully."})


def lambda_handler(event, _context):
    method = event.get("httpMethod", "")
    asset_id = (event.get("pathParameters") or {}).get("assetId")
    claims, groups = _identity(event)

    if not claims.get("sub"):
        return response(401, {"error": "Unauthorized", "message": "Sign in to access this resource."})

    try:
        if method == "POST" and not asset_id:
            return _create(event, claims, groups)
        if method == "GET" and asset_id:
            return _get(asset_id, claims, groups)
        if method == "GET":
            return _list(event, claims, groups)
        if method == "PUT" and asset_id:
            return _update(event, asset_id, claims, groups)
        return response(405, {"error": "MethodNotAllowed", "message": "Method is not supported."})
    except ValidationError as exc:
        return response(400, {"error": "ValidationError", "message": str(exc), "fields": exc.fields})
    except Exception:
        LOGGER.exception("Unhandled asset API error")
        return response(500, {"error": "InternalServerError", "message": "The request could not be completed."})

