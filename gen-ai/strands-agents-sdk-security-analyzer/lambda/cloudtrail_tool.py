"""
AWS CloudTrail 보안 분석 도구
CloudTrail 이벤트를 분석하여 보안 위협 및 이상 징후를 탐지합니다.

사용법:
    from cloudtrail_scanner import CloudTrailTool

    scanner = CloudTrailTool(region_name="us-east-1")
    result = await scanner.scan_cloudtrail_events()
    print(f"분석 결과: {result}")

필요한 의존성:
    pip install boto3 strands-agents strands-agents-tools
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from strands import Agent
from strands.models import BedrockModel
from strands.tools import tool
import subprocess
import tempfile
import os

@tool
def python_repl(code: str) -> str:
    """Execute Python code in a temporary environment."""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Execute the code
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/tmp'
        )
        
        # Clean up
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
            
    except Exception as e:
        return f"Error executing Python code: {str(e)}"

# python_repl 자동 승인 설정
os.environ["BYPASS_TOOL_CONSENT"] = "true"

logger = logging.getLogger(__name__)


class CloudTrailTool:
    """AWS CloudTrail에서 발생 가능한 이상 징후를 파악합니다"""

    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    ):
        """
        AWS CloudTrail 이벤트 조회 도구 초기화

        Args:
            region_name: AWS 리전
            model_id: Bedrock 모델 ID
        """
        self.region_name = region_name
        self.model = BedrockModel(
            region_name=region_name,
            model_id=model_id,
            max_tokens=64000
        )

        # CloudTrail 분석 에이전트 초기화
        self.cloudtrail_agent = Agent(
            model=self.model,
            system_prompt=self._get_cloudtrail_events_prompt(),
            tools=[python_repl],
            callback_handler=None
        )

    def _get_cloudtrail_events_prompt(self) -> str:
        """CloudTrail 이벤트 분석 프롬프트"""
        return """
당신은 AWS 보안 전문가입니다. 최근 3일간의 AWS CloudTrail 이벤트를 분석하여 보안 위협을 탐지하세요.

## 위험 이벤트 분류

### CRITICAL (즉시 조치 필요)
- userIdentity.type = "Root"
- eventName = "ConsoleLogin" AND errorMessage EXISTS
- eventName = "CreateUser" OR "DeleteUser" OR "CreateRole" OR "DeleteRole"
- eventName = "AttachUserPolicy" AND requestParameters.policyArn = "*Administrator*"
- eventName = "PutBucketPolicy" OR "DeleteBucketPolicy"
- eventName = "StopLogging" OR "DeleteTrail" OR "UpdateTrail"
- eventName = "AuthorizeSecurityGroupIngress" AND requestParameters.cidrIp = "0.0.0.0/0"

### HIGH (24시간 내 조치)
- eventName = "AssumeRole" AND errorCode EXISTS
- eventName = "CreateAccessKey" OR "DeleteAccessKey"
- eventName = "PutUserPolicy" OR "PutRolePolicy"
- eventName = "ModifySnapshotAttribute"
- eventName = "GetSecretValue" OR "GetParameter"
- eventName = "DeleteLogGroup" OR "DeleteLogStream"

### MEDIUM (검토 필요)
- eventName = "ListBuckets" (정찰 활동)
- eventName = "DescribeDBInstances" OR "DescribeDBClusters"
- 대량 List*/Describe* API 호출
- 업무시간 외 활동 (22:00-06:00)
- 새로운 IP 주소에서의 접근

## 분석 기준
- 시간: 22:00-06:00 (업무시간 외)
- 빈도: 동일 API 1시간 내 10회 이상
- 지역: 평소와 다른 sourceIPAddress
- 사용자: Root 계정, 새로운 사용자

## 분석 작업

python_repl을 사용하여 다음 작업을 수행하세요:

1. boto3로 CloudTrail 클라이언트 생성
2. 최근 3일간 이벤트 조회 (최대 50개)
3. 위험 이벤트 필터링 및 분석
4. 패턴 분석 및 결과 출력

python
import boto3
from datetime import datetime, timedelta
import json

cloudtrail = boto3.client('cloudtrail', region_name='us-east-1')
end_time = datetime.now()
start_time = end_time - timedelta(days=3)

response = cloudtrail.lookup_events(
   StartTime=start_time,
   EndTime=end_time,
   MaxResults=50
)

## 출력 형식

분석 완료 후 다음과 같은 간단한 텍스트 요약으로 결과를 출력하세요:

=== CloudTrail 보안 분석 결과 ===

분석 개요:
- 분석 기간: 최근 3일 (2024-01-01 ~ 2024-01-04)
- 총 이벤트: 50개 분석

위험 이벤트:
[위험 이벤트가 있는 경우]
- CRITICAL: 루트 계정 사용 (2024-01-01 14:30, IP: 203.0.113.1)
  → 즉시 조치: 루트 계정 MFA 확인 및 사용 제한
- HIGH: 새벽 관리자 로그인 (admin@company.com, 2024-01-02 02:15, IP: 198.51.100.1)
  → 즉시 조치: 해당 관리자에게 로그인 확인 필요

[위험 이벤트가 없는 경우]
- 위험 이벤트 없음 (모든 활동이 AWS 서비스 정상 동작)

활동 요약:
- 고유 사용자: 3명
- 고유 IP 주소: 5개
- AWS 서비스 자동화 활동: 대부분

권장사항:
1. 정기적인 CloudTrail 로그 검토 (월 1회)
2. 업무시간 외 접근 모니터링 강화
3. MFA 설정 확인 및 강화
4. 루트 계정 사용 최소화

## 분석 지침
1. 실제 CloudTrail 데이터 조회
2. 각 이벤트의 위험성을 명확히 분류
3. 구체적인 조치사항 제공
4. 위험도별 우선순위 구분
5. IP, 사용자, 시간대별 패턴 분석
        """

    async def scan_cloudtrail_events(self) -> str:
        """
        CloudTrail 이벤트 스캔 및 보안 분석 실행

        Returns:
            CloudTrail 분석 결과 텍스트
        """
        try:
            logger.info("CloudTrail 보안 분석 시작...")

            prompt = f"""
            AWS CloudTrail 이벤트를 분석하여 보안 위협을 탐지해주세요.

            분석 대상:
            - AWS 리전: {self.region_name}
            - 분석 기간: 최근 3일
            - 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            작업 순서:
            1. python_repl을 사용하여 boto3로 CloudTrail 이벤트 조회
            2. 위험 이벤트 분류 및 분석
            3. 사용자, IP, 시간대별 패턴 분석
            4. 구체적인 조치사항 제공

            중요사항:
            - 실제 데이터 기반 분석
            - 간단한 텍스트 요약으로 출력 (JSON 형식 사용 금지)
            - 위험 이벤트가 있으면 구체적으로, 없으면 "정상"으로 명시
            - 토큰 절약을 위해 간결하게 작성
            """

            logger.info("CloudTrail 분석 중...")

            result = self.cloudtrail_agent(prompt)

            if hasattr(result, 'text'):
                full_response = result.text
            elif hasattr(result, 'content'):
                full_response = result.content
            else:
                full_response = str(result)

            logger.info("CloudTrail 분석 완료")
            
            # 구조화된 결과 반환
            return {
                "scanner_type": "cloudtrail",
                "timestamp": datetime.now().isoformat(),
                "analysis_result": full_response,  # analysis_text 대신 full_response 사용
                "region": self.region_name,
                "scan_status": "completed"
            }

        except Exception as e:
            logger.error(f"CloudTrail 분석 중 오류: {e}")
            return {
                "scanner_type": "cloudtrail",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "scan_status": "failed"
            }

    def analyze_events_sync(self) -> str:
        """
        동기 버전의 CloudTrail 이벤트 분석

        Returns:
            CloudTrail 분석 결과 텍스트
        """
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.scan_cloudtrail_events())
            loop.close()
            return result
        except Exception as e:
            logger.error(f"동기 CloudTrail 분석 중 오류: {e}")
            return f"CloudTrail 분석 실패: {str(e)}"

async def main():
    """사용 예시"""
    logging.basicConfig(level=logging.INFO)

    scanner = CloudTrailTool(region_name="us-east-1")
    result = await scanner.scan_cloudtrail_events()

    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())