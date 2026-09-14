# AWS Smart Asset Lifecycle Tracker

A secure, serverless asset-tracking application developed as part of the Digital Cloud Training project course.

## Project Goal

The application will help an organization register, locate, assign and maintain technology assets. It will calculate asset depreciation and use Amazon Bedrock to provide AI-assisted asset identification and maintenance recommendations.

## Week 1 Milestone

An authenticated user can:

- Log in and log out
- Reset their password
- Access protected application pages
- Manually create an asset
- View asset records
- Search for assets

An unauthenticated user cannot access the application or its protected API.

## Planned AWS Services

- AWS Amplify
- Amazon Cognito
- Amazon API Gateway
- AWS Lambda
- Amazon DynamoDB
- Amazon S3
- Amazon Bedrock
- Amazon EventBridge
- Amazon SNS
- Amazon CloudWatch
- AWS SAM

## Project Status

## Architecture

The architecture is developed cumulatively across the four project weeks. Each week builds on the services and functionality completed during the previous week.

### Complete Target Architecture

The complete architecture represents the final serverless application after all four project weeks.

![Complete AWS architecture](docs/architecture/smart-asset-tracker-full-architecture.png)

### Weekly Architecture Progression

#### Week 1 — Authentication and Core Asset Management

Week 1 establishes the foundation: the Amplify frontend, Cognito authentication, protected API Gateway endpoints, Lambda application logic and DynamoDB asset storage.

![Week 1 architecture](docs/architecture/smart-asset-tracker-week-1-architecture.png)

#### Week 2 — Secure Image Upload and AI Identification

Week 2 extends the Week 1 architecture with private S3 image storage, an AI-processing Lambda function, Amazon Bedrock and human review of AI-generated suggestions.

![Week 2 architecture](docs/architecture/smart-asset-tracker-week-2-architecture.png)

#### Week 3 — Depreciation and Maintenance Automation

Week 3 extends the previous architecture with depreciation calculations, maintenance history, scheduled EventBridge checks, a maintenance Lambda function and SNS notifications.

![Week 3 architecture](docs/architecture/smart-asset-tracker-week-3-architecture.png)

#### Week 4 — Security, Monitoring and Deployment

Week 4 completes the architecture with CloudWatch monitoring, security hardening, testing and repeatable Infrastructure-as-Code deployment.

![Week 4 architecture](docs/architecture/smart-asset-tracker-week-4-architecture.png)

Week 1 — Authentication and core asset management.

## Security

AWS credentials, passwords, access tokens and personal information must never be committed to this repository.
