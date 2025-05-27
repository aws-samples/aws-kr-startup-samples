"""
계약서 필드 추출 및 위험 분석 앱
"""
import streamlit as st
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import boto3
import pandas as pd
import re
import io
import fitz  # PyMuPDF
from pathlib import Path

# 모듈 가져오기
from services.bedrock import get_bedrock_client
from services.pdf import extract_text_from_pdf, get_pdf_preview_html, generate_risk_analysis_pdf
from services.extraction import extract_contract_fields_with_bedrock, find_source_text_for_fields
from services.risk_analysis import analyze_contract_risks
from services.summarization import summarize_contract_with_bedrock
from models.contract import Contract, RecommendedField, FieldSource
from models.analytics import ContractAnalytics, RiskAnalysis
from utils.text_processing import highlight_text
from utils.pricing import get_token_pricing
from utils.metrics import calculate_cost_metrics, display_basic_metrics, display_detailed_metrics

# 환경 변수 로드
load_dotenv()

# 리전을 us-east-1로 설정
os.environ["AWS_REGION"] = "us-east-1"

# 페이지 설정
st.set_page_config(
    page_title="AI 계약 관리 비서",
    page_icon="📄",
    layout="wide"
)

# 마크다운 파일에서 오류 도움말 읽기 함수
def load_error_help():
    error_help_path = Path(__file__).parent / "docs" / "error_help.md"
    if error_help_path.exists():
        with open(error_help_path, "r", encoding="utf-8") as file:
            return file.read()
    else:
        return """### 일반적인 오류 및 해결 방법\n\n오류 도움말 파일을 찾을 수 없습니다."""

