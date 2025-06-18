import asyncio
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

from notion_formatters import NotionBlockFormatter, NotionPropertyFormatter, NotionTimeFormatter
from notion_validators import NotionIdValidator, NotionParameterValidator, NotionTextProcessor
from notion_result_generators import (
    NotionSearchResultGenerator,
    NotionPageContentGenerator,
    NotionDatabaseListGenerator,
    NotionDatabaseQueryGenerator
)


load_dotenv()

mcp = FastMCP("Notion MCP Server")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"


print(f"Starting Notion MCP Server with API Key: {NOTION_API_KEY}")

HOST = os.getenv("HOST", "0.0.0.0") 
PORT = int(os.getenv("PORT", 8000))

if not NOTION_API_KEY:
    print("NOTION_API_KEY is required.")
    exit(1)

http_client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json"
    },
    timeout=30.0
)

search_result_generator = NotionSearchResultGenerator()
page_content_generator = NotionPageContentGenerator()
database_list_generator = NotionDatabaseListGenerator()
database_query_generator = NotionDatabaseQueryGenerator()
id_validator = NotionIdValidator()
param_validator = NotionParameterValidator()


@mcp.tool()
async def search_notion(
    query: str,
    sort_by: str = "last_edited_time",
    sort_direction: str = "descending",
    page_size: int = 10
) -> str:
    """
    Notion에서 페이지와 데이터베이스를 검색합니다.
    
    Args:
        query: 검색할 키워드
        sort_by: 정렬 기준 (last_edited_time, created_time)
        sort_direction: 정렬 방향 (ascending, descending)
        page_size: 반환할 결과 수 (최대 100)
    
    Returns:
        검색 결과를 포맷된 텍스트로 반환
    """
    try:
        page_size = param_validator.validate_page_size(page_size)
        sort_by = param_validator.validate_sort_by(sort_by)
        sort_direction = param_validator.validate_sort_direction(sort_direction)
        
        search_data = {
            "query": query,
            "sort": {
                "direction": sort_direction,
                "timestamp": sort_by
            },
            "page_size": page_size
        }
        
        response = await http_client.post(f"{NOTION_BASE_URL}/search", json=search_data)
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            return f"Fail to search: {error_msg}"
        
        data = response.json()
        results = data.get("results", [])
        has_more = data.get("has_more", False)
        
        return search_result_generator.generate_search_results(query, results, has_more)
        
    except httpx.TimeoutException:
        return "TimeoutException"
    except httpx.RequestError as e:
        return f"RequestError"
    except Exception as e:
        return f"Exception: {str(e)}"


@mcp.tool()
async def get_notion_page_content(page_id: str, include_children: bool = True) -> str:
    """
    특정 Notion 페이지의 상세 내용을 가져옵니다.
    
    Args:
        page_id: 페이지 ID (URL에서 추출하거나 검색 결과에서 확인)
        include_children: 하위 블록들도 포함할지 여부
    
    Returns:
        페이지의 상세 내용을 포맷된 텍스트로 반환
    """
    try:
        page_id = id_validator.clean_id(page_id)
        
        page_response = await http_client.get(f"{NOTION_BASE_URL}/pages/{page_id}")
        
        if page_response.status_code != 200:
            error_data = page_response.json() if page_response.content else {}
            error_msg = error_data.get("message", f"HTTP {page_response.status_code}")
            return f"Fail to find the page: {error_msg}"
        
        page_data = page_response.json()
        
        blocks = None
        if include_children:
            blocks_response = await http_client.get(f"{NOTION_BASE_URL}/blocks/{page_id}/children")
            
            if blocks_response.status_code == 200:
                blocks_data = blocks_response.json()
                blocks = blocks_data.get("results", [])
        
        # 결과 생성
        return page_content_generator.generate_page_content(page_data, blocks)
        
    except httpx.TimeoutException:
        return "❌ 요청 시간 초과: Notion API 응답이 너무 오래 걸립니다."
    except httpx.RequestError as e:
        return f"❌ 네트워크 오류: {str(e)}"
    except Exception as e:
        return f"❌ 예상치 못한 오류: {str(e)}"


@mcp.tool()
async def list_notion_databases(page_size: int = 10) -> str:
    """
    접근 가능한 Notion 데이터베이스 목록을 가져옵니다.
    
    Args:
        page_size: 반환할 결과 수 (최대 100)
    
    Returns:
        데이터베이스 목록을 포맷된 텍스트로 반환
    """
    try:

        page_size = param_validator.validate_page_size(page_size)
        
        search_data = {
            "filter": {
                "value": "database",
                "property": "object"
            },
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time"
            },
            "page_size": page_size
        }
        
        response = await http_client.post(f"{NOTION_BASE_URL}/search", json=search_data)
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            return f"❌ 데이터베이스 목록 조회 실패: {error_msg}"
        
        data = response.json()
        results = data.get("results", [])
        has_more = data.get("has_more", False)
        
        # 결과 생성
        return database_list_generator.generate_database_list(results, has_more)
        
    except httpx.TimeoutException:
        return "❌ 요청 시간 초과: Notion API 응답이 너무 오래 걸립니다."
    except httpx.RequestError as e:
        return f"❌ 네트워크 오류: {str(e)}"
    except Exception as e:
        return f"❌ 예상치 못한 오류: {str(e)}"


