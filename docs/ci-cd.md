# CI/CD

GitHub Actions tests every pull request and deploys to AWS on merge. It signs in to AWS with GitHub OIDC, so no AWS access keys are stored anywhere.

| Event | Workflow | Result |
|---|---|---|
| Pull request to `develop` or `main` | `ci.yml` | Unit tests, `sam validate --lint`, `sam build`, frontend build. No AWS access. |
| Push to `develop` | `deploy.yml` | Tests, deploy `smart-asset-tracker-dev`, smoke test, rebuild the dev Amplify branch. |
| Push to `main` | `deploy.yml` | Tests, wait for approval, deploy `smart-asset-tracker-prod`, health check, rebuild the prod Amplify branch. |

The shared checks live in `test.yml` and the shared deploy steps in `.github/actions/deploy-stack/`, so dev and prod only differ in the role, variables and approval gate.

## How the AWS sign-in works

1. The job asks GitHub for a short-lived signed token (`id-token: write`).
2. `aws-actions/configure-aws-credentials` presents it to AWS and asks to assume a deploy role.
3. The role's trust policy (`infrastructure/ci-bootstrap.yaml`) only accepts a matching token subject:

| Role | Trusted token subject | Effect |
|---|---|---|
| `saltracker-deploy-dev` | `<prefix>:ref:refs/heads/develop` | Only pushes to `develop`. |
| `saltracker-deploy-prod` | `<prefix>:environment:prod` | Only jobs in the `prod` GitHub Environment, which waits for a reviewer. |

`<prefix>` is `repo:PellizzoniCode/saltracker` in the classic format, or `repo:PellizzoniCode@191217257/saltracker@1367469052` with GitHub's immutable subject (this repo). It is set by the `GitHubSubjectPrefix` parameter below.

Pull requests and forks get a different subject that no role trusts, so they can never reach AWS. The dev deploy job must not declare `environment:`; doing so changes its subject and the dev role would refuse it.

Both roles can only create IAM roles that carry the `saltracker-lambda-boundary` permission boundary, cannot remove it, and cannot modify the `saltracker-deploy-*` roles themselves.

## One-time setup

### 1. Deploy the bootstrap stack (administrator, not the pipeline)

The bootstrap stack creates the OIDC provider, both deploy roles, the permission boundary and the SAM artifact bucket. Deploy it with admin credentials, in the same region as the app:

```bash
aws cloudformation deploy \
  --template-file infrastructure/ci-bootstrap.yaml \
  --stack-name saltracker-ci-bootstrap \
  --region us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM
```

Parameters (add with `--parameter-overrides`):

- `ExistingOidcProviderArn`: set it if the account already has a `token.actions.githubusercontent.com` provider. An account can only have one, and the stack fails if you try to create a second.
- `AmplifyAppId`: set the real Amplify app id. It defaults to `*`, which lets the deploy roles update any Amplify app in the account.
- `GitHubSubjectPrefix`: **required if the repo uses GitHub's immutable OIDC subject**, which is the default for newer repositories. Their tokens carry numeric owner and repo ids (`repo:<org>@<owner-id>/<repo>@<repo-id>:...`), so the role trust only matches if you pass that prefix. Read it from the `sub_claim_prefix` field:

  ```bash
  gh api repos/PellizzoniCode/saltracker/actions/oidc/customization/sub
  ```

  Then add `GitHubSubjectPrefix=<that value>` to `--parameter-overrides`. If the role is refused with `Not authorized to perform sts:AssumeRoleWithWebIdentity`, a wrong prefix is the first thing to check; CloudTrail's rejected `AssumeRoleWithWebIdentity` events show the subject GitHub actually sent.
- `GitHubOrg`, `GitHubRepo`, `DevBranch`, `ProdEnvironmentName`: only if you fork or rename.

The stack is deliberately not deployed by the pipeline, so the pipeline can never widen its own permissions.

Read the outputs:

```bash
aws cloudformation describe-stacks --stack-name saltracker-ci-bootstrap --region us-east-1 \
  --query 'Stacks[0].Outputs' --output table
```

### 2. Configure GitHub

Repository settings, Secrets and variables, Actions, **Variables** tab (these are not secrets):

| Variable | Value |
|---|---|
| `AWS_DEV_ROLE_ARN` | `DevDeployRoleArn` output |
| `SAM_ARTIFACT_BUCKET` | `SamArtifactBucketName` output |
| `PERMISSIONS_BOUNDARY_ARN` | `LambdaPermissionBoundaryArn` output |
| `DEV_PHOTO_UPLOAD_ORIGINS` | Optional. Comma-separated origins for the dev stack; blank keeps the template default. |
| `DEV_AMPLIFY_APP_ID`, `DEV_AMPLIFY_BRANCH` | Optional. Blank skips the dev frontend rebuild. |

Settings, Environments, create **`prod`**:

- Add **required reviewers**. This is what holds the prod credentials back until someone approves.
- Restrict deployment branches to `main`.
- Add these environment variables:

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `ProdDeployRoleArn` output |
| `PHOTO_UPLOAD_ORIGINS` | **Required.** The prod frontend origin, for example `https://main.<id>.amplifyapp.com`. The deploy fails without it so the dev and localhost defaults never reach prod. |
| `AMPLIFY_APP_ID`, `AMPLIFY_BRANCH` | Optional. Blank skips the prod frontend rebuild. |

Settings, Branches: protect `develop` and `main`, and require the `CI / test / backend` and `CI / test / frontend` checks, so only tested code can be merged and trigger a deploy.

## Frontend (Amplify)

The Amplify app itself is still configured by hand and is not in the SAM template. After each backend deploy the pipeline reads `ApiUrl`, `UserPoolId` and `UserPoolClientId` from the stack, merges them with `VITE_AWS_REGION` into the Amplify branch's environment variables (existing variables are kept) and starts a release job. It does not wait for the Amplify build to finish; check the Amplify console for that.

## Day-to-day

- Merge a PR into `develop`: the dev stack redeploys and the smoke test runs. The report appears on the run summary and as the `smoke-test-results` artifact.
- Release: merge `develop` into `main`, then approve the `prod` deployment on the run page.

## Rollback

CloudFormation rolls a failed update back automatically and the job fails. To roll back a deploy that succeeded but is wrong, revert the commit on the branch; the pipeline redeploys the previous code. DynamoDB, the photo bucket and the log groups are `Retain`, so data survives a stack replacement.

## First prod deploy: manual steps the pipeline does not do

- If the environment already has CloudWatch log groups, import them first (see [cloudwatch-monitoring.md](cloudwatch-monitoring.md)), or the deploy fails with "log group already exists".
- `PendingUploadExpiration` stays `Disabled` until the photo migration is verified (see [photo-storage-migration.md](photo-storage-migration.md)).

## Tightening permissions

The deploy policies were written from the template and have not been exercised against a real account. After the first dev run, look for `AccessDenied` events from `saltracker-deploy-dev` in CloudTrail and add only what is missing. API Gateway and Cognito resources have generated ids, so those two statements can only be scoped by region and account, not by name.

## Not covered

- `scripts/dev.sh` stays dev and test only; its prod guard is unchanged.
- The API Gateway CORS origin is still `*`. The API authenticates with a Bearer token in the `Authorization` header and not cookies, so another site cannot act as a signed-in user.
- A `test` environment is not wired up. Adding one means a third role in `ci-bootstrap.yaml` and a job in `deploy.yml`.
