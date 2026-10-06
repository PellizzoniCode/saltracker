# CI/CD

GitHub Actions tests every pull request and deploys to AWS on merge. It signs in to AWS with GitHub OIDC, so no AWS access keys are stored anywhere.

| Event | Workflow | Result |
|---|---|---|
| Pull request to `develop` or `main` | `ci.yml` | Unit tests, `sam validate --lint`, `sam build`, frontend build. No AWS access. |
| Push to `develop` (a merged PR counts) | `deploy.yml` | Tests, deploy `smart-asset-tracker-dev`, smoke test, build the frontend and publish it to the dev Amplify app. |

**Production is not deployed yet.** Nothing in the workflows touches `smart-asset-tracker-prod`; see [Enabling prod](#enabling-prod) for what turning it on involves.

The shared checks live in `test.yml` and the shared deploy steps in `.github/actions/deploy-stack/`, so enabling prod later only needs a role, a secret and an approval gate.

## How the AWS sign-in works

1. The job asks GitHub for a short-lived signed token (`id-token: write`).
2. `aws-actions/configure-aws-credentials` presents it to AWS and asks to assume a deploy role.
3. The role's trust policy (`infrastructure/ci-bootstrap.yaml`) only accepts a matching token subject:

| Role | Trusted token subject | Effect |
|---|---|---|
| `saltracker-deploy-dev` | `<prefix>:ref:refs/heads/develop` | Only pushes to `develop`. |
| `saltracker-deploy-prod` | `<prefix>:environment:prod` | Only jobs in the `prod` GitHub Environment. **Not used yet**, see [Enabling prod](#enabling-prod). |

`<prefix>` is `repo:<org>/<repo>` in the classic format, or `repo:<org>@<owner-id>/<repo>@<repo-id>` when the repository uses GitHub's immutable subject claim (the default for newer repositories). It is set by the `GitHubSubjectPrefix` bootstrap parameter below.

Pull requests and forks get a different subject that no role trusts, so they can never reach AWS. The dev deploy job must not declare `environment:`; doing so changes its subject and the dev role would refuse it.

Both roles can only create IAM roles that carry the `saltracker-lambda-boundary` permission boundary, cannot remove it, and cannot modify the `saltracker-deploy-*` roles themselves.

## Configuration reference

Everything a fork has to configure, in one place. The repository is public, so GitHub **variables** are printed unmasked in the Actions logs; anything account-specific is a **secret**.

| Where | Name | Required | Purpose |
|---|---|---|---|
| GitHub secret | `AWS_ACCOUNT_ID` | Yes | 12-digit id of the AWS account that holds the bootstrap stack. The pipeline derives the deploy role, artifact bucket and permission boundary from it, and GitHub masks it in logs. |
| GitHub variable | `AWS_REGION` | No (default `us-east-1`) | Region of the bootstrap and application stacks. |
| GitHub variable | `DEV_PHOTO_UPLOAD_ORIGINS` | No | Comma-separated browser origins allowed to upload photos to the dev bucket. Blank keeps the template default. |
| GitHub variables | `DEV_AMPLIFY_APP_ID`, `DEV_AMPLIFY_BRANCH` | No | Amplify app and branch to publish the dev frontend to. Blank skips the frontend. |
| Bootstrap parameter | `GitHubOrg`, `GitHubRepo` | Yes | The repository whose workflows may assume the deploy roles. |
| Bootstrap parameter | `GitHubSubjectPrefix` | If the repo uses the immutable subject | The `sub_claim_prefix` GitHub puts in its tokens (see below). |
| Bootstrap parameter | `ExistingOidcProviderArn` | If the account already has the GitHub provider | An account can only have one `token.actions.githubusercontent.com` provider. |
| Bootstrap parameter | `DevBranch` | No (default `develop`) | Branch whose pushes may assume the dev role. |
| Bootstrap parameter | `AmplifyAppId` | No (default `*`) | Narrow the Amplify permission to one app once it exists. |

The pipeline relies on these fixed names from the bootstrap template, so do not rename them without updating both sides (`backend/tests/test_ci_names.py` fails CI if they drift apart): role `saltracker-deploy-<env>`, bucket `saltracker-sam-artifacts-<account-id>-<region>`, policy `saltracker-lambda-boundary`, and stack `smart-asset-tracker-<env>`.

## One-time setup

### 1. Deploy the bootstrap stack (administrator, not the pipeline)

The bootstrap stack creates the OIDC provider, both deploy roles, the permission boundary and the SAM artifact bucket. The stack is deliberately not deployed by the pipeline, so the pipeline can never widen its own permissions.

Read your repository's subject prefix first (only needed with the immutable subject; the command returns `sub_claim_prefix`):

```bash
gh api repos/<org>/<repo>/actions/oidc/customization/sub
```

Then deploy it with admin credentials, in the same region as the app. Leave out `ExistingOidcProviderArn` if the account has no GitHub provider yet, and leave out `GitHubSubjectPrefix` if the classic subject format applies:

```bash
aws cloudformation deploy \
  --template-file infrastructure/ci-bootstrap.yaml \
  --stack-name saltracker-ci-bootstrap \
  --region <region> \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    GitHubOrg=<org> \
    GitHubRepo=<repo> \
    GitHubSubjectPrefix=<sub_claim_prefix> \
    ExistingOidcProviderArn=<oidc-provider-arn>
```

If the role is later refused with `Not authorized to perform sts:AssumeRoleWithWebIdentity`, a wrong `GitHubSubjectPrefix` is the first thing to check. CloudTrail's rejected `AssumeRoleWithWebIdentity` events show the subject GitHub actually sent.

### 2. Configure GitHub

Set the secret first. Without `--body` the command prompts for the value, which keeps the account id out of your shell history:

```bash
gh secret set AWS_ACCOUNT_ID
```

Optional variables:

```bash
gh variable set AWS_REGION --body "<region>"
```

```bash
gh variable set DEV_PHOTO_UPLOAD_ORIGINS --body "https://<branch>.<amplify-app-id>.amplifyapp.com,http://localhost:5173"
```

```bash
gh variable set DEV_AMPLIFY_APP_ID --body "<amplify-app-id>"
```

```bash
gh variable set DEV_AMPLIFY_BRANCH --body "<branch>"
```

Check what is set (the secret list shows names only, never values):

```bash
gh secret list
```

```bash
gh variable list
```

### 3. Protect the deploy branch

Settings, Branches: protect `develop` and require the `CI / test / backend` and `CI / test / frontend` checks, so only tested code can be merged and trigger a deploy.

The dev role trusts pushes to `develop` (the bootstrap `DevBranch` parameter). To test the pipeline from a feature branch you would have to redeploy the bootstrap stack with `DevBranch=<that branch>` and temporarily add the branch to `deploy.yml`; set it back afterwards, because the role accepts that branch's code with no review.

## Frontend (Amplify)

After each backend deploy the pipeline builds the frontend against the stack it just deployed (`VITE_API_URL`, `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID` and `VITE_AWS_REGION` are read from the stack outputs and baked into the bundle), zips `frontend/dist`, uploads it to Amplify with a manual deployment, and waits for the Amplify job to finish. A failed Amplify deployment fails the pipeline, and the published URL is printed in the log.

Amplify is not in the SAM template. This works only with a **manual-deploy** Amplify app, one created without a Git repository. An app connected to Git does not accept manual deployments, and it would also build the site itself without the stack's values. Skipping the frontend is safe: leave `DEV_AMPLIFY_APP_ID` blank.

### One-time setup (dev)

1. Create the app and a branch (administrator, once):

   ```bash
   aws amplify create-app --region <region> --name saltracker-dev --query 'app.appId' --output text
   ```

   ```bash
   aws amplify create-branch --region <region> --app-id <amplify-app-id> --branch-name <branch>
   ```

2. The site is served at `https://<branch>.<amplify-app-id>.amplifyapp.com`. Photo uploads go straight from the browser to S3, so that origin must be allowed by the bucket CORS rules: set `DEV_PHOTO_UPLOAD_ORIGINS` as shown above (keep localhost if you also run the frontend locally).

3. Set `DEV_AMPLIFY_APP_ID` and `DEV_AMPLIFY_BRANCH` as shown above.

4. Redeploy the bootstrap stack with `AmplifyAppId=<amplify-app-id>` added to `--parameter-overrides`, so the deploy role can publish to that app only.

5. Merge to `develop` (or re-run the workflow). The dev deploy now ends with the frontend published.

Prod would need its own Amplify app and branch; see [Enabling prod](#enabling-prod).

## Day-to-day

- Merge a PR into `develop`: the dev stack redeploys and the smoke test runs. The report appears on the run summary and as the `smoke-test-results` artifact.
- Re-run a deploy without a new commit (for example after fixing the Amplify setup): **Actions > Deploy > Run workflow**, with branch `develop` selected, or `gh workflow run deploy.yml --ref develop`. Other branches are refused by the role's trust policy.
- There is no automated release to prod yet.

## Rollback

CloudFormation rolls a failed update back automatically and the job fails. To roll back a deploy that succeeded but is wrong, revert the commit on the branch; the pipeline redeploys the previous code. DynamoDB, the photo bucket and the log groups are `Retain`, so data survives a stack replacement.

## Troubleshooting

- **`The AWS_ACCOUNT_ID secret is missing or not a 12-digit account id`**: set it with `gh secret set AWS_ACCOUNT_ID`.
- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`**: the role's trust does not match the token. Check `GitHubSubjectPrefix` and `DevBranch` on the bootstrap stack, and that the workflow runs from the branch the role trusts.
- **Stack in `UPDATE_ROLLBACK_FAILED`**: nothing can deploy until it is recovered. Fix the cause, then finish the rollback with admin credentials (they are not subject to the deploy role's restrictions):

  ```bash
  aws cloudformation continue-update-rollback --stack-name smart-asset-tracker-dev --region <region>
  ```

  A deploy that adds the permission boundary to Lambda roles that did not have it yet can fail on rollback this way, because the deploy role may not remove the boundary. Stacks created by the pipeline are not affected.
- **`AccessDenied` from the deploy role in the deploy log**: look at the rejected call in CloudTrail and add only that action to `ci-bootstrap.yaml`, then redeploy the bootstrap stack.
- **`log group already exists` / bucket name conflicts**: leftovers from an earlier stack; see [cloudwatch-monitoring.md](cloudwatch-monitoring.md).

## Enabling prod

Not done yet. The bootstrap stack already creates the `saltracker-deploy-prod` role, and the previous `deploy-prod` job (with its health check) is in git history at commit `5137944`. To turn prod on:

1. In GitHub, Settings, Environments, create **`prod`** with **required reviewers** and restrict deployment branches to `main`. The role trusts any job that declares `environment: prod`, so these reviewers are the only gate; create the Environment with them before anything uses the role.
2. Restore the `deploy-prod` job and add `main` to the push trigger in `deploy.yml`. Pass `account-id: ${{ secrets.AWS_ACCOUNT_ID }}` as the dev job does (if prod lives in a different AWS account, add an `AWS_ACCOUNT_ID` secret on the `prod` Environment; it overrides the repository one for that job).
3. Add **`PHOTO_UPLOAD_ORIGINS`** as a `prod` Environment variable and pass it to the action (required: the prod frontend origin, so the dev and localhost defaults never reach prod), plus `AMPLIFY_APP_ID` and `AMPLIFY_BRANCH` for a separate manual-deploy Amplify app.
4. Prepare the environment by hand first, because the pipeline does not:
   - If it already has CloudWatch log groups, import them (see [cloudwatch-monitoring.md](cloudwatch-monitoring.md)), or the deploy fails with "log group already exists".
   - `PendingUploadExpiration` stays `Disabled` until the photo migration is verified (see [photo-storage-migration.md](photo-storage-migration.md)).
5. The bootstrap `AmplifyAppId` parameter holds one app id shared by both roles; leave it `*` or extend the template to take one id per environment.

## Tightening permissions

The deploy policies were written from the template and only partly exercised. API Gateway and Cognito resources have generated ids, so those two statements can only be scoped by region and account, not by name.

## Not covered

- `scripts/dev.sh` stays dev and test only; its prod guard is unchanged.
- The API Gateway CORS origin is still `*`. The API authenticates with a Bearer token in the `Authorization` header and not cookies, so another site cannot act as a signed-in user.
- A `test` environment is not wired up. Adding one means a third role in `ci-bootstrap.yaml` and a job in `deploy.yml`.
