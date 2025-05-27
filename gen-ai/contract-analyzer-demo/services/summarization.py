"""
계약서 요약 서비스
"""
import json
import time
import streamlit as st
from pathlib import Path
from services.bedrock import invoke_bedrock_model
import re

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
        st.error(f"프롬프트 템플릿 파일을 찾을 수 없습니다: {prompt_path}")
        return None

def summarize_contract_with_bedrock(bedrock_client, text, model_id):
    """Bedrock 모델을 사용하여 계약서를 요약합니다.
    
    Args:
        bedrock_client: Bedrock 클라이언트
        text: 계약서 텍스트
        model_id: 모델 ID
        
    Returns:
        summary, processing_time, prompt_tokens, response_tokens, raw_response
    """
    # 요약 프롬프트 템플릿 로드 - 모든 모델에 동일한 템플릿 사용
    prompt_template = load_prompt_template("summarization")
    if not prompt_template:
        return None, 0, 0, 0, "프롬프트 템플릿을 로드할 수 없습니다"
    
    # 프롬프트에 텍스트 삽입
    prompt = prompt_template.replace("{text}", text[:8000])

    start_time = time.time()
    
    try:
        # 모델 호출 - 모델별 요청 형식과 응답 처리를 invoke_bedrock_model에서 처리
        processed_response, processing_time, prompt_tokens, response_tokens, raw_response = invoke_bedrock_model(
            bedrock_client, 
            model_id, 
            prompt
        )
        
        # DeepSeek 모델인 경우 처리된 응답과 원본 응답 비교 로깅
        if "deepseek" in model_id.lower():
            print("\n====================== 요약 서비스에서 DeepSeek 응답 확인 ======================")
            print(f"처리된 응답: {processed_response}")
            print(f"원본 응답 키 목록: {list(raw_response.keys()) if isinstance(raw_response, dict) else 'dict 아님'}")
            print("====================== 요약 서비스 DeepSeek 응답 확인 끝 ======================\n")
        
        # 응답이 없는 경우 처리
        if processed_response is None:
            print(f"모델에서 응답을 받지 못했습니다: {raw_response}")
            return None, processing_time, prompt_tokens, response_tokens, raw_response
            
        # 디버깅 정보 출력
        print(f"모델 ID: {model_id}")
        print(f"처리된 응답 (처음 200자): {processed_response[:200] if processed_response else 'None'}")
        
        if not processed_response:
            return None, processing_time, prompt_tokens, response_tokens, raw_response
            
        # JSON 응답 추출 시도
        try:
            # 응답에서 JSON 부분 추출
            json_str = processed_response
            
            print(f"JSON 파싱 시작 - 원본 응답 (처음 100자): {processed_response[:100] if processed_response else 'None'}")
            
            # Assistant: 접두사 제거
            if isinstance(json_str, str) and json_str.startswith("Assistant:"):
                json_str = json_str.replace("Assistant:", "", 1).strip()
                print(f"'Assistant:' 접두사 제거 후 (처음 100자): {json_str[:100]}")
            
            # JSON 코드 블록 추출 시도
            if isinstance(json_str, str):
                # ```json 형식 코드 블록
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                    print(f"```json 블록 추출 후 (처음 100자): {json_str[:100]}")
                # ``` 형식 코드 블록
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                    print(f"``` 블록 추출 후 (처음 100자): {json_str[:100]}")
            
            # DeepSeek 오류 메시지인 경우
            if isinstance(json_str, str) and "DeepSeek 모델이 빈 응답을 반환했습니다" in json_str:
                print(f"DeepSeek 모델 오류 감지: {json_str}")
                return {
                    "summary": "모델이 응답을 생성하지 못했습니다.",
                    "contract_type": "오류",
                    "parties": ["알 수 없음"],
                    "key_points": [json_str]
                }, processing_time, prompt_tokens, response_tokens, processed_response
            
            # 디버깅
            print(f"최종 JSON 파싱 시도 (처음 100자): {json_str[:100] if isinstance(json_str, str) else 'None'}")
                
            # JSON 파싱 시도 - 기본 방식
            try:
                summary_data = json.loads(json_str)
                print(f"JSON 파싱 성공 - 결과: {json.dumps(summary_data, indent=2, ensure_ascii=False)[:300]}...")
                return summary_data, processing_time, prompt_tokens, response_tokens, processed_response
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 실패: {str(e)}")
                
                # 대안 1: 배열 패턴 찾기
                if isinstance(json_str, str):
                    array_match = re.search(r'(\[\s*{[\s\S]*?}\s*\])', json_str, re.DOTALL)
                    if array_match:
                        try:
                            match_str = array_match.group(1).strip()
                            print(f"배열 패턴 매칭 시도: {match_str[:100]}...")
                            summary_data = json.loads(match_str)
                            print("배열 패턴 JSON 파싱 성공")
                            return summary_data, processing_time, prompt_tokens, response_tokens, processed_response
                        except json.JSONDecodeError as e2:
                            print(f"배열 패턴 JSON 파싱 실패: {str(e2)}")
                
                # 모든 파싱 시도 실패
                print(f"모든 JSON 파싱 시도 실패 - 처리된 응답: {processed_response[:500]}")
                
                # JSON 파싱 실패 시 텍스트 형식으로 가공하여 반환
                return {
                    "summary": processed_response[:500] if processed_response else "응답 없음",
                    "contract_type": "알 수 없음",
                    "parties": ["알 수 없음"],
                    "key_points": ["요약을 생성할 수 없습니다. 다른 모델을 시도해보세요."]
                }, processing_time, prompt_tokens, response_tokens, processed_response
                
        except Exception as e:
            print(f"JSON 파싱 중 예외 발생: {str(e)}, 타입: {type(e)}")
            print(f"응답 타입: {type(processed_response)}")
            
            # 예외 발생 시 기본 응답 반환
            return {
                "summary": "JSON 파싱 중 오류가 발생했습니다.",
                "contract_type": "오류",
                "parties": ["알 수 없음"],
                "key_points": [f"오류 내용: {str(e)}"]
            }, processing_time, prompt_tokens, response_tokens, processed_response
            
    except Exception as e:
        print(f"모델 호출 중 오류 발생: {str(e)}")
        print(f"모델 ID: {model_id}, 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, 0, 0, 0, str(e) 