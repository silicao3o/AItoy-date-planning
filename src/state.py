from typing import TypedDict, List, Optional
from models import Location, ScheduleItem, TimeSettings, UserIntent

class TripState(TypedDict):
    """여행 계획 상태"""
    user_input: str  # 사용자가 입력한 지역/장소
    input_type: Optional[str]  # "region" (지역) or "specific_place" (특정 장소)
    parsed_location: Optional[str]  # 파싱된 위치명
    starting_point: Optional[Location]  # 시작 지점 (특정 장소일 경우)

    # 장소 목록
    activity_places: List[Location]  # 찾은 활동 장소 (놀거리/명소)
    dining_places: List[Location]  # 찾은 식사 장소
    cafe_places: List[Location]  # 찾은 카페/디저트 장소
    drinking_places: List[Location]  # 찾은 술집/바
    final_itinerary: List[ScheduleItem]  # 최종 여행 일정

    # 검색 설정
    search_radius: int  # 검색 반경 (미터)

    # 사용자 설정 (프론트에서 받음)
    time_settings: Optional[TimeSettings]  # 시간 설정
    user_intent: Optional['UserIntent']  # 자연어 분석 결과

    # 상태 관리
    progress_messages: List[str]  # 진행 상황 메시지
    needs_refinement: bool  # 재정리 필요 여부
    user_activity_preference: Optional[str]  # 사용자 선호 활동 카테고리 (HIL용)
    user_food_preference: Optional[str]  # 사용자 선호 음식 종류 (HIL용)
    user_feedback: Optional[str]  # 사용자 피드백
    next_action: Optional[str]  # 다음 액션
    workflow_id: Optional[str]  # DB 워크플로우 ID (UUID)
    current_node_id: Optional[str]  # 현재 실행 중인 노드 ID (UUID)
