# Bedrock Multi-Tenant SaaS with Token Metering

이 프로젝트는 AWS CDK를 사용하여 멀티테넌트 SaaS 환경에서 Amazon Bedrock의 토큰 사용량을 미터링하는 시스템을 구축합니다.

## 🏗️ SaaS 구조 개요

이 샘플은 **단순하고 실용적인 SaaS 구조**로 구현되었습니다:

### 📋 핵심 컨셉
**고정된 모델 사용**
- 모든 요청에 대해 고정된 모델 사용 (실제 환경에서는 사용자에게 다양한 모델 선택 옵션 제공 권장)
- 테넌트는 프롬프트만 입력하면 됨

**빌링 중심 설계**
- 토큰 사용량은 SaaS 제공자의 빌링 목적으로 수집
- 테넌트에게는 응답 텍스트만 제공
- CloudWatch Logs와 Athena를 통한 사용량 분석

**단순한 API**
```javascript
// 테넌트 관점: 단순한 프롬프트 입력
{
  "prompt": "AWS에 대해 설명해주세요."
}

// 응답: 텍스트만 제공
{
  "response": "AWS는 아마존이 제공하는 클라우드 컴퓨팅 플랫폼입니다..."
}
```

## 📁 프로젝트 구조

```
bedrock-saas-metering/
├── bin/
│   └── app.ts                           # CDK 앱 엔트리포인트
├── lib/
│   ├── bedrock-metering-stack.ts        # 메인 API 스택 (Cognito, API Gateway, Lambda)
│   └── metering-analytics-stack.ts      # 분석 스택 (S3, Glue, Athena)

├── package.json                         # 의존성 및 스크립트
├── cdk.json                            # CDK 설정
├── tsconfig.json                       # TypeScript 설정
├── .gitignore                          # Git 무시 파일
└── README.md                           # 이 파일
```

## 🏛️ 아키텍처 개요

### 주요 구성 요소

1. **인증 및 권한 관리**
   - Amazon Cognito User Pool: 테넌트별 사용자 인증
   - JWT 토큰을 통한 테넌트 식별

2. **API 서비스**
   - API Gateway: RESTful API 엔드포인트
   - Lambda Function: Bedrock 호출 및 토큰 미터링
   - Cognito Authorizer: JWT 토큰 기반 인증

3. **AI 서비스**
   - Amazon Bedrock: Claude 3 Haiku 모델 사용
   - 토큰 사용량 추적 (입력/출력 토큰)

4. **미터링 및 분석**
   - CloudWatch Logs: 실시간 토큰 사용량 로깅
   - S3: 로그 데이터 장기 저장
   - AWS Glue: 데이터 카탈로그 및 스키마 관리
   - Amazon Athena: SQL 기반 사용량 분석

## 🚀 배포 방법

### 사전 요구사항

```bash
# Node.js 및 npm 설치 확인
node --version
npm --version

# AWS CLI 설정
aws configure

# CDK CLI 설치
npm install -g aws-cdk
```

### 프로젝트 설정

```bash
# 의존성 설치
npm install

# TypeScript 컴파일
npm run build

# CDK 부트스트랩 (최초 1회)
cdk bootstrap
```

### 배포

```bash
# 모든 스택 배포
npm run deploy

# 또는 개별 스택 배포
cdk deploy BedrockMeteringStack
cdk deploy MeteringAnalyticsStack
```

## 💻 사용 방법

**⚠️ 보안 주의사항**
- **절대 하드코딩 금지**: 실제 배포 값들(USER_POOL_ID, CLIENT_ID, API_URL 등)을 코드에 직접 입력하지 마세요
- **환경변수 사용**: 테스트 시에는 환경변수나 별도 설정 파일(.env, config.json 등)을 사용하세요
- **Git 보안**: 민감한 정보가 포함된 파일을 Git에 커밋하지 마세요
- **사용자 정의 값**: 아래 예제의 모든 `<YOUR_XXX>` 값들은 사용자가 직접 설정해야 하는 값입니다

**⚠️ 중요: 배포 완료 후 설정 값 확인**

CDK 배포가 완료되면 터미널에 다음과 같은 Outputs가 표시됩니다:
```
BedrockMeteringStack.UserPoolId = ap-northeast-2_AbCdEfGhI
BedrockMeteringStack.UserPoolClientId = 1a2b3c4d5e6f7g8h9i0j1k2l3m
BedrockMeteringStack.ApiGatewayUrl = https://abc123def4.execute-api.ap-northeast-2.amazonaws.com/prod/
```

