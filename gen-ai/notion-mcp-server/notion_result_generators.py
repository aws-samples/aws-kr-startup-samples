"""
Notion 검색 결과 및 페이지 내용 생성을 담당하는 클래스들
"""
from typing import Any, Dict, List
from notion_formatters import NotionPropertyFormatter, NotionTimeFormatter, NotionBlockFormatter
from notion_validators import NotionTextProcessor


class NotionSearchResultGenerator:
    """Notion 검색 결과를 생성하는 클래스"""
    
    def __init__(self):
        self.property_formatter = NotionPropertyFormatter()
        self.time_formatter = NotionTimeFormatter()
        self.text_processor = NotionTextProcessor()
    
    def generate_search_results(self, query: str, results: List[Dict[str, Any]], has_more: bool = False) -> str:
        """검색 결과를 포맷된 텍스트로 생성"""
        if not results:
            return f"🔍 '{query}' 검색 결과가 없습니다."
        
        formatted_results = []
        formatted_results.append(f"🔍 Notion 검색 결과: '{query}' ({len(results)}개)")
        formatted_results.append("=" * 50)
        
        for i, result in enumerate(results, 1):
            formatted_result = self._format_single_result(result, i)
            formatted_results.extend(formatted_result)
        
        if has_more:
            formatted_results.append(f"\n💡 더 많은 결과가 있습니다. page_size를 늘려서 더 많은 결과를 확인해보세요.")
        
        return "\n".join(formatted_results)
    
    def _format_single_result(self, result: Dict[str, Any], index: int) -> List[str]:
        """단일 검색 결과를 포맷팅"""
        formatted_result = []
        
        object_type = result.get("object", "")
        result_id = result.get("id", "")
        url = result.get("url", "")
        created_time = result.get("created_time", "")
        last_edited_time = result.get("last_edited_time", "")
        
        formatted_result.append(f"\n📄 결과 {index}")
        formatted_result.append(f"타입: {object_type}")
        formatted_result.append(f"ID: {result_id}")
        formatted_result.append(f"URL: {url}")
        
        if object_type == "page":
            page_info = self._format_page_info(result)
            formatted_result.extend(page_info)
        elif object_type == "database":
            db_info = self._format_database_info(result)
            formatted_result.extend(db_info)
        
        # 시간 정보 추가
        time_info = self._format_time_info(created_time, last_edited_time)
        formatted_result.extend(time_info)
        
        formatted_result.append("-" * 30)
        return formatted_result
    
    def _format_page_info(self, page: Dict[str, Any]) -> List[str]:
        """페이지 정보를 포맷팅"""
        page_info = []
        properties = page.get("properties", {})
        
        if properties:
            formatted_props = self.property_formatter.format_properties(properties)
            title = self.property_formatter.extract_title(formatted_props)
            page_info.append(f"제목: {title}")
            
            # 기타 속성들
            other_props = {k: v for k, v in formatted_props.items() 
                          if k.lower() not in ["title", "name", "제목", "이름"] and v}
            
            if other_props:
                page_info.append("속성:")
                for prop_name, prop_value in other_props.items():
                    display_value = self.text_processor.format_display_value(prop_value)
                    page_info.append(f"  • {prop_name}: {display_value}")
        
        return page_info
    
    def _format_database_info(self, database: Dict[str, Any]) -> List[str]:
        """데이터베이스 정보를 포맷팅"""
        db_info = []
        
        # 데이터베이스 제목
        title_list = database.get("title", [])
        title = self.text_processor.extract_rich_text(title_list)
        if not title:
            title = "데이터베이스"
        db_info.append(f"제목: {title}")
        
        # 데이터베이스 설명
        description = database.get("description", [])
        if description:
            desc_text = self.text_processor.extract_rich_text(description)
            if desc_text:
                display_desc = self.text_processor.truncate_text(desc_text, 200)
                db_info.append(f"설명: {display_desc}")
        
        # 속성 정보
        properties = database.get("properties", {})
        if properties:
            db_info.append(f"속성 ({len(properties)}개):")
            for prop_name, prop_info in list(properties.items())[:5]:  # 처음 5개만 표시
                prop_type = prop_info.get("type", "")
                db_info.append(f"  • {prop_name} ({prop_type})")
            
            if len(properties) > 5:
                db_info.append(f"  • ... 및 {len(properties) - 5}개 더")
        
        return db_info
    
    def _format_time_info(self, created_time: str, last_edited_time: str) -> List[str]:
        """시간 정보를 포맷팅"""
        time_info = []
        
        if created_time:
            formatted_time = self.time_formatter.format_datetime(created_time)
            time_info.append(f"생성일: {formatted_time}")
        
        if last_edited_time:
            formatted_time = self.time_formatter.format_datetime(last_edited_time)
            time_info.append(f"수정일: {formatted_time}")
        
        return time_info


