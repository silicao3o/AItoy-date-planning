from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field


class Location(BaseModel):
    """장소 정보"""
    name: str
    category: str
    address: str
    x: float  # 경도
    y: float  # 위도
    phone: Optional[str] = None
    place_url: Optional[str] = None
    distance: Optional[int] = None
    rating: Optional[float] = None  # 평점 (추가)
    review_count: Optional[int] = None  # 리뷰 수 (추가)


class TravelInfo(BaseModel):
    """이동 정보"""
    method: str  # "walk", "subway", "bus"
    duration_minutes: int  # 소요 시간 (분)
    distance_meters: int  # 거리 (미터)
    description: str  # "도보 5분" 등


class ScheduleItem(BaseModel):
    """스케줄 항목"""
    order: int
    start_time: Optional[str] = None  # "14:00" (추가)
    end_time: Optional[str] = None  # "16:00" (추가)
    duration_minutes: Optional[int] = None  # 소요 시간 (분) (추가)
    location: Location
    estimated_time: str  # "2시간", "1시간 30분" 등
    notes: Optional[str] = None
    travel_to_next: Optional[TravelInfo] = None  # 다음 장소로의 이동 정보 (추가)


class TimeSettings(BaseModel):
    """시간 설정"""
    enabled: bool = Field(default=False, description="시간 설정 사용 여부")
    start_time: str = Field(default="14:00", description="시작 시간 (HH:MM)")
    duration_hours: int = Field(default=6, ge=2, le=12, description="데이트 시간 (시간)")


class DateTheme(BaseModel):
    """데이트 테마"""
    theme: str = Field(
        default="casual",
        description="테마: cultural(문화예술), healing(힐링자연), activity(액티비티), foodie(맛집투어), nightlife(나이트라이프)"
    )
    atmosphere: str = Field(
        default="casual",
        description="분위기: casual(캐주얼), romantic(로맨틱), energetic(활기찬)"
    )


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
    date_theme: Optional[DateTheme]  # 데이트 테마

    # 상태 관리
    progress_messages: List[str]  # 진행 상황 메시지
    needs_refinement: bool  # 재정리 필요 여부
    user_activity_preference: Optional[str]  # 사용자 선호 활동 카테고리 (HIL용)
    user_food_preference: Optional[str]  # 사용자 선호 음식 종류 (HIL용)
    user_feedback: Optional[str]  # 사용자 피드백
    next_action: Optional[str]  # 다음 액션