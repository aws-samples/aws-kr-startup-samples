# CLEANAUTH - MCP Authentication System

이 프로젝트는 MCP(Microservice Control Platform)의 인증 시스템을 위한 환경을 구성합니다.
Public Subnet에 EC2 인스턴스를 생성하여 mcp-client-auth와 mcp-server-auth를 테스트할 수 있는 환경을 제공합니다.

## 1. CDK 배포를 위한 환경 구성

### 사전 요구사항
- AWS CLI가 설치되어 있어야 합니다.
- AWS 계정에 대한 적절한 권한이 필요합니다.
- Python 3.9 이상이 설치되어 있어야 합니다.
- Node.js 14 이상이 설치되어 있어야 합니다.

### CDK 설치 및 환경 설정
```bash
# CDK CLI 설치
npm install -g aws-cdk

# 프로젝트 디렉토리로 이동
cd mcp-auth-cdk

# 가상 환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 필요한 패키지 설치
pip install -r requirements.txt
```

### CDK 부트스트랩 및 배포
```bash
# CDK 부트스트랩 (계정당 한 번만 실행)
cdk bootstrap --context bootstrap=true

# CDK 스택 배포
cdk deploy --parameters VpcId=<your-vpc-id> --parameters PublicSubnetId=<your-subnet-id> --parameters AvailabilityZone=<your-az>
```

### 배포 후 작업
배포가 완료되면 다음과 같은 출력값이 표시됩니다:
- **InstancePublicIP**: EC2 인스턴스의 공개 IP 주소
- **InstanceId**: EC2 인스턴스 ID
- **SSMConnectCommand**: Session Manager를 통해 인스턴스에 연결하는 명령어
- **SecurityGroupUpdateCommand**: 보안 그룹 규칙을 업데이트하는 명령어

보안 그룹 규칙을 업데이트하여 EC2 인스턴스의 IP에서 포트 8080과 8501에 접근할 수 있도록 합니다:
```bash
# 출력된 SecurityGroupUpdateCommand 실행
aws ec2 authorize-security-group-ingress --group-id <security-group-id> --protocol tcp --port 8080 --cidr <instance-ip>/32 --region <region>
aws ec2 authorize-security-group-ingress --group-id <security-group-id> --protocol tcp --port 8501 --cidr <instance-ip>/32 --region <region>
```

## 2. mcp-server-auth 배포 구성

### EC2 인스턴스 접속
AWS Systems Manager Session Manager를 사용하여 EC2 인스턴스에 접속합니다:
```bash
# 출력된 SSMConnectCommand 실행
aws ssm start-session --target <instance-id> --region <region>

# 루트 권한으로 전환 (권한 문제 방지)
sudo su
```

### 서버 설치 및 구성
```bash
# 필요한 패키지 설치
yum update -y
yum install -y git python3 python3-pip


# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/ec2-user/.cargo/bin:$PATH"
uv --version

# mcp-server-auth 디렉토리로 이동
cd mcp-server-auth

# 가상 환경 생성 및 의존성 설치
uv venv --python 3.11
source .venv/bin/activate
uv sync
uv pip install -r ./requirements.txt
```

### Cognito 설정 구성
서버를 실행하기 전에 Cognito 설정을 구성해야 합니다. 다음 두 파일에서 Cognito 설정값을 수정해야 합니다:

1. **서버 설정 수정**:
```bash
# main.py 파일 편집
vi app/main.py
```

다음 부분을 찾아 자신의 Cognito 설정으로 변경합니다:

```python
# Cognito configuration
COGNITO_POOL_ID = os.getenv('COGNITO_POOL_ID', 'your-region_YourPoolId')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', 'your-client-id-value')
COGNITO_REGION = os.getenv('COGNITO_REGION', 'your-region')
```

2. **클라이언트 설정 수정**:
```bash
# client.py 파일 편집
vi ../mcp-client-auth/app/streamlit-app/client.py
```

다음 부분을 찾아 자신의 Cognito 설정으로 변경합니다:

```python
# Initialize Cognito client with environment variables
self.cognito_region = os.getenv('COGNITO_REGION', 'your-region')
self.cognito_client = boto3.client('cognito-idp', region_name=self.cognito_region)
self.cognito_pool_id = os.getenv('COGNITO_POOL_ID', 'your-region_YourPoolId')
self.cognito_client_id = os.getenv('COGNITO_CLIENT_ID', 'your-client-id-value')
self.cognito_client_secret = os.getenv('COGNITO_CLIENT_SECRET', 'your-client-secret-value')
```

