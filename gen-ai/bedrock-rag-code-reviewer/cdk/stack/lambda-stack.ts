import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';

interface LambdaStackProps extends cdk.StackProps {
  s3BucketArn: string;
  knowledgeBaseId: string;
  dataSourceId: string;
  lambdaLayer: lambda.LayerVersion;
}

export class LambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    // IAM role for git-push-analyzer (needs broader permissions)
    const gitPushAnalyzerRole = new iam.Role(this, 'GitPushAnalyzerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        BedrockS3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['bedrock:*'],
              resources: ['*'],
            }),
            new iam.PolicyStatement({
              actions: ['s3:*'],
              resources: [
                props.s3BucketArn,
                `${props.s3BucketArn}/*`
              ],
            }),
          ],
        }),
      },
    });

    // IAM role for webhook processor (needs Lambda invoke permissions)
    const webhookProcessorRole = new iam.Role(this, 'WebhookProcessorRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        LambdaInvokeAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['lambda:InvokeFunction'],
              resources: ['*'], // Will be updated after creating the git-push-analyzer function
            }),
          ],
        }),
      },
    });

    // Git Push Analyzer Lambda function
    const gitPushAnalyzerFunction = new lambda.Function(this, 'GitPushAnalyzerFunction', {
      functionName: `git-push-analyzer`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/git-push-analyzer'),
      layers: [props.lambdaLayer],
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        S3_BUCKET: cdk.Stack.of(this).node.tryGetContext('s3Bucket'),
        CODEBASE_S3_PREFIX: cdk.Stack.of(this).node.tryGetContext('codebaseS3Prefix'),
        REPORT_S3_PREFIX: cdk.Stack.of(this).node.tryGetContext('reportS3Prefix'),
        MODEL_ARN: cdk.Stack.of(this).node.tryGetContext('modelArn'),
        SLACK_WEBHOOK_URL: cdk.Stack.of(this).node.tryGetContext('slackWebhookUrl'),
        GITHUB_TOKEN: cdk.Stack.of(this).node.tryGetContext('githubToken'),
        INCLUDE_FILE_PATH_IN_CHUNKS: cdk.Stack.of(this).node.tryGetContext('includeFilePathInChunks'),
        KB_ID: props.knowledgeBaseId,
        DATA_SOURCE_ID: props.dataSourceId,
      },
      role: gitPushAnalyzerRole,
    });

    // GitHub Webhook Processor Lambda function
    const webhookProcessorFunction = new lambda.Function(this, 'WebhookProcessorFunction', {
      functionName: `github-webhook-processor`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('../lambda/github-webhook-processor'),
      layers: [props.lambdaLayer],
      timeout: cdk.Duration.seconds(30), // Shorter timeout for webhook processing
      memorySize: 256, // Less memory needed for webhook processing
      environment: {
        GITHUB_WEBHOOK_SECRET: cdk.Stack.of(this).node.tryGetContext('githubWebhookSecret'),
        GIT_PUSH_ANALYZER_FUNCTION_NAME: gitPushAnalyzerFunction.functionName,
      },
      role: webhookProcessorRole,
    });

    // Update webhook processor role to allow invoking the specific git-push-analyzer function
    webhookProcessorRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['lambda:InvokeFunction'],
        resources: [gitPushAnalyzerFunction.functionArn],
      })
    );

    // Create API Gateway for the webhook processor
    const api = new apigateway.RestApi(this, 'WebhookApi', {
      restApiName: 'GitHub Webhook API',
      description: 'API Gateway for GitHub webhooks',
      deployOptions: {
        stageName: "dev",
      },
      // Disable the default endpoint
      endpointConfiguration: {
        types: [apigateway.EndpointType.REGIONAL]
      }
    });

    // Create a resource and method for the webhook
    const webhookResource = api.root.addResource('webhook');
    webhookResource.addMethod('POST', new apigateway.LambdaIntegration(webhookProcessorFunction, {
      proxy: true
    }));

    // Outputs
    new cdk.CfnOutput(this, 'GitPushAnalyzerFunctionArn', { 
      value: gitPushAnalyzerFunction.functionArn,
      description: 'ARN of the Git Push Analyzer Lambda function'
    });
    
    new cdk.CfnOutput(this, 'WebhookProcessorFunctionArn', { 
      value: webhookProcessorFunction.functionArn,
      description: 'ARN of the GitHub Webhook Processor Lambda function'
    });

    new cdk.CfnOutput(this, 'GitPushAnalyzerFunctionName', { 
      value: gitPushAnalyzerFunction.functionName,
      description: 'Name of the Git Push Analyzer Lambda function'
    });
    
    new cdk.CfnOutput(this, 'WebhookProcessorFunctionName', { 
      value: webhookProcessorFunction.functionName,
      description: 'Name of the GitHub Webhook Processor Lambda function'
    });
    
    new cdk.CfnOutput(this, 'WebhookApiUrl', { 
      value: `${api.url}webhook`,
      description: 'URL of the GitHub Webhook API endpoint'
    });
  }
}
