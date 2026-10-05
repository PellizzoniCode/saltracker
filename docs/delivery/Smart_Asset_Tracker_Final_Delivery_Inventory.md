# Final Delivery Plan and Materials Inventory
## AWS Smart Asset Lifecycle Tracker — Group 2

**Inventory date:** 5 October 2026  
**Document revision:** 10 — consolidated delivery edits  
**Document language:** English  
**Delivery status:** Preparation in progress; acceptance evidence and final team review remain outstanding.

This document maps the final submission requirements to available materials, defines the proposed delivery package, and records the remaining work. It is a delivery tracker, not a statement that every requirement has passed.

## 1. Scope and evidence basis

This inventory includes only the latest relevant delivery documents: the Markdown delivery plan, the Week 4 presentation and the current cost-estimate materials.

The GitHub issue list was retrieved for the progress snapshot in section 12. The repository implementation files and deployed application functionality were not audited for this document. A file not found in this inventory may already exist in the repository or another team workspace. “Not located” means no verified submission artifact has been identified here, rather than proof that the work has not been done.

## 2. Delivery links and version control

| Item | Location | Current evidence / next action |
| --- | --- | --- |
| Application | [Application URL](https://main.dx980x98nt3d5.amplifyapp.com/) | This URL needs to be confirmed for the final delivery. |
| Git repository | [saltracker repository](https://github.com/PellizzoniCode/saltracker) | Confirm the submission branch, commit SHA and release tag. |
| AWS Pricing Calculator | [Calculator](https://calculator.aws/) | Tool used to prepare the estimate. |
| Shared cost estimate | [Group 2 estimate](https://calculator.aws/#/estimate?id=98808bdeb1af05aa13d820d3abe167b94a322e0a) | Link recorded in the latest JSON export and cost guide; verify instructor access before submission. |
| Final slides | `Smart_Asset_Tracker_Week_4_Final_Presentation_Updated.pptx` | Current saved version 6; 10 editable slides. |
| Requirements | `Assest Tracker Requirements.pdf` | Authoritative project requirements; submission and demo on page 10, cost/cleanup on page 11. |
| GitHub issues — open | [View open issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue%20is%3Aopen) | 7 open issues at last check; link opens the current list. |
| GitHub issues — closed | [View closed issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue%20is%3Aclosed) | 15 closed issues at last check; link opens the current list. |
| GitHub issues — all | [View all issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue) | 22 issues in total; open and closed. |
| Submission destination | To be confirmed from instructor directions | Record the portal/folder/link, submission deadline and access requirements. |
| Delivery coordinator | To be agreed by the team | One person should assemble and check the package; responsibilities below are suggestions until agreed. |

Keep a single submission index and a single final slide deck. Record the final repository commit, deployed environment, evidence capture date and package version in the index. Do not use an unmerged PR snapshot as proof of the deployed application.

## 3. Required submission materials — readiness matrix

| # | Required material | Existing material | Status | Remaining work / proposed package destination |
| --- | --- | --- | --- | --- |
| 1 | Working application URL | Proposed Amplify URL in section 2 and the final slides | Final URL confirmation required | This URL needs to be confirmed for the final delivery. Then complete the demo and record the environment/date in `README.md`. |
| 2 | Git repository | Repository URL above | Link available; submission revision unconfirmed | Record branch, commit SHA and optional release tag in `README.md`. |
| 3 | Architecture diagram | Native architecture diagram in final slides, slide 4 | Available in slides; deployment alignment to check | Export a standalone diagram and supply editable source if available under `architecture/`. Reconcile actual EventBridge/SNS resources. |
| 4 | Infrastructure-as-Code templates | Slides and cost guide refer to AWS SAM; no standalone final template identified in this inventory | Repository confirmation required | Link/copy the final SAM templates and safe deployment instructions under `infrastructure/`. |
| 5 | DynamoDB data-model documentation | No verified standalone final document located here | Locate or complete | Document keys, GSIs, entities, access patterns and example synthetic records in `docs/dynamodb-data-model.md`. |
| 6 | Cognito groups and permissions | Five required roles described in final slides | Partial; deployed permissions to verify | Provide a backend permissions matrix and tests in `docs/cognito-groups-permissions.md`. |
| 7 | Screenshots of working application | No verified final application screenshot set selected | Evidence set to collect or confirm | Select fresh screenshots from the final deployment, caption them and map them to demo steps under `evidence/application/`. |
| 8 | Depreciation calculation documentation | Straight-line approach in slides and requirements | Partial; implementation-specific document not located | Record formula, elapsed-time convention, rounding, date handling, salvage floor and tested examples in `docs/depreciation.md`. |
| 9 | AI prompt and structured-output example | AI workflow described in slides; no verified final prompt/output pair located | Locate or complete | Include actual prompt/schema and a sanitized output example with human corrections in `docs/ai-prompt-and-output.md`. |
| 10 | Security test results | Expected criteria in slide 7 | Final deployment results outstanding | Record actual results, timestamps, roles, expected/actual responses and evidence links in `evidence/security/security-test-results.md`. |
| 11 | CloudWatch dashboard or log screenshots | Monitoring described in slides and cost guide | Deployment captures not verified | Capture relevant logs/alarms after demo requests under `evidence/monitoring/`. |
| 12 | Estimated monthly AWS cost | Latest `group2-aws-cost-estimate(1).pdf`, `.json`, and `group2-aws-pricing-team-guide(1).docx` | Available; assumptions/export consistency to review | Deliver latest exports and guide under `cost/`; use USD 3.55/month. Obtain matching latest CSV if required for reproducibility. |
| 13 | Team contribution summary | All six names and a collective contribution summary in section 9 | Draft prepared | Include the shared summary in the final package; align slide 9 with this collective wording. |
| 14 | Final presentation slides | Current Week 4 PPTX, version 6 | Prepared; final factual sign-off pending | Resolve remaining pending statements and package under `presentation/`. PDF is optional. |
| 15 | Short project reflection | Lessons in slide 9 | Partial; standalone reflection not located | Write a brief team reflection in `docs/project-reflection.md`. |

The package paths above are proposed destinations. They do not assert that these files have already been created.

## 4. Inventory of relevant delivery materials

### Relevant delivery files — latest versions only

The table contains one current version per relevant document or export format.

| Latest file | Requirement / purpose | Delivery treatment |
| --- | --- | --- |
| `Smart_Asset_Tracker_Final_Delivery_Inventory.md` | Delivery plan, requirements mapping and links to open/closed GitHub issue lists | Current updated document; include in `docs/delivery/`. |
| `Smart_Asset_Tracker_Week_4_Final_Presentation_Updated.pptx` | Final slides and architecture diagram | Latest prepared deck, saved version 6. Include in `docs/delivery/`; obtain final team review and factual sign-off. |
| `group2-aws-cost-estimate(1).pdf` | Estimated monthly AWS cost | Latest supplied human-readable export dated 4 October 2026: USD 3.55/month, USD 42.60/year, USD 0 upfront. |
| `group2-aws-cost-estimate(1).json` | Cost-estimate reproducibility | Latest supplied machine-readable export. Keep with the matching PDF and shared Calculator link; review parameter consistency. |
| `group2-aws-pricing-team-guide(1).docx` | Cost assumptions; cost monitoring and cleanup plan | Latest supplied guide. Confirm deployed resources and distinguish recommendations from actions actually performed. |

The initial delivery PR contains only this Markdown document and the PPTX. Cost materials can remain in their established repository location and be linked from the final submission index.

Application, repository and AWS Pricing Calculator links are listed in section 2. Missing or unverified submission materials remain tracked in section 3. Selected final application and monitoring evidence should be added to the delivery package only when it covers a specific requirement.

## 5. Proposed submission package

Deliver one indexed package, using the instructor’s designated channel. A repository release or shared folder can host it; a ZIP can be supplied if requested. These are packaging recommendations, not confirmed instructor instructions.

| Folder / file | Contents |
| --- | --- |
| `README.md` | Application/repository links, final commit, environment, requirement-to-file index, known limitations and demo instructions |
| `architecture/` | Architecture PNG/PDF and editable source |
| `infrastructure/` | SAM/CloudFormation templates or precise repository links, deployment instructions and sanitized example configuration |
| `docs/` | DynamoDB model, Cognito permissions, depreciation, AI prompt/output, contributions and reflection |
| `evidence/application/` | Captioned screenshots from the working final deployment |
| `evidence/security/` | Actual security test results and supporting captures |
| `evidence/monitoring/` | CloudWatch logs/dashboard/alarm evidence |
| `cost/` | Current estimate PDF/JSON, matching CSV if available, cost assumptions and cleanup plan |
| `presentation/` | Final Week 4 PPTX; optional PDF |
| `cleanup/` | Resource inventory, cleanup checklist and post-grading verification record |

Use relative links in the submission index so the package remains usable after download. If files stay in GitHub, link to the selected commit rather than a changing branch wherever practical. Verify that the instructor can access every link without receiving AWS credentials.

## 6. Required final demonstration and evidence checklist

All 12 steps are planned in the final presentation speaker notes. Their successful execution still needs to be recorded against the selected deployment.

| Step | Demonstration | Evidence to collect | Result |
| --- | --- | --- | --- |
| 1 | Attempt application access without signing in | Login redirect / denied protected-page access | Pending |
| 2 | Successful Cognito login | Authenticated application screen | Pending |
| 3 | Manual asset creation | Form and saved synthetic asset | Pending |
| 4 | Asset creation using an uploaded photograph | Upload and saved photo-based asset | Pending |
| 5 | Review and correction of AI-generated information | Suggested values, corrected values and confirmation before save | Pending |
| 6 | Manual fallback when an image cannot be identified | Unclear image/error and usable manual-entry form | Pending |
| 7 | Automatic depreciation calculation | Purchase/salvage/useful-life inputs and calculated value | Pending |
| 8 | Maintenance-record creation | New record in asset history | Pending |
| 9 | AI maintenance or replacement recommendation | Action, priority/date and explanation | Pending |
| 10 | Restricted action blocked | Auditor write attempt and backend denial | Pending |
| 11 | CloudWatch monitoring information | Logs or monitoring capture associated with demo activity | Pending |
| 12 | Logout and loss of application access | Logged-out screen and failed protected access | Pending |

Use synthetic assets and test identities. Prepare a clear image and an unidentifiable image in advance. Record a fallback video or screenshots if useful, but preserve the required live demonstration unless the instructor approves another format.

## 7. Security results to document

| Test | Expected behavior | Required record |
| --- | --- | --- |
| Unauthenticated protected route | Redirect to login; no asset information displayed | Actual result and screenshot |
| API request without valid token | 401 Unauthorized | Sanitized status/response |
| Auditor modifies an asset | Backend refuses modification | Test role, request/action, actual response and unchanged record |
| Anonymous photograph access | Private image cannot be retrieved anonymously | Sanitized access test |
| Authorized photograph access | Permitted user retrieves image securely | Actual result |
| Source/configuration review | No credentials or tokens stored in source | Review scope, method and result |
| Invalid or malicious input | Rejected safely | Input category, expected/actual response and log evidence |

Record the tested commit, environment, execution date and tester. Mark each test Pass, Fail or Blocked based on observed results. Static review and passing CI are useful supporting evidence but do not establish that deployment tests passed.

## 8. Cost, monitoring and cleanup

The latest PDF estimate reports **USD 3.55/month**, **USD 42.60 over 12 months**, **USD 0 upfront**, approximately **USD 0.12/day**. These are estimates for documented assumptions, not observed billing.

The latest guide includes cost-conscious usage assumptions and a cleanup plan. It proposes a USD 10/month budget; it does not establish that a budget has been created. Its earlier repository review describes EventBridge as planned, monitoring SNS/alarms outside SAM, and retained DynamoDB/S3 resources. Confirm the final deployed inventory because later PR changes may alter this description.

The Bedrock export includes multiple parameter sets. The PDF’s relevant image-inference section shows 1 hour/day and 1,000 input / 500 output tokens, while the available JSON has parameters requiring reconciliation. Do not rewrite raw exports to hide differences; verify the final Calculator configuration and re-export a consistent set if necessary.

| Requirement | Existing documentation | Execution / evidence still needed |
| --- | --- | --- |
| Cost-conscious configurations | Latest cost guide and estimate | Confirm deployed settings and actual usage |
| AWS Budget when lab permits | Suggested USD 10/month budget | Create if permitted; otherwise record lab restriction |
| Avoid unnecessary images/records | Cleanup guidance | Review and remove unnecessary data |
| Remove test data containing personal information | Requirement recorded here | Use synthetic data; verify personal test data removal |
| Follow instructor deletion directions | Cleanup guidance | Confirm when resources may be removed |
| Remove unnecessary resources after grading | Guide warns about retained and external resources | Perform cleanup after grading and record verification |

Do not delete resources needed for grading. Before cleanup, preserve required evidence and confirm ownership of shared resources. Check Lambda functions, APIs, DynamoDB tables/backups, S3 objects/buckets, CloudWatch log groups and alarms, SNS topics/subscriptions, EventBridge rules/schedules, Amplify hosting, deployment artifacts and any additional resources introduced in the final templates.

Record each resource’s type, name, region, owner, retention policy, deletion action and verification date. Stack deletion alone may leave retained or externally managed resources. Review billing again after usage reporting catches up.

## 9. Team members

| Team member |
| --- |
| Ashok Hota |
| Ema Sena |
| Gergely Pankucsi |
| Giovanni Pellizzoni |
| Richard Asamoah |
| Mladen Mrkić |

### Team contribution summary

Team members contributed according to their knowledge, available time and capabilities. The project combined application development, infrastructure configuration, testing, peer review, documentation and presentation preparation. The final delivery represents the team’s collective effort.

## 10. Completion sequence

1. Agree on the delivery coordinator, submission destination, deadline and final repository revision.
2. Confirm the deployment corresponds to that revision and record any known limitations.
3. Locate the final documentation and IaC in the repository; fill gaps in the readiness matrix.
4. Execute the 12 demo steps and security tests, then collect application and CloudWatch evidence.
5. Reconcile the architecture, deployed inventory and cost assumptions.
6. Review the collective team summary and complete the short reflection.
7. Update the final slide deck with verified results and the collective team summary.
8. Assemble the indexed package, check every link and inspect for credentials or personal test data.
9. Submit through the instructor’s channel and retain confirmation.
10. After grading, perform authorized cleanup and record resource/billing verification.

## 11. Final submission gate

- [ ] All 15 required materials are linked in the package index.
- [ ] Final branch, commit and deployed environment are recorded.
- [ ] All 12 demonstration steps have been rehearsed and observed results recorded.
- [ ] Security results report actual outcomes rather than expected criteria only.
- [ ] Application and monitoring screenshots match the final deployment.
- [ ] Architecture, IaC and DynamoDB documentation describe the final implementation.
- [ ] AI prompt/output and depreciation examples match application behavior.
- [ ] Cost files use one consistent current estimate and disclose assumptions.
- [ ] The collective team contribution summary has been reviewed for final delivery.
- [ ] Final slides and reflection are included.
- [ ] Instructor access to package/repository/application has been checked.
- [ ] No passwords, AWS access keys, secret keys, session tokens or other credentials are included.
- [ ] Cleanup owner and post-grading plan are agreed.

## 12. GitHub issue tracker

**Checked:** 05 October 2026 at 22:19 CEST (Europe/Belgrade).  

| Issue list | Link | Count at last check |
| --- | --- | ---: |
| Open issues | [View open issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue%20is%3Aopen) | 7 |
| Closed issues | [View closed issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue%20is%3Aclosed) | 15 |
| All issues | [View all issues](https://github.com/PellizzoniCode/saltracker/issues?q=is%3Aissue) | 22 |

The links show the current GitHub issue lists. Counts reflect the last check and may change. Pull requests are excluded. A closed issue indicates team tracking status; final acceptance still requires the corresponding delivery evidence.
