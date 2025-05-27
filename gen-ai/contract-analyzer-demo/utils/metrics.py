"""
성능 지표 계산 및 표시를 위한 유틸리티 함수
"""
import streamlit as st
from typing import Dict, Tuple, Any, List

def calculate_cost_metrics(prompt_tokens: int, response_tokens: int, price_per_thousand: Tuple[float, float]) -> Dict[str, Any]:
    """토큰 사용량과 가격 정보를 기반으로 비용 지표를 계산합니다.
    
    Args:
        prompt_tokens: 입력 토큰 수
        response_tokens: 출력 토큰 수
        price_per_thousand: (입력 토큰 1000개당 가격, 출력 토큰 1000개당 가격)
    
    Returns:
        계산된 성능 지표를 포함하는 딕셔너리
    """
    total_tokens = prompt_tokens + response_tokens
    input_token_price, output_token_price = price_per_thousand
    input_cost = (prompt_tokens / 1000) * input_token_price
    output_cost = (response_tokens / 1000) * output_token_price
    single_call_cost = input_cost + output_cost
    cost_per_10k_calls = single_call_cost * 10000
    
    return {
        "total_tokens": total_tokens,
        "input_token_price": input_token_price,
        "output_token_price": output_token_price,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "single_call_cost": single_call_cost,
        "cost_per_10k_calls": cost_per_10k_calls,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens
    }

def display_basic_metrics(processing_time: float, metrics: Dict[str, Any], with_bulk_metrics: bool = True) -> None:
    """기본 성능 지표를 표시합니다.
    
    Args:
        processing_time: 처리 시간 (초)
        metrics: calculate_cost_metrics 함수에서 반환된 지표 딕셔너리
        with_bulk_metrics: 대량 처리 비용도 표시할지 여부
    """
    if with_bulk_metrics:
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("처리 시간", f"{processing_time:.2f}초")
        with metrics_col2:
            st.metric("총 토큰", f"{metrics['total_tokens']:,}")
        with metrics_col3:
            st.metric("1만건 비용", f"${metrics['cost_per_10k_calls']:.2f}")
    else:
        metrics_col1, metrics_col2 = st.columns(2)
        with metrics_col1:
            st.metric("처리 시간", f"{processing_time:.2f}초")
        with metrics_col2:
            st.metric("총 토큰", f"{metrics['total_tokens']:,}")

def display_detailed_metrics(metrics: Dict[str, Any]) -> None:
    """세부 비용 지표를 확장 가능한 섹션에 표시합니다.
    
    Args:
        metrics: calculate_cost_metrics 함수에서 반환된 지표 딕셔너리
    """
    with st.expander("비용 세부 정보"):
        st.markdown(f"""
        ### 토큰 및 비용 세부 정보
        
        **토큰 사용량**
        - 입력 토큰: {metrics['prompt_tokens']:,}
        - 출력 토큰: {metrics['response_tokens']:,}
        - 총 토큰: {metrics['total_tokens']:,}
        
        **토큰당 가격**
        - 입력 토큰 1000개당: ${metrics['input_token_price']:.4f}
        - 출력 토큰 1000개당: ${metrics['output_token_price']:.4f}
        
        **단일 호출 비용 내역**
        - 입력 토큰 비용: ${metrics['input_cost']:.4f} (입력 토큰 {metrics['prompt_tokens']:,}개 기준)
        - 출력 토큰 비용: ${metrics['output_cost']:.4f} (출력 토큰 {metrics['response_tokens']:,}개 기준)
        - 총 비용: ${metrics['single_call_cost']:.4f}
        
        **대량 호출 예상 비용**
        - 100건: ${metrics['single_call_cost'] * 100:.4f}
        - 1,000건: ${metrics['single_call_cost'] * 1000:.2f}
        - 10,000건: ${metrics['cost_per_10k_calls']:.2f}
        - 100,000건: ${metrics['single_call_cost'] * 100000:.2f}
        
        > 참고: 실제 비용은 AWS Bedrock 요금에 따라 달라질 수 있습니다.
        """) 