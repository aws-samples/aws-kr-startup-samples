# Llama3 Blossom 8B AWS Inferentia2 배포

AWS CDK를 사용하여 SageMaker에서 한국어 Llama3 Blossom 8B 모델을 Inferentia2 인스턴스에 배포하는 프로젝트입니다.

## 🏗️ 프로젝트 구조

```
llama3-blossom-8b-aws-inf2/
├── bin/
│   └── app.ts                 # CDK 앱 진입점
├── lib/
│   └── sagemaker-llm-stack.ts # 메인 CDK 스택
├── scripts/
│   ├── deploy.sh             # 자동 배포 스크립트
│   └── cleanup.sh            # 리소스 정리 스크립트
├── test/
│   └── test_endpoint.py       # 엔드포인트 테스트 스크립트
├── download_model.py          # HuggingFace 모델 다운로드
├── package_model.py           # 모델 패키징 및 S3 업로드
├── requirements.txt           # Python 의존성
├── package.json              # Node.js 의존성
├── tsconfig.json             # TypeScript 설정
├── cdk.json                  # CDK 설정
└── README.md                 # 이 파일
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- **Node.js 18+** 
- **Python 3.8+**
- **AWS CLI** 설정 완료
- **AWS CDK CLI** 설치
- 충분한 AWS 권한 (SageMaker, IAM, S3, CloudFormation 등)

```bash
# AWS CDK CLI 설치
npm install -g aws-cdk

# AWS 계정 확인
aws sts get-caller-identity
```

### 2. 프로젝트 설정

```bash
# 프로젝트 디렉토리로 이동
cd llama3-blossom-8b-aws-inf2

# 실행 권한 부여
chmod +x scripts/deploy.sh
chmod +x scripts/cleanup.sh
```

### 3. 자동 배포

```bash
# 기본 설정으로 배포
./scripts/deploy.sh

# 커스텀 설정으로 배포
./scripts/deploy.sh --instance-type=ml.inf2.2xlarge --instance-count=2 --volume-size=128
```

#### 배포 옵션

| 옵션 | 설명 | 기본값 | 예시 |
|------|------|--------|------|
| `--model-name` | SageMaker 모델 이름 | `llama3-blsm-8b` | `--model-name=my-model` |
| `--endpoint-name` | SageMaker 엔드포인트 이름 | 자동 생성 | `--endpoint-name=my-endpoint` |
| `--instance-type` | 인스턴스 타입 | `ml.inf2.xlarge` | `--instance-type=ml.inf2.2xlarge` |
| `--instance-count` | 인스턴스 수 | `1` | `--instance-count=2` |
| `--volume-size` | 볼륨 크기 (GB) | `64` | `--volume-size=128` |
| `--health-check-timeout` | 헬스체크 타임아웃 (초) | `600` | `--health-check-timeout=900` |
| `--bucket-name` | S3 버킷 이름 | 자동 생성 | `--bucket-name=my-bucket` |

#### 배포 예시

```bash
# 개발 환경용 (기본)
./scripts/deploy.sh

# 프로덕션 환경용
./scripts/deploy.sh \
  --instance-type=ml.inf2.2xlarge \
  --instance-count=2 \
  --volume-size=128 \
  --health-check-timeout=900

# 커스텀 이름 지정
./scripts/deploy.sh \
  --model-name=llama3-korean-prod \
  --endpoint-name=llama3-korean-endpoint \
  --bucket-name=my-llm-models-bucket
```

### 4. 배포 프로세스

배포 스크립트는 다음 단계를 자동으로 수행합니다:

1. **Python 의존성 설치** - `requirements.txt` 기반
2. **모델 다운로드** - HuggingFace에서 Llama3 Blossom 8B 모델 다운로드
3. **S3 버킷 생성** - 모델 저장용 버킷 자동 생성 (필요시)
4. **모델 패키징** - 모델을 tar.gz로 압축하여 S3에 업로드
5. **CDK 의존성 설치** - Node.js 패키지 설치
6. **CDK 부트스트랩** - AWS 계정/리전에 CDK 초기화
7. **TypeScript 빌드** - CDK 스택 컴파일
8. **CloudFormation 배포** - SageMaker 리소스 생성

### 5. 테스트

```bash
# 엔드포인트 상태 확인 및 테스트
python test/test_endpoint.py <endpoint_name>

