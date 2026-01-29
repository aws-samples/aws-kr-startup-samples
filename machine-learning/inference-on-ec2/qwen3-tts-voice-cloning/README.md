# Qwen3-TTS Voice Cloning on AWS EC2

Qwen3-TTS-12Hz-1.7B-Base 모델을 AWS EC2 GPU 인스턴스에 배포하여 Voice Cloning 기능을 제공하는 샘플 프로젝트입니다.

## 아키텍처

- **인스턴스**: g4dn.xlarge (NVIDIA T4 16GB)
- **AMI**: Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.6 (Ubuntu 22.04)
- **모델**: [Qwen/Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)
- **UI**: Gradio (포트 7860)

## 사전 요구사항

- AWS CLI 설정 완료
- Node.js 18+ 및 npm
- AWS CDK CLI (`npm install -g aws-cdk`)

## 배포 방법

```bash
cd cdk
npm install
npx cdk deploy
```

배포 완료 후 출력되는 `GradioUrl`로 접속하면 됩니다.

## 사용 방법

### Voice Cloning 입력 필드 설명

| 필드 | 설명 | 예시 |
|-----|-----|-----|
| **Reference Audio** | 복제할 목소리의 샘플 오디오 파일 (3초 이상 권장) | 직접 녹음한 WAV/MP3 파일 업로드 |
| **Reference Text** | Reference Audio에서 말한 내용의 정확한 대본 | "안녕하세요 반갑습니다" |
| **Text to Synthesize** | 복제된 목소리로 새로 생성할 문장 | "오늘 날씨가 좋네요" |
| **Language** | 생성할 음성의 언어 | Korean, English, Chinese, Japanese |

### 사용 예시

1. 본인 목소리로 "테스트 음성입니다"라고 녹음한 파일을 **Reference Audio**에 업로드
2. **Reference Text**에 `테스트 음성입니다` 입력
3. **Text to Synthesize**에 생성하고 싶은 문장 입력:
   ```
   안녕하세요~ 오랜만에 뵙겠습니다. 저는 AWS에서 Solutions Architect로 근무하고 있는 홍길동이라고 해요.
   ```
4. **Language**에서 `Korean` 선택
5. **Submit** 클릭

### 주의사항

- Reference Text는 Reference Audio의 내용과 정확히 일치해야 합니다
- Reference Audio는 3초 이상, 깨끗한 음질을 권장합니다
- HTTP 환경에서는 브라우저 마이크 녹음이 불가능하므로, 미리 녹음한 파일을 업로드하세요

## 프로젝트 구조

```
qwen3-tts-voice-cloning/
├── README.md
├── cdk/
│   ├── bin/cdk.ts
│   ├── lib/cdk-stack.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── cdk.json
└── scripts/
    └── setup.sh
```

## 인프라 삭제

```bash
cd cdk
npx cdk destroy
```

## 보안

Security Group은 기본적으로 7860 포트를 전체 개방(0.0.0.0/0)합니다. 프로덕션 환경에서는 `cdk/lib/cdk-stack.ts`에서 특정 IP 대역만 허용하도록 수정하세요.

## 트러블슈팅

### Gradio UI 접속 불가
- Security Group에서 본인 IP가 허용되어 있는지 확인
- EC2 인스턴스가 running 상태인지 확인

### 모델 로딩 실패
- CloudWatch 로그 그룹 `/qwen3-tts-voice-cloning/model-setup` 확인
- GPU 메모리 부족 시 인스턴스 타입 업그레이드 고려

### 오디오 처리 에러
- ffmpeg이 설치되어 있는지 확인 (setup.sh에 포함됨)
- 지원되는 오디오 포맷: WAV, MP3, FLAC, OGG

## 라이선스

이 프로젝트는 샘플 코드입니다. Qwen3-TTS 모델의 라이선스는 [HuggingFace 모델 페이지](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)를 참조하세요.