아래 사용 예제에서 `<USER_POOL_ID>`, `<USER_POOL_CLIENT_ID>`, `<API_GATEWAY_URL>` 등의 꺽쇠 괄호로 표시된 부분은 위 Outputs에서 해당하는 실제 값으로 복사해서 사용하세요.

### 1. API 테스트 (CLI 명령어)

#### 1단계: 사용자 생성 및 비밀번호 설정

**⚠️ 사용자 설정 필요 값들:**
- `<USER_POOL_ID>`: CDK 배포 후 출력되는 실제 User Pool ID
- `<YOUR_USERNAME>`: 원하는 사용자명 (예: tenant1-user1, company-admin 등)
- `<YOUR_EMAIL>`: 실제 이메일 주소
- `<YOUR_TENANT_ID>`: 테넌트 식별자 (예: tenant-001, company-alpha 등)
- `<YOUR_TEMP_PASSWORD>`: 임시 비밀번호 (8자 이상, 대소문자+숫자+특수문자)
- `<YOUR_PASSWORD>`: 실제 사용할 비밀번호 (8자 이상, 대소문자+숫자+특수문자)

```bash
# 1. 사용자 생성 (임시 비밀번호)
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username <YOUR_USERNAME> \
  --user-attributes Name=email,Value=<YOUR_EMAIL> Name=custom:tenant_id,Value=<YOUR_TENANT_ID> \
  --temporary-password <YOUR_TEMP_PASSWORD> \
  --message-action SUPPRESS

# 2. 비밀번호 영구 설정 (임시 비밀번호를 실제 비밀번호로 변경)
aws cognito-idp admin-set-user-password \
  --user-pool-id <USER_POOL_ID> \
  --username <YOUR_USERNAME> \
  --password <YOUR_PASSWORD> \
  --permanent
```

#### 2단계: 로그인하여 토큰 획득

**⚠️ 사용자 설정 필요 값들:**
- `<USER_POOL_CLIENT_ID>`: CDK 배포 후 출력되는 실제 Client ID
- `<YOUR_USERNAME>`: 1단계에서 생성한 사용자명
- `<YOUR_PASSWORD>`: 1단계에서 설정한 비밀번호

```bash
# Cognito 로그인 (액세스 토큰 획득)
aws cognito-idp initiate-auth \
  --client-id <USER_POOL_CLIENT_ID> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=<YOUR_USERNAME>,PASSWORD=<YOUR_PASSWORD>
```

위 명령어 실행 후 응답에서 `IdToken` 값을 복사하세요 (테넌트 ID 정보가 포함됨):
```json
{
    "AuthenticationResult": {
        "AccessToken": "abCDefGhIjKlMnOpQrStUvWxYz123456...",
        "IdToken": "xyZ789AbCdEfGhIjKlMnOpQrStUvWx...",  // 이 값을 복사 (테넌트 ID 포함)
        "ExpiresIn": 3600,
        "TokenType": "Bearer"
    }
}
```

#### 3단계: API 호출 테스트

**⚠️ 사용자 설정 필요 값들:**
- `<API_GATEWAY_URL>`: CDK 배포 후 출력되는 실제 API Gateway URL
- `<YOUR_ID_TOKEN>`: 2단계에서 획득한 IdToken 값 (테넌트 ID 포함)
- `<YOUR_PROMPT>`: 테스트하고 싶은 프롬프트 내용

```bash
# Bedrock API 호출 (위에서 복사한 IdToken을 사용)
curl -X POST <API_GATEWAY_URL>/bedrock/chat \
  -H "Authorization: Bearer <YOUR_ID_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "<YOUR_PROMPT>"
  }'
```

**💡 완전한 예시 (모든 값을 실제 값으로 대체):**
```bash
# 예시: 모든 플레이스홀더를 실제 값으로 대체한 완전한 명령어
curl -X POST https://abc123def4.execute-api.ap-northeast-2.amazonaws.com/prod/bedrock/chat \
  -H "Authorization: Bearer xyZ789AbCdEfGhIjKlMnOpQrStUvWx..." \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "AWS Lambda에 대해 설명해주세요."
  }'
```

**예상 응답:**
```json
{
  "response": "AWS Lambda는 서버리스 컴퓨팅 서비스로, 서버를 관리하지 않고도 코드를 실행할 수 있게 해줍니다..."
}
```

### 2. 사용량 분석 쿼리

**⚠️ 중요: 데이터 저장 방식 이해**

이 시스템은 **배치 처리 방식**으로 CloudWatch Logs 데이터를 S3에 저장합니다:

