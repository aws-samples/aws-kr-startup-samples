import * as cdk from 'aws-cdk-lib';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
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
export declare class SageMakerLLMStack extends cdk.Stack {
    readonly endpoint: sagemaker.CfnEndpoint;
    readonly endpointName: string;
    constructor(scope: Construct, id: string, props: SageMakerLLMStackProps);
}
