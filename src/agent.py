from langgraph.graph import StateGraph, END
import httpx
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from models import TripState, ScheduleItem, Location
from kakao_client import KakaoMapClient
import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


class TripPlannerAgent:
    """여행 계획 에이전트"""

    def __init__(self):
        self.llm = ChatOllama(
            model="llama3.2",
            temperature=0.7,
        )
        self.kakao_client = KakaoMapClient()
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(TripState)

        # 노드 추가 - 더 명확한 이름 사용
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

        # 조건부 엣지: 지역 vs 특정 장소
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

        # 재정리 루프
        workflow.add_edge("generate_itinerary", "request_refinement_feedback")
        workflow.add_edge("request_refinement_feedback", "validate_itinerary_quality")

        # 조건부 엣지: 품질 체크 후 재검색 또는 종료
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
        """사용자 입력 분석: 지역명 vs 특정 장소"""
        print(f"[DEBUG] Analyzing input: {state['user_input']}")
        messages = [
            SystemMessage(content="""
당신은 여행 전문가입니다. 사용자의 입력이 '넓은 지역명(동/구/시)'인지 '특정 장소(건물/가게/명소)'인지 판단하세요.
- "홍대", "강남", "부산", "명동", "망원동" -> region
- "롯데월드", "서울타워", "스타벅스 홍대점", "더현대 서울" -> specific_place

응답 형식:
TYPE: [region|specific_place]
VALUE: [정제된 지역명 또는 장소명]
            """),
            HumanMessage(content=f"입력: {state['user_input']}")
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        print(f"[DEBUG] LLM Raw Response:\n{content}")

        # 파싱
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

        print(f"[DEBUG] Parsed Result -> Type: {input_type}, Value: {parsed_value}")

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
                # 검색 실패 시 region으로 fallback
                state["input_type"] = "region"
                state["progress_messages"].append(f"! 장소 검색 실패, 지역 검색으로 전환")

        return state

    async def request_activity_preference(self, state: TripState) -> TripState:
        """사용자에게 활동 선호도 질문 (HIL)"""
        msg = "어떤 스타일의 활동을 원하시나요? (예: 전시, 이색체험, 힐링, 쇼핑 등)"
        state["progress_messages"].append(msg)
        return state

    async def request_food_preference(self, state: TripState) -> TripState:
        """사용자에게 음식 선호도 질문 (HIL)"""
        msg = "어떤 종류의 음식을 선호하시나요? (예: 한식/양식/중식/일식/회 등) '상관없음'이라고 하시면 추천해드릴게요."
        state["progress_messages"].append(msg)
        return state

    async def discover_activity_places(self, state: TripState) -> TripState:
        """활동 장소 검색"""
        location = state["parsed_location"]
        radius = state.get("search_radius", 2000)

        # 사용자 선호도 반영
        preference = state.get("user_activity_preference")

        if preference:
            state["progress_messages"].append(f"✓ '{preference}' 테마로 활동 장소를 검색합니다.")

            # 키워드 확장 (LLM 활용)
            expansion_prompt = f"""
            '{location}' 지역에서 '{preference}'와(과) 관련된 장소를 카카오맵에서 찾으려고 해.
            검색 결과가 잘 나올 수 있는 구체적인 검색 키워드 3~4개를 한국어로 제시해줘.

            형식: 키워드1, 키워드2, 키워드3
            예시: 이태원 미술관, 이태원 갤러리, 이태원 전시회
            """

            try:
                expansion_msg = [HumanMessage(content=expansion_prompt)]
                expansion_res = await self.llm.ainvoke(expansion_msg)
                content = expansion_res.content.strip()

                keywords = [k.strip() for k in content.split(",") if k.strip()]
                print(f"[DEBUG] Expanded Keywords: {keywords}")

                if not keywords:
                    keywords = [f"{location} {preference}"]
            except Exception as e:
                print(f"[WARN] Keyword expansion failed: {e}")
                keywords = [f"{location} {preference}"]

            # 키워드 검색
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

            # 중복 제거
            seen = set()
            unique_places = []
            for a in activity_places:
                if a.name not in seen:
                    seen.add(a.name)
                    unique_places.append(a)

            state["activity_places"] = unique_places[:5]

        else:
            # 기본 로직
            places = await self.kakao_client.find_activity_places(location, radius)
            state["activity_places"] = places

        state["progress_messages"].append(f"✓ 활동 장소 {len(state['activity_places'])}개 발견")
        return state

    async def discover_dining_places(self, state: TripState) -> TripState:
        """식사 장소 검색"""
        current_locations = []

        # 검색 기준점 설정
        if state["input_type"] == "specific_place" and state.get("starting_point"):
            current_locations = [state["starting_point"]]
        elif state["activity_places"]:
            current_locations = state["activity_places"][:3]
        else:
            current_locations = []

        if not current_locations and state["input_type"] == "specific_place":
            return state

        all_dining = []
        for loc in current_locations:
            if state.get("user_food_preference") and state["user_food_preference"] != "상관없음":
                # 음식 취향 반영 검색
                keyword = f"{state['user_food_preference']} 맛집"
                places = await self.kakao_client.search_nearby_by_keyword(
                    keyword=keyword,
                    x=loc.x,
                    y=loc.y,
                    radius=500,
                    size=3
                )
            else:
                # 일반 맛집 검색
                places = await self.kakao_client.find_dining_places(
                    x=loc.x,
                    y=loc.y,
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
        state["progress_messages"].append(f"✓ 식사 장소 {len(unique_dining)}개 발견")

        return state

    async def discover_cafe_places(self, state: TripState) -> TripState:
        """카페/디저트 장소 검색"""
        if not state["dining_places"]:
            state["cafe_places"] = []
            return state

        target_places = state["dining_places"][:2]
        all_cafes = []

        for place in target_places:
            cafes = await self.kakao_client.search_by_category(
                category_code="CE7",
                x=place.x,
                y=place.y,
                radius=300,
                size=2
            )
            all_cafes.extend(cafes)

        # 중복 제거
        seen = set()
        unique_cafes = []
        for c in all_cafes:
            if c.name not in seen:
                seen.add(c.name)
                unique_cafes.append(c)

        state["cafe_places"] = unique_cafes[:3]
        state["progress_messages"].append(f"✓ 카페/디저트 {len(unique_cafes)}개 발견")
        return state

    async def discover_drinking_places(self, state: TripState) -> TripState:
        """술집/바 검색"""
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
            bars = await self.kakao_client.search_nearby_by_keyword(
                keyword="술집",
                x=target.x,
                y=target.y,
                radius=300,
                size=2
            )
            all_bars.extend(bars)

        # 중복 제거
        seen = set()
        unique_bars = []
        for b in all_bars:
            if b.name not in seen:
                seen.add(b.name)
                unique_bars.append(b)

        state["drinking_places"] = unique_bars[:3]
        state["progress_messages"].append(f"✓ 술집/바 {len(unique_bars)}개 발견")
        return state

    async def generate_itinerary(self, state: TripState) -> TripState:
        """여행 일정 생성"""
        places = []

        # 1. 시작점 (특정 장소일 경우)
        if state["input_type"] == "specific_place" and state.get("starting_point"):
            places.append(("출발 지점", state["starting_point"]))

        # 2. 활동 장소 (지역일 경우)
        for place in state["activity_places"][:2]:
            places.append(("활동", place))

        # 3. 식사 장소
        for place in state["dining_places"][:2]:
            places.append(("식사", place))

        # 4. 카페
        for place in state["cafe_places"][:1]:
            places.append(("디저트", place))

        # 5. 술집
        for place in state["drinking_places"][:1]:
            places.append(("음주", place))

        if not places:
            return state

        # 스케줄 객체 생성
        itinerary = []
        for i, (category, loc) in enumerate(places, 1):
            itinerary.append(ScheduleItem(
                order=i,
                location=loc,
                estimated_time="1~2시간",
                notes=f"{category} 추천"
            ))

        state["final_itinerary"] = itinerary

        # 일정 요약 메시지 추가
        summary = f"\n\n📋 생성된 일정:\n"
        for item in itinerary:
            summary += f"{item.order}. {item.location.name} ({item.location.category})\n"
            summary += f"   📍 {item.location.address}\n"

        state["progress_messages"].append(f"✓ 최종 일정 생성 완료")
        state["progress_messages"].append(summary)

        return state

    async def request_refinement_feedback(self, state: TripState) -> TripState:
        """최종 일정 확인 및 수정 요청 (HIL)"""
        msg = "생성된 일정이 마음에 드시나요? '완료'라고 하시면 종료하고, 수정하고 싶다면 '카페 바꿔줘', '음식점 다른 곳' 등으로 말씀해주세요."
        state["progress_messages"].append(msg)
        return state

    async def validate_itinerary_quality(self, state: TripState) -> TripState:
        """일정 품질 검증 및 피드백 반영"""

        # 1. 사용자 피드백 처리
        feedback = state.get("user_feedback")
        if feedback:
            msgs = [
                SystemMessage(content="""
                사용자의 피드백을 분석하여 다음 행동을 결정하세요.
                - 음식점 변경 요청 -> ACTION: refine_food
                - 카페 변경 요청 -> ACTION: refine_cafe
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

        # 2. 품질 체크
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

    async def plan_trip(self, user_input: str, session_id: str) -> dict:
        """여행 계획 실행"""

        config = {"configurable": {"thread_id": session_id}}
        current_state = await self.graph.aget_state(config)

        if not current_state.values:
            # 처음 시작
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
                "next_action": None
            }
            await self.graph.ainvoke(initial_state, config)

        # 실행 후 상태 확인
        final_state = await self.graph.aget_state(config)

        # 중단된 경우
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

        # 완료된 경우
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
        """사용자 피드백 제공 및 재개"""
        config = {"configurable": {"thread_id": session_id}}

        current_state = await self.graph.aget_state(config)
        if not current_state.next:
            return {"status": "error", "message": "진행 중인 세션이 없습니다"}

        next_node = current_state.next[0] if isinstance(current_state.next, tuple) else current_state.next

        # 다음 단계에 따라 적절한 필드 업데이트
        if next_node == "discover_activity_places":
            await self.graph.aupdate_state(config, {"user_activity_preference": feedback_content})
        elif next_node == "discover_dining_places":
            await self.graph.aupdate_state(config, {"user_food_preference": feedback_content})
        elif next_node == "validate_itinerary_quality":
            await self.graph.aupdate_state(config, {"user_feedback": feedback_content})
        else:
            print(f"[WARN] Unknown next step for feedback: {next_node}")

        # 실행 재개
        await self.graph.ainvoke(None, config)

        # 최종 상태 확인
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