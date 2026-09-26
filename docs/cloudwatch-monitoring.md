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

If you deployed this stack before this change (or ran the old `scripts/configure-cloudwatch.sh`), the Lambda log groups already exist outside CloudFormation. Deploying the new template will fail with "log group already exists" unless you first remove them so CloudFormation can (re)create and manage them:

```bash
for fn in api health photo-upload photo-analysis photo-analysis-api; do
  aws logs delete-log-group --log-group-name "/aws/lambda/smart-asset-${fn}-dev" --region us-east-1 || true
done
```

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
