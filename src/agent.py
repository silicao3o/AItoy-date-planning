from langgraph.graph import StateGraph, END
import httpx
# from langchain_openai import ChatOpenAI
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
            # model="gpt-4o-mini",
            model="llama3.2",
            temperature=0.7,
            # api_key=os.getenv("OPENAI_API_KEY")
        )
        self.kakao_client = KakaoMapClient()
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(TripState)

        # 노드 추가
        workflow.add_node("analyze_input", self.analyze_input)
        workflow.add_node("ask_preference", self.ask_preference)  # HIL Node
        workflow.add_node("ask_food_preference", self.ask_food_preference) # HIL Node for Food
        workflow.add_node("search_attractions", self.search_attractions)
        workflow.add_node("search_restaurants", self.search_restaurants)
        workflow.add_node("search_cafes", self.search_cafes)
        workflow.add_node("search_bars", self.search_bars)
        workflow.add_node("create_schedule", self.create_schedule)
        workflow.add_node("check_quality", self.check_quality)

        # 엣지 정의
        workflow.set_entry_point("analyze_input")
        
        # 조건부 엣지: 지역 vs 장소
        workflow.add_conditional_edges(
            "analyze_input",
            self.route_by_location_type,
            {
                "region": "ask_preference", # Region이면 물어보러 감
                "spot": "ask_food_preference"
            }
        )

        workflow.add_edge("ask_preference", "search_attractions")
        workflow.add_edge("search_attractions", "ask_food_preference")
        workflow.add_edge("ask_food_preference", "search_restaurants")
        workflow.add_edge("search_restaurants", "search_cafes")
        workflow.add_edge("search_cafes", "search_bars")
        workflow.add_edge("search_bars", "create_schedule")
        workflow.add_node("ask_refinement", self.ask_refinement) # Multi-turn HIL
        
        # 엣지 정의
        workflow.set_entry_point("analyze_input")
        
        # ... (Existing conditional edges) ...
        
        # refinement Loop
        workflow.add_edge("create_schedule", "ask_refinement")
        workflow.add_edge("ask_refinement", "check_quality") # check_quality에서 분기 처리

        # 조건부 엣지: 품질 체크 또는 피드백 후 재검색 또는 종료
        workflow.add_conditional_edges(
            "check_quality",
            self.should_replan,
            {
                "replan_region": "search_attractions",
                "replan_spot": "search_restaurants",
                "replan_food": "search_restaurants",
                "replan_cafe": "search_cafes",
                "end": END
            }
        )

        # ask_preference 노드 실행 후 중단 (사용자 입력 대기)
        return workflow.compile(
            checkpointer=self.memory,
            interrupt_after=["ask_preference", "ask_food_preference", "ask_refinement"]
        )

    def route_by_location_type(self, state: TripState) -> str:
        """지역 타입에 따른 경로 분기"""
        return state.get("location_type", "region")

    async def analyze_input(self, state: TripState) -> TripState:
        """사용자 입력 분석: 지역명 vs 특정 장소"""
        print(f"[DEBUG] Analyzing input: {state['region']}")
        messages = [
            SystemMessage(content="""
당신은 여행 전문가입니다. 사용자의 입력이 '넓은 지역명(동/구/시)'인지 '특정 장소(건물/가게/명소)'인지 판단하세요.
- "홍대", "강남", "부산", "명동", "망원동" -> region
- "롯데월드", "서울타워", "스타벅스 홍대점", "더현대 서울" -> spot

응답 형식:
TYPE: [region|spot]
VALUE: [정제된 지역명 또는 장소명]
            """),
            HumanMessage(content=f"입력: {state['region']}")
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        print(f"[DEBUG] LLM Raw Response:\n{content}")
        
        # 파싱
        location_type = "region"
        parsed_value = state['region']
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.upper().startswith("TYPE:"):
                location_type = line.split(":", 1)[1].strip().lower()
            elif line.upper().startswith("VALUE:"):
                parsed_value = line.split(":", 1)[1].strip()

        print(f"[DEBUG] Parsed Result -> Type: {location_type}, Value: {parsed_value}")

        state["location_type"] = location_type
        state["parsed_region"] = parsed_value
        state["messages"].append(f"✓ 입력 분석: {parsed_value} ({location_type})")

        # Spot일 경우 좌표 미리 확보
        if location_type == "spot":
            spot_location = await self.kakao_client.search_place(parsed_value)
            if spot_location:
                state["start_location"] = spot_location
                state["messages"].append(f"✓ 출발 장소 확인: {spot_location.name}")
            else:
                # 검색 실패 시 region으로 fallback
                 state["location_type"] = "region"
                 state["messages"].append(f"! 장소 검색 실패, 지역 검색으로 전환")

        return state

    async def ask_preference(self, state: TripState) -> TripState:
        """사용자에게 놀거리 선호도 질문 (HIL용)"""
        msg = "어떤 스타일의 놀거리를 원하시나요? (예: 전시, 이색체험, 힐링, 쇼핑 등)"
        state["messages"].append(msg)
        return state

    async def ask_food_preference(self, state: TripState) -> TripState:
        """사용자에게 음식 선호도 질문 (HIL용)"""
        msg = "어떤 종류의 음식을 선호하시나요? (예: 한식/양식/중식/일식/회 등) '상관없음'이라고 하시면 추천해드릴게요."
        state["messages"].append(msg)
        return state

    async def search_attractions(self, state: TripState) -> TripState:
        """놀거리 검색"""
        region = state["parsed_region"]
        radius = state.get("search_radius", 2000)
        
        # HIL로 받은 선호 카테고리 적용
        preference = state.get("preferred_category")
        
        if preference:
            state["messages"].append(f"✓ '{preference}' 테마로 검색합니다.")
            # KakaoMapClient 수정 없이 여기서 검색어 조합으로 처리
            # 하지만 KakaoMapClient.search_attractions 메소드가 고정 키워드를 쓰고 있어서 
            # 커스텀 검색이 필요함. search_keyword_nearby 등을 활용하는게 나을 수 있음.
            # 여기서는 kakao_client를 직접 호출하지 않고 search_keyword_nearby를 씀.
            
            # 중심 좌표를 먼저 구해야 하는데, region 검색은 좌표가 없음. 
            # KakaoMapClient.search_place 로 지역 센터 좌표를 구하거나
            # 그냥 keyword search ("홍대 방탈출") 형태로 호출해야 함.
            
            # 1. 키워드 확장 (LLM 활용)
            # 사용자가 "전시"라고만 해도 "미술관", "갤러리" 등을 검색하도록 확장
            expansion_prompt = f"""
            '{region}' 지역에서 '{preference}'와(과) 관련된 장소를 카카오맵에서 찾으려고 해.
            검색 결과가 잘 나올 수 있는 구체적인 검색 키워드 3~4개를 한국어로 제시해줘.
            
            형식: 키워드1, 키워드2, 키워드3
            예시: 이태원 미술관, 이태원 갤러리, 이태원 전시회
            """
            
            try:
                # LLM에게 키워드 추천 받기
                expansion_msg = [HumanMessage(content=expansion_prompt)]
                expansion_res = await self.llm.ainvoke(expansion_msg)
                content = expansion_res.content.strip()
                
                # 쉼표로 구분하여 파싱
                keywords = [k.strip() for k in content.split(",") if k.strip()]
                print(f"[DEBUG] Expanded Keywords: {keywords}")
                
                # 혹시 파싱 실패하거나 빈 값이면 기본값 사용
                if not keywords:
                    keywords = [f"{region} {preference}"]
            except Exception as e:
                print(f"[WARN] Keyword expansion failed: {e}")
                keywords = [f"{region} {preference}"]

            # 직접 구현
            attractions = []
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
                            attractions.append(Location(
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
            unique_attractions = []
            for a in attractions:
                if a.name not in seen:
                    seen.add(a.name)
                    unique_attractions.append(a)
            
            state["attractions"] = unique_attractions[:5]
            
        else:
            # 기본 로직
            attractions = await self.kakao_client.search_attractions(region, radius)
            state["attractions"] = attractions

        state["messages"].append(f"✓ 놀거리 {len(state['attractions'])}개 발견")
        return state

    async def search_restaurants(self, state: TripState) -> TripState:
        """음식점 검색"""
        current_locations = []
        
        # 검색 기준점 설정
        if state["location_type"] == "spot" and state.get("start_location"):
            current_locations = [state["start_location"]]
        elif state["attractions"]:
            current_locations = state["attractions"][:3]
        else:
            # Fallback if no attractions found in region mode
            current_locations = []

        if not current_locations and state["location_type"] == "spot":
             # Spot failure fallback
             return state

        all_restaurants = []
        for loc in current_locations:
            if state.get("preferred_food") and state["preferred_food"] != "상관없음":
                # 음식 취향 반영 검색
                keyword = f"{state['preferred_food']} 맛집"
                restaurants = await self.kakao_client.search_keyword_nearby(
                    keyword=keyword,
                    x=loc.x,
                    y=loc.y,
                    radius=500,
                    size=3
                )
            else:
                 # 일반 맛집 검색
                restaurants = await self.kakao_client.search_restaurants_nearby(
                    x=loc.x,
                    y=loc.y,
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

    async def search_cafes(self, state: TripState) -> TripState:
        """디저트/카페 검색"""
        # 음식점 근처에서 카페 검색
        if not state["restaurants"]:
            state["desserts"] = []
            return state

        target_restaurants = state["restaurants"][:2] # 상위 2개 음식점 근처
        all_cafes = []

        for restaurant in target_restaurants:
            cafes = await self.kakao_client.search_category(
                category_code="CE7", # 카페
                x=restaurant.x, 
                y=restaurant.y,
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

        state["desserts"] = unique_cafes[:3]
        
        state["messages"].append(f"✓ 디저트/카페 {len(unique_cafes)}개 발견")
        return state

    async def search_bars(self, state: TripState) -> TripState:
        """술집 검색"""
        # 카페(또는 음식점) 근처에서 술집 검색
        targets = []
        if state["desserts"]:
            targets = state["desserts"][:2]
        elif state["restaurants"]:
            targets = state["restaurants"][:2]
        
        if not targets:
            state["bars"] = []
            return state

        all_bars = []
        for target in targets:
            # "술집", "요리주점", "와인", "칵테일" 등의 키워드 사용
            bars = await self.kakao_client.search_keyword_nearby(
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

        state["bars"] = unique_bars[:3]
        
        state["messages"].append(f"✓ 술집 {len(unique_bars)}개 발견")
        return state

    async def create_schedule(self, state: TripState) -> TripState:
        """스케줄 생성"""
        # 수집된 모든 장소들을 조합
        places = []
        
        # 1. 시작점 (Spot일 경우)
        if state["location_type"] == "spot" and state.get("start_location"):
            places.append(("출발", state["start_location"]))
        
        # 2. 놀거리 (Region일 경우)
        for attr in state["attractions"][:2]:
            places.append(("명소", attr))
            
        # 3. 음식점
        for res in state["restaurants"][:2]:
            places.append(("식사", res))
            
        # 4. 카페
        for cafe in state["desserts"][:1]:
             places.append(("디저트", cafe))

        # 5. 술집
        for bar in state["bars"][:1]:
             places.append(("술집", bar))

        if not places:
             return state

        prompt = f"""
다음 장소들로 데이트/놀거리 코스를 짜주세요. 순서는 자연스럽게 연결해주세요.
(일반적인 순서: 놀거리 -> 밥 -> 카페 -> 술)

장소 목록:
{chr(10).join([f"- [{p[0]}] {p[1].name} ({p[1].address})" for p in places])}

각 장소별로 이동 동선을 고려해서 순서를 정하고, 간단한 한 줄 팁을 적어주세요.
        """

        messages = [
            SystemMessage(content="당신은 서울 핫플레이스 코스 플래너입니다."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)

        # 스케줄 객체 생성 (단순 매핑)
        schedule = []
        for i, (cat, loc) in enumerate(places, 1):
            schedule.append(ScheduleItem(
                order=i,
                location=loc,
                estimated_time="1~2시간",
                notes=f"{cat} - 코스 추천"
            ))

        state["schedule"] = schedule
        state["messages"].append(f"✓ 최종 코스 생성 완료")

        return state

    async def ask_refinement(self, state: TripState) -> TripState:
        """최종 스케줄 확인 및 수정 요청 (HIL)"""
        msg = "생성된 코스가 마음에 드시나요? '완료'라고 하시면 종료하고, 수정하고 싶다면 '카페 바꿔줘', '음식점 다른 곳' 등으로 말씀해주세요."
        state["messages"].append(msg)
        return state

    async def check_quality(self, state: TripState) -> TripState:
        """스케줄 품질 체크 및 피드백 반영"""
        
        # 1. 사용자 피드백 처리 (ask_refinement 이후)
        feedback = state.get("user_feedback") # provide_feedback에서 넣어줄 예정
        if feedback:
            # LLM으로 피드백 분석
            msgs = [
                SystemMessage(content="""
                사용자의 피드백을 분석하여 다음 행동을 결정하세요.
                - 음식점 변경 요청 -> ACTION: replan_food
                - 카페 변경 요청 -> ACTION: replan_cafe
                - 전체 다시 -> ACTION: replan_region
                - 완료/좋음 -> ACTION: end
                
                응답 형식: ACTION: [action_code]
                """),
                HumanMessage(content=feedback)
            ]
            res = await self.llm.ainvoke(msgs)
            content = res.content.strip()
            
            action = "end"
            if "replan_food" in content: action = "replan_food"
            elif "replan_cafe" in content: action = "replan_cafe"
            elif "replan_region" in content: action = "replan_region"
            
            state["next_action"] = action
            state["messages"].append(f"✓ 피드백 반영: {action}")
            state["user_feedback"] = None # Reset
            
            if action != "end":
                 state["needs_replan"] = True
                 return state

        # 2. 품질 체크 (기존 로직)
        if len(state["schedule"]) < 2 and state["search_radius"] < 5000:
            state["needs_replan"] = True
            state["search_radius"] += 1000
            state["messages"].append(f"! 검색 결과 부족, 반경 확대: {state['search_radius']}m")
            state["next_action"] = "replan_region" # Default fallback
        else:
            state["needs_replan"] = False
            state["next_action"] = "end"
            state["messages"].append("✓ 플래닝 완료")

        return state

    def should_replan(self, state: TripState) -> str:
        """재계획 필요 여부 판단"""
        if state["needs_replan"]:
            action = state.get("next_action", "replan_region")
            # 스팟/지역 기본 구분
            if action == "replan_spot" or (state.get("location_type") == "spot" and action == "replan_region"):
                return "replan_spot"
                
            return action # replan_food, replan_cafe, replan_region, etc.
        return "end"

    async def plan_trip(self, region: str, thread_id: str) -> dict:
        """여행 계획 실행 (Stream & Checkpoint)"""
        
        # 설정 객체
        config = {"configurable": {"thread_id": thread_id}}
        
        # 현재 상태 확인 (혹시 멈춰있는지)
        current_state = await self.graph.aget_state(config)
        
        if not current_state.values:
            # 처음 시작
            initial_state: TripState = {
                "region": region,
                "parsed_region": None,
                "attractions": [],
                "restaurants": [],
                "desserts": [],
                "bars": [],
                "schedule": [],
                "search_radius": 2000,
                "messages": [],
                "needs_replan": False,
                "location_type": None,
                "start_location": None,
                "preferred_category": None,
                "preferred_food": None
            }
            # 첫 실행
            await self.graph.ainvoke(initial_state, config)
        else:
            # 이미 상태가 있음 -> 아무것도 안했지만 continue 요청이 아닌 plan 요청이 왔다면? 
            # 일단 여기서는 새로 시작하는 것이 맞음 (새 thread_id 권장하지만, 같은 id면 덮어쓰거나 무시)
            # 여기서는 편의상 처음부터 다시 시작 (update_state로 초기화하거나 그냥 새 id 쓰라고 가이드)
            pass

        # 실행 후 상태 확인
        final_state = await self.graph.aget_state(config)
        
        # next가 있으면 중단된 것
        if final_state.next:
            return {
                "status": "waiting_permission",
                "next_step": final_state.next,
                "messages": final_state.values.get("messages", []),
                "thread_id": thread_id
            }
        
        return {
            "status": "completed",
            "result": final_state.values,
            "thread_id": thread_id
        }

    async def provide_feedback(self, thread_id: str, category: str) -> dict:
        """사용자 피드백(카테고리) 제공 및 재개"""
        config = {"configurable": {"thread_id": thread_id}}
        
        # 상태 업데이트
        current_state = await self.graph.aget_state(config)
        if not current_state.next:
             return {"status": "error", "message": "No active conversation to resume"}

        # Determine which preference to update based on the next step
        next_node = current_state.next[0] if isinstance(current_state.next, tuple) else current_state.next
        
        if next_node == "search_attractions":
            await self.graph.aupdate_state(config, {"preferred_category": category})
        elif next_node == "search_restaurants":
            await self.graph.aupdate_state(config, {"preferred_food": category})
        elif next_node == "check_quality":
             # ask_refinement 다음 단계가 check_quality이므로 여기서 피드백 처리
             await self.graph.aupdate_state(config, {"user_feedback": category})
        else:
             print(f"[WARN] Unknown next step for feedback: {next_node}")
        
        # 실행 재개 (None을 입력으로 주어 멈춘 곳 부터 시작)
        await self.graph.ainvoke(None, config)
        
        # 최종 상태 확인
        final_state = await self.graph.aget_state(config)
        
        if final_state.next:
             return {
                "status": "waiting_permission",
                "next_step": final_state.next,
                 "messages": final_state.values.get("messages", []),
                 "thread_id": thread_id
            }
             
        return {
            "status": "completed",
            "result": final_state.values,
            "thread_id": thread_id
        }