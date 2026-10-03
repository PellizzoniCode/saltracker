# Estimated monthly AWS cost

## Source files and estimate baseline

This estimate was prepared from these repository configuration files:

1. `infrastructure/template.yaml` — SAM infrastructure, service configuration, function memory, tracing, and resource retention settings.
2. `samconfig.toml` — deployment stack, region, and environment parameters.

| Field | Value |
| --- | --- |
| Project | Smart Asset Lifecycle Tracker — Group 2 |
| Submission requirement | Estimated monthly AWS cost; Issue #24 |
| Prepared by | Group 2 |
| Document date | 3 October 2026 |
| Calculator export date | 2 October 2026 |
| Reviewed develop revision | `619ae93` |
| Environment / stack | `dev` / `smart-asset-tracker-dev` |
| Primary region | US East (N. Virginia), `us-east-1` |
| Currency | USD |

The estimate covers one development environment at low usage. It combines configuration from the source files with explicitly assumed usage volumes; it is not a measurement of production traffic or an AWS bill. Amplify hosting is included separately because the frontend deployment is outside the reviewed SAM template.

## Estimated cost

**Estimated monthly cost: USD 3.25.** Estimated daily equivalent: **USD 0.11**, calculated as USD 3.25 / 30 days. The exported upfront cost is USD 0.00 and the 12-month total is USD 39.00.

The monthly figure is the submission total. The daily figure is an average allocation of that total, not a prediction of each day's charges; storage, active-user counts, builds, and requests have different billing patterns.

| Service / estimate component | Monthly cost (USD) | Scope |
| --- | ---: | --- |
| Amazon Cognito | 0.00 | Authentication |
| Amazon API Gateway | 0.04 | REST API |
| AWS Lambda — standard backend functions | 0.02 | Aggregate standard function usage |
| AWS Lambda — photo analysis | 0.02 | Photo workflow |
| Amazon DynamoDB | 0.27 | Table, requests, and PITR |
| Amazon S3 | 0.13 | Photos, deployment artifacts, requests, and transfer |
| Amazon Bedrock | 0.48 | Amazon Nova Lite photo analysis |
| Amazon EventBridge | 0.01 | Planned lifecycle events |
| Amazon SNS | 0.02 | Planned notifications |
| Amazon CloudWatch | 0.50 | Application logs |
| AWS Amplify | 1.75 | React frontend hosting and builds |
| AWS X-Ray | 0.01 | API and Lambda tracing |
| **Total** | **3.25** | **Calculator export total** |

These component amounts follow the PDF export. The JSON export and Bedrock configuration screen display USD 0.47 for Bedrock, while the PDF displays USD 0.48. The exported overall total is USD 3.25 in both PDF and JSON. The one-cent component display difference has not been reconciled; the authoritative submission total here is the exported overall total.

## Usage assumptions and Calculator inputs

All request volumes below are monthly unless stated otherwise.

| Service | Configuration and assumed usage |
| --- | --- |
| Cognito | Essentials selected in Calculator; 20 direct monthly active users; zero SAML/OIDC users and machine-to-machine token requests; multi-region replication disabled. The deployed pool tier is not explicit in the reviewed template and should be verified. |
| API Gateway | REST API: 0.01 million requests = 10,000 requests; no cache; no HTTP API or WebSocket workload. |
| Lambda — standard | Four standard functions represented by 10,000 aggregate invocations; x86 architecture; 256 MB memory; 500 ms assumed average duration; buffered invocation; 512 MB ephemeral storage; no provisioned concurrency. |
| Lambda — photo | 100 invocations; x86; 512 MB memory; 20,000 ms assumed average duration; buffered invocation; 512 MB ephemeral storage; no provisioned concurrency. |
| DynamoDB | On-demand, Standard table; 0.1 GB data; 1 KB average item; 50,000 standard write equivalents and 200,000 eventually consistent reads; no strongly consistent or transactional reads entered. PITR storage: 1 GB; on-demand backup storage and restore volume: zero. |
| S3 | Standard storage: 1.5 GB, comprising 1 GB photos and 0.5 GB SAM deployment artifacts; 1,020 PUT/COPY/POST/LIST requests; 1,000 GET and other requests; 1 GB outbound internet transfer; no S3 Select workload. |
| Bedrock | Amazon Nova Lite, corresponding to `us.amazon.nova-lite-v1:0`; Geo Cross Region Inference; On Demand — Standard; 1,000 input text tokens and 500 output tokens per request; one 1024 × 1024 image per request; no prompt caching. Rate: one request/minute for one hour/day. |
| CloudWatch | 1 GB Standard Logs ingested; no Infrequent Access or delivered-log workload; one month assumed log retention; Calculator compressed stored volume approximately 0.15 GB; no custom metrics or paid metrics API workload entered. |
| EventBridge | Planned workload: 10,000 custom events; 1 KB payload; 10,000 deliveries to a service in the same account; no archive, replay, Scheduler, Pipes, API destinations, or cross-account/bus workload entered. |
| SNS | Planned workload: Standard topics; 1,000 requests and 2,000 EMAIL/EMAIL-JSON notifications; no FIFO, SMS, or other delivery workload entered. |
| Amplify | Standard build instance, 8 GB memory / 4 vCPUs; 100 build minutes, assumed as 20 builds × 5 minutes; 200 MB stored; 5 GB served; no SSR request workload or WAF selected. |
| X-Ray | 10,000 requests; assumed 10% sampling = 1,000 recorded traces; zero queries and retrieved traces; Insights disabled. |

