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


class UserIntent(BaseModel):
    """자연어 분석 결과"""
    location: str  # 지역명 (예: "홍대", "강남")
    
    # 각 카테고리별 요구사항 및 구체적 키워드(분위기 등)
    activity_required: bool = True
    activity_preference: Optional[str] = None
    activity_keywords: List[str] = Field(default_factory=list)  # 예: ["활동적인", "이색적인"]
    
    dining_required: bool = True
    food_preference: Optional[str] = None
    food_keywords: List[str] = Field(default_factory=list)  # 예: ["가성비", "노포"]
    
    cafe_required: bool = True
    cafe_preference: Optional[str] = None
    cafe_keywords: List[str] = Field(default_factory=list)  # 예: ["조용한", "뷰좋은"]
    
    drinking_required: bool = True
    drinking_preference: Optional[str] = None
    drinking_keywords: List[str] = Field(default_factory=list)  # 예: ["시끄러운", "헌팅"]

