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
exports.SageMakerLLMStack = void 0;
const cdk = __importStar(require("aws-cdk-lib"));
const sagemaker = __importStar(require("aws-cdk-lib/aws-sagemaker"));
const iam = __importStar(require("aws-cdk-lib/aws-iam"));
class SageMakerLLMStack extends cdk.Stack {
    constructor(scope, id, props) {
        super(scope, id, props);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        // Default values
        const modelName = props.modelName || `llama3-kr-model-${timestamp}`;
        const endpointConfigName = `${modelName}-config`;
        this.endpointName = props.endpointName || `sm-llama3-kr-inf2-${timestamp}`;
        const instanceType = props.instanceType || 'ml.inf2.xlarge';
        const instanceCount = props.instanceCount || 1;
        const volumeSize = props.volumeSize || 64;
        const healthCheckTimeout = props.healthCheckTimeout || 600;
        // SageMaker Execution Role
        const sagemakerRole = new iam.Role(this, 'SageMakerExecutionRole', {
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
            description: 'Execution role for SageMaker LLM endpoint',
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
            ],
            inlinePolicies: {
                S3ModelAccess: new iam.PolicyDocument({
                    statements: [
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                's3:GetObject',
                                's3:ListBucket',
                            ],
                            resources: [
                                // Extract bucket name from S3 URI and create proper ARN format
                                `arn:aws:s3:::${props.modelS3Uri.replace('s3://', '').split('/')[0]}`,
                                `arn:aws:s3:::${props.modelS3Uri.replace('s3://', '').split('/')[0]}/*`,
                            ],
                        }),
                    ],
                }),
                ECRAccess: new iam.PolicyDocument({
                    statements: [
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                'ecr:BatchCheckLayerAvailability',
                                'ecr:GetDownloadUrlForLayer',
                                'ecr:BatchGetImage',
                                'ecr:GetAuthorizationToken',
                            ],
                            resources: ['*'],
                        }),
                    ],
                }),
                CloudWatchLogs: new iam.PolicyDocument({
                    statements: [
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                'logs:CreateLogGroup',
                                'logs:CreateLogStream',
                                'logs:DescribeLogGroups',
                                'logs:DescribeLogStreams',
                                'logs:PutLogEvents',
                            ],
                            resources: [`arn:aws:logs:${this.region}:${this.account}:*`],
                        }),
                    ],
                }),
            },
        });
        // Model Configuration
        const modelEnvironment = {
            HF_MODEL_ID: '/opt/ml/model',
            HF_NUM_CORES: '2',
            HF_BATCH_SIZE: '4',
            HF_SEQUENCE_LENGTH: '4096',
            HF_AUTO_CAST_TYPE: 'fp16',
            MAX_BATCH_SIZE: '4',
            MAX_INPUT_LENGTH: '2048',
            MAX_TOTAL_TOKENS: '4096',
            MESSAGES_API_ENABLED: 'true',
        };
        // Container Image URI
        const imageUri = `763104351884.dkr.ecr.${this.region}.amazonaws.com/huggingface-pytorch-tgi-inference:2.1.2-optimum0.0.28-neuronx-py310-ubuntu22.04-v1.2`;
        // SageMaker Model
        const model = new sagemaker.CfnModel(this, 'LLMModel', {
            modelName: modelName,
            executionRoleArn: sagemakerRole.roleArn,
            primaryContainer: {
                image: imageUri,
                modelDataUrl: props.modelS3Uri,
                environment: modelEnvironment,
            },
            tags: [
                {
                    key: 'Name',
                    value: modelName,
                },
                {
                    key: 'ModelType',
                    value: 'LLM',
                },
                {
                    key: 'Framework',
                    value: 'HuggingFace',
                },
            ],
        });
        // SageMaker Endpoint Configuration
        const endpointConfig = new sagemaker.CfnEndpointConfig(this, 'LLMEndpointConfig', {
            endpointConfigName: endpointConfigName,
            productionVariants: [
                {
                    modelName: model.modelName,
                    variantName: 'primary',
                    initialInstanceCount: instanceCount,
                    instanceType: instanceType,
                    initialVariantWeight: 1,
                    containerStartupHealthCheckTimeoutInSeconds: healthCheckTimeout,
                    volumeSizeInGb: volumeSize,
                },
            ],
            tags: [
                {
                    key: 'Name',
                    value: endpointConfigName,
                },
                {
                    key: 'ModelType',
                    value: 'LLM',
                },
            ],
        });
        endpointConfig.addDependency(model);
        // SageMaker Endpoint
        this.endpoint = new sagemaker.CfnEndpoint(this, 'LLMEndpoint', {
            endpointName: this.endpointName,
            endpointConfigName: endpointConfig.endpointConfigName,
            tags: [
                {
                    key: 'Name',
                    value: this.endpointName,
                },
                {
                    key: 'ModelType',
                    value: 'LLM',
                },
                {
                    key: 'Environment',
                    value: 'production',
                },
            ],
        });
        this.endpoint.addDependency(endpointConfig);
        // Outputs
        new cdk.CfnOutput(this, 'EndpointName', {
            value: this.endpointName,
            description: 'SageMaker Endpoint Name',
            exportName: `${this.stackName}-EndpointName`,
        });
        new cdk.CfnOutput(this, 'EndpointArn', {
            value: this.endpoint.ref,
            description: 'SageMaker Endpoint ARN',
            exportName: `${this.stackName}-EndpointArn`,
        });
        new cdk.CfnOutput(this, 'ModelName', {
            value: model.modelName,
            description: 'SageMaker Model Name',
            exportName: `${this.stackName}-ModelName`,
        });
        new cdk.CfnOutput(this, 'ExecutionRoleArn', {
            value: sagemakerRole.roleArn,
            description: 'SageMaker Execution Role ARN',
            exportName: `${this.stackName}-ExecutionRoleArn`,
        });
    }
}
exports.SageMakerLLMStack = SageMakerLLMStack;
// This file now contains only the stack definition
// The application entry point is in bin/app.ts
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic2FnZW1ha2VyLWxsbS1zdGFjay5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbInNhZ2VtYWtlci1sbG0tc3RhY2sudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSxpREFBbUM7QUFDbkMscUVBQXVEO0FBQ3ZELHlEQUEyQztBQWMzQyxNQUFhLGlCQUFrQixTQUFRLEdBQUcsQ0FBQyxLQUFLO0lBSTlDLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBNkI7UUFDckUsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLEVBQUUsS0FBSyxDQUFDLENBQUM7UUFFeEIsTUFBTSxTQUFTLEdBQUcsSUFBSSxJQUFJLEVBQUUsQ0FBQyxXQUFXLEVBQUUsQ0FBQyxPQUFPLENBQUMsT0FBTyxFQUFFLEdBQUcsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLEVBQUUsRUFBRSxDQUFDLENBQUM7UUFFOUUsaUJBQWlCO1FBQ2pCLE1BQU0sU0FBUyxHQUFHLEtBQUssQ0FBQyxTQUFTLElBQUksbUJBQW1CLFNBQVMsRUFBRSxDQUFDO1FBQ3BFLE1BQU0sa0JBQWtCLEdBQUcsR0FBRyxTQUFTLFNBQVMsQ0FBQztRQUNqRCxJQUFJLENBQUMsWUFBWSxHQUFHLEtBQUssQ0FBQyxZQUFZLElBQUkscUJBQXFCLFNBQVMsRUFBRSxDQUFDO1FBQzNFLE1BQU0sWUFBWSxHQUFHLEtBQUssQ0FBQyxZQUFZLElBQUksZ0JBQWdCLENBQUM7UUFDNUQsTUFBTSxhQUFhLEdBQUcsS0FBSyxDQUFDLGFBQWEsSUFBSSxDQUFDLENBQUM7UUFDL0MsTUFBTSxVQUFVLEdBQUcsS0FBSyxDQUFDLFVBQVUsSUFBSSxFQUFFLENBQUM7UUFDMUMsTUFBTSxrQkFBa0IsR0FBRyxLQUFLLENBQUMsa0JBQWtCLElBQUksR0FBRyxDQUFDO1FBRTNELDJCQUEyQjtRQUMzQixNQUFNLGFBQWEsR0FBRyxJQUFJLEdBQUcsQ0FBQyxJQUFJLENBQUMsSUFBSSxF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O0FBOUxELDhDQThMQztBQUVELG1EQUFtRDtBQUNuRCwrQ0FBK0MiLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0ICogYXMgc2FnZW1ha2VyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zYWdlbWFrZXInO1xuaW1wb3J0ICogYXMgaWFtIGZyb20gJ2F3cy1jZGstbGliL2F3cy1pYW0nO1xuaW1wb3J0ICogYXMgczMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXMzJztcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xuXG5leHBvcnQgaW50ZXJmYWNlIFNhZ2VNYWtlckxMTVN0YWNrUHJvcHMgZXh0ZW5kcyBjZGsuU3RhY2tQcm9wcyB7XG4gIHJlYWRvbmx5IG1vZGVsUzNVcmk6IHN0cmluZztcbiAgcmVhZG9ubHkgbW9kZWxOYW1lPzogc3RyaW5nO1xuICByZWFkb25seSBlbmRwb2ludE5hbWU/OiBzdHJpbmc7XG4gIHJlYWRvbmx5IGluc3RhbmNlVHlwZT86IHN0cmluZztcbiAgcmVhZG9ubHkgaW5zdGFuY2VDb3VudD86IG51bWJlcjtcbiAgcmVhZG9ubHkgdm9sdW1lU2l6ZT86IG51bWJlcjtcbiAgcmVhZG9ubHkgaGVhbHRoQ2hlY2tUaW1lb3V0PzogbnVtYmVyO1xufVxuXG5leHBvcnQgY2xhc3MgU2FnZU1ha2VyTExNU3RhY2sgZXh0ZW5kcyBjZGsuU3RhY2sge1xuICBwdWJsaWMgcmVhZG9ubHkgZW5kcG9pbnQ6IHNhZ2VtYWtlci5DZm5FbmRwb2ludDtcbiAgcHVibGljIHJlYWRvbmx5IGVuZHBvaW50TmFtZTogc3RyaW5nO1xuICBcbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM6IFNhZ2VNYWtlckxMTVN0YWNrUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQsIHByb3BzKTtcblxuICAgIGNvbnN0IHRpbWVzdGFtcCA9IG5ldyBEYXRlKCkudG9JU09TdHJpbmcoKS5yZXBsYWNlKC9bOi5dL2csICctJykuc2xpY2UoMCwgMTkpO1xuICAgIFxuICAgIC8vIERlZmF1bHQgdmFsdWVzXG4gICAgY29uc3QgbW9kZWxOYW1lID0gcHJvcHMubW9kZWxOYW1lIHx8IGBsbGFtYTMta3ItbW9kZWwtJHt0aW1lc3RhbXB9YDtcbiAgICBjb25zdCBlbmRwb2ludENvbmZpZ05hbWUgPSBgJHttb2RlbE5hbWV9LWNvbmZpZ2A7XG4gICAgdGhpcy5lbmRwb2ludE5hbWUgPSBwcm9wcy5lbmRwb2ludE5hbWUgfHwgYHNtLWxsYW1hMy1rci1pbmYyLSR7dGltZXN0YW1wfWA7XG4gICAgY29uc3QgaW5zdGFuY2VUeXBlID0gcHJvcHMuaW5zdGFuY2VUeXBlIHx8ICdtbC5pbmYyLnhsYXJnZSc7XG4gICAgY29uc3QgaW5zdGFuY2VDb3VudCA9IHByb3BzLmluc3RhbmNlQ291bnQgfHwgMTtcbiAgICBjb25zdCB2b2x1bWVTaXplID0gcHJvcHMudm9sdW1lU2l6ZSB8fCA2NDtcbiAgICBjb25zdCBoZWFsdGhDaGVja1RpbWVvdXQgPSBwcm9wcy5oZWFsdGhDaGVja1RpbWVvdXQgfHwgNjAwO1xuXG4gICAgLy8gU2FnZU1ha2VyIEV4ZWN1dGlvbiBSb2xlXG4gICAgY29uc3Qgc2FnZW1ha2VyUm9sZSA9IG5ldyBpYW0uUm9sZSh0aGlzLCAnU2FnZU1ha2VyRXhlY3V0aW9uUm9sZScsIHtcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdzYWdlbWFrZXIuYW1hem9uYXdzLmNvbScpLFxuICAgICAgZGVzY3JpcHRpb246ICdFeGVjdXRpb24gcm9sZSBmb3IgU2FnZU1ha2VyIExMTSBlbmRwb2ludCcsXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdBbWF6b25TYWdlTWFrZXJGdWxsQWNjZXNzJyksXG4gICAgICBdLFxuICAgICAgaW5saW5lUG9saWNpZXM6IHtcbiAgICAgICAgUzNNb2RlbEFjY2VzczogbmV3IGlhbS5Qb2xpY3lEb2N1bWVudCh7XG4gICAgICAgICAgc3RhdGVtZW50czogW1xuICAgICAgICAgICAgbmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuQUxMT1csXG4gICAgICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgICAgICAnczM6R2V0T2JqZWN0JyxcbiAgICAgICAgICAgICAgICAnczM6TGlzdEJ1Y2tldCcsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW1xuICAgICAgICAgICAgICAgIC8vIEV4dHJhY3QgYnVja2V0IG5hbWUgZnJvbSBTMyBVUkkgYW5kIGNyZWF0ZSBwcm9wZXIgQVJOIGZvcm1hdFxuICAgICAgICAgICAgICAgIGBhcm46YXdzOnMzOjo6JHtwcm9wcy5tb2RlbFMzVXJpLnJlcGxhY2UoJ3MzOi8vJywgJycpLnNwbGl0KCcvJylbMF19YCxcbiAgICAgICAgICAgICAgICBgYXJuOmF3czpzMzo6OiR7cHJvcHMubW9kZWxTM1VyaS5yZXBsYWNlKCdzMzovLycsICcnKS5zcGxpdCgnLycpWzBdfS8qYCxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0pLFxuICAgICAgICBFQ1JBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ2VjcjpCYXRjaENoZWNrTGF5ZXJBdmFpbGFiaWxpdHknLFxuICAgICAgICAgICAgICAgICdlY3I6R2V0RG93bmxvYWRVcmxGb3JMYXllcicsXG4gICAgICAgICAgICAgICAgJ2VjcjpCYXRjaEdldEltYWdlJyxcbiAgICAgICAgICAgICAgICAnZWNyOkdldEF1dGhvcml6YXRpb25Ub2tlbicsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICAgIHJlc291cmNlczogWycqJ10sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgQ2xvdWRXYXRjaExvZ3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ2xvZ3M6Q3JlYXRlTG9nR3JvdXAnLFxuICAgICAgICAgICAgICAgICdsb2dzOkNyZWF0ZUxvZ1N0cmVhbScsXG4gICAgICAgICAgICAgICAgJ2xvZ3M6RGVzY3JpYmVMb2dHcm91cHMnLFxuICAgICAgICAgICAgICAgICdsb2dzOkRlc2NyaWJlTG9nU3RyZWFtcycsXG4gICAgICAgICAgICAgICAgJ2xvZ3M6UHV0TG9nRXZlbnRzJyxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbYGFybjphd3M6bG9nczoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06KmBdLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgXSxcbiAgICAgICAgfSksXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gTW9kZWwgQ29uZmlndXJhdGlvblxuICAgIGNvbnN0IG1vZGVsRW52aXJvbm1lbnQgPSB7XG4gICAgICBIRl9NT0RFTF9JRDogJy9vcHQvbWwvbW9kZWwnLFxuICAgICAgSEZfTlVNX0NPUkVTOiAnMicsXG4gICAgICBIRl9CQVRDSF9TSVpFOiAnNCcsXG4gICAgICBIRl9TRVFVRU5DRV9MRU5HVEg6ICc0MDk2JyxcbiAgICAgIEhGX0FVVE9fQ0FTVF9UWVBFOiAnZnAxNicsXG4gICAgICBNQVhfQkFUQ0hfU0laRTogJzQnLFxuICAgICAgTUFYX0lOUFVUX0xFTkdUSDogJzIwNDgnLFxuICAgICAgTUFYX1RPVEFMX1RPS0VOUzogJzQwOTYnLFxuICAgICAgTUVTU0FHRVNfQVBJX0VOQUJMRUQ6ICd0cnVlJyxcbiAgICB9O1xuXG4gICAgLy8gQ29udGFpbmVyIEltYWdlIFVSSVxuICAgIGNvbnN0IGltYWdlVXJpID0gYDc2MzEwNDM1MTg4NC5ka3IuZWNyLiR7dGhpcy5yZWdpb259LmFtYXpvbmF3cy5jb20vaHVnZ2luZ2ZhY2UtcHl0b3JjaC10Z2ktaW5mZXJlbmNlOjIuMS4yLW9wdGltdW0wLjAuMjgtbmV1cm9ueC1weTMxMC11YnVudHUyMi4wNC12MS4yYDtcblxuICAgIC8vIFNhZ2VNYWtlciBNb2RlbFxuICAgIGNvbnN0IG1vZGVsID0gbmV3IHNhZ2VtYWtlci5DZm5Nb2RlbCh0aGlzLCAnTExNTW9kZWwnLCB7XG4gICAgICBtb2RlbE5hbWU6IG1vZGVsTmFtZSxcbiAgICAgIGV4ZWN1dGlvblJvbGVBcm46IHNhZ2VtYWtlclJvbGUucm9sZUFybixcbiAgICAgIHByaW1hcnlDb250YWluZXI6IHtcbiAgICAgICAgaW1hZ2U6IGltYWdlVXJpLFxuICAgICAgICBtb2RlbERhdGFVcmw6IHByb3BzLm1vZGVsUzNVcmksXG4gICAgICAgIGVudmlyb25tZW50OiBtb2RlbEVudmlyb25tZW50LFxuICAgICAgfSxcbiAgICAgIHRhZ3M6IFtcbiAgICAgICAge1xuICAgICAgICAgIGtleTogJ05hbWUnLFxuICAgICAgICAgIHZhbHVlOiBtb2RlbE5hbWUsXG4gICAgICAgIH0sXG4gICAgICAgIHtcbiAgICAgICAgICBrZXk6ICdNb2RlbFR5cGUnLFxuICAgICAgICAgIHZhbHVlOiAnTExNJyxcbiAgICAgICAgfSxcbiAgICAgICAge1xuICAgICAgICAgIGtleTogJ0ZyYW1ld29yaycsXG4gICAgICAgICAgdmFsdWU6ICdIdWdnaW5nRmFjZScsXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgLy8gU2FnZU1ha2VyIEVuZHBvaW50IENvbmZpZ3VyYXRpb25cbiAgICBjb25zdCBlbmRwb2ludENvbmZpZyA9IG5ldyBzYWdlbWFrZXIuQ2ZuRW5kcG9pbnRDb25maWcodGhpcywgJ0xMTUVuZHBvaW50Q29uZmlnJywge1xuICAgICAgZW5kcG9pbnRDb25maWdOYW1lOiBlbmRwb2ludENvbmZpZ05hbWUsXG4gICAgICBwcm9kdWN0aW9uVmFyaWFudHM6IFtcbiAgICAgICAge1xuICAgICAgICAgIG1vZGVsTmFtZTogbW9kZWwubW9kZWxOYW1lISxcbiAgICAgICAgICB2YXJpYW50TmFtZTogJ3ByaW1hcnknLFxuICAgICAgICAgIGluaXRpYWxJbnN0YW5jZUNvdW50OiBpbnN0YW5jZUNvdW50LFxuICAgICAgICAgIGluc3RhbmNlVHlwZTogaW5zdGFuY2VUeXBlLFxuICAgICAgICAgIGluaXRpYWxWYXJpYW50V2VpZ2h0OiAxLFxuICAgICAgICAgIGNvbnRhaW5lclN0YXJ0dXBIZWFsdGhDaGVja1RpbWVvdXRJblNlY29uZHM6IGhlYWx0aENoZWNrVGltZW91dCxcbiAgICAgICAgICB2b2x1bWVTaXplSW5HYjogdm9sdW1lU2l6ZSxcbiAgICAgICAgfSxcbiAgICAgIF0sXG4gICAgICB0YWdzOiBbXG4gICAgICAgIHtcbiAgICAgICAgICBrZXk6ICdOYW1lJyxcbiAgICAgICAgICB2YWx1ZTogZW5kcG9pbnRDb25maWdOYW1lLFxuICAgICAgICB9LFxuICAgICAgICB7XG4gICAgICAgICAga2V5OiAnTW9kZWxUeXBlJyxcbiAgICAgICAgICB2YWx1ZTogJ0xMTScsXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgZW5kcG9pbnRDb25maWcuYWRkRGVwZW5kZW5jeShtb2RlbCk7XG5cbiAgICAvLyBTYWdlTWFrZXIgRW5kcG9pbnRcbiAgICB0aGlzLmVuZHBvaW50ID0gbmV3IHNhZ2VtYWtlci5DZm5FbmRwb2ludCh0aGlzLCAnTExNRW5kcG9pbnQnLCB7XG4gICAgICBlbmRwb2ludE5hbWU6IHRoaXMuZW5kcG9pbnROYW1lLFxuICAgICAgZW5kcG9pbnRDb25maWdOYW1lOiBlbmRwb2ludENvbmZpZy5lbmRwb2ludENvbmZpZ05hbWUhLFxuICAgICAgdGFnczogW1xuICAgICAgICB7XG4gICAgICAgICAga2V5OiAnTmFtZScsXG4gICAgICAgICAgdmFsdWU6IHRoaXMuZW5kcG9pbnROYW1lLFxuICAgICAgICB9LFxuICAgICAgICB7XG4gICAgICAgICAga2V5OiAnTW9kZWxUeXBlJyxcbiAgICAgICAgICB2YWx1ZTogJ0xMTScsXG4gICAgICAgIH0sXG4gICAgICAgIHtcbiAgICAgICAgICBrZXk6ICdFbnZpcm9ubWVudCcsXG4gICAgICAgICAgdmFsdWU6ICdwcm9kdWN0aW9uJyxcbiAgICAgICAgfSxcbiAgICAgIF0sXG4gICAgfSk7XG5cbiAgICB0aGlzLmVuZHBvaW50LmFkZERlcGVuZGVuY3koZW5kcG9pbnRDb25maWcpO1xuXG4gICAgLy8gT3V0cHV0c1xuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdFbmRwb2ludE5hbWUnLCB7XG4gICAgICB2YWx1ZTogdGhpcy5lbmRwb2ludE5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ1NhZ2VNYWtlciBFbmRwb2ludCBOYW1lJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3RoaXMuc3RhY2tOYW1lfS1FbmRwb2ludE5hbWVgLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0VuZHBvaW50QXJuJywge1xuICAgICAgdmFsdWU6IHRoaXMuZW5kcG9pbnQucmVmLFxuICAgICAgZGVzY3JpcHRpb246ICdTYWdlTWFrZXIgRW5kcG9pbnQgQVJOJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3RoaXMuc3RhY2tOYW1lfS1FbmRwb2ludEFybmAsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnTW9kZWxOYW1lJywge1xuICAgICAgdmFsdWU6IG1vZGVsLm1vZGVsTmFtZSEsXG4gICAgICBkZXNjcmlwdGlvbjogJ1NhZ2VNYWtlciBNb2RlbCBOYW1lJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3RoaXMuc3RhY2tOYW1lfS1Nb2RlbE5hbWVgLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0V4ZWN1dGlvblJvbGVBcm4nLCB7XG4gICAgICB2YWx1ZTogc2FnZW1ha2VyUm9sZS5yb2xlQXJuLFxuICAgICAgZGVzY3JpcHRpb246ICdTYWdlTWFrZXIgRXhlY3V0aW9uIFJvbGUgQVJOJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3RoaXMuc3RhY2tOYW1lfS1FeGVjdXRpb25Sb2xlQXJuYCxcbiAgICB9KTtcbiAgfVxufVxuXG4vLyBUaGlzIGZpbGUgbm93IGNvbnRhaW5zIG9ubHkgdGhlIHN0YWNrIGRlZmluaXRpb25cbi8vIFRoZSBhcHBsaWNhdGlvbiBlbnRyeSBwb2ludCBpcyBpbiBiaW4vYXBwLnRzXG4iXX0=