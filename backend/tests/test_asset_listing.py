import importlib.util
import json
import os
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


API_DIR = pathlib.Path(__file__).parents[1] / "asset_api"
sys.path.insert(0, str(API_DIR))


class _Condition:
    def __init__(self, name):
        self.name = name

    def eq(self, value):
        return self

    def contains(self, value):
        return self

    def __and__(self, other):
        return self

    def __or__(self, other):
        return self


class _Serializer:
    def serialize(self, value):
        return {"S": str(value)}


class _ClientError(Exception):
    def __init__(self, response):
        self.response = response


def _load_api():
    table = MagicMock(name="table")
    table.name = "test-assets"

    transactions = MagicMock(name="transactions")

    boto3 = types.ModuleType("boto3")
    boto3.resource = MagicMock(
        return_value=types.SimpleNamespace(Table=lambda name: table)
    )
    boto3.client = MagicMock(return_value=transactions)

    dynamodb = types.ModuleType("boto3.dynamodb")

    conditions = types.ModuleType("boto3.dynamodb.conditions")
    conditions.Attr = _Condition
    conditions.Key = _Condition

    types_module = types.ModuleType("boto3.dynamodb.types")
    types_module.TypeSerializer = _Serializer

    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = _ClientError

    modules = {
        "boto3": boto3,
        "boto3.dynamodb": dynamodb,
        "boto3.dynamodb.conditions": conditions,
        "boto3.dynamodb.types": types_module,
        "botocore": botocore,
        "botocore.exceptions": exceptions,
    }

    spec = importlib.util.spec_from_file_location(
        "asset_listing_api_under_test",
        API_DIR / "app.py",
    )

    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, modules), patch.dict(
        os.environ,
        {"ASSET_TABLE_NAME": "test-assets"},
    ):
        spec.loader.exec_module(module)

    return module, table


class AssetListingTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table = _load_api()
        self.event = {"queryStringParameters": None}

    def test_employee_uses_assigned_user_index(self):
        self.table.query.return_value = {"Items": []}

        result = self.api._list(
            self.event,
            {"sub": "employee-123"},
            {"Employee"},
        )

        self.assertEqual(result["statusCode"], 200)
        self.table.query.assert_called_once()
        self.table.scan.assert_not_called()

        request = self.table.query.call_args.kwargs
        self.assertEqual(request["IndexName"], "AssignedUserIndex")
        self.assertIn("KeyConditionExpression", request)

    def test_manager_uses_department_index(self):
        self.table.query.return_value = {"Items": []}

        result = self.api._list(
            self.event,
            {
                "sub": "manager-123",
                "custom:department": "IT",
            },
            {"Manager"},
        )

        self.assertEqual(result["statusCode"], 200)
        self.table.query.assert_called_once()
        self.table.scan.assert_not_called()

        request = self.table.query.call_args.kwargs
        self.assertEqual(request["IndexName"], "DepartmentIndex")
        self.assertIn("KeyConditionExpression", request)

    def test_administrator_uses_scan(self):
        self.table.scan.return_value = {"Items": []}

        result = self.api._list(
            self.event,
            {"sub": "admin-123"},
            {"Administrator"},
        )

        self.assertEqual(result["statusCode"], 200)
        self.table.scan.assert_called_once()
        self.table.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
