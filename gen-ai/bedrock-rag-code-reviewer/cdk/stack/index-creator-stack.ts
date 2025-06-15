import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Duration } from 'aws-cdk-lib';
import { Role } from 'aws-cdk-lib/aws-iam';
import { Provider } from 'aws-cdk-lib/custom-resources';

interface IndexCreatorStackProps extends cdk.StackProps {
  collectionEndpoint: string;
  lambdaRole: Role;
}

export class IndexCreatorStack extends cdk.Stack {
  public readonly indexCreator: cdk.CustomResource;
  public readonly lambdaLayer: lambda.LayerVersion;

  constructor(scope: Construct, id: string, props: IndexCreatorStackProps) {
    super(scope, id, props);

    const collectionName = cdk.Stack.of(this).node.tryGetContext('collectionName');

    // Create a Lambda layer with dependencies
    this.lambdaLayer = new lambda.LayerVersion(this, 'LambdaLayer', {
      layerVersionName: 'lambda-dependencies',
      code: lambda.Code.fromAsset('../lambda/layer.zip'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
    });

    // Create a Lambda function to create the index
    const indexCreatorFunction = new lambda.Function(this, 'IndexCreator', {
      functionName: 'opensearch-index-creator',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_function.handler',
      role: props.lambdaRole,
      code: lambda.Code.fromAsset('../lambda/opensearch-index-creator'),
      timeout: Duration.minutes(5),
      layers: [this.lambdaLayer],
      environment: {
        HOST: cdk.Fn.select(2, cdk.Fn.split('/', props.collectionEndpoint)),
      }
    });

    // Create custom resource to create the index
    this.indexCreator = new cdk.CustomResource(this, 'OpenSearchIndex', {
      serviceToken: new Provider(this, 'IndexCreatorProvider', {
        onEventHandler: indexCreatorFunction,
      }).serviceToken,
      properties: {
        CollectionEndpoint: props.collectionEndpoint,
        IndexName: collectionName
      }
    });

    // Outputs
    new cdk.CfnOutput(this, 'IndexName', {
      value: collectionName
    });
  }
}