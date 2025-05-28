import boto3
import json
from datetime import datetime

class SageMakerLLMClient:
    def __init__(self, endpoint_name: str, region: str = 'us-west-2'):
        self.endpoint_name = endpoint_name
        self.region = region
        self.sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=region)
        
    def invoke_endpoint(self, messages: list, parameters: dict = None) -> dict:
        """
        Invoke the SageMaker endpoint with messages
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            parameters: Optional generation parameters
        
        Returns:
            Response from the endpoint
        """
        if parameters is None:
            parameters = {
                "model": "Gonsoo/AWS-Neuron-llama-3-Korean-Bllossom-8B",
                "top_p": 0.6,
                "temperature": 0.9,
                "max_tokens": 2048,
                "stop": ["<|eot_id|>"]
            }
        
        payload = {
            "messages": messages,
            **parameters
        }
        
        try:
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            return result
            
        except Exception as e:
            print(f"Error invoking endpoint: {str(e)}")
            raise

def test_korean_qa(endpoint_name: str):
    """Test Korean Q&A functionality"""
    
    client = SageMakerLLMClient(endpoint_name)
    
    # Test messages
    test_cases = [
        {
            "name": "AI 기술 질문",
            "messages": [
                {"role": "system", "content": "당신은 인공지능 전문가입니다."},
                {"role": "user", "content": "딥러닝이 무엇인지 말해 주세요?"}
            ]
        },
        {
            "name": "일반 대화",
            "messages": [
                {"role": "system", "content": "당신은 친근한 AI 어시스턴트입니다."},
                {"role": "user", "content": "안녕하세요! 오늘 날씨가 좋네요."}
            ]
        },
        {
            "name": "코딩 질문",
            "messages": [
                {"role": "system", "content": "당신은 프로그래밍 전문가입니다."},
                {"role": "user", "content": "Python에서 리스트와 튜플의 차이점을 설명해주세요."}
            ]
        }
    ]
    
    print("🧪 SageMaker LLM Endpoint 테스트 시작")
    print(f"📡 Endpoint: {endpoint_name}")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 테스트 {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            start_time = datetime.now()
            
            response = client.invoke_endpoint(
                messages=test_case['messages'],
                parameters={
                    "model": "Gonsoo/AWS-Neuron-llama-3-Korean-Bllossom-8B",
                    "top_p": 0.6,
                    "temperature": 0.9,
                    "max_tokens": 1024,
                    "stop": ["<|eot_id|>"]
                }
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ 응답 시간: {duration:.2f}초")
            print(f"📝 응답:")
            
            # Extract response text based on the actual response format
            if 'choices' in response and len(response['choices']) > 0:
                content = response['choices'][0].get('message', {}).get('content', '')
                print(content)
            elif 'generated_text' in response:
                print(response['generated_text'])
            else:
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 테스트 완료!")

def check_endpoint_status(endpoint_name: str, region: str = 'us-west-2'):
    """Check the status of the SageMaker endpoint"""
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    try:
        response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        
        print(f"📊 Endpoint Status Report")
        print(f"   Name: {response['EndpointName']}")
        print(f"   Status: {response['EndpointStatus']}")
        print(f"   Creation Time: {response['CreationTime']}")
        print(f"   Last Modified: {response['LastModifiedTime']}")
        
        if response['EndpointStatus'] == 'InService':
            print("✅ Endpoint is ready for inference!")
        elif response['EndpointStatus'] == 'Creating':
            print("🔄 Endpoint is still being created...")
        elif response['EndpointStatus'] == 'Failed':
            print("❌ Endpoint creation failed!")
            if 'FailureReason' in response:
                print(f"   Failure Reason: {response['FailureReason']}")
        
        return response['EndpointStatus']
        
    except Exception as e:
        print(f"❌ Error checking endpoint status: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python test_endpoint.py <endpoint_name>")
        print("Example: python test_endpoint.py sm-llama3-kr-inf2-2024-01-01-12-00-00")
        sys.exit(1)
    
    endpoint_name = sys.argv[1]
    
    # Check endpoint status first
    status = check_endpoint_status(endpoint_name)
    
    if status == 'InService':
        print("\n" + "=" * 50)
        test_korean_qa(endpoint_name)
    elif status == 'Creating':
        print("\n⏳ Please wait for the endpoint to be ready and try again.")
    else:
        print("\n❌ Endpoint is not available for testing.")

# requirements.txt for the test script
"""
boto3>=1.26.0
"""