def main():
    st.title("📄 AI 계약 관리 비서")
    st.write("AI를 이용해 계약서를 쉽게 분석하고 관리하세요.")
    
    # 모델 옵션 정의 (업데이트된 모델 ID 포함)
    model_options = {
        "Amazon Nova Micro": "amazon.nova-micro-v1:0",
        "Amazon Nova Lite": "amazon.nova-lite-v1:0",
        "Amazon Nova Pro": "amazon.nova-pro-v1:0", 
        "Anthropic Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "Anthropic Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "Anthropic Claude 3.5 Haiku": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "Anthropic Claude 3.5 Sonnet": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "Anthropic Claude 3.7 Sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "DeepSeek R1": "us.deepseek.r1-v1:0"  # DeepSeek R1 모델 추가
    }
    
    # 사이드바 설정 및 정보
    with st.sidebar:
        st.header("기능 선택")
        selected_feature = st.radio(
            "작업 선택",
            ["계약서 요약", "필드값 추출", "위험도 분석"],
            index=0
        )
        
        # 선택된 기능에 따른 모델 선택 옵션
        st.subheader(f"{selected_feature} 설정")
        
        # 모델 선택 (기본값: Amazon Nova Micro)
        selected_model_name = st.selectbox(
            "AI 모델 선택",
            list(model_options.keys()),
            index=0
        )
        selected_model_id = model_options[selected_model_name]
        
        # 가격 정보 표시
        price_per_thousand = get_token_pricing(selected_model_id)
        st.info(f"모델 가격: 1M 토큰당 ${1000*price_per_thousand[0]:.4f} (입력), ${1000*price_per_thousand[1]:.4f} (출력)")
        
        # 기능별 안내 정보
        st.header("정보")
        
        if selected_feature == "계약서 요약":
            st.subheader("계약서 요약")
            st.markdown("""
            이 도구는 계약서의 내용을 분석하여 다음 정보를 제공합니다:
            
            - **계약 유형**: 계약서의 종류 (판매계약, 고용계약 등)
            - **계약 당사자**: 계약에 참여하는 주요 당사자
            - **주요 내용 요약**: 계약서 핵심 내용의 간략한 요약
            - **주요 포인트**: 계약서에서 주목할 만한 중요 사항들
            """)
        elif selected_feature == "필드값 추출":
            st.subheader("추출되는 필드")
            st.markdown("""
            이 도구는 다음 계약 필드를 추출합니다:
            
            - **계약 시작일**: 계약이 효력을 발생하는 날짜 (YYYY-MM-DD 형식)
            - **계약 종료일**: 계약이 만료되는 날짜 (YYYY-MM-DD 형식)
            - **자동 갱신**: 계약이 자동으로 갱신되는지 여부 (예/아니오)
            - **갱신 거절 통지 기간**: 갱신을 방지하기 위해 필요한 사전 통지 기간 (구체적인 날짜정보를 추출하거나 추론하여 표시)
            """)
        else:  # 위험도 분석
            st.subheader("위험도 분석")
            st.markdown("""
            이 도구는 계약서의 잠재적 위험 요소를 분석하고 다음을 제공합니다:
            
            - **위험 카테고리**: 위험이 속한 카테고리
            - **위험 수준**: 높음, 중간, 낮음으로 구분
            - **위험 설명**: 위험 요소에 대한 상세 설명
            - **권장사항**: 위험 요소 해결을 위한 권장 조치
            - **위험 출처**: 계약서 내 관련 조항 참조
            """)
        
        # 오류 도움말 섹션
        with st.expander("오류 해결 도움말"):
            st.markdown(load_error_help())
    
    # 메인 패널 - 파일 업로드 및 결과
    uploaded_file = st.file_uploader("계약서 문서 업로드", type=["pdf"])
    
    if uploaded_file is not None:
        # 화면을 두 영역으로 분할
        col1, col2 = st.columns([1, 1])
        
        # 왼쪽 영역 - PDF 미리보기
        with col1:
            st.subheader("계약서 미리보기")
            # PDF 미리보기 HTML 생성 및 표시
            pdf_display = get_pdf_preview_html(uploaded_file)
            st.markdown(pdf_display, unsafe_allow_html=True)
        
        # 오른쪽 영역 - 선택된 기능에 따른 UI
        with col2:
            # 계약서 요약 기능 UI
            if selected_feature == "계약서 요약":
                st.subheader("계약서 요약")
                
                # 처리 버튼
                summarize_button = st.button(f"{selected_model_name}으로 계약서 요약", key="summarize_button")
                
                if summarize_button:
                    with st.spinner(f"{selected_model_name}으로 계약서 요약 중..."):
                        # Bedrock 클라이언트 초기화
                        bedrock_client = get_bedrock_client()
                        
                        if bedrock_client:
                            # PDF에서 텍스트 추출
                            text, extraction_time, pages_text, page_starts = extract_text_from_pdf(uploaded_file)
                            
                            if text:
                                # 텍스트 길이 표시
                                st.info(f"{extraction_time:.2f}초 동안 문서에서 {len(text)}자의 텍스트를 추출했습니다")
                                
                                # 계약서 요약 실행
                                summary_result = summarize_contract_with_bedrock(
                                    bedrock_client, 
                                    text, 
                                    selected_model_id
                                )
                                
                                if summary_result and len(summary_result) == 5:
                                    summary_data, processing_time, prompt_tokens, response_tokens, raw_response = summary_result
                                    
                                    # 성능 지표 계산
                                    price_per_thousand = get_token_pricing(selected_model_id)
                                    metrics = calculate_cost_metrics(prompt_tokens, response_tokens, price_per_thousand)
                                    
                                    # 기본 지표 표시
                                    display_basic_metrics(processing_time, metrics, with_bulk_metrics=False)
                                    
                                    # 요약 결과 표시
                                    if summary_data is not None:
                                        st.subheader("계약서 개요")
                                        
                                        # 계약 유형 및 당사자 표시
                                        st.markdown(f"**계약 유형:** {summary_data.get('contract_type', '알 수 없음')}")
                                        
                                        parties = summary_data.get('parties', ['알 수 없음'])
                                        if isinstance(parties, list) and len(parties) > 0:
                                            st.markdown(f"**계약 당사자:** {', '.join(parties)}")
                                        else:
                                            st.markdown(f"**계약 당사자:** {parties}")
                                        
                                        # 요약 표시
                                        st.markdown("### 요약")
                                        st.markdown(summary_data.get('summary', '요약을 생성할 수 없습니다.'))
                                        
                                        # 주요 포인트 표시
                                        st.markdown("### 주요 포인트")
                                        key_points = summary_data.get('key_points', [])
                                        if isinstance(key_points, list) and len(key_points) > 0:
                                            for point in key_points:
                                                st.markdown(f"- {point}")
                                        else:
                                            st.markdown("주요 포인트를 추출할 수 없습니다.")
                                    else:
                                        st.error("요약 데이터를 생성할 수 없습니다. API 응답에 문제가 있습니다.")
                                        if raw_response:
                                            with st.expander("원본 오류 응답"):
                                                st.text(raw_response)
                                else:
                                    st.error("요약을 생성할 수 없습니다. 다른 모델을 시도해보세요.")
                            else:
                                st.error("PDF에서 텍스트를 추출할 수 없습니다. 다른 PDF 파일을 시도하세요.")
                        else:
                            st.error("AWS Bedrock 클라이언트를 초기화할 수 없습니다. AWS 자격 증명을 확인하세요.")
            
            # 필드값 추출 기능 UI
            elif selected_feature == "필드값 추출":
                st.subheader("필드값 추출")
                # 처리 버튼
                process_button = st.button(f"{selected_model_name}으로 계약 필드 추출", key="extract_fields_button")
                
                if process_button:
                    with st.spinner(f"{selected_model_name}으로 계약서 문서 처리 중..."):
                        # Bedrock 클라이언트 초기화
                        bedrock_client = get_bedrock_client()
                        
                        if bedrock_client:
                            # PDF에서 페이지 정보와 함께 텍스트 추출
                            text, extraction_time, pages_text, page_starts = extract_text_from_pdf(uploaded_file)
                            
                            if text:
                                # 텍스트 길이 표시
                                st.info(f"{extraction_time:.2f}초 동안 문서에서 {len(text)}자의 텍스트를 추출했습니다")
                                
                                # Bedrock 모델로 계약 필드 추출
                                result = extract_contract_fields_with_bedrock(
                                    bedrock_client, 
                                    text, 
                                    selected_model_id
                                )
                                
                                if result and len(result) == 6:
                                    extracted_fields, processing_time, prompt_tokens, response_tokens, raw_response, model_source_texts = result
                                else:
                                    st.error("모델 처리 결과가 없거나 예상과 다릅니다")
                                    return
                                
                                # 추출된 필드가 없으면 처리 중단
                                if not extracted_fields:
                                    st.warning("추출된 필드가 없습니다. 다른 모델을 시도해보세요.")
                                    # 원본 응답 표시
                                    st.subheader("원본 모델 응답")
                                    st.text_area("응답", raw_response, height=300)
                                    return
                                
                                # 원본 문서에서 각 필드에 대한 소스 텍스트 찾기
                                field_sources = find_source_text_for_fields(text, extracted_fields, pages_text, page_starts)
                                
                                # AI가 제공한 출처 텍스트와 추출한 텍스트 결합
                                for field, ai_source in model_source_texts.items():
                                    if field in field_sources and isinstance(ai_source, str) and len(ai_source) > 10:
                                        # AI가 제공한 출처 텍스트를 첫 번째 결과로 추가
                                        field_sources[field].insert(0, {
                                            "text": ai_source,
                                            "page": "AI 추출",
                                            "relevance": 1.5,
                                            "ai_extracted": True
                                        })
                                
                                # 성능 지표 계산
                                price_per_thousand = get_token_pricing(selected_model_id)
                                metrics = calculate_cost_metrics(prompt_tokens, response_tokens, price_per_thousand)
                                
                                # 기본 지표 표시
                                display_basic_metrics(processing_time, metrics)
                                
                                # 세부 비용 정보 표시
                                display_detailed_metrics(metrics)
                                
                                # 결과 필드가 있으면 표시
                                if extracted_fields:
                                    # 결과 테이블 생성
                                    st.subheader("추출된 계약 필드")
                                    
                                    # 기본 필드 표시
                                    for field_name in ["계약 시작일", "계약 종료일", "자동 갱신", "갱신 거절 통지 기간"]:
                                        field_value = extracted_fields.get(field_name, "찾을 수 없음")
                                        
                                        st.markdown(f"**{field_name}:** {field_value}")
                                        
                                        # 필드 소스 표시
                                        if field_name in field_sources and field_sources[field_name]:
                                            st.markdown("**출처:**")
                                            for i, source in enumerate(field_sources[field_name]):
                                                if source.get("ai_extracted", False):
                                                    st.info(f"AI 모델 추출 소스: {source['text']}")
                                                else:
                                                    page_num = source.get("page", "알 수 없음")
                                                    highlighted_text = highlight_text(source.get("text", ""), field_value)
                                                    st.markdown(f"페이지 {page_num} 참조: {highlighted_text}", unsafe_allow_html=True)
                                        
                                        st.markdown("---")
                                    
                                    # 추천 필드 표시
                                    recommended_fields = extracted_fields.get("추천 계약 필드", [])
                                    if recommended_fields:
                                        st.subheader("추천 계약 필드")
                                        
                                        for field in recommended_fields:
                                            field_name = field.get("필드명", "알 수 없음")
                                            field_value = field.get("필드값", "")
                                            importance = field.get("중요도 설명", "")
                                            source = field.get("출처", "")
                                            
                                            st.markdown(f"**{field_name}:** {field_value}")
                                            
                                            if importance:
                                                st.markdown(f"**중요도 설명:** {importance}")
                                            
                                            if source:
                                                st.markdown(f"**출처:** {source}")
                                            
                                            # 출처 텍스트 소스가 있으면 표시
                                            if field_name in model_source_texts:
                                                source_text = model_source_texts[field_name]
                                                highlighted_text = highlight_text(source_text, field_value)
                                                st.markdown(f"**참조 텍스트:** {highlighted_text}", unsafe_allow_html=True)
                                            
                                            st.markdown("---")
                                
                                    # 원본 응답 표시 (디버깅용)
                                    with st.expander("원본 모델 응답 (디버깅)"):
                                        st.text_area("JSON 응답", raw_response, height=300)
                            else:
                                st.error("PDF에서 텍스트를 추출할 수 없습니다. 다른 PDF 파일을 시도하세요.")
                        else:
                            st.error("AWS Bedrock 클라이언트를 초기화할 수 없습니다. AWS 자격 증명을 확인하세요.")
            
            # 위험도 분석 기능 UI
            else:
                st.subheader("계약서 위험 분석")
                # 위험 분석 버튼
                risk_analysis_button = st.button("계약서 위험 분석 실행", key="risk_analysis_button")
                
                if risk_analysis_button:
                    with st.spinner("계약서 위험 분석 중..."):
                        # Bedrock 클라이언트 초기화
                        bedrock_client = get_bedrock_client()
                        
                        if bedrock_client:
                            # PDF에서 텍스트 추출
                            text, extraction_time, pages_text, page_starts = extract_text_from_pdf(uploaded_file)
                            
                            if text:
                                # 텍스트 길이 표시
                                st.info(f"{extraction_time:.2f}초 동안 문서에서 {len(text)}자의 텍스트를 추출했습니다")
                                
                                # 위험 분석 실행
                                risk_model_id = selected_model_id
                                risk_analysis, processing_time, prompt_tokens, response_tokens, raw_response = analyze_contract_risks(
                                    bedrock_client, 
                                    text, 
                                    risk_model_id
                                )
                                
                                if risk_analysis:
                                    # 성능 지표 계산
                                    price_per_thousand = get_token_pricing(risk_model_id)
                                    metrics = calculate_cost_metrics(prompt_tokens, response_tokens, price_per_thousand)
                                    
                                    # 기본 지표 표시
                                    display_basic_metrics(processing_time, metrics, with_bulk_metrics=False)
                                    
                                    # 위험 분석 결과 표시
                                    st.subheader("계약서 위험 분석 결과")
                                    
                                    # 위험 수준별 필터링 옵션
                                    risk_levels = ["모든 위험", "높음", "중간", "낮음"]
                                    selected_risk_level = st.selectbox("위험 수준 필터", risk_levels)
                                    
                                    # 각 위험 항목 표시
                                    for risk in risk_analysis:
                                        # 위험 수준으로 필터링
                                        if selected_risk_level != "모든 위험" and risk["risk_level"] != selected_risk_level:
                                            continue
                                        
                                        # 위험 수준에 따른 색상 설정
                                        level_color = "black"
                                        if risk["risk_level"] == "높음":
                                            level_color = "red"
                                        elif risk["risk_level"] == "중간":
                                            level_color = "orange"
                                        elif risk["risk_level"] == "낮음":
                                            level_color = "green"
                                        
                                        # 위험 항목 표시
                                        with st.container():
                                            st.markdown(f"### {risk['category']}: {risk['title']}")
                                            st.markdown(f"**위험 수준:** <span style='color:{level_color};'>{risk['risk_level']}</span>", unsafe_allow_html=True)
                                            
                                            if risk['description']:
                                                st.markdown(f"**설명:** {risk['description']}")
                                            
                                            if risk['recommendation']:
                                                st.markdown(f"**권장사항:** {risk['recommendation']}")
                                            
                                            if risk['source']:
                                                st.markdown(f"**출처:** {risk['source']}")
                                            
                                            st.markdown("---")
                                    
                                    # 세부 비용 정보 표시
                                    display_detailed_metrics(metrics)
                                    
                                    # PDF 다운로드 옵션
                                    st.subheader("분석 결과 다운로드")
                                    
                                    # 계약서 이름 입력
                                    contract_name = st.text_input("계약서 이름 (PDF 파일 이름에 사용)", 
                                                               value=uploaded_file.name if uploaded_file else "계약서")
                                    
                                    # 성능 지표 저장
                                    metrics_data = {
                                        "processing_time": processing_time,
                                        "total_tokens": metrics["total_tokens"],
                                        "cost": metrics["single_call_cost"]
                                    }
                                    
                                    # PDF 파일 이름 생성
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    file_name = f"{contract_name.replace('.pdf', '')}_위험분석_{timestamp}.pdf"
                                    
                                    # PDF 생성 및 다운로드 버튼
                                    pdf_buffer = generate_risk_analysis_pdf(risk_analysis, file_name, contract_name, metrics_data)
                                    
                                    if pdf_buffer:
                                        st.download_button(
                                            label="위험 분석 결과 PDF 다운로드",
                                            data=pdf_buffer,
                                            file_name=file_name,
                                            mime="application/pdf"
                                        )
                                    
                                    # 원본 응답 표시 (디버깅용)
                                    with st.expander("원본 모델 응답 (디버깅)"):
                                        st.text_area("응답", raw_response, height=300)
                                else:
                                    st.error("위험 분석을 수행할 수 없습니다. 다른 PDF 파일을 시도하세요.")
                            else:
                                st.error("PDF에서 텍스트를 추출할 수 없습니다. 다른 PDF 파일을 시도하세요.")
                        else:
                            st.error("AWS Bedrock 클라이언트를 초기화할 수 없습니다. AWS 자격 증명을 확인하세요.")

if __name__ == "__main__":
    main() 