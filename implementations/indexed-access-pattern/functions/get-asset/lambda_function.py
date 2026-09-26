import json
import os
import boto3
from decimal import Decimal


TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def decimal_default(value):
    """Convert DynamoDB Decimal numbers so they can be returned as JSON."""
    if isinstance(value, Decimal):
        return float(value)

    raise TypeError


def get_user_groups(claims):
    """Convert the Cognito groups claim into a Python set."""
    groups_claim = claims.get("cognito:groups", "")

    if isinstance(groups_claim, str):
        return {
            group.strip()
            for group in groups_claim.strip("[]").split(",")
            if group.strip()
        }

    return set(groups_claim or [])


def lambda_handler(event, context):
    try:
        # Get verified Cognito claims passed by API Gateway
        claims = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
        )

        user_groups = get_user_groups(claims)
        user_email = claims.get("email")

        # Only known application roles may continue
        valid_groups = {
            "Employee",
            "Technician",
            "Manager",
            "Administrator",
            "Auditor"
        }

        if not user_groups.intersection(valid_groups):
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "You are not authorized to view assets"
                })
            }

        # Get asset ID from the URL
        asset_id = event["pathParameters"]["assetId"]

        # Support both our original ASSET-001 format
        # and UUID-based asset IDs
        if asset_id.startswith("ASSET-"):
            asset_number = asset_id.replace("ASSET-", "", 1)
            pk = f"ASSET#{asset_number}"
        else:
            pk = f"ASSET#{asset_id}"

        # Retrieve the asset from DynamoDB
        response = table.get_item(
            Key={
                "PK": pk,
                "SK": "METADATA"
            }
        )

        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Asset not found"
                })
            }

        asset = response["Item"]

        # Employee:
        # may only view assets assigned to their own Cognito email
        if "Employee" in user_groups:
            if not user_email:
                return {
                    "statusCode": 403,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "message": "User identity could not be verified"
                    })
                }

            if asset.get("assignedEmployee") != user_email:
                return {
                    "statusCode": 403,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "message": "You are not authorized to view this asset"
                    })
                }

        # Manager:
        # department-based authorization will be implemented next
        if "Manager" in user_groups:
            return {
                "statusCode": 403,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "Manager department access is not configured yet"
                })
            }

        # Technician, Administrator and Auditor may view the asset.
        # Their modification permissions will be controlled separately.

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(
                asset,
                default=decimal_default
            )
        }

    except KeyError:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "assetId is required"
            })
        }

    except Exception as error:
        print(f"Error retrieving asset: {error}")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Internal server error"
            })
        }
