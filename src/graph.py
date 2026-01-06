from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state import TripState
from nodes import TripNodes

def build_trip_graph(nodes: TripNodes, memory: MemorySaver) -> StateGraph:
    """LangGraph 워크플로우 구성"""
    workflow = StateGraph(TripState)

    # 노드 추가
    workflow.add_node("analyze_user_input", nodes.analyze_user_input)
    workflow.add_node("request_activity_preference", nodes.request_activity_preference)
    workflow.add_node("request_food_preference", nodes.request_food_preference)
    workflow.add_node("discover_activity_places", nodes.discover_activity_places)
    workflow.add_node("discover_dining_places", nodes.discover_dining_places)
    workflow.add_node("discover_cafe_places", nodes.discover_cafe_places)
    workflow.add_node("discover_drinking_places", nodes.discover_drinking_places)
    workflow.add_node("generate_itinerary", nodes.generate_itinerary)
    workflow.add_node("request_refinement_feedback", nodes.request_refinement_feedback)
    workflow.add_node("validate_itinerary_quality", nodes.validate_itinerary_quality)

    # 엣지 정의
    workflow.set_entry_point("analyze_user_input")

    # 조건부 엣지: 입력 타입과 테마 설정에 따라 분기
    workflow.add_conditional_edges(
        "analyze_user_input",
        nodes.route_after_analysis,
        {
            "ask_activity": "request_activity_preference",
            "skip_to_activity": "discover_activity_places",
            "skip_to_food": "request_food_preference"
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
        nodes.determine_next_step,
        {
            "refine_region": "discover_activity_places",
            "refine_place": "discover_dining_places",
            "refine_food": "discover_dining_places",
            "refine_cafe": "discover_cafe_places",
            "complete": END
        }
    )

    return workflow.compile(
        checkpointer=memory,
        interrupt_after=["request_activity_preference", "request_food_preference", "request_refinement_feedback"]
    )
