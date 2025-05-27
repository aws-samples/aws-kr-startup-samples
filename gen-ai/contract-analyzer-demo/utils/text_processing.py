"""
텍스트 처리 관련 유틸리티 함수
"""
import re

def estimate_token_count(text, model_id):
    """텍스트의 토큰 수를 대략적으로 추정합니다."""
    # 다른 모델은 토큰 계산 방식이 다를 수 있음
    # 이것은 매우 대략적인 추정치
    if "claude" in model_id.lower():
        # Anthropic Claude 모델: 한국어의 경우 약 문자 3~4개당 토큰 1개
        return len(text) // 3
    else:
        # Amazon 모델: 한국어의 경우 약 문자 3~5개당 토큰 1개
        return len(text) // 4

def highlight_text(snippet, field_value):
    """필드 값을 강조 표시하기 위해 HTML로 래핑합니다."""
    if not snippet or not field_value or field_value in ["예", "아니오", "Yes", "No"]:
        return snippet
    
    try:
        # 하이라이트 스타일
        highlight_style = "background-color: #FFFF00; font-weight: bold;"
        
        # 필드 값을 정규 표현식 패턴으로 이스케이프
        escaped_value = re.escape(field_value)
        
        # 대소문자를 구분하지 않는 정규식으로 필드 값 검색
        pattern = re.compile(f'({escaped_value})', re.IGNORECASE)
        
        # 필드 값을 하이라이트된 HTML로 대체
        highlighted = pattern.sub(f'<span style="{highlight_style}">\\1</span>', snippet)
        
        return highlighted
    except Exception as e:
        print(f"하이라이트 오류: {str(e)}")
        return snippet 