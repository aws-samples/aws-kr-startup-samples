#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { Qwen3TtsVoiceCloningStack } from '../lib/cdk-stack';

const app = new cdk.App();
new Qwen3TtsVoiceCloningStack(app, 'Qwen3TtsVoiceCloningStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'ap-northeast-2',
  },
});
