"""
계약서 데이터 모델 클래스
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class RecommendedField:
    """추천 계약 필드 클래스"""
    field_name: str
    field_value: str
    importance_desc: str
    source: str

@dataclass
class FieldSource:
    """필드 소스 정보 클래스"""
    text: str
    page: int
    relevance: float
    ai_extracted: bool = False

@dataclass
class Contract:
    """계약서 데이터 모델 클래스"""
    # 기본 필드
    contract_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_renewal: Optional[str] = None
    renewal_notice_period: Optional[str] = None
    
    # 추천 필드
    recommended_fields: List[RecommendedField] = field(default_factory=list)
    
    # 필드 소스 정보
    field_sources: Dict[str, List[FieldSource]] = field(default_factory=dict)
    
    # 원본 응답 저장
    raw_response: Optional[str] = None
    
    # 처리 정보
    processing_time: float = 0.0
    prompt_tokens: int = 0
    response_tokens: int = 0
    model_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """계약서 객체를 딕셔너리로 변환합니다."""
        return {
            "contract_name": self.contract_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "auto_renewal": self.auto_renewal,
            "renewal_notice_period": self.renewal_notice_period,
            "recommended_fields": [
                {
                    "field_name": field.field_name,
                    "field_value": field.field_value,
                    "importance_desc": field.importance_desc,
                    "source": field.source
                }
                for field in self.recommended_fields
            ],
            "processing_info": {
                "processing_time": self.processing_time,
                "prompt_tokens": self.prompt_tokens,
                "response_tokens": self.response_tokens,
                "model_id": self.model_id
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contract':
        """딕셔너리에서 계약서 객체를 생성합니다."""
        contract = cls(
            contract_name=data.get("contract_name"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            auto_renewal=data.get("auto_renewal"),
            renewal_notice_period=data.get("renewal_notice_period")
        )
        
        # 추천 필드 추가
        for field_data in data.get("recommended_fields", []):
            contract.recommended_fields.append(
                RecommendedField(
                    field_name=field_data.get("field_name", ""),
                    field_value=field_data.get("field_value", ""),
                    importance_desc=field_data.get("importance_desc", ""),
                    source=field_data.get("source", "")
                )
            )
        
        # 처리 정보 추가
        if "processing_info" in data:
            info = data["processing_info"]
            contract.processing_time = info.get("processing_time", 0.0)
            contract.prompt_tokens = info.get("prompt_tokens", 0)
            contract.response_tokens = info.get("response_tokens", 0)
            contract.model_id = info.get("model_id")
        
        return contract 