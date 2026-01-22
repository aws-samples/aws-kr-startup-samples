# Security Review Report

**Date:** 2026-01-21
**Reviewed By:** Security Engineering Team
**Scope:** Backend/Frontend/Infrastructure static review (code + IaC + docs)
**Last Updated:** 2026-01-21T23:15 KST

---

## Executive Summary

정적 코드 리뷰 기준, **0개의 Critical, 4개의 High, 3개의 Medium, 3개의 Low** 리스크가 확인되었습니다. 고위험 항목은 CORS 전체 허용, DB SSL 검증 비활성화, 관리자 비밀번호 해싱 약함, 액세스 키 로그 노출 가능성입니다.

| Severity | Count | Status |
|----------|-------|--------|
| Critical (P0) | 0 | ✅ None |
| High (P1) | 4 | 🔴 Action Required |
| Medium (P2) | 3 | 🟡 Recommended |
| Low (P3) | 3 | 🟢 Advisory |

---

## Risk Matrix

| ID | Severity | Category | Location | Status |
|----|----------|----------|----------|--------|
| SEC-001 | P1 | CORS Misconfiguration | backend/src/main.py | 🔴 Open |
| SEC-002 | P1 | DB TLS Verification Disabled | backend/src/db/session.py | 🔴 Open |
| SEC-003 | P1 | Weak Admin Password Hashing | backend/src/api/admin_auth.py, backend/src/config.py | 🔴 Open |
| SEC-004 | P2 | JWT Secret Fallback | backend/src/api/admin_auth.py | 🟡 Open |
| SEC-005 | P3 | Internal Function Name Disclosure | .kiro/steering/tech.md | 🟢 Open |
| SEC-006 | P2 | Token Storage in localStorage | frontend/src/lib/api.ts | 🟡 Open |
| SEC-007 | P3 | Missing Rate Limiting | backend/src/api/admin_auth.py, backend/src/api/proxy_router.py | 🟢 Open |
| SEC-008 | P3 | Default Credentials in Example/Dev Config | backend/.env.example, docker-compose.yml | 🟢 Open |
| SEC-009 | P1 | Sensitive Access Key Logging | backend/src/api/proxy_router.py | 🔴 Open |
| SEC-010 | P2 | Origin Verification Secret Exposure + Public ALB | infra/stacks/cloudfront_stack.py, infra/stacks/compute_stack.py, infra/stacks/network_stack.py | 🟡 Open |

---

## Remediation Roadmap

### Immediate (Within 24 hours)
1. **SEC-001**: CORS origins/methods/headers 제한 및 환경변수 기반 allowlist 적용
2. **SEC-002**: RDS CA 번들로 SSL 검증 활성화 (dev 환경에서만 예외)
3. **SEC-003**: 관리자 비밀번호 해싱을 bcrypt/argon2로 전환
4. **SEC-009**: 로그에서 `/ak/{access_key}` 마스킹 또는 경로 로그 제거

### Short-term (Within 1 week)
5. **SEC-004**: `PROXY_JWT_SECRET` 미설정 시 기동 실패하도록 강제
6. **SEC-006**: httpOnly 쿠키 또는 메모리 토큰 방식으로 전환 (쿠키 사용 시 CSRF 보호 추가)
7. **SEC-010**: `unsafe_unwrap` 제거, CloudFormation 내 시크릿 노출 방지 및 ALB 접근 제한 강화

### Medium-term (Within 1 month)
8. **SEC-007**: Admin 로그인 및 Proxy 엔드포인트에 rate limiting 추가
9. **SEC-008**: 예제/로컬 구성의 기본 자격 증명 제거 또는 강한 경고 추가
10. **SEC-005**: 내부 함수명 문서에서 제거

---

## Reviewed Scope

