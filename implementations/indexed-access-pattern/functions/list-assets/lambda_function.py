import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key


TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# CORS headers allow the CloudFront frontend to read Lambda responses
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://d10114m5tqjy2i.cloudfront.net"
}


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

        # Only recognized application roles may use this function
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
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "message": "You are not authorized to view assets"
                })
            }

        # Employees may only list assets assigned to themselves
        if "Employee" in user_groups:
            if not user_email:
                return {
                    "statusCode": 403,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({
                        "message": "User identity could not be verified"
                    })
                }

            # Query EmployeeIndex using the authenticated user's email
            response = table.query(
                IndexName="EmployeeIndex",
                KeyConditionExpression=Key("GSI1PK").eq(
                    f"EMPLOYEE#{user_email}"
                )
            )

            assets = response.get("Items", [])

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {
                        "count": len(assets),
                        "assets": assets
                    },
                    default=decimal_default
                )
            }

        # Other roles will be implemented in their appropriate access paths
        return {
            "statusCode": 403,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "message": "Asset listing for this role is not configured yet"
            })
        }

    except Exception as error:
        print(f"Error listing assets: {error}")

        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "message": "Internal server error"
            })
        }
