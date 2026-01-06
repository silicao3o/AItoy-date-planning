from langchain_community.chat_models import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from typing import Optional

from kakao_client import KakaoMapClient
from time_calculator import TimeCalculator
from models import TimeSettings, DateTheme
from state import TripState
from nodes import TripNodes
from graph import build_trip_graph

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
        
        # 노드 및 그래프 초기화
        self.nodes = TripNodes(self.llm, self.kakao_client, self.time_calc)
        self.graph = build_trip_graph(self.nodes, self.memory)

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
                "date_theme": date_theme,
                "user_intent": None
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