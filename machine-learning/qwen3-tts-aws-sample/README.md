# Qwen3-TTS Voice Cloning on AWS EC2

Qwen3-TTS 1.7B 모델 3종을 AWS EC2 GPU 인스턴스에 배포하여 Voice Cloning, Custom Voice, Voice Design 기능을 제공하는 샘플 프로젝트입니다.

## 아키텍처

```
User → CloudFront (HTTPS) → ALB (Custom Header 검증) → Private EC2
```

### 보안 구성
- **EC2**: Private Subnet에 배치, NAT Gateway를 통한 아웃바운드만 허용
- **ALB**: CloudFront Prefix List Security Group으로 보호
- **CloudFront → ALB**: Custom Header (`X-Origin-Verify`)로 직접 ALB 접근 차단
- **HTTPS**: CloudFront에서 HTTPS 강제, Mixed Content 방지

### 인프라
- **인스턴스**: g4dn.xlarge (NVIDIA T4 16GB), Private Subnet
- **AMI**: Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.6 (Ubuntu 22.04)
- **모델**:
  - [Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) - Voice Cloning
  - [Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) - Preset Voices
  - [Qwen3-TTS-12Hz-1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign) - Voice Design
- **UI**: Gradio (포트 7860)

## 사전 요구사항

- AWS CLI 설정 완료
- Node.js 18+ 및 npm
- AWS CDK CLI (`npm install -g aws-cdk`)

## 배포 방법

```bash
cd cdk
npm install
cdk deploy
```

배포 완료 후 출력되는 `CloudFrontUrl`로 접속하면 됩니다.

**참고**: 모델 다운로드에 약 10-15분 소요됩니다. CloudWatch 로그 그룹 `/qwen3-tts-voice-cloning/model-setup`에서 진행 상황을 확인할 수 있습니다.

## 사용 방법

Gradio UI에서 3개의 탭으로 각 모델을 테스트할 수 있습니다.

### Tab 1: Voice Cloning

참조 오디오의 목소리를 복제하여 새로운 텍스트를 읽어줍니다.

| 필드 | 설명 | 예시 |
|-----|-----|-----|
| **Reference Audio** | 복제할 목소리의 샘플 오디오 (3초 이상 권장) | WAV/MP3 파일 업로드 |
| **Reference Text** | Reference Audio에서 말한 내용의 정확한 대본 | "안녕하세요 반갑습니다" |
| **Text to Synthesize** | 복제된 목소리로 생성할 문장 | "오늘 날씨가 좋네요" |
| **Language** | 생성할 음성의 언어 | Korean, English, Chinese, Japanese |

### Tab 2: Custom Voice

9개의 프리셋 음성 중 선택하여 TTS를 수행합니다.

| 필드 | 설명 |
|-----|-----|
| **Text to Synthesize** | 읽어줄 텍스트 |
| **Speaker** | 프리셋 음성 선택 (Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee) |
| **Language** | 언어 선택 |
| **Style Instruction** | (선택) 스타일 지시 (예: "Speak with excitement") |

### Tab 3: Voice Design

자연어로 원하는 음성의 특성을 설명하면 해당 음성으로 TTS를 수행합니다.

| 필드 | 설명 |
|-----|-----|
| **Text to Synthesize** | 읽어줄 텍스트 |
| **Voice Description** | 원하는 음성 특성 설명 |
| **Language** | 언어 선택 |

**Voice Description 예시**
- "A warm, gentle female voice with a slight smile, speaking slowly and softly"
- "차분하고 낮은 톤의 남성 목소리, 뉴스 앵커처럼 또박또박 말함"

## 지원 언어

English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian

## 프로젝트 구조

```
qwen3-tts-aws-sample/
├── README.md
├── cdk/
│   ├── bin/cdk.ts
│   ├── lib/cdk-stack.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── cdk.json
└── scripts/
    ├── setup.sh
    └── server.py
```

## 인프라 삭제

```bash
cd cdk
cdk destroy
```

## 트러블슈팅

### Gradio UI 접속 불가
- CloudFront URL로 접속하고 있는지 확인 (ALB 직접 접속 불가)
- EC2 인스턴스가 running 상태인지 확인
- SSM으로 접속하여 서버 프로세스 확인: `systemctl status gradio-server`

### UI가 깨져 보임 (Mixed Content)
- 브라우저 캐시 삭제 후 재접속
- 시크릿/프라이빗 창에서 접속 시도

### 모델 로딩 실패
- CloudWatch 로그 그룹 `/qwen3-tts-voice-cloning/model-setup` 확인
- GPU 메모리 부족 시 인스턴스 타입 업그레이드 고려 (g4dn.2xlarge 등)

### SSM 접속
```bash
aws ssm start-session --target <instance-id>
tail -f /var/log/model-setup.log
tail -f /var/log/gradio-server.log
```

## 라이선스

이 프로젝트는 샘플 코드입니다. Qwen3-TTS 모델의 라이선스는 [HuggingFace 모델 컬렉션](https://huggingface.co/collections/Qwen/qwen3-tts)을 참조하세요.
