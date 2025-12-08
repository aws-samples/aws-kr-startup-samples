import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as athena from 'aws-cdk-lib/aws-athena';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface MeteringAnalyticsStackProps extends cdk.StackProps {
  logGroup: logs.LogGroup;
}

export class MeteringAnalyticsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MeteringAnalyticsStackProps) {
    super(scope, id, props);

    // S3 버킷 - Athena 쿼리 결과 및 로그 데이터 저장
    const analyticsBucket = new s3.Bucket(this, 'MeteringAnalyticsBucket', {
      bucketName: `bedrock-metering-analytics-${this.account}-${this.region}`,
      versioned: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [{
        id: 'DeleteOldData',
        expiration: cdk.Duration.days(90),
      }],
    });

    // Glue Database
    const glueDatabase = new glue.CfnDatabase(this, 'MeteringDatabase', {
      catalogId: this.account,
      databaseInput: {
        name: 'bedrock_metering_db',
        description: 'Database for Bedrock token usage metering analytics',
      },
    });

    // Glue Table - CloudWatch Logs 데이터 구조 정의
    const meteringTable = new glue.CfnTable(this, 'MeteringTable', {
      catalogId: this.account,
      databaseName: glueDatabase.ref,
      tableInput: {
        name: 'token_usage_logs',
        description: 'Bedrock token usage logs from CloudWatch',
        tableType: 'EXTERNAL_TABLE',
        parameters: {
          'projection.enabled': 'true',
          'projection.year.type': 'integer',
          'projection.year.range': '2025,2030',
          'projection.month.type': 'integer',
          'projection.month.range': '1,12',
          'projection.day.type': 'integer',
          'projection.day.range': '1,31',
          'storage.location.template': `s3://${analyticsBucket.bucketName}/logs/year=\${year}/month=\${month}/day=\${day}/`,
        },
        storageDescriptor: {
          columns: [
            {
              name: 'timestamp',
              type: 'string',
            },
            {
              name: 'tenant_id',
              type: 'string',
            },
            {
              name: 'user_id',
              type: 'string',
            },
            {
              name: 'model_id',
              type: 'string',
            },
            {
              name: 'input_tokens',
              type: 'bigint',
            },
            {
              name: 'output_tokens',
              type: 'bigint',
            },
            {
              name: 'total_tokens',
              type: 'bigint',
            },
            {
              name: 'event_type',
              type: 'string',
            },
          ],
          location: `s3://${analyticsBucket.bucketName}/logs/`,
          inputFormat: 'org.apache.hadoop.mapred.TextInputFormat',
          outputFormat: 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
          serdeInfo: {
            serializationLibrary: 'org.openx.data.jsonserde.JsonSerDe',
          },
        },
        partitionKeys: [
          {
            name: 'year',
            type: 'string',
          },
          {
            name: 'month',
            type: 'string',
          },
          {
            name: 'day',
            type: 'string',
          },
        ],
      },
    });

    // Athena Workgroup
    const athenaWorkgroup = new athena.CfnWorkGroup(this, 'MeteringWorkgroup', {
      name: 'bedrock-metering-workgroup',
      description: 'Workgroup for Bedrock metering analytics',
      workGroupConfiguration: {
        resultConfiguration: {
          outputLocation: `s3://${analyticsBucket.bucketName}/athena-results/`,
        },
        enforceWorkGroupConfiguration: true,
      },
    });

