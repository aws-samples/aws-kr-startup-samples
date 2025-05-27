"""
토큰 가격 계산 관련 유틸리티 함수
"""
import os
import json

# 설정 파일 경로
PRICING_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'pricing.json')

# 설정 파일 캐싱
_pricing_config = None

def _load_pricing_config():
    """가격 정보 설정 파일을 로드합니다."""
    global _pricing_config
    if _pricing_config is None:
        try:
            with open(PRICING_CONFIG_PATH, 'r') as f:
                _pricing_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Exception(f"가격 정보 설정 파일을 로드할 수 없습니다: {e}")
    return _pricing_config

def get_token_pricing(model_id):
    """모델 ID에 따른 토큰 가격 정보를 반환합니다.
    
    Returns:
        tuple: (입력 토큰 1000개당 가격, 출력 토큰 1000개당 가격)
    """
    config = _load_pricing_config()
    model_id_lower = model_id.lower()
    model_type = determine_model_type(model_id_lower)
    
    # 모델 유형별 가격 검색
    if model_type in config:
        # 특정 모델 가격 검색
        for model_key in config[model_type]:
            if model_key in model_id_lower:
                pricing = config[model_type][model_key]
                return (pricing["input"] / 1000, pricing["output"] / 1000)
    
    # 기본 가격 반환 (알 수 없는 모델)
    return (config["default"]["input"] / 1000, config["default"]["output"] / 1000)

def determine_model_type(model_id):
    """모델 ID에 따른 모델 유형을 반환합니다."""
    model_id_lower = model_id.lower()
    
    if "anthropic" in model_id_lower or "claude" in model_id_lower:
        return "claude"
    elif "nova" in model_id_lower:
        return "nova"
    elif "deepseek" in model_id_lower:
        return "deepseek"
    else:
        return "unknown" 