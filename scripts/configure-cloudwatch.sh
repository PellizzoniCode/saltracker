#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ALERT_EMAIL="${1:-}"

ASSET_FUNCTION="smart-asset-api-${ENVIRONMENT}"
HEALTH_FUNCTION="smart-asset-health-${ENVIRONMENT}"
API_NAME="smart-asset-tracker-${ENVIRONMENT}"
TOPIC_NAME="smart-asset-tracker-alerts"

TOPIC_ARN="$(aws sns create-topic \
  --name "${TOPIC_NAME}" \
  --region "${REGION}" \
  --query TopicArn \
  --output text)"

aws logs put-retention-policy \
  --log-group-name "/aws/lambda/${ASSET_FUNCTION}" \
  --retention-in-days 30 \
  --region "${REGION}"

aws logs put-retention-policy \
  --log-group-name "/aws/lambda/${HEALTH_FUNCTION}" \
  --retention-in-days 14 \
  --region "${REGION}"

if [[ -n "${ALERT_EMAIL}" ]]; then
  SUBSCRIBED_ENDPOINTS="$(aws sns list-subscriptions-by-topic \
    --topic-arn "${TOPIC_ARN}" \
    --region "${REGION}" \
    --query 'Subscriptions[].Endpoint' \
    --output text)"

  if ! grep -Fqw -- "${ALERT_EMAIL}" <<<"${SUBSCRIBED_ENDPOINTS}"; then
    aws sns subscribe \
      --topic-arn "${TOPIC_ARN}" \
      --protocol email \
      --notification-endpoint "${ALERT_EMAIL}" \
      --region "${REGION}"
    echo "Confirm the SNS subscription from the email AWS sends to ${ALERT_EMAIL}."
  fi
fi

aws cloudwatch put-metric-alarm \
  --alarm-name "${ASSET_FUNCTION}-errors" \
  --alarm-description "Asset API Lambda returned errors" \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions "Name=FunctionName,Value=${ASSET_FUNCTION}" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "${TOPIC_ARN}" \
  --ok-actions "${TOPIC_ARN}" \
  --region "${REGION}"

aws cloudwatch put-metric-alarm \
  --alarm-name "${ASSET_FUNCTION}-throttles" \
  --alarm-description "Asset API Lambda was throttled" \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions "Name=FunctionName,Value=${ASSET_FUNCTION}" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "${TOPIC_ARN}" \
  --ok-actions "${TOPIC_ARN}" \
  --region "${REGION}"

aws cloudwatch put-metric-alarm \
  --alarm-name "${ASSET_FUNCTION}-5xx" \
  --alarm-description "API Gateway returned server errors" \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions "Name=ApiName,Value=${API_NAME}" "Name=Stage,Value=${ENVIRONMENT}" \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions "${TOPIC_ARN}" \
  --ok-actions "${TOPIC_ARN}" \
  --region "${REGION}"

echo "CloudWatch monitoring configured."
echo "SNS topic: ${TOPIC_ARN}"

