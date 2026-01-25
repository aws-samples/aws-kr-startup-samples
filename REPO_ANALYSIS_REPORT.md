# AWS KR Startup Samples Repository Analysis Report

**Report Date**: 2026-01-25  
**Purpose**: APJ 공통 Repository 전환을 위한 정리 및 권장사항

---

## 📊 Executive Summary

| 항목 | 수치 |
|------|------|
| 총 카테고리 | 8개 |
| 총 프로젝트 | 29개 |
| 활성 프로젝트 (3개월 내 업데이트) | 8개 |
| 정리 권장 프로젝트 | 6개 |
| 통합 권장 프로젝트 | 4개 (RAG 관련) |

---

## 📁 Repository 구조 분석

### 카테고리별 프로젝트 현황

```
aws-kr-startup-samples/
├── gen-ai/              # 20개 프로젝트 (가장 활발)
├── database/            # 1개 프로젝트
├── observability/       # 1개 프로젝트
├── analytics/           # 1개 프로젝트
├── machine-learning/    # 2개 프로젝트
├── saas/                # 1개 프로젝트
├── security/            # 1개 프로젝트
└── kiro/                # 2개 프로젝트
```

---

## 🟢 유지 권장 프로젝트 (Active & High Value)

### Tier 1: 핵심 프로젝트 (최근 활발, APJ 공통 가치 높음)

| 프로젝트 | 마지막 업데이트 | 기술 스택 | 설명 |
|----------|----------------|-----------|------|
| `gen-ai/claude-code-proxy` | 2026-01-25 | Python, FastAPI, React, CDK | Claude Code 프록시 서비스, Bedrock 연동 |
| `gen-ai/strands-agents-chatbot` | 2026-01-05 | Python, React, Strands Agents | AI Agent 기반 AWS 리소스 관리 챗봇 |
| `gen-ai/fashion-king` | 2026-01-03 | Python, React, SageMaker, CDK | AI 패션 스타일링 데모 |
| `gen-ai/code-execution-with-mcp-strands-sdk` | 2025-11-25 | Python, Strands, MCP | MCP 코드 실행 데모 |
| `saas/bedrock-saas-metering` | 2026-01-05 | TypeScript, CDK | Bedrock 멀티테넌트 토큰 미터링 |
| `kiro/agents/code-review` | 2026-01-05 | JSON, Markdown | Kiro 코드 리뷰 에이전트 |

### Tier 2: 유지 권장 (안정적, 교육 가치 높음)

| 프로젝트 | 마지막 업데이트 | 기술 스택 | 설명 |
|----------|----------------|-----------|------|
| `gen-ai/rag-with-knowledge-bases-for-amazon-bedrock` | 2025-10-22 | Python, Jupyter | Bedrock KB 워크샵 (가장 포괄적) |
| `gen-ai/rag-with-amazon-bedrock-knowledge-bases-using-s3-vectors` | 2025-07-31 | Python | S3 Vectors 기반 RAG |
| `security/waf-log-analysis-duckdb` | 2025-11-12 | Python, CDK, DuckDB | WAF 로그 분석 |
| `database/milvus-on-aws` | 2025-07-10 | Kubernetes, Helm | Milvus on EKS |
| `observability/observability-assistant` | 2025-07-25 | Python, Strands, MCP | Grafana 연동 옵저버빌리티 |
| `gen-ai/strands-agent-with-eventbridge-fargate` | 2025-09-23 | Python, CDK | EventBridge + Fargate 패턴 |
| `analytics/cost-optimization/cost-effective-athena-and-dbt` | 2025-08-07 | Python, dbt | Athena 비용 최적화 |
| `machine-learning/sagemaker/wan21-on-sagemaker` | 2025-10-15 | Python, SageMaker | WAN 2.1 모델 배포 |

---

## 🟡 통합/정리 권장 프로젝트

### RAG 프로젝트 통합 권장

현재 유사한 구조의 RAG 프로젝트 4개가 존재합니다. **하나의 통합 프로젝트로 정리**를 권장합니다.

| 현재 프로젝트 | 마지막 업데이트 | 특징 |
|--------------|----------------|------|
| `rag-with-amazon-bedrock-and-opensearch` | 2025-10-15 | Bedrock + OpenSearch |
| `rag-with-amazon-opensearch-and-sagemaker` | 2025-10-15 | SageMaker + OpenSearch |
| `rag-with-amazon-bedrock-and-opensearch-serverless` | 2025-10-15 | Bedrock + AOSS |
| `rag-with-amazon-opensearch-serverless-and-sagemaker` | 2025-10-15 | SageMaker + AOSS |

**권장 조치**:
1. `rag-with-knowledge-bases-for-amazon-bedrock`를 메인 RAG 프로젝트로 유지
2. 위 4개 프로젝트를 하나의 `rag-patterns` 디렉토리로 통합
3. 각 패턴을 서브디렉토리로 구성 (bedrock-opensearch, sagemaker-opensearch, etc.)

---

## 🔴 정리/아카이브 권장 프로젝트

### 즉시 정리 권장

