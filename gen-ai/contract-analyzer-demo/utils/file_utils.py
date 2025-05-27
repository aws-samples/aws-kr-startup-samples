"""
파일 처리를 위한 유틸리티 함수
"""
import os

def read_markdown_file(file_path):
    """마크다운 파일의 내용을 읽어 문자열로 반환합니다.
    
    Args:
        file_path: 마크다운 파일의 경로
        
    Returns:
        파일 내용을 담은 문자열. 파일이 없거나 읽을 수 없을 경우 오류 메시지 반환
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return f"오류: '{file_path}' 파일을 찾을 수 없습니다."
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}" 