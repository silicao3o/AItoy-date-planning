"""
데이터베이스 사용 예시
워크플로우 실행 시 DB 로깅을 통합하는 방법을 보여줍니다.
"""
import asyncio
from datetime import datetime

from database import init_db
from db_logger import DatabaseLogger
from state import TripState
from models import TimeSettings, UserIntent


async def example_workflow_with_logging():
    """DB 로깅이 통합된 워크플로우 실행 예시"""
    
    # 1. 데이터베이스 초기화
    engine = init_db("sqlite:///trip_planner.db")
    logger = DatabaseLogger(engine)
    
    try:
        # 2. 사용자 생성 또는 가져오기
        user = logger.get_or_create_user(
            username="test_user",
            email="test@example.com"
        )
        print(f"✓ User: {user.username} (ID: {user.id})")
        
        # 3. 초기 State 설정
        initial_state: TripState = {
            "user_input": "홍대에서 데이트하고 싶어",
            "input_type": "region",
            "parsed_location": None,
            "starting_point": None,
            "activity_places": [],
            "dining_places": [],
            "cafe_places": [],
            "drinking_places": [],
            "final_itinerary": [],
            "search_radius": 2000,
            "time_settings": TimeSettings(
                enabled=True,
                start_time="14:00",
                duration_hours=6
            ),
            "user_intent": None,
            "progress_messages": [],
            "needs_refinement": False,
            "user_activity_preference": None,
            "user_food_preference": None,
            "user_feedback": None,
            "next_action": None
        }
        
        # 4. 워크플로우 시작
        workflow = logger.start_workflow(user.id, initial_state)
        print(f"✓ Workflow started (ID: {workflow.id})")
        
        # 5. 노드 1: 입력 분석
        with logger.node_context("analyze_user_input", "analysis") as node:
            print(f"  → Node: {node.node_name} (ID: {node.id})")
            
            # 실제 노드 로직 시뮬레이션
            await asyncio.sleep(0.1)  # LLM 호출 시뮬레이션
            
            # LLM 생성 기록
            start_time = datetime.utcnow()
            
            system_prompt = "당신은 여행 계획 전문가입니다..."
            user_prompt = initial_state["user_input"]
            llm_output = """{
                "location": "홍대",
                "activity": {"required": true, "preference": "전시", "keywords": ["문화", "예술"]},
                "dining": {"required": true, "preference": null, "keywords": ["분위기좋은"]},
                "cafe": {"required": true, "preference": null, "keywords": ["감성"]},
                "drinking": {"required": false, "preference": null, "keywords": []}
            }"""
            
            latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.log_generation(
                model_name="llama3.2",
                model_provider="ollama",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output=llm_output,
                node_id=node.id,
                temperature=0.7,
                latency_ms=latency
            )
            
            # State 업데이트
            initial_state["user_intent"] = UserIntent(
                location="홍대",
                activity_required=True,
                activity_preference="전시",
                activity_keywords=["문화", "예술"],
                dining_required=True,
                food_keywords=["분위기좋은"],
                cafe_required=True,
                cafe_keywords=["감성"],
                drinking_required=False
            )
            initial_state["parsed_location"] = "홍대"
            initial_state["progress_messages"].append("✓ 입력 분석 완료: 홍대")
            
            logger.log_node_complete(node.id, initial_state)
        
        # 6. 노드 2: 활동 장소 검색
        with logger.node_context("discover_activity_places", "search") as node:
            print(f"  → Node: {node.node_name} (ID: {node.id})")
            
            await asyncio.sleep(0.05)  # API 호출 시뮬레이션
            
            from models import Location
            
            # 검색 결과 시뮬레이션
            initial_state["activity_places"] = [
                Location(
                    name="홍대 미술관",
                    category="문화시설",
                    address="서울 마포구 홍익로",
                    x=126.9222,
                    y=37.5511,
                    phone="02-1234-5678"
                )
            ]
            initial_state["progress_messages"].append("✓ 활동 장소 1개 발견")
            
            logger.log_node_complete(
                node.id, 
                initial_state,
                output_data={"places_found": 1}
            )
        
        # 7. 노드 3: 식당 검색 (스킵 예시)
        logger.log_node_skip(
            "discover_dining_places",
            "search",
            "사용자가 식사 불필요 선택"
        )
        
        # 8. 워크플로우 완료
        from models import ScheduleItem
        
        initial_state["final_itinerary"] = [
            ScheduleItem(
                order=1,
                start_time="14:00",
                end_time="16:00",
                duration_minutes=120,
                location=initial_state["activity_places"][0],
                estimated_time="2시간",
                notes="문화 활동"
            )
        ]
        
        logger.complete_workflow(initial_state, status="completed")
        print(f"✓ Workflow completed")
        
        # 9. 히스토리 조회
        print("\n=== Workflow History ===")
        history = logger.get_workflow_history(user.id, limit=5)
        for wf in history:
            print(f"  - [{wf.status}] {wf.user_input[:30]}... (created: {wf.created_at})")
        
        # 10. 상세 정보 조회
        print(f"\n=== Workflow Details (ID: {workflow.id}) ===")
        details = logger.get_workflow_details(workflow.id)
        if details:
            print(f"  Status: {details['workflow'].status}")
            print(f"  Nodes executed: {len(details['nodes'])}")
            for n in details['nodes']:
                print(f"    - {n.node_name} ({n.status}) - {n.duration_ms}ms")
            print(f"  LLM generations: {len(details['generations'])}")
            for g in details['generations']:
                print(f"    - {g.model_name} - {g.latency_ms}ms")
    
    finally:
        logger.close()


async def example_error_handling():
    """에러 처리 예시"""
    
    engine = init_db("sqlite:///trip_planner.db")
    logger = DatabaseLogger(engine)
    
    try:
        user = logger.get_or_create_user("error_test_user")
        
        initial_state: TripState = {
            "user_input": "에러 테스트",
            "input_type": "region",
            "parsed_location": None,
            "starting_point": None,
            "activity_places": [],
            "dining_places": [],
            "cafe_places": [],
            "drinking_places": [],
            "final_itinerary": [],
            "search_radius": 2000,
            "time_settings": None,
            "user_intent": None,
            "progress_messages": [],
            "needs_refinement": False,
            "user_activity_preference": None,
            "user_food_preference": None,
            "user_feedback": None,
            "next_action": None
        }
        
        workflow = logger.start_workflow(user.id, initial_state)
        
        try:
            with logger.node_context("failing_node", "test") as node:
                # 의도적으로 에러 발생
                raise ValueError("This is a test error")
        except ValueError as e:
            print(f"✓ Error caught and logged: {e}")
        
        # 워크플로우 실패로 마킹
        logger.fail_workflow("Node execution failed")
        
        # 확인
        details = logger.get_workflow_details(workflow.id)
        print(f"Workflow status: {details['workflow'].status}")
        print(f"Failed node: {details['nodes'][0].node_name}")
        print(f"Error: {details['nodes'][0].error_message}")
    
    finally:
        logger.close()


if __name__ == "__main__":
    print("=== Example 1: Normal Workflow ===")
    asyncio.run(example_workflow_with_logging())
    
    print("\n\n=== Example 2: Error Handling ===")
    asyncio.run(example_error_handling())
