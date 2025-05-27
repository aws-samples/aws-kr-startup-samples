"""
계약서 필드 추출 관련 서비스 함수
"""
import json
import re
import time
from pathlib import Path
from services.bedrock import invoke_bedrock_model

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

def find_source_text_for_fields(full_text, extracted_fields, pages_text, page_starts):
    """추출된 필드에 대한 원본 텍스트 위치를 찾습니다.
    
    Args:
        full_text: 전체 텍스트
        extracted_fields: 추출된 필드 딕셔너리
        pages_text: 페이지별 텍스트 리스트
        page_starts: 각 페이지 시작 위치 리스트
    
    Returns:
        dict: 필드별 원본 텍스트 정보 딕셔너리
    """
    field_sources = {}
    
    # extracted_fields가 None이면 빈 딕셔너리 반환
    if extracted_fields is None:
        return field_sources
    
    # 일반적인 필드 관련 키워드 정의
    field_keywords = {
        "계약 시작일": ["시작일", "개시일", "효력발생일", "계약일", "contract start", "effective date", "commencement date"],
        "계약 종료일": ["종료일", "만료일", "계약기간", "contract end", "termination date", "expiry date"],
        "자동 갱신": ["자동갱신", "자동 갱신", "갱신", "auto renewal", "automatic renewal", "renewal"],
        "갱신 거절 통지 기간": ["통지기간", "사전통지", "해지통보", "해지 통보", "갱신거절", "notice period", "prior notice", "termination notice"]
    }
    
    # 각 추출된 필드에 대해 관련 텍스트 스니펫 찾기
    for field_name, field_value in extracted_fields.items():
        if field_value == "찾을 수 없음" or not field_value:
            field_sources[field_name] = []
            continue
            
        # 필드 값이 문자열이 아니면 건너뛰기
        if not isinstance(field_value, str):
            field_sources[field_name] = []
            continue
            
        # 이 필드에 대한 키워드 가져오기
        keywords = field_keywords.get(field_name, [])
        
        # 너무 일반적이지 않다면 필드 값 자체도 키워드로 사용
        if len(field_value) > 3 and field_value not in ["예", "아니오", "Yes", "No"]:
            keywords.append(field_value)
        
        # 키워드와 값을 모두 포함하는 스니펫 찾기
        snippets = []
        
        for keyword in keywords:
            # 이 키워드의 모든 출현 위치 찾기
            for match in re.finditer(re.escape(keyword), full_text, re.IGNORECASE):
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(full_text), match.end() + 100)
                
                # 주변 컨텍스트와 함께 스니펫 가져오기
                snippet = full_text[start_pos:end_pos]
                
                # 페이지 번호 결정
                page_num = 0
                for i, pos in enumerate(page_starts):
                    if pos > match.start():
                        page_num = i
                        break
                if page_num > 0:
                    page_num -= 1  # 0 인덱싱 조정
                
                # 페이지 정보와 함께 스니펫 추가
                snippets.append({
                    "text": snippet,
                    "page": page_num,
                    "relevance": 1.0 if field_value.lower() in snippet.lower() else 0.5
                })
        
        # 중복 제거 및 관련성별 정렬
        unique_snippets = []
        seen_texts = set()
        for snippet in sorted(snippets, key=lambda x: -x["relevance"]):
            # 중복 제거를 위한 정규화 버전 생성
            normalized = re.sub(r'\s+', ' ', snippet["text"]).strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_snippets.append(snippet)
                # 가장 관련성 높은 스니펫 최대 3개로 제한
                if len(unique_snippets) >= 3:
                    break
        
        field_sources[field_name] = unique_snippets
    
    return field_sources

def extract_contract_fields_with_bedrock(bedrock_client, text, model_id):
    """Bedrock 모델을 사용하여 계약서 필드를 추출합니다.
    
    Args:
        bedrock_client: AWS Bedrock 클라이언트
        text: 추출할 텍스트
        model_id: 사용할 모델 ID
    
    Returns:
        tuple: (추출된 필드, 처리 시간, 입력 토큰, 출력 토큰, 원본 응답, 모델이 제공한 출처 텍스트)
    """
    try:
        # 프롬프트 템플릿 로드
        prompt_template = load_prompt_template("extraction")
        if not prompt_template:
            return None, 0, 0, 0, "프롬프트 템플릿을 로드할 수 없습니다", {}
        
        # 프롬프트에 텍스트 삽입
        prompt = prompt_template.replace("{text}", text[:8000])
        
        # 실제 모델 호출 시간은 invoke_bedrock_model 내에서 계산됨
        processed_response, processing_time, prompt_tokens, response_tokens, raw_response = invoke_bedrock_model(
            bedrock_client, 
            model_id, 
            prompt
        )
        
        # 응답이 없으면 None 반환
        if not processed_response:
            return None, processing_time, prompt_tokens, response_tokens, raw_response, {}
        
        try:
            # JSON 응답 파싱 시도
            try:
                # 먼저 응답이 이미 JSON인지 확인
                json_response = json.loads(processed_response)
            except json.JSONDecodeError:
                # JSON이 아닌 경우, JSON 블록 찾기
                json_match = re.search(r'```json\s*(.*?)\s*```', processed_response, re.DOTALL)
                if json_match:
                    processed_response = json_match.group(1).strip()
                
                # 중괄호 내용 찾기
                json_obj_match = re.search(r'({[\s\S]*})', processed_response, re.DOTALL)
                if json_obj_match:
                    processed_response = json_obj_match.group(1).strip()
                
                # 다시 JSON 파싱 시도
                json_response = json.loads(processed_response)
            
            # 핵심 필드 추출
            extracted_fields = {
                "계약 시작일": json_response.get("계약 시작일", "찾을 수 없음"),
                "계약 종료일": json_response.get("계약 종료일", "찾을 수 없음"),
                "자동 갱신": json_response.get("자동 갱신", "찾을 수 없음"),
                "갱신 거절 통지 기간": json_response.get("갱신 거절 통지 기간", "찾을 수 없음"),
                "추천 계약 필드": json_response.get("추천 계약 필드", [])
            }
            
            # 모델이 제공한 출처 텍스트 추출
            model_source_texts = json_response.get("추천 계약 필드 출처", {})
            
            # 추천 필드에서 필드명만 추출하여 출처 텍스트 사전 완성
            for field in extracted_fields.get("추천 계약 필드", []):
                field_name = field.get("필드명", "")
                if field_name and field_name not in model_source_texts:
                    # 출처 정보에서 텍스트 가져오기 시도
                    source_info = field.get("출처", "")
                    if source_info:
                        model_source_texts[field_name] = f"출처: {source_info}"
            
            return extracted_fields, processing_time, prompt_tokens, response_tokens, processed_response, model_source_texts
            
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"JSON 파싱 오류: {str(e)}")
            print(f"원본 응답: {processed_response[:500]}")
            return None, processing_time, prompt_tokens, response_tokens, processed_response, {}
            
    except Exception as e:
        print(f"필드 추출 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, 0, 0, 0, str(e), {} 