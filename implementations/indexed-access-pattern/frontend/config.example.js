/*
  Copy this file to config.js and replace the placeholder values for the
  AWS account and deployment being used.

  config.js is excluded from Git. Do not add passwords, access keys,
  client secrets or tokens to browser configuration.
*/
window.APP_CONFIG = {
  cognitoDomain: "YOUR_COGNITO_DOMAIN",
  clientId: "YOUR_COGNITO_APP_CLIENT_ID",
  redirectUri: "YOUR_CLOUDFRONT_URL",
  apiBaseUrl: "YOUR_API_GATEWAY_STAGE_URL"
};
