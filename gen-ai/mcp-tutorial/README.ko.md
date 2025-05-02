## Getting started with MCP(Model Context Protocol)

이 워크샵은 **Model Context Protocol(MCP)** 서버의 로컬/클라우드 배포에서부터 AWS 기반 애플리케이션 연동까지 종합적인 인프라 구축 역량을 키우기 위해 설계되었습니다.

실습을 통해 AI 모델과 외부 시스템의 연동 메커니즘을 이해하고, 실제 비즈니스 시나리오에 적용 가능한 MCP 기반 솔루션 아키텍처를 구현할 수 있습니다.

## 핵심 학습 목표
- **MCP 프로토콜**을 이용한 AI-인프라 연동 시스템 설계
- **AWS CDK**를 활용한 클라우드 네이티브 MCP 서버 배포
- **MCP Client 애플리케이션**과의 실시간 연동을 통한 LLM 확장 기능 구현

## 모듈별 세부 구성

**Module-01: 로컬 MCP 서버 구축**[:link:](./module-01/)
- **Part 1: 기본 MCP 서버 설정**[:link:](./module-01/part-01/)

  로컬 머신에 Python 기반 MCP 서버를 구축하고 Claude Desktop과 연동해 도구 호출 기능을 구현합니다.

- **Part 2: 공개 MCP 서버 활용**[:link:](./module-01/part-02/)

  Smithery에서 제공하는 오픈소스 MCP 서버를 연동하는 방법을 학습합니다.

**Module-02: AWS 클라우드 배포**[:link:](./module-02/)
- **AWS CDK 인프라 자동화**

  CDK를 활용한 IaC(Infrastructure as Code) 통해 Amazon ECS 클러스터에 MCP 서버를 배포합니다.

- **Claude Desktop 연동**

  배포된 MCP 서버 엔드포인트를 Claude Desktop 애플리케이션에 연결해 중앙 집중식 리소스 관리 시스템을 구성합니다.

**Module-03: Streamlit MCP 호스트 개발**[:link:](./module-03/)
- **대화형 웹 인터페이스 구축**

  Model Context Protocol(MCP)을 활용하여 Streamlit 기반의 MCP Client 애플리케이션을 개발합니다.

- **MCP Server 연동**

  Streamlit 기반의 MCP Client 애플리케이션과 MCP 서버를 연동하는 MCP Client-Server 시스템을 AWS에서 구성합니다.

## 실습 결과물
- 로컬/클라우드 환경에 배포된 MCP 서버 인스턴스
- AWS CDK로 생성된 인프라 스택(CloudFormation 템플릿)
- Streamlit 기반 LLM 애플리케이션과 MCP 서버 연동 데모

이 워크샵을 마치면 참가자들은 AI 모델과 클라우드 인프라를 연동하는 End-to-End 시스템을 설계/운영할 때 **MCP를 활용하는 방법**을 배우게 될 것 입니다.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.