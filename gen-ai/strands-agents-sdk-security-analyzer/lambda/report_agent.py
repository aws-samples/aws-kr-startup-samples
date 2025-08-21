"""
AWS 보안 리포트 생성 에이전트
AWS 보안 평가 결과를 기반으로 전문적인 HTML 리포트를 생성합니다.

사용법:
    from aws_security_report_agent import AWSSecurityReportAgent
    
    reporter = AWSSecurityReportAgent(region_name="us-east-1")
    report_path = await reporter.generate_report(evaluation_results, account_info)
    print(f"리포트 경로: {report_path}")

필요한 의존성:
    pip install strands-agents strands-agents-tools
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
import re
import boto3

from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

class AWSSecurityReportAgent:
    """AWS 보안 리포트 생성 전용 에이전트"""
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    ):
        """
        AWS 보안 리포트 에이전트 초기화
        
        Args:
            region_name: AWS 리전
            model_id: Bedrock 모델 ID
        """
        self.region_name = region_name
        self.model = BedrockModel(region_name=region_name, model_id=model_id)
        self.bucket_name = os.environ.get('SECURITY_SCAN_BUCKET')
        self.s3_client = boto3.client('s3', region_name=region_name)
        
        # HTML 리포터 에이전트 초기화
        self.html_reporter = Agent(
            model=self.model,
            system_prompt=self._get_html_reporter_prompt(),
            callback_handler=None
        )

    def _get_html_reporter_prompt(self) -> str:
        """HTML 리포터 에이전트 시스템 프롬프트"""
        return """
        당신은 AWS 보안 전문가이자 웹 개발자입니다.
        
        역할:
        - AWS 보안 평가 결과를 기반으로 전문적인 HTML 리포트 생성
        - 사용자 친화적이고 시각적으로 매력적인 리포트 디자인
        - 보안 위험도에 따른 적절한 색상 및 아이콘 사용
        - 인터랙티브한 요소 (드롭다운, 토글 등) 포함
        
        HTML 리포트 요구사항:
        1. **반드시 한국어로 작성**: 모든 제목, 설명, 텍스트를 한국어로 작성
        2. 반응형 디자인 (모바일/데스크톱 호환)
        3. 현대적인 CSS 스타일링 (인라인 또는 <style> 태그)
        4. 보안 위험도별 색상 구분 (CRITICAL: 빨강, HIGH: 주황, MEDIUM: 노랑, LOW: 초록)
        5. 드롭다운으로 상세 정보 표시
        6. 요약 통계 대시보드
        7. 위반 리소스 목록 및 상세 정보
        8. 권장사항 및 해결 방법 제시
        9. JavaScript 인터랙션 기능
        10. 최근 보안 뉴스 정리
        
        중요: 생성하는 HTML 리포트의 모든 텍스트는 반드시 한국어로 작성해야 합니다.
        완전한 HTML 문서를 바로 생성해주세요. 추가 도구나 코드 실행은 필요하지 않습니다.
        """

    def generate_report(
        self, 
        prompt: str, 
        # account_info: Dict[str, Any]
    ) -> str:
        """
        HTML 리포트 생성 및 저장
        
        Args:
            prompt: 보안 평가 결과 텍스트
            
        Returns:
            생성된 HTML 리포트 파일 경로
        """
        try:
            logger.info("HTML 리포트 생성 시작...")
            
            # HTML 콘텐츠 생성
            html_content = self._generate_html_content(prompt)

            # HTML 코드 블록에서 추출 시도, 실패하면 전체 내용 사용
            html_match = re.search(r"```html\n(.*?)\n```", html_content, re.DOTALL)
            if html_match:
                html_content = html_match.group(1)
            # HTML 태그가 있으면 그대로 사용
            elif "<html" in html_content.lower():
                pass  # 이미 HTML 형식
            else:
                # HTML이 아니면 간단한 HTML로 래핑
                html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS 보안 리포트</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .finding {{ background: white; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .high {{ border-left: 4px solid #dc3545; }}
        .medium {{ border-left: 4px solid #ffc107; }}
        .low {{ border-left: 4px solid #28a745; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AWS 보안 분석 리포트</h1>
        <div class="summary">
            <h2>분석 결과 요약</h2>
            <pre>{html_content}</pre>
        </div>
    </div>
</body>
</html>
"""

            # 파일로 저장
            report_path = self._save_html_report(html_content)
            
            logger.info(f"HTML 리포트 생성 완료: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"리포트 생성 중 오류: {e}")
            raise

    def _generate_html_content(
        self, 
        prompt: str, 
    ) -> str:
        """HTML 콘텐츠 생성"""
        
        # 샘플 템플릿 파일 읽기
        try:
            with open('report/sample_report.html', 'r', encoding='utf-8') as f:
                sample_template = f.read()
        except FileNotFoundError:
            sample_template = "샘플 템플릿을 찾을 수 없습니다."
        
        prompt = f"""
        다음 AWS 보안 분석 결과를 바탕으로 HTML 리포트를 생성해주세요.
        
        전체 분석 결과:
        {prompt}
        
        계정 정보:
        - 리전: {self.region_name}
        - 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        **중요: 다음 샘플 템플릿의 구조와 스타일을 참고하여 리포트를 생성하세요:**
        
        {sample_template}
        
        **생성 지침:**
        1. 위 샘플 템플릿의 구조를 그대로 사용하되, 실제 분석 데이터로 내용을 채워주세요
        2. Tailwind CSS 스타일링을 유지하세요
        3. Chart.js를 사용한 차트 기능을 포함하세요
        4. 확장/축소 가능한 섹션 기능을 유지하세요
        5. 모든 텍스트를 한국어로 작성하세요
        
        **데이터 매핑:**
        - Header 섹션: 실제 계정 ID, 스캔 시간, 리전, 스캔된 리소스 수
        - Security Score: CloudTrail 보안 점수 반영
        - Resource Summary: S3 버킷, 보안 그룹, IAM 실제 검사 결과
        - CloudTrail Analysis: 실제 CloudTrail 분석 결과 반영
        - Recommendations: 실제 권장사항으로 교체
        - Security News: 실제 뉴스 데이터로 교체
        
        **출력 형식:**
        완전한 HTML 문서를 ```html 코드 블록 안에 작성해주세요.
        """
        
        logger.info("HTML 콘텐츠 생성 중...")
        
        result = self.html_reporter(prompt)
        
        # AgentResult에서 텍스트 추출
        if hasattr(result, 'text'):
            return result.text
        elif hasattr(result, 'content'):
            return result.content
        else:
            return str(result)

    def _save_html_report(self, html_content: str) -> str:
        """HTML 리포트를 S3에 저장 (구현 완료)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"security_report/{timestamp}/report.html"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=html_content,
                ContentType='text/html'
            )
            
            report_path = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"HTML 리포트 S3 저장: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"S3 저장 실패: {e}")
            # 로컬 폴백
            local_path = f"/tmp/security_report_{timestamp}.html"
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return local_path

    def generate_report_from_file(self, evaluation_file_path: str, account_info: Dict[str, Any]) -> str:
        """
        파일에서 평가 결과를 읽어 리포트 생성 (동기 버전)
        
        Args:
            evaluation_file_path: 평가 결과 파일 경로
            account_info: AWS 계정 정보
            
        Returns:
            생성된 HTML 리포트 파일 경로
        """
        try:
            with open(evaluation_file_path, 'r', encoding='utf-8') as f:
                evaluation_response = f.read()
            
            # 동기 버전으로 실행
            import asyncio
            return asyncio.run(self.generate_report(evaluation_response, account_info))
            
        except Exception as e:
            logger.error(f"파일에서 리포트 생성 중 오류: {e}")
            raise


# 사용 예시
async def main():
    """사용 예시"""
    logging.basicConfig(level=logging.INFO)
    
    # 샘플 데이터
    sample_evaluation = """
    === EVALUATION_RESULTS ===
    {
        "total_rules": 5,
        "compliant_rules": 2,
        "non_compliant_rules": 3,
        "not_applicable_rules": 0,
        "overall_compliance_percentage": 40.0,
        "rule_results": [
            {
                "rule_id": "S3_PUBLIC_ACCESS",
                "rule_name": "S3 버킷 퍼블릭 액세스 차단",
                "service": "S3",
                "description": "S3 버킷은 퍼블릭 읽기/쓰기가 차단되어야 함",
                "severity": "HIGH",
                "compliance_status": "NON_COMPLIANT",
                "total_resources_checked": 3,
                "compliant_resources_count": 1,
                "non_compliant_resources_count": 2,
                "recommendation": "퍼블릭 액세스 블록 설정을 활성화하세요"
            }
        ]
    }
    """
    
    sample_account_info = {
        "account_id": "123456789012",
        "region": "us-east-1",
        "scan_time": datetime.now().isoformat()
    }
    
    reporter = AWSSecurityReportAgent(region_name="us-east-1")
    report_path = await reporter.generate_report(sample_evaluation, sample_account_info)
    
    print("✅ AWS 보안 리포트 생성 완료!")
    # add report to s3
    print(f"📄 리포트 경로: {report_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())