- **자동 스케줄**: 매일 UTC 1시(한국시간 오전 10시)에 전날 데이터를 S3로 내보냄
- **실시간 저장 아님**: API 호출 직후에는 S3에 데이터가 없음
- **Athena 쿼리**: S3에 데이터가 있어야 쿼리 가능

**즉시 테스트하려면 수동으로 데이터 내보내기 실행:**

```bash
# 1. Lambda 함수명 확인 (배포 후 AWS 콘솔에서 확인 또는 아래 명령어 사용)
aws lambda list-functions --query 'Functions[?contains(FunctionName, `LogProcessor`)].FunctionName' --output text

# 2. 수동으로 로그 처리 Lambda 실행 (오늘 데이터를 S3로 내보냄)
aws lambda invoke \
  --function-name <LogProcessorFunction명> \
  --payload '{}' \
  response.json

# 3. 실행 결과 확인
cat response.json

# 4. S3에 데이터가 저장되었는지 확인
aws s3 ls s3://<ANALYTICS_BUCKET_NAME>/logs/ --recursive
```

배포 후 Athena에서 다음 쿼리들을 실행할 수 있습니다.

**⚠️ 사용자 설정 필요 값들:**
- `<YEAR>`, `<MONTH>`, `<DAY>`: 조회하고 싶은 실제 날짜 (예: '2025', '12', '07')
- `<YOUR_TENANT_ID>`: 1단계에서 설정한 실제 테넌트 ID (예: 'tenant-001', 'company-alpha')

**Athena에서 쿼리 테스트:**

**🔍 Athena 콘솔 접속 방법:**
1. AWS Athena 콘솔 접속
2. **Workgroup**: `bedrock-metering-workgroup` 선택  
3. **Database**: `bedrock_metering_db` 선택
4. 아래 쿼리들을 복사해서 실행

**1. 기본 데이터 확인 :**
```sql
-- 테넌트 목록 확인 
SELECT DISTINCT tenant_id 
FROM bedrock_metering_db.token_usage_logs 
WHERE year='2025' AND month='12' AND day='07' -- 실제 날짜로 변경 
LIMIT 10;

-- 사용 중인 모델 확인
SELECT DISTINCT model_id 
FROM bedrock_metering_db.token_usage_logs 
WHERE year='2025' AND month='12' AND day='07'-- 실제 날짜로 변경
; 
```

**2. 주요 분석 쿼리 :**

```sql
-- 일별 테넌트별 사용량 분석
SELECT 
    tenant_id,
    DATE(from_iso8601_timestamp(timestamp)) as usage_date,
    SUM(total_tokens) as total_tokens,
    COUNT(*) as request_count,
    AVG(total_tokens) as avg_tokens_per_request
FROM bedrock_metering_db.token_usage_logs
WHERE year = '2025' AND month = '12' AND day = '07'  -- 실제 날짜로 변경
GROUP BY tenant_id, DATE(from_iso8601_timestamp(timestamp))
ORDER BY usage_date DESC, total_tokens DESC;

-- 시간대별 사용 패턴 분석
SELECT 
    EXTRACT(hour FROM from_iso8601_timestamp(timestamp)) as usage_hour,
    tenant_id,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    AVG(total_tokens) as avg_tokens_per_request
FROM bedrock_metering_db.token_usage_logs
WHERE year = '2025' AND month = '12' AND day = '07'  -- 실제 날짜로 변경
GROUP BY EXTRACT(hour FROM from_iso8601_timestamp(timestamp)), tenant_id
ORDER BY usage_hour, total_tokens DESC;
```

## ⭐ 주요 기능

### 토큰 미터링
- 실시간 토큰 사용량 추적 (SaaS 제공자용)
- 테넌트별 사용량 분리
- 입력/출력 토큰 구분 기록

### 보안
- Cognito JWT 토큰 기반 인증
- 테넌트 격리 보장
- API Gateway 레벨 권한 제어

### 분석 및 리포팅
- CloudWatch Logs를 통한 실시간 모니터링
- S3 기반 데이터 레이크
- Athena를 통한 SQL 분석
- 파티션 기반 효율적 쿼리

## 🧹 정리

```bash
# 모든 리소스 삭제
npm run destroy
```

## 📋 참고사항

- Bedrock 모델 사용을 위해 해당 리전에서 모델 액세스 권한이 필요합니다
- 실제 운영 환경에서는 VPC, WAF 등 추가 보안 설정을 고려하세요
- 대용량 데이터 처리 시 Athena 쿼리 비용을 모니터링하세요
- 테넌트별 사용량 제한 및 알람 설정을 권장합니다
