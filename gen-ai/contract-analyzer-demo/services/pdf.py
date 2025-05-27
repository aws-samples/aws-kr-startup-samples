"""
PDF 파일 처리 관련 서비스 함수
"""
import os
import tempfile
import time
import pdfplumber
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from datetime import datetime
from io import BytesIO
from utils.fonts import setup_korean_font, handle_korean_text, wrap_text_for_table

def extract_text_from_pdf(pdf_file):
    """PDF 파일에서 텍스트를 추출합니다.
    
    Args:
        pdf_file: Streamlit 업로드 파일 객체
    
    Returns:
        tuple: (전체 텍스트, 추출 시간, 페이지별 텍스트 리스트, 페이지 시작 위치 리스트)
    """
    try:
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_file.getvalue())
            temp_file_path = temp_file.name
        
        # 페이지 정보와 함께 텍스트 추출
        full_text = ""
        pages_text = []
        page_starts = [0]  # 각 페이지가 시작되는 문자 위치 추적
        
        with pdfplumber.open(temp_file_path) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    full_text += extracted_text + "\n\n"
                    pages_text.append(extracted_text)
                    page_starts.append(len(full_text))
        
        # 임시 파일 정리
        os.unlink(temp_file_path)
        
        end_time = time.time()
        extraction_time = end_time - start_time
        
        return full_text, extraction_time, pages_text, page_starts
    except Exception as e:
        print(f"PDF에서 텍스트 추출 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, 0, [], []

def get_pdf_preview_html(pdf_file):
    """PDF 파일의 미리보기 HTML을 생성합니다.
    
    Args:
        pdf_file: Streamlit 업로드 파일 객체
    
    Returns:
        str: HTML 형식의 PDF 미리보기
    """
    try:
        # PDF를 base64로 인코딩
        base64_pdf = base64.b64encode(pdf_file.getvalue()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500px" type="application/pdf"></iframe>'
        return pdf_display
    except Exception as e:
        print(f"PDF 미리보기 생성 오류: {str(e)}")
        return f"<p>PDF 미리보기를 생성할 수 없습니다: {str(e)}</p>"

def generate_risk_analysis_pdf(risk_analysis, file_name, contract_name=None, metrics=None):
    """위험 분석 결과를 PDF로 생성합니다.
    
    Args:
        risk_analysis: 위험 분석 결과 데이터
        file_name: 생성할 PDF 파일 이름
        contract_name: 계약서 이름 (옵션)
        metrics: 성능 지표 (옵션)
    
    Returns:
        BytesIO: PDF 파일 내용을 담은 BytesIO 객체
    """
    try:
        # PDF 버퍼 생성
        buffer = BytesIO()
        
        # PDF 문서 설정 (A4 크기)
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=1.5*cm, leftMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        # 한글 폰트 설정
        font_name = setup_korean_font()
        print(f"PDF 생성에 사용할 폰트: {font_name}")
        
        # 스타일 설정
        styles = getSampleStyleSheet()
        
        # 한글 지원을 위한 사용자 정의 스타일
        styles.add(ParagraphStyle(name='KoreanTitle',
                                 fontName=font_name,
                                 fontSize=18,
                                 leading=22,
                                 alignment=1,  # 중앙 정렬
                                 spaceAfter=12))
        
        styles.add(ParagraphStyle(name='KoreanSubtitle',
                                 fontName=font_name,
                                 fontSize=14,
                                 leading=18,
                                 alignment=0,  # 왼쪽 정렬
                                 spaceAfter=6))
        
        styles.add(ParagraphStyle(name='KoreanNormal',
                                 fontName=font_name,
                                 fontSize=10,
                                 leading=14,
                                 alignment=0))  # 왼쪽 정렬
                                 
        styles.add(ParagraphStyle(name='KoreanTable',
                                 fontName=font_name,
                                 fontSize=9,
                                 leading=12))
        
        # 문서 요소 리스트
        elements = []
        
        # 제목 추가
        title_text = f"계약서 위험 분석 보고서"
        elements.append(Paragraph(handle_korean_text(title_text), styles['KoreanTitle']))
        
        # 계약서 이름 추가 (제공된 경우)
        if contract_name:
            elements.append(Paragraph(f"계약서: {handle_korean_text(contract_name)}", styles['KoreanSubtitle']))
        
        # 생성 날짜 추가
        current_date = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
        elements.append(Paragraph(f"생성 일시: {current_date}", styles['KoreanNormal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # 성능 지표 추가 (제공된 경우)
        if metrics:
            elements.append(Paragraph("분석 성능", styles['KoreanSubtitle']))
            
            metrics_data = [
                ["지표", "값"],
                ["처리 시간", f"{metrics.get('processing_time', 0):.2f}초"],
                ["총 토큰", f"{metrics.get('total_tokens', 0):,}개"],
                ["예상 비용", f"${metrics.get('cost', 0):.6f}"]
            ]
            
            # 테이블 스타일 설정
            metrics_table = Table(metrics_data, colWidths=[4*cm, 10*cm])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), font_name),
                ('FONTSIZE', (0, 0), (1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (1, 0), 8),
                ('BACKGROUND', (0, 1), (1, -1), colors.white),
                ('FONTNAME', (0, 1), (1, -1), font_name),
                ('FONTSIZE', (0, 1), (1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ]))
            elements.append(metrics_table)
            elements.append(Spacer(1, 0.5*cm))
        
        # 위험 분석 결과 추가
        if risk_analysis:
            elements.append(Paragraph("위험 분석 결과", styles['KoreanSubtitle']))
            
            for i, risk in enumerate(risk_analysis):
                # 위험 수준 색상 매핑
                risk_level = risk.get('risk_level', '').strip().lower()
                if risk_level == '높음' or risk_level == 'high':
                    level_color = "red"
                elif risk_level == '중간' or risk_level == 'medium':
                    level_color = "orange"
                elif risk_level == '낮음' or risk_level == 'low':
                    level_color = "green"
                else:
                    level_color = "black"
                
                # 위험 항목 카테고리 및 제목
                category = risk.get('category', '')
                title = risk.get('title', '')
                risk_title = f"<b>{i+1}. {handle_korean_text(category)}</b>: {handle_korean_text(title)}"
                elements.append(Paragraph(risk_title, styles['KoreanNormal']))
                
                # 위험 수준
                level_text = f"<b>위험 수준</b>: <font color='{level_color}'>{handle_korean_text(risk_level)}</font>"
                elements.append(Paragraph(level_text, styles['KoreanNormal']))
                
                # 설명
                description = risk.get('description', '')
                if description:
                    desc_text = f"<b>설명</b>: {handle_korean_text(description)}"
                    elements.append(Paragraph(desc_text, styles['KoreanNormal']))
                
                # 권장사항
                recommendation = risk.get('recommendation', '')
                if recommendation:
                    rec_text = f"<b>권장사항</b>: {handle_korean_text(recommendation)}"
                    elements.append(Paragraph(rec_text, styles['KoreanNormal']))
                
                # 출처
                source = risk.get('source', '')
                if source:
                    source_text = f"<b>출처</b>: {handle_korean_text(source)}"
                    elements.append(Paragraph(source_text, styles['KoreanNormal']))
                
                elements.append(Spacer(1, 0.3*cm))
        
        # 문서 생성
        doc.build(elements)
        
        # 버퍼를 처음으로 되돌림
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"PDF 생성 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None 