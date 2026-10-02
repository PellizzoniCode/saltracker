import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from domain import (
    MAINTENANCE_FIELDS,
    SERVICE_DATE_FIELDS,
    ValidationError,
    can_create,
    can_manage_maintenance,
    can_read,
    can_record_maintenance,
    parse_groups,
    validate_asset,
    validate_create_permissions,
    validate_maintenance,
    validate_update_permissions,
)


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
TABLE = boto3.resource("dynamodb").Table(os.environ["ASSET_TABLE_NAME"])
TRANSACTIONS = boto3.client("dynamodb")
SERIALIZER = TypeSerializer()
MAINTENANCE_PREFIX = "MAINTENANCE#"
MAINTENANCE_COLLECTION = "/assets/{assetId}/maintenance"
MAINTENANCE_ITEM = "/assets/{assetId}/maintenance/{maintenanceId}"
MAINTENANCE_ID_INDEX = "MaintenanceIdIndex"


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


def _asset_tag(tag):
    return tag.strip().upper()


def _tag_key(tag):
    return {"PK": f"ASSET_TAG#{_asset_tag(tag)}", "SK": "UNIQUE"}


def _wire_item(item):
    return {name: SERIALIZER.serialize(value) for name, value in item.items()}


def _existing_tag(tag, excluding_asset_id=None):
    """Cover assets created before unique tag reservation records existed."""
    params = {
        "FilterExpression": Attr("SK").eq("METADATA"),
        "ProjectionExpression": "assetId, assetTag",
        "ConsistentRead": True,
    }
    while True:
        page = TABLE.scan(**params)
        for item in page.get("Items", []):
            current = item.get("assetTag")
            if (isinstance(current, str) and _asset_tag(current) == _asset_tag(tag)
                    and item.get("assetId") != excluding_asset_id):
                return True
        if "LastEvaluatedKey" not in page:
            return False
        params["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _condition_failed(exc):
    if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
        return False
    return any(reason.get("Code") == "ConditionalCheckFailed"
               for reason in exc.response.get("CancellationReasons", []))

def _clean_asset(item):
    if not item:
        return None

    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK"}
    }


def _normalise_index_fields(item):
    for field in ("assignedUserId", "department"):
        value = item.get(field)

        if value is None or (
            isinstance(value, str)
            and not value.strip()
        ):
            item.pop(field, None)

        elif not isinstance(value, str):
            raise ValidationError(
                f"{field} must be a string.",
                [field],
            )

        else:
            item[field] = value.strip()

    return item

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

    payload["assetTag"] = _asset_tag(payload["assetTag"])

    if "Technician" in groups and "Administrator" not in groups:
        department = claims.get("custom:department")

        if not department:
            return response(
                403,
                {
                    "error": "Forbidden",
                    "message": "Your account does not have a department assigned.",
                },
            )

        payload["department"] = department

    if _existing_tag(payload["assetTag"]):
        return response(
            409,
            {
                "error": "Conflict",
                "message": "An asset with this asset tag already exists.",
            },
        )

    asset_id = f"AST-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    item = {
        **payload,
        **_asset_key(asset_id),
        "assetId": asset_id,
        "depreciationMethod": payload.get(
            "depreciationMethod",
            "straight-line",
        ),
        "reviewStatus": payload.get(
            "reviewStatus",
            "ManualEntry",
        ),
        "createdBy": claims.get("sub"),
        "createdAt": now,
        "updatedAt": now,
    }

    item = _normalise_index_fields(item)

    item["purchaseValue"] = Decimal(str(item["purchaseValue"]))
    item["salvageValue"] = Decimal(str(item["salvageValue"]))

    # The tag reservation and the asset record commit together. Two requests
    # for the same tag cannot both succeed, even when they arrive concurrently.
    try:
        TRANSACTIONS.transact_write_items(TransactItems=[
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item({**_tag_key(payload["assetTag"]), "assetId": asset_id}),
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item(item),
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
        ])
    except ClientError as exc:
        if _condition_failed(exc):
            return response(409, {"error": "Conflict", "message": "An asset with this asset tag already exists."})
        raise

    LOGGER.info("Asset created assetId=%s actorSub=%s", asset_id, claims.get("sub"))
    return response(201, {"assetId": asset_id, "message": "Asset created successfully."})


def _get(asset_id, claims, groups):
    item = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")
    if not item:
        return response(404, {"error": "NotFound", "message": "Asset was not found."})
    if not can_read(groups, claims, item):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to view this asset."})
    return response(200, _clean_asset(item))

