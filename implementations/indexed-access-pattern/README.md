# Indexed Asset Access Implementation

## Overview

This is an independently built and tested alternative implementation for the AWS Smart Asset Lifecycle Tracker.

It demonstrates how DynamoDB secondary indexes and `Query` operations can retrieve assets efficiently without scanning the entire table. This implementation is provided as a proof of concept and does not replace the existing implementation.

## AWS Services Used

- Amazon Cognito
- Amazon API Gateway
- AWS Lambda
- Amazon DynamoDB
- Amazon S3
- Amazon CloudFront

## What I Implemented

- Cognito user authentication
- Protected API Gateway endpoints
- Backend authorization using Cognito claims
- Asset creation Lambda function
- Individual asset retrieval Lambda function
- Employee asset-listing Lambda function
- DynamoDB `EmployeeIndex`
- DynamoDB `DepartmentIndex`
- Private S3 frontend delivered through CloudFront

## Employee Asset Access

The completed end-to-end employee flow is:

1. The employee signs in using Cognito.
2. Cognito provides a JWT authentication token.
3. The frontend sends the token to API Gateway.
4. Lambda reads the authenticated employee identity from the token.
5. Lambda queries `EmployeeIndex`.
6. Only assets assigned to that employee are returned.

## Department Access

`DepartmentIndex` was created and tested separately using DynamoDB queries. Complete manager authorization and frontend integration are not yet implemented.

## Current Status

The employee asset-listing flow works end-to-end.

The create-asset and get-asset backend functions have also been implemented and tested, but they still require complete frontend integration and CORS verification.

## Integration

This implementation can be compared with the existing scan-based approach. The team can review and selectively integrate the indexes, query operations and authorization logic into the shared application.
