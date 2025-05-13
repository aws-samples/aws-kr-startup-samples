# 개요

Amazon Q Developer를 사용하여 git, npm, docker, aws와 같은 수백 개의 인기 있는 CLI에 대한 자동 완성을 활성화할 수 있습니다. 명령줄용 Amazon Q는 상황에 맞는 정보를 통합하여 사용 사례에 대한 이해를 향상시키고, 관련성 있고 상황 인식이 가능한 응답을 제공할 수 있도록 합니다. 입력을 시작하면 Amazon Q가 상황에 맞는 하위 명령어, 옵션 및 인수를 자동으로 채워줍니다.

이 모듈에서는 [**Part 1: 로컬 MCP 서버 구축 및 Claude Desktop 연동**](../part-01/README.ko.md)에서 만들었던 MCP Server를 Amazon Q Developer CLI와 연동하는 방법을 알아보겠습니다.

# 사전 준비사항

아래 내용은 MacOS 환경을 기준으로 설명합니다. Amazon Q Developer CLI 설치는 [Installing Amazon Q for command line](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html)를 참고하세요.

## 1. Amazon Q Developer CLI 설치하기

```bash
brew install amazon-q
q --version
```

## 2. Amazon Q Developer CLI 로그인하기

Amazon Q Developer CLI는 터미널에서 직접 대화형 채팅 환경을 제공합니다. 명령줄 환경을 벗어나지 않고도 질문하고, AWS 서비스에 대한 도움을 받고, 문제를 해결하고, 코드 조각을 생성할 수 있습니다. Amazon Q로 채팅 세션을 시작하려면 chat 하위 명령을 사용합니다.

```bash
q chat
```

아래와 같이 질문이나 명령을 입력할 수 있는 대화형 채팅 세션이 열립니다.

# 단계 1: Amazon Q Developer CLI에서 MCP 서버 설정하기

홈 디렉토리에 (예 : ~/.aws/amazonq/mcp.json) 설정 파일을 생성합니다. 이 설정은 내 컴퓨터의 모든 프로젝트에 적용됩니다. [**Part 1: 로컬 MCP 서버 구축 및 Claude Desktop 연동**](../part-01/README.ko.md)에서 설정한 값을 그대로 사용합니다.

```json
{
    "mcpServers": {
        "weather": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/aws-kr-startup-samples/gen-ai/mcp-tutorial/module-01/part-01/src/example-1",
                "run",
                "weather.py"
            ]
        }
    }
}
```

MCP 서버가 정상적으로 등록됐는지 CLI에서 `/tools` 명령어로 확인합니다.

```bash
/tools
```

# 단계 2: Amazon Q Developer CLI에서 MCP 서버 확인하기

`What's the weather in Newyork?` 와 같은 질문을 입력하여 응답을 확인합니다.

# 요약

이 모듈에서는 로컬 MCP 서버를 Amazon Q Developer CLI와 연동하는 방법을 학습했습니다. 이전 모듈에서 구축한 MCP 서버를 Amazon Q Developer CLI와 연동함으로써 터미널에서 직접 대화형 채팅을 통해 다양한 정보를 얻고 작업을 수행할 수 있습니다.

# 참고 자료

- [AWS 한국 블로그: Amazon Q Developer CLI, 모델 컨텍스트 프로토콜(MCP) 지원 시작](https://aws.amazon.com/ko/blogs/korea/extend-the-amazon-q-developer-cli-with-mcp/)
- [Using Amazon Q Developer on the command line](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html)
