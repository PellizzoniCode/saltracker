# AWS Smart Asset Lifecycle Tracker

A secure serverless asset-management application built with Amazon Cognito, API Gateway, Lambda, DynamoDB, S3, Amazon Bedrock, EventBridge, SNS, and CloudWatch. SailPoint is planned as the identity-governance and lifecycle-provisioning layer while Cognito remains the application's authentication and JWT provider.

## Current milestone: Week 2

Week 1 established the serverless asset-management foundation with AWS SAM, Cognito authentication, API Gateway, Lambda, DynamoDB, record-level authorization, and the React asset-entry interface.

Week 2 adds a secure, AI-assisted photograph workflow:

- Private S3 photo bucket with all public access blocked, bucket-owner-enforced ownership, and server-side encryption
- Five-minute presigned POST forms for JPEG and PNG uploads, limited to 3.75 MB
- Upload authorization based only on verified Cognito claims; administrators and technicians can upload, and technicians require a department claim
- User-scoped object keys under `pending/{cognito-sub}/`
- S3 event notification that invokes the photo-analysis Lambda asynchronously
- Amazon Bedrock Nova Lite multimodal analysis with deterministic inference settings
- Strict JSON validation before AI suggestions are stored in DynamoDB
- Suggested category, description, condition, useful life, maintenance category, and review status
- Frontend photo preview, analysis polling, and explicit human review before suggestions enter the asset form
- Atomic DynamoDB asset-tag reservation to prevent duplicate tags during concurrent requests
- CloudWatch logging and AWS X-Ray tracing for the serverless workflow

## Architecture

See [`docs/architecture.md`](docs/architecture.md), [`docs/data-model.md`](docs/data-model.md), [`docs/role-permissions.md`](docs/role-permissions.md), and [`docs/sailpoint-integration.md`](docs/sailpoint-integration.md).

## Architecture diagrams

See [`docs/architecture/README.md`](docs/architecture/README.md) for the complete four-week target architecture and the weekly architecture progression diagrams.

## Prerequisites

- AWS CLI configured for a non-production AWS account
- AWS SAM CLI
- Python 3.11 (matches the Lambda `Runtime` in `infrastructure/template.yaml`; required for a native `sam build` — use `sam build --use-container` instead if you don't have 3.11 installed locally)
- Node.js 20 or later

## Test and deploy the backend

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

For employee record scoping, set each asset's `assignedUserId` to the user's Cognito `sub`. For manager scoping, add a mutable Cognito custom attribute named `custom:department` and populate it before the user signs in.

## Week 2 security controls

- Asset photographs remain private in S3; the bucket blocks public ACLs and public bucket policies.
- The backend creates short-lived upload forms only after API Gateway validates the Cognito token.
- Lambda reads roles, user identity, and department from verified Cognito claims instead of trusting values supplied by the browser.
- Upload policies restrict the content type, object-key prefix, file size, and expiration time.
- The analysis Lambda accepts only the configured bucket, the expected `pending/` key format, supported image signatures, and files within the size limit.
- Bedrock output is treated as untrusted input and must pass schema, type, length, enum, and range validation.
- Photo-analysis results are visible only to an administrator or the technician who owns the uploaded photo.
- Asset API permissions remain enforced in Lambda, including department and assigned-user record scoping.
- Technician asset updates remain restricted to operational fields.
- Financial values use `Decimal`, never binary floating point.
- Secrets and tokens must not be committed.

## Week 2 validation

Run the backend suite and production frontend build before deployment:

```bash
python3 -m unittest discover -s backend/tests -v
sam validate --template-file infrastructure/template.yaml --lint
sam build --template-file infrastructure/template.yaml
cd frontend && npm ci && npm run build
```

The tests cover role-based asset access, restricted photograph uploads, missing identity claims, content-type and size controls, and atomic asset-tag uniqueness.

## Next milestone

- Promote accepted photographs from `pending/` to an asset-specific prefix and expire abandoned uploads.
- Add authorized, short-lived photograph retrieval for the asset gallery.
- Expand automated tests for direct public-access denial, presigned URL expiration, and cross-asset authorization.
- Add CloudWatch alarms, dashboards, retention policies, and end-to-end deployment automation.
- Replace scan-based search with indexed DynamoDB access patterns as the dataset grows.