    // Lambda function for log processing and S3 export
    const logProcessorLambda = new lambda.Function(this, 'LogProcessorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3
import gzip
import base64
from datetime import datetime
import os

s3_client = boto3.client('s3')
logs_client = boto3.client('logs')

def handler(event, context):
    """CloudWatch Logs를 S3로 내보내고 파티션 구조로 저장"""
    
    bucket_name = os.environ['ANALYTICS_BUCKET']
    log_group_name = os.environ['LOG_GROUP_NAME']
    
    try:
        # 현재 날짜 기준으로 로그 내보내기
        now = datetime.utcnow()
        year = now.year
        month = now.month
        day = now.day
        
        # 오늘 날짜의 로그를 처리 (테스트용 - 실제 운영시에는 어제 데이터 처리)
        # 수동 실행시에는 오늘 데이터를, 자동 스케줄시에는 어제 데이터를 처리
        from datetime import timedelta
        
        # 이벤트에서 날짜 지정이 있으면 해당 날짜, 없으면 오늘 날짜 사용
        target_date = now
        if 'use_yesterday' in event and event['use_yesterday']:
            target_date = now - timedelta(days=1)
        
        start_time = int(target_date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        end_time = int(now.timestamp() * 1000)  # 현재 시간까지
        
        # CloudWatch Logs Insights 쿼리 실행
        query = f'''
        fields @timestamp, @message
        | filter @message like /bedrock_token_usage/
        | sort @timestamp desc
        '''
        
        response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )
        
        query_id = response['queryId']
        
        # 쿼리 완료 대기
        import time
        while True:
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            elif result['status'] == 'Failed':
                raise Exception(f"Query failed: {result}")
            time.sleep(1)
        
        # 결과를 S3에 저장
        if result['results']:
            s3_key = f"logs/year={target_date.year}/month={target_date.month:02d}/day={target_date.day:02d}/bedrock-usage-{target_date.strftime('%Y%m%d')}.json"
            
            # JSON Lines 형식으로 변환
            json_lines = []
            for row in result['results']:
                message_field = next((field for field in row if field['field'] == '@message'), None)
                if message_field:
                    try:
                        log_data = json.loads(message_field['value'])
                        json_lines.append(json.dumps(log_data))
                    except json.JSONDecodeError:
                        continue
            
            if json_lines:
                content = '\\n'.join(json_lines)
                
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType='application/json'
                )
                