class NotionPageContentGenerator:
    """Notion 페이지 내용을 생성하는 클래스"""
    
    def __init__(self):
        self.property_formatter = NotionPropertyFormatter()
        self.time_formatter = NotionTimeFormatter()
        self.block_formatter = NotionBlockFormatter()
    
    def generate_page_content(self, page_data: Dict[str, Any], blocks: List[Dict[str, Any]] = None) -> str:
        """페이지 내용을 포맷된 텍스트로 생성"""
        formatted_content = []
        formatted_content.append("📄 Notion 페이지 내용")
        formatted_content.append("=" * 50)
        
        # 페이지 기본 정보
        basic_info = self._format_basic_info(page_data)
        formatted_content.extend(basic_info)
        
        # 페이지 속성
        properties_info = self._format_properties_info(page_data)
        formatted_content.extend(properties_info)
        
        # 시간 정보
        time_info = self._format_time_info(page_data)
        formatted_content.extend(time_info)
        
        # 페이지 내용 (블록들)
        if blocks is not None:
            content_info = self._format_content_blocks(blocks)
            formatted_content.extend(content_info)
        
        return "\n".join(formatted_content)
    
    def _format_basic_info(self, page_data: Dict[str, Any]) -> List[str]:
        """페이지 기본 정보를 포맷팅"""
        basic_info = []
        page_id = page_data.get("id", "")
        url = page_data.get("url", "")
        
        basic_info.append(f"ID: {page_id}")
        basic_info.append(f"URL: {url}")
        
        return basic_info
    
    def _format_properties_info(self, page_data: Dict[str, Any]) -> List[str]:
        """페이지 속성 정보를 포맷팅"""
        properties_info = []
        properties = page_data.get("properties", {})
        
        if properties:
            formatted_props = self.property_formatter.format_properties(properties)
            
            # 제목 찾기
            title = self.property_formatter.extract_title(formatted_props)
            if title:
                properties_info.append(f"\n📌 제목: {title}")
            
            # 기타 속성들
            other_props = {k: v for k, v in formatted_props.items() 
                          if k.lower() not in ["title", "name", "제목", "이름"] and v}
            
            if other_props:
                properties_info.append("\n📋 속성:")
                for prop_name, prop_value in other_props.items():
                    properties_info.append(f"  • {prop_name}: {prop_value}")
        
        return properties_info
    
    def _format_time_info(self, page_data: Dict[str, Any]) -> List[str]:
        """시간 정보를 포맷팅"""
        time_info = []
        created_time = page_data.get("created_time", "")
        last_edited_time = page_data.get("last_edited_time", "")
        
        if created_time:
            formatted_time = self.time_formatter.format_datetime(created_time)
            time_info.append(f"\n🕐 생성일: {formatted_time}")
        
        if last_edited_time:
            formatted_time = self.time_formatter.format_datetime(last_edited_time)
            time_info.append(f"🕑 수정일: {formatted_time}")
        
        return time_info
    
    def _format_content_blocks(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """페이지 내용 블록들을 포맷팅"""
        content_info = []
        content_info.append("\n" + "=" * 50)
        content_info.append("📝 페이지 내용:")
        content_info.append("")
        
        if blocks:
            for block in blocks:
                content = self.block_formatter.format_content(block)
                if content.strip():
                    content_info.append(content)
                    content_info.append("")
        else:
            content_info.append("(내용이 없습니다)")
        
        return content_info


class NotionDatabaseListGenerator:
    """Notion 데이터베이스 목록을 생성하는 클래스"""
    
    def __init__(self):
        self.time_formatter = NotionTimeFormatter()
        self.text_processor = NotionTextProcessor()
    
    def generate_database_list(self, databases: List[Dict[str, Any]], has_more: bool = False) -> str:
        """데이터베이스 목록을 포맷된 텍스트로 생성"""
        if not databases:
            return "📋 접근 가능한 데이터베이스가 없습니다."
        
        formatted_results = []
        formatted_results.append(f"📋 Notion 데이터베이스 목록 ({len(databases)}개)")
        formatted_results.append("=" * 50)
        
        for i, db in enumerate(databases, 1):
            db_info = self._format_single_database(db, i)
            formatted_results.extend(db_info)
        
        if has_more:
            formatted_results.append(f"\n💡 더 많은 데이터베이스가 있습니다. page_size를 늘려서 더 많은 결과를 확인해보세요.")
        
        return "\n".join(formatted_results)
    
    def _format_single_database(self, db: Dict[str, Any], index: int) -> List[str]:
        """단일 데이터베이스 정보를 포맷팅"""
        db_info = []
        
        db_id = db.get("id", "")
        url = db.get("url", "")
        created_time = db.get("created_time", "")
        last_edited_time = db.get("last_edited_time", "")
        
        # 데이터베이스 제목
        title_list = db.get("title", [])
        title = self.text_processor.extract_rich_text(title_list)
        if not title:
            title = "제목 없는 데이터베이스"
        
        db_info.append(f"\n🗂️  데이터베이스 {index}: {title}")
        db_info.append(f"ID: {db_id}")
        db_info.append(f"URL: {url}")
        
        # 데이터베이스 설명
        description = db.get("description", [])
        if description:
            desc_text = self.text_processor.extract_rich_text(description)
            if desc_text:
                display_desc = self.text_processor.truncate_text(desc_text, 200)
                db_info.append(f"설명: {display_desc}")
        
        # 속성 정보
        properties = db.get("properties", {})
        if properties:
            db_info.append(f"속성 ({len(properties)}개):")
            for prop_name, prop_info in list(properties.items())[:10]:  # 처음 10개만 표시
                prop_type = prop_info.get("type", "")
                db_info.append(f"  • {prop_name} ({prop_type})")
            
            if len(properties) > 10:
                db_info.append(f"  • ... 및 {len(properties) - 10}개 더")
        
        # 시간 정보
        if created_time:
            formatted_time = self.time_formatter.format_datetime(created_time)
            db_info.append(f"생성일: {formatted_time}")
        
        if last_edited_time:
            formatted_time = self.time_formatter.format_datetime(last_edited_time)
            db_info.append(f"수정일: {formatted_time}")
        
        db_info.append("-" * 30)
        return db_info


class NotionDatabaseQueryGenerator:
    """Notion 데이터베이스 쿼리 결과를 생성하는 클래스"""
    
    def __init__(self):
        self.property_formatter = NotionPropertyFormatter()
        self.time_formatter = NotionTimeFormatter()
        self.text_processor = NotionTextProcessor()
    
    def generate_query_results(self, results: List[Dict[str, Any]], has_more: bool = False) -> str:
        """데이터베이스 쿼리 결과를 포맷된 텍스트로 생성"""
        if not results:
            return f"📊 데이터베이스에서 조건에 맞는 결과가 없습니다."
        
        formatted_results = []
        formatted_results.append(f"📊 데이터베이스 쿼리 결과 ({len(results)}개)")
        formatted_results.append("=" * 50)
        
        for i, page in enumerate(results, 1):
            page_info = self._format_single_page(page, i)
            formatted_results.extend(page_info)
        
        if has_more:
            formatted_results.append(f"\n💡 더 많은 결과가 있습니다. page_size를 늘려서 더 많은 결과를 확인해보세요.")
        
        return "\n".join(formatted_results)
    
    def _format_single_page(self, page: Dict[str, Any], index: int) -> List[str]:
        """단일 페이지 정보를 포맷팅"""
        page_info = []
        
        page_id = page.get("id", "")
        url = page.get("url", "")
        created_time = page.get("created_time", "")
        last_edited_time = page.get("last_edited_time", "")
        
        page_info.append(f"\n📄 항목 {index}")
        page_info.append(f"ID: {page_id}")
        page_info.append(f"URL: {url}")
        
        # 페이지 속성
        properties = page.get("properties", {})
        if properties:
            formatted_props = self.property_formatter.format_properties(properties)
            
            # 제목 찾기
            title = self.property_formatter.extract_title(formatted_props)
            if title:
                page_info.append(f"제목: {title}")
            
            # 모든 속성 표시
            page_info.append("속성:")
            for prop_name, prop_value in formatted_props.items():
                if prop_value:
                    display_value = self.text_processor.format_display_value(prop_value)
                    page_info.append(f"  • {prop_name}: {display_value}")
        
        # 시간 정보
        if created_time:
            formatted_time = self.time_formatter.format_datetime(created_time)
            page_info.append(f"생성일: {formatted_time}")
        
        if last_edited_time:
            formatted_time = self.time_formatter.format_datetime(last_edited_time)
            page_info.append(f"수정일: {formatted_time}")
        
        page_info.append("-" * 30)
        return page_info
