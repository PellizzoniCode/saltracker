"""Security acceptance tests for the Week 4 milestone."""

import json
import pathlib
import re
import subprocess
import sys
import unittest


TEST_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
TEMPLATE = REPO_ROOT / "infrastructure" / "template.yaml"
sys.path.insert(0, str(TEST_DIR))

from test_unique_asset_tags import _load_api  # noqa: E402


ASSET = {
    "PK": "ASSET#AST-SECURITY",
    "SK": "METADATA",
    "assetId": "AST-SECURITY",
    "assetTag": "SEC-001",
    "category": "Laptop",
    "description": "Security test laptop",
    "purchaseDate": "2026-01-01",
    "inServiceDate": "2026-01-01",
    "purchaseValue": "1500.00",
    "salvageValue": "100.00",
    "usefulLifeMonths": 48,
    "department": "IT",
    "condition": "Good",
    "status": "Available",
}


def authenticated_event(
    method,
    resource,
    *,
    asset_id=None,
    group="Administrator",
    sub="security-user",
    body=None,
):
    event = {
        "httpMethod": method,
        "resource": resource,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": sub,
                    "email": f"{sub}@example.com",
                    "cognito:groups": f"[{group}]",
                    "custom:department": "IT",
                }
            }
        },
    }

    if asset_id:
        event["pathParameters"] = {
            "assetId": asset_id,
        }

    if body is not None:
        event["body"] = body

    return event


class SecurityRequirementTests(unittest.TestCase):
    def setUp(self):
        self.api, self.table, self.transactions, self.s3 = _load_api()

    def response_body(self, result):
        return json.loads(result["body"])

    def test_request_without_authenticated_identity_returns_401(self):
        event = {
            "httpMethod": "GET",
            "resource": "/assets",
            "requestContext": {},
        }

        result = self.api.lambda_handler(event, None)
        body = self.response_body(result)

        self.assertEqual(result["statusCode"], 401)
        self.assertEqual(body["error"], "Unauthorized")
        self.table.scan.assert_not_called()
        self.table.query.assert_not_called()

    def test_auditor_cannot_modify_asset(self):
        self.table.get_item.return_value = {
            "Item": ASSET,
        }

        event = authenticated_event(
            "PUT",
            "/assets/{assetId}",
            asset_id="AST-SECURITY",
            group="Auditor",
            sub="auditor-1",
            body=json.dumps({
                "condition": "Poor",
            }),
        )

        result = self.api.lambda_handler(event, None)
        body = self.response_body(result)

        self.assertEqual(result["statusCode"], 403)
        self.assertEqual(body["error"], "Forbidden")
        self.table.put_item.assert_not_called()
        self.transactions.transact_write_items.assert_not_called()

    def test_malformed_json_is_rejected(self):
        event = authenticated_event(
            "POST",
            "/assets",
            body='{"assetTag": "SEC-001", invalid}',
        )

        result = self.api.lambda_handler(event, None)
        body = self.response_body(result)

        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(body["error"], "ValidationError")
        self.table.put_item.assert_not_called()
        self.transactions.transact_write_items.assert_not_called()

    def test_unsupported_method_is_rejected(self):
        event = authenticated_event(
            "DELETE",
            "/assets/{assetId}",
            asset_id="AST-SECURITY",
        )

        result = self.api.lambda_handler(event, None)
        body = self.response_body(result)

        self.assertEqual(result["statusCode"], 405)
        self.assertEqual(body["error"], "MethodNotAllowed")

    def test_employee_cannot_read_another_users_asset(self):
        protected_asset = {
            **ASSET,
            "assignedUserId": "employee-owner",
        }
        self.table.get_item.return_value = {
            "Item": protected_asset,
        }

        event = authenticated_event(
            "GET",
            "/assets/{assetId}",
            asset_id="AST-SECURITY",
            group="Employee",
            sub="different-employee",
        )

        result = self.api.lambda_handler(event, None)
        body = self.response_body(result)

        self.assertEqual(result["statusCode"], 403)
        self.assertEqual(body["error"], "Forbidden")


class InfrastructureSecurityTests(unittest.TestCase):
    """Static checks on the SAM template; live checks stay manual."""

    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text()

    def resource_block(self, name):
        match = re.search(
            rf"^  {name}:\n(.*?)(?=^  [A-Za-z0-9]+:\n|^Outputs:)",
            self.template,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"{name} is missing from the template")
        return match.group(1)

    def test_api_uses_cognito_authorizer_by_default(self):
        block = self.resource_block("AssetApi")

        self.assertIn("DefaultAuthorizer: CognitoAuthorizer", block)
        self.assertIn("UserPoolArn: !GetAtt UserPool.Arn", block)

    def test_only_health_endpoint_is_unauthenticated(self):
        self.assertEqual(self.template.count("Authorizer: NONE"), 1)
        self.assertIn("Authorizer: NONE", self.resource_block("HealthFunction"))

    def test_photo_bucket_blocks_all_public_access(self):
        block = self.resource_block("AssetPhotoBucket")

        for setting in (
            "BlockPublicAcls",
            "BlockPublicPolicy",
            "IgnorePublicAcls",
            "RestrictPublicBuckets",
        ):
            self.assertIn(f"{setting}: true", block)

    def test_photo_urls_are_short_lived(self):
        api, *_ = _load_api()

        self.assertLessEqual(api.PHOTO_URL_EXPIRES_IN, 300)

    def test_tracked_files_contain_no_credentials(self):
        try:
            tracked = subprocess.run(
                ["git", "ls-files"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")

        patterns = [
            re.compile(r"AKIA[0-9A-Z]{16}"),
            re.compile(r"ASIA[0-9A-Z]{16}"),
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
            re.compile(r"aws_secret_access_key\s*=\s*\S+", re.IGNORECASE),
        ]
        text_suffixes = {
            ".py", ".js", ".jsx", ".json", ".yaml", ".yml", ".toml",
            ".sh", ".md", ".html", ".css", ".env", ".txt",
        }
        findings = []

        for name in tracked:
            path = REPO_ROOT / name

            if path.suffix not in text_suffixes or not path.is_file():
                continue

            content = path.read_text(errors="ignore")
            findings.extend(
                f"{name}: {pattern.pattern}"
                for pattern in patterns
                if pattern.search(content)
            )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
