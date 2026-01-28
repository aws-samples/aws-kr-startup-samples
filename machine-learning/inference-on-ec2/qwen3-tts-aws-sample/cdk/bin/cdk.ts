#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { Qwen3TtsStack } from '../lib/cdk-stack';

const app = new cdk.App();
new Qwen3TtsStack(app, 'Qwen3TtsStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'ap-northeast-2',
  },
});