# 예시 (배포 완료 후 출력되는 엔드포인트 이름 사용)
python test/test_endpoint.py sm-llama3-kr-inf2-2024-01-01-12-00-00
```

테스트 스크립트는 다음을 수행합니다:
- 엔드포인트 상태 확인
- AI 기술 질문 테스트
- 일반 대화 테스트  
- 코딩 질문 테스트
- 응답 시간 측정

### 6. 리소스 정리

```bash
# 모든 AWS 리소스 정리
./scripts/cleanup.sh
```

## 🔧 주요 구성 요소

### 모델 정보

- **모델**: `Gonsoo/AWS-HF-optimum-neuron-0-0-28-llama-3-Korean-Bllossom-8B`
- **타입**: 한국어 특화 Llama3 8B 모델
- **최적화**: AWS Neuron SDK로 Inferentia2 최적화
- **소스**: HuggingFace Hub

### 인프라 구성

- **컴퓨팅**: AWS Inferentia2 인스턴스 (ml.inf2.xlarge/2xlarge)
- **스토리지**: EBS 볼륨 (기본 64GB, 확장 가능)
- **네트워킹**: VPC 내 프라이빗 서브넷
- **보안**: IAM 역할 기반 최소 권한 원칙

### CDK 스택 특징

- **타입 안전성**: TypeScript로 작성된 인프라 코드
- **모듈화**: 재사용 가능한 컴포넌트 설계
- **환경 변수**: 런타임 설정 지원
- **태깅**: 리소스 관리 및 비용 추적

## 🛠️ 수동 배포 (고급)

자동 배포 스크립트 대신 수동으로 단계별 배포:

```bash
# 1. Python 의존성 설치
pip install -r requirements.txt

# 2. 모델 다운로드
python download_model.py

# 3. 모델 패키징 및 S3 업로드
python package_model.py

# 4. Node.js 의존성 설치
npm install

# 5. CDK 부트스트랩 (최초 1회)
npx cdk bootstrap

# 6. TypeScript 빌드
npm run build

# 7. CloudFormation 템플릿 생성
npx cdk synth

# 8. 변경사항 확인
npx cdk diff

# 9. 배포 실행
npx cdk deploy --require-approval never
```

## 📊 비용 최적화

### 인스턴스 타입별 예상 비용 (시간당)

| 인스턴스 타입 | vCPU | 메모리 | Inferentia2 칩 | 시간당 비용 (USD) |
|---------------|------|--------|----------------|-------------------|
| ml.inf2.xlarge | 4 | 16 GB | 1 | ~$0.76 |
| ml.inf2.2xlarge | 8 | 32 GB | 1 | ~$1.04 |
| ml.inf2.8xlarge | 32 | 128 GB | 2 | ~$2.97 |

### 비용 절약 팁

1. **개발/테스트**: `ml.inf2.xlarge` 사용
2. **프로덕션**: 트래픽에 따라 `ml.inf2.2xlarge` 이상
3. **Auto Scaling**: 트래픽 패턴에 따른 자동 스케일링 설정
4. **스케줄링**: 개발 환경은 업무 시간에만 운영

## 🔍 모니터링 및 로깅

### CloudWatch 메트릭

- **Invocations**: 호출 횟수
- **Duration**: 응답 시간
- **Errors**: 오류율
- **ModelLatency**: 모델 추론 지연시간

### 로그 확인

```bash
# CloudWatch 로그 그룹
/aws/sagemaker/Endpoints/{endpoint-name}

# AWS CLI로 로그 확인
aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker/Endpoints"
```

## 🚨 문제 해결

### 일반적인 문제

1. **배포 실패**
   ```bash
   # CDK 상태 확인
   npx cdk ls
   npx cdk diff
   
   # CloudFormation 스택 상태 확인
   aws cloudformation describe-stacks --stack-name SageMakerLLM
   ```

2. **엔드포인트 생성 실패**
   ```bash
   # SageMaker 엔드포인트 상태 확인
   aws sagemaker describe-endpoint --endpoint-name <endpoint-name>
   
   # 로그 확인
   aws logs filter-log-events --log-group-name "/aws/sagemaker/Endpoints/<endpoint-name>"
   ```

3. **권한 오류**
   - IAM 정책 확인
   - SageMaker 실행 역할 권한 확인
   - S3 버킷 접근 권한 확인

### 디버깅 명령어

```bash
# AWS 계정 정보 확인
aws sts get-caller-identity

# 리전 설정 확인
aws configure get region

# CDK 부트스트랩 상태 확인
aws cloudformation describe-stacks --stack-name CDKToolkit

# S3 버킷 확인
aws s3 ls s3://your-bucket-name/
```

## 📚 참고 자료

- [AWS SageMaker 문서](https://docs.aws.amazon.com/sagemaker/)
- [AWS Inferentia2 가이드](https://docs.aws.amazon.com/dlami/latest/devguide/tutorial-inferentia.html)
- [AWS CDK 문서](https://docs.aws.amazon.com/cdk/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)
- [AWS Neuron SDK](https://awsdocs-neuron.readthedocs-hosted.com/)

## 📄 라이선스

MIT License - 자세한 내용은 LICENSE 파일을 참조하세요.

## 🤝 기여

이슈 리포트나 풀 리퀘스트를 환영합니다. 기여하기 전에 기여 가이드라인을 확인해주세요.
