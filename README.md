# AWS Smart Asset Lifecycle Tracker

A secure serverless asset-management application built with Amazon Cognito, API Gateway, Lambda, DynamoDB, S3, Amazon Bedrock, EventBridge, SNS, and CloudWatch. SailPoint is planned as the identity-governance and lifecycle-provisioning layer while Cognito remains the application's authentication and JWT provider.

## Current milestone

The starter implements the Week 1 foundation:

- AWS SAM infrastructure
- Cognito user pool and five application groups
- API Gateway Cognito authorizer
- DynamoDB asset table
- Python Lambda REST API for create, list, view, and update
- Backend RBAC and record-scope authorization
- React login and manual asset-entry interface
- Ten sample assets and unit tests
- SailPoint-to-Cognito role mapping documentation

## Architecture

See [`docs/architecture.md`](docs/architecture.md), [`docs/data-model.md`](docs/data-model.md), [`docs/role-permissions.md`](docs/role-permissions.md), and [`docs/sailpoint-integration.md`](docs/sailpoint-integration.md).

## Architecture diagrams

See [`docs/architecture/README.md`](docs/architecture/README.md) for the complete four-week target architecture and the weekly architecture progression diagrams.

## Prerequisites

- AWS CLI configured for a non-production AWS account
- AWS SAM CLI
- Python 3.11 (matches the Lambda `Runtime` in `infrastructure/template.yaml`; required for a native `sam build` — use `sam build --use-container` instead if you don't have 3.11 installed locally)
- Node.js 20 or later

## Quick start with `scripts/dev.sh`

`scripts/dev.sh` wraps the manual steps below into single commands for a non-production test stack. It requires the AWS CLI configured for your account, the SAM CLI, `python3`, and `npm`.

```bash
scripts/dev.sh up                                                    # test, build, deploy, write frontend/.env, seed sample data
scripts/dev.sh user you@example.com Administrator 'Your-Pass123!' IT # create a confirmed login
scripts/dev.sh web                                                   # start the frontend
```

| Command                                  | What it does                                                                                                                                                                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `up`                                     | Runs unit tests, validates and builds (cached), deploys without prompts, writes `frontend/.env`, and seeds `sample-data/assets.json`                                                                                       |
| `deploy`                                 | Build and deploy only, then refresh `frontend/.env`                                                                                                                                                                        |
| `sync`                                   | Watches backend code and hot-syncs Lambda changes with `sam sync --watch` (dev stacks only)                                                                                                                                |
| `env`                                    | Writes `frontend/.env` from the stack outputs                                                                                                                                                                              |
| `seed`                                   | Loads the sample assets through the deployed Lambda, so validation and tag uniqueness still apply. Safe to re-run; existing tags are skipped                                                                               |
| `user EMAIL GROUP PASSWORD [DEPARTMENT]` | Creates a confirmed Cognito user in `GROUP`, optionally setting `custom:department`. The password must meet the pool policy (12+ characters with upper, lower, number, and symbol); pass `-` to be prompted for it instead |
| `web`                                    | Installs frontend dependencies if needed and runs the Vite dev server                                                                                                                                                      |
| `down [--purge]`                         | Deletes the stack; `--purge` also deletes the retained DynamoDB table                                                                                                                                                      |
| `test` / `build`                         | Runs only the unit tests / only validate and build                                                                                                                                                                         |

Defaults can be overridden with environment variables: `ENVIRONMENT` (default `dev`), `STACK_NAME` (default `smart-asset-tracker-$ENVIRONMENT`), and `AWS_REGION` (default `us-east-1`).

Wrap the password in single quotes so characters like `!` and `$` aren't interpreted by the shell. A password passed as an argument is saved in your shell history; pass `-` instead to type it at a hidden prompt.

To test without touching the shared `dev` stack, use a different environment. Resource names are derived from `ENVIRONMENT`, so this creates a fully separate stack, table, functions, and user pool. Changing only `STACK_NAME` is not enough, because the table and function names would collide.

```bash
ENVIRONMENT=test scripts/dev.sh up
ENVIRONMENT=test scripts/dev.sh down --purge
```

## Test and deploy the backend manually

```bash
python3 -m unittest discover -s backend/tests -v
sam validate --template-file infrastructure/template.yaml
sam build --template-file infrastructure/template.yaml
sam deploy --guided
```

Use stack name `smart-asset-tracker-dev` and a development AWS region. After deployment, copy the stack outputs into `frontend/.env` using `frontend/.env.example`.

### Tear down after testing

The stack has billable resources (DynamoDB, API Gateway, Cognito). Once you're done testing, delete it rather than leaving it running:

```bash
sam delete --stack-name smart-asset-tracker-dev
```

`AssetTable` has `DeletionPolicy: Retain`, so the DynamoDB table survives the stack delete — remove it manually from the AWS Console/CLI if you don't need the data anymore.

## Run the frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Create test users

Create users in Cognito, confirm them, and assign them to one of these groups:

- `Employee`
- `Technician`
- `Manager`
- `Administrator`
- `Auditor`

`scripts/dev.sh user EMAIL GROUP PASSWORD [DEPARTMENT]` does this in one step.

For employee record scoping, set each asset's `assignedUserId` to the user's Cognito `sub`. For manager scoping, add a mutable Cognito custom attribute named `custom:department` and populate it before the user signs in.

## Security notes

- API permissions are enforced in Lambda as well as API Gateway.
- Employee and Manager access is restricted at record level.
- Technician updates are restricted to operational fields.
- Financial values are validated with `Decimal`, never floating point.
- Secrets and tokens must not be committed.
- The current scan-based search is appropriate only for the small Week 1 dataset; production access patterns should use indexes.

## Next milestone

Week 2 adds a private S3 bucket, presigned uploads, Bedrock image analysis with structured output, manual fallback, and mandatory human confirmation before saving AI suggestions.
