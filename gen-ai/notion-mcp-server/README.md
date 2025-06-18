# Notion MCP Server

Notion API를 활용한 MCP (Model Context Protocol) 서버입니다.

## 📋 요구사항

- Docker
- Notion API Key

## 🔑 Notion API Key 발급

1. [Notion 개발자 페이지](https://www.notion.so/my-integrations)에 접속
2. "New integration" 클릭
3. Integration 이름 입력 후 생성
4. "Internal Integration Token" 복사

## 🚀 실행 방법

### 방법 1: Docker Compose 사용 (권장)

**환경변수 설정:**
```bash
# 환경변수로 설정
export NOTION_API_KEY="your_secret_key"

# 또는 .env 파일에 작성
echo "NOTION_API_KEY=your_secret_key" > .env
```

**실행:**
```bash
# 빌드 및 실행
docker-compose up -d

# 중지
docker-compose down
```

### 방법 2: Docker 직접 사용

**이미지 빌드:**
```bash
docker build -t notion-mcp-server .
```

**컨테이너 실행:**
```bash
docker run -d \
  --name notion-mcp \
  -p 8080:8000 \
  -e NOTION_API_KEY="your_secret_key" \
  notion-mcp-server
```

## 🔧 개발 및 디버깅

**개발 모드 실행 (로그 확인):**
```bash
# 포그라운드에서 실행
docker run --rm \
  -p 8080:8000 \
  -e NOTION_API_KEY="your_secret_key" \
  notion-mcp-server
```

**로그 확인:**
```bash
# 컨테이너 로그 확인
docker logs notion-mcp

# 실시간 로그 확인
docker logs -f notion-mcp
```

**컨테이너 내부 접속:**
```bash
docker exec -it notion-mcp /bin/bash
```

## 📄 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.