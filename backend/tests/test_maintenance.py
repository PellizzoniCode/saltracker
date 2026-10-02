import importlib.util
import json
import os
import pathlib
import sys
import types
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


API_DIR = pathlib.Path(__file__).parents[1] / "asset_api"
sys.path.insert(0, str(API_DIR))


class _Condition:
    def __init__(self, name):
        self.name = name

    def eq(self, value):
        return self

    def begins_with(self, value):
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
    boto3.resource = MagicMock(return_value=types.SimpleNamespace(Table=lambda name: table))
    boto3.client = MagicMock(return_value=transactions)

    conditions = types.ModuleType("boto3.dynamodb.conditions")
    conditions.Attr = _Condition
    conditions.Key = _Condition

    types_module = types.ModuleType("boto3.dynamodb.types")
    types_module.TypeSerializer = _Serializer

    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = _ClientError

    modules = {
        "boto3": boto3,
        "boto3.dynamodb": types.ModuleType("boto3.dynamodb"),
        "boto3.dynamodb.conditions": conditions,
        "boto3.dynamodb.types": types_module,
        "botocore": types.ModuleType("botocore"),
        "botocore.exceptions": exceptions,
    }

    spec = importlib.util.spec_from_file_location("maintenance_api_under_test", API_DIR / "app.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules), patch.dict(os.environ, {"ASSET_TABLE_NAME": "test-assets"}):
        spec.loader.exec_module(module)
    return module, table, transactions


ASSET = {
    "PK": "ASSET#AST-0001",
    "SK": "METADATA",
    "assetId": "AST-0001",
    "department": "IT",
    "assignedUserId": "employee-1",
    "lastMaintenanceDate": "2026-01-01",
}

RECORD = {
    "PK": "ASSET#AST-0001",
    "SK": "MAINTENANCE#2026-08-15#MNT-0001",
    "maintenanceId": "MNT-0001",
    "assetId": "AST-0001",
    "performedDate": "2026-08-15",
    "maintenanceType": "Cleaning",
    "notes": "Removed external dust.",
    "performedBy": "tech-1",
    "cost": "25.00",
    "conditionAfterService": "Good",
    "createdAt": "2026-08-15T10:00:00+00:00",
}

TECHNICIAN = ({"sub": "tech-1", "custom:department": "IT"}, {"Technician"})
ADMIN = ({"sub": "admin-1"}, {"Administrator"})


def _event(body=None, query=None):
    return {"body": json.dumps(body) if body is not None else None, "queryStringParameters": query}


def _conflict():
    return _ClientError({
        "Error": {"Code": "TransactionCanceledException"},
        "CancellationReasons": [{"Code": "ConditionalCheckFailed"}],
    })


class MaintenanceCreateTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, self.transactions = _load_api()
        self.table.get_item.return_value = {"Item": dict(ASSET)}

    def _create(self, body, identity=TECHNICIAN):
        return self.api._create_maintenance(_event(body), "AST-0001", *identity)

    def test_technician_records_maintenance_as_authenticated_identity(self):
        result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair", "cost": "25.00"})

        self.assertEqual(result["statusCode"], 201)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        item = writes[0]["Put"]["Item"]
        self.assertEqual(item["performedBy"], {"S": "tech-1"})
        self.assertTrue(item["SK"]["S"].startswith("MAINTENANCE#2026-08-15#MNT-"))
        self.assertEqual(writes[0]["Put"]["ConditionExpression"], "attribute_not_exists(PK)")

    def test_client_supplied_performed_by_is_rejected(self):
        with self.assertRaises(self.api.ValidationError) as raised:
            self._create({
                "performedDate": "2026-08-15",
                "maintenanceType": "Repair",
                "performedBy": "someone-else",
            })

        self.assertIn("performedBy", raised.exception.fields)
        self.transactions.transact_write_items.assert_not_called()

    def test_technician_outside_department_is_forbidden(self):
        identity = ({"sub": "tech-2", "custom:department": "Finance"}, {"Technician"})

        result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"}, identity)

        self.assertEqual(result["statusCode"], 403)
        self.transactions.transact_write_items.assert_not_called()

    def test_read_only_roles_cannot_record_maintenance(self):
        for groups in ({"Employee"}, {"Manager"}, {"Auditor"}):
            with self.subTest(groups=groups):
                identity = ({"sub": "employee-1", "custom:department": "IT"}, groups)
                result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"}, identity)
                self.assertEqual(result["statusCode"], 403)
        self.transactions.transact_write_items.assert_not_called()

    def test_missing_asset_returns_not_found(self):
        self.table.get_item.return_value = {}

        result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"})

        self.assertEqual(result["statusCode"], 404)

    def test_later_date_bumps_asset_maintenance_date(self):
        self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"})

        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 2)
        update = writes[1]["Update"]
        self.assertEqual(list(update["ExpressionAttributeNames"].values()), ["lastMaintenanceDate"])
        self.assertEqual(update["ExpressionAttributeValues"][":date"], {"S": "2026-08-15"})

    def test_cleaning_also_bumps_last_cleaning_date(self):
        self._create({"performedDate": "2026-08-15", "maintenanceType": "Cleaning"})

        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        names = writes[1]["Update"]["ExpressionAttributeNames"].values()
        self.assertEqual(sorted(names), ["lastCleaningDate", "lastMaintenanceDate"])

    def test_earlier_date_leaves_asset_untouched(self):
        self._create({"performedDate": "2025-12-01", "maintenanceType": "Repair"})

        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 1)
        self.assertIn("Put", writes[0])

    def test_non_string_asset_date_is_treated_as_stale(self):
        self.table.get_item.return_value = {"Item": {**ASSET, "lastMaintenanceDate": 5}}

        result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"})

        self.assertEqual(result["statusCode"], 201)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        update = writes[1]["Update"]
        self.assertIn("NOT attribute_type(#f0, :string)", update["ConditionExpression"])
        self.assertEqual(update["ExpressionAttributeValues"][":string"], {"S": "S"})

    def test_concurrent_change_returns_conflict(self):
        self.transactions.transact_write_items.side_effect = _conflict()

        result = self._create({"performedDate": "2026-08-15", "maintenanceType": "Repair"})

        self.assertEqual(result["statusCode"], 409)

    def test_future_date_is_rejected(self):
        future = (date.today() + timedelta(days=2)).isoformat()

        with self.assertRaises(self.api.ValidationError):
            self._create({"performedDate": future, "maintenanceType": "Repair"})


class MaintenanceReadTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, _ = _load_api()
        self.table.get_item.return_value = {"Item": dict(ASSET)}

    def test_list_queries_asset_partition_newest_first(self):
        self.table.query.return_value = {
            "Items": [dict(RECORD)],
            "LastEvaluatedKey": {"PK": RECORD["PK"], "SK": RECORD["SK"]},
        }

        result = self.api._list_maintenance(_event(), "AST-0001", {"sub": "employee-1"}, {"Employee"})

        self.assertEqual(result["statusCode"], 200)
        request = self.table.query.call_args.kwargs
        self.assertFalse(request["ScanIndexForward"])
        self.assertNotIn("IndexName", request)
        body = json.loads(result["body"])
        self.assertEqual(body["items"][0]["maintenanceId"], "MNT-0001")
        self.assertNotIn("PK", body["items"][0])
        self.assertIn("nextToken", body)

    def test_list_accepts_its_own_next_token(self):
        self.table.query.return_value = {"Items": []}
        token = self.api._encode_next_token({"PK": RECORD["PK"], "SK": RECORD["SK"]})

        result = self.api._list_maintenance(_event(query={"nextToken": token}), "AST-0001", *ADMIN)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(self.table.query.call_args.kwargs["ExclusiveStartKey"]["SK"], RECORD["SK"])

    def test_list_rejects_next_token_from_another_asset(self):
        token = self.api._encode_next_token({"PK": "ASSET#AST-9999", "SK": "MAINTENANCE#2026-01-01#MNT-9"})

        with self.assertRaises(self.api.ValidationError):
            self.api._list_maintenance(_event(query={"nextToken": token}), "AST-0001", *ADMIN)
        self.table.query.assert_not_called()

    def test_employee_cannot_list_unassigned_asset_history(self):
        result = self.api._list_maintenance(_event(), "AST-0001", {"sub": "employee-2"}, {"Employee"})

        self.assertEqual(result["statusCode"], 403)
        self.table.query.assert_not_called()

    def test_get_returns_not_found_for_unknown_record(self):
        self.table.query.return_value = {"Items": []}

        result = self.api._get_maintenance("AST-0001", "MNT-9999", *ADMIN)

        self.assertEqual(result["statusCode"], 404)


class MaintenanceManageTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, self.transactions = _load_api()
        self.table.get_item.return_value = {"Item": dict(ASSET)}
        self.table.query.return_value = {"Items": [dict(RECORD)]}

    def test_technician_cannot_update_or_delete(self):
        update = self.api._update_maintenance(_event({"notes": "x"}), "AST-0001", "MNT-0001", *TECHNICIAN)
        delete = self.api._delete_maintenance("AST-0001", "MNT-0001", *TECHNICIAN)

        self.assertEqual(update["statusCode"], 403)
        self.assertEqual(delete["statusCode"], 403)
        self.transactions.transact_write_items.assert_not_called()
        self.table.delete_item.assert_not_called()

    def test_admin_update_keeps_original_performer(self):
        self.table.get_item.return_value = {"Item": {
            **ASSET, "lastMaintenanceDate": "2026-09-01", "lastCleaningDate": "2026-09-01",
        }}

        result = self.api._update_maintenance(_event({"notes": "Updated"}), "AST-0001", "MNT-0001", *ADMIN)

        self.assertEqual(result["statusCode"], 200)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 1)
        item = writes[0]["Put"]["Item"]
        self.assertEqual(item["performedBy"], {"S": "tech-1"})
        self.assertEqual(item["updatedBy"], {"S": "admin-1"})
        self.assertEqual(item["notes"], {"S": "Updated"})

    def test_notes_only_edit_leaves_asset_dates_alone(self):
        # The asset has no lastCleaningDate, but nothing about the service itself changed.
        result = self.api._update_maintenance(_event({"notes": "Typo fixed"}), "AST-0001", "MNT-0001", *ADMIN)

        self.assertEqual(result["statusCode"], 200)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 1)
        self.assertIn("Put", writes[0])

    def test_admin_cannot_override_performer(self):
        with self.assertRaises(self.api.ValidationError):
            self.api._update_maintenance(_event({"performedBy": "admin-1"}), "AST-0001", "MNT-0001", *ADMIN)
        self.transactions.transact_write_items.assert_not_called()

    def test_changing_date_moves_record(self):
        result = self.api._update_maintenance(
            _event({"performedDate": "2026-08-20"}), "AST-0001", "MNT-0001", *ADMIN,
        )

        self.assertEqual(result["statusCode"], 200)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(writes[0]["Delete"]["Key"]["SK"], {"S": RECORD["SK"]})
        self.assertEqual(writes[1]["Put"]["Item"]["SK"], {"S": "MAINTENANCE#2026-08-20#MNT-0001"})
        self.assertIn("Update", writes[2])

    def test_empty_update_is_rejected(self):
        with self.assertRaises(self.api.ValidationError):
            self.api._update_maintenance(_event({}), "AST-0001", "MNT-0001", *ADMIN)

    def test_admin_deletes_record(self):
        result = self.api._delete_maintenance("AST-0001", "MNT-0001", *ADMIN)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(
            self.table.delete_item.call_args.kwargs["Key"],
            {"PK": RECORD["PK"], "SK": RECORD["SK"]},
        )

    def test_delete_unknown_record_returns_not_found(self):
        self.table.query.return_value = {"Items": []}

        result = self.api._delete_maintenance("AST-0001", "MNT-9999", *ADMIN)

        self.assertEqual(result["statusCode"], 404)
        self.table.delete_item.assert_not_called()


class MaintenanceRoutingTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, _ = _load_api()
        self.table.get_item.return_value = {"Item": dict(ASSET)}
        self.table.query.return_value = {"Items": [dict(RECORD)]}

    def _event(self, method, resource, maintenance_id=None):
        path = {"assetId": "AST-0001"}
        if maintenance_id:
            path["maintenanceId"] = maintenance_id
        return {
            "httpMethod": method,
            "resource": resource,
            "pathParameters": path,
            "requestContext": {"authorizer": {"claims": {"sub": "admin-1", "cognito:groups": "Administrator"}}},
        }

    def test_routes_maintenance_requests(self):
        cases = [
            ("GET", "/assets/{assetId}/maintenance", None, 200),
            ("GET", "/assets/{assetId}/maintenance/{maintenanceId}", "MNT-0001", 200),
            ("DELETE", "/assets/{assetId}/maintenance/{maintenanceId}", "MNT-0001", 200),
            ("PATCH", "/assets/{assetId}/maintenance", None, 405),
        ]
        for method, resource, maintenance_id, status in cases:
            with self.subTest(method=method, resource=resource):
                result = self.api.lambda_handler(self._event(method, resource, maintenance_id), None)
                self.assertEqual(result["statusCode"], status)

    def test_spoofed_performer_returns_bad_request(self):
        event = self._event("POST", "/assets/{assetId}/maintenance")
        event["body"] = json.dumps({
            "performedDate": "2026-08-15",
            "maintenanceType": "Repair",
            "performedBy": "someone-else",
        })

        result = self.api.lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(json.loads(result["body"])["fields"], ["performedBy"])

    def test_asset_get_still_routes_to_asset_handler(self):
        result = self.api.lambda_handler(self._event("GET", "/assets/{assetId}"), None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["assetId"], "AST-0001")
        self.table.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
