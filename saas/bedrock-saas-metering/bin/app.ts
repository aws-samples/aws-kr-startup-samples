#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { BedrockMeteringStack } from '../lib/bedrock-metering-stack';
import { MeteringAnalyticsStack } from '../lib/metering-analytics-stack';

const app = new cdk.App();

// 메인 SaaS 스택 - Cognito, API Gateway, Lambda, Bedrock 미터링
const meteringStack = new BedrockMeteringStack(app, 'BedrockMeteringStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// 분석 스택 - Athena를 이용한 테넌트별 사용량 집계
new MeteringAnalyticsStack(app, 'MeteringAnalyticsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  logGroup: meteringStack.meteringLogGroup,
});