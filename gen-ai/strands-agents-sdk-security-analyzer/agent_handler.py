import asyncio
import json
import os
from typing import Dict, Any

# Lambda 환경에서 python_repl이 /tmp 디렉터리를 사용하도록 작업 디렉터리를 먼저 변경
os.chdir('/tmp')

# 이제 strands 모듈들을 import (python_repl이 /tmp에 repl_state 디렉터리 생성)
from workflow_agent import SecurityWorkflowAgent


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler - 보안 워크플로우 진입점
    """
    try:
        # 워크플로우 에이전트 초기화
        workflow_agent = SecurityWorkflowAgent()
        
        # 비동기 워크플로우 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(workflow_agent.run_workflow())
        finally:
            loop.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Security workflow completed',
                'result': result,
                'request_id': context.aws_request_id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'request_id': context.aws_request_id
            })
        }