Lambda durations are estimates, not measured averages. The template's timeouts are 15 seconds for standard functions and 90 seconds for photo analysis; timeouts are not the execution durations used for pricing.

The DynamoDB write volume is a normalized allowance for billable writes, including the two global secondary indexes and transaction amplification. It should not be interpreted as 50,000 application write operations without accounting for those effects. The read assumption corresponds to approximately 100,000 read request units for items of the assumed size.

## Scope and limitations

- **EventBridge and SNS are planned allowances.** No EventBridge, Scheduler, or SNS resources were found in the reviewed template or repository search. Their presence in this estimate does not demonstrate that they are deployed. Confirm their deployment status before final submission.
- **Bedrock volume is intentionally higher than photo Lambda volume.** The Calculator rejected fractional values for the attempted rate fields. The accepted setting of one request/minute for one hour/day represents approximately 1,800 requests over 30 days, compared with 100 photo Lambda invocations. This estimate retains that conservative Bedrock workload and is not a fully aligned end-to-end traffic scenario. Recalculate both services together if a consistent 100-photo/month scenario is required.
- **Integer-field rounding increases two allowances.** Planned PITR storage of 0.1 GB was entered as 1 GB, and planned S3 internet transfer of 0.1 GB was entered as 1 GB because those selected fields rejected decimals. EventBridge was entered using the per-month unit and the actual value 10,000.
- **Free Tier treatment varies.** Lambda was estimated using “Without Free Tier”; Amplify was estimated without Free Tier deductions; Cognito's zero cost reflects the selected Calculator allowance. Actual account eligibility and shared account usage have not been audited. This is not a uniform estimate with all Free Tier benefits removed.
- **Retention is an assumption, not an infrastructure change.** CloudWatch pricing assumes one month of retention. The reviewed template does not explicitly configure log retention, so logs may accumulate indefinitely unless retention is configured separately.
- **Tracing is enabled; sampling remains an assumption.** Lambda Active tracing and API Gateway tracing are present in the template. The assumed 10% X-Ray sampling rate has not been confirmed in deployed sampling rules.
- **Additional costs depend on actual deployment and usage.** This scenario includes no custom domain, SMS notifications, paid support, or additional environments. Taxes are excluded. Actual charges may differ with retries, larger images/items, longer execution, additional logs, higher transfer, model changes, and resources outside this scope.

## Method and supporting evidence

1. Review the two source files and identify the deployed configuration and resources retained on deletion.
2. Create an AWS Pricing Calculator estimate in `us-east-1` and add every required service, plus Amplify and X-Ray.
3. Enter the assumptions above. Check units carefully: 0.01 million API requests means 10,000 requests; EventBridge uses 10,000 events per month directly.
4. Save each service configuration. Confirm the Bedrock inputs are 1,000 text input tokens, 500 output tokens, and a 1024 × 1024 image, avoiding the earlier incorrect one-token / 1 × 1 image inputs.
5. Save and share the complete estimate; export PDF, JSON, and CSV. Compare the summary totals and retain the exports as evidence.
6. Divide the exported monthly total by 30 to report the daily equivalent.

Saved estimate: [AWS Pricing Calculator — Group 2 development estimate](https://calculator.aws/#/estimate?id=65e464b771d2eaca71851be32afdadcb4ebe475d).

The latest JSON export also contains a separate snapshot URL: [export snapshot](https://calculator.aws/#/estimate?id=fba3992f9a8ce8392e8436d1ec6c9525d10f4cb1). The first link is the final share link supplied after the correction; the second records the JSON export's provenance.

Supporting Calculator exports and team guide:

- [PDF cost estimate](cost-estimate/group2-aws-cost-estimate.pdf)
- [JSON estimate parameters](cost-estimate/group2-aws-cost-estimate.json)
- [CSV cost breakdown](cost-estimate/group2-aws-cost-estimate.csv)
- [Word team guide](cost-estimate/group2-aws-pricing-team-guide.docx)

The PDF records USD 3.25/month, USD 0.00 upfront, and USD 39.00 over 12 months. The Word team guide explains the detailed estimation workflow and is included in this repository.

## Cost control and cleanup

Recommended controls are to review actual costs after demonstrations, limit repeated photo-analysis calls, monitor Lambda duration and log ingestion, and configure CloudWatch retention explicitly. A USD 10 monthly AWS Budget with alerts is suggested for this development scenario; it has not been configured as part of this work. Budget alerts notify the team and do not cap spending.

After preserving submission evidence and agreeing the shutdown with the team:

1. Identify the correct environment and export any data that must be retained.
2. Delete the environment's CloudFormation/SAM stack when it is no longer needed.
3. Review retained resources separately. The DynamoDB table and photo S3 bucket have `Retain` policies, so stack deletion alone does not remove them or end all storage charges. Delete approved retained data, objects, backups, and resources as appropriate.
4. Review CloudWatch log groups and remove logs no longer required. Review the separately deployed Amplify app, branches, and hosting resources.
5. Review SAM deployment artifacts and remove only environment-owned artifacts that are no longer needed; do not delete a shared deployment bucket indiscriminately.
6. If EventBridge schedules/rules or SNS resources were added later, disable or delete the environment's resources and subscriptions as appropriate.
7. Check billing after usage reporting catches up to confirm that no unwanted billable resources remain.

This document records an estimate and a cleanup procedure. It does not assert that budgets, retention changes, or resource deletion have been performed.
