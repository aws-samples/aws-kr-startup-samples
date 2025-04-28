# MCP 튜토리얼 모듈 3 - Streamlit MCP 호스트

이 모듈은 Model Context Protocol(MCP)을 활용하여 Streamlit 기반 대화형 웹 애플리케이션을 구축하는 방법을 보여줍니다. Amazon Bedrock과 LangChain을 통합하여 AI 모델을 활용한 인터랙티브한 MCP 서버-클라이언트 시스템을 구현합니다.

## 프로젝트 구조

- `app.py`: Streamlit을 사용한 메인 웹 애플리케이션
- `src/server.py`: 기본 수학 연산을 제공하는 간단한 MCP 서버
- `src/client.py`: MCP 클라이언트 구현 및 Amazon Bedrock 모델 연결
- `requirements.txt`: 필요한 패키지 목록

## 기능

- MCP 서버와 클라이언트 간 통신
- Streamlit을 통한 대화형 웹 인터페이스
- Amazon Bedrock 모델과 LangChain 통합
- 간단한 수학 연산 도구 제공 (덧셈, 곱셈)

## 설치 방법

1. 가상 환경 생성 및 활성화

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 또는 
.venv\Scripts\activate  # Windows
```

2. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
streamlit run app.py
```

브라우저에서 Streamlit 앱이 열리면:

1. 사이드바에서 설정 확인 (모델 ID, AWS 리전, 서버 스크립트 경로)
2. "서버 연결" 버튼 클릭
3. 연결 성공 후 채팅창에서 메시지 입력

## 참고사항

- AWS 계정 및 적절한 권한이 필요합니다
- Amazon Bedrock 모델 사용을 위한 액세스 권한이 설정되어 있어야 합니다
