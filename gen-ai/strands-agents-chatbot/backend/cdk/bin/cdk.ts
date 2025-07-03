#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { FargateStack } from '../lib/cdk-stack';


const app = new cdk.App();
new FargateStack(app, 'StrandsAgents-Chatbot', {
  env: {
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1'
  }
});