# BPFDoor 악성코드 점검 가이드

한국인터넷진흥원(KISA)에서는 최근 발생한 해킹 사건과 관련하여 백도어 악성코드 'BPFDoor'를 점검하는 방법을 안내하고 있습니다. 이 가이드는 보호나라 보안공지 게시판에서 확인하실 수 있으며, KISA에서 배포한 점검 가이드를 참고하여 시스템 점검을 실시하시기 바랍니다.

## BPFDoor 악성코드란?

KISA BPFDoor 점검 가이드에 따르면, BPFDoor는 Linux 운영체제를 대상으로 하는 고도화된 악성코드입니다. 이 악성코드는 리눅스 커널의 Berkeley Packet Filter(BPF) 기능을 악용하여 시스템에 지속적으로 접근할 수 있으며, 강력한 지속성과 은닉성을 갖추고 있어 탐지와 제거가 매우 어렵습니다.

## 대응 방안

다음과 같은 대응 방안을 권장합니다:
- 최신 커널 패치 및 보안 업데이트 적용
- BPF 사용 제한
- 로그 모니터링 강화
- 호스트 기반 IPS/IDS 활용
- 네트워크 트래픽 분석

## 점검 도구

가이드에서 제공하는 `bpfdoor_bpf.sh`와 `bpfdoor_env.sh`는 BPFDoor 감염 여부를 자동으로 점검하기 위한 셸 스크립트 도구입니다.

### bpfdoor_bpf.sh
이 스크립트는 시스템에 등록된 BPF(Berkeley Packet Filter) 필터를 점검합니다. `ss -0pb`와 같은 명령어를 자동화하여 수동으로 확인하기 어려운 BPF 필터 정보를 분석하고 악성코드의 흔적을 찾아냅니다.

### bpfdoor_env.sh
이 스크립트는 시스템에서 실행 중인 프로세스들의 환경변수를 점검합니다. 다음과 같은 의심스러운 환경변수를 사용하는 프로세스를 식별하여 감염 가능성을 판단합니다:
- `HOME=/tmp` (홈 디렉터리를 임시 폴더로 설정)
- `HISTFILE=/dev/null` (명령어 기록을 남기지 않도록 설정)

이 두 스크립트를 통해 시스템 관리자는 복잡한 명령어를 직접 입력하지 않고도 BPFDoor 악성코드의 주요 특징인 'BPF 필터 사용'과 '특정 환경변수 설정'을 손쉽게 점검할 수 있습니다.

## Amazon EC2에서 BPFDoor 점검하기

Amazon EC2 인스턴스에서 이 스크립트를 활용하여 BPFDoor 악성코드를 점검하려면 AWS Systems Manager를 활용할 수 있습니다. Systems Manager의 Run Command 기능을 사용하면 점검 작업을 자동화할 수 있으며, Amazon Q Developer CLI를 활용하여 작업을 수행하고 결과를 취합하여 리포트를 생성할 수 있습니다.

### 사전 준비사항

**Amazon Q Developer CLI 설정:**
1. Amazon Q Developer CLI를 설치합니다.
2. Builder ID 또는 IAM 계정으로 인증을 완료합니다.

**EC2 인스턴스 요구사항:**
- SSM Agent가 설치되어 있어야 합니다.
- AWS Systems Manager 서비스와 통신할 수 있는 권한을 가진 IAM 인스턴스 프로파일이 연결되어 있어야 합니다.
- SSM Agent가 AWS의 Systems Manager 엔드포인트와 HTTPS(포트 443)를 통해 통신할 수 있어야 합니다.

**AWS CLI 계정 권한:**
- AWS Systems Manager Run Command를 실행할 수 있는 권한이 필요합니다.

### 실행 방법

1. **컨텍스트 등록**
   Amazon Q Developer CLI를 실행하고 다음 파일들을 컨텍스트로 등록합니다:
   - `bpfdoor_bpf.sh`
   - `bpfdoor_env.sh`
   - `bpfdoor_inspection_template.html` (리포트 템플릿)

   ```
   /context add <paths...>
   ```

2. **점검 실행**
   다음과 같은 프롬프트를 입력합니다:

   **프롬프트 예시:**
   ```
   ap-northeast-2 지역에서 실행 중인 EC2 인스턴스에 AWS Systems Manager Run Command 기능을 활용하여 직접 접속한 후, bpfdoor_env.sh와 bpfdoor_bpf.sh 스크립트를 이용해서 BPFDoor 악성코드가 있는지 확인하고, bpfdoor_inspection_template.html 형식으로 리포트를 생성해주세요.
   ```

   > **팁:** 타겟을 명확하게 지정하면 Q Developer CLI의 수행 시간을 단축할 수 있습니다.

3. **결과 확인**
   점검이 완료되면 생성된 리포트를 통해 결과를 확인할 수 있습니다.

이 방법을 통해 여러 EC2 인스턴스에 대한 BPFDoor 악성코드 점검을 효율적으로 수행하고, 체계적인 보안 점검 결과를 얻을 수 있습니다.

위 예제는 Amazon Q Developer CLI를 운영에 적용해볼 수 있는 좋은 사례입니다. 다만, AI가 생성하는 답변의 특성상 내용이 항상 정확하지 않을 수 있으니 중요한 작업에 적용하기 전에는 참고용으로 활용하며 검증하는 과정을 거치는 것이 좋습니다.