@mcp.tool()
async def query_notion_database(
    database_id: str,
    filter_conditions: Optional[str] = None,
    sorts: Optional[str] = None,
    page_size: int = 10
) -> str:
    """
    특정 Notion 데이터베이스를 쿼리합니다.
    
    Args:
        database_id: 데이터베이스 ID
        filter_conditions: 필터 조건 (JSON 문자열, 선택사항)
        sorts: 정렬 조건 (JSON 문자열, 선택사항)
        page_size: 반환할 결과 수 (최대 100)
    
    Returns:
        쿼리 결과를 포맷된 텍스트로 반환
    """
    try:
        page_size = param_validator.validate_page_size(page_size)
        database_id = id_validator.clean_id(database_id)
        
        query_data = {
            "page_size": page_size
        }
        
        if filter_conditions:
            is_valid, filter_obj, error_msg = param_validator.validate_json_string(filter_conditions, "필터 조건")
            if not is_valid:
                return f"❌ {error_msg}"
            query_data["filter"] = filter_obj
        
        if sorts:
            is_valid, sorts_obj, error_msg = param_validator.validate_json_string(sorts, "정렬 조건")
            if not is_valid:
                return f"❌ {error_msg}"
            query_data["sorts"] = sorts_obj
        
        response = await http_client.post(
            f"{NOTION_BASE_URL}/databases/{database_id}/query",
            json=query_data
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            return f"❌ 데이터베이스 쿼리 실패: {error_msg}"
        
        data = response.json()
        results = data.get("results", [])
        has_more = data.get("has_more", False)
        
        return database_query_generator.generate_query_results(results, has_more)
        
    except httpx.TimeoutException:
        return "❌ 요청 시간 초과: Notion API 응답이 너무 오래 걸립니다."
    except httpx.RequestError as e:
        return f"❌ 네트워크 오류: {str(e)}"
    except Exception as e:
        return f"❌ 예상치 못한 오류: {str(e)}"


async def cleanup():
    """리소스 정리"""
    await http_client.aclose()


# 메인 실행 함수
async def main():
    """원격 HTTP MCP 서버 실행"""
    print("🚀 Notion MCP 원격 HTTP 서버를 시작합니다...")
    print(f"📋 사용 가능한 도구:")
    print(f"  • search_notion: Notion에서 검색")
    print(f"  • get_notion_page_content: 페이지 상세 내용 조회")
    print(f"  • list_notion_databases: 데이터베이스 목록 조회")
    print(f"  • query_notion_database: 데이터베이스 쿼리")
    print(f"🌐 HTTP 서버 주소: http://{HOST}:{PORT}")
    print(f"📡 원격 접근 가능: {'예' if HOST == '0.0.0.0' else '아니오'}")
    print(f"🔑 Notion API 설정: {'완료' if NOTION_API_KEY else '미완료'}")
    print(f"✅ 서버가 준비되었습니다!")
    print(f"📍 MCP over Streamable HTTP 프로토콜로 통신합니다")
    
    try:
        # FastMCP 2.0의 올바른 HTTP 서버 실행 방법
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
    except Exception as e:
        print(f"Exception: {e}")
        raise
    finally:
        await cleanup()


if __name__ == "__main__":
    import sys
    
    try:
        print("🚀 Notion MCP 원격 HTTP 서버를 시작합니다...", file=sys.stderr)
        print(f"📋 사용 가능한 도구:", file=sys.stderr)
        print(f"  • search_notion: Notion에서 검색", file=sys.stderr)
        print(f"  • get_notion_page_content: 페이지 상세 내용 조회", file=sys.stderr)
        print(f"  • list_notion_databases: 데이터베이스 목록 조회", file=sys.stderr)
        print(f"  • query_notion_database: 데이터베이스 쿼리", file=sys.stderr)
        print(f"🌐 HTTP 서버 주소: http://{HOST}:{PORT}", file=sys.stderr)
        print(f"🔑 Notion API 설정: {'완료' if NOTION_API_KEY else '미완료'}", file=sys.stderr)
        print(f"✅ 서버가 준비되었습니다!", file=sys.stderr)
        print(f"📍 MCP over Streamable HTTP (경로: /mcp)", file=sys.stderr)
        
        # 원격 HTTP 서버로 실행 - /mcp 경로 지정
        mcp.run(transport="streamable-http", host=HOST, port=PORT, path="/mcp")
    except KeyboardInterrupt:
        print("\n⏹️  서버를 종료합니다...", file=sys.stderr)
    except Exception as e:
        print(f"❌ 서버 실행 중 오류: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    finally:
        # 정리 작업
        try:
            asyncio.run(cleanup())
        except:
            pass
