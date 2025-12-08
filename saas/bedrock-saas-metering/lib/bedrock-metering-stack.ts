import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class BedrockMeteringStack extends cdk.Stack {
    public readonly meteringLogGroup: logs.LogGroup;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Cognito User Pool - 테넌트 인증
        const userPool = new cognito.UserPool(this, 'SaaSUserPool', {
            userPoolName: 'bedrock-saas-users',
            selfSignUpEnabled: true,
            signInAliases: {
                email: true,
                username: true,
            },
            standardAttributes: {
                email: {
                    required: true,
                    mutable: true,
                },
            },
            // 테넌트 ID를 커스텀 속성으로 추가
            customAttributes: {
                tenant_id: new cognito.StringAttribute({
                    minLen: 1,
                    maxLen: 50,
                    mutable: false,
                }),
            },
            passwordPolicy: {
                minLength: 8,
                requireLowercase: true,
                requireUppercase: true,
                requireDigits: true,
                requireSymbols: false,
            },
            accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        // Cognito User Pool Client
        const userPoolClient = new cognito.UserPoolClient(this, 'SaaSUserPoolClient', {
            userPool,
            generateSecret: false,
            authFlows: {
                userPassword: true,
                userSrp: true,
            },
            oAuth: {
                flows: {
                    authorizationCodeGrant: true,
                },
                scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
            },
        });

        // CloudWatch Log Group for metering
        this.meteringLogGroup = new logs.LogGroup(this, 'BedrockMeteringLogGroup', {
            logGroupName: '/aws/bedrock/metering',
            retention: logs.RetentionDays.ONE_MONTH,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        // Lambda function for Bedrock API calls and metering
        const bedrockLambda = new lambda.Function(this, 'BedrockMeteringFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'index.handler',
            code: lambda.Code.fromInline(`
import json
import boto3
import logging
import time
from datetime import datetime
import os

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
bedrock_runtime = boto3.client('bedrock-runtime')
cloudwatch_logs = boto3.client('logs')

def call_bedrock_model(prompt):
    """Bedrock 모델 호출 - 고정된 모델 사용"""
    try:
        # 고정된 모델 사용 (샘플용)
        model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        # 토큰 사용량 정보 추출 (내부 빌링용)
        usage = response_body.get('usage', {})
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        
        return {
            'response': response_body.get('content', [{}])[0].get('text', ''),
            'model_id': model_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens
        }
    except Exception as e:
        logger.error(f"Bedrock 호출 실패: {str(e)}")
        raise

def log_token_usage(tenant_id, user_id, model_id, input_tokens, output_tokens, total_tokens):
    """CloudWatch Logs에 토큰 사용량 기록"""
    try:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'user_id': user_id,
            'model_id': model_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'event_type': 'bedrock_token_usage'
        }
        
        log_stream_name = f"tenant-{tenant_id}"
        
        # 로그 스트림이 존재하지 않으면 생성
        try:
            cloudwatch_logs.create_log_stream(
                logGroupName=os.environ['LOG_GROUP_NAME'],
                logStreamName=log_stream_name
            )
        except cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
            # 이미 존재하는 경우 무시
            pass
        
        cloudwatch_logs.put_log_events(
            logGroupName=os.environ['LOG_GROUP_NAME'],
            logStreamName=log_stream_name,
            logEvents=[
                {
                    'timestamp': int(time.time() * 1000),
                    'message': json.dumps(log_entry, ensure_ascii=False)
                }
            ]
        )
        
        logger.info(f"토큰 사용량 기록됨: {log_entry}")
    except Exception as e:
        logger.error(f"로그 기록 실패: {str(e)}")

def handler(event, context):
    try:
        # API Gateway Cognito Authorizer에서 사용자 정보 추출 (ID Token 사용)
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        
        # 사용자 정보 추출 (ID Token에서 직접 가져옴)
        user_id = claims.get('sub')
        username = claims.get('cognito:username')
        tenant_id = claims.get('custom:tenant_id')
        
        if not user_id or not tenant_id:
            return {
                'statusCode': 401,
                'headers': {'Content-Type': 'application/json; charset=utf-8'},
                'body': json.dumps({'error': 'Missing user or tenant information'}, ensure_ascii=False)
            }
        
        user_info = {
            'tenant_id': tenant_id,
            'user_id': user_id,
            'username': username
        }
        
        # 요청 본문에서 프롬프트 추출
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt')
        
        if not prompt:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json; charset=utf-8'},
                'body': json.dumps({'error': 'Missing prompt in request body'}, ensure_ascii=False)
            }
        
        # Bedrock 모델 호출
        bedrock_response = call_bedrock_model(prompt)
        
        # 토큰 사용량 로깅
        log_token_usage(
            tenant_id=user_info['tenant_id'],
            user_id=user_info['user_id'],
            model_id=bedrock_response['model_id'],  # 실제 사용된 모델 ID
            input_tokens=bedrock_response['input_tokens'],
            output_tokens=bedrock_response['output_tokens'],
            total_tokens=bedrock_response['total_tokens']
        )
        
        # 응답 반환 (테넌트에게는 응답 텍스트만 제공)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'response': bedrock_response['response']
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8'
            },
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }
`),
            environment: {
                COGNITO_REGION: this.region,
                USER_POOL_ID: userPool.userPoolId,
                USER_POOL_CLIENT_ID: userPoolClient.userPoolClientId,
                LOG_GROUP_NAME: this.meteringLogGroup.logGroupName,
            },
            timeout: cdk.Duration.seconds(30),
        });

        // Lambda에 필요한 권한 부여
        bedrockLambda.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
            ],
            resources: ['*'],
        }));

        bedrockLambda.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources: [this.meteringLogGroup.logGroupArn],
        }));

        // API Gateway 설정
        const api = new apigateway.RestApi(this, 'BedrockSaaSApi', {
            restApiName: 'Bedrock SaaS API',
            description: 'Multi-tenant SaaS API with Bedrock integration',
            defaultCorsPreflightOptions: {
                allowOrigins: apigateway.Cors.ALL_ORIGINS,
                allowMethods: apigateway.Cors.ALL_METHODS,
                allowHeaders: ['Content-Type', 'Authorization'],
            },
        });

        // Cognito Authorizer - ID Token 사용
        const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
            cognitoUserPools: [userPool],
            identitySource: 'method.request.header.Authorization',
            resultsCacheTtl: cdk.Duration.minutes(0), // 캐시 비활성화로 실시간 검증
        });

        // API 엔드포인트 설정
        const bedrockResource = api.root.addResource('bedrock');
        const chatResource = bedrockResource.addResource('chat');

        chatResource.addMethod('POST', new apigateway.LambdaIntegration(bedrockLambda), {
            authorizer: cognitoAuthorizer,
            authorizationType: apigateway.AuthorizationType.COGNITO,
        });

        // 출력값들
        new cdk.CfnOutput(this, 'UserPoolId', {
            value: userPool.userPoolId,
            description: 'Cognito User Pool ID',
        });

        new cdk.CfnOutput(this, 'UserPoolClientId', {
            value: userPoolClient.userPoolClientId,
            description: 'Cognito User Pool Client ID',
        });

        new cdk.CfnOutput(this, 'ApiGatewayUrl', {
            value: api.url,
            description: 'API Gateway URL',
        });

        new cdk.CfnOutput(this, 'MeteringLogGroupName', {
            value: this.meteringLogGroup.logGroupName,
            description: 'CloudWatch Log Group for metering data',
        });
    }
}