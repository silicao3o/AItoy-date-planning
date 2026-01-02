from typing import TypedDict, List, Optional
from pydantic import BaseModel


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


class ScheduleItem(BaseModel):
    """스케줄 항목"""
    order: int
    location: Location
    estimated_time: str  # "2시간", "1시간 30분" 등
    notes: Optional[str] = None


class TripState(TypedDict):
    """여행 계획 상태"""
    region: str  # 사용자가 입력한 지역
    parsed_region: Optional[str]  # 파싱된 지역명
    attractions: List[Location]  # 찾은 놀거리
    restaurants: List[Location]  # 찾은 음식점
    desserts: List[Location]     # 찾은 디저트/카페
    bars: List[Location]         # 찾은 술집
    schedule: List[ScheduleItem]  # 최종 스케줄
    search_radius: int  # 검색 반경 (미터)
    messages: List[str]  # 진행 상황 메시지
    needs_replan: bool  # 재계획 필요 여부
    location_type: Optional[str] # "region" or "spot"
    start_location: Optional[Location] # 시작 장소 (spot일 경우)
    preferred_category: Optional[str] # 선호하는 놀거리 카테고리 (HIL 용)