vi 편집기 사용법:
- `i` 키를 눌러 편집 모드로 전환
- 설정값 수정
- `ESC` 키를 누른 후 `:wq` 입력하고 Enter 키를 눌러 저장 후 종료

또는 환경 변수를 사용하여 설정할 수도 있습니다:
```bash
export COGNITO_POOL_ID="your-pool-id"
export COGNITO_CLIENT_ID="your-client-id"
export COGNITO_REGION="your-region"
export COGNITO_CLIENT_SECRET="your-client-secret"  # 클라이언트에만 필요
```

### 서버 실행
```bash
# 서버 실행
uv run start
```

### 서버 실행 확인
서버가 정상적으로 실행되면 8080 포트에서 요청을 수신합니다. 다음 명령어로 서버 상태를 확인할 수 있습니다:
```bash
curl http://localhost:8080/health
```

## 3. mcp-client-auth 배포 구성

### 클라이언트 설치 및 구성
새로운 터미널 세션을 열고 EC2 인스턴스에 다시 접속합니다:
```bash
aws ssm start-session --target <instance-id> --region <region>

# 루트 권한으로 전환 (권한 문제 방지)
sudo su
```

그런 다음 클라이언트를 설치하고 구성합니다:
```bash
# cleanauth 디렉토리로 이동
cd /home/ec2-user/cleanauth

# mcp-client-auth 디렉토리로 이동
cd mcp-client-auth

# 가상 환경 생성 및 의존성 설치
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r ./requirements.txt

# 서버 상태 확인
curl http://localhost:8080/health

# 클라이언트 실행
python app/streamlit-app/client.py http://localhost:8080/sse <user-id> <password>
```

### Streamlit 앱 실행 (선택 사항)
Streamlit 앱을 실행하려면 다음 명령어를 사용합니다:
```bash
cd app/streamlit-app
python -m streamlit run app.py
```

### 클라이언트 접속
Streamlit 앱이 실행되면 8501 포트에서 웹 인터페이스를 제공합니다. 웹 브라우저에서 다음 URL로 접속할 수 있습니다:
```
http://<instance-public-ip>:8501
```

## 문제 해결

### 일반적인 문제
1. **연결 문제**
   - 보안 그룹 설정이 올바른지 확인
   - 인스턴스가 실행 중인지 확인
   - 서버와 클라이언트가 모두 실행 중인지 확인

2. **권한 문제**
   - EC2 인스턴스의 IAM 역할에 필요한 권한이 있는지 확인
   - Bedrock 모델 호출 권한이 있는지 확인
   - Cognito 접근 권한이 있는지 확인

3. **의존성 문제**
   - 필요한 모든 패키지가 설치되어 있는지 확인
   - Python 버전이 호환되는지 확인

### Cognito 인증 오류
Cognito 인증 관련 오류가 발생하면 다음을 확인하세요:
- Cognito 설정값(Pool ID, Client ID, Region)이 올바른지 확인
- 사용자가 Cognito 사용자 풀에 등록되어 있는지 확인
- 사용자 계정이 확인되었는지 확인
- 제공한 사용자 ID와 비밀번호가 올바른지 확인

### Bedrock 권한 오류
다음과 같은 오류가 발생하면 IAM 역할에 Bedrock 권한이 없는 것입니다:
```
ERROR    Error in invoke_agent: An error occurred (AccessDeniedException) when calling the Converse operation: User: arn:aws:sts::XXXX:assumed-role/MCPAuthStack-EC2SSMRole/i-XXXX is not authorized to perform: bedrock:InvokeModel
```

이 경우 EC2 인스턴스의 IAM 역할에 다음 권한을 추가해야 합니다:
- bedrock:InvokeModel
- bedrock:Converse
- bedrock:InvokeModelWithResponseStream

### 로그 확인
서버와 클라이언트의 로그를 확인하여 문제를 진단할 수 있습니다:
```bash
# 서버 로그 확인
cd /home/ec2-user/cleanauth/mcp-server-auth
tail -f server.log

# 클라이언트 로그 확인
cd /home/ec2-user/cleanauth/mcp-client-auth
tail -f client.log
```

## 보안 고려사항
- MCP Server/Client 간에 인증 동작 방식에 대한 설명을 위한 샘플로 테스트용도로만 사용하세요.
- 프로덕션 환경에서는 보안 그룹 규칙을 더 엄격하게 설정하세요. 특히나, 가능한 경우 HTTPS를 사용하세요.
- 민감한 정보는 환경 변수나 AWS Secrets Manager를 통해 관리하세요.
- IAM 역할과 정책을 최소 권한 원칙에 따라 설정하세요.
- Cognito 사용자 풀의 보안 설정을 검토하고 필요에 따라 MFA를 활성화하세요.