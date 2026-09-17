import json


def lambda_handler(_event, _context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"status": "UP", "service": "smart-asset-tracker"}),
    }