| 프로젝트 | 마지막 업데이트 | 정리 사유 |
|----------|----------------|-----------|
| `gen-ai/video-maker-with-nova-reel` | 2025-04-30 | 9개월 이상 미활동, cdk.out 포함 |
| `gen-ai/bpfdoor-qcli` | 2025-07-01 | 일회성 보안 이슈 대응용, 범용성 낮음 |
| `gen-ai/mcp-server-proxy` | 2025-07-22 | 6개월 미활동, 한국어 README만 존재 |
| `gen-ai/dashboard-agent` | 2025-10-22 | 3개월 미활동, 미완성 상태 |

### 검토 후 결정 필요

| 프로젝트 | 마지막 업데이트 | 검토 사항 |
|----------|----------------|-----------|
| `gen-ai/mcp-tutorial` | 2025-09-17 | MCP 튜토리얼, 업데이트 필요 여부 확인 |
| `gen-ai/slackGateway-confluence-with-knowledge-base-for-amazon-bedrock` | 2025-10-15 | 프로젝트명 정리 필요 |
| `gen-ai/rag-with-knowledge-bases-for-amazon-bedrock-using-L1-cdk-constructs` | 2025-10-15 | L1 CDK 사용, 현재 권장 패턴인지 확인 |
| `gen-ai/contract-analyzer-demo` | 2025-12-06 | README 없음, 문서화 필요 |
| `kiro/power-fetch-openapi` | 2025-12-17 | Kiro 관련, 유지 여부 확인 |
| `machine-learning/sagemaker/qwen3-embedding` | 2025-10-15 | 단일 노트북, 통합 검토 |
| `machine-learning/sagemaker/llava-next-video-model-on-sagemaker-endpoint` | 2025-10-15 | 단일 노트북, 통합 검토 |

---

## 📋 APJ 공통 Repo 전환 권장사항

### 1. 즉시 조치 사항

- [ ] `video-maker-with-nova-reel/backend/cdk.out` 디렉토리 삭제 (빌드 아티팩트)
- [ ] `.venv`, `node_modules` 등 로컬 환경 파일 정리
- [ ] `.DS_Store` 파일 제거 및 `.gitignore` 업데이트

### 2. 문서화 개선

- [ ] 모든 프로젝트에 영문 README.md 추가 (현재 일부 한국어만 존재)
- [ ] 루트 README.md에 프로젝트 카탈로그 테이블 추가
- [ ] 각 프로젝트에 Architecture Diagram 추가
- [ ] CONTRIBUTING.md에 APJ 기여 가이드라인 추가

### 3. 구조 개선

```
aws-apj-startup-samples/           # 이름 변경 권장
├── README.md                      # 프로젝트 카탈로그 포함
├── CONTRIBUTING.md
├── gen-ai/
│   ├── agents/                    # Agent 관련 통합
│   │   ├── strands-chatbot/
│   │   ├── claude-code-proxy/
│   │   └── observability-assistant/
│   ├── rag/                       # RAG 패턴 통합
│   │   ├── knowledge-bases-workshop/
│   │   └── patterns/
│   │       ├── bedrock-opensearch/
│   │       ├── bedrock-aoss/
│   │       └── sagemaker-opensearch/
│   ├── mcp/                       # MCP 관련 통합
│   │   ├── code-execution/
│   │   └── tutorial/
│   └── applications/              # 완성된 애플리케이션
│       ├── fashion-king/
│       └── contract-analyzer/
├── database/
├── machine-learning/
├── saas/
├── security/
├── analytics/
└── kiro/
```

### 4. 품질 기준 수립

APJ 공통 Repo에 포함될 프로젝트 기준:
- [ ] 영문 README.md 필수
- [ ] 아키텍처 다이어그램 포함
- [ ] 최소 6개월 내 업데이트
- [ ] 빌드/배포 가이드 포함
- [ ] 정리된 의존성 파일 (requirements.txt 또는 package.json)

---

## 📈 프로젝트 활동 타임라인

```
2026-01 ████████████████████ claude-code-proxy, strands-chatbot, fashion-king
2025-12 ████████             contract-analyzer, power-fetch-openapi
2025-11 ██████               code-execution-mcp, waf-log-analysis
2025-10 ████████████         RAG projects, dashboard-agent, sagemaker
2025-09 ████                 mcp-tutorial, strands-eventbridge
2025-08 ██                   cost-optimization
2025-07 ████                 milvus, observability, bpfdoor, mcp-proxy
2025-04 ██                   video-maker-nova-reel
```

---

## 🎯 우선순위 액션 아이템

### Phase 1: 즉시 (1주 내)
1. 빌드 아티팩트 및 로컬 환경 파일 정리
2. `video-maker-with-nova-reel`, `bpfdoor-qcli` 아카이브 또는 삭제

### Phase 2: 단기 (1개월 내)
1. RAG 프로젝트 4개 통합
2. 모든 활성 프로젝트 영문 README 추가
3. 루트 README에 프로젝트 카탈로그 추가

### Phase 3: 중기 (3개월 내)
1. 디렉토리 구조 재편성
2. APJ 기여 가이드라인 수립
3. 프로젝트 품질 기준 적용

---

## 📝 Notes

- 이 리포트는 2026-01-25 기준 git log 및 파일 시스템 분석을 기반으로 작성됨
- 각 프로젝트의 실제 사용 빈도나 고객 피드백은 별도 확인 필요
- APJ 팀과의 협의를 통해 최종 정리 범위 결정 권장
