import * as cdk from 'aws-cdk-lib';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface SageMakerLLMStackProps extends cdk.StackProps {
  readonly modelS3Uri: string;
  readonly modelName?: string;
  readonly endpointName?: string;
  readonly instanceType?: string;
  readonly instanceCount?: number;
  readonly volumeSize?: number;
  readonly healthCheckTimeout?: number;
}

export class SageMakerLLMStack extends cdk.Stack {
  public readonly endpoint: sagemaker.CfnEndpoint;
  public readonly endpointName: string;
  
  constructor(scope: Construct, id: string, props: SageMakerLLMStackProps) {
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
          modelName: model.modelName!,
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
      endpointConfigName: endpointConfig.endpointConfigName!,
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
      value: model.modelName!,
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

// This file now contains only the stack definition
// The application entry point is in bin/app.ts