                print(f"Successfully exported {len(json_lines)} log entries to s3://{bucket_name}/{s3_key}")
            else:
                print("No valid log entries found to export")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Log processing completed successfully',
                'records_processed': len(result.get('results', []))
            })
        }
        
    except Exception as e:
        print(f"Error processing logs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
`),
      environment: {
        ANALYTICS_BUCKET: analyticsBucket.bucketName,
        LOG_GROUP_NAME: props.logGroup.logGroupName,
      },
      timeout: cdk.Duration.minutes(5),
    });

    // Lambda에 필요한 권한 부여
    analyticsBucket.grantReadWrite(logProcessorLambda);

    logProcessorLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:StartQuery',
        'logs:GetQueryResults',
        'logs:DescribeLogGroups',
        'logs:DescribeLogStreams',
      ],
      resources: [props.logGroup.logGroupArn],
    }));

    // EventBridge 규칙 - 매일 자정에 로그 처리 실행
    const dailyLogProcessing = new events.Rule(this, 'DailyLogProcessingRule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '1', // UTC 1시 (한국시간 10시)
      }),
    });

    // 자동 스케줄 실행시에는 어제 데이터 처리하도록 설정
    dailyLogProcessing.addTarget(new targets.LambdaFunction(logProcessorLambda, {
      event: events.RuleTargetInput.fromObject({
        use_yesterday: true
      })
    }));

    // Athena 쿼리 예제들을 저장할 Lambda
    const queryExamplesLambda = new lambda.Function(this, 'QueryExamplesFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import json
import boto3

athena_client = boto3.client('athena')

# 미리 정의된 쿼리 예제들
QUERY_EXAMPLES = {
    "daily_usage_by_tenant": '''
    SELECT 
        tenant_id,
        DATE(from_iso8601_timestamp(timestamp)) as usage_date,
        model_id,
        SUM(input_tokens) as total_input_tokens,
        SUM(output_tokens) as total_output_tokens,
        SUM(total_tokens) as total_tokens,
        COUNT(*) as request_count
    FROM bedrock_metering_db.token_usage_logs
    WHERE year = '{year}' AND month = '{month}' AND day = '{day}'
    GROUP BY tenant_id, DATE(from_iso8601_timestamp(timestamp)), model_id
    ORDER BY usage_date DESC, total_tokens DESC
    ''',
    
    "monthly_tenant_summary": '''
    SELECT 
        tenant_id,
        model_id,
        SUM(input_tokens) as monthly_input_tokens,
        SUM(output_tokens) as monthly_output_tokens,
        SUM(total_tokens) as monthly_total_tokens,
        COUNT(*) as monthly_requests,
        AVG(total_tokens) as avg_tokens_per_request
    FROM bedrock_metering_db.token_usage_logs
    WHERE year = '{year}' AND month = '{month}'
    GROUP BY tenant_id, model_id
    ORDER BY monthly_total_tokens DESC
    ''',
    
    "top_users_by_usage": '''
    SELECT 
        tenant_id,
        user_id,
        model_id,
        SUM(total_tokens) as total_usage,
        COUNT(*) as request_count,
        AVG(total_tokens) as avg_tokens_per_request,
        MIN(from_iso8601_timestamp(timestamp)) as first_usage,
        MAX(from_iso8601_timestamp(timestamp)) as last_usage
    FROM bedrock_metering_db.token_usage_logs
    WHERE year = '{year}' AND month = '{month}'
    GROUP BY tenant_id, user_id, model_id
    HAVING SUM(total_tokens) > 1000
    ORDER BY total_usage DESC
    LIMIT 50
    ''',
    
    "cost_estimation": '''
    SELECT 
        tenant_id,
        model_id,
        SUM(input_tokens) as total_input_tokens,
        SUM(output_tokens) as total_output_tokens,
        SUM(total_tokens) as total_tokens,
        -- Claude 3 Haiku 가격 기준 (입력: $0.25/1M 토큰, 출력: $1.25/1M 토큰)
        ROUND(
            (SUM(input_tokens) * 0.25 / 1000000.0) + 
            (SUM(output_tokens) * 1.25 / 1000000.0), 4
        ) as estimated_cost_usd
    FROM bedrock_metering_db.token_usage_logs
    WHERE year = '{year}' AND month = '{month}'
    GROUP BY tenant_id, model_id
    ORDER BY estimated_cost_usd DESC
    '''
}

def handler(event, context):
    """Athena 쿼리 실행 및 결과 반환"""
    
    try:
        query_name = event.get('query_name')
        parameters = event.get('parameters', {})
        
        if query_name not in QUERY_EXAMPLES:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown query: {query_name}',
                    'available_queries': list(QUERY_EXAMPLES.keys())
                })
            }
        
        # 쿼리 템플릿에 파라미터 적용
        query = QUERY_EXAMPLES[query_name].format(**parameters)
        
        # Athena 쿼리 실행
        response = athena_client.start_query_execution(
            QueryString=query,
            WorkGroup=os.environ['WORKGROUP_NAME']
        )
        
        query_execution_id = response['QueryExecutionId']
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'query_execution_id': query_execution_id,
                'query': query,
                'message': 'Query started successfully'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
`),
      environment: {
        WORKGROUP_NAME: athenaWorkgroup.ref,
      },
    });

    // Athena 쿼리 실행 권한
    queryExamplesLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'athena:StartQueryExecution',
        'athena:GetQueryExecution',
        'athena:GetQueryResults',
        'athena:StopQueryExecution',
      ],
      resources: ['*'],
    }));

    queryExamplesLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'glue:GetDatabase',
        'glue:GetTable',
        'glue:GetPartitions',
      ],
      resources: ['*'],
    }));

    analyticsBucket.grantReadWrite(queryExamplesLambda);

    // 출력값들
    new cdk.CfnOutput(this, 'AnalyticsBucketName', {
      value: analyticsBucket.bucketName,
      description: 'S3 bucket for analytics data',
    });

    new cdk.CfnOutput(this, 'GlueDatabaseName', {
      value: glueDatabase.ref,
      description: 'Glue database name',
    });

    new cdk.CfnOutput(this, 'AthenaWorkgroupName', {
      value: athenaWorkgroup.ref,
      description: 'Athena workgroup name',
    });

    new cdk.CfnOutput(this, 'QueryExamplesLambdaArn', {
      value: queryExamplesLambda.functionArn,
      description: 'Lambda function for running example queries',
    });

    // 샘플 쿼리 예제 출력
    new cdk.CfnOutput(this, 'SampleQueries', {
      value: JSON.stringify({
        daily_usage: 'Daily usage by tenant',
        monthly_summary: 'Monthly tenant summary',
        top_users: 'Top users by usage',
        cost_estimation: 'Cost estimation by tenant'
      }),
      description: 'Available sample queries',
    });
  }
}