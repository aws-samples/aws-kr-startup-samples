from strands import Agent
from strands_tools import rss, current_time

class SecurtyNewsScrapper:
    def __init__(self):
        self.feeds = [
            "https://aws.amazon.com/security/security-bulletins/rss/feed/",
            "https://knvd.krcert.or.kr/rss/securityNotice.do",
            "https://knvd.krcert.or.kr/rss/securityInfo.do"
        ]

        self.security_agent = Agent(
            tools=[rss, current_time],
            system_prompt="""당신은 최신 보안 정보와 공지 사항을 분석하는 보안 전문가입니다. 최근 14일 이내의 항목들의 제목과, 날짜, url을 보기 좋게 정리해서 출력하세요.""",
        )

        # RSS 피드 초기화 제거 - Agent 호출 시에만 RSS 가져오기

    def agent(self, message):
        """RSS 피드에서 최근 보안 뉴스를 분석합니다."""
        return self.security_agent(message)