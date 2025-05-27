"""
계약서 분석 결과 데이터 모델 클래스
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class RiskAnalysis:
    """계약서 위험 분석 결과 클래스"""
    category: str
    title: str
    risk_level: str
    description: str
    recommendation: str
    source: str

@dataclass
class ContractAnalytics:
    """계약서 분석 결과 데이터 모델 클래스"""
    # 기본 정보
    contract_name: Optional[str] = None
    
    # 위험 분석 결과
    risk_analysis: List[RiskAnalysis] = field(default_factory=list)
    
    # 처리 정보
    processing_time: float = 0.0
    prompt_tokens: int = 0
    response_tokens: int = 0
    model_id: Optional[str] = None
    
    # 원본 응답 저장
    raw_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """분석 결과 객체를 딕셔너리로 변환합니다."""
        return {
            "contract_name": self.contract_name,
            "risk_analysis": [
                {
                    "category": risk.category,
                    "title": risk.title,
                    "risk_level": risk.risk_level,
                    "description": risk.description,
                    "recommendation": risk.recommendation,
                    "source": risk.source
                }
                for risk in self.risk_analysis
            ],
            "processing_info": {
                "processing_time": self.processing_time,
                "prompt_tokens": self.prompt_tokens,
                "response_tokens": self.response_tokens,
                "model_id": self.model_id
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractAnalytics':
        """딕셔너리에서 분석 결과 객체를 생성합니다."""
        analytics = cls(
            contract_name=data.get("contract_name")
        )
        
        # 위험 분석 결과 추가
        for risk_data in data.get("risk_analysis", []):
            analytics.risk_analysis.append(
                RiskAnalysis(
                    category=risk_data.get("category", ""),
                    title=risk_data.get("title", ""),
                    risk_level=risk_data.get("risk_level", ""),
                    description=risk_data.get("description", ""),
                    recommendation=risk_data.get("recommendation", ""),
                    source=risk_data.get("source", "")
                )
            )
        
        # 처리 정보 추가
        if "processing_info" in data:
            info = data["processing_info"]
            analytics.processing_time = info.get("processing_time", 0.0)
            analytics.prompt_tokens = info.get("prompt_tokens", 0)
            analytics.response_tokens = info.get("response_tokens", 0)
            analytics.model_id = info.get("model_id")
        
        return analytics 