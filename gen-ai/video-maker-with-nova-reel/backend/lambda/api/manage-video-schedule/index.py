import boto3
import json
import os
import logging
from datetime import datetime, timezone # timezone 추가
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 환경 변수 (CDK에서 주입)
TARGET_LAMBDA_ARN = os.environ['TARGET_LAMBDA_ARN']
SCHEDULER_ROLE_ARN = os.environ['SCHEDULER_ROLE_ARN']
SCHEDULE_NAME = os.environ['SCHEDULE_NAME'] # 고정 스케줄 이름
SCHEDULE_GROUP_NAME = 'default' # 기본 그룹 사용

scheduler_client = boto3.client('scheduler')

# --- API Gateway 응답 생성 헬퍼 --- 
def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'body': json.dumps(body),
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,GET,DELETE,OPTIONS' # GET, DELETE 추가
        }
    }

# --- 날짜/시간 형식 검증 (ISO 8601 UTC 입력 가정) --- 
def validate_iso_utc_datetime(dt_string):
    try:
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt_string # 유효하면 원본 반환
    except (ValueError, TypeError):
        return None

# --- Lambda 핸들러 --- 
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    http_method = event.get('httpMethod', '')

    # --- OPTIONS (CORS Preflight) --- 
    if http_method == 'OPTIONS':
        return create_response(200, {})

    # --- GET /apis/videos/schedule (현재 스케줄 상태 조회) --- 
    elif http_method == 'GET':
        try:
            logger.info(f"Getting schedule status for: {SCHEDULE_NAME}")
            response = scheduler_client.get_schedule(
                Name=SCHEDULE_NAME,
                GroupName=SCHEDULE_GROUP_NAME
            )
            logger.info(f"Found schedule: {response}")
            # 필요한 정보만 가공하여 반환 (예: 상태, 시작/종료 시간)
            # boto3는 datetime 객체로 반환하므로 ISO 문자열로 변환
            start_date_str = response.get('StartDate').isoformat().split('.')[0] + 'Z' if response.get('StartDate') else None
            end_date_str = response.get('EndDate').isoformat().split('.')[0] + 'Z' if response.get('EndDate') else None
            # Input 페이로드에서 프롬프트 추출 시도
            prompt = None
            try:
                target_input = json.loads(response.get('Target', {}).get('Input', '{}'))
                prompt = target_input.get('prompt')
            except json.JSONDecodeError:
                logger.warning("Could not parse prompt from schedule input.")
                
            schedule_info = {
                'exists': True,
                'scheduleName': response.get('Name'),
                'state': response.get('State'),
                'startTime': start_date_str,
                'endTime': end_date_str,
                'prompt': prompt # 저장된 프롬프트 반환
            }
            return create_response(200, schedule_info)

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Schedule '{SCHEDULE_NAME}' not found.")
                return create_response(200, {'exists': False})
            else:
                logger.error(f"Error getting schedule '{SCHEDULE_NAME}': {e}")
                return create_response(500, {'error': f"Failed to get schedule status: {e.response['Error']['Message']}"})
        except Exception as e:
            logger.error(f"Unexpected error getting schedule: {e}")
            return create_response(500, {'error': 'Internal server error.'})

    # --- POST /apis/videos/schedule (스케줄 생성 또는 업데이트) --- 
    elif http_method == 'POST':
        try:
            body = event.get('body')
            if not body: return create_response(400, {'error': 'Bad Request: Missing body.'})
            parsed_body = json.loads(body)

            prompt = parsed_body.get('prompt')
            start_time_str = parsed_body.get('startTime')
            end_time_str = parsed_body.get('endTime')

            if not all([prompt, start_time_str, end_time_str]):
                return create_response(400, {'error': 'Bad Request: Missing prompt, startTime, or endTime.'})

            start_date = validate_iso_utc_datetime(start_time_str)
            end_date = validate_iso_utc_datetime(end_time_str)

            if not start_date or not end_date:
                return create_response(400, {'error': 'Bad Request: Invalid startTime or endTime format (Use ISO 8601 UTC: YYYY-MM-DDTHH:MM:SSZ).'}) 
            
            # 시작 시간이 종료 시간보다 이후인지 확인
            if datetime.fromisoformat(start_date.replace('Z', '+00:00')) >= datetime.fromisoformat(end_date.replace('Z', '+00:00')):
                return create_response(400, {'error': 'Bad Request: End time must be after start time.'})

            # 대상 Lambda에 전달할 입력
            target_input = json.dumps({
                "source": "user-schedule", # 호출 소스 명시
                "prompt": prompt
            })

            schedule_payload = {
                'GroupName': SCHEDULE_GROUP_NAME,
                'Name': SCHEDULE_NAME,
                'ScheduleExpression': 'rate(5 minutes)',
                'StartDate': start_date,
                'EndDate': end_date,
                'State': 'ENABLED',
                'Target': {
                    'Arn': TARGET_LAMBDA_ARN,
                    'RoleArn': SCHEDULER_ROLE_ARN,
                    'Input': target_input
                },
                'FlexibleTimeWindow': {'Mode': 'OFF'}
            }

            try:
                # 스케줄 업데이트 시도
                logger.info(f"Attempting to update schedule: {SCHEDULE_NAME}")
                response = scheduler_client.update_schedule(**schedule_payload)
                schedule_arn = response.get('ScheduleArn')
                logger.info(f"Successfully updated schedule: {schedule_arn}")
                return create_response(200, {
                    'message': 'Schedule updated successfully.',
                    'scheduleName': SCHEDULE_NAME,
                    'scheduleArn': schedule_arn
                })
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # 스케줄이 없으면 생성 시도
                    logger.info(f"Schedule '{SCHEDULE_NAME}' not found, attempting to create.")
                    try:
                        response = scheduler_client.create_schedule(**schedule_payload)
                        schedule_arn = response.get('ScheduleArn')
                        logger.info(f"Successfully created schedule: {schedule_arn}")
                        return create_response(201, { # 201 Created 반환
                            'message': 'Schedule created successfully.',
                            'scheduleName': SCHEDULE_NAME,
                            'scheduleArn': schedule_arn
                        })
                    except ClientError as create_e:
                        logger.error(f"Error creating schedule after not found: {create_e}")
                        return create_response(500, {'error': f"Failed to create schedule: {create_e.response['Error']['Message']}"})
                else:
                    # 업데이트 중 다른 오류 발생
                    logger.error(f"Error updating schedule '{SCHEDULE_NAME}': {e}")
                    return create_response(500, {'error': f"Failed to update schedule: {e.response['Error']['Message']}"})

        except json.JSONDecodeError: return create_response(400, {'error': 'Bad Request: Invalid JSON.'})
        except Exception as e: logger.error(f"Unexpected error on POST: {e}"); return create_response(500, {'error': 'Internal server error.'})

    # --- DELETE /apis/videos/schedule (스케줄 삭제) --- 
    elif http_method == 'DELETE':
        try:
            logger.info(f"Attempting to delete schedule: {SCHEDULE_NAME}")
            scheduler_client.delete_schedule(
                Name=SCHEDULE_NAME,
                GroupName=SCHEDULE_GROUP_NAME
            )
            logger.info(f"Successfully deleted schedule: {SCHEDULE_NAME}")
            return create_response(200, {'message': f'Schedule {SCHEDULE_NAME} deleted successfully.'})

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning(f"Schedule '{SCHEDULE_NAME}' not found for deletion.")
                return create_response(200, {'message': f'Schedule {SCHEDULE_NAME} was already deleted or not found.'})
            else:
                logger.error(f"Error deleting schedule '{SCHEDULE_NAME}': {e}")
                return create_response(500, {'error': f"Failed to delete schedule: {e.response['Error']['Message']}"})
        except Exception as e: logger.error(f"Unexpected error on DELETE: {e}"); return create_response(500, {'error': 'Internal server error.'})

    # --- 지원하지 않는 메서드 --- 
    else:
        logger.warning(f"Unsupported method: {http_method}")
        return create_response(405, {'error': f'Method {http_method} Not Allowed'}) 