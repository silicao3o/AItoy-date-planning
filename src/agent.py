from langgraph.graph import StateGraph, END
# from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from models import TripState, ScheduleItem
from kakao_client import KakaoMapClient
import os
from dotenv import load_dotenv

load_dotenv()


class TripPlannerAgent:
    """여행 계획 에이전트"""

    def __init__(self):
        self.llm = ChatOllama(
            # model="gpt-4o-mini",
            model="llama3.2",
            temperature=0.7,
            # api_key=os.getenv("OPENAI_API_KEY")
        )
        self.kakao_client = KakaoMapClient()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(TripState)

        # 노드 추가
        workflow.add_node("parse_region", self.parse_region)
        workflow.add_node("search_attractions", self.search_attractions)
        workflow.add_node("search_restaurants", self.search_restaurants)
        workflow.add_node("create_schedule", self.create_schedule)
        workflow.add_node("check_quality", self.check_quality)

        # 엣지 정의
        workflow.set_entry_point("parse_region")
        workflow.add_edge("parse_region", "search_attractions")
        workflow.add_edge("search_attractions", "search_restaurants")
        workflow.add_edge("search_restaurants", "create_schedule")
        workflow.add_edge("create_schedule", "check_quality")

        # 조건부 엣지: 품질 체크 후 재검색 또는 종료
        workflow.add_conditional_edges(
            "check_quality",
            self.should_replan,
            {
                "replan": "search_attractions",
                "end": END
            }
        )

        return workflow.compile()

    async def parse_region(self, state: TripState) -> TripState:
        """지역명 파싱 및 정규화"""
        messages = [
            SystemMessage(content="""
당신은 서울 지역 전문가입니다. 
사용자가 입력한 지역명을 서울의 정확한 구/동 이름으로 변환하세요.
예: "홍대" -> "마포구 홍대", "강남" -> "강남구", "이태원" -> "용산구 이태원"
지역명만 간단히 답변하세요.
            """),
            HumanMessage(content=f"지역: {state['region']}")
        ]

        response = await self.llm.ainvoke(messages)
        parsed_region = response.content.strip()

        state["parsed_region"] = parsed_region
        state["messages"].append(f"✓ 지역 파싱 완료: {parsed_region}")

        return state

    async def search_attractions(self, state: TripState) -> TripState:
        """놀거리 검색"""
        region = state["parsed_region"]
        radius = state.get("search_radius", 2000)

        attractions = await self.kakao_client.search_attractions(region, radius)

        state["attractions"] = attractions
        state["messages"].append(f"✓ 놀거리 {len(attractions)}개 발견")

        return state

    async def search_restaurants(self, state: TripState) -> TripState:
        """각 놀거리 주변 음식점 검색"""
        all_restaurants = []

        for attraction in state["attractions"][:3]:  # 상위 3개 명소만
            restaurants = await self.kakao_client.search_restaurants_nearby(
                x=attraction.x,
                y=attraction.y,
                radius=500,
                size=3
            )
            all_restaurants.extend(restaurants)

        # 중복 제거
        seen = set()
        unique_restaurants = []
        for r in all_restaurants:
            if r.name not in seen:
                seen.add(r.name)
                unique_restaurants.append(r)

        state["restaurants"] = unique_restaurants[:5]
        state["messages"].append(f"✓ 음식점 {len(unique_restaurants)}개 발견")

        return state

    async def create_schedule(self, state: TripState) -> TripState:
        """스케줄 생성"""
        attractions = state["attractions"][:3]
        restaurants = state["restaurants"][:2]

        # LLM을 활용한 스케줄 최적화
        prompt = f"""
다음 장소들로 하루 일정을 짜주세요:

놀거리:
{chr(10).join([f"- {a.name} ({a.address})" for a in attractions])}

음식점:
{chr(10).join([f"- {r.name} ({r.address})" for r in restaurants])}

이동 거리와 시간을 고려하여 효율적인 순서로 배치하고,
각 장소별 예상 소요 시간을 알려주세요.

형식:
1. [장소명] - 예상시간: [시간], 특징: [간단한 설명]
        """

        messages = [
            SystemMessage(content="당신은 서울 여행 전문 플래너입니다."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        # 간단한 스케줄 생성 (실제로는 LLM 응답 파싱 필요)
        schedule = []
        order = 1

        for i, attraction in enumerate(attractions):
            schedule.append(ScheduleItem(
                order=order,
                location=attraction,
                estimated_time="1시간 30분",
                notes=f"주요 명소 방문"
            ))
            order += 1

            # 각 명소 후 음식점 추가
            if i < len(restaurants):
                schedule.append(ScheduleItem(
                    order=order,
                    location=restaurants[i],
                    estimated_time="1시간",
                    notes="식사"
                ))
                order += 1

        state["schedule"] = schedule
        state["messages"].append(f"✓ 스케줄 생성 완료: {len(schedule)}개 항목")

        return state

    async def check_quality(self, state: TripState) -> TripState:
        """스케줄 품질 체크"""
        # 간단한 품질 체크: 최소 3개 이상의 항목이 있는지
        if len(state["schedule"]) < 3 and state["search_radius"] < 5000:
            state["needs_replan"] = True
            state["search_radius"] = state["search_radius"] + 1000
            state["messages"].append(f"! 검색 반경 확대: {state['search_radius']}m")
        else:
            state["needs_replan"] = False
            state["messages"].append("✓ 스케줄 품질 확인 완료")

        return state

    def should_replan(self, state: TripState) -> str:
        """재계획 필요 여부 판단"""
        return "replan" if state["needs_replan"] else "end"

    async def plan_trip(self, region: str) -> TripState:
        """여행 계획 실행"""
        initial_state: TripState = {
            "region": region,
            "parsed_region": None,
            "attractions": [],
            "restaurants": [],
            "schedule": [],
            "search_radius": 2000,
            "messages": [],
            "needs_replan": False
        }

        result = await self.graph.ainvoke(initial_state)
        return result