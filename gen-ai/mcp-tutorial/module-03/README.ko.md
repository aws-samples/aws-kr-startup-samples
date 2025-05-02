# 실습 3: MCP 클라이언트 구축 및 MCP 서버와 연결

이 모듈에서는 MCP(Model Context Protocol) 클라이언트 기반의 Streamlit MCP Host 챗봇을 구축하고, 이전 모듈에서 배포한 MCP 서버와의 연동 방법을 학습합니다. 이를 통해 LLM과 외부 도구 간의 상호작용을 위한 표준 프로토콜인 MCP의 클라이언트 측 구현을 실습합니다.

# 사전 준비사항

## Bedrock 모델 액세스 설정

1. AWS 콘솔 페이지로 접속하여 Amazon Bedrock 서비스로 이동합니다.

2. 좌측 네비게이션의 'Bedrock configurations'에서 '모델 액세스(Model access)'를 선택합니다.

3. '모델 액세스 권한 수정(Modify model access)' 버튼을 클릭하여 '모델 액세스 권한 편집(Edit model access)' 화면으로 이동한 후, Amaon Nova Lite 모델에 대한 액세스 권한을 활성화합니다.

## 가상환경 구성 및 의존성 패키지 설치:

IDE 터미널에서 다음 명령어를 실행하여 Python 가상 환경을 생성합니다:

```bash
uv venv --python 3.11
source .venv/bin/activate
```

다음 명령어를 실행하여 필요한 의존성 패키지를 설치합니다:

```bash
uv pip install -r requirements.txt
```

터미널에서 다음 명령어를 실행하여 MCP Client를 테스트할 수 있습니다.
이때, module-02에서 배포한 MCP Server의 URL 뒤에 `/sse` 엔드포인트를 추가하여 명령행 인자로 전달합니다.

```bash
python app/streamplit-app/client.py <module-02에서 배포한 MCP Server URL>/sse
```

`What's the weather in Newyork?`와 같은 쿼리를 입력하여 응답을 확인합니다. 정상적인 응답이 반환되면 클라이언트 설정이 완료된 것입니다.

# 애플리케이션 확인하기

## 로컬에서 실행하기

IDE 터미널에서 다음 명령어를 실행하여 Streamlit 애플리케이션을 실행합니다.

```bash
streamlit run app/streamplit-app/app.py
```

## AWS 환경에 배포하기

cdk 폴더 내의 `cdk.context.json` 파일을 열어 module-02에서 배포한 cdk outputs 값들을 추가합니다.

```bash
McpServerAmazonECSStack.McpServerAmazonECSStackClusterNameOutput = McpServerAmazonECSStack-***
McpServerAmazonECSStack.McpServerAmazonECSStackListenerArnOutput = arn:aws:elasticloadbalancing:***
McpServerAmazonECSStack.McpServerAmazonECSStackVpcIdOutput = vpc-***
```

```json
{
  "vpc-id": "vpc-***",
  "cluster-name": "McpServerAmazonECSStack-***",
  "listener-arn": "arn:aws:elasticloadbalancing:***"
}
```

이후 IDE의 터미널에서 아래 명령어를 실행하여 CDK Stack을 배포합니다.

```bash
cdk deploy --require-approval never
```

`http://<module-02에서 배포한 MCP Server URL>/app`로 접속하여 배포된 streamlit 애플리케이션을 확인합니다.

# 참고 자료

- [Model Context Protocol 공식 문서](https://modelcontextprotocol.io/)
- [langchain-aws 라이브러리 문서](https://python.langchain.com/docs/integrations/providers/aws/)
- [LangChain MCP Adapters 리포지토리](https://github.com/langchain-ai/langchain-mcp-adapters)
- [LangGraph 프레임워크 공식 문서](https://langchain-ai.github.io/langgraph/) 