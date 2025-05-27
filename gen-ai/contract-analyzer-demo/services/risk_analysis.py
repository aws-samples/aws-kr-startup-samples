"""
계약서 위험 분석 관련 서비스 함수
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

def analyze_contract_risks(bedrock_client, text, model_id="us.deepseek.r1-v1:0"):
    """AWS Bedrock 모델을 사용하여 계약서의 위험 요소를 분석합니다.
    
    Args:
        bedrock_client: AWS Bedrock 클라이언트
        text: 분석할 텍스트
        model_id: 사용할 모델 ID, 기본값은 DeepSeek R1
    
    Returns:
        tuple: (위험 분석 결과, 처리 시간, 입력 토큰, 출력 토큰, 원본 응답)
    """
    try:
        # 모든 모델에 대해 동일한 프롬프트 템플릿 사용
        prompt_template = load_prompt_template("risk_analysis")
        if not prompt_template:
            return None, 0, 0, 0, "프롬프트 템플릿을 로드할 수 없습니다"
        
        # 프롬프트에 텍스트 삽입
        prompt = prompt_template.replace("{text}", text[:8000])
        
        # 모델 타입 확인 (DeepSeek 모델 특별 처리를 위해)
        is_deepseek = "deepseek" in model_id.lower()
        
        # 모델 호출
        try:
            processed_response, processing_time, prompt_tokens, response_tokens, raw_response = invoke_bedrock_model(
                bedrock_client, 
                model_id, 
                prompt
            )
            
            # DeepSeek 모델인 경우 처리된 응답과 원본 응답 비교 로깅
            if is_deepseek:
                print("\n====================== 위험 분석 서비스에서 DeepSeek 응답 확인 ======================")
                print(f"처리된 응답: {processed_response}")
                print(f"원본 응답 키 목록: {list(raw_response.keys()) if isinstance(raw_response, dict) else 'dict 아님'}")
                print("====================== 위험 분석 서비스 DeepSeek 응답 확인 끝 ======================\n")
            
            # 응답이 없는 경우 처리
            if processed_response is None:
                print(f"모델에서 응답을 받지 못했습니다: {raw_response}")
                return None, processing_time, prompt_tokens, response_tokens, raw_response
                
        except Exception as e:
            print(f"모델 호출 오류 상세: {str(e)}")
            return None, 0, 0, 0, f"모델 호출 오류: {str(e)}"
        
        # 디버깅 정보 출력
        print(f"모델 ID: {model_id}")
        print(f"처리된 응답 (처음 200자): {processed_response[:200] if processed_response else 'None'}")
        
        try:
            # JSON 응답 파싱 시도
            risk_analysis = []
            
            # DeepSeek 모델 응답 처리
            if is_deepseek and processed_response:
                # 'Assistant:' 접두사 제거
                if isinstance(processed_response, str) and processed_response.startswith("Assistant:"):
                    processed_response = processed_response.replace("Assistant:", "", 1).strip()
                
                # 모델 출력에 JSON 블록만 있을 경우를 처리
                if isinstance(processed_response, str) and processed_response.startswith("[") and processed_response.endswith("]"):
                    try:
                        risk_analysis = json.loads(processed_response)
                        print("DeepSeek 모델에서 JSON 배열 직접 파싱 성공")
                    except json.JSONDecodeError:
                        print("DeepSeek 모델 JSON 배열 직접 파싱 실패")
                
                # 코드 블록으로 감싸진 JSON 찾기
                if not risk_analysis and isinstance(processed_response, str):
                    # ```json 형식 코드 블록
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', processed_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1).strip()
                        try:
                            risk_analysis = json.loads(json_str)
                            print("DeepSeek 모델에서 코드 블록 내 JSON 파싱 성공")
                        except json.JSONDecodeError:
                            print(f"DeepSeek 모델 코드 블록 JSON 파싱 실패: {json_str[:100]}")
                
                # 중괄호로 둘러싸인 배열 찾기
                if not risk_analysis and isinstance(processed_response, str):
                    array_match = re.search(r'(\[\s*{[\s\S]*?}\s*\])', processed_response, re.DOTALL)
                    if array_match:
                        try:
                            json_str = array_match.group(1).strip()
                            risk_analysis = json.loads(json_str)
                            print("DeepSeek 모델에서 배열 패턴 매칭으로 JSON 파싱 성공")
                        except json.JSONDecodeError:
                            print(f"DeepSeek 모델 배열 패턴 JSON 파싱 실패: {json_str[:100]}")
            
            # 기존 JSON 파싱 로직
            if not risk_analysis:
                try:
                    # 먼저 응답이 이미 JSON인지 확인
                    risk_analysis = json.loads(processed_response)
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 추출 시도
                    # JSON 블록 찾기
                    json_match = re.search(r'```json\s*(.*?)\s*```', processed_response, re.DOTALL)
                    if json_match:
                        try:
                            risk_analysis = json.loads(json_match.group(1).strip())
                        except json.JSONDecodeError:
                            pass
                    
                    # 중괄호 배열 찾기
                    if not risk_analysis:
                        array_match = re.search(r'(\[\s*{.*}\s*\])', processed_response, re.DOTALL)
                        if array_match:
                            try:
                                risk_analysis = json.loads(array_match.group(1).strip())
                            except json.JSONDecodeError:
                                pass
            
            # 배열이 아니거나 비어있으면 딕셔너리인지 확인
            if not isinstance(risk_analysis, list) or not risk_analysis:
                if isinstance(risk_analysis, dict) and "risks" in risk_analysis:
                    risk_analysis = risk_analysis.get("risks", [])
                
                # 여전히 배열이 아니거나 비어있으면 텍스트 파싱
                if not isinstance(risk_analysis, list) or not risk_analysis:
                    # 간단한 텍스트 파싱 시도
                    risks = []
                    sections = re.split(r'\n\s*(?:\d+\.\s+|위험\s+\d+:\s+)', processed_response)
                    
                    for section in sections:
                        if len(section.strip()) > 50:  # 충분히 긴 섹션만 처리
                            risk = {}
                            
                            # 카테고리 추출 시도
                            category_match = re.search(r'카테고리:\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                            if category_match:
                                risk["category"] = category_match.group(1).strip()
                            
                            # 제목 추출 시도
                            title_match = re.search(r'제목:\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                            if title_match:
                                risk["title"] = title_match.group(1).strip()
                            elif "category" in risk:
                                risk["title"] = risk["category"]  # 카테고리를 제목으로 사용
                            
                            # 위험 수준 추출 시도
                            level_match = re.search(r'위험\s*수준:\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
                            if level_match:
                                risk["risk_level"] = level_match.group(1).strip()
                            
                            # 설명 추출 시도
                            desc_match = re.search(r'설명:\s*(.*?)(?:권장|$)', section, re.DOTALL | re.IGNORECASE)
                            if desc_match:
                                risk["description"] = desc_match.group(1).strip()
                            
                            # 권장사항 추출 시도
                            rec_match = re.search(r'권장[^:]*:\s*(.*?)(?:출처|$)', section, re.DOTALL | re.IGNORECASE)
                            if rec_match:
                                risk["recommendation"] = rec_match.group(1).strip()
                            
                            # 출처 추출 시도
                            source_match = re.search(r'출처:\s*(.*?)(?:\n|$)', section, re.DOTALL | re.IGNORECASE)
                            if source_match:
                                risk["source"] = source_match.group(1).strip()
                            
                            # 최소한 제목과 설명이 있는 경우만 추가
                            if ("title" in risk or "category" in risk) and "description" in risk:
                                # 제목이 없으면 설명의 첫 부분을 제목으로
                                if "title" not in risk and "description" in risk:
                                    desc = risk["description"]
                                    risk["title"] = desc[:min(40, len(desc))] + ("..." if len(desc) > 40 else "")
                                
                                # 위험 수준이 없으면 '중간'으로 기본 설정
                                if "risk_level" not in risk:
                                    risk["risk_level"] = "중간"
                                    
                                risks.append(risk)
                    
                    risk_analysis = risks
            
            # 최종 검증 및 정제
            validated_risks = []
            for risk in risk_analysis:
                if isinstance(risk, dict):
                    # 필수 필드 확인 및 기본값 설정
                    validated_risk = {
                        "category": risk.get("category", "기타"),
                        "title": risk.get("title", "미상"),
                        "risk_level": risk.get("risk_level", "중간"),
                        "description": risk.get("description", ""),
                        "recommendation": risk.get("recommendation", ""),
                        "source": risk.get("source", "")
                    }
                    
                    # 위험 수준 정규화
                    level = validated_risk["risk_level"].lower()
                    if "높" in level or "high" in level:
                        validated_risk["risk_level"] = "높음"
                    elif "중" in level or "medium" in level:
                        validated_risk["risk_level"] = "중간"
                    elif "낮" in level or "low" in level:
                        validated_risk["risk_level"] = "낮음"
                    
                    validated_risks.append(validated_risk)
            
            # 빈 분석 결과인 경우 기본 메시지 추가
            if not validated_risks:
                validated_risks = [{
                    "category": "분석 결과",
                    "title": "위험 요소 식별 불가",
                    "risk_level": "알 수 없음",
                    "description": "계약서 텍스트에서 특정 위험 요소를 식별할 수 없습니다. 계약서 전문을 법률 전문가에게 검토 받으세요.",
                    "recommendation": "계약 체결 전 법률 전문가의 검토를 받으세요.",
                    "source": ""
                }]
            
            return validated_risks, processing_time, prompt_tokens, response_tokens, processed_response
            
        except Exception as e:
            print(f"위험 분석 결과 처리 오류: {str(e)}")
            print(f"원본 응답: {processed_response[:500]}")
            return None, processing_time, prompt_tokens, response_tokens, processed_response
            
    except Exception as e:
        print(f"위험 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, 0, 0, 0, str(e)