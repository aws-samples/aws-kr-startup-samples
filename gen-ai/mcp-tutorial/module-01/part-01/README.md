# Local MCP Server 구축 및 Claude Desktop 연동

## 개요
이 모듈에서는 로컬 환경에서 MCP(Model Context Protocol) 서버를 구축하고 Claude Desktop과 연동하는 방법을 학습합니다. MCP 서버를 통해 LLM이 외부 데이터 소스나 도구에 접근할 수 있도록 설정하는 과정을 실습합니다.

## 주요 개념
MCP(Model Context Protocol) 서버는 LLM(Large Language Model)과 외부 데이터 소스나 도구를 연결하는 표준화된 방법을 제공하는 서버입니다. MCP 서버는 특정 기능을 표준화된 Model Context Protocol을 통해 노출시키며 세 가지 주요 기능을 제공할 수 있습니다:

이 과정에서 MCP Server는 MCP Client와 표준화된 방식으로 통신합니다.
![Claude Desktop](../part-01/assets/images/mcp.jpg)

사용자는 [Claude Desktop](https://claude.ai/download)과 같은 MCP 클라이언트를 통해 이러한 기능에 쉽게 접근할 수 있습니다. Claude Desktop은 MCP 호스트 역할을 하며, 사용자의 질문을 Claude에 전달하고, Claude가 필요에 따라 MCP 서버의 도구를 호출하도록 합니다. 서버는 요청된 데이터나 기능을 처리한 후 결과를 클라이언트에 반환하고, 이 정보는 다시 Claude에게 전달되어 최종적으로 자연어 형태의 응답으로 사용자에게 제공됩니다.

## 사전 준비사항

### 1. Claude Desktop 설치 및 설정
1. [Claude Desktop](https://claude.ai/download)을 운영체제에 맞게 다운로드하고 설치합니다.
2. [For Claude Desktop Users](https://modelcontextprotocol.io/quickstart/user) 가이드에 따라 MCP Host 설정을 완료합니다.

> 💡 **참고**: Claude Desktop은 MCP 서버와 통신하기 위한 클라이언트 역할을 합니다.

### 2. uv 설치
[uv](https://github.com/astral-sh/uv)는 Python 패키지 설치 및 가상 환경 관리를 위한 빠른 도구입니다. 터미널에서 다음 명령어를 실행합니다:
```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치가 완료되면 다음 명령어로 설치 여부를 확인합니다:
```bash
uv --version
```

> 💡 **팁**: 설치 후 터미널을 재시작해야 할 수 있습니다. 만약 `uv` 명령어가 인식되지 않는다면, 터미널을 재시작하거나 PATH 환경 변수에 uv가 추가되었는지 확인하세요.

### 실습 1: Weather API MCP Server 만들기

1. 먼저 로컬에서 아래 명령어를 실행하여 파이썬 프로젝트를 구성합니다.
    ```bash
    uv init weather
    cd weather

    uv venv
    source .venv/bin/activate

    uv add "mcp[cli]" httpx

    touch weather.py
    ```

2. 생성한 `weather.py`의 내용은 [weather.py](./src/example-1/weather.py) 파일을 복사하여 붙여 넣습니다.
    > 💡 **참고**: 이 스크립트는 미국 국립 기상 서비스 API를 통해 날씨 정보를 가져오는 MCP 서버를 구현합니다. 사용자의 프롬프트로부터 날씨를 받을 때, `get_alerts`, `get_forecast`를 활용하여 위도와 경보를 파악하고 기상 정보를 가져오도록 동작합니다.

3. Claude Desktop에서 확인하기 위해 `/Library/Application\ Support/Claude/claude_desktop_config.json` 파일을 수정합니다:
   ```json
   {
       "mcpServers": {
           "weather": {
               "command": "uv",
               "args": [
                   "--directory",
                   "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather",
                   "run",
                   "weather.py"
               ]
           }
       }
   }
   ```
   > 💡 **팁**: 파일을 찾기 어려운 경우, Claude Desktop을 실행하고 Settings -> Developer -> Edit Config 에서 찾아보세요.
   > ![ClaudeDesktopSetting](./assets/images/ClaudeFindSetting.png)

4. Claude Desktop을 로컬에서 실행하고 날씨를 질의합니다.
   ![ClaudeMCPWeahter](./assets/images/ClaudeMCPWeather.png)

### 실습 2: Amazon Bedrock Nova Canvas MCP 서버 만들기

이제 AWS Resource를 활용한 MCP Server를 만들어 보겠습니다. Claude Desktop에서 자연어로 [Amazon Nova Canvas](https://aws.amazon.com/ko/ai/generative-ai/nova/creative/) 모델을 호출하여 이미지를 생성하는 예시입니다.

1. 먼저 로컬에서 아래 명령어를 실행하여 파이썬 프로젝트를 구성합니다.
    ```bash
    uv init mcp-nova-canvas
    cd mcp-nova-canvas

    uv venv
    source .venv/bin/activate

    uv add "mcp[cli]"
    ```

2. 필요한 종속성을 pyproject.toml에 설정합니다.
    ```toml
    [project]
    name = "mcp-server-amazon-nova-canvas"
    version = "0.1.0"
    description = "Add your description here"
    readme = "README.md"
    requires-python = ">=3.11"
    dependencies = [
        "boto3>=1.37.24",
        "httpx>=0.28.1",
        "mcp[cli]>=1.6.0",
        "pillow>=11.1.0",
        "uuid>=1.30",
        "loguru"
    ]
    ```

3. main.py 파일에 [mcp-nova-canvas.py](./src/example-2/mcp-nova-canvas.py)를 붙여넣습니다.

4. Claude Desktop에서 확인하기 위해 `/Library/Application\ Support/Claude/claude_desktop_config.json` 파일에 아래 내용을 추가합니다.
    ```json
    {
        "mcpServers": {
            "canvas": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/ABSOLUTE/ATH/TO/PARENT/FOLDER/mcp-server-amazon-nova-canvas",
                    "run",
                    "main.py"
                ]
            }
        }
    }
    ```
    > 💡 **참고**: AWS_PROFILE이 로컬에 없는 경우, ENV에 Credential("AWS_ACCESS_KEY_ID, "AWS_SECRET_ACCESS_KEY")을 추가하여 진행할 수 있습니다. 가급적 Profile을 활용해야하며 Credential을 활용할 경우 외부에 노출되지 않도록 유의하세요.

5. Claude Desktop을 재실행하여 "generate_image PROMPT"를 입력합니다.
    ![image](./assets/images/mcp-nova-canvas.png)

6. output 폴더에서 이미지를 확인합니다.
    ![image](./assets/images/nova-flower.png)

## 요약
이 모듈에서는 로컬 환경에서 MCP 서버를 구축하고 Claude Desktop과 연동하는 방법을 학습했습니다. Weather API를 활용한 MCP 서버를 구현하여 Claude가 실시간 날씨 정보에 접근할 수 있도록 설정했습니다. 이를 통해 LLM이 외부 데이터 소스와 상호작용하는 방법의 기초를 이해할 수 있습니다.

## 참고 자료
- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/)
- [Claude Desktop 다운로드](https://claude.ai/download)
- [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)
