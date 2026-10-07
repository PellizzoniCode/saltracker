import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = (ROOT / "infrastructure" / "ci-bootstrap.yaml").read_text()
ACTION = (ROOT / ".github" / "actions" / "deploy-stack" / "action.yml").read_text()
DEPLOY = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
PUBLISH = (ROOT / ".github" / "actions" / "publish-frontend" / "action.yml").read_text()

# The deploy action derives AWS resource names from the account id instead of
# taking them as GitHub variables (variables are not masked in public logs).
# These tests fail in CI if the names in the workflows and in
# infrastructure/ci-bootstrap.yaml drift apart, which would otherwise only show
# up as a failed deploy.


def bootstrap_value(key):
    return re.findall(rf"^\s+{key}:\s*(?:!Sub\s+)?(\S+)\s*$", BOOTSTRAP, re.MULTILINE)


class CiNameTests(unittest.TestCase):
    def test_deploy_roles_match_what_the_workflows_assume(self):
        self.assertIn("saltracker-deploy-dev", bootstrap_value("RoleName"))
        self.assertIn("saltracker-deploy-prod", bootstrap_value("RoleName"))
        self.assertIn(":role/saltracker-deploy-${{ inputs.environment }}", ACTION)
        self.assertIn(":role/saltracker-deploy-dev", DEPLOY)

    def test_artifact_bucket_matches_the_bootstrap_bucket(self):
        (declared,) = bootstrap_value("BucketName")
        derived = re.search(r"^\s+ARTIFACT_BUCKET: (.+)$", ACTION, re.MULTILINE).group(1).strip()

        def normalise(name):
            return (
                name.replace("${AWS::AccountId}", "<account>").replace("${AWS::Region}", "<region>")
                .replace("${{ inputs.account-id }}", "<account>").replace("${{ inputs.region }}", "<region>")
            )

        self.assertEqual(normalise(declared), normalise(derived))

    def test_artifact_prefix_is_the_environment_the_roles_may_write_to(self):
        self.assertIn('--s3-prefix "$ENVIRONMENT"', ACTION)
        for env in ("dev", "prod"):
            self.assertIn("${SamArtifactBucket.Arn}/%s/*" % env, BOOTSTRAP)

    def test_permission_boundaries_match_the_bootstrap_policies(self):
        for env in ("dev", "prod"):
            self.assertIn("saltracker-lambda-boundary-%s" % env, bootstrap_value("ManagedPolicyName"))
        self.assertIn(":policy/saltracker-lambda-boundary-${{ inputs.environment }}", ACTION)

    def test_each_deploy_role_may_only_create_roles_with_its_own_boundary(self):
        self.assertIn("iam:PermissionsBoundary: !Ref LambdaPermissionBoundaryDev", BOOTSTRAP)
        self.assertIn("iam:PermissionsBoundary: !Ref LambdaPermissionBoundaryProd", BOOTSTRAP)
        self.assertNotIn("!Ref LambdaPermissionBoundary\n", BOOTSTRAP)

    def test_boundaries_do_not_reach_the_other_environment(self):
        def policy(resource):
            start = BOOTSTRAP.index("\n  %s:\n" % resource) + 1
            following = re.search(r"^  \S", BOOTSTRAP[start + 1:], re.MULTILINE)
            return BOOTSTRAP[start : start + 1 + following.start()]

        for env, other in (("dev", "prod"), ("prod", "dev")):
            text = policy("LambdaPermissionBoundary%s" % env.capitalize())
            self.assertIn("smart-asset-tracker-%s" % env, text)
            self.assertNotIn(other, text)
            # No wildcard may span environments.
            self.assertNotIn("table/smart-asset-tracker-*", text)
            self.assertNotIn("smart-asset-tracker-*-photos", text)
            self.assertNotIn("log-group:/aws/lambda/smart-asset-*:*", text)

    def test_sam_deploy_uses_the_configured_region_not_samconfig(self):
        self.assertIn('--region "$REGION"', ACTION)
        self.assertIn("REGION: ${{ inputs.region }}", ACTION)

    def test_photo_upload_origins_are_required_for_every_environment(self):
        self.assertRegex(ACTION, r"photo-upload-origins:\n(?:    .*\n)*?    required: true")
        self.assertIn('[ -z "$PHOTO_UPLOAD_ORIGINS" ]', ACTION)
        self.assertNotIn('"$ENVIRONMENT" = prod', ACTION)

    def test_frontend_is_published_only_after_the_smoke_test(self):
        self.assertNotIn("aws amplify", ACTION)
        self.assertNotIn("inputs.amplify", ACTION)
        self.assertIn("needs: smoke-dev", DEPLOY.split("publish-frontend-dev:")[1])
        self.assertIn("./.github/actions/publish-frontend", DEPLOY)
        self.assertIn(":role/saltracker-deploy-${{ inputs.environment }}", PUBLISH)

    def test_stack_names_match_what_the_deploy_roles_may_change(self):
        self.assertIn('--stack-name "smart-asset-tracker-$ENVIRONMENT"', ACTION)
        for env in ("dev", "prod"):
            self.assertIn(":stack/smart-asset-tracker-%s/*" % env, BOOTSTRAP)

    def test_no_account_id_is_committed_in_ci_files(self):
        # AWS's documentation example id is allowed as a placeholder.
        account_id = re.compile(r"(?<![\d.])\d{12}(?![\d.])")
        files = [
            *(ROOT / ".github").rglob("*.yml"),
            ROOT / "infrastructure" / "ci-bootstrap.yaml",
            ROOT / "docs" / "ci-cd.md",
            ROOT / "README.md",
        ]
        for path in files:
            for number in account_id.findall(path.read_text()):
                self.assertEqual("123456789012", number, f"possible account id in {path.relative_to(ROOT)}")


if __name__ == "__main__":
    unittest.main()
