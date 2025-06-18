"""
Notion 데이터 포맷팅 관련 클래스들
"""
from typing import Any, Dict, List
from datetime import datetime


class NotionBlockFormatter:
    """Notion 블록 데이터를 텍스트로 변환하는 클래스"""
    
    @staticmethod
    def format_content(block_data: Dict[str, Any]) -> str:
        """Notion 블록 데이터를 텍스트로 변환"""
        block_type = block_data.get("type", "")
        
        if block_type == "paragraph":
            rich_text = block_data.get("paragraph", {}).get("rich_text", [])
            return "".join([text.get("plain_text", "") for text in rich_text])
        
        elif block_type == "heading_1":
            rich_text = block_data.get("heading_1", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"# {text}"
        
        elif block_type == "heading_2":
            rich_text = block_data.get("heading_2", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"## {text}"
        
        elif block_type == "heading_3":
            rich_text = block_data.get("heading_3", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"### {text}"
        
        elif block_type == "bulleted_list_item":
            rich_text = block_data.get("bulleted_list_item", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"• {text}"
        
        elif block_type == "numbered_list_item":
            rich_text = block_data.get("numbered_list_item", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"1. {text}"
        
        elif block_type == "to_do":
            rich_text = block_data.get("to_do", {}).get("rich_text", [])
            checked = block_data.get("to_do", {}).get("checked", False)
            text = "".join([text.get("plain_text", "") for text in rich_text])
            checkbox = "☑" if checked else "☐"
            return f"{checkbox} {text}"
        
        elif block_type == "code":
            rich_text = block_data.get("code", {}).get("rich_text", [])
            language = block_data.get("code", {}).get("language", "")
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"```{language}\n{text}\n```"
        
        elif block_type == "quote":
            rich_text = block_data.get("quote", {}).get("rich_text", [])
            text = "".join([text.get("plain_text", "") for text in rich_text])
            return f"> {text}"
        
        else:
            # 기타 타입들에 대한 기본 처리
            for key, value in block_data.items():
                if isinstance(value, dict) and "rich_text" in value:
                    rich_text = value.get("rich_text", [])
                    text = "".join([text.get("plain_text", "") for text in rich_text])
                    if text.strip():
                        return text
            return ""


class NotionPropertyFormatter:
    """Notion 페이지 속성을 포맷팅하는 클래스"""
    
    @staticmethod
    def format_properties(properties: Dict[str, Any]) -> Dict[str, str]:
        """페이지 속성을 읽기 쉬운 형태로 변환"""
        formatted_props = {}
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "")
            
            if prop_type == "title":
                title_list = prop_data.get("title", [])
                formatted_props[prop_name] = "".join([t.get("plain_text", "") for t in title_list])
            
            elif prop_type == "rich_text":
                rich_text = prop_data.get("rich_text", [])
                formatted_props[prop_name] = "".join([t.get("plain_text", "") for t in rich_text])
            
            elif prop_type == "number":
                number = prop_data.get("number")
                formatted_props[prop_name] = str(number) if number is not None else ""
            
            elif prop_type == "select":
                select = prop_data.get("select")
                formatted_props[prop_name] = select.get("name", "") if select else ""
            
            elif prop_type == "multi_select":
                multi_select = prop_data.get("multi_select", [])
                formatted_props[prop_name] = ", ".join([item.get("name", "") for item in multi_select])
            
            elif prop_type == "date":
                date_obj = prop_data.get("date")
                if date_obj:
                    start = date_obj.get("start", "")
                    end = date_obj.get("end", "")
                    formatted_props[prop_name] = f"{start}" + (f" ~ {end}" if end else "")
                else:
                    formatted_props[prop_name] = ""
            
            elif prop_type == "checkbox":
                checkbox = prop_data.get("checkbox", False)
                formatted_props[prop_name] = "Yes" if checkbox else "No"
            
            elif prop_type == "url":
                url = prop_data.get("url", "")
                formatted_props[prop_name] = url
            
            elif prop_type == "email":
                email = prop_data.get("email", "")
                formatted_props[prop_name] = email
            
            elif prop_type == "phone_number":
                phone = prop_data.get("phone_number", "")
                formatted_props[prop_name] = phone
            
            elif prop_type == "people":
                people = prop_data.get("people", [])
                names = []
                for person in people:
                    if person.get("name"):
                        names.append(person.get("name"))
                    elif person.get("id"):
                        names.append(f"User-{person.get('id')[:8]}")
                formatted_props[prop_name] = ", ".join(names)
            
            elif prop_type == "files":
                files = prop_data.get("files", [])
                file_names = []
                for file in files:
                    if file.get("name"):
                        file_names.append(file.get("name"))
                    elif file.get("file", {}).get("url"):
                        file_names.append("File")
                formatted_props[prop_name] = ", ".join(file_names)
            
            elif prop_type == "relation":
                relation = prop_data.get("relation", [])
                formatted_props[prop_name] = f"{len(relation)} related items"
            
            elif prop_type == "formula":
                formula = prop_data.get("formula", {})
                formula_type = formula.get("type", "")
                if formula_type == "string":
                    formatted_props[prop_name] = formula.get("string", "")
                elif formula_type == "number":
                    formatted_props[prop_name] = str(formula.get("number", ""))
                elif formula_type == "boolean":
                    formatted_props[prop_name] = "Yes" if formula.get("boolean") else "No"
                elif formula_type == "date":
                    date_obj = formula.get("date")
                    if date_obj:
                        formatted_props[prop_name] = date_obj.get("start", "")
                    else:
                        formatted_props[prop_name] = ""
                else:
                    formatted_props[prop_name] = ""
            
            elif prop_type == "rollup":
                rollup = prop_data.get("rollup", {})
                rollup_type = rollup.get("type", "")
                if rollup_type == "number":
                    formatted_props[prop_name] = str(rollup.get("number", ""))
                elif rollup_type == "array":
                    array = rollup.get("array", [])
                    formatted_props[prop_name] = f"{len(array)} items"
                else:
                    formatted_props[prop_name] = ""
            
            elif prop_type == "created_time":
                created_time = prop_data.get("created_time", "")
                formatted_props[prop_name] = created_time
            
            elif prop_type == "created_by":
                created_by = prop_data.get("created_by", {})
                name = created_by.get("name", "")
                if not name and created_by.get("id"):
                    name = f"User-{created_by.get('id')[:8]}"
                formatted_props[prop_name] = name
            
            elif prop_type == "last_edited_time":
                last_edited_time = prop_data.get("last_edited_time", "")
                formatted_props[prop_name] = last_edited_time
            
            elif prop_type == "last_edited_by":
                last_edited_by = prop_data.get("last_edited_by", {})
                name = last_edited_by.get("name", "")
                if not name and last_edited_by.get("id"):
                    name = f"User-{last_edited_by.get('id')[:8]}"
                formatted_props[prop_name] = name
            
            else:
                formatted_props[prop_name] = str(prop_data)
        
        return formatted_props
    
    @staticmethod
    def extract_title(formatted_props: Dict[str, str]) -> str:
        """속성에서 제목을 추출"""
        # 제목 찾기
        for prop_name, prop_value in formatted_props.items():
            if prop_name.lower() in ["title", "name", "제목", "이름"] and prop_value:
                return prop_value
        
        # 제목이 없으면 첫 번째 텍스트 속성 사용
        for prop_value in formatted_props.values():
            if prop_value and isinstance(prop_value, str) and len(prop_value.strip()) > 0:
                return prop_value[:100] + ("..." if len(prop_value) > 100 else "")
        
        return "제목 없음"


class NotionTimeFormatter:
    """Notion 시간 데이터를 포맷팅하는 클래스"""
    
    @staticmethod
    def format_datetime(datetime_str: str) -> str:
        """ISO 형식의 날짜/시간 문자열을 읽기 쉬운 형태로 변환"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return datetime_str
