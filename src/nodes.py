import httpx
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime, timedelta
from typing import List, Optional

from state import TripState
from models import ScheduleItem, Location, TravelInfo
from kakao_client import KakaoMapClient
from time_calculator import TimeCalculator

class TripNodes:
    def __init__(self, llm: ChatOllama, kakao_client: KakaoMapClient, time_calc: TimeCalculator):
        self.llm = llm
        self.kakao_client = kakao_client
        self.time_calc = time_calc

    def route_after_analysis(self, state: TripState) -> str:
        """입력 분석 후 라우팅 (테마 및 자연어 분석 결과 고려)"""
        input_type = state.get("input_type", "region")
        user_intent = state.get("user_intent")
        date_theme = state.get("date_theme")

        # 1. 특정 장소 검색인 경우 -> 활동 검색 건너뜀
        if input_type == "specific_place":
            # 음식 취향도 이미 알거나 필요 없다면 바로 식당 검색으로
            if user_intent and (not user_intent.dining_required or user_intent.food_preference):
                return "skip_to_dining"
            return "skip_to_food"

        # 2. 테마가 설정되어 있는 경우 -> HIL 건너뛰기
        if date_theme and date_theme.theme:
            return "skip_to_activity"

        # 3. 자연어 분석 결과에 활동 선호도가 이미 있는 경우 -> HIL 건너뛰기
        if user_intent and user_intent.activity_preference:
            return "skip_to_activity"

        # 4. 아무것도 없다면 -> HIL 활동 선호도 질문
        return "ask_activity"

    def route_after_activity(self, state: TripState) -> str:
        """활동 검색 후 라우팅 (음식 선호도 고려)"""
        user_intent = state.get("user_intent")

        # 자연어 분석 결과에 식사 선호도가 이미 있거나, 식사 검색이 필요 없는 경우 -> HIL 건너뛰기
        if user_intent:
            if not user_intent.dining_required or user_intent.food_preference:
                return "skip_to_dining"

        return "ask_food"

    async def analyze_user_input(self, state: TripState) -> TripState:
        """사용자 입력 분석 (자연어 처리 강화)"""
        print(f"[DEBUG] Analyzing input: {state['user_input']}")
        
        # 자연어 분석 프롬프트
        messages = [
            SystemMessage(content="""
            당신은 여행 계획 전문가입니다. 사용자의 자연어 입력을 분석하여 다음 정보를 추출하세요:
            
            1. 지역명 (예: "홍대", "강남", "신촌")
            2. 활동 장소 필요 여부 및 선호도 (예: "보드게임카페", "방탈출", "전시" 등)
            3. 식사 장소 필요 여부 및 음식 선호도 (예: "한식", "양식", "일식" 등)
            4. 카페 필요 여부 및 선호도
            5. 술집 필요 여부 및 선호도
            
            **중요**: 
            - 사용자가 명시적으로 "필요없다", "안 갈거야", "제외" 등의 표현을 사용하면 해당 항목은 required=false
            - 언급이 없으면 기본값으로 required=true
            - 구체적인 선호도가 있으면 preference에 기록
            
            응답 형식 (각 줄은 정확히 이 형식을 따라야 함):
            LOCATION: [지역명]
            ACTIVITY_REQUIRED: [true|false]
            ACTIVITY_PREFERENCE: [선호도 또는 none]
            DINING_REQUIRED: [true|false]
            FOOD_PREFERENCE: [음식 종류 또는 none]
            CAFE_REQUIRED: [true|false]
            CAFE_PREFERENCE: [선호도 또는 none]
            DRINKING_REQUIRED: [true|false]
            DRINKING_PREFERENCE: [선호도 또는 none]
            
            예시 1: "홍대에서 보드게임카페 가고 한식 먹고 싶어"
            LOCATION: 홍대
            ACTIVITY_REQUIRED: true
            ACTIVITY_PREFERENCE: 보드게임카페
            DINING_REQUIRED: true
            FOOD_PREFERENCE: 한식
            CAFE_REQUIRED: true
            CAFE_PREFERENCE: none
            DRINKING_REQUIRED: true
            DRINKING_PREFERENCE: none
            
            예시 2: "강남에서 전시 보고 술은 안 마실거야"
            LOCATION: 강남
            ACTIVITY_REQUIRED: true
            ACTIVITY_PREFERENCE: 전시
            DINING_REQUIRED: true
            FOOD_PREFERENCE: none
            CAFE_REQUIRED: true
            CAFE_PREFERENCE: none
            DRINKING_REQUIRED: false
            DRINKING_PREFERENCE: none
            """),
            HumanMessage(content=f"입력: {state['user_input']}")
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        
        # 파싱 결과 저장
        from models import UserIntent
        
        intent_data = {
            "location": "",
            "activity_required": True,
            "activity_preference": None,
            "dining_required": True,
            "food_preference": None,
            "cafe_required": True,
            "cafe_preference": None,
            "drinking_required": True,
            "drinking_preference": None
        }
        
        # LLM 응답 파싱
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.upper().startswith("LOCATION:"):
                intent_data["location"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("ACTIVITY_REQUIRED:"):
                value = line.split(":", 1)[1].strip().lower()
                intent_data["activity_required"] = value == "true"
            elif line.upper().startswith("ACTIVITY_PREFERENCE:"):
                value = line.split(":", 1)[1].strip()
                intent_data["activity_preference"] = None if value.lower() == "none" else value
            elif line.upper().startswith("DINING_REQUIRED:"):
                value = line.split(":", 1)[1].strip().lower()
                intent_data["dining_required"] = value == "true"
            elif line.upper().startswith("FOOD_PREFERENCE:"):
                value = line.split(":", 1)[1].strip()
                intent_data["food_preference"] = None if value.lower() == "none" else value
            elif line.upper().startswith("CAFE_REQUIRED:"):
                value = line.split(":", 1)[1].strip().lower()
                intent_data["cafe_required"] = value == "true"
            elif line.upper().startswith("CAFE_PREFERENCE:"):
                value = line.split(":", 1)[1].strip()
                intent_data["cafe_preference"] = None if value.lower() == "none" else value
            elif line.upper().startswith("DRINKING_REQUIRED:"):
                value = line.split(":", 1)[1].strip().lower()
                intent_data["drinking_required"] = value == "true"
            elif line.upper().startswith("DRINKING_PREFERENCE:"):
                value = line.split(":", 1)[1].strip()
                intent_data["drinking_preference"] = None if value.lower() == "none" else value
        
        # UserIntent 객체 생성
        user_intent = UserIntent(**intent_data)
        state["user_intent"] = user_intent
        state["parsed_location"] = user_intent.location
        state["input_type"] = "region"  # 자연어 입력은 기본적으로 지역 검색
        
        # 선호도를 state에도 저장 (기존 로직 호환성)
        if user_intent.activity_preference:
            state["user_activity_preference"] = user_intent.activity_preference
        if user_intent.food_preference:
            state["user_food_preference"] = user_intent.food_preference
        
        # 진행 메시지
        state["progress_messages"].append(f"✓ 입력 분석 완료: {user_intent.location}")
        if user_intent.activity_preference:
            state["progress_messages"].append(f"  - 활동: {user_intent.activity_preference}")
        if user_intent.food_preference:
            state["progress_messages"].append(f"  - 음식: {user_intent.food_preference}")
        if not user_intent.cafe_required:
            state["progress_messages"].append(f"  - 카페: 제외")
        if not user_intent.drinking_required:
            state["progress_messages"].append(f"  - 술집: 제외")
        
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
        # 자연어 분석 결과 확인
        user_intent = state.get("user_intent")
        if user_intent and not user_intent.activity_required:
            state["activity_places"] = []
            state["progress_messages"].append("✓ 활동 장소 검색 건너뛰기 (사용자 요청)")
            return state
        
        location = state["parsed_location"]
        radius = state.get("search_radius", 2000)

        # 🎨 테마 설정 vs 사용자 선호도 경쟁
        date_theme = state.get("date_theme")
        theme = date_theme.theme if date_theme else None

        # 사용자 선호도 (NLP 또는 HIL)
        preference = state.get("user_activity_preference")

        # 1. 사용자 선호도가 명확하면 최우선 적용
        if preference and preference not in ["상관없음", "없음"]:
            state["progress_messages"].append(f"✓ '{preference}' 테마로 활동 장소를 검색합니다. (사용자 선호 우선)")

            # 키워드 확장
            expansion_prompt = f"""
            '{location}' 지역에서 '{preference}'와(과) 관련된 장소를 찾기 위한 검색 키워드 3개를 쉼표로 구분하여 나열하세요.
            다른 설명 없이 오직 키워드만 반환하세요.
            예시: {location} {preference}, {location} 추천, {location} 데이트
            """

            try:
                expansion_msg = [HumanMessage(content=expansion_prompt)]
                expansion_res = await self.llm.ainvoke(expansion_msg)
                content = expansion_res.content.strip()
                keywords = [k.strip() for k in content.split(",") if k.strip()]
            except Exception as e:
                print(f"[ERROR] Keyword expansion failed: {e}")
                keywords = []

            # 기본 키워드 추가 (LLM 실패 대비 및 정확도 보장)
            default_keyword = f"{location} {preference}"
            if default_keyword not in keywords:
                keywords.insert(0, default_keyword)

            print(f"[DEBUG] Expanded keywords for {preference}: {keywords}")

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

        # 2. 선호도가 없으면 테마 적용
        elif theme:
            state["progress_messages"].append(f"✓ '{theme}' 테마로 활동 장소를 검색합니다.")
            places = await self.kakao_client.find_activity_places(location, theme, radius)
            state["activity_places"] = places

        # 3. 둘 다 없으면 기본 검색
        else:
            places = await self.kakao_client.find_activity_places(location, None, radius)
            state["activity_places"] = places

        state["progress_messages"].append(f"✓ 활동 장소 {len(state['activity_places'])}개 발견")
        return state

    async def discover_dining_places(self, state: TripState) -> TripState:
        """식사 장소 검색 (분위기 반영)"""
        # 자연어 분석 결과 확인
        user_intent = state.get("user_intent")
        if user_intent and not user_intent.dining_required:
            state["dining_places"] = []
            state["progress_messages"].append("✓ 식사 장소 검색 건너뛰기 (사용자 요청)")
            return state
        
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
        state["progress_messages"].append(f"✓ 식사 장소 {len(unique_dining)}개 발견 (분위기 기반)")

        return state

    async def discover_cafe_places(self, state: TripState) -> TripState:
        """카페 검색 (분위기 반영)"""
        # 자연어 분석 결과 확인
        user_intent = state.get("user_intent")
        if user_intent and not user_intent.cafe_required:
            state["cafe_places"] = []
            state["progress_messages"].append("✓ 카페 검색 건너뛰기 (사용자 요청)")
            return state
        
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
        state["progress_messages"].append(f"✓ 카페 {len(unique_cafes)}개 발견 (분위기 기반)")
        return state

    async def discover_drinking_places(self, state: TripState) -> TripState:
        """술집 검색"""
        # 자연어 분석 결과 확인
        user_intent = state.get("user_intent")
        if user_intent and not user_intent.drinking_required:
            state["drinking_places"] = []
            state["progress_messages"].append("✓ 술집 검색 건너뛰기 (사용자 요청)")
            return state
        
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
        state["progress_messages"].append(f"✓ 술집/바 {len(unique_bars)}개 발견")
        return state

    async def generate_itinerary(self, state: TripState) -> TripState:
        """⏰ 시간표가 포함된 여행 일정 생성"""
        places = []

        # 장소 수집
        if state["input_type"] == "specific_place" and state.get("starting_point"):
            # 시작점이 고정된 경우
            start_point = state["starting_point"]
            places = []
            places.append(("activity", start_point)) # 시작점은 무조건 포함
            
            # 나머지 경로 최적화 (시작점 제외하고 최적화)
            # 여기서는 편의상 시작점이 activity라고 가정했지만, 실제로는 타입이 다를 수 있음.
            # 하지만 user_input이 specific_place면 보통 그곳을 기점으로 함.
            
            optimized = self.time_calc.find_optimized_path(
                start_point,
                [], # activities (시작점이 엑티비티라면 제외) -> 로직상 분리 필요하지만 복잡도 줄이기 위해 공백
                state["dining_places"],
                state["cafe_places"],
                state["drinking_places"]
            )
            places.extend(optimized)
            
        else:
            # 지역 검색인 경우, 전체 최적화
            # 시작점이 없으므로 첫 번째 장소가 기준이 됨 (find_optimized_path 내부 로직에 맡김 or None)
            places = self.time_calc.find_optimized_path(
                None,
                state["activity_places"],
                state["dining_places"],
                state["cafe_places"],
                state["drinking_places"]
            )

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
