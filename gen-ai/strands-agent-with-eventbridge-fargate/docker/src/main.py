import json
import boto3
import os
import time
from datetime import datetime

def main():
    print("Starting Strands Agent...")
    
    # 환경 변수에서 S3 버킷 이름 가져오기
    s3_bucket = os.environ.get('S3_BUCKET', 'default-bucket')
    aws_region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    
    print(f"S3 Bucket: {s3_bucket}")
    print(f"AWS Region: {aws_region}")
    
    # 현재 시간 기록
    current_time = datetime.now().isoformat()
    
    # 간단한 작업 시뮬레이션
    result = {
        "timestamp": current_time,
        "status": "completed",
        "message": "Strands Agent executed successfully",
        "s3_bucket": s3_bucket,
        "region": aws_region
    }
    
    # S3에 결과 저장 (선택사항)
    try:
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # 결과를 JSON 파일로 S3에 업로드
        result_key = f"results/{current_time.replace(':', '-')}_result.json"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=result_key,
            Body=json.dumps(result, indent=2),
            ContentType='application/json'
        )
        
        print(f"Result saved to S3: s3://{s3_bucket}/{result_key}")
        
    except Exception as e:
        print(f"Error saving to S3: {str(e)}")
        # S3 저장 실패해도 프로그램은 계속 실행
    
    print("Strands Agent completed successfully")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
