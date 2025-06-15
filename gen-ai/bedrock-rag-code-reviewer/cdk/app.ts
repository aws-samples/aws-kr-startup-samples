#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { LambdaStack } from '../lib/lambda-stack';
import { OpenSearchStack } from '../lib/opensearch-stack';
import { BedrockStack } from '../lib/bedrock-stack';
import { IndexCreatorStack } from '../lib/index-creator-stack';

const app = new cdk.App();

const openSearchStack = new OpenSearchStack(app, `OpenSearchStack`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});

const indexCreatorStack = new IndexCreatorStack(app, `IndexCreatorStack`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  collectionEndpoint: openSearchStack.collection.attrCollectionEndpoint,
  lambdaRole: openSearchStack.lambdaRole,
});

const bedrockStack = new BedrockStack(app, `BedrockStack`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  collectionArn: openSearchStack.collection.attrArn,
  collectionEndpoint: openSearchStack.collection.attrCollectionEndpoint,
  bucketArn: openSearchStack.s3Bucket.attrArn,
  bedrockRoleArn: openSearchStack.bedrockRole.attrArn,
  indexCreator: indexCreatorStack.indexCreator,
});

const lambdaStack = new LambdaStack(app, `LambdaStack`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  s3BucketArn: openSearchStack.s3Bucket.attrArn,
  knowledgeBaseId: bedrockStack.knowledgeBase.attrKnowledgeBaseId,
  dataSourceId: bedrockStack.dataSource.attrDataSourceId,
  lambdaLayer: indexCreatorStack.lambdaLayer,
});

