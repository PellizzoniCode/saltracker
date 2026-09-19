import json
import os
import boto3
import uuid
from datetime import datetime, timezone
from decimal import Decimal


# Get the DynamoDB table name from the Lambda environment variable
TABLE_NAME = os.environ["TABLE_NAME"]

# Connect to DynamoDB
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def decimal_default(value):
    """Convert DynamoDB Decimal values so they can be returned as JSON."""
    if isinstance(value, Decimal):
        return float(value)

    raise TypeError


def lambda_handler(event, context):
    try:
        # Get the authenticated user's Cognito claims from API Gateway
        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        # Read the Cognito groups the authenticated user belongs to
        groups_claim = claims.get("cognito:groups", "")

        if isinstance(groups_claim, str):
            user_groups = {
                group.strip()
                for group in groups_claim.split(",")
                if group.strip()
            }
        else:
            user_groups = set(groups_claim or [])

        # Only Technicians and Administrators may create assets
        allowed_groups = {"Technician", "Administrator"}

        if not user_groups.intersection(allowed_groups):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "You are not authorized to create assets"
                })
            }

        # API Gateway sends the request body to Lambda as a JSON string
        body = json.loads(event.get("body") or "{}")

        # Fields that must be supplied when creating an asset
        required_fields = [
            "assetTag",
            "category",
            "assignedEmployee",
            "department"
        ]

        # Check whether any required fields are missing
        missing_fields = [
            field
            for field in required_fields
            if not body.get(field)
        ]

        if missing_fields:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Missing required fields",
                    "missingFields": missing_fields
                })
            }

        # Generate a unique ID for the new asset
        asset_id = str(uuid.uuid4())

        # Record the creation time in UTC
        created_at = datetime.now(timezone.utc).isoformat()

        # Build the DynamoDB asset item
        item = {
            "PK": f"ASSET#{asset_id}",
            "SK": "METADATA",

            "GSI1PK": f"EMPLOYEE#{body['assignedEmployee']}",
            "GSI1SK": f"ASSET#{asset_id}",

            "GSI2PK": f"DEPARTMENT#{body['department']}",
            "GSI2SK": f"ASSET#{asset_id}",

            "entityType": "ASSET",

            "assetId": asset_id,
            "assetTag": body["assetTag"],
            "category": body["category"],
            "assignedEmployee": body["assignedEmployee"],
            "department": body["department"],

            "createdAt": created_at,
            "updatedAt": created_at
        }

        # Optional asset fields
        optional_fields = [
            "description",
            "manufacturer",
            "model",
            "serialNumber",
            "building",
            "room",
            "condition",
            "status",
            "purchaseDate",
            "purchaseValue",
            "salvageValue",
            "usefulLifeYears"
        ]

        # Add optional fields only if they were provided
        for field in optional_fields:
            if field in body and body[field] is not None:
                value = body[field]

                # DynamoDB does not accept Python float values directly
                if isinstance(value, float):
                    value = Decimal(str(value))

                item[field] = value

        # Write the new asset into DynamoDB
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK)"
        )

        # Return the newly created asset
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(
                {
                    "message": "Asset created successfully",
                    "asset": item
                },
                default=decimal_default
            )
        }

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Request body must contain valid JSON"
            })
        }

    except Exception as error:
        print(f"Error creating asset: {error}")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Internal server error"
            })
        }
