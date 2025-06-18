"""
Notion 데이터 검증 및 처리 관련 클래스들
"""
import json
from typing import Any, Dict, Optional, Tuple


class NotionIdValidator:
    """Notion ID 검증 및 정리를 담당하는 클래스"""
    
    @staticmethod
    def clean_id(id_string: str) -> str:
        """Notion ID를 정리하여 올바른 형태로 변환"""
        # URL에서 ID만 추출
        if "notion.so" in id_string:
            id_string = id_string.split("/")[-1].split("?")[0].split("#")[0]
        
        # 하이픈이 없는 경우 추가
        if len(id_string) == 32 and "-" not in id_string:
            id_string = f"{id_string[:8]}-{id_string[8:12]}-{id_string[12:16]}-{id_string[16:20]}-{id_string[20:]}"
        
        return id_string
    
    @staticmethod
    def is_valid_id(id_string: str) -> bool:
        """Notion ID가 유효한 형태인지 검증"""
        cleaned_id = NotionIdValidator.clean_id(id_string)
        # UUID 형태인지 확인 (8-4-4-4-12)
        parts = cleaned_id.split("-")
        if len(parts) != 5:
            return False
        
        expected_lengths = [8, 4, 4, 4, 12]
        for i, part in enumerate(parts):
            if len(part) != expected_lengths[i] or not all(c.isalnum() for c in part):
                return False
        
        return True


class NotionParameterValidator:
    """Notion API 파라미터 검증을 담당하는 클래스"""
    
    @staticmethod
    def validate_page_size(page_size: int) -> int:
        """페이지 크기를 검증하고 유효한 범위로 조정"""
        return min(max(1, page_size), 100)
    
    @staticmethod
    def validate_sort_direction(direction: str) -> str:
        """정렬 방향을 검증"""
        valid_directions = ["ascending", "descending"]
        return direction if direction in valid_directions else "descending"
    
    @staticmethod
    def validate_sort_by(sort_by: str) -> str:
        """정렬 기준을 검증"""
        valid_sort_fields = ["last_edited_time", "created_time"]
        return sort_by if sort_by in valid_sort_fields else "last_edited_time"
    
    @staticmethod
    def validate_json_string(json_string: str, field_name: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """JSON 문자열을 검증하고 파싱"""
        try:
            parsed_json = json.loads(json_string)
            return True, parsed_json, ""
        except json.JSONDecodeError as e:
            return False, None, f"{field_name} JSON 파싱 오류: {str(e)}"


class NotionTextProcessor:
    """텍스트 처리 및 길이 제한을 담당하는 클래스"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """텍스트를 지정된 길이로 자르고 suffix 추가"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + suffix
    
    @staticmethod
    def format_display_value(value: str, max_length: int = 150) -> str:
        """표시용 값을 포맷팅 (긴 값은 줄여서 표시)"""
        if len(str(value)) > max_length:
            return str(value)[:max_length] + "..."
        return str(value)
    
    @staticmethod
    def extract_rich_text(rich_text_array: list) -> str:
        """rich_text 배열에서 plain_text를 추출하여 결합"""
        return "".join([text.get("plain_text", "") for text in rich_text_array])
    
    @staticmethod
    def clean_empty_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """빈 값들을 제거한 딕셔너리 반환"""
        return {k: v for k, v in data.items() if v}