### Files Reviewed:
- `backend/src/main.py`
- `backend/src/config.py`
- `backend/src/api/proxy_router.py`
- `backend/src/api/admin_auth.py`
- `backend/src/api/admin_users.py`
- `backend/src/api/admin_keys.py`
- `backend/src/api/admin_models.py`
- `backend/src/api/admin_pricing.py`
- `backend/src/api/admin_usage.py`
- `backend/src/api/deps.py`
- `backend/src/proxy/auth.py`
- `backend/src/proxy/budget.py`
- `backend/src/proxy/plan_adapter.py`
- `backend/src/proxy/bedrock_adapter.py`
- `backend/src/security/keys.py`
- `backend/src/security/encryption.py`
- `backend/src/db/session.py`
- `backend/src/db/models.py`
- `backend/src/repositories/user_repository.py`
- `backend/src/repositories/access_key_repository.py`
- `backend/src/logging.py`
- `backend/.env.example`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/LoginPage.tsx`
- `infra/stacks/compute_stack.py`
- `infra/stacks/cloudfront_stack.py`
- `infra/stacks/network_stack.py`
- `infra/stacks/secrets_stack.py`
- `infra/stacks/database_stack.py`
- `docker-compose.yml`
- `.kiro/steering/tech.md`

### Not Reviewed / Missing Context:
- Third-party dependency vulnerabilities (SAST/SCA 필요)
- Runtime container security (이미지 스캔, IAM 최소권한 검증)
- WAF/CloudFront 실제 운영 설정, TLS 인증서 배치 여부
- 로그 보존/마스킹 정책 및 SIEM 연동 구성

---

## Findings (P0 → P4)

### SEC-001: CORS Wildcard Configuration
- **ID:** SEC-001
- **Severity:** P1 (High)
- **Location:** `backend/src/main.py:56-61`
- **Issue:** CORS가 모든 origin (`*`)을 허용하고 credentials를 허용함
- **Why it matters:** 의도치 않은 도메인에서 API 응답을 읽을 수 있어 세션/토큰 전략 변경 시 CSRF/데이터 노출 위험이 커짐
- **Evidence:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Recommendation:**
```python
allowed_origins = [
    "https://<cloudfront-distribution-domain>",
    "https://admin.your-domain.com",
    "http://localhost:5173",
]
allowed_headers = [
    "Authorization",
    "Content-Type",
    "X-API-Key",
    "Anthropic-Version",
    "Anthropic-Beta",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=allowed_headers,
)
```
- **Note:** 관리자 UI가 CloudFront 배포 도메인을 사용한다면 해당 도메인을 allowlist에 포함해야 합니다. 커스텀 도메인(CNAME)을 쓰는 경우 배포 도메인/커스텀 도메인 둘 다 포함하는 것이 안전합니다. 배포 환경별로 `PROXY_CORS_ALLOW_ORIGINS` 같은 환경변수로 관리하는 방식을 권장합니다.
- **Alternative:** CloudFront에서 같은 도메인으로 프론트(`/`)와 API(`/api/*` 또는 `/ak/*`)를 경로 기반으로 라우팅하면 브라우저에서 CORS가 필요 없습니다. 단, 로컬 개발(`http://localhost:5173`)을 위해서는 dev 전용 CORS 허용이 필요할 수 있습니다.
- **Scope note:** Directly related

---

### SEC-002: SSL Certificate Verification Disabled (DB)
- **ID:** SEC-002
- **Severity:** P1 (High)
- **Location:** `backend/src/db/session.py:10-14`
- **Issue:** Aurora/RDS 연결 시 SSL 인증서 검증이 비활성화됨
- **Why it matters:** MITM 공격에 취약해 DB 자격 증명과 데이터 노출 가능
- **Evidence:**
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```
- **Recommendation:**
```python
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations("/path/to/rds-ca-bundle.pem")
```
- **Scope note:** Directly related

---

### SEC-003: Weak Admin Password Hashing Algorithm
- **ID:** SEC-003
- **Severity:** P1 (High)
- **Location:** `backend/src/api/admin_auth.py:32-34`, `backend/src/config.py:137-139`
- **Issue:** 관리자 비밀번호가 SHA256으로 해싱됨 (salt 없음)
- **Why it matters:** GPU 기반 brute-force에 취약, rainbow table 공격 위험
- **Evidence:**
```python
provided_hash = hashlib.sha256(credentials.password.encode()).hexdigest()

password_hash = hashlib.sha256(creds["password"].encode()).hexdigest()
```
- **Recommendation:**
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

pwd_context.verify(plain_password, hashed_password)
```
- **Scope note:** Directly related

---

### SEC-004: JWT Secret Fallback to Random Value
- **ID:** SEC-004
- **Severity:** P2 (Medium)
- **Location:** `backend/src/api/admin_auth.py:23-25`
- **Issue:** JWT secret 미설정 시 런타임에 랜덤 값 생성
- **Why it matters:** 재시작/다중 인스턴스 환경에서 토큰 검증 실패 및 세션 불안정
- **Evidence:**
```python
def _get_jwt_secret() -> str:
    settings = get_settings()
    return settings.jwt_secret or secrets.token_hex(32)
```
- **Recommendation:**
```python
if not settings.jwt_secret:
    raise RuntimeError("PROXY_JWT_SECRET must be configured")
```
- **Scope note:** Directly related

---

### SEC-005: Internal Function Name Disclosure in Docs
- **ID:** SEC-005
- **Severity:** P3 (Low)
- **Location:** `.kiro/steering/tech.md:169`
- **Issue:** 문서에 내부 캐시 무효화 함수명이 노출됨
- **Why it matters:** 내부 운영 동작이 외부 문서로 유출될 경우 공격자에게 힌트를 제공
- **Evidence:**
```markdown
| Budget not updating | Cache TTL is 60s; call `invalidate_budget_cache(user_id)` or wait |
```
- **Recommendation:**
```markdown
| Budget not updating | Cache TTL is 60s; contact DevOps or wait for TTL expiration |
```
- **Scope note:** Directly related

---

### SEC-006: Token Storage in localStorage
- **ID:** SEC-006
- **Severity:** P2 (Medium)
- **Location:** `frontend/src/lib/api.ts:6-16`
- **Issue:** 관리자 JWT 토큰이 localStorage에 저장됨
- **Why it matters:** XSS 발생 시 토큰 탈취 가능 (localStorage는 JS 접근 가능)
- **Evidence:**
```typescript
localStorage.setItem('token', token);
```
- **Recommendation:** httpOnly 쿠키 저장 또는 in-memory 토큰 사용 + CSRF 보호
- **Scope note:** Directly related

---

### SEC-007: Missing Rate Limiting on Admin/Proxy Endpoints
- **ID:** SEC-007
- **Severity:** P3 (Low)
- **Location:** `backend/src/api/admin_auth.py`, `backend/src/api/proxy_router.py`
- **Issue:** 로그인 및 주요 API 엔드포인트에 rate limiting 없음
- **Why it matters:** Brute-force, credential stuffing, DoS 위험 증가
- **Evidence:** SlowAPI/Rate limiter 미들웨어 부재
- **Recommendation:** Admin 로그인 및 `/ak/*`에 IP/키 기반 rate limiting 적용
- **Scope note:** Adjacent

---

### SEC-008: Default Credentials in Example/Dev Config
- **ID:** SEC-008
- **Severity:** P3 (Low)
- **Location:** `backend/.env.example:3-7`, `docker-compose.yml:18-22`
- **Issue:** 예제/로컬 구성에 기본 관리자 해시 및 개발용 시크릿 포함
- **Why it matters:** 기본값을 그대로 운영 환경에 배포할 위험
- **Evidence:**
```
PROXY_ADMIN_PASSWORD_HASH=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
PROXY_KEY_HASHER_SECRET=dev-secret-key-for-local-development
```
- **Recommendation:** 예제에는 placeholder 사용, 운영 환경에서 필수 설정 강제
- **Scope note:** Directly related

---

### SEC-009: Sensitive Access Key Logged in Request Path
- **ID:** SEC-009
- **Severity:** P1 (High)
- **Location:** `backend/src/api/proxy_router.py:62-94`
- **Issue:** `/ak/{access_key}` 경로가 로그에 그대로 기록됨
- **Why it matters:** 액세스 키는 인증 수단이므로 로그 유출 시 즉시 악용 가능
- **Evidence:**
```python
method, path = _extract_request_info(raw_request)
logger.info(
    "api_request",
    request_id=ctx.request_id,
    method=method,
    path=path,
)
```
- **Recommendation:** access_key 마스킹(예: `ak_***`) 또는 경로 로깅 제거
- **Scope note:** Directly related

---

### SEC-010: Origin Verification Secret Exposure + Public ALB
- **ID:** SEC-010
- **Severity:** P2 (Medium)
- **Location:** `infra/stacks/cloudfront_stack.py:34-40`, `infra/stacks/compute_stack.py:150-160`, `infra/stacks/network_stack.py:37-46`
- **Issue:** `unsafe_unwrap()`로 시크릿을 CFN 템플릿에 평문 포함, ALB가 0.0.0.0/0에 노출됨
- **Why it matters:** 템플릿/변경 이력 접근 가능한 사용자에게 시크릿 노출 가능. 헤더 기반 보호가 단일 방어선으로 작동
- **Evidence:**
```python
custom_headers={
    "X-Origin-Verify": self.origin_verify_secret.secret_value.unsafe_unwrap(),
}

self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
```
- **Recommendation:** Secrets Manager dynamic reference 사용, ALB를 CloudFront prefix list/WAF로 제한, origin HTTPS 적용 검토
- **Scope note:** Directly related

---

## Quick Wins

1. ✅ **SQL Injection**: SQLAlchemy ORM 사용으로 파라미터화된 쿼리 적용됨
2. ✅ **Access Key Hashing**: HMAC-SHA256으로 키 해싱 처리
3. ✅ **Secrets Management**: AWS Secrets Manager 통합으로 시크릿 외부화
4. ✅ **Key Encryption**: Bedrock API 키는 KMS/AES-GCM으로 암호화됨
5. ✅ **Timing-Safe Comparison**: `secrets.compare_digest` 사용
6. ✅ **No Dangerous Functions**: `eval`, `exec`, `pickle`, unsafe `yaml.load` 미사용
7. ✅ **DB Storage Encryption**: Aurora storage_encrypted 적용

---

## Open Questions

1. **Audit Logging**: 관리자 작업에 대한 감사 로그 수집/보존 정책 확인 필요
2. **Token Revocation**: 관리자 토큰 강제 폐기/로그아웃 기능 필요 여부
3. **Edge Controls**: WAF, IP allowlist, CloudFront rate limiting 적용 여부
4. **Dependency Vulnerabilities**: `pip-audit`/`npm audit` 등 의존성 스캔 필요

---

## OWASP Top 10 Compliance Status

| Category | Status | Notes |
|----------|--------|-------|
| A01:2021 Broken Access Control | ⚠️ Partial | CORS 전체 허용, 액세스 키 URL 노출 고려 필요 |
| A02:2021 Cryptographic Failures | ❌ Fail | SHA256 비밀번호 해싱, DB TLS 검증 비활성화 |
| A03:2021 Injection | ✅ Pass | SQLAlchemy ORM 사용 |
| A04:2021 Insecure Design | ⚠️ Partial | 토큰 저장 방식, rate limiting 부재 |
| A05:2021 Security Misconfiguration | ❌ Fail | CORS wildcard, origin secret 노출, 공개 ALB |
| A06:2021 Vulnerable Components | ⚠️ Unknown | 의존성 스캔 필요 |
| A07:2021 Identification and Authentication Failures | ⚠️ Partial | 약한 해싱, JWT secret fallback |
| A08:2021 Software and Data Integrity Failures | ✅ Pass | KMS/AES-GCM 사용 |
| A09:2021 Security Logging and Monitoring Failures | ⚠️ Partial | 로그에 액세스 키 기록 가능성 |
| A10:2021 SSRF | ✅ Pass | 외부 URL 입력 제한됨 |

---

**Review Completed:** 2026-01-21T23:15 KST
**Next Review:** 2026-02-21 (Monthly)
**Status:** REQUIRES REMEDIATION
