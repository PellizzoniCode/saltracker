"""Tests the legacy-page check and the atomic tag reservation in the API."""

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


class _Attr:
    def __init__(self, name):
        self.name = name

    def eq(self, value):
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
    s3 = MagicMock(name="s3")
    boto3 = types.ModuleType("boto3")
    boto3.resource = MagicMock(return_value=types.SimpleNamespace(Table=lambda name: table))
    boto3.client = MagicMock(side_effect=lambda service, *a, **k: {"dynamodb": transactions, "s3": s3}[service])
    dynamodb = types.ModuleType("boto3.dynamodb")
    conditions = types.ModuleType("boto3.dynamodb.conditions")
    conditions.Attr = _Attr
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
    spec = importlib.util.spec_from_file_location("asset_api_under_test", API_DIR / "app.py")
    module = importlib.util.module_from_spec(spec)
    env = {"ASSET_TABLE_NAME": "test-assets", "ASSET_PHOTO_BUCKET": "private-photos"}
    with patch.dict(sys.modules, modules), patch.dict(os.environ, env):
        spec.loader.exec_module(module)
    return module, table, transactions, s3


ASSET = {
    "assetTag": "TAG-0001", "category": "Laptop", "description": "Business laptop",
    "purchaseDate": "2026-09-01", "inServiceDate": "2026-09-01",
    "purchaseValue": "1500.00", "salvageValue": "100.00",
    "usefulLifeMonths": 48, "condition": "Good", "status": "Available",
}


class UniqueTagTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, self.transactions, self.s3 = _load_api()
        self.event = {"body": json.dumps(ASSET)}

    def test_duplicate_on_later_scan_page_is_rejected(self):
        self.table.scan.side_effect = [
            {"Items": [], "LastEvaluatedKey": {"PK": "ASSET#OTHER", "SK": "METADATA"}},
            {"Items": [{"assetId": "AST-EXISTING", "assetTag": "tag-0001"}]},
        ]
        result = self.api._create(self.event, {"sub": "admin"}, {"Administrator"})
        self.assertEqual(result["statusCode"], 409)
        self.transactions.transact_write_items.assert_not_called()
        self.assertIn("ExclusiveStartKey", self.table.scan.call_args_list[1].kwargs)

    def test_create_reserves_tag_and_asset_in_one_transaction(self):
        self.table.scan.return_value = {"Items": []}
        result = self.api._create(self.event, {"sub": "admin"}, {"Administrator"})
        self.assertEqual(result["statusCode"], 201)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 2)
        self.assertEqual(writes[0]["Put"]["Item"]["PK"], {"S": "ASSET_TAG#TAG-0001"})
        self.assertEqual(writes[0]["Put"]["ConditionExpression"], "attribute_not_exists(PK)")
        self.assertEqual(writes[1]["Put"]["ConditionExpression"], "attribute_not_exists(PK)")

    def test_tag_rename_checks_legacy_assets(self):
        existing = {**ASSET, "assetId": "AST-OWN", "PK": "ASSET#AST-OWN", "SK": "METADATA"}
        self.table.get_item.return_value = {"Item": existing}
        self.table.scan.return_value = {"Items": [{"assetId": "AST-OTHER", "assetTag": "TAG-0002"}]}
        event = {"body": json.dumps({"assetTag": "TAG-0002"})}
        result = self.api._update(event, "AST-OWN", {"sub": "admin"}, {"Administrator"})
        self.assertEqual(result["statusCode"], 409)
        self.transactions.transact_write_items.assert_not_called()

    def test_tag_rename_moves_reservation_with_asset(self):
        existing = {**ASSET, "assetId": "AST-OWN", "PK": "ASSET#AST-OWN", "SK": "METADATA"}
        self.table.get_item.side_effect = [
            {"Item": existing},
            {"Item": {"PK": "ASSET_TAG#TAG-0001", "SK": "UNIQUE", "assetId": "AST-OWN"}},
        ]
        self.table.scan.return_value = {"Items": []}
        event = {"body": json.dumps({"assetTag": "TAG-0002"})}
        result = self.api._update(event, "AST-OWN", {"sub": "admin"}, {"Administrator"})
        self.assertEqual(result["statusCode"], 200)
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(len(writes), 3)
        self.assertEqual(writes[0]["Put"]["Item"]["PK"], {"S": "ASSET_TAG#TAG-0002"})
        self.assertEqual(writes[2]["Delete"]["Key"]["PK"], {"S": "ASSET_TAG#TAG-0001"})

    def test_concurrent_tag_reservation_conflict_returns_409(self):
        self.table.scan.return_value = {"Items": []}
        self.transactions.transact_write_items.side_effect = _ClientError({
            "Error": {"Code": "TransactionCanceledException"},
            "CancellationReasons": [{"Code": "ConditionalCheckFailed"}, {"Code": "None"}],
        })
        result = self.api._create(self.event, {"sub": "admin"}, {"Administrator"})
        self.assertEqual(result["statusCode"], 409)


class ClaimPendingPhotoTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, self.transactions, self.s3 = _load_api()

    def test_claim_photo_moves_pending_object_to_claimed_prefix(self):
        claimed = self.api._claim_photo("pending/user-1/abc123.jpg")

        self.assertEqual(claimed, "claimed/user-1/abc123.jpg")
        self.s3.copy_object.assert_called_once_with(
            Bucket="private-photos",
            CopySource={"Bucket": "private-photos", "Key": "pending/user-1/abc123.jpg"},
            Key="claimed/user-1/abc123.jpg",
        )
        self.s3.delete_object.assert_called_once_with(
            Bucket="private-photos", Key="pending/user-1/abc123.jpg"
        )

    def test_claim_photo_on_already_claimed_key_is_a_no_op(self):
        claimed = self.api._claim_photo("claimed/user-1/abc123.jpg")

        self.assertEqual(claimed, "claimed/user-1/abc123.jpg")
        self.s3.copy_object.assert_not_called()
        self.s3.delete_object.assert_not_called()

    def test_claim_photo_raises_when_pending_object_is_missing(self):
        self.s3.copy_object.side_effect = _ClientError({"Error": {"Code": "NoSuchKey"}})

        with self.assertRaises(self.api.ValidationError):
            self.api._claim_photo("pending/user-1/missing.jpg")

    def test_create_claims_pending_photo_before_saving_asset(self):
        self.table.scan.return_value = {"Items": []}
        event = {"body": json.dumps({**ASSET, "imageKey": "pending/user-1/abc123.jpg"})}

        result = self.api._create(event, {"sub": "admin"}, {"Administrator"})

        self.assertEqual(result["statusCode"], 201)
        self.s3.copy_object.assert_called_once()
        writes = self.transactions.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(writes[1]["Put"]["Item"]["imageKey"], {"S": "claimed/user-1/abc123.jpg"})

    def test_update_claims_pending_photo_only_when_imagekey_changes(self):
        existing = {
            **ASSET, "assetId": "AST-OWN", "PK": "ASSET#AST-OWN", "SK": "METADATA",
            "imageKey": "claimed/user-1/old.jpg",
        }
        self.table.get_item.return_value = {"Item": existing}
        event = {"body": json.dumps({"imageKey": "pending/user-1/new.jpg"})}

        result = self.api._update(event, "AST-OWN", {"sub": "admin"}, {"Administrator"})

        self.assertEqual(result["statusCode"], 200)
        self.s3.copy_object.assert_called_once_with(
            Bucket="private-photos",
            CopySource={"Bucket": "private-photos", "Key": "pending/user-1/new.jpg"},
            Key="claimed/user-1/new.jpg",
        )
        saved_item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(saved_item["imageKey"], "claimed/user-1/new.jpg")

    def test_update_without_imagekey_change_does_not_touch_s3(self):
        existing = {
            **ASSET, "assetId": "AST-OWN", "PK": "ASSET#AST-OWN", "SK": "METADATA",
            "imageKey": "claimed/user-1/old.jpg",
        }
        self.table.get_item.return_value = {"Item": existing}
        event = {"body": json.dumps({"description": "Updated description"})}

        result = self.api._update(event, "AST-OWN", {"sub": "admin"}, {"Administrator"})

        self.assertEqual(result["statusCode"], 200)
        self.s3.copy_object.assert_not_called()
        self.s3.delete_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
