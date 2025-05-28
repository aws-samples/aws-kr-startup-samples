#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SageMakerLLMStack } from '../lib/sagemaker-llm-stack';

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-west-2'
};

// Application configuration
interface AppConfig {
  modelS3Uri: string;
  modelName?: string;
  endpointName?: string;
  instanceType?: string;
  instanceCount?: number;
  volumeSize?: number;
  healthCheckTimeout?: number;
}

// Get bucket name from environment variable or use default
const bucketName = process.env.CDK_BUCKET_NAME || 'sagemaker-us-west-2-803936485311';

// Default configuration
const config: AppConfig = {
  modelS3Uri: `s3://${bucketName}/llama3-blsm-8b/model.tar.gz`,
  modelName: 'llama3-blsm-8b',
  instanceType: 'ml.inf2.xlarge',
  instanceCount: 1,
  volumeSize: 64,
  healthCheckTimeout: 600,
};

if (process.env.CDK_MODEL_NAME) {
  config.modelName = process.env.CDK_MODEL_NAME;
}
if (process.env.CDK_ENDPOINT_NAME) {
  config.endpointName = process.env.CDK_ENDPOINT_NAME;
}
if (process.env.CDK_INSTANCE_TYPE) {
  config.instanceType = process.env.CDK_INSTANCE_TYPE;
}
if (process.env.CDK_INSTANCE_COUNT) {
  config.instanceCount = parseInt(process.env.CDK_INSTANCE_COUNT, 10);
}
if (process.env.CDK_VOLUME_SIZE) {
  config.volumeSize = parseInt(process.env.CDK_VOLUME_SIZE, 10);
}
if (process.env.CDK_HEALTH_CHECK_TIMEOUT) {
  config.healthCheckTimeout = parseInt(process.env.CDK_HEALTH_CHECK_TIMEOUT, 10);
}

console.log(`🚀 Deploying SageMaker LLM Endpoint`);
console.log(`📦 Model S3 URI: ${config.modelS3Uri}`);
console.log(`🏷️  Model Name: ${config.modelName || 'auto-generated'}`);
console.log(`📡 Endpoint Name: ${config.endpointName || 'auto-generated'}`);
console.log(`🖥️  Instance Type: ${config.instanceType}`);
console.log(`📊 Instance Count: ${config.instanceCount}`);
console.log(`💾 Volume Size: ${config.volumeSize} GB`);
console.log(`⏱️  Health Check Timeout: ${config.healthCheckTimeout} seconds`);

// Create CDK App
const app = new cdk.App();

// Create the SageMaker LLM Stack
new SageMakerLLMStack(app, 'SageMakerLLM', {
  env,
  stackName: 'SageMakerLLM',
  description: 'SageMaker LLM Endpoint for Korean Llama3 model',
  
  // Pass configuration to the stack
  modelS3Uri: config.modelS3Uri,
  modelName: config.modelName,
  endpointName: config.endpointName,
  instanceType: config.instanceType,
  instanceCount: config.instanceCount,
  volumeSize: config.volumeSize,
  healthCheckTimeout: config.healthCheckTimeout,
  
  // Add tags
  tags: {
    Project: 'SageMakerLLM',
    ModelType: 'Llama3-Korean',
    CostCenter: 'AI-ML',
    Owner: 'ML-Team',
    ManagedBy: 'CDK'
  }
});

// Synthesize the CDK app
app.synth();
