## Amazon Bedrock과 오픈소스 프레임워크를 활용한 Agentic Workflow 구축

> [!NOTE]
> 이 저장소는 "[AIM323 Build Agentic Workflows with Amazon Bedrock and Open Source Frameworks](https://github.com/aws-samples/aim323_build_agents_with_bedrock_oss/tree/main)"의 한글 번역본이며 제공된 번역과 원본 영어의 내용이 상충하는 경우에는 영어 버전이 우선합니다.

이 저장소는 "Amazon Bedrock과 오픈소스 프레임워크를 활용한 Agentic Workflow 구축"이라는 Amazon Reinvent 2024 워크샵의 코드를 포함하고 있습니다. 이 워크샵에서 참가자들은 Amazon Bedrock, LangGraph, CrewAI 및 Ragas를 사용하여 end-to-end agentic 워크로드를 구축하는 실습 경험을 하게 됩니다.

**Lab 1: AI 여행 도우미 유스케이스 소개**
- 여행 도우미 유스케이스를 탐색하며, 실습 전반에 걸쳐 사용될 목적지, 예약 및 선호도에 대한 데이터셋을 다룹니다. 또한 지능적인 응답 생성과 데이터 검색을 가능하게 하는 Amazon Bedrock 모델을 설정하여, 향후 실습에서 사용될 도우미의 기능을 위한 기반을 마련합니다.

**Lab 2: LangGraph를 활용한 여행 플래너 구축**
- LangGraph의 기본 요소인 노드, 엣지, 그래프 및 메모리 개념을 학습합니다. 실습을 통해 이러한 요소들을 사용하여 간단한 여행 추천 시스템을 구축합니다.

**Lab 3: 도구를 활용한 여행 에이전트**
- 사용자가 이상적인 휴가 목적지를 찾는 것을 돕는 여행 챗봇 에이전트를 구축합니다. 이 에이전트는 사용자의 프로필과 유사한 사용자들의 여행 이력을 기반으로 검색할 수 있는 다양한 도구에 접근할 수 있습니다. 또한 미국 전역의 다양한 도시에 대한 상세 정보를 제공하는 검색 도구도 사용합니다.

**Lab 4: 여행 예약 멀티 에이전트**
- 여행 예약을 처리하기 위한 supervisor agentic 패턴을 구현합니다. 여기서는 중앙 supervisor 에이전트가 각각 전용 스크래치패드를 가진 여러 전문 에이전트들을 조정합니다. supervisor 에이전트는 조정자 역할을 하며, Flight Agent와 Hotel Agent에게 검색, 조회, 변경 및 취소와 같은 각자의 기능에 따라 작업을 할당합니다.

**Lab 5: CrewAI를 활용한 꿈의 여행지 찾기**
- CrewAI 프레임워크와 Amazon Bedrock을 사용하여 사용자 선호도를 기반으로 꿈의 여행지를 찾아주는 지능형 에이전트를 구축하는 방법을 탐색합니다. 이 에이전트는 대규모 언어 모델(LLM)과 웹 검색 기능을 활용하여 사용자의 설명과 일치하는 목적지를 연구하고 추천합니다.

**Lab 6: Ragas를 사용한 에이전트 평가**
- [Ragas 라이브러리](https://docs.ragas.io/en/stable/)를 사용하여 멀티 에이전트 여행 예약 시스템의 효과성과 정확성을 평가합니다. 이 실습에서는 관련 정보 검색, 정확한 응답 생성, 사용자 요청의 효과적인 처리 등 다양한 작업에서 에이전트의 성능을 평가하는 과정을 안내합니다.

## 모델 엑세스 허용

이 노트북에서는 Amazon Bedrock의 다양한 Foundation Models(FMs)을 호출합니다. [Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) 가이드에 따라서 호출에 사용하는 모델의 엑세스를 허용해주세요.
워크샵에서는 아래의 모델을 사용하고 있습니다.

- Amazon Nova Lite
- Anthropic Claude 3 Haiku
- Amazon Titan Embedding V1

## 보안

자세한 내용은 [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications)을 참조하세요.

## 라이선스

MIT-0 License
