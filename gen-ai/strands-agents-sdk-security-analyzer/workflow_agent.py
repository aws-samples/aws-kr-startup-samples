import asyncio
import json
import boto3
import os
from datetime import datetime

from security_news import SecurtyNewsScrapper
from aws_security_scanner import AWSSecurityScanner
from cloudtrail_tool import CloudTrailTool
from report_agent import AWSSecurityReportAgent

class SecurityWorkflowAgent:
    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.bucket_name = os.environ.get('SECURITY_SCAN_BUCKET')
        self.s3_client = boto3.client('s3', region_name=region_name)
        
        if not self.bucket_name:
            raise ValueError("SECURITY_SCAN_BUCKET environment variable not set")

    def _save_to_s3(self, data, scanner_type: str) -> str:
        """S3에 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{scanner_type}/{timestamp}/result.json"
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(data, indent=2, ensure_ascii=False, default=str),
            ContentType='application/json'
        )
        return f"s3://{self.bucket_name}/{s3_key}"

    async def run_workflow(self):
        """워크플로우 실행 - API 제한 회피를 위한 순차 실행"""
        results = {}
        
        print("보안 워크플로우 시작...")
        
        # 1단계: AWS 보안 스캐너 (Bedrock 사용 안함)
        print("1/3: AWS 보안 스캐너 실행 중...")
        scanner = AWSSecurityScanner(region_name=self.region_name)
        try:
            scanner_result = await scanner.run_full_scan()
            print("✅ AWS 보안 스캐너 완료")
        except Exception as e:
            print(f"❌ AWS 보안 스캐너 실패: {e}")
            scanner_result = {"error": str(e), "scan_status": "failed"}
        
        # 2단계: CloudTrail 스캐너 (Bedrock 사용)
        print("2/3: CloudTrail 스캐너 실행 중...")
        cloudtrail_scanner = CloudTrailTool(region_name=self.region_name)
        try:
            cloudtrail_result = await cloudtrail_scanner.scan_cloudtrail_events()
            print("✅ CloudTrail 스캐너 완료")
        except Exception as e:
            print(f"❌ CloudTrail 스캐너 실패: {e}")
            cloudtrail_result = {"error": str(e), "scan_status": "failed"}
        
        # 3단계: 보안 뉴스 스크래퍼 (Bedrock 사용)
        print("3/3: 보안 뉴스 스크래퍼 실행 중...")
        scrapper = SecurtyNewsScrapper()
        try:
            news_result = scrapper.agent("최근 14일 이내의 보안 뉴스를 분석해주세요.")
            print("✅ 보안 뉴스 스크래퍼 완료")
        except Exception as e:
            print(f"❌ 보안 뉴스 스크래퍼 실패: {e}")
            news_result = f"Error: {str(e)}"
        
        # S3에 각 결과 저장
        print("S3에 결과 저장 중...")
        results['scanner'] = self._save_to_s3(scanner_result, "aws_security_scanner")
        results['cloudtrail'] = self._save_to_s3(cloudtrail_result, "cloudtrail_scanner")
        results['news'] = self._save_to_s3(str(news_result), "security_news_scrapper")
        
        # 2단계: 리포트 생성
        combined_data = f"""
AWS Security Scanner Results:
{json.dumps(scanner_result, indent=2, default=str)}

CloudTrail Analysis:
{cloudtrail_result}

Security News:
{str(news_result)}
"""
        
        reporter = AWSSecurityReportAgent(region_name=self.region_name)
        report_result = reporter.generate_report(combined_data)
        results['report'] = self._save_to_s3(report_result, "security_report")
        
        return {
            "workflow_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "results": results
        }