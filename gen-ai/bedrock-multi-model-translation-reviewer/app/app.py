import streamlit as st
import boto3
import json
import time
from typing import List, Dict, Any

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

MODELS = {
    "us.amazon.nova-pro-v1:0": "Nova Pro",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0": "Claude 3.5 Sonnet",
    "anthropic.claude-3-sonnet-20240229-v1:0": "Claude 3 Sonnet",
    "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku"
}

# 검수에 사용할 모델
REVIEW_MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

def detect_language(text: str) -> str:
    korean_chars = sum(1 for char in text if ord('가') <= ord(char) <= ord('힣'))
    return "ko" if korean_chars > 0 else "en"

def get_translation_prompt(text: str, source_lang: str, target_lang: str) -> str:
    lang_map = {"ko": "한국어", "en": "영어"}
    source = lang_map[source_lang]
    target = lang_map[target_lang]
    
    prompt = f"""당신은 전문 번역가입니다. 다음 {source} 텍스트를 {target}로 정확하게 번역해주세요.
    
중요한 지침:
1. 오역이 없어야 합니다.
2. 자연스러운 표현을 사용해야 합니다.
3. 제품명이나 브랜드 이름은 변경하지 마세요.
4. 번역 이외의 대화나 설명은 하지 마세요.
5. 원문의 의미와 뉘앙스를 최대한 유지하세요.
6. "실리콘투": "siliconii"로 번역하세요.

번역할 텍스트:
{text}

다른 말은 하지말고 번역 결과만 출력하세요.
"""
    return prompt

def get_review_prompt(text: str, translated_text: str) -> str:
    source_lang = detect_language(text)
    target_lang = "en" if source_lang == "ko" else "ko"
    
    lang_map = {"ko": "한국어", "en": "영어"}
    source = lang_map[source_lang]
    target = lang_map[target_lang]
    
    prompt = f"""당신은 전문 번역가이자 품질 검수자입니다. 다음 {source}에서 {target}로 번역된 텍스트를 검수해주세요.
    
원본 텍스트:
{text}

번역된 텍스트:
{translated_text}

번역을 검수하고 다음 사항들만 간결하게 확인해주세요:
1. 문맥상 어색한 표현
2. 오탈자나 문법적 오류
3. 오역
4. 개선 제안

핵심적인 내용만 간결하게 작성하고, 문제가 없으면 "번역이 적절합니다."라고만 답변하세요.
"""
    return prompt

def translate_with_bedrock(text: str, model_id: str) -> Dict[str, Any]:
    source_lang = detect_language(text)
    target_lang = "en" if source_lang == "ko" else "ko"
    
    prompt = get_translation_prompt(text, source_lang, target_lang)
    
    # 모델별 공통 메시지 구조
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": prompt
                }
            ]
        }
    ]
    
    try:
        # 시작 시간 기록
        start_time = time.time()
        
        # 모델별 요청 파라미터 설정
        kwargs = {
            "modelId": model_id,
            "messages": messages
        }
        
        # 모델별 인퍼런스 구성 추가
        if "nova" in model_id:
            # Nova Pro에 대한 인퍼런스 구성
            kwargs["inferenceConfig"] = {"maxTokens": 1000}
        elif "anthropic" in model_id:
            pass
            
        # Bedrock Converse API 호출
        response = bedrock_runtime.converse(**kwargs)
        
        # 응답 처리
        result_text = response["output"]["message"]["content"][0]["text"]
        
        token_usage = response.get("usage", {})
        latency_ms = response.get("metrics", {}).get("latencyMs", 0)
        
        return {
            "text": result_text,
            "input_tokens": token_usage.get("inputTokens", 0),
            "output_tokens": token_usage.get("outputTokens", 0),
            "total_tokens": token_usage.get("totalTokens", 0),
            "latency_ms": latency_ms,
            "latency_s": round(latency_ms / 1000, 2) if latency_ms else round(time.time() - start_time, 2)
        }
    except Exception as e:
        return {
            "text": f"오류 발생: {str(e)}",
            "input_tokens": 0,
            "output_tokens": 0, 
            "total_tokens": 0,
            "latency_ms": 0,
            "latency_s": 0
        }

