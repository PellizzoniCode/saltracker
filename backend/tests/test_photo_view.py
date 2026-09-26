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


def load_handler():
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://s3.example/signed-get"
    table = MagicMock()
    dynamodb_resource = MagicMock()
    dynamodb_resource.Table.return_value = table

    boto3 = types.ModuleType("boto3")
    boto3.client = MagicMock(return_value=s3)
    boto3.resource = MagicMock(return_value=dynamodb_resource)

    spec = importlib.util.spec_from_file_location("photo_view_under_test", API_DIR / "photo_view.py")
    module = importlib.util.module_from_spec(spec)
    env = {"ASSET_TABLE_NAME": "asset-table", "ASSET_PHOTO_BUCKET": "private-photos"}
    with patch.dict(sys.modules, {"boto3": boto3}), patch.dict(os.environ, env):
        spec.loader.exec_module(module)
    return module, {"s3": s3, "table": table}


def asset_item(**overrides):
    return {
        "assetId": "AST-0001",
        "imageKey": "pending/tech-1/" + "a" * 32 + ".jpg",
        "department": "IT",
        "assignedUserId": "emp-1",
        **overrides,
    }


class PhotoViewTests(unittest.TestCase):
    def setUp(self):
        self.module, self.mocks = load_handler()

    def _event(self, sub, groups, department=None, asset_id="AST-0001"):
        claims = {"cognito:groups": groups}
        if sub is not None:
            claims["sub"] = sub
        if department is not None:
            claims["custom:department"] = department
        return {
            "requestContext": {"authorizer": {"claims": claims}},
            "pathParameters": {"assetId": asset_id},
        }

    def test_missing_subject_returns_401(self):
        result = self.module.lambda_handler(self._event(None, "[Employee]"), None)
        self.assertEqual(result["statusCode"], 401)
        self.mocks["table"].get_item.assert_not_called()

    def test_asset_not_found_returns_404(self):
        self.mocks["table"].get_item.return_value = {}
        result = self.module.lambda_handler(self._event("admin-1", "[Administrator]"), None)
        self.assertEqual(result["statusCode"], 404)

    def test_administrator_can_view_any_asset_photo(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item()}
        result = self.module.lambda_handler(self._event("admin-1", "[Administrator]"), None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["url"], "https://s3.example/signed-get")
        self.assertEqual(body["expiresIn"], 300)

    def test_auditor_can_view_any_asset_photo(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item()}
        result = self.module.lambda_handler(self._event("auditor-1", "[Auditor]"), None)
        self.assertEqual(result["statusCode"], 200)

    def test_manager_in_same_department_can_view(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item(department="IT")}
        event = self._event("mgr-1", "[Manager]", department="IT")
        result = self.module.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 200)

    def test_manager_in_different_department_is_denied(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item(department="IT")}
        event = self._event("mgr-1", "[Manager]", department="Facilities")
        result = self.module.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 403)
        self.mocks["s3"].generate_presigned_url.assert_not_called()

    def test_assigned_employee_can_view_own_asset(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item(assignedUserId="emp-1")}
        result = self.module.lambda_handler(self._event("emp-1", "[Employee]"), None)
        self.assertEqual(result["statusCode"], 200)

    def test_other_employee_is_denied(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item(assignedUserId="emp-1")}
        result = self.module.lambda_handler(self._event("emp-2", "[Employee]"), None)
        self.assertEqual(result["statusCode"], 403)

    def test_asset_without_photo_returns_404(self):
        item = asset_item()
        del item["imageKey"]
        self.mocks["table"].get_item.return_value = {"Item": item}
        result = self.module.lambda_handler(self._event("admin-1", "[Administrator]"), None)
        self.assertEqual(result["statusCode"], 404)
        self.mocks["s3"].generate_presigned_url.assert_not_called()

    def test_presign_failure_returns_500(self):
        self.mocks["table"].get_item.return_value = {"Item": asset_item()}
        self.mocks["s3"].generate_presigned_url.side_effect = Exception("boom")
        result = self.module.lambda_handler(self._event("admin-1", "[Administrator]"), None)
        self.assertEqual(result["statusCode"], 500)


if __name__ == "__main__":
    unittest.main()
