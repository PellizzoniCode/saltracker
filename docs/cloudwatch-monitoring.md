# CloudWatch monitoring

The monitoring script configures the deployed Smart Asset Lifecycle Tracker with:

- 30-day retention for the asset API Lambda logs
- 14-day retention for the health Lambda logs
- Lambda error and throttle alarms
- API Gateway 5XX alarms
- SNS email notifications for alarm and recovery transitions

## Configure

Sign in to the intended AWS account with the AWS CLI, then run from the repository root:

```bash
bash scripts/configure-cloudwatch.sh your-email@example.com
```

Confirm the subscription using the link in the email from AWS. Re-running the script safely updates the same topic, retention policies, and alarms.

The defaults target `us-east-1` and the `dev` environment. Override them when needed:

```bash
AWS_REGION=us-east-1 ENVIRONMENT=dev bash scripts/configure-cloudwatch.sh your-email@example.com
```

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