def _encode_next_token(last_evaluated_key):
    if not last_evaluated_key:
        return None

    raw = json.dumps(last_evaluated_key, default=_json_default).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_next_token(token):
    if not token:
        return None

    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("Invalid nextToken.")

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

    request = {
        "FilterExpression": filters,
        "Limit": 100,
    }

    if params.get("nextToken"):
        request["ExclusiveStartKey"] = _decode_next_token(params["nextToken"])

    if groups.intersection({"Administrator", "Auditor"}):
        result = TABLE.scan(**request)

    elif groups.intersection({"Manager", "Technician"}):
        department = claims.get("custom:department")

        if not department:
            return response(403, {
                "error": "Forbidden",
                "message": "Your account does not have a department assigned.",
            })

        request["IndexName"] = "DepartmentIndex"
        request["KeyConditionExpression"] = Key("department").eq(department)
        result = TABLE.query(**request)

    elif "Employee" in groups:
        request["IndexName"] = "AssignedUserIndex"
        request["KeyConditionExpression"] = Key("assignedUserId").eq(claims["sub"])
        result = TABLE.query(**request)

    else:
        return response(403, {
            "error": "Forbidden",
            "message": "You do not have permission to list assets.",
        })

    items = [_clean_asset(item) for item in result.get("Items", [])]

    body = {
            "items": items,
            "count": len(items),
    }

    if result.get("LastEvaluatedKey"):
        body["nextToken"] = _encode_next_token(result["LastEvaluatedKey"])

    return response(200, body)


def _service_dates_guard(existing):
    """Condition that the asset's service dates still hold the values this update read.

    Recording maintenance moves these dates forward in its own transaction; without
    this guard a concurrent asset update would write the stale values back.
    """
    clauses, names, values = [], {}, {}
    for index, field in enumerate(SERVICE_DATE_FIELDS):
        name = f"#sd{index}"
        names[name] = field
        if existing.get(field) is not None:
            clauses.append(f"{name} = :sd{index}")
            values[f":sd{index}"] = existing[field]
        elif field in existing:
            clauses.append(f"attribute_type({name}, :sdnull)")
            values[":sdnull"] = "NULL"
        else:
            clauses.append(f"attribute_not_exists({name})")
    return " AND ".join(clauses), names, values


def _update(event, asset_id, claims, groups):
    existing = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")
    if not existing:
        return response(404, {"error": "NotFound", "message": "Asset was not found."})

    if not can_read(groups, claims, existing):
        return response(
            403,
            {
                "error": "Forbidden",
                "message": "You cannot modify assets outside your authorized scope.",
            },
        )

    payload = _body(event)
    immutable = {"assetId", "PK", "SK", "createdAt", "createdBy"}
    changed_fields = set(payload) - immutable
    if not changed_fields:
        raise ValidationError("No editable fields were supplied.")
    if not validate_update_permissions(groups, changed_fields):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to update these asset fields."})

    candidate = {
        **_clean_asset(existing),
        **{
            key: value
            for key, value in payload.items()
            if key not in immutable
        },
    }

    validate_asset(candidate)
    candidate = _normalise_index_fields(candidate)

    candidate["assetTag"] = _asset_tag(candidate["assetTag"])
    candidate["purchaseValue"] = Decimal(str(candidate["purchaseValue"]))
    candidate["salvageValue"] = Decimal(str(candidate["salvageValue"]))
    candidate["updatedAt"] = datetime.now(timezone.utc).isoformat()
    candidate["updatedBy"] = claims.get("sub")

    old_tag = _asset_tag(existing["assetTag"])
    new_tag = candidate["assetTag"]
    dates_guard, guard_names, guard_values = _service_dates_guard(existing)

    if old_tag != new_tag:
        if _existing_tag(new_tag, excluding_asset_id=asset_id):
            return response(409, {"error": "Conflict", "message": "An asset with this asset tag already exists."})

        writes = [
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item({**_tag_key(new_tag), "assetId": asset_id}),
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item({**candidate, **_asset_key(asset_id)}),
                "ConditionExpression": f"attribute_exists(PK) AND assetTag = :old_tag AND {dates_guard}",
                "ExpressionAttributeNames": guard_names,
                "ExpressionAttributeValues": {
                    ":old_tag": SERIALIZER.serialize(existing["assetTag"]),
                    **{key: SERIALIZER.serialize(value) for key, value in guard_values.items()},
                },
            }},
        ]
        old_reservation = TABLE.get_item(Key=_tag_key(old_tag), ConsistentRead=True).get("Item")
        if old_reservation and old_reservation.get("assetId") == asset_id:
            writes.append({"Delete": {
                "TableName": TABLE.name,
                "Key": _wire_item(_tag_key(old_tag)),
                "ConditionExpression": "assetId = :asset_id",
                "ExpressionAttributeValues": {":asset_id": SERIALIZER.serialize(asset_id)},
            }})
        try:
            TRANSACTIONS.transact_write_items(TransactItems=writes)
        except ClientError as exc:
            if _condition_failed(exc):
                return response(409, {"error": "Conflict", "message": "The asset tag is already in use or the asset changed during your update."})
            raise
    else:
        try:
            TABLE.put_item(
                Item={**candidate, **_asset_key(asset_id)},
                ConditionExpression=f"attribute_exists(PK) AND assetTag = :old_tag AND {dates_guard}",
                ExpressionAttributeNames=guard_names,
                ExpressionAttributeValues={":old_tag": existing["assetTag"], **guard_values},
            )
        except TABLE.meta.client.exceptions.ConditionalCheckFailedException:
            return response(409, {"error": "Conflict", "message": "The asset changed during your update. Refresh and try again."})
    LOGGER.info("Asset updated assetId=%s actorSub=%s fields=%s", asset_id, claims.get("sub"), sorted(changed_fields))
    return response(200, {"assetId": asset_id, "message": "Asset updated successfully."})


