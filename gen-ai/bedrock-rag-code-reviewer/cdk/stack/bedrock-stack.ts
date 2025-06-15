import * as cdk from 'aws-cdk-lib';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import { Construct } from 'constructs';

interface BedrockStackProps extends cdk.StackProps {
  collectionArn: string;
  collectionEndpoint: string;
  bucketArn: string;
  bedrockRoleArn: string;
  indexCreator: cdk.CustomResource;
}

export class BedrockStack extends cdk.Stack {
  public readonly knowledgeBase: bedrock.CfnKnowledgeBase;
  public readonly dataSource: bedrock.CfnDataSource;

  constructor(scope: Construct, id: string, props: BedrockStackProps) {
    super(scope, id, props);

    const collectionName = cdk.Stack.of(this).node.tryGetContext('collectionName');
    const knowledgeBaseName = cdk.Stack.of(this).node.tryGetContext('knowledgeBaseName');
    const codebaseS3Prefix = cdk.Stack.of(this).node.tryGetContext('codebaseS3Prefix');
    const embeddingModelArn = cdk.Stack.of(this).node.tryGetContext('embeddingModelArn');

    // Knowledge Base
    this.knowledgeBase = new bedrock.CfnKnowledgeBase(this, 'KnowledgeBase', {
      name: knowledgeBaseName,
      description: 'Answers on basis of data in knowledge base',
      roleArn: props.bedrockRoleArn,
      knowledgeBaseConfiguration: {
        type: 'VECTOR',
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: embeddingModelArn
        }
      },
      storageConfiguration: {
        type: 'OPENSEARCH_SERVERLESS',
        opensearchServerlessConfiguration: {
          collectionArn: props.collectionArn,
          vectorIndexName: collectionName,
          fieldMapping: {
            vectorField: 'vector_field',
            textField: 'text',
            metadataField: 'filepath'
          }
        }
      }
    });

    // Data Source
    this.dataSource = new bedrock.CfnDataSource(this, 'DataSource', {
      knowledgeBaseId: this.knowledgeBase.ref,
      name: collectionName,
      dataSourceConfiguration: {
        type: 'S3',
        s3Configuration: {
          bucketArn: props.bucketArn,
          inclusionPrefixes: [
            codebaseS3Prefix
          ]
        }
      },
      vectorIngestionConfiguration: {
        chunkingConfiguration: {
          chunkingStrategy: 'NONE'
        }
      }
    });

    this.knowledgeBase.addDependency(props.indexCreator.node.defaultChild as cdk.CfnResource);

    // Outputs
    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: this.knowledgeBase.ref
    });

    new cdk.CfnOutput(this, 'DataSourceId', {
      value: this.dataSource.ref
    });
  }
}