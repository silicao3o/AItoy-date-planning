from langgraph.graph import StateGraph, END
# from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from models import TripState, ScheduleItem, Location
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
        workflow.add_node("classify_input", self.classify_input)
        workflow.add_node("parse_region", self.parse_region)
        workflow.add_node("find_target_place", self.find_target_place)
        workflow.add_node("search_attractions", self.search_attractions)
        workflow.add_node("search_restaurants", self.search_restaurants)
        workflow.add_node("search_desserts", self.search_desserts)
        workflow.add_node("search_bars", self.search_bars)
        workflow.add_node("create_schedule", self.create_schedule)
        workflow.add_node("check_quality", self.check_quality)

        # 엣지 정의
        workflow.set_entry_point("classify_input")

        # classify_input 다음 분기
        workflow.add_conditional_edges(
            "classify_input",
            self.route_by_input_type,
            {
                "region": "parse_region",
                "specific_place": "find_target_place"
            }
        )

        # 지역명 입력 플로우: 지역 파싱 -> 놀거리 검색 -> 음식점 검색
        workflow.add_edge("parse_region", "search_attractions")
        workflow.add_edge("search_attractions", "search_restaurants")

        # 특정 장소 입력 플로우: 장소 찾기 -> 음식점 검색
        workflow.add_edge("find_target_place", "search_restaurants")

        # 공통 플로우: 음식점 -> 디저트 -> 술집 -> 스케줄 생성 -> 품질 체크
        workflow.add_edge("search_restaurants", "search_desserts")
        workflow.add_edge("search_desserts", "search_bars")
        workflow.add_edge("search_bars", "create_schedule")
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

    async def classify_input(self, state: TripState) -> TripState:
        """입력이 지역명인지 특정 장소인지 분류"""
        messages = [
            SystemMessage(content="""
당신은 사용자 입력을 분류하는 전문가입니다.
사용자가 입력한 내용이 "지역명"인지 "특정 장소명"인지 판단하세요.

지역명의 예: 홍대, 강남, 이태원, 명동, 종로, 마포구, 강남구
특정 장소명의 예: 롯데월드, 경복궁, N서울타워, 스타벅스 홍대점, 교보문고 광화문점

오직 "region" 또는 "specific_place" 중 하나만 답변하세요.
            """),
            HumanMessage(content=f"입력: {state['region']}")
        ]

        response = await self.llm.ainvoke(messages)
        input_type = response.content.strip().lower()

        # 응답 정규화
        if "region" in input_type:
            input_type = "region"
        elif "specific" in input_type or "place" in input_type:
            input_type = "specific_place"
        else:
            # 기본값은 지역명으로 처리
            input_type = "region"

        state["input_type"] = input_type
        state["messages"].append(f"✓ 입력 분류: {input_type}")

        return state

    def route_by_input_type(self, state: TripState) -> str:
        """입력 타입에 따라 라우팅"""
        return state["input_type"]

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

    async def find_target_place(self, state: TripState) -> TripState:
        """특정 장소 검색"""
        place_name = state["region"]

        location = await self.kakao_client.search_place_by_name(place_name)

        if location:
            state["target_location"] = location
            state["messages"].append(f"✓ 장소 찾기 완료: {location.name}")
        else:
            state["messages"].append(f"! 장소를 찾지 못했습니다. 지역 검색으로 전환합니다.")
            # 찾지 못하면 지역명으로 처리
            state["input_type"] = "region"
            state["parsed_region"] = place_name

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
        """음식점 검색"""
        # 기준 좌표 결정
        if state["input_type"] == "specific_place" and state.get("target_location"):
            # 특정 장소가 있으면 그 주변 검색
            target = state["target_location"]
            x, y = target.x, target.y
            state["messages"].append(f"✓ '{target.name}' 주변 음식점 검색 중...")
        elif state["attractions"]:
            # 놀거리가 있으면 첫 번째 놀거리 주변 검색
            target = state["attractions"][0]
            x, y = target.x, target.y
            state["messages"].append(f"✓ '{target.name}' 주변 음식점 검색 중...")
        else:
            state["messages"].append("! 검색 기준점을 찾을 수 없습니다.")
            state["restaurants"] = []
            return state

        restaurants = await self.kakao_client.search_restaurants_nearby(
            x=x,
            y=y,
            radius=500,
            size=5
        )

        state["restaurants"] = restaurants
        state["messages"].append(f"✓ 음식점 {len(restaurants)}개 발견")

        return state

    async def search_desserts(self, state: TripState) -> TripState:
        """디저트 가게 검색"""
        # 기준 좌표 결정
        if state["input_type"] == "specific_place" and state.get("target_location"):
            target = state["target_location"]
            x, y = target.x, target.y
        elif state["restaurants"]:
            target = state["restaurants"][0]
            x, y = target.x, target.y
        elif state["attractions"]:
            target = state["attractions"][0]
            x, y = target.x, target.y
        else:
            state["messages"].append("! 검색 기준점을 찾을 수 없습니다.")
            state["desserts"] = []
            return state

        desserts = await self.kakao_client.search_desserts_nearby(
            x=x,
            y=y,
            radius=500,
            size=5
        )

        state["desserts"] = desserts
        state["messages"].append(f"✓ 디저트 카페 {len(desserts)}개 발견")

        return state

    async def search_bars(self, state: TripState) -> TripState:
        """술집 검색"""
        # 기준 좌표 결정
        if state["input_type"] == "specific_place" and state.get("target_location"):
            target = state["target_location"]
            x, y = target.x, target.y
        elif state["desserts"]:
            target = state["desserts"][0]
            x, y = target.x, target.y
        elif state["restaurants"]:
            target = state["restaurants"][0]
            x, y = target.x, target.y
        elif state["attractions"]:
            target = state["attractions"][0]
            x, y = target.x, target.y
        else:
            state["messages"].append("! 검색 기준점을 찾을 수 없습니다.")
            state["bars"] = []
            return state

        bars = await self.kakao_client.search_bars_nearby(
            x=x,
            y=y,
            radius=500,
            size=5
        )

        state["bars"] = bars
        state["messages"].append(f"✓ 술집 {len(bars)}개 발견")

        return state

    async def create_schedule(self, state: TripState) -> TripState:
        """스케줄 생성"""
        schedule = []
        order = 1

        # 특정 장소가 입력된 경우 먼저 추가
        if state["input_type"] == "specific_place" and state.get("target_location"):
            schedule.append(ScheduleItem(
                order=order,
                location=state["target_location"],
                estimated_time="1시간",
                notes="방문 장소"
            ))
            order += 1

        # 지역명이 입력된 경우 놀거리 추가
        if state["input_type"] == "region" and state["attractions"]:
            for attraction in state["attractions"][:3]:
                schedule.append(ScheduleItem(
                    order=order,
                    location=attraction,
                    estimated_time="1시간 30분",
                    notes="주요 명소 방문"
                ))
                order += 1

        # 음식점 추가
        if state["restaurants"]:
            for restaurant in state["restaurants"][:2]:
                schedule.append(ScheduleItem(
                    order=order,
                    location=restaurant,
                    estimated_time="1시간",
                    notes="식사"
                ))
                order += 1

        # 디저트 카페 추가
        if state["desserts"]:
            for dessert in state["desserts"][:2]:
                schedule.append(ScheduleItem(
                    order=order,
                    location=dessert,
                    estimated_time="40분",
                    notes="디저트 타임"
                ))
                order += 1

        # 술집 추가
        if state["bars"]:
            for bar in state["bars"][:2]:
                schedule.append(ScheduleItem(
                    order=order,
                    location=bar,
                    estimated_time="1시간 30분",
                    notes="저녁 음주"
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
            "input_type": None,
            "parsed_region": None,
            "target_location": None,
            "attractions": [],
            "restaurants": [],
            "desserts": [],
            "bars": [],
            "schedule": [],
            "search_radius": 2000,
            "messages": [],
            "needs_replan": False
        }

        result = await self.graph.ainvoke(initial_state)
        return result