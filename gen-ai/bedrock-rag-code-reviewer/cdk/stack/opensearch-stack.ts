import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';
import { Construct } from 'constructs';

export class OpenSearchStack extends cdk.Stack {
  public readonly collection: opensearchserverless.CfnCollection;
  public readonly s3Bucket: s3.CfnBucket;
  public readonly bedrockRole: iam.CfnRole;
  public readonly lambdaRole: iam.Role;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const collectionName = cdk.Stack.of(this).node.tryGetContext('collectionName');
    const s3BucketName = cdk.Stack.of(this).node.tryGetContext('s3Bucket');
    const iamUserArn = cdk.Stack.of(this).node.tryGetContext('iaUserArn');

    // Encryption Policy
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'EncryptionPolicy', {
      name: `${collectionName}-security-policy`,
      type: 'encryption',
      description: 'Encryption policy for OpenSearch Serverless collection',
      policy: JSON.stringify({
        Rules: [{
          ResourceType: 'collection',
          Resource: [`collection/${collectionName}`]
        }],
        AWSOwnedKey: true
      })
    });

    // Network Policy
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'NetworkPolicy', {
      name: `${collectionName}-network-policy`,
      type: 'network',
      description: 'Network policy for OpenSearch Serverless collection',
      policy: JSON.stringify([{
        Rules: [
          { ResourceType: 'collection', Resource: [`collection/${collectionName}`] },
          { ResourceType: 'dashboard', Resource: [`collection/${collectionName}`] }
        ],
        AllowFromPublic: true
      }])
    });

    // Bedrock Role
    this.bedrockRole = new iam.CfnRole(this, 'BedrockRole', {
        roleName: `AmazonBedrockExecutionRoleForKB-${collectionName}`,
        assumeRolePolicyDocument: {
          Statement: [{
            Effect: 'Allow',
            Principal: {
              Service: 'bedrock.amazonaws.com'
            },
            Action: 'sts:AssumeRole',
            Condition: {
              StringEquals: {
                'aws:SourceAccount': this.account
              },
              ArnLike: {
                'aws:SourceArn': `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/*`
              }
            }
          }]
        },
        policies: [
            {
                policyName: 'OpensearchServerlessAccessPolicy',
                policyDocument: {
                  Version: '2012-10-17',
                  Statement: [
                    {
                      Effect: 'Allow',
                      Action: [
                        'aoss:APIAccessAll',
                        'aoss:DashboardsAccessAll',
                      ],
                      Resource: `arn:aws:aoss:${this.region}:${this.account}:collection/*`
                    }
                  ]
                }
              },
              {
                policyName: 'BedrockAccessPolicy',
                policyDocument: {
                  Version: '2012-10-17',
                  Statement: [
                    {
                      Effect: 'Allow',
                      Action: [
                        'bedrock:*',
                      ],
                      Resource: '*'
                    }
                  ]
                }
              },
              {
                policyName: 'S3AccessForKnowledgeBase',
                policyDocument: {
                  Version: '2012-10-17',
                  Statement: [
                    {
                      Effect: 'Allow',
                      Action: [
                        's3:*',
                      ],
                      Resource: [ 
                        `arn:aws:s3:::${s3BucketName}`,
                        `arn:aws:s3:::${s3BucketName}/*`
                      ]
                    }
                  ]
                }
              },
          ]
      });

    // Lambda Role

    this.lambdaRole = new iam.Role(this, 'IndexCreationLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        BedrockS3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              resources: ['*'],
              actions: [
                'aoss:APIAccessAll',
                'aoss:DashboardsAccessAll'
              ]
            })
          ],
        }),
      },
    });

    const dataAccessPolicy = new opensearchserverless.CfnAccessPolicy(this, 'DataAccessPolicy', {
        name: `${collectionName}-access-policy`,
        type: 'data',
        description: 'Data access policy for OpenSearch Serverless collection',
        policy: JSON.stringify([
          {
            Description: "Provided Access for Bedrock and IAM user",
            Rules: [
              {
                ResourceType: 'index',
                Resource: ['index/*/*'],
                Permission: [
                  'aoss:ReadDocument',
                  'aoss:WriteDocument',
                  'aoss:CreateIndex',
                  'aoss:DeleteIndex',
                  'aoss:UpdateIndex',
                  'aoss:DescribeIndex'
                ]
              },
              {
                ResourceType: 'collection',
                Resource: [`collection/${collectionName}`],
                Permission: [
                  'aoss:CreateCollectionItems',
                  'aoss:DeleteCollectionItems',
                  'aoss:UpdateCollectionItems',
                  'aoss:DescribeCollectionItems'
                ]
              }
            ],
            Principal: [
              iamUserArn,
              this.bedrockRole.attrArn,
              `arn:aws:iam::${this.account}:role/aws-service-role/bedrock.amazonaws.com/AWSServiceRoleForAmazonBedrock`,
              this.lambdaRole.roleArn
            ]
          }
        ])
      });

    // S3 Bucket
    this.s3Bucket = new s3.CfnBucket(this, 'S3Bucket', {
      bucketName: s3BucketName,
      accessControl: 'Private' ,
      publicAccessBlockConfiguration: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true
      },
      versioningConfiguration: { status: "Enabled" },
      bucketEncryption: {
        serverSideEncryptionConfiguration: [{
          serverSideEncryptionByDefault: {
            sseAlgorithm: 'AES256'
          }
        }]
      }
    });

    // S3 bucket to allow deletion
    this.s3Bucket.cfnOptions.deletionPolicy = cdk.CfnDeletionPolicy.DELETE;

    // Collection
    this.collection = new opensearchserverless.CfnCollection(this, 'Collection', {
      name: collectionName,
      type: 'VECTORSEARCH',
      description: 'Collection for vector search data'
    });

    this.collection.addDependency(encryptionPolicy);
    this.collection.addDependency(networkPolicy);

    // Outputs
    new cdk.CfnOutput(this, 'CollectionArn', {
      value: this.collection.attrArn,
      exportName: 'OpenSearchCollectionArn'
    });

    new cdk.CfnOutput(this, 'BucketArn', {
      value: this.s3Bucket.attrArn,
      exportName: 'OpenSearchBucketArn'
    });

    new cdk.CfnOutput(this, 'BedrockRoleArn', {
      value: this.bedrockRole.attrArn,
      exportName: 'BedrockRoleArn'
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: this.s3Bucket.ref,
      exportName: 'BucketName'
    });
  }
}