def review_translation(original_text: str, translated_text: str) -> Dict[str, Any]:
    prompt = get_review_prompt(original_text, translated_text)
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": prompt
                }
            ]
        }
    ]
    
    try:
        start_time = time.time()
        
        response = bedrock_runtime.converse(
            modelId=REVIEW_MODEL,
            messages=messages
        )
        
        result_text = response["output"]["message"]["content"][0]["text"]
        
        token_usage = response.get("usage", {})
        latency_ms = response.get("metrics", {}).get("latencyMs", 0)
        
        return {
            "text": result_text,
            "input_tokens": token_usage.get("inputTokens", 0),
            "output_tokens": token_usage.get("outputTokens", 0),
            "total_tokens": token_usage.get("totalTokens", 0),
            "latency_ms": latency_ms,
            "latency_s": round(latency_ms / 1000, 2) if latency_ms else round(time.time() - start_time, 2)
        }
    except Exception as e:
        return {
            "text": f"검수 중 오류 발생: {str(e)}",
            "input_tokens": 0,
            "output_tokens": 0, 
            "total_tokens": 0,
            "latency_ms": 0,
            "latency_s": 0
        }

def main():
    st.set_page_config(
        page_title="Amazon Bedrock 번역기 데모",
        page_icon="🌍",
        layout="wide"
    )
    
    st.markdown("""
    <style>
        /* 스크롤바 커스터마이징 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        /* 초록색 토큰 및 지연시간 메트릭 스타일 */
        .green-metric {
            color: #28a745 !important;
            font-weight: bold;
        }
        
        /* 검수 결과 컨테이너 스타일 */
        .review-container {
            height: 200px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #e6e6e6;
            border-radius: 5px;
            background-color: #f9f9f9;
            margin-bottom: 20px;
        }
        
        /* 모델 섹션 컨테이너 스타일 */
        .model-container {
            background-color: #1E1E1E;
            border-radius: 5px;
            padding: 10px; /* 패딩 축소 */
            margin-bottom: 10px; /* 마진 축소 */
            height: 650px; /* 높이 축소 */
            overflow-y: auto;
        }
        
        /* 번역 결과 컨테이너 스타일 */
        .translation-container {
            height: 180px; /* 높이 축소 */
            overflow-y: auto;
            padding: 8px; /* 패딩 축소 */
            border: 1px solid #333;
            border-radius: 5px;
            background-color: #2d2d2d;
            margin-bottom: 8px; /* 마진 축소 */
        }
        
        /* 검수 결과 영역 스타일 */
        .review-result-container {
            height: 160px; /* 높이 축소 */
            overflow-y: auto;
            padding: 8px; /* 패딩 축소 */
            border: 1px solid #333;
            border-radius: 5px;
            background-color: #2d2d2d;
            margin-bottom: 10px; /* 마진 축소 */
            color: white;
        }
        
        /* 검수 결과 영역 숨김 상태 스타일 */
        .review-result-hidden {
            height: 160px; /* 높이 축소 */
            padding: 8px; /* 패딩 축소 */
            border: 1px solid #333;
            border-radius: 5px;
            background-color: #2d2d2d;
            margin-bottom: 10px; /* 마진 축소 */
            color: #555;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* 여백 공간 줄이기 */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* 상단 헤더 여백 줄이기 */
        .main .block-container {
            margin-top: -2rem;
        }
        
        /* 컬럼 간 간격 축소 */
        .row-widget {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        /* 타이틀과 헤더 간격 조정 */
        h1, h2, h3, h4 {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* 입력 필드 간격 축소 */
        .stTextArea {
            margin-bottom: 0.5rem !important;
        }
        
        /* 버튼 여백 축소 */
        .stButton > button {
            margin-top: 0.3rem;
            margin-bottom: 0.5rem;
        }
        
        /* 메트릭 컬럼 여백 조정 */
        div.column > div {
            padding-top: 0.2rem !important;
            padding-bottom: 0.2rem !important;
        }
        
        /* 헤더 감추기 (선택적) */
        header {
            visibility: hidden;
        }
        
        /* 푸터 감추기 (선택적) */
        footer {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""
    if 'translation_results' not in st.session_state:
        st.session_state.translation_results = {}
    if 'review_results' not in st.session_state:
        st.session_state.review_results = {}
    # 검수 진행 중 상태 추가
    if 'reviewing_models' not in st.session_state:
        st.session_state.reviewing_models = set()
    
    st.title("Amazon Bedrock 번역기 데모")
    st.markdown("영어 ↔ 한국어 번역 비교 데모입니다. 각 모델별 번역 결과를 비교해보세요.")
    
    # 사용자 입력 텍스트 영역
    user_input = st.text_area("번역할 텍스트를 입력하세요:", 
                              value=st.session_state.user_input, 
                              height=150,
                              key="input_text")
    
    # 번역 버튼
    translate_button = st.button("번역하기")
    
    # 번역 버튼 클릭 시 처리
    if translate_button and user_input:
        st.session_state.user_input = user_input
        results = {}
        
        # 진행 상황 표시
        progress_container = st.empty()
        status_text = st.empty()
        
        with progress_container.container():
            progress_bar = st.progress(0)
            
            for i, (model_id, model_name) in enumerate(MODELS.items()):
                status_text.text(f"{model_name} 모델로 번역 중...")
                results[model_id] = translate_with_bedrock(user_input, model_id)
                progress_bar.progress((i + 1) / len(MODELS))
        
        status_text.text("번역 완료!")
        st.session_state.translation_results = results
    
    # 결과 표시 부분
    if st.session_state.translation_results:
        col1, col2 = st.columns(2)
        model_ids = list(MODELS.keys())
        
        # 왼쪽 열 (첫 두 모델)
        with col1:
            for idx in range(0, 2):
                if idx < len(model_ids):
                    model_id = model_ids[idx]
                    model_name = MODELS[model_id]
                    result = st.session_state.translation_results[model_id]
                    
                    # 고정된 높이의 모델 컨테이너 생성
                    with st.container():
                        st.markdown(f"""
                        <div class="model-container">
                            <h3 style="color: white;">{model_name}</h3>
                            <div class="translation-container">
                                <p style="color: white;">{result["text"]}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 토큰 사용량과 지연시간 표시 (초록색으로)
                        col1_metrics, col2_metrics, col3_metrics = st.columns(3)
                        with col1_metrics:
                            st.markdown(f"<p style='color: white;'>입력 토큰</p><p style='color:#28a745; font-weight:bold;'>{result['input_tokens']:,}</p>", unsafe_allow_html=True)
                        with col2_metrics:
                            st.markdown(f"<p style='color: white;'>출력 토큰</p><p style='color:#28a745; font-weight:bold;'>{result['output_tokens']:,}</p>", unsafe_allow_html=True)
                        with col3_metrics:
                            st.markdown(f"<p style='color: white;'>지연시간</p><p style='color:#28a745; font-weight:bold;'>{result['latency_s']}초</p>", unsafe_allow_html=True)
                        
                        # 검수 버튼 (진행 중이면 비활성화)
                        is_reviewing = model_id in st.session_state.reviewing_models
                        button_text = "검수 진행 중..." if is_reviewing else f"{model_name} 번역 검수하기"
                        button_disabled = is_reviewing
                        review_button = st.button(button_text, key=f"review_btn_{idx}", disabled=button_disabled)
                        
                        # 검수 결과 영역 (항상 표시)
                        st.markdown(f"""
                            <h4 style="color: white;">{model_name} 번역 검수 결과</h4>
                        """, unsafe_allow_html=True)
                        
                        # 검수 진행 중인 경우 로딩 표시
                        if is_reviewing:
                            result_container = st.empty()
                            result_container.markdown(f"""
                                <div class="review-result-hidden">
                                    <p style="color: white;">검수 진행 중...</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 빈 메트릭 영역 표시
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            
                        # 검수 결과가 있으면 내용 표시, 없으면 placeholder 표시
                        elif model_id in st.session_state.review_results:
                            review_result = st.session_state.review_results[model_id]
                            st.markdown(f"""
                                <div class="review-result-container">
                                    {review_result["text"]}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 검수 토큰 사용량과 지연시간 표시 (초록색으로)
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#28a745; font-weight:bold;'>{review_result['input_tokens']:,}</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#28a745; font-weight:bold;'>{review_result['output_tokens']:,}</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#28a745; font-weight:bold;'>{review_result['latency_s']}초</p>", unsafe_allow_html=True)
                        else:
                            # 검수 결과가 없는 경우 placeholder 표시
                            st.markdown(f"""
                                <div class="review-result-hidden">
                                    검수 결과가 여기에 표시됩니다
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 빈 메트릭 영역도 유지하여 레이아웃 일관성 확보
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                        
                        # 컨테이너 닫기
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # 검수 버튼 클릭 처리
                        if review_button:
                            # 검수 진행 중 상태로 설정
                            st.session_state.reviewing_models.add(model_id)
                            st.rerun()
        
        # 오른쪽 열 (다음 두 모델)
        with col2:
            for idx in range(2, 4):
                if idx < len(model_ids):
                    model_id = model_ids[idx]
                    model_name = MODELS[model_id]
                    result = st.session_state.translation_results[model_id]
                    
                    # 고정된 높이의 모델 컨테이너 생성
                    with st.container():
                        st.markdown(f"""
                        <div class="model-container">
                            <h3 style="color: white;">{model_name}</h3>
                            <div class="translation-container">
                                <p style="color: white;">{result["text"]}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 토큰 사용량과 지연시간 표시 (초록색으로)
                        col1_metrics, col2_metrics, col3_metrics = st.columns(3)
                        with col1_metrics:
                            st.markdown(f"<p style='color: white;'>입력 토큰</p><p style='color:#28a745; font-weight:bold;'>{result['input_tokens']:,}</p>", unsafe_allow_html=True)
                        with col2_metrics:
                            st.markdown(f"<p style='color: white;'>출력 토큰</p><p style='color:#28a745; font-weight:bold;'>{result['output_tokens']:,}</p>", unsafe_allow_html=True)
                        with col3_metrics:
                            st.markdown(f"<p style='color: white;'>지연시간</p><p style='color:#28a745; font-weight:bold;'>{result['latency_s']}초</p>", unsafe_allow_html=True)
                        
                        # 검수 버튼 (진행 중이면 비활성화)
                        is_reviewing = model_id in st.session_state.reviewing_models
                        button_text = "검수 진행 중..." if is_reviewing else f"{model_name} 번역 검수하기"
                        button_disabled = is_reviewing
                        review_button = st.button(button_text, key=f"review_btn_{idx}", disabled=button_disabled)
                        
                        # 검수 결과 영역 (항상 표시)
                        st.markdown(f"""
                            <h4 style="color: white;">{model_name} 번역 검수 결과</h4>
                        """, unsafe_allow_html=True)
                        
                        # 검수 진행 중인 경우 로딩 표시
                        if is_reviewing:
                            result_container = st.empty()
                            result_container.markdown(f"""
                                <div class="review-result-hidden">
                                    <p style="color: white;">검수 진행 중...</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 빈 메트릭 영역 표시
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            
                        # 검수 결과가 있으면 내용 표시, 없으면 placeholder 표시
                        elif model_id in st.session_state.review_results:
                            review_result = st.session_state.review_results[model_id]
                            st.markdown(f"""
                                <div class="review-result-container">
                                    {review_result["text"]}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 검수 토큰 사용량과 지연시간 표시 (초록색으로)
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#28a745; font-weight:bold;'>{review_result['input_tokens']:,}</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#28a745; font-weight:bold;'>{review_result['output_tokens']:,}</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#28a745; font-weight:bold;'>{review_result['latency_s']}초</p>", unsafe_allow_html=True)
                        else:
                            # 검수 결과가 없는 경우 placeholder 표시
                            st.markdown(f"""
                                <div class="review-result-hidden">
                                    검수 결과가 여기에 표시됩니다
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 빈 메트릭 영역도 유지하여 레이아웃 일관성 확보
                            review_col1, review_col2, review_col3 = st.columns(3)
                            with review_col1:
                                st.markdown(f"<p style='color: white;'>검수 입력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col2:
                                st.markdown(f"<p style='color: white;'>검수 출력 토큰</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                            with review_col3:
                                st.markdown(f"<p style='color: white;'>검수 지연시간</p><p style='color:#555;'>-</p>", unsafe_allow_html=True)
                        
                        # 컨테이너 닫기
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # 검수 버튼 클릭 처리
                        if review_button:
                            # 검수 진행 중 상태로 설정
                            st.session_state.reviewing_models.add(model_id)
                            st.rerun()

# 메인 루프 외부에서 검수 진행 중인 모델들에 대한 처리
if st.session_state.get('reviewing_models'):
    # 현재 검수 중인 모델들을 복사 (반복 중에 수정하면 오류 발생)
    reviewing_models = st.session_state.reviewing_models.copy()
    
    for model_id in reviewing_models:
        if model_id in st.session_state.translation_results:
            result = st.session_state.translation_results[model_id]
            
            # 검수 수행
            review_result = review_translation(
                st.session_state.user_input, 
                result["text"]
            )
            
            # 결과 저장
            st.session_state.review_results[model_id] = review_result
            
            # 검수 완료 표시
            st.session_state.reviewing_models.remove(model_id)
    
    # 검수 중인 모델이 하나라도 있으면 페이지 다시 로드
    if st.session_state.reviewing_models:
        st.rerun()

if __name__ == "__main__":
    main()