def _maintenance_key(asset_id, performed_date, maintenance_id):
    return {"PK": f"ASSET#{asset_id}", "SK": f"{MAINTENANCE_PREFIX}{performed_date}#{maintenance_id}"}


def _maintenance_partition(asset_id):
    return Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(MAINTENANCE_PREFIX)


def _load_asset_for(asset_id, claims, groups):
    """Return (asset, None) when the caller may see the asset, else (None, error response)."""
    asset = TABLE.get_item(Key=_asset_key(asset_id), ConsistentRead=True).get("Item")
    if not asset:
        return None, response(404, {"error": "NotFound", "message": "Asset was not found."})
    if not can_read(groups, claims, asset):
        return None, response(403, {"error": "Forbidden", "message": "You do not have permission to view this asset."})
    return asset, None


def _find_maintenance(asset_id, maintenance_id):
    """Locate a record by ID without reading the asset's whole history.

    The sort key embeds the date, so MaintenanceIdIndex maps the ID to the item key
    and the item is then read with a strongly consistent GetItem. The index is
    eventually consistent: a record created or re-dated moments ago may be missing
    or point at its old key, so a miss falls back to searching the asset partition.
    """
    keys = TABLE.query(
        IndexName=MAINTENANCE_ID_INDEX,
        KeyConditionExpression=Key("maintenanceId").eq(maintenance_id),
    ).get("Items", [])

    for key in keys:
        # IDs are only unique in practice; never follow one into another asset's partition.
        if key.get("PK") != f"ASSET#{asset_id}":
            continue
        item = TABLE.get_item(Key={"PK": key["PK"], "SK": key["SK"]}, ConsistentRead=True).get("Item")
        if item and item.get("maintenanceId") == maintenance_id:
            return item

    return _search_maintenance_partition(asset_id, maintenance_id)


def _search_maintenance_partition(asset_id, maintenance_id):
    params = {
        "KeyConditionExpression": _maintenance_partition(asset_id),
        "FilterExpression": Attr("maintenanceId").eq(maintenance_id),
        "ConsistentRead": True,
    }
    while True:
        page = TABLE.query(**params)
        for item in page.get("Items", []):
            if item.get("maintenanceId") == maintenance_id:
                return item
        if "LastEvaluatedKey" not in page:
            return None
        params["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _normalise_maintenance(payload):
    notes = payload.get("notes")
    cost = payload.get("cost")
    return {
        "performedDate": payload["performedDate"],
        "maintenanceType": payload["maintenanceType"],
        "notes": notes.strip() if isinstance(notes, str) and notes.strip() else None,
        "cost": None if cost in (None, "") else Decimal(str(cost)),
        "conditionAfterService": payload.get("conditionAfterService"),
    }


def _asset_date_bump(asset, record):
    """Transactional update moving the asset's service dates forward, or [] when already current."""
    performed = record["performedDate"]
    fields = ["lastMaintenanceDate"]
    if record["maintenanceType"] == "Cleaning":
        fields.append("lastCleaningDate")

    stale = [
        field for field in fields
        if not isinstance(asset.get(field), str) or not asset[field] or asset[field] < performed
    ]
    if not stale:
        return []

    names = {f"#f{index}": field for index, field in enumerate(stale)}
    assignments = ", ".join(f"{name} = :date" for name in names)
    # A concurrent request may already have recorded a later date; the
    # condition then cancels the transaction instead of moving it backwards.
    guards = " AND ".join(
        f"(attribute_not_exists({name}) OR NOT attribute_type({name}, :string) OR {name} < :date)"
        for name in names
    )
    return [{"Update": {
        "TableName": TABLE.name,
        "Key": _wire_item(_asset_key(asset["assetId"])),
        "UpdateExpression": f"SET {assignments}",
        "ConditionExpression": f"attribute_exists(PK) AND {guards}",
        "ExpressionAttributeNames": names,
        "ExpressionAttributeValues": {
            ":date": SERIALIZER.serialize(performed),
            ":string": SERIALIZER.serialize("S"),
        },
    }}]


def _list_maintenance(event, asset_id, claims, groups):
    _, denied = _load_asset_for(asset_id, claims, groups)
    if denied:
        return denied

    params = event.get("queryStringParameters") or {}
    request = {
        "KeyConditionExpression": _maintenance_partition(asset_id),
        "ScanIndexForward": False,
        "Limit": 50,
    }

    if params.get("nextToken"):
        start = _decode_next_token(params["nextToken"])
        if (not isinstance(start, dict) or start.get("PK") != f"ASSET#{asset_id}"
                or not str(start.get("SK", "")).startswith(MAINTENANCE_PREFIX)):
            raise ValidationError("Invalid nextToken.")
        request["ExclusiveStartKey"] = start

    result = TABLE.query(**request)
    items = [_clean_asset(item) for item in result.get("Items", [])]
    body = {"items": items, "count": len(items)}

    if result.get("LastEvaluatedKey"):
        body["nextToken"] = _encode_next_token(result["LastEvaluatedKey"])

    return response(200, body)


def _create_maintenance(event, asset_id, claims, groups):
    if not can_record_maintenance(groups):
        return response(403, {"error": "Forbidden", "message": "You do not have permission to record maintenance."})

    asset, denied = _load_asset_for(asset_id, claims, groups)
    if denied:
        return denied

    payload = _body(event)
    validate_maintenance(payload)

    maintenance_id = f"MNT-{uuid.uuid4().hex[:8].upper()}"
    fields = _normalise_maintenance(payload)
    item = {
        **fields,
        **_maintenance_key(asset_id, fields["performedDate"], maintenance_id),
        "maintenanceId": maintenance_id,
        "assetId": asset_id,
        # Always the authenticated identity; validate_maintenance rejects a client-supplied value.
        "performedBy": claims["sub"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    try:
        TRANSACTIONS.transact_write_items(TransactItems=[
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item(item),
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
            *_asset_date_bump(asset, fields),
        ])
    except ClientError as exc:
        if _condition_failed(exc):
            return response(409, {"error": "Conflict", "message": "The asset changed while recording maintenance. Refresh and try again."})
        raise

    LOGGER.info("Maintenance recorded assetId=%s maintenanceId=%s actorSub=%s", asset_id, maintenance_id, claims["sub"])
    return response(201, {"assetId": asset_id, "maintenanceId": maintenance_id, "message": "Maintenance recorded successfully."})


def _get_maintenance(asset_id, maintenance_id, claims, groups):
    _, denied = _load_asset_for(asset_id, claims, groups)
    if denied:
        return denied

    item = _find_maintenance(asset_id, maintenance_id)
    if not item:
        return response(404, {"error": "NotFound", "message": "Maintenance record was not found."})
    return response(200, _clean_asset(item))


def _update_maintenance(event, asset_id, maintenance_id, claims, groups):
    if not can_manage_maintenance(groups):
        return response(403, {"error": "Forbidden", "message": "Only an Administrator can change maintenance records."})

    asset, denied = _load_asset_for(asset_id, claims, groups)
    if denied:
        return denied

    existing = _find_maintenance(asset_id, maintenance_id)
    if not existing:
        return response(404, {"error": "NotFound", "message": "Maintenance record was not found."})

    payload = _body(event)
    validate_maintenance(payload, partial=True)
    if not payload:
        raise ValidationError("No editable fields were supplied.")

    merged = {field: existing.get(field) for field in MAINTENANCE_FIELDS}
    merged.update(payload)
    validate_maintenance(merged)

    fields = _normalise_maintenance(merged)
    new_key = _maintenance_key(asset_id, fields["performedDate"], maintenance_id)
    item = {
        **_clean_asset(existing),
        **fields,
        **new_key,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "updatedBy": claims["sub"],
    }

    if existing["SK"] == new_key["SK"]:
        writes = [{"Put": {
            "TableName": TABLE.name,
            "Item": _wire_item(item),
            "ConditionExpression": "attribute_exists(PK)",
        }}]
    else:
        # The date is part of the sort key, so re-dating moves the record.
        writes = [
            {"Delete": {
                "TableName": TABLE.name,
                "Key": _wire_item({"PK": existing["PK"], "SK": existing["SK"]}),
                "ConditionExpression": "maintenanceId = :maintenance_id",
                "ExpressionAttributeValues": {":maintenance_id": SERIALIZER.serialize(maintenance_id)},
            }},
            {"Put": {
                "TableName": TABLE.name,
                "Item": _wire_item(item),
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
        ]

    service_changed = (fields["performedDate"] != existing.get("performedDate")
                       or fields["maintenanceType"] != existing.get("maintenanceType"))
    if service_changed:
        writes.extend(_asset_date_bump(asset, fields))

    try:
        TRANSACTIONS.transact_write_items(TransactItems=writes)
    except ClientError as exc:
        if _condition_failed(exc):
            return response(409, {"error": "Conflict", "message": "The maintenance record changed during your update. Refresh and try again."})
        raise

    LOGGER.info("Maintenance updated assetId=%s maintenanceId=%s actorSub=%s fields=%s",
                asset_id, maintenance_id, claims["sub"], sorted(payload))
    return response(200, {"assetId": asset_id, "maintenanceId": maintenance_id, "message": "Maintenance record updated successfully."})


def _delete_maintenance(asset_id, maintenance_id, claims, groups):
    if not can_manage_maintenance(groups):
        return response(403, {"error": "Forbidden", "message": "Only an Administrator can delete maintenance records."})

    _, denied = _load_asset_for(asset_id, claims, groups)
    if denied:
        return denied

    existing = _find_maintenance(asset_id, maintenance_id)
    if not existing:
        return response(404, {"error": "NotFound", "message": "Maintenance record was not found."})

    try:
        TABLE.delete_item(
            Key={"PK": existing["PK"], "SK": existing["SK"]},
            ConditionExpression="maintenanceId = :maintenance_id",
            ExpressionAttributeValues={":maintenance_id": maintenance_id},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return response(404, {"error": "NotFound", "message": "Maintenance record was not found."})
        raise

    LOGGER.info("Maintenance deleted assetId=%s maintenanceId=%s actorSub=%s", asset_id, maintenance_id, claims["sub"])
    return response(200, {"assetId": asset_id, "maintenanceId": maintenance_id, "message": "Maintenance record deleted successfully."})


def _route_maintenance(event, method, asset_id, claims, groups):
    maintenance_id = (event.get("pathParameters") or {}).get("maintenanceId")
    if event.get("resource") == MAINTENANCE_COLLECTION:
        if method == "GET":
            return _list_maintenance(event, asset_id, claims, groups)
        if method == "POST":
            return _create_maintenance(event, asset_id, claims, groups)
    elif maintenance_id:
        if method == "GET":
            return _get_maintenance(asset_id, maintenance_id, claims, groups)
        if method == "PUT":
            return _update_maintenance(event, asset_id, maintenance_id, claims, groups)
        if method == "DELETE":
            return _delete_maintenance(asset_id, maintenance_id, claims, groups)
    return response(405, {"error": "MethodNotAllowed", "message": "Method is not supported."})


def lambda_handler(event, _context):
    method = event.get("httpMethod", "")
    asset_id = (event.get("pathParameters") or {}).get("assetId")
    claims, groups = _identity(event)

    if not claims.get("sub"):
        return response(401, {"error": "Unauthorized", "message": "Sign in to access this resource."})

    try:
        if asset_id and event.get("resource") in (MAINTENANCE_COLLECTION, MAINTENANCE_ITEM):
            return _route_maintenance(event, method, asset_id, claims, groups)
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
