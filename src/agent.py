from langchain_community.chat_models import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from typing import Optional

from kakao_client import KakaoMapClient
from time_calculator import TimeCalculator
from models import TimeSettings
from state import TripState
from nodes import TripNodes
from graph import build_trip_graph
from database import init_db
from db_logger import DatabaseLogger

load_dotenv()


class TripPlannerAgent:
    """여행 계획 에이전트"""

    def __init__(self):
        self.llm = ChatOllama(
            model="llama3.2",
            temperature=0.7,
        )
        self.kakao_client = KakaoMapClient()
        self.time_calc = TimeCalculator()
        self.memory = MemorySaver()
        
        # 데이터베이스 초기화
        try:
            self.engine = init_db()
            print("[INFO] Database initialized successfully")
        except Exception as e:
            print(f"[WARNING] Database initialization failed: {e}")
            self.engine = None
        
        # 노드 및 그래프 초기화
        self.nodes = TripNodes(self.llm, self.kakao_client, self.time_calc, self.engine)
        self.graph = build_trip_graph(self.nodes, self.memory)

    async def plan_trip(
            self,
            user_input: str,
            session_id: Optional[str] = None,
            time_settings: Optional[TimeSettings] = None
    ) -> dict:
        """여행 계획 실행"""
        # 워크플로우 ID 생성 (이것이 곧 thread_id가 됨)
        import uuid
        workflow_id = str(uuid.uuid4())
        
        config = {"configurable": {"thread_id": workflow_id}}
        # 초기 상태이므로 로드할 필요 없음 (항상 새로 시작)
        
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
            "user_intent": None,
            "workflow_id": None
        }
        
        # DB에 워크플로우 시작 기록
        if self.engine:
            try:
                logger = DatabaseLogger(self.engine)
                # 여기서는 사용자 구분이 모호하므로 임시 유저 사용 (TODO: 로그인 연동 필요)
                user = logger.get_or_create_user(username="anonymous")
                workflow = logger.start_workflow(user.id, initial_state, workflow_id=workflow_id, session_id=workflow_id)
                initial_state["workflow_id"] = workflow_id
                logger.close()
                print(f"[DB] Workflow started with ID: {workflow.id}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[ERROR] Failed to log workflow start: {e}")
        else:
            initial_state["workflow_id"] = workflow_id
        
        await self.graph.ainvoke(initial_state, config)
        
        # 상태 조회
        final_state = await self.graph.aget_state(config)

        if final_state.next:
            # 워크플로우 상태 업데이트 (대기 중)
            if self.engine:
                try:
                    logger = DatabaseLogger(self.engine)
                    logger.current_workflow_id = final_state.values.get("workflow_id")
                    logger.complete_workflow(final_state.values, status="awaiting_input")
                    logger.close()
                except Exception as e:
                    print(f"[ERROR] Failed to log workflow status update: {e}")

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
                "session_id": workflow_id,
                "workflow_id": workflow_id
            }

        # 워크플로우 완료 기록
        if self.engine:
            try:
                logger = DatabaseLogger(self.engine)
                logger.current_workflow_id = final_state.values.get("workflow_id")
                logger.complete_workflow(final_state.values)
                logger.close()
                print(f"[DB] Workflow completed")
            except Exception as e:
                print(f"[ERROR] Failed to log workflow completion: {e}")

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
            "progress": final_state.values.get("progress_messages", []),
            "session_id": workflow_id,
            "workflow_id": workflow_id
        }

    async def provide_user_feedback(self, workflow_id: str, feedback_content: str) -> dict:
        """사용자 피드백 제공 (workflow_id를 thread_id로 사용)"""
        # workflow_id 자체가 thread_id
        config = {"configurable": {"thread_id": workflow_id}}

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
                "progress": final_state.values.get("progress_messages", []),
                "session_id": workflow_id,
                "workflow_id": workflow_id
            }

        # 워크플로우 완료 기록 (피드백 후)
        if self.engine:
            try:
                logger = DatabaseLogger(self.engine)
                logger.current_workflow_id = final_state.values.get("workflow_id")
                # 피드백 후 완료되었으면 completed, 아니면 유지 (여기서는 완료된 경우만 진입)
                logger.complete_workflow(final_state.values)
                logger.close()
            except Exception as e:
                print(f"[ERROR] Failed to log workflow completion (feedback): {e}")

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
            "progress": final_state.values.get("progress_messages", []),
            "session_id": workflow_id,
            "workflow_id": workflow_id
        }