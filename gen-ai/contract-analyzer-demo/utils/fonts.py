"""
한글 폰트 설정 관련 유틸리티 함수
"""
import os
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def setup_korean_font():
    """한글 폰트를 설정하고 등록합니다."""
    try:
        # 프로젝트 디렉토리 경로 확인 (Streamlit 환경에서는 __file__이 없을 수 있음)
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # utils 디렉토리에서 상위 디렉토리로 이동
            current_dir = os.path.dirname(current_dir)
        except NameError:
            # Streamlit 환경에서는 현재 작업 디렉토리를 사용
            current_dir = os.getcwd()
            # 만약 jinhyeok/ai-document-form-parser가 현재 경로에 포함되어 있지 않다면
            if not current_dir.endswith('ai-document-form-parser'):
                if os.path.exists('jinhyeok/ai-document-form-parser'):
                    current_dir = os.path.join(current_dir, 'jinhyeok/ai-document-form-parser')
                elif os.path.exists('ai-document-form-parser'):
                    current_dir = os.path.join(current_dir, 'ai-document-form-parser')
        
        fonts_dir = os.path.join(current_dir, "fonts")
        
        print(f"현재 디렉토리: {current_dir}")
        print(f"폰트 디렉토리: {fonts_dir}")
        
        # 폰트 디렉토리 확인
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir, exist_ok=True)
            print(f"폰트 디렉토리 생성: {fonts_dir}")
        
        # 솔뫼 김대건 폰트 파일 확인 (영문 파일명)
        kdg_light_file = os.path.join(fonts_dir, "SolmoeKimDaeGunLight.ttf")
        kdg_medium_file = os.path.join(fonts_dir, "SolmoeKimDaeGunMedium.ttf")
        
        print(f"솔뫼 김대건 Light 폰트 파일 경로: {kdg_light_file}")
        print(f"솔뫼 김대건 Medium 폰트 파일 경로: {kdg_medium_file}")
        
        # 파일 존재 여부 및 크기 확인
        if os.path.exists(kdg_light_file):
            file_size = os.path.getsize(kdg_light_file)
            print(f"솔뫼 김대건 Light 폰트 파일 크기: {file_size} 바이트")
            
            if file_size < 10000:
                print("경고: 솔뫼 김대건 Light 폰트 파일이 손상된 것 같습니다. 파일 크기가 너무 작습니다.")
                return 'Helvetica'
                
            # 솔뫼 김대건 Light 폰트 등록 시도
            try:
                # 기본 솔뫼 김대건 Light 폰트 등록
                pdfmetrics.registerFont(TTFont('SolmoeKimDaeGunLight', kdg_light_file))
                print("솔뫼 김대건 Light 폰트 등록 성공")
                
                # Medium 폰트 등록 시도
                if os.path.exists(kdg_medium_file) and os.path.getsize(kdg_medium_file) > 10000:
                    try:
                        pdfmetrics.registerFont(TTFont('SolmoeKimDaeGunMedium', kdg_medium_file))
                        print("솔뫼 김대건 Medium 폰트 등록 성공")
                        
                        # 폰트 패밀리 등록
                        from reportlab.pdfbase.pdfmetrics import registerFontFamily
                        registerFontFamily('SolmoeKimDaeGun', 
                                         normal='SolmoeKimDaeGunLight', 
                                         bold='SolmoeKimDaeGunMedium')
                        print("솔뫼 김대건 폰트 패밀리 등록 완료")
                    except Exception as e:
                        print(f"솔뫼 김대건 Medium 폰트 등록 실패: {str(e)}")
                
                return 'SolmoeKimDaeGunLight'
            except Exception as e:
                print(f"솔뫼 김대건 Light 폰트 등록 실패 - 상세 에러: {str(e)}")
        else:
            print(f"솔뫼 김대건 Light 폰트 파일을 찾을 수 없습니다: {kdg_light_file}")
        
        # 모든 방법 실패 시 기본 Helvetica 사용 (한글 표시는 안됨)
        print("한글 폰트를 등록할 수 없어 기본 폰트(Helvetica)를 사용합니다. 한글이 제대로 표시되지 않을 수 있습니다.")
        return 'Helvetica'
    except Exception as e:
        print(f"폰트 설정 중 예기치 않은 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 'Helvetica'

def handle_korean_text(text):
    """한글 텍스트를 처리하여 PDF에 올바르게 표시될 수 있도록 합니다."""
    if not text:
        return ""
    return text

def wrap_text_for_table(text, max_width):
    """테이블에 표시될 텍스트를 지정된 최대 너비로 줄바꿈합니다."""
    if not text:
        return ""
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        # 한글은 글자당 2칸으로 계산 (대략적)
        word_length = sum(2 if ord(char) > 127 else 1 for char in word)
        
        if current_length + word_length + len(current_line) > max_width:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
        else:
            current_line.append(word)
            current_length += word_length
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines) 