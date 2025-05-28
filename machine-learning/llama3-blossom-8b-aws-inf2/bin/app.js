#!/usr/bin/env node
"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
require("source-map-support/register");
const cdk = __importStar(require("aws-cdk-lib"));
const sagemaker_llm_stack_1 = require("../lib/sagemaker-llm-stack");
// Environment configuration
const env = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2'
};
// Get bucket name from environment variable or use default
const bucketName = process.env.CDK_BUCKET_NAME || 'sagemaker-us-west-2-803936485311';
// Default configuration
const config = {
    modelS3Uri: `s3://${bucketName}/llama3-blsm-8b/model.tar.gz`,
    modelName: 'llama3-korean',
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
new sagemaker_llm_stack_1.SageMakerLLMStack(app, 'SageMakerLLM', {
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXBwLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiYXBwLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0FBQ0EsdUNBQXFDO0FBQ3JDLGlEQUFtQztBQUNuQyxvRUFBK0Q7QUFFL0QsNEJBQTRCO0FBQzVCLE1BQU0sR0FBRyxHQUFHO0lBQ1YsT0FBTyxFQUFFLE9BQU8sQ0FBQyxHQUFHLENBQUMsbUJBQW1CO0lBQ3hDLE1BQU0sRUFBRSxPQUFPLENBQUMsR0FBRyxDQUFDLGtCQUFrQixJQUFJLFdBQVc7Q0FDdEQsQ0FBQztBQWFGLDJEQUEyRDtBQUMzRCxNQUFNLFVBQVUsR0FBRyxPQUFPLENBQUMsR0FBRyxDQUFDLGVBQWUsSUFBSSxrQ0FBa0MsQ0FBQztBQUVyRix3QkFBd0I7QUFDeEIsTUFBTSxNQUFNLEdBQWM7SUFDeEIsVUFBVSxFQUFFLFFBQVEsVUFBVSw4QkFBOEI7SUFDNUQsU0FBUyxFQUFFLGVBQWU7SUFDMUIsWUFBWSxFQUFFLGdCQUFnQjtJQUM5QixhQUFhLEVBQUUsQ0FBQztJQUNoQixVQUFVLEVBQUUsRUFBRTtJQUNkLGtCQUFrQixFQUFFLEdBQUc7Q0FDeEIsQ0FBQztBQUVGLElBQUksT0FBTyxDQUFDLEdBQUcsQ0FBQyxjQUFjLEVBQUU7SUFDOUIsTUFBTSxDQUFDLFNBQVMsR0FBRyxPQUFPLENBQUMsR0FBRyxDQUFDLGNBQWMsQ0FBQztDQUMvQztBQUNELElBQUksT0FBTyxDQUFDLEdBQUcsQ0FBQyxpQkFBaUIsRUFBRTtJQUNqQyxNQUFNLENBQUMsWUFBWSxHQUFHLE9BQU8sQ0FBQyxHQUFHLENBQUMsaUJBQWlCLENBQUM7Q0FDckQ7QUFDRCxJQUFJLE9BQU8sQ0FBQyxHQUFHLENBQUMsaUJBQWlCLEVBQUU7SUFDakMsTUFBTSxDQUFDLFlBQVksR0FBRyxPQUFPLENBQUMsR0FBRyxDQUFDLGlCQUFpQixDQUFDO0NBQ3JEO0FBQ0QsSUFBSSxPQUFPLENBQUMsR0FBRyxDQUFDLGtCQUFrQixFQUFFO0lBQ2xDLE1BQU0sQ0FBQyxhQUFhLEdBQUcsUUFBUSxDQUFDLE9BQU8sQ0FBQyxHQUFHLENBQUMsa0JBQWtCLEVBQUUsRUFBRSxDQUFDLENBQUM7Q0FDckU7QUFDRCxJQUFJLE9BQU8sQ0FBQyxHQUFHLENBQUMsZUFBZSxFQUFFO0lBQy9CLE1BQU0sQ0FBQyxVQUFVLEdBQUcsUUFBUSxDQUFDLE9BQU8sQ0FBQyxHQUFHLENBQUMsZUFBZSxFQUFFLEVBQUUsQ0FBQyxDQUFDO0NBQy9EO0FBQ0QsSUFBSSxPQUFPLENBQUMsR0FBRyxDQUFDLHdCQUF3QixFQUFFO0lBQ3hDLE1BQU0sQ0FBQyxrQkFBa0IsR0FBRyxRQUFRLENBQUMsT0FBTyxDQUFDLEdBQUcsQ0FBQyx3QkFBd0IsRUFBRSxFQUFFLENBQUMsQ0FBQztDQUNoRjtBQUVELE9BQU8sQ0FBQyxHQUFHLENBQUMscUNBQXFDLENBQUMsQ0FBQztBQUNuRCxPQUFPLENBQUMsR0FBRyxDQUFDLG9CQUFvQixNQUFNLENBQUMsVUFBVSxFQUFFLENBQUMsQ0FBQztBQUNyRCxPQUFPLENBQUMsR0FBRyxDQUFDLG9CQUFvQixNQUFNLENBQUMsU0FBUyxJQUFJLGdCQUFnQixFQUFFLENBQUMsQ0FBQztBQUN4RSxPQUFPLENBQUMsR0FBRyxDQUFDLHFCQUFxQixNQUFNLENBQUMsWUFBWSxJQUFJLGdCQUFnQixFQUFFLENBQUMsQ0FBQztBQUM1RSxPQUFPLENBQUMsR0FBRyxDQUFDLHVCQUF1QixNQUFNLENBQUMsWUFBWSxFQUFFLENBQUMsQ0FBQztBQUMxRCxPQUFPLENBQUMsR0FBRyxDQUFDLHNCQUFzQixNQUFNLENBQUMsYUFBYSxFQUFFLENBQUMsQ0FBQztBQUMxRCxPQUFPLENBQUMsR0FBRyxDQUFDLG1CQUFtQixNQUFNLENBQUMsVUFBVSxLQUFLLENBQUMsQ0FBQztBQUN2RCxPQUFPLENBQUMsR0FBRyxDQUFDLDZCQUE2QixNQUFNLENBQUMsa0JBQWtCLFVBQVUsQ0FBQyxDQUFDO0FBRTlFLGlCQUFpQjtBQUNqQixNQUFNLEdBQUcsR0FBRyxJQUFJLEdBQUcsQ0FBQyxHQUFHLEVBQUUsQ0FBQztBQUUxQixpQ0FBaUM7QUFDakMsSUFBSSx1Q0FBaUIsQ0FBQyxHQUFHLEVBQUUsY0FBYyxFQUFFO0lBQ3pDLEdBQUc7SUFDSCxTQUFTLEVBQUUsY0FBYztJQUN6QixXQUFXLEVBQUUsZ0RBQWdEO0lBRTdELGtDQUFrQztJQUNsQyxVQUFVLEVBQUUsTUFBTSxDQUFDLFVBQVU7SUFDN0IsU0FBUyxFQUFFLE1BQU0sQ0FBQyxTQUFTO0lBQzNCLFlBQVksRUFBRSxNQUFNLENBQUMsWUFBWTtJQUNqQyxZQUFZLEVBQUUsTUFBTSxDQUFDLFlBQVk7SUFDakMsYUFBYSxFQUFFLE1BQU0sQ0FBQyxhQUFhO0lBQ25DLFVBQVUsRUFBRSxNQUFNLENBQUMsVUFBVTtJQUM3QixrQkFBa0IsRUFBRSxNQUFNLENBQUMsa0JBQWtCO0lBRTdDLFdBQVc7SUFDWCxJQUFJLEVBQUU7UUFDSixPQUFPLEVBQUUsY0FBYztRQUN2QixTQUFTLEVBQUUsZUFBZTtRQUMxQixVQUFVLEVBQUUsT0FBTztRQUNuQixLQUFLLEVBQUUsU0FBUztRQUNoQixTQUFTLEVBQUUsS0FBSztLQUNqQjtDQUNGLENBQUMsQ0FBQztBQUVILHlCQUF5QjtBQUN6QixHQUFHLENBQUMsS0FBSyxFQUFFLENBQUMiLCJzb3VyY2VzQ29udGVudCI6WyIjIS91c3IvYmluL2VudiBub2RlXG5pbXBvcnQgJ3NvdXJjZS1tYXAtc3VwcG9ydC9yZWdpc3Rlcic7XG5pbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0IHsgU2FnZU1ha2VyTExNU3RhY2sgfSBmcm9tICcuLi9saWIvc2FnZW1ha2VyLWxsbS1zdGFjayc7XG5cbi8vIEVudmlyb25tZW50IGNvbmZpZ3VyYXRpb25cbmNvbnN0IGVudiA9IHtcbiAgYWNjb3VudDogcHJvY2Vzcy5lbnYuQ0RLX0RFRkFVTFRfQUNDT1VOVCxcbiAgcmVnaW9uOiBwcm9jZXNzLmVudi5DREtfREVGQVVMVF9SRUdJT04gfHwgJ3VzLXdlc3QtMidcbn07XG5cbi8vIEFwcGxpY2F0aW9uIGNvbmZpZ3VyYXRpb25cbmludGVyZmFjZSBBcHBDb25maWcge1xuICBtb2RlbFMzVXJpOiBzdHJpbmc7XG4gIG1vZGVsTmFtZT86IHN0cmluZztcbiAgZW5kcG9pbnROYW1lPzogc3RyaW5nO1xuICBpbnN0YW5jZVR5cGU/OiBzdHJpbmc7XG4gIGluc3RhbmNlQ291bnQ/OiBudW1iZXI7XG4gIHZvbHVtZVNpemU/OiBudW1iZXI7XG4gIGhlYWx0aENoZWNrVGltZW91dD86IG51bWJlcjtcbn1cblxuLy8gR2V0IGJ1Y2tldCBuYW1lIGZyb20gZW52aXJvbm1lbnQgdmFyaWFibGUgb3IgdXNlIGRlZmF1bHRcbmNvbnN0IGJ1Y2tldE5hbWUgPSBwcm9jZXNzLmVudi5DREtfQlVDS0VUX05BTUUgfHwgJ3NhZ2VtYWtlci11cy13ZXN0LTItODAzOTM2NDg1MzExJztcblxuLy8gRGVmYXVsdCBjb25maWd1cmF0aW9uXG5jb25zdCBjb25maWc6IEFwcENvbmZpZyA9IHtcbiAgbW9kZWxTM1VyaTogYHMzOi8vJHtidWNrZXROYW1lfS9sbGFtYTMtYmxzbS04Yi9tb2RlbC50YXIuZ3pgLFxuICBtb2RlbE5hbWU6ICdsbGFtYTMta29yZWFuJyxcbiAgaW5zdGFuY2VUeXBlOiAnbWwuaW5mMi54bGFyZ2UnLFxuICBpbnN0YW5jZUNvdW50OiAxLFxuICB2b2x1bWVTaXplOiA2NCxcbiAgaGVhbHRoQ2hlY2tUaW1lb3V0OiA2MDAsXG59O1xuXG5pZiAocHJvY2Vzcy5lbnYuQ0RLX01PREVMX05BTUUpIHtcbiAgY29uZmlnLm1vZGVsTmFtZSA9IHByb2Nlc3MuZW52LkNES19NT0RFTF9OQU1FO1xufVxuaWYgKHByb2Nlc3MuZW52LkNES19FTkRQT0lOVF9OQU1FKSB7XG4gIGNvbmZpZy5lbmRwb2ludE5hbWUgPSBwcm9jZXNzLmVudi5DREtfRU5EUE9JTlRfTkFNRTtcbn1cbmlmIChwcm9jZXNzLmVudi5DREtfSU5TVEFOQ0VfVFlQRSkge1xuICBjb25maWcuaW5zdGFuY2VUeXBlID0gcHJvY2Vzcy5lbnYuQ0RLX0lOU1RBTkNFX1RZUEU7XG59XG5pZiAocHJvY2Vzcy5lbnYuQ0RLX0lOU1RBTkNFX0NPVU5UKSB7XG4gIGNvbmZpZy5pbnN0YW5jZUNvdW50ID0gcGFyc2VJbnQocHJvY2Vzcy5lbnYuQ0RLX0lOU1RBTkNFX0NPVU5ULCAxMCk7XG59XG5pZiAocHJvY2Vzcy5lbnYuQ0RLX1ZPTFVNRV9TSVpFKSB7XG4gIGNvbmZpZy52b2x1bWVTaXplID0gcGFyc2VJbnQocHJvY2Vzcy5lbnYuQ0RLX1ZPTFVNRV9TSVpFLCAxMCk7XG59XG5pZiAocHJvY2Vzcy5lbnYuQ0RLX0hFQUxUSF9DSEVDS19USU1FT1VUKSB7XG4gIGNvbmZpZy5oZWFsdGhDaGVja1RpbWVvdXQgPSBwYXJzZUludChwcm9jZXNzLmVudi5DREtfSEVBTFRIX0NIRUNLX1RJTUVPVVQsIDEwKTtcbn1cblxuY29uc29sZS5sb2coYPCfmoAgRGVwbG95aW5nIFNhZ2VNYWtlciBMTE0gRW5kcG9pbnRgKTtcbmNvbnNvbGUubG9nKGDwn5OmIE1vZGVsIFMzIFVSSTogJHtjb25maWcubW9kZWxTM1VyaX1gKTtcbmNvbnNvbGUubG9nKGDwn4+377iPICBNb2RlbCBOYW1lOiAke2NvbmZpZy5tb2RlbE5hbWUgfHwgJ2F1dG8tZ2VuZXJhdGVkJ31gKTtcbmNvbnNvbGUubG9nKGDwn5OhIEVuZHBvaW50IE5hbWU6ICR7Y29uZmlnLmVuZHBvaW50TmFtZSB8fCAnYXV0by1nZW5lcmF0ZWQnfWApO1xuY29uc29sZS5sb2coYPCflqXvuI8gIEluc3RhbmNlIFR5cGU6ICR7Y29uZmlnLmluc3RhbmNlVHlwZX1gKTtcbmNvbnNvbGUubG9nKGDwn5OKIEluc3RhbmNlIENvdW50OiAke2NvbmZpZy5pbnN0YW5jZUNvdW50fWApO1xuY29uc29sZS5sb2coYPCfkr4gVm9sdW1lIFNpemU6ICR7Y29uZmlnLnZvbHVtZVNpemV9IEdCYCk7XG5jb25zb2xlLmxvZyhg4o+x77iPICBIZWFsdGggQ2hlY2sgVGltZW91dDogJHtjb25maWcuaGVhbHRoQ2hlY2tUaW1lb3V0fSBzZWNvbmRzYCk7XG5cbi8vIENyZWF0ZSBDREsgQXBwXG5jb25zdCBhcHAgPSBuZXcgY2RrLkFwcCgpO1xuXG4vLyBDcmVhdGUgdGhlIFNhZ2VNYWtlciBMTE0gU3RhY2tcbm5ldyBTYWdlTWFrZXJMTE1TdGFjayhhcHAsICdTYWdlTWFrZXJMTE0nLCB7XG4gIGVudixcbiAgc3RhY2tOYW1lOiAnU2FnZU1ha2VyTExNJyxcbiAgZGVzY3JpcHRpb246ICdTYWdlTWFrZXIgTExNIEVuZHBvaW50IGZvciBLb3JlYW4gTGxhbWEzIG1vZGVsJyxcbiAgXG4gIC8vIFBhc3MgY29uZmlndXJhdGlvbiB0byB0aGUgc3RhY2tcbiAgbW9kZWxTM1VyaTogY29uZmlnLm1vZGVsUzNVcmksXG4gIG1vZGVsTmFtZTogY29uZmlnLm1vZGVsTmFtZSxcbiAgZW5kcG9pbnROYW1lOiBjb25maWcuZW5kcG9pbnROYW1lLFxuICBpbnN0YW5jZVR5cGU6IGNvbmZpZy5pbnN0YW5jZVR5cGUsXG4gIGluc3RhbmNlQ291bnQ6IGNvbmZpZy5pbnN0YW5jZUNvdW50LFxuICB2b2x1bWVTaXplOiBjb25maWcudm9sdW1lU2l6ZSxcbiAgaGVhbHRoQ2hlY2tUaW1lb3V0OiBjb25maWcuaGVhbHRoQ2hlY2tUaW1lb3V0LFxuICBcbiAgLy8gQWRkIHRhZ3NcbiAgdGFnczoge1xuICAgIFByb2plY3Q6ICdTYWdlTWFrZXJMTE0nLFxuICAgIE1vZGVsVHlwZTogJ0xsYW1hMy1Lb3JlYW4nLFxuICAgIENvc3RDZW50ZXI6ICdBSS1NTCcsXG4gICAgT3duZXI6ICdNTC1UZWFtJyxcbiAgICBNYW5hZ2VkQnk6ICdDREsnXG4gIH1cbn0pO1xuXG4vLyBTeW50aGVzaXplIHRoZSBDREsgYXBwXG5hcHAuc3ludGgoKTtcbiJdfQ==