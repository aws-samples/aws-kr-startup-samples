"""
AWS Bedrock 연결 및 모델 호출 관련 서비스 함수
"""
import boto3
import json
import os
import time
from utils.text_processing import estimate_token_count
from utils.pricing import determine_model_type
from pathlib import Path

def load_prompt_template(template_name):
    """프롬프트 템플릿 파일을 로드합니다.
    
    Args:
        template_name: 템플릿 파일 이름 (확장자 없이)
        
    Returns:
        템플릿 문자열, 파일이 없으면 None
    """
    prompt_path = Path(__file__).parents[1] / "prompts" / f"{template_name}.txt"
    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"프롬프트 템플릿 파일을 찾을 수 없습니다: {prompt_path}")
        return None

def get_bedrock_client():
    """Bedrock 클라이언트를 초기화하고 반환합니다."""
    try:
        # 지정된 리전으로 Bedrock 클라이언트 초기화
        region = os.environ.get("AWS_REGION", "us-east-1")
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        return bedrock_client
    except Exception as e:
        print(f"Bedrock 클라이언트 초기화 오류: {str(e)}")
        return None

def create_model_request(model_id, prompt):
    """모델 ID에 따라 적절한 요청 본문을 생성합니다."""
    model_id_lower = model_id.lower()
    
    # Nova 모델 요청 형식 (Amazon Nova)
    if "nova" in model_id_lower:
        print(f"Amazon Nova 모델 요청 형식 사용: {model_id}")
        
        # Nova 모델은 system 역할을 지원하지 않음 - 모든 내용을 user 메시지에 포함
        system_prompt = "당신은 정밀한 계약서 분석 AI 모델입니다. 주어진 계약서를 분석하여 요청된 필드를 정확히 추출해주세요."
        combined_prompt = system_prompt + "\n\n" + prompt
        
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": combined_prompt}]
                }
            ],
            "inferenceConfig": {
                "max_new_tokens": 4000,
                "temperature": 0.0,
                "top_k": 50
            }
        }
        
        print(f"Nova 요청 본문: {json.dumps(request_body, indent=2)[:300]}...")
        return request_body
    
    # DeepSeek 모델 요청 형식 (DeepSeek)
    elif "deepseek" in model_id_lower:
        print(f"DeepSeek 모델 요청 형식 사용 (ChatML 형식): {model_id}")
        # DeepSeek은 ChatML 형식의 messages 배열 사용
        return {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.0,
            "top_p": 0.9
        }
    
    # Claude 모델 요청 형식 (Anthropic Claude)
    elif "claude" in model_id_lower or "anthropic" in model_id_lower:
        print(f"Claude 모델 요청 형식 사용: {model_id}")
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        
        return request_body
    
    # 기타 모델 요청 형식 (기본)
    else:
        print(f"기본 모델 요청 형식 사용: {model_id}")
        return {
            "prompt": prompt,
            "max_tokens": 2000,
            "temperature": 0.0
        }

def handle_model_response(model_id, response_body):
    """모델에 따라 응답을 처리합니다."""
    model_id_lower = model_id.lower()
    
    try:
        if "amazon.nova" in model_id_lower:
            # Amazon Nova 모델 응답 형식 처리 - 정확한 경로로 수정
            print(f"Nova 모델 응답 처리: {json.dumps(response_body, indent=2)[:200]}...")
            
            if "output" in response_body and "message" in response_body["output"]:
                message = response_body["output"]["message"]
                if "content" in message and isinstance(message["content"], list):
                    response_text = ""
                    for content_item in message["content"]:
                        if "text" in content_item:
                            response_text += content_item["text"]
                    
                    # 응답 텍스트에서 JSON 블록 추출
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                    if json_match:
                        return json_match.group(1)
                    return response_text
            
            # 토큰 사용량 정보 추출 (별도 처리 필요 시)
            if "usage" in response_body:
                print(f"토큰 사용량: {response_body['usage']}")
            
            # 여기까지 왔다면 원하는 구조를 찾지 못한 경우
            return str(response_body)
        
        elif "deepseek" in model_id_lower:
            # DeepSeek R1 모델 응답 형식 처리
            print(f"DeepSeek R1 모델 응답 처리 - 전체 응답 구조: {json.dumps(response_body, indent=2)}")
            
            # 응답 본문 구조 확인
            if "generation" in response_body:
                # Bedrock 최신 API 형식
                print("DeepSeek 응답 형식: 'generation' 키 사용")
                return response_body["generation"]
            elif "text" in response_body:
                # 일부 DeepSeek 응답 형식
                print("DeepSeek 응답 형식: 루트 레벨 'text' 키 사용")
                return response_body["text"]
            elif "choices" in response_body and len(response_body["choices"]) > 0:
                # 최신 ChatML 형식 - messages/choices 구조 
                choice = response_body["choices"][0]
                print(f"DeepSeek 응답 형식: 'choices' 배열 사용 - 첫 번째 choice: {json.dumps(choice, indent=2)}")
                
                # 새로운 ChatML 형식 (message.content 구조)
                if "message" in choice and "content" in choice["message"]:
                    print("DeepSeek 응답 형식: 'choices[0].message.content' 경로 사용")
                    return choice["message"]["content"]
                # 기존 text 직접 접근 방식    
                elif "text" in choice:
                    response_text = choice.get("text", "")
                    print(f"DeepSeek 응답 형식: 'choices[0].text' 경로 사용 - 값: '{response_text}'")
                    
                    # 빈 text 값 처리
                    if response_text == "":
                        print("DeepSeek 응답: 빈 텍스트 반환됨. stop_reason 확인:", choice.get("stop_reason", "unknown"))
                        error_msg = f"DeepSeek 모델이 빈 응답을 반환했습니다. 이유: {choice.get('stop_reason', '알 수 없음')}"
                        return error_msg
                        
                    # Assistant: 접두사 제거
                    if response_text.startswith("Assistant:"):
                        response_text = response_text.replace("Assistant:", "", 1).strip()
                        print(f"DeepSeek 응답: 'Assistant:' 접두사 제거 후: '{response_text[:50]}...'")
                    return response_text
            
            # 응답 구조 자체를 문자열로 반환 (로깅 용도)
            print(f"구조 알 수 없는 DeepSeek 응답: {str(response_body)}")
            return f"알 수 없는 응답 구조: {str(response_body)}"
            
        elif "claude" in model_id_lower or "us.anthropic" in model_id_lower:
            # Anthropic Claude 모델 응답 형식
            if "claude-3-7" in model_id_lower:
                # Claude 3.7 Sonnet 모델 응답 처리
                print(f"Claude 3.7 Sonnet 모델 응답 처리: {json.dumps(response_body, indent=2)[:200]}...")
                response_text = ""
                
                if "content" in response_body and isinstance(response_body["content"], list):
                    for item in response_body["content"]:
                        if item.get("type") == "text":
                            response_text += item.get("text", "")
                
                # 토큰 사용량 정보 (Claude 3.7은 직접 제공)
                if "usage" in response_body:
                    usage = response_body.get("usage", {})
                    prompt_tokens = usage.get("input_tokens", 0)
                    response_tokens = usage.get("output_tokens", 0)
                else:
                    response_tokens = estimate_token_count(response_text, model_id)
                
                return response_text
            else:
                # 기존 Claude 모델 응답 처리
                if "content" in response_body:
                    if isinstance(response_body["content"], list):
                        response_text = ""
                        for item in response_body["content"]:
                            if item.get("type") == "text":
                                response_text += item.get("text", "")
                        return response_text
                    return str(response_body["content"])
                return str(response_body)
            
        else:
            # 알 수 없는 모델 - 응답 본문을 문자열로 반환
            return str(response_body)
            
    except Exception as e:
        print(f"응답 처리 중 오류: {str(e)}")
        # 디버깅 정보 추가
        print(f"모델 ID: {model_id}")
        print(f"응답 본문: {json.dumps(response_body, indent=2)[:500] if isinstance(response_body, dict) else str(response_body)[:500]}")
        return str(response_body)

def invoke_bedrock_model(bedrock_client, model_id, prompt, trace_name=None):
    """AWS Bedrock 모델을 호출하여 응답을 받습니다."""
    if not bedrock_client:
        print("Bedrock 클라이언트가 초기화되지 않았습니다.")
        return None, 0, 0, 0, "Bedrock 클라이언트가 초기화되지 않았습니다."
    
    try:
        # 모델 호출 시작 시간 기록
        start_time = time.time()
        
        # 모델 타입에 따른 요청 바디 생성
        request_body = create_model_request(model_id, prompt)
        
        # 모델 타입 확인
        model_type = determine_model_type(model_id)
        
        # 디버깅 정보 출력
        print(f"모델 ID: {model_id}, 모델 타입: {model_type}")
        print(f"요청 본문 샘플: {json.dumps(request_body)[:300]}...")
        
        # 모델 호출
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 처리
        response_body = json.loads(response.get('body').read())
        
        # DeepSeek 모델이면 전체 응답을 로그로 출력
        if "deepseek" in model_id.lower():
            print("\n====================== DeepSeek 원본 응답 시작 ======================")
            print(json.dumps(response_body, indent=2, ensure_ascii=False))
            print("====================== DeepSeek 원본 응답 끝 ======================\n")
        
        # 모델별 응답 처리
        processed_response = handle_model_response(model_id, response_body)
        
        # 처리 시간 계산
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 토큰 사용량 추정
        prompt_tokens = estimate_token_count(prompt, model_id)
        response_tokens = estimate_token_count(processed_response, model_id)
        
        # 실제 토큰 사용량 (AWS 응답에서 제공되는 경우)
        if model_type == "nova" and "usage" in response_body:
            usage = response_body.get("usage", {})
            prompt_tokens = usage.get("input_tokens", prompt_tokens)
            response_tokens = usage.get("output_tokens", response_tokens)
        elif model_type == "claude" and "claude-3-7" in model_id.lower() and "usage" in response_body:
            usage = response_body.get("usage", {})
            prompt_tokens = usage.get("input_tokens", prompt_tokens)
            response_tokens = usage.get("output_tokens", response_tokens)
        
        return processed_response, processing_time, prompt_tokens, response_tokens, response_body
        
    except Exception as e:
        print(f"모델 호출 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 일관된 반환값 형식 유지
        return None, 0, 0, 0, f"모델 호출 오류: {str(e)}" 