from langgraph.graph import StateGraph, END
import httpx
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from models_v2 import TripState, ScheduleItem, Location, TravelInfo, TimeSettings, DateTheme
from kakao_client_v2 import KakaoMapClient
from time_calculator import TimeCalculator
import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

load_dotenv()


class TripPlannerAgent:
    """여행 계획 에이전트 (v2 - 시간/평점/테마 기능 포함)"""

    def __init__(self):
        self.llm = ChatOllama(
            model="llama3.2",
            temperature=0.7,
        )
        self.kakao_client = KakaoMapClient()
        self.time_calc = TimeCalculator()
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(TripState)

        # 노드 추가
        workflow.add_node("analyze_user_input", self.analyze_user_input)
        workflow.add_node("request_activity_preference", self.request_activity_preference)
        workflow.add_node("request_food_preference", self.request_food_preference)
        workflow.add_node("discover_activity_places", self.discover_activity_places)
        workflow.add_node("discover_dining_places", self.discover_dining_places)
        workflow.add_node("discover_cafe_places", self.discover_cafe_places)
        workflow.add_node("discover_drinking_places", self.discover_drinking_places)
        workflow.add_node("generate_itinerary", self.generate_itinerary)
        workflow.add_node("request_refinement_feedback", self.request_refinement_feedback)
        workflow.add_node("validate_itinerary_quality", self.validate_itinerary_quality)

        # 엣지 정의
        workflow.set_entry_point("analyze_user_input")

        # 조건부 엣지
        workflow.add_conditional_edges(
            "analyze_user_input",
            self.route_by_input_type,
            {
                "region": "request_activity_preference",
                "specific_place": "request_food_preference"
            }
        )

        workflow.add_edge("request_activity_preference", "discover_activity_places")
        workflow.add_edge("discover_activity_places", "request_food_preference")
        workflow.add_edge("request_food_preference", "discover_dining_places")
        workflow.add_edge("discover_dining_places", "discover_cafe_places")
        workflow.add_edge("discover_cafe_places", "discover_drinking_places")
        workflow.add_edge("discover_drinking_places", "generate_itinerary")

        workflow.add_edge("generate_itinerary", "request_refinement_feedback")
        workflow.add_edge("request_refinement_feedback", "validate_itinerary_quality")

        workflow.add_conditional_edges(
            "validate_itinerary_quality",
            self.determine_next_step,
            {
                "refine_region": "discover_activity_places",
                "refine_place": "discover_dining_places",
                "refine_food": "discover_dining_places",
                "refine_cafe": "discover_cafe_places",
                "complete": END
            }
        )

        return workflow.compile(
            checkpointer=self.memory,
            interrupt_after=["request_activity_preference", "request_food_preference", "request_refinement_feedback"]
        )

    def route_by_input_type(self, state: TripState) -> str:
        """입력 타입에 따른 경로 분기"""
        return state.get("input_type", "region")

    async def analyze_user_input(self, state: TripState) -> TripState:
        """사용자 입력 분석"""
        print(f"[DEBUG] Analyzing input: {state['user_input']}")
        messages = [
            SystemMessage(content="""
당신은 여행 전문가입니다. 사용자의 입력이 '넓은 지역명(동/구/시)'인지 '특정 장소(건물/가게/명소)'인지 판단하세요.
- "홍대", "강남", "부산", "명동" -> region
- "롯데월드", "서울타워", "리움미술관" -> specific_place

응답 형식:
TYPE: [region|specific_place]
VALUE: [정제된 지역명 또는 장소명]
            """),
            HumanMessage(content=f"입력: {state['user_input']}")
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()

        input_type = "region"
        parsed_value = state['user_input']

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue

            if line.upper().startswith("TYPE:"):
                input_type = line.split(":", 1)[1].strip().lower()
                if "specific" in input_type:
                    input_type = "specific_place"
                elif "region" in input_type:
                    input_type = "region"
            elif line.upper().startswith("VALUE:"):
                parsed_value = line.split(":", 1)[1].strip()

        state["input_type"] = input_type
        state["parsed_location"] = parsed_value
        state["progress_messages"].append(f"✓ 입력 분석 완료: {parsed_value} ({input_type})")

        # 특정 장소일 경우 좌표 미리 확보
        if input_type == "specific_place":
            place_location = await self.kakao_client.find_specific_place(parsed_value)
            if place_location:
                state["starting_point"] = place_location
                state["progress_messages"].append(f"✓ 시작 지점 확인: {place_location.name}")
            else:
                state["input_type"] = "region"
                state["progress_messages"].append(f"! 장소 검색 실패, 지역 검색으로 전환")

        return state

    async def request_activity_preference(self, state: TripState) -> TripState:
        """활동 선호도 질문"""
        msg = "어떤 스타일의 활동을 원하시나요? (예: 전시, 체험, 힐링, 쇼핑 등)"
        state["progress_messages"].append(msg)
        return state

    async def request_food_preference(self, state: TripState) -> TripState:
        """음식 선호도 질문"""
        msg = "어떤 종류의 음식을 선호하시나요? (예: 한식/양식/중식/일식 등) '상관없음'이라고 하시면 추천해드릴게요."
        state["progress_messages"].append(msg)
        return state

    async def discover_activity_places(self, state: TripState) -> TripState:
        """활동 장소 검색 (테마 반영)"""
        location = state["parsed_location"]
        radius = state.get("search_radius", 2000)

        # 🎨 테마 설정 활용
        date_theme = state.get("date_theme")
        theme = date_theme.theme if date_theme else None

        preference = state.get("user_activity_preference")

        if preference:
            state["progress_messages"].append(f"✓ '{preference}' 테마로 활동 장소를 검색합니다.")

            # 키워드 확장
            expansion_prompt = f"""
            '{location}' 지역에서 '{preference}'와(과) 관련된 장소를 찾으려고 합니다.
            검색 키워드 3~4개를 제시해주세요.
            형식: 키워드1, 키워드2, 키워드3
            """

            try:
                expansion_msg = [HumanMessage(content=expansion_prompt)]
                expansion_res = await self.llm.ainvoke(expansion_msg)
                content = expansion_res.content.strip()
                keywords = [k.strip() for k in content.split(",") if k.strip()]
                if not keywords:
                    keywords = [f"{location} {preference}"]
            except Exception as e:
                keywords = [f"{location} {preference}"]

            activity_places = []
            async with httpx.AsyncClient() as client:
                for kw in keywords:
                    params = {"query": kw, "size": 5, "sort": "accuracy"}
                    headers = {"Authorization": f"KakaoAK {self.kakao_client.api_key}"}
                    try:
                        res = await client.get(
                            "https://dapi.kakao.com/v2/local/search/keyword.json",
                            headers=headers,
                            params=params
                        )
                        res.raise_for_status()
                        data = res.json()
                        for doc in data.get("documents", []):
                            activity_places.append(Location(
                                name=doc["place_name"],
                                category=doc["category_name"],
                                address=doc["address_name"],
                                x=float(doc["x"]),
                                y=float(doc["y"]),
                                phone=doc.get("phone"),
                                place_url=doc.get("place_url"),
                                distance=0
                            ))
                    except Exception as e:
                        print(f"Search failed for {kw}: {e}")

            seen = set()
            unique_places = []
            for a in activity_places:
                if a.name not in seen:
                    seen.add(a.name)
                    unique_places.append(a)

            state["activity_places"] = unique_places[:5]

        else:
            # ⭐ 테마 기반 검색 (평점 필터링 포함)
            places = await self.kakao_client.find_activity_places(location, theme, radius)
            state["activity_places"] = places

        state["progress_messages"].append(f"✓ 활동 장소 {len(state['activity_places'])}개 발견 (평점 기반 필터링 적용)")
        return state

    async def discover_dining_places(self, state: TripState) -> TripState:
        """식사 장소 검색 (분위기 반영)"""
        current_locations = []

        if state["input_type"] == "specific_place" and state.get("starting_point"):
            current_locations = [state["starting_point"]]
        elif state["activity_places"]:
            current_locations = state["activity_places"][:3]
        else:
            current_locations = []

        if not current_locations:
            return state

        # 🎨 분위기 설정 활용
        date_theme = state.get("date_theme")
        atmosphere = date_theme.atmosphere if date_theme else "casual"

        all_dining = []
        for loc in current_locations:
            if state.get("user_food_preference") and state["user_food_preference"] != "상관없음":
                keyword = f"{state['user_food_preference']} 맛집"
                places = await self.kakao_client.search_nearby_by_keyword(
                    keyword=keyword,
                    x=loc.x,
                    y=loc.y,
                    radius=500,
                    size=3
                )
            else:
                # ⭐ 분위기 반영 + 평점 필터링
                places = await self.kakao_client.find_dining_places(
                    x=loc.x,
                    y=loc.y,
                    atmosphere=atmosphere,
                    radius=500,
                    size=3
                )
            all_dining.extend(places)

        # 중복 제거
        seen = set()
        unique_dining = []
        for r in all_dining:
            if r.name not in seen:
                seen.add(r.name)
                unique_dining.append(r)

        state["dining_places"] = unique_dining[:5]
        state["progress_messages"].append(f"✓ 식사 장소 {len(unique_dining)}개 발견 (평점/분위기 기반)")

        return state

    async def discover_cafe_places(self, state: TripState) -> TripState:
        """카페 검색 (분위기 반영)"""
        if not state["dining_places"]:
            state["cafe_places"] = []
            return state

        # 🎨 분위기 설정 활용
        date_theme = state.get("date_theme")
        atmosphere = date_theme.atmosphere if date_theme else "casual"

        target_places = state["dining_places"][:2]
        all_cafes = []

        for place in target_places:
            # ⭐ 분위기 반영 + 평점 필터링
            cafes = await self.kakao_client.find_cafe_places(
                x=place.x,
                y=place.y,
                atmosphere=atmosphere,
                radius=300,
                size=2
            )
            all_cafes.extend(cafes)

        seen = set()
        unique_cafes = []
        for c in all_cafes:
            if c.name not in seen:
                seen.add(c.name)
                unique_cafes.append(c)

        state["cafe_places"] = unique_cafes[:3]
        state["progress_messages"].append(f"✓ 카페 {len(unique_cafes)}개 발견 (평점/분위기 기반)")
        return state

    async def discover_drinking_places(self, state: TripState) -> TripState:
        """술집 검색"""
        targets = []
        if state["cafe_places"]:
            targets = state["cafe_places"][:2]
        elif state["dining_places"]:
            targets = state["dining_places"][:2]

        if not targets:
            state["drinking_places"] = []
            return state

        all_bars = []
        for target in targets:
            # ⭐ 평점 필터링 적용
            bars = await self.kakao_client.search_nearby_by_keyword(
                keyword="술집",
                x=target.x,
                y=target.y,
                radius=300,
                size=2
            )
            all_bars.extend(bars)

        seen = set()
        unique_bars = []
        for b in all_bars:
            if b.name not in seen:
                seen.add(b.name)
                unique_bars.append(b)

        state["drinking_places"] = unique_bars[:3]
        state["progress_messages"].append(f"✓ 술집/바 {len(unique_bars)}개 발견 (평점 기반)")
        return state

    async def generate_itinerary(self, state: TripState) -> TripState:
        """⏰ 시간표가 포함된 여행 일정 생성"""
        places = []

        # 장소 수집
        if state["input_type"] == "specific_place" and state.get("starting_point"):
            places.append(("activity", state["starting_point"]))

        for place in state["activity_places"][:2]:
            places.append(("activity", place))

        for place in state["dining_places"][:2]:
            places.append(("dining", place))

        for place in state["cafe_places"][:1]:
            places.append(("cafe", place))

        for place in state["drinking_places"][:1]:
            places.append(("drinking", place))

        if not places:
            return state

        # ⏰ 시간 설정 확인
        time_settings = state.get("time_settings")

        if time_settings and time_settings.enabled:
            # 시간표 생성
            start_time = self.time_calc.parse_time(time_settings.start_time)
            current_time = start_time

            itinerary = []

            for i, (place_type, location) in enumerate(places):
                # 소요 시간 결정
                duration = self.time_calc.DEFAULT_DURATIONS.get(place_type, 60)
                end_time = current_time + timedelta(minutes=duration)

                # 다음 장소로의 이동 정보
                travel_info = None
                if i < len(places) - 1:
                    next_location = places[i + 1][1]
                    method, travel_minutes, distance = self.time_calc.calculate_travel_time(
                        location, next_location
                    )
                    description = self.time_calc.get_travel_description(method, travel_minutes, distance)

                    travel_info = TravelInfo(
                        method=method,
                        duration_minutes=travel_minutes,
                        distance_meters=distance,
                        description=description
                    )

                # 스케줄 아이템 생성
                schedule_item = ScheduleItem(
                    order=i + 1,
                    start_time=self.time_calc.format_time(current_time),
                    end_time=self.time_calc.format_time(end_time),
                    duration_minutes=duration,
                    location=location,
                    estimated_time=self.time_calc.format_duration(duration),
                    notes=f"{place_type} 추천",
                    travel_to_next=travel_info
                )

                itinerary.append(schedule_item)

                # 다음 시작 시간 = 현재 종료 + 이동시간
                if travel_info:
                    current_time = end_time + timedelta(minutes=travel_info.duration_minutes)
                else:
                    current_time = end_time

            state["final_itinerary"] = itinerary

            # 요약 메시지
            first_time = itinerary[0].start_time
            last_time = itinerary[-1].end_time
            summary = f"\n\n📋 생성된 일정 ({first_time} ~ {last_time}):\n"

            for item in itinerary:
                summary += f"\n{item.order}. [{item.start_time}-{item.end_time}] {item.location.name}\n"
                summary += f"   📍 {item.location.address}\n"
                if item.travel_to_next:
                    summary += f"   🚶 다음 장소까지: {item.travel_to_next.description}\n"

            state["progress_messages"].append(summary)
        else:
            # 시간 설정이 없을 때는 기존 방식
            itinerary = []
            for i, (category, loc) in enumerate(places, 1):
                itinerary.append(ScheduleItem(
                    order=i,
                    location=loc,
                    estimated_time="1~2시간",
                    notes=f"{category} 추천"
                ))

            state["final_itinerary"] = itinerary

            summary = f"\n\n📋 생성된 일정:\n"
            for item in itinerary:
                summary += f"{item.order}. {item.location.name} ({item.location.category})\n"
                summary += f"   📍 {item.location.address}\n"

            state["progress_messages"].append(summary)

        state["progress_messages"].append(f"✓ 최종 일정 생성 완료")
        return state

    async def request_refinement_feedback(self, state: TripState) -> TripState:
        """일정 확인 및 수정 요청"""
        msg = "생성된 일정이 마음에 드시나요? '완료'라고 하시면 종료하고, 수정하고 싶다면 '카페 바꿔줘', '음식점 다른 곳' 등으로 말씀해주세요."
        state["progress_messages"].append(msg)
        return state

    async def validate_itinerary_quality(self, state: TripState) -> TripState:
        """일정 품질 검증"""
        feedback = state.get("user_feedback")
        if feedback:
            msgs = [
                SystemMessage(content="""
                사용자 피드백을 분석하세요.
                - 음식점 변경 -> ACTION: refine_food
                - 카페 변경 -> ACTION: refine_cafe
                - 전체 다시 -> ACTION: refine_region
                - 완료/좋음 -> ACTION: complete

                응답 형식: ACTION: [action_code]
                """),
                HumanMessage(content=feedback)
            ]
            res = await self.llm.ainvoke(msgs)
            content = res.content.strip()

            action = "complete"
            if "refine_food" in content:
                action = "refine_food"
            elif "refine_cafe" in content:
                action = "refine_cafe"
            elif "refine_region" in content:
                action = "refine_region"

            state["next_action"] = action
            state["progress_messages"].append(f"✓ 피드백 반영: {action}")
            state["user_feedback"] = None

            if action != "complete":
                state["needs_refinement"] = True
                return state

        if len(state["final_itinerary"]) < 2 and state["search_radius"] < 5000:
            state["needs_refinement"] = True
            state["search_radius"] += 1000
            state["progress_messages"].append(f"! 검색 결과 부족, 반경 확대: {state['search_radius']}m")
            state["next_action"] = "refine_region"
        else:
            state["needs_refinement"] = False
            state["next_action"] = "complete"
            state["progress_messages"].append("✓ 일정 생성 완료")

        return state

    def determine_next_step(self, state: TripState) -> str:
        """다음 단계 결정"""
        if state["needs_refinement"]:
            action = state.get("next_action", "refine_region")
            if action == "refine_place" or (state.get("input_type") == "specific_place" and action == "refine_region"):
                return "refine_place"
            return action
        return "complete"

    async def plan_trip(
            self,
            user_input: str,
            session_id: str,
            time_settings: Optional[TimeSettings] = None,
            date_theme: Optional[DateTheme] = None
    ) -> dict:
        """여행 계획 실행"""

        config = {"configurable": {"thread_id": session_id}}
        current_state = await self.graph.aget_state(config)

        if not current_state.values:
            initial_state: TripState = {
                "user_input": user_input,
                "input_type": None,
                "parsed_location": None,
                "starting_point": None,
                "activity_places": [],
                "dining_places": [],
                "cafe_places": [],
                "drinking_places": [],
                "final_itinerary": [],
                "search_radius": 2000,
                "progress_messages": [],
                "needs_refinement": False,
                "user_activity_preference": None,
                "user_food_preference": None,
                "user_feedback": None,
                "next_action": None,
                "time_settings": time_settings,
                "date_theme": date_theme
            }
            await self.graph.ainvoke(initial_state, config)

        final_state = await self.graph.aget_state(config)

        if final_state.next:
            return {
                "status": "awaiting_user_input",
                "pending_step": final_state.next,
                "itinerary": {
                    "locations": {
                        "activities": [loc.dict() for loc in final_state.values.get("activity_places", [])],
                        "dining": [loc.dict() for loc in final_state.values.get("dining_places", [])],
                        "cafes": [loc.dict() for loc in final_state.values.get("cafe_places", [])],
                        "bars": [loc.dict() for loc in final_state.values.get("drinking_places", [])]
                    },
                    "schedule": [item.dict() for item in final_state.values.get("final_itinerary", [])]
                },
                "progress": final_state.values.get("progress_messages", []),
                "session_id": session_id
            }

        return {
            "status": "completed",
            "itinerary": {
                "input": {
                    "original": final_state.values.get("user_input"),
                    "type": final_state.values.get("input_type"),
                    "parsed": final_state.values.get("parsed_location")
                },
                "locations": {
                    "starting_point": final_state.values.get("starting_point").dict() if final_state.values.get(
                        "starting_point") else None,
                    "activities": [loc.dict() for loc in final_state.values.get("activity_places", [])],
                    "dining": [loc.dict() for loc in final_state.values.get("dining_places", [])],
                    "cafes": [loc.dict() for loc in final_state.values.get("cafe_places", [])],
                    "bars": [loc.dict() for loc in final_state.values.get("drinking_places", [])]
                },
                "schedule": [item.dict() for item in final_state.values.get("final_itinerary", [])]
            },
            "progress": final_state.values.get("progress_messages", []),
            "session_id": session_id
        }

    async def provide_user_feedback(self, session_id: str, feedback_content: str) -> dict:
        """사용자 피드백 제공"""
        config = {"configurable": {"thread_id": session_id}}

        current_state = await self.graph.aget_state(config)
        if not current_state.next:
            return {"status": "error", "message": "진행 중인 세션이 없습니다"}

        next_node = current_state.next[0] if isinstance(current_state.next, tuple) else current_state.next

        if next_node == "discover_activity_places":
            await self.graph.aupdate_state(config, {"user_activity_preference": feedback_content})
        elif next_node == "discover_dining_places":
            await self.graph.aupdate_state(config, {"user_food_preference": feedback_content})
        elif next_node == "validate_itinerary_quality":
            await self.graph.aupdate_state(config, {"user_feedback": feedback_content})

        await self.graph.ainvoke(None, config)
        final_state = await self.graph.aget_state(config)

        if final_state.next:
            return {
                "status": "awaiting_user_input",
                "pending_step": final_state.next,
                "itinerary": {
                    "locations": {
                        "activities": [loc.dict() for loc in final_state.values.get("activity_places", [])],
                        "dining": [loc.dict() for loc in final_state.values.get("dining_places", [])],
                        "cafes": [loc.dict() for loc in final_state.values.get("cafe_places", [])],
                        "bars": [loc.dict() for loc in final_state.values.get("drinking_places", [])]
                    },
                    "schedule": [item.dict() for item in final_state.values.get("final_itinerary", [])]
                },
                "progress": final_state.values.get("progress_messages", []),
                "session_id": session_id
            }

        return {
            "status": "completed",
            "itinerary": {
                "input": {
                    "original": final_state.values.get("user_input"),
                    "type": final_state.values.get("input_type"),
                    "parsed": final_state.values.get("parsed_location")
                },
                "locations": {
                    "starting_point": final_state.values.get("starting_point").dict() if final_state.values.get(
                        "starting_point") else None,
                    "activities": [loc.dict() for loc in final_state.values.get("activity_places", [])],
                    "dining": [loc.dict() for loc in final_state.values.get("dining_places", [])],
                    "cafes": [loc.dict() for loc in final_state.values.get("cafe_places", [])],
                    "bars": [loc.dict() for loc in final_state.values.get("drinking_places", [])]
                },
                "schedule": [item.dict() for item in final_state.values.get("final_itinerary", [])]
            },
            "progress": final_state.values.get("progress_messages", []),
            "session_id": session_id
        }