#!/usr/bin/env python3
"""
AWS 보안 스캐너 에이전트 - 올인원 버전
팀 협업용 단일 파일 구현

사용법:
    from aws_security_scanner import AWSSecurityScanner
    
    scanner = AWSSecurityScanner(region_name="us-east-1")
    result = await scanner.run_full_scan()
    print(f"리포트 경로: {result['report_path']}")

필요한 의존성:
    pip install boto3 strands-agents strands-agents-tools jinja2
"""

import json
import logging
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import boto3
from strands import Agent
from strands.models import BedrockModel
from strands_tools import python_repl

# python_repl 자동 승인 설정
os.environ["BYPASS_TOOL_CONSENT"] = "true"

logger = logging.getLogger(__name__)


class AWSSecurityScanner:
    """AWS 보안 스캐너 - 올인원 에이전트"""
    
    # 핵심 보안 정책 (간소화 버전)
    SECURITY_POLICIES = """
# AWS 핵심 보안 규칙 (간소화)

## 주요 보안 검사 항목

### 1. S3 버킷 퍼블릭 액세스 차단
- S3 버킷은 퍼블릭 읽기/쓰기가 차단되어야 함
- 불필요한 외부 노출 방지

### 2. 보안 그룹 SSH 퍼블릭 접근 차단
- 보안 그룹에서 SSH(22번 포트)는 0.0.0.0/0으로 개방되면 안됨
- 특정 IP 대역으로만 제한 필요

### 3. IAM 루트 계정 사용 최소화
- 루트 계정 직접 사용은 최소화해야 함
- IAM 사용자나 역할을 통한 접근 권장
"""

    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    ):
        """
        AWS 보안 스캐너 초기화
        
        Args:
            region_name: AWS 리전
            model_id: Bedrock 모델 ID
        """
        self.region_name = region_name
        self.model = BedrockModel(region_name=region_name, model_id=model_id)
        
        # 코드 생성 에이전트 초기화
        self.code_generator = Agent(
            model=self.model,
            system_prompt=self._get_code_generator_prompt(),
            tools=[python_repl],
            callback_handler=None
        )

    def _get_code_generator_prompt(self) -> str:
        """코드 생성 에이전트 시스템 프롬프트"""
        return """
        당신은 AWS 보안 전문가이자 Python 개발자입니다.
        
        역할:
        - 보안 정책을 분석하여 AWS 리소스 평가 Python 코드 생성
        - 표준화된 input/output 인터페이스를 준수하는 코드 작성
        - python_repl을 사용하여 코드 실행 및 검증
        
        표준 인터페이스:
        
        INPUT (항상 이 변수명 사용):
        ```python
        aws_resources = [
            # AWSResource 객체들의 리스트
            # 각 객체는 다음 속성을 가짐:
            # - resource_id: str
            # - resource_type: str ('ec2_instance', 's3_bucket', 'ec2_security_group', etc.)
            # - region: str
            # - account_id: str
            # - tags: dict
            # - metadata: dict (실제 리소스 상세 정보)
        ]
        ```
        
        OUTPUT (항상 이 변수명과 구조 사용):
        ```python
        evaluation_results = {
            "total_rules": int,
            "compliant_rules": int,
            "non_compliant_rules": int,
            "not_applicable_rules": int,
            "overall_compliance_percentage": float,
            "rule_results": [
                {
                    "rule_id": str,
                    "rule_name": str,
                    "service": str,
                    "description": str,
                    "severity": str,  # 'HIGH', 'MEDIUM', 'LOW'
                    "compliance_status": str,  # 'COMPLIANT', 'NON_COMPLIANT', 'NOT_APPLICABLE'
                    "total_resources_checked": int,
                    "compliant_resources_count": int,
                    "non_compliant_resources_count": int,
                    "non_compliant_resources": [
                        {
                            "resource_id": str,
                            "resource_type": str,
                            "region": str,
                            "account_id": str,
                            "violation_details": str,
                            "tags": dict
                        }
                    ],
                    "recommendation": str
                }
            ]
        }
        ```
        
        코드 작성 규칙:
        1. 항상 aws_resources 변수에서 데이터를 읽어옴
        2. 결과는 항상 evaluation_results 변수에 저장
        3. 각 보안 정책에 대해 check_ 함수를 생성
        4. 리소스 타입별로 적절한 검사 수행
        5. 명확한 위반 사항 설명 제공
        
        python_repl을 사용하여 코드를 실행하고 결과를 확인하세요.
        """



    async def run_full_scan(self) -> Dict[str, Any]:
        """
        전체 AWS 보안 스캔 실행
        
        Returns:
            Dict containing scan results and report path
        """
        try:
            logger.info("AWS 보안 스캔 시작...")
            
            # 1. 계정 정보 조회
            account_info = self._get_aws_account_info()
            account_id = account_info.get("account_id", "unknown")
            logger.info(f"AWS 계정 ID: {account_id}")
            
            # 2. AWS 리소스 스캔 (비동기 병렬)
            raw_resources = await self._scan_all_aws_resources()
            logger.info(f"총 {len(raw_resources)}개 리소스 스캔 완료")
            
            # 3. 리소스 데이터를 S3에 저장
            resources_file_path = self._save_resources_to_s3(raw_resources, account_id, "scanner1")
            
            # 4. 보안 평가 코드 생성 및 실행
            evaluation_response = await self._generate_and_run_evaluation(resources_file_path)
            
            # 5. HTML 리포트 생성은 별도 report agent에서 처리
            
            return {
                "account_info": account_info,
                "scan_summary": {
                    "message": "보안 스캔 완료 - 리포트 생성은 별도 report agent 사용",
                    "total_resources_scanned": len(raw_resources),
                    "response": evaluation_response
                },
            }
            
        except Exception as e:
            logger.error(f"보안 스캔 실행 중 오류: {e}")
            raise

    def _get_aws_account_info(self) -> Dict[str, Any]:
        """AWS 계정 정보 조회"""
        try:
            sts_client = boto3.client("sts", region_name=self.region_name)
            response = sts_client.get_caller_identity()
            
            return {
                "account_id": response.get("Account"),
                "user_id": response.get("UserId"),
                "arn": response.get("Arn"),
                "region": self.region_name,
                "scan_time": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"계정 정보 조회 실패: {e}")
            return {"error": str(e), "service": "STS"}

    async def _scan_all_aws_resources(self) -> List[Dict[str, Any]]:
        """핵심 AWS 리소스만 스캔 (간소화 버전)"""
        scan_functions = [
            self._scan_s3_buckets,
            self._scan_security_groups,
            self._scan_iam_root_account,
        ]
        
        # 모든 스캔을 병렬로 실행
        tasks = [func() for func in scan_functions]
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 수집
        all_resources = []
        for result in scan_results:
            if isinstance(result, list):
                all_resources.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"스캔 중 오류: {result}")
        
        return all_resources

    async def _scan_ec2_instances(self) -> List[Dict[str, Any]]:
        """EC2 인스턴스 스캔"""
        try:
            ec2_client = boto3.client("ec2", region_name=self.region_name)
            response = ec2_client.describe_instances()
            
            resources = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    resource = {
                        "resource_id": instance["InstanceId"],
                        "resource_type": "ec2_instance",
                        "region": self.region_name,
                        "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                        "metadata": instance
                    }
                    resources.append(resource)
            
            logger.info(f"EC2 인스턴스 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"EC2 스캔 실패: {e}")
            return []

    async def _scan_s3_buckets(self) -> List[Dict[str, Any]]:
        """S3 버킷 스캔"""
        try:
            s3_client = boto3.client("s3", region_name=self.region_name)
            response = s3_client.list_buckets()
            
            resources = []
            for bucket in response["Buckets"]:
                bucket_name = bucket["Name"]
                
                # 버킷 상세 정보 수집
                try:
                    # 퍼블릭 액세스 블록 설정 확인
                    pab_response = s3_client.get_public_access_block(Bucket=bucket_name)
                    public_access_block = pab_response.get("PublicAccessBlockConfiguration", {})
                except:
                    public_access_block = {}
                
                resource = {
                    "resource_id": bucket_name,
                    "resource_type": "s3_bucket",
                    "region": self.region_name,
                    "tags": {},
                    "metadata": {
                        "bucket_name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "public_access_block": public_access_block
                    }
                }
                resources.append(resource)
            
            logger.info(f"S3 버킷 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"S3 스캔 실패: {e}")
            return []

    async def _scan_security_groups(self) -> List[Dict[str, Any]]:
        """보안 그룹 스캔"""
        try:
            ec2_client = boto3.client("ec2", region_name=self.region_name)
            response = ec2_client.describe_security_groups()
            
            resources = []
            for sg in response["SecurityGroups"]:
                resource = {
                    "resource_id": sg["GroupId"],
                    "resource_type": "ec2_security_group",
                    "region": self.region_name,
                    "tags": {tag["Key"]: tag["Value"] for tag in sg.get("Tags", [])},
                    "metadata": sg
                }
                resources.append(resource)
            
            logger.info(f"보안 그룹 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"보안 그룹 스캔 실패: {e}")
            return []

    async def _scan_rds_instances(self) -> List[Dict[str, Any]]:
        """RDS 인스턴스 스캔"""
        try:
            rds_client = boto3.client("rds", region_name=self.region_name)
            response = rds_client.describe_db_instances()
            
            resources = []
            for db in response["DBInstances"]:
                resource = {
                    "resource_id": db["DBInstanceIdentifier"],
                    "resource_type": "rds_instance",
                    "region": self.region_name,
                    "tags": {},
                    "metadata": db
                }
                resources.append(resource)
            
            logger.info(f"RDS 인스턴스 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"RDS 스캔 실패: {e}")
            return []

    async def _scan_cloudtrail_trails(self) -> List[Dict[str, Any]]:
        """CloudTrail 트레일 스캔"""
        try:
            cloudtrail_client = boto3.client("cloudtrail", region_name=self.region_name)
            response = cloudtrail_client.describe_trails()
            
            resources = []
            for trail in response["trailList"]:
                resource = {
                    "resource_id": trail["Name"],
                    "resource_type": "cloudtrail_trail",
                    "region": self.region_name,
                    "tags": {},
                    "metadata": trail
                }
                resources.append(resource)
            
            logger.info(f"CloudTrail 트레일 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"CloudTrail 스캔 실패: {e}")
            return []

    async def _scan_kms_keys(self) -> List[Dict[str, Any]]:
        """KMS 키 스캔"""
        try:
            kms_client = boto3.client("kms", region_name=self.region_name)
            response = kms_client.list_keys()
            
            resources = []
            for key in response["Keys"]:
                key_id = key["KeyId"]
                
                # 키 상세 정보 조회
                try:
                    key_details = kms_client.describe_key(KeyId=key_id)
                    key_metadata = key_details["KeyMetadata"]
                    
                    # 고객 관리 키만 포함
                    if key_metadata.get("KeyManager") == "CUSTOMER":
                        resource = {
                            "resource_id": key_id,
                            "resource_type": "kms_key",
                            "region": self.region_name,
                            "tags": {},
                            "metadata": key_metadata
                        }
                        resources.append(resource)
                except:
                    continue
            
            logger.info(f"KMS 키 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"KMS 스캔 실패: {e}")
            return []

    async def _scan_secrets_manager(self) -> List[Dict[str, Any]]:
        """Secrets Manager 시크릿 스캔"""
        try:
            secrets_client = boto3.client("secretsmanager", region_name=self.region_name)
            response = secrets_client.list_secrets()
            
            resources = []
            for secret in response["SecretList"]:
                resource = {
                    "resource_id": secret["Name"],
                    "resource_type": "secrets_manager_secret",
                    "region": self.region_name,
                    "tags": {},
                    "metadata": secret
                }
                resources.append(resource)
            
            logger.info(f"Secrets Manager 시크릿 {len(resources)}개 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"Secrets Manager 스캔 실패: {e}")
            return []

    async def _scan_iam_root_account(self) -> List[Dict[str, Any]]:
        """IAM 루트 계정 사용 패턴 스캔 (간소화)"""
        try:
            sts_client = boto3.client("sts", region_name=self.region_name)
            caller_identity = sts_client.get_caller_identity()
            
            resources = []
            
            # 현재 호출자 정보만 수집
            resource = {
                "resource_id": caller_identity.get("Arn", "unknown"),
                "resource_type": "iam_caller_identity",
                "region": self.region_name,
                "tags": {},
                "metadata": {
                    "account_id": caller_identity.get("Account"),
                    "user_id": caller_identity.get("UserId"),
                    "arn": caller_identity.get("Arn"),
                    "is_root": "root" in caller_identity.get("Arn", "").lower()
                }
            }
            resources.append(resource)
            
            logger.info(f"IAM 호출자 정보 스캔 완료")
            return resources
            
        except Exception as e:
            logger.error(f"IAM 스캔 실패: {e}")
            return []

    def _save_resources_to_s3(self, resources: List[Dict[str, Any]], account_id: str, scanner_type: str = "scanner1") -> str:
        """리소스 데이터를 S3에 JSON 파일로 저장"""
        # S3 버킷 이름 (환경변수 또는 기본값)
        bucket_name = os.environ.get('SECURITY_SCAN_BUCKET', f'aws-security-scan-{account_id}-{self.region_name}')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{scanner_type}/{timestamp}/aws_resources.json"
        
        # account_id 추가
        for resource in resources:
            resource["account_id"] = account_id
        
        # S3에 업로드
        s3_client = boto3.client('s3', region_name=self.region_name)
        
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(resources, indent=2, ensure_ascii=False, default=str),
                ContentType='application/json'
            )
            
            s3_path = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"리소스 데이터 S3 저장: {s3_path} ({len(resources)}개)")
            return s3_path
            
        except Exception as e:
            logger.error(f"S3 저장 실패: {e}")
            # 로컬 파일로 폴백
            os.makedirs("/tmp/resources", exist_ok=True)
            local_path = f"/tmp/resources/aws_resources_{timestamp}.json"
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(resources, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"로컬 파일로 저장: {local_path}")
            return local_path

    async def _generate_and_run_evaluation(self, resources_file_path: str) -> str:
        """보안 평가 코드 생성 및 실행"""
        
        # S3 경로인지 로컬 경로인지 확인
        if resources_file_path.startswith('s3://'):
            data_load_code = f"""
import json
import boto3

# S3에서 리소스 데이터 로드
s3_path = '{resources_file_path}'
bucket_name = s3_path.split('/')[2]
s3_key = '/'.join(s3_path.split('/')[3:])

s3_client = boto3.client('s3')
response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
aws_resources = json.loads(response['Body'].read().decode('utf-8'))
"""
        else:
            data_load_code = f"""
import json

# 로컬 파일에서 리소스 데이터 로드
with open('{resources_file_path}', 'r', encoding='utf-8') as f:
    aws_resources = json.load(f)
"""
        
        prompt = f"""
        다음 보안 정책을 분석하여 AWS 리소스 평가 Python 코드를 생성해주세요:
        
        보안 정책:
        {self.SECURITY_POLICIES}
        
        AWS 리소스 데이터 경로: {resources_file_path}
        
        작업 순서:
        1. python_repl을 사용하여 다음 코드를 생성하고 실행:
        
        ```python
        {data_load_code}
        
        # 2. 검사 함수들 정의
        def check_s3_public_access():
            # S3 버킷 퍼블릭 액세스 검사
            pass
            
        def check_security_group_ssh():
            # 보안 그룹 SSH 개방 검사
            pass
        
        # 3. 모든 규칙 실행 및 결과 생성
        evaluation_results = {{
            "total_rules": 0,
            "compliant_rules": 0,
            "non_compliant_rules": 0,
            "not_applicable_rules": 0,
            "overall_compliance_percentage": 0.0,
            "rule_results": []
        }}
        ```
        
        중요: 
        - aws_resources 변수에서 데이터 로드 후 분석
        - evaluation_results 변수에 표준 형식으로 저장
        - 각 규칙별로 적용 가능한 리소스 타입 확인
        - 명확한 위반 사항 설명 제공
        
        코드를 생성하고 실행해주세요.
        """
        
        logger.info("보안 평가 코드 생성 및 실행 중...")
        
        # 스트리밍으로 응답 받기
        full_response = ""
        async for chunk in self.code_generator.stream_async(prompt):
            if "data" in chunk:
                full_response += chunk["data"]
        
        logger.info("보안 평가 완료")
        return full_response




# 사용 예시
async def main():
    """사용 예시"""
    logging.basicConfig(level=logging.INFO)
    
    scanner = AWSSecurityScanner(region_name="us-east-1")
    result = await scanner.run_full_scan()
    
    print("✅ AWS 보안 스캔 완료!")
    print(f"📊 스캔 결과:")
    print(f"   - 메시지: {result['scan_summary']['message']}")
    print(f"   - 스캔된 리소스: {result['scan_summary']['total_resources_scanned']}개")
    print(f"   - 계정 ID: {result['account_info'].get('account_id', 'unknown')}")
    print(f"   - HTML 리포트 생성은 별도 AWSSecurityReportAgent 사용")


if __name__ == "__main__":
    asyncio.run(main())