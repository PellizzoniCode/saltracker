# CloudWatch monitoring

Monitoring is defined in `infrastructure/template.yaml` and deploys with the rest of the stack — there is no separate manual step. It provisions:

- 30-day retention for the asset API and photo-analysis Lambda logs; 14-day retention for health, photo-upload, and photo-analysis-API logs
- Lambda error and throttle alarms for the asset API and photo-analysis functions
- A photo-upload error alarm
- An API Gateway 5XX alarm
- An SNS topic, with an optional email subscription

## Configure

Pass an email address as a stack parameter to receive alarm notifications:

```bash
sam deploy --parameter-overrides Environment=dev AlertEmail=your-email@example.com
```

Leaving `AlertEmail` blank (the default) skips creating the subscription — the topic and alarms are still created, so you can subscribe another endpoint (e.g. a queue) later.

Confirm the subscription using the link in the email AWS sends. Re-deploying with the same `AlertEmail` is a no-op for the subscription; changing it replaces the subscription.

### Migrating an existing deployment

Lambda auto-creates `/aws/lambda/<function>` on first invoke, so any environment that has run before already owns the log groups this template now declares. A plain deploy fails with "log group already exists". **Do not delete them** (that destroys the logs). Import them into the stack instead. Run this once per environment (`test`, `dev`, ...), before that environment's first deploy of this template. The groups are declared with `DeletionPolicy: Retain`, which import requires.

The six groups are `api`, `health`, `photo-upload`, `photo-analysis`, `photo-analysis-api` and `maintenance-scheduler`, mapped to the template's logical IDs below.

1. **Find which groups already exist.** A function that never ran has no group; CloudFormation creates those in step 4, so only import the ones listed here.

   ```bash
   ENVIRONMENT=test   # match the stack you're migrating
   REGION=us-east-1
   aws logs describe-log-groups --region $REGION \
     --log-group-name-prefix "/aws/lambda/smart-asset-" \
     --query "logGroups[?ends_with(logGroupName, '-${ENVIRONMENT}')].[logGroupName,storedBytes,retentionInDays]" \
     --output table
   ```

   Note `storedBytes` for each group so you can compare after the migration.

2. **Build an import template.** An import change set may not create or modify anything else, so it must be the template that is *currently deployed* (e.g. `git show <deployed-commit>:infrastructure/template.yaml`) plus only the log-group resources found in step 1, copied from `infrastructure/template.yaml` with their `DeletionPolicy`/`UpdateReplacePolicy`. Do not include alarms, the SNS topic or other new resources yet.

3. **Import.** Map each existing group to its logical ID (`AssetApiLogGroup` -> `smart-asset-api-$ENVIRONMENT`, `HealthLogGroup` -> `...-health-...`, `PhotoUploadLogGroup` -> `...-photo-upload-...`, `PhotoAnalysisLogGroup` -> `...-photo-analysis-...`, `PhotoAnalysisApiLogGroup` -> `...-photo-analysis-api-...`, `MaintenanceSchedulerLogGroup` -> `...-maintenance-scheduler-...`):

   ```bash
   aws cloudformation create-change-set --region $REGION \
     --stack-name smart-asset-tracker-$ENVIRONMENT --change-set-name import-log-groups \
     --change-set-type IMPORT --capabilities CAPABILITY_IAM \
     --template-body file://import-template.yaml \
     --parameters ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
     --resources-to-import '[{"ResourceType":"AWS::Logs::LogGroup","LogicalResourceId":"AssetApiLogGroup","ResourceIdentifier":{"LogGroupName":"/aws/lambda/smart-asset-api-'$ENVIRONMENT'"}}]'   # one entry per existing group
   aws cloudformation describe-change-set --region $REGION --stack-name smart-asset-tracker-$ENVIRONMENT --change-set-name import-log-groups
   aws cloudformation execute-change-set --region $REGION --stack-name smart-asset-tracker-$ENVIRONMENT --change-set-name import-log-groups
   ```

4. **Deploy the new template normally** (see `docs/photo-storage-migration.md` for the parameter ordering). This applies retention, creates the alarms and SNS topic, and creates any group that did not exist.

5. **Confirm nothing was lost.** Re-run the step 1 command: `storedBytes` must be at least what you recorded, and `retentionInDays` should now be 30 (api, photo-analysis, maintenance-scheduler) or 14 (health, photo-upload, photo-analysis-api).

If you would rather not import, the alternative is to export each group to S3 (`aws logs create-export-task`) and then delete it before deploying; that keeps an archive but loses the live logs.

Any CloudWatch alarms or SNS topic/subscription created by the old script are unrelated to the ones this template manages and can be deleted separately once you've confirmed the new ones are in place.

## Inspect

List the alarms:

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix smart-asset \
  --region us-east-1 \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue}' \
  --output table
```

Tail application logs:

```bash
aws logs tail /aws/lambda/smart-asset-api-dev \
  --since 15m \
  --follow \
  --region us-east-1
```

Do not store AWS access keys or other credentials